"""Unchanged current extension, isolated profile and cliExecutable bridge.

This establishes connection only. It does not inject composer/write RPCs,
certify startup-setting parity, or make the development override a supported
production configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from probe_desktop_connection import ROOT, Relay
from native_support import NativeFixture
from codex_auto_continuer.config import Config
from codex_auto_continuer.codex import find_codex, codex_version
from codex_auto_continuer.supervisor import Supervisor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    args = parser.parse_args()
    extension = args.extension.resolve(strict=True)
    manifest = json.loads((extension / "package.json").read_text(encoding="utf-8"))
    assert (manifest["publisher"], manifest["name"]) == ("openai", "chatgpt")
    binary = extension / "bin/windows-x86_64/codex.exe"
    sources = [extension / "package.json", extension / manifest["main"], binary]
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
    packaged_cli = find_codex()
    cli_version = codex_version(packaged_cli, 10)
    extension_codex_version = codex_version(str(binary), 10)
    with NativeFixture(ROOT, packaged_cli, managed=True) as native:
        native.service.allow_rejected_external = True
        bridge = native.home / "CACProbeBridge.exe"
        compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        compiled = subprocess.run([str(compiler), "/nologo", "/target:exe", "/out:" + str(bridge),
            str(Path(__file__).with_name("StdioBridge.cs"))], capture_output=True, text=True,
            timeout=25, creationflags=subprocess.CREATE_NO_WINDOW)
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        with Relay(native.socket) as relay:
            profile = native.home / "vscode-profile"
            settings = profile / "User/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"chatgpt.cliExecutable": str(bridge),
                "chatgpt.runCodexInWindowsSubsystemForLinux": False, "telemetry.telemetryLevel": "off",
                "update.mode": "none", "extensions.autoUpdate": False, "extensions.autoCheckUpdates": False,
                "workbench.startupEditor": "none", "window.title": "CAC isolated extension connection probe"}), encoding="utf-8")
            env = native.env | {"CAC_OWNER_WS_URL": relay.url, "CAC_BRIDGE_NATIVE_CODEX": str(binary),
                "APPDATA": str(native.home / "roaming")}
            env.pop("ELECTRON_RUN_AS_NODE", None)
            previous = os.environ.copy()
            os.environ.clear()
            os.environ.update(native.env)
            try:
                supervisor = Supervisor(Config(codex_executable=packaged_cli, queue_holding=True), native.data / "state.json")
                native.supervisors.append(supervisor)
                supervisor.connect()
                assert supervisor.client.socket_path == native.socket
            finally:
                os.environ.clear()
                os.environ.update(previous)
            output = native.stack.enter_context((native.home / "vscode.stdout").open("wb"))
            process = subprocess.Popen([str(args.code.resolve(strict=True)), f"--user-data-dir={profile}",
                f"--extensions-dir={native.home / 'extensions'}", f"--extensionDevelopmentPath={extension}",
                "--disable-extensions", "--disable-workspace-trust", "--skip-welcome", "--skip-release-notes",
                str(native.home)], cwd=native.home, env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=output)
            try:
                deadline = time.monotonic() + 35
                while time.monotonic() < deadline:
                    if any(s.identity and s.methods.get("config/read") and s.methods.get("thread/list") for s in relay.summaries):
                        break
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                print(json.dumps({"client": "installed VS Code extension", "extensionVersion": manifest["version"],
                    "productionCACConnectionUnmodified": True, "developmentCliExecutableOverride": True,
                    "daemonCLIVersion": cli_version, "extensionBundledCLIVersion": extension_codex_version,
                    "launchSettingsParity": "not certified: adapter does not apply app-server launch overrides",
                    "connections": [{"identity": s.identity, "methods": dict(s.methods)} for s in relay.summaries],
                    "relayErrors": relay.errors, "modelRequests": native.service.inference_count,
                    "composerAcceptance": "not tested: native GUI input tool unavailable"}, indent=2))
                assert any(s.identity and s.methods.get("config/read") and s.methods.get("thread/list")
                    for s in relay.summaries), "Extension did not initialize/read through the owner"
                assert hashes == [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
            finally:
                if process.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                        timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
