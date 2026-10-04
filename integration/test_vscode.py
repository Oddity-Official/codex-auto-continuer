"""Actual extension-host/native-owner integration; not a visual webview test."""
from __future__ import annotations

import hashlib
import itertools
import json
import shutil
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import pytest

from codex_auto_continuer.codex import codex_version
from codex_auto_continuer.state import load_state
from native_support import NativeFixture, TOKEN


def wait_result(home, name, process, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        error = home / "error.json"
        if error.exists():
            raise AssertionError(json.loads(error.read_text(encoding="utf-8"))["error"])
        target = home / name
        if target.exists():
            return json.loads(target.read_text(encoding="utf-8"))
        if process.poll() is not None:
            raise AssertionError(f"Isolated VS Code exited before {name}: {process.returncode}")
        time.sleep(0.1)
    raise TimeoutError(f"Isolated VS Code did not produce {name} within {seconds}s")


def test_installed_extension_filtering_and_quota_recovery(request):
    code = request.config.getoption("--vscode-executable")
    extension = request.config.getoption("--vscode-extension")
    if not code or not extension:
        pytest.fail("Use scripts/verify-vscode.ps1 with -CodePath and -ExtensionPath; this is an explicit integration gate.")
    extension = Path(extension).resolve(strict=True)
    manifest = json.loads((extension / "package.json").read_text(encoding="utf-8"))
    assert (manifest["publisher"], manifest["name"]) == ("openai", "chatgpt")
    binary = extension / "bin/windows-x86_64/codex.exe"
    originals = (extension / "package.json", extension / manifest["main"], binary)
    fingerprints = {path: hashlib.sha256(path.read_bytes()).digest() for path in originals}
    version = codex_version(str(binary), 10)
    root = Path(__file__).resolve().parents[1]
    with NativeFixture(root, str(binary)) as native:
        # VS Code's workbench checks remote services; the proxy must reject, never forward.
        native.service.allow_rejected_external = True
        profile = native.home / "profile"
        settings = profile / "User/settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"telemetry.telemetryLevel": "off",
            "update.mode": "none", "extensions.autoUpdate": False, "extensions.autoCheckUpdates": False,
            "workbench.startupEditor": "none", "window.title": "CAC isolated VS Code fixture",
            "chatgpt.runCodexInWindowsSubsystemForLinux": False}), encoding="utf-8")
        env = dict(native.env, CAC_VSCODE_TEST=str(native.home))
        env["CAC_VSCODE_EXTENSION"] = str(extension)
        env.pop("ELECTRON_RUN_AS_NODE", None)
        output = native.stack.enter_context((native.home / "vscode.stdout").open("wb"))
        # The test bootstrap observes spawn before onStartupFinished activates the
        # original bundle. Its context still points to installed assets/binaries.
        bootstrap = native.home / "extension"
        bootstrap.mkdir()
        test_manifest = dict(manifest, main="./vscode_bootstrap.cjs")
        (bootstrap / "package.json").write_text(json.dumps(test_manifest), encoding="utf-8")
        for name in ("vscode_bootstrap.cjs", "vscode_driver.cjs"):
            shutil.copyfile(root / "integration" / name, bootstrap / name)
        process = subprocess.Popen([str(Path(code).resolve(strict=True)),
            f"--user-data-dir={profile}", f"--extensions-dir={native.home / 'extensions'}",
            f"--extensionDevelopmentPath={bootstrap}",
            f"--extensionTestsPath={bootstrap / 'vscode_driver.cjs'}",
            "--disable-extensions", "--disable-workspace-trust", "--skip-welcome", "--skip-release-notes",
            str(native.home)], env=env, cwd=native.home, stdout=output, stderr=output)

        def stop():
            if process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True, timeout=5, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
                if process.poll() is None:
                    process.kill()
            process.wait(timeout=5)

        native.stack.callback(stop)
        failed = wait_result(native.home, "failed.json", process)
        owner = wait_result(native.home, "owner.json", process)
        assert Path(owner["executable"]).resolve() == binary.resolve()
        assert owner["originator"] == "codex_vscode"
        assert failed["extensionVersion"] == manifest["version"]
        thread_id = failed["threadId"]
        observer = native.client()
        thread = observer.thread_read(thread_id)
        assert thread["source"] == "vscode"
        assert thread["originator"] == "codex_vscode"
        assert thread["status"]["type"] == "notLoaded"
        native.assert_quota_failure(observer.latest_turn(thread_id))
        supervisor = native.supervisor()
        for choices in itertools.product((False, True), repeat=3):
            clients = tuple(client for client, enabled in zip(("cli", "vscode", "desktop"), choices) if enabled)
            supervisor.config = replace(supervisor.config, clients=clients)
            assert supervisor._scope_accepts(thread) is choices[1], clients
        for clients in (("cli",), ("desktop",), ()):
            supervisor.config = replace(supervisor.config, clients=clients)
            result = supervisor.run_cycle()
            assert result.detected == result.dispatched == result.pending == 0
        supervisor.config = replace(supervisor.config, clients=("vscode",))
        for cycle in range(3):
            result = supervisor.run_cycle()
            assert result.ordinary_usage_allowed is False
            assert result.detected == (1 if cycle == 0 else 0)
            assert result.pending == 1 and result.dispatched == 0
            assert native.service.inference_count == 1
        saved = load_state(supervisor.state_file).obligations
        assert len(saved) == 1 and saved[0].thread_id == thread_id
        assert saved[0].failed_turn_id == failed["failedTurnId"]
        native.service.allowed = True
        native.service.fail_inference = False
        result = supervisor.run_cycle()
        assert result.dispatched == 1 and result.ordinary_usage_allowed is True
        completed = wait_result(native.home, "completed.json", process)
        assert completed["turns"] == 2 and completed["status"] == "completed"
        assert native.service.user_messages == ["VS Code quota fixture", "Continue"]
        for _ in range(3):
            result = supervisor.run_cycle()
            assert result.dispatched == result.pending == 0
        assert native.service.inference_count == 2
        assert len(observer.request("thread/turns/list", {"threadId": thread_id, "limit": 100,
            "sortDirection": "asc", "itemsView": "notLoaded"})["data"]) == 2
        assert not observer.queue_items(thread_id)
        names = [event["event"] for event in native.events()]
        assert names.count("dispatch.submitted") == 1
        assert "dispatch.separate_owner" in names and "delivery.subsequent_turn" in names
        log = native.telemetry_file.read_text(encoding="utf-8")
        for private in (TOKEN, thread_id, failed["failedTurnId"], "VS Code quota fixture", "CAC_FIXTURE_OK"):
            assert private not in log
        (native.home / "finish").touch()
        assert process.wait(timeout=20) == 0
        assert fingerprints == {path: hashlib.sha256(path.read_bytes()).digest() for path in originals}
        print(f"\nVS Code {failed['vscodeVersion']}; extension {manifest['version']}; Codex {version}: "
            "8 filter combinations, quota denial, one original-owner continuation, no duplicates, "
            "private telemetry and original-file hashes passed")
