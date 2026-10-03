"""Exercise unloaded queue CRUD and a detached turn on an owned native test thread."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))

from codex_auto_continuer.appserver import AppServerClient
from codex_auto_continuer.codex import daemon_version, find_codex


def main():
    path = daemon_version(find_codex(), 10).socket_path
    client = AppServerClient.connect(path, 5)
    thread_id = None
    def completed(expected_previous=None):
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if expected_previous is None:
                client.rate_limits()
                if not any(n.get("method") == "turn/completed" and n.get("params", {}).get("threadId") == thread_id
                           for n in client.notifications):
                    time.sleep(0.2)
                    continue
            turn = client.latest_turn(thread_id)
            if client.thread_read(thread_id)["status"]["type"] == "active":
                time.sleep(0.2)
                continue
            if turn and turn["id"] != expected_previous and turn["status"] in {"completed", "failed", "interrupted"}:
                if turn["status"] != "completed":
                    raise RuntimeError(f"Probe turn stopped: {turn['status']}, {(turn.get('error') or {}).get('codexErrorInfo')}, thread={client.thread_read(thread_id)['status']}")
                return turn["id"]
            time.sleep(0.2)
        raise TimeoutError("Probe turn did not complete in 35 seconds.")
    try:
        response = client.request("thread/start", {
            "cwd": str(ROOT / ".data"), "model": "gpt-6-luna",
            "approvalPolicy": "never", "sandbox": "read-only",
            "baseInstructions": "Reply with exactly CAC_NATIVE_OK. Do not use tools.",
        })
        thread_id = response["thread"]["id"]
        client.request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": "Reply CAC_NATIVE_OK."}]})
        previous = completed()
        client.request("thread/archive", {"threadId": thread_id})
        client.request("thread/unarchive", {"threadId": thread_id})
        deadline = time.monotonic() + 5
        while client.thread_read(thread_id)["status"]["type"] != "notLoaded":
            if time.monotonic() >= deadline:
                raise TimeoutError("Probe thread did not unload.")
            time.sleep(0.1)
        one = client.queue_add(thread_id, "Reply CAC_NATIVE_OK.", "cac-delete-own")["queuedSubmission"]["id"]
        two = client.queue_add(thread_id, "Reply CAC_NATIVE_OK.", "cac-delete-other")["queuedSubmission"]["id"]
        assert len(client.queue_items(thread_id)) == 2
        assert client.queue_delete(thread_id, one)
        assert [x["id"] for x in client.queue_items(thread_id)] == [two]
        assert client.queue_delete(thread_id, two)
        assert not client.queue_items(thread_id)
        client.resume_thread(thread_id)
        client.queue_add(thread_id, "Reply CAC_NATIVE_OK.", "cac-detached-queue")
        client.close()
        client = AppServerClient.connect(path, 5)
        completed(previous)
        assert not client.queue_items(thread_id)
        print(json.dumps({"unloadedQueueCrud": "passed", "unrelatedItemPreserved": True,
                          "unloadedResume": "passed", "detachedQueuedTurn": "completed"}, indent=2))
    finally:
        if thread_id:
            for item in client.queue_items(thread_id):
                if item.get("clientUserMessageId", "").startswith("cac-"):
                    client.queue_delete(thread_id, item["id"])
            client.request("thread/archive", {"threadId": thread_id})
        client.close()


if __name__ == "__main__":
    main()
