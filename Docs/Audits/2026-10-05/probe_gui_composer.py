"""Actual installed GUI composer, native owner and production CAC connection.

Computer Use supplies synthetic inputs through the isolated client's normal UI.
No thread/start, turn/start or queue/add RPC is injected by this harness.
All profiles, credentials, service responses and journals are disposable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

from probe_desktop_connection import ROOT, Relay
import native_support
from codex_auto_continuer.codex import find_codex
from codex_auto_continuer.config import Config
from codex_auto_continuer.supervisor import Supervisor


class ComposerService(native_support.Service):
    def __init__(self):
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()
        self.gate = True

    def handler(self):
        parent = super().handler()
        service = self

        class Handler(parent):
            def reply(self, status, body, content_type="application/json"):
                if self.path == "/v1/responses" and service.gate:
                    service.gate = False
                    service.entered.set()
                    if not service.release.wait(240):
                        service.errors.append("Composer input gate exceeded 240 seconds")
                try:
                    super().reply(status, body, content_type)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        return Handler

    def __exit__(self, *args):
        self.release.set()
        super().__exit__(*args)


class ComposerFixture(native_support.NativeFixture):
    def start_managed(self):
        # This model fixture has no tools. Declare its real read-only policy
        # before launching clients; do not simulate Windows sandbox readiness.
        config = self.home / "config.toml"
        config.write_text('sandbox_mode = "read-only"\napproval_policy = "never"\n' +
            config.read_text(encoding="utf-8"), encoding="utf-8")
        super().start_managed()


def report(phase, **fields):
    value = {"phase": phase, **fields}
    (ROOT / ".data/composer-status.json").write_text(json.dumps(value), encoding="utf-8")
    print(json.dumps(value), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop", type=Path)
    parser.add_argument("--code", type=Path)
    parser.add_argument("--extension", type=Path)
    args = parser.parse_args()
    if bool(args.desktop) == bool(args.code) or bool(args.code) != bool(args.extension):
        parser.error("Select --desktop, or both --code and --extension")
    binary = find_codex()
    previous_service = native_support.Service
    previous_env = os.environ.copy()
    native_support.Service = ComposerService
    try:
        with ComposerFixture(ROOT, binary, managed=True) as native:
            native.service.allow_rejected_external = True
            with Relay(native.socket) as relay:
                env = native.env | {"APPDATA": str(native.home / "roaming")}
                env.pop("ELECTRON_RUN_AS_NODE", None)
                hashes = []
                sources = []
                if args.desktop:
                    env.update(CODEX_ELECTRON_USER_DATA_PATH=str(native.home / "desktop-profile"),
                        CODEX_APP_SERVER_WS_URL=relay.url)
                    command = [str(args.desktop.resolve(strict=True))]
                else:
                    extension = args.extension.resolve(strict=True)
                    manifest = json.loads((extension / "package.json").read_text(encoding="utf-8"))
                    assert (manifest["publisher"], manifest["name"]) == ("openai", "chatgpt")
                    extension_binary = extension / "bin/windows-x86_64/codex.exe"
                    sources = [extension / "package.json", extension / manifest["main"], extension_binary]
                    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
                    bridge = native.home / "CACProbeBridge.exe"
                    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
                    compiled = subprocess.run([str(compiler), "/nologo", "/target:exe", "/out:" + str(bridge),
                        str(Path(__file__).with_name("StdioBridge.cs"))], capture_output=True,
                        text=True, timeout=25, creationflags=subprocess.CREATE_NO_WINDOW)
                    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
                    profile = native.home / "vscode-profile"
                    settings = profile / "User/settings.json"
                    settings.parent.mkdir(parents=True)
                    settings.write_text(json.dumps({"chatgpt.cliExecutable": str(bridge),
                        "chatgpt.runCodexInWindowsSubsystemForLinux": False,
                        "telemetry.telemetryLevel": "off", "update.mode": "none",
                        "extensions.autoUpdate": False, "extensions.autoCheckUpdates": False,
                        "workbench.startupEditor": "none", "window.title": "CAC isolated composer probe"}), encoding="utf-8")
                    env.update(CAC_OWNER_WS_URL=relay.url, CAC_BRIDGE_NATIVE_CODEX=str(extension_binary),
                        CAC_BRIDGE_TIMEOUT_SECONDS="480")
                    command = [str(args.code.resolve(strict=True)), f"--user-data-dir={profile}",
                        f"--extensions-dir={native.home / 'extensions'}", f"--extensionDevelopmentPath={extension}",
                        "--disable-extensions", "--disable-workspace-trust", "--skip-welcome", "--skip-release-notes",
                        str(native.home)]
                # Keep reconnects pinned through the real environment, not a mocked connect().
                os.environ.clear()
                os.environ.update(native.env)
                supervisor = Supervisor(Config(codex_executable=binary, queue_holding=True,
                    dispatch_spacing_seconds=0), native.data / "state.json")
                native.supervisors.append(supervisor)
                supervisor.connect()
                assert supervisor.client.socket_path == native.socket
                supervisor.client.request("project/create", {"idempotencyKey": "cac-composer-project",
                    "name": "CAC composer fixture", "roots": [{"path": str(native.home)}]})
                output = native.stack.enter_context((native.home / "gui.stdout").open("wb"))
                process = subprocess.Popen(command, env=env, cwd=native.home,
                    stdin=subprocess.DEVNULL, stdout=output, stderr=output)
                try:
                    report("waiting_for_composer", client="Desktop" if args.desktop else "VS Code",
                        fixture=str(native.home), pid=process.pid,
                        instructions="Send CAC_INITIAL_SYNTHETIC, then queue CAC_FOLLOW_UP_0 and CAC_FOLLOW_UP_1")
                    deadline = time.monotonic() + 480
                    phase = "waiting_for_composer"
                    captured = False
                    identity = None
                    denied_at = None
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise AssertionError("Isolated GUI process exited before composer acceptance")
                        result = supervisor.run_cycle()
                        journal = supervisor.holding.journal.read() or {}
                        records = journal.get("records", [])
                        if phase == "waiting_for_composer" and native.service.entered.is_set():
                            phase = "initial_response_gated"
                            report(phase, holding=result.holding)
                        if not captured and len(records) == 2 and all(r["phase"] == "held" for r in records):
                            captured = True
                            identity = records[0]["threadId"]
                            assert all(r["threadId"] == identity for r in records)
                            assert not supervisor.client.queue_items(identity)
                            assert b"CAC_FOLLOW_UP" not in supervisor.holding.journal.path.read_bytes()
                            report("two_composer_inputs_held", holding=result.holding)
                            native.service.release.set()
                        if captured and result.pending and denied_at is None:
                            denied_at = time.monotonic()
                            report("quota_failure_recorded", pending=result.pending, allowed=result.ordinary_usage_allowed)
                            assert result.ordinary_usage_allowed is False
                            assert "Continue" not in native.service.user_messages
                        if denied_at is not None and time.monotonic() - denied_at >= 2:
                            native.service.allowed = True
                            native.service.fail_inference = False
                        if captured and not records:
                            # Normalize only test markers, not stored input or delivery identity.
                            assert [text.strip() for text in native.service.user_messages] == [
                                "CAC_INITIAL_SYNTHETIC", "Continue", "CAC_FOLLOW_UP_0", "CAC_FOLLOW_UP_1"
                            ], native.service.user_messages
                            assert "CAC_FOLLOW_UP" not in native.telemetry_file.read_text(encoding="utf-8")
                            assert hashes == [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
                            report("passed", orderedSyntheticInputs=native.service.user_messages,
                                holding=result.holding, originalClientFilesUnchanged=True,
                                relayErrors=relay.errors,
                                connections=[{"identity": s.identity, "methods": dict(s.methods)} for s in relay.summaries])
                            return
                        time.sleep(0.15)
                    report("timeout", holding=supervisor.holding.report(),
                        inferenceRequests=native.service.inference_count,
                        syntheticInputs=native.service.user_messages,
                        connections=[{"identity": s.identity, "methods": dict(s.methods)} for s in relay.summaries])
                    raise TimeoutError("GUI composer acceptance exceeded 480 seconds")
                except BaseException as exc:
                    report("failed", errorType=type(exc).__name__, reason=str(exc),
                        holding=supervisor.holding.report() if supervisor.holding else None,
                        inferenceRequests=native.service.inference_count,
                        syntheticInputs=native.service.user_messages,
                        connections=[{"identity": s.identity, "methods": dict(s.methods)} for s in relay.summaries])
                    raise
                finally:
                    native.service.release.set()
                    if process.poll() is None:
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                    process.wait(timeout=5)
    finally:
        os.environ.clear()
        os.environ.update(previous_env)
        native_support.Service = previous_service


if __name__ == "__main__":
    main()
