"""Actual CLI Tab-queued input versus CAC's unchanged production connection.

Only the service is synthetic. Initial and queued inputs use normal terminal
input, never write RPC injection. After measuring CAC's failed recovery, one
explicit native-queue diagnostic distinguishes server refusal from CAC policy.
All state and credentials are disposable; production connect is unchanged.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "integration")]
import native_support
from test_holding import GatedService
from codex_auto_continuer.codex import find_codex, codex_version
from codex_auto_continuer.config import Config
from codex_auto_continuer.supervisor import Supervisor
from winpty import PtyProcess


def wait(predicate, seconds, label):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise TimeoutError(label)


def main():
    binary = find_codex()
    version = codex_version(binary, 10)
    original_service = native_support.Service
    native_support.Service = GatedService
    process = None
    previous_env = os.environ.copy()
    screen = []
    try:
        with native_support.NativeFixture(ROOT, binary, managed=True) as native:
            native.service.allow_rejected_external = True
            config = native.home / "config.toml"
            with config.open("a", encoding="utf-8") as file:
                file.write(f"\n[projects.'{native.home}']\ntrust_level = 'trusted'\n")
            # Production connect() invokes Codex lifecycle commands; use the same
            # isolated environment as the real TUI, not a replacement connection.
            os.environ.clear()
            os.environ.update(native.env)
            supervisor = Supervisor(Config(codex_executable=binary, queue_holding=True,
                dispatch_spacing_seconds=0), native.data / "state.json")
            native.supervisors.append(supervisor)
            supervisor.connect()
            peer = supervisor.client
            assert peer.socket_path == native.socket
            process = PtyProcess.spawn([binary, "--no-alt-screen", "-C", str(native.home),
                "--sandbox", "read-only", "--ask-for-approval", "never",
                "CAC_INITIAL_SYNTHETIC. Do not use tools."], env=native.env | {"TERM": "xterm-256color"},
                dimensions=(30, 110))

            def drain():
                try:
                    while process.isalive():
                        text = process.read(4096)
                        screen.append(text)
                        if "\x1b[6n" in text:
                            process.write("\x1b[1;1R")
                except (EOFError, OSError):
                    pass
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                wait(native.service.entered.is_set, 10, "CLI initial inference did not reach loopback service")
                threads = wait(lambda: peer.request("thread/list", {"cwd": str(native.home),
                    "sourceKinds": [], "limit": 10})["data"], 3, "CLI thread was not indexed")
                assert len(threads) == 1
                identity = threads[0]["id"]
                supervisor.run_cycle()
                watcher = supervisor.holding.watchers[identity]
                assert watcher.ready.wait(3) and not supervisor.holding.issues
                # Tab is the upstream CLI's actual queue gesture; Enter steers.
                process.write("CAC_QUEUED_SYNTHETIC")
                time.sleep(0.15)
                process.write("\t")
                time.sleep(0.5)
                queued_on_server = len(peer.queue_items(identity))
                captured = len((supervisor.holding.journal.read() or {}).get("records", []))
                terminal = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", "".join(screen))
                preview_seen = "CAC_QUEUED_SYNTHETIC" in terminal
                print(json.dumps({"phase": "before-quota", "serverQueuedInputs": queued_on_server,
                    "capturedInputs": captured, "terminalInputVisible": preview_seen,
                    "threadSource": threads[0]["source"], "threadOriginator": threads[0].get("originator")}))
                native.service.release.set()
                wait(lambda: "CAC_QUEUED_SYNTHETIC" in native.service.user_messages, 8,
                    "TUI did not drain its local queued input while quota remained denied")
                wait(lambda: (turn := peer.latest_turn(identity)) and turn["status"] == "failed", 8,
                    "Expected synthetic quota failure")
                assert peer.latest_turn(identity)["error"]["codexErrorInfo"] == "usageLimitExceeded"
                supervisor.run_cycle()
                pending = len(supervisor.state.obligations)
                native.service.allowed = True
                native.service.fail_inference = False
                result = supervisor.run_cycle()
                assert queued_on_server == captured == result.dispatched == 0
                assert pending == 1 and preview_seen
                assert peer.thread_read(identity)["status"]["type"] == "systemError"
                assert "Continue" not in native.service.user_messages
                assert any(event.get("event") == "dispatch.deferred" and event.get("fields", {}).get("reason") == "runtime_system_error"
                    for event in native.events())
                # Explicit counterfactual, not a production recovery pass. The
                # original TUI remains the real client on the same native owner.
                before = peer.latest_turn(identity)["id"]
                peer.queue_add(identity, "Continue", "cli-system-error-diagnostic")
                wait(lambda: "Continue" in native.service.user_messages, 8, "Native diagnostic queue was not consumed")
                wait(lambda: (turn := peer.latest_turn(identity)) and turn["id"] != before
                    and turn["status"] == "completed", 8, "Native diagnostic Continue did not complete")
                print(json.dumps({"cliVersion": version, "productionConnectUnmodified": True,
                    "threadSource": threads[0]["source"], "threadOriginator": threads[0].get("originator"),
                    "sameOwnerWatcherReady": True, "composerInputViaConPTYTab": True,
                    "terminalInputVisible": preview_seen, "serverQueuedInputsBeforeFailure": queued_on_server,
                    "capturedInputs": captured, "quotaObligations": pending, "continuesDispatched": result.dispatched,
                    "localQueueDrainedBeforeUsageReturned": True,
                    "latestQuotaError": "usageLimitExceeded", "statusBeforeDiagnostic": "systemError",
                    "CACRecoveryAcceptance": "failed: runtime_system_error deferral",
                    "explicitNativeQueueDiagnostic": "Continue accepted and completed; not a CAC recovery pass",
                    "conclusion": "CLI composer queue is client-local; owner connection alone cannot hold it. CAC blocks this recoverable native quota state."}, indent=2))
            except BaseException:
                terminal = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", "".join(screen)).lower()
                print(json.dumps({"terminalBytes": len(terminal), "trustPrompt": "trust" in terminal,
                    "inferenceRequests": native.service.inference_count, "fixtureErrors": native.service.errors,
                    "queuedPromptReachedService": "CAC_QUEUED_SYNTHETIC" in native.service.user_messages,
                    "latestFailureKind": (peer.latest_turn(identity).get("error") or {}).get("codexErrorInfo")
                        if 'identity' in locals() else None,
                    "visibleThreads": [{"source": t["source"], "originator": t.get("originator"),
                        "status": t.get("status")} for t in peer.thread_list()["data"]]}))
                raise
            finally:
                native.service.release.set()
                if process.isalive():
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                process.close(force=True)
                reader.join(timeout=3)
    finally:
        os.environ.clear()
        os.environ.update(previous_env)
        native_support.Service = original_service


if __name__ == "__main__":
    main()
