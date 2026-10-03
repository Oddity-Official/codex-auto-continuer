"""Bounded real Windows CLI ownership/queue probe on one disposable read-only thread."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import re
from pathlib import Path

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from winpty import PtyProcess
from codex_auto_continuer.appserver import AppServerClient, RpcError
from codex_auto_continuer.codex import daemon_version, find_codex


def main():
    binary = find_codex()
    client = AppServerClient.connect(daemon_version(binary, 10).socket_path, 5)
    process = None
    thread_id = None
    screen = []
    temporary = tempfile.TemporaryDirectory(prefix="cli-owned-", dir=ROOT / ".data")
    try:
        directory = temporary.name
        process = PtyProcess.spawn([binary, "--no-alt-screen", "--no-daemon", "-C", directory, "-m", "gpt-6-luna",
                                    "--sandbox", "read-only", "--ask-for-approval", "never",
                                    "-c", 'model_reasoning_effort="low"',
                                    "-c", 'base_instructions="Reply exactly CAC_CLI_OK. Do not use tools."',
                                    "Reply CAC_CLI_OK. Do not use tools."], dimensions=(30, 120), env=os.environ | {"TERM": "xterm-256color"})
        def drain():
            try:
                while process.isalive():
                    text = process.read(4096)
                    screen.append(text)
                    if "\x1b[6n" in text:
                        process.write("\x1b[1;1R")
            except (EOFError, OSError):
                pass
        threading.Thread(target=drain, daemon=True).start()
        deadline = time.monotonic() + 35
        initial = None
        while time.monotonic() < deadline:
            page = client.request("thread/list", {"cwd": directory, "limit": 10, "sourceKinds": ["cli"], "archived": False})
            threads = page.get("data", [])
            if threads:
                if len(threads) != 1:
                    raise RuntimeError("Probe could not identify exactly one owned CLI thread.")
                thread_id = threads[0]["id"]
                initial = client.latest_turn(thread_id)
                if initial and initial.get("status") == "completed":
                    break
                if initial and initial.get("status") == "failed":
                    raise RuntimeError("Owned CLI initial turn failed; no queue submission attempted.")
            time.sleep(0.5)
        else:
            diagnostic = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", "".join(screen)).lower()
            print(json.dumps({"terminalDumbWarning": "term is set to" in diagnostic,
                              "trustPrompt": "trust" in diagnostic, "terminalBytes": len(diagnostic)}))
            raise TimeoutError("Owned CLI initial turn did not complete in 35s.")
        thread = client.thread_read(thread_id)
        owner_error = False
        try:
            client.resume_thread(thread_id)
        except RpcError as exc:
            if not exc.is_active_writer(thread_id):
                raise
            owner_error = True
        if not owner_error:
            raise RuntimeError("The CLI was not the verified active writer.")
        queued = client.queue_add(thread_id, "Reply CAC_CLI_QUEUE_OK. Do not use tools.", str(uuid.uuid4()))
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            latest = client.latest_turn(thread_id)
            if latest and latest["id"] != initial["id"] and latest.get("status") in {"completed", "failed"}:
                if latest["status"] != "completed":
                    raise RuntimeError("Owned CLI queued turn failed.")
                print(json.dumps({"source": thread["source"], "originator": thread.get("originator"),
                                  "initialTurn": "completed", "verifiedSeparateWriter": True,
                                  "queuedIdReturned": bool(queued["queuedSubmission"]["id"]),
                                  "queuedTurn": "completed"}, indent=2))
                break
            time.sleep(0.5)
        else:
            raise TimeoutError("CLI-owned queued turn did not complete in 35s.")
    finally:
        if process is not None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                           timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            process.close(force=True)
        if thread_id is not None:
            client.request("thread/archive", {"threadId": thread_id})
        client.close()
        temporary.cleanup()


if __name__ == "__main__":
    main()
