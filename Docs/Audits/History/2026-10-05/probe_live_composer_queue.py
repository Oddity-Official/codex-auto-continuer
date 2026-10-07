"""Read-only queue visibility for one explicitly identified synthetic GUI chat.

No message, queue mutation, resume, cancellation or recovery RPC is sent.
Only new chats, or an explicitly named test chat, are inspected for the probe
marker. Bodies stay in RAM; private status files contain thread IDs. Public
output contains counts/provenance, not real chat identities.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from probe_desktop_connection import ROOT
from codex_auto_continuer.appserver import AppServerClient

MARKER = "CAC_DESKTOP_COMPOSER_PROBE_20261005"
FOLLOW_UPS = ("CAC_DESKTOP_FOLLOW_UP_0", "CAC_DESKTOP_FOLLOW_UP_1")


def texts(inputs):
    return [item.get("text", "") for item in inputs if item.get("type") == "text"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--title", help="Exact authoritative title of an existing synthetic probe chat")
    args = parser.parse_args()
    client = AppServerClient.connect(args.socket, 10)
    try:
        baseline = set() if args.title else {t["id"] for t in client.thread_list(limit=100)["data"]}
        print(json.dumps({"phase": "ready", "readOnly": True}), flush=True)
        deadline = time.monotonic() + 180
        identity = None
        captured = {}
        while time.monotonic() < deadline:
            if identity is None:
                for thread in client.thread_list(limit=20)["data"]:
                    if thread["id"] in baseline:
                        continue
                    if args.title and thread.get("name") != args.title:
                        continue
                    turns = client.full_turns(thread["id"])
                    if any(MARKER in text for turn in turns for item in turn.get("items", [])
                        if item.get("type") == "userMessage" for text in texts(item.get("content", []))):
                        identity = thread["id"]
                        provenance = {k: thread.get(k) for k in ("source", "originator")}
                        (ROOT / ".data/live-composer-status.json").write_text(json.dumps({
                            "phase": "identified", "threadId": identity, "queued": 0}), encoding="utf-8")
                        break
            if identity is not None:
                for queued in client.queue_items(identity):
                    # The actual composer retains a trailing newline in input.
                    # This normalization identifies only synthetic test markers;
                    # delivery identity is still the native client message ID.
                    text = "".join(texts(queued["input"])).strip()
                    if text in FOLLOW_UPS:
                        captured[text] = queued["clientUserMessageId"]
                (ROOT / ".data/live-composer-status.json").write_text(json.dumps({
                    "phase": "observing", "threadId": identity, "observedInputs": len(captured),
                    "queueCount": len(client.queue_items(identity)),
                    "latestStatus": (client.latest_turn(identity) or {}).get("status")}), encoding="utf-8")
                if len(captured) == 2:
                    turns = client.full_turns(identity)
                    counts = {text: sum(item.get("clientId") == message_id
                        for turn in turns for item in turn.get("items", []) if item.get("type") == "userMessage")
                        for text, message_id in captured.items()}
                    if all(count == 1 for count in counts.values()) and turns[-1]["status"] == "completed":
                        result = {"phase": "passed", "readOnlyObserver": True,
                            "actualComposerQueuedInputsVisible": 2,
                            "eachQueueClientIdConsumedExactlyOnce": True,
                            "remainingQueue": len(client.queue_items(identity)), **provenance}
                        (ROOT / ".data/live-composer-result.json").write_text(json.dumps(result | {"threadId": identity}), encoding="utf-8")
                        print(json.dumps(result), flush=True)
                        return
            time.sleep(0.08)
        raise TimeoutError(f"Live queue visibility exceeded 180 seconds; identifiedChat={identity is not None}, observedInputs={len(captured)}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
