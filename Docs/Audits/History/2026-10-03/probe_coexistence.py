"""Test two native app-server owners using one disposable, two-token-answer thread."""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))

from codex_auto_continuer.appserver import AppServerClient, RpcError
from codex_auto_continuer.codex import daemon_version, find_codex


def main():
    binary = find_codex()
    process = subprocess.Popen(
        [binary, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    incoming = queue.Queue()
    def read():
        for line in process.stdout:
            incoming.put(json.loads(line))
        incoming.put(None)
    threading.Thread(target=read, daemon=True).start()
    request_id = 0
    def request(method, params):
        nonlocal request_id
        request_id += 1
        process.stdin.write(json.dumps({"id": request_id, "method": method, "params": params}) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + 12
        while True:
            message = incoming.get(timeout=max(0.01, deadline - time.monotonic()))
            if message is None:
                raise RuntimeError("Probe app-server exited.")
            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    raise RpcError(method, message["error"])
                return message["result"]
    def wait_completed():
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            message = incoming.get(timeout=max(0.01, deadline - time.monotonic()))
            if message and message.get("method") == "turn/completed":
                turn = message["params"]["turn"]
                return {"status": turn["status"], "errorInfo": (turn.get("error") or {}).get("codexErrorInfo")}
        raise TimeoutError("Probe turn did not complete.")
    client = None
    thread_id = None
    out = {}
    try:
        request("initialize", {
            "clientInfo": {"name": "cac_coexistence_probe", "version": "0.1.0"},
            "capabilities": {"experimentalApi": True},
        })
        process.stdin.write('{"method":"initialized"}\n')
        process.stdin.flush()
        models = request("model/list", {"includeHidden": False})["data"]
        model = next((m["model"] for m in models if m["model"] == "gpt-6-luna"), None)
        if model is None:
            raise RuntimeError("The bounded probe requires the available gpt-6-luna model.")
        response = request("thread/start", {
            "cwd": str(ROOT / ".data"), "ephemeral": False, "model": model,
            "approvalPolicy": "never", "sandbox": "read-only",
            "baseInstructions": "Reply with exactly CAC_NATIVE_OK. Do not use tools.",
        })
        thread_id = response["thread"]["id"]
        out["ownerStatus"] = response["thread"]["status"]
        request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": "Reply CAC_NATIVE_OK."}]})
        out["initialTurn"] = wait_completed()
        client = AppServerClient.connect(daemon_version(binary, 10).socket_path, 5)
        try:
            out["daemonReadStatus"] = client.thread_read(thread_id)["status"]
            out["daemonResumeStatus"] = client.resume_thread(thread_id)["thread"]["status"]
        except RpcError as exc:
            out["daemonError"] = exc.error
        if out["initialTurn"]["status"] == "completed":
            queued = client.queue_add(thread_id, "Reply CAC_NATIVE_OK.", "cac-coexistence-probe")
            out["queuedIdReturned"] = bool(queued.get("queuedSubmission", {}).get("id"))
            out["queueTurnOnOriginalOwner"] = wait_completed()
        print(json.dumps(out, indent=2))
    finally:
        if client:
            client.close()
        if thread_id:
            request("thread/archive", {"threadId": thread_id})
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=5, check=False)
        else:
            process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
