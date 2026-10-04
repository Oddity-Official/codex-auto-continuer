"""Extract lifecycle evidence without exporting user messages or chat identities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--after", required=True)
    parser.add_argument("--before", required=True)
    args = parser.parse_args()
    with args.path.open(encoding="utf-8") as source:
        length = args.path.stat().st_size
        while source.tell() < length:
            line = source.readline()
            if not line.endswith("\n"):
                break
            item = json.loads(line)
            stamp, payload = item.get("timestamp", ""), item.get("payload", {})
            if not args.after <= stamp <= args.before:
                continue
            if item.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "user":
                text = "".join(part.get("text", "") for part in payload.get("content", []) if isinstance(part, dict))
                print(json.dumps({"timestamp": stamp, "event": "user_message", "messageLength": len(text),
                                  "isContinue": text.strip() == "Continue"}))
                continue
            if item.get("type") != "event_msg":
                continue
            kind = payload.get("type")
            if kind not in {"task_started", "task_complete", "turn_aborted", "error", "user_message"}:
                continue
            text = payload.get("message", "")
            if not isinstance(text, str):
                text = ""
            row = {"timestamp": stamp, "event": kind}
            if kind == "user_message":
                row.update(messageLength=len(text), isContinue=text.strip() == "Continue",
                           isQuestionReply=text.startswith("<send_user_message_question_reply>"))
            if kind == "error":
                row["isUsageLimit"] = "usage limit" in text.lower() or "usage_limit" in text.lower()
            if kind == "task_complete":
                error = payload.get("error") or {}
                row["isUsageLimit"] = error.get("codex_error_info") == "usage_limit_exceeded"
            print(json.dumps(row))


if __name__ == "__main__":
    main()
