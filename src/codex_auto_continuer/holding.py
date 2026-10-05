"""Optional owner-side interception. Peer storage access never authorizes replay."""
from __future__ import annotations

import hashlib
import math
import copy
import time
import threading
from pathlib import Path

from .appserver import AppServerClient
from .errors import ConfigurationError, ProtocolError
from .holding_journal import Journal, account_binding
from .telemetry import emit, failure


def status_type(thread):
    status = thread.get("status")
    if not isinstance(status, dict) or status.get("type") not in {"active", "idle", "notLoaded", "systemError"}:
        raise ProtocolError("Queue holding cannot interpret the owner thread status.")
    return status["type"]


def metadata(turns):
    matches = {}
    for turn in turns:
        for item in turn["items"]:
            if item.get("type") == "userMessage":
                if "clientId" not in item:
                    raise ProtocolError("Full history does not expose user-message client identity. Holding is blocked.")
                identity = item["clientId"]
                if identity is not None and not isinstance(identity, str):
                    raise ProtocolError("Invalid full-history client identity.")
                if identity:
                    matches.setdefault(identity, []).append(turn)
    return matches


def terminal(turn):
    return (turn is not None and turn.get("status") in {"completed", "failed", "interrupted"}
        and type(turn.get("completedAt")) in (int, float) and math.isfinite(turn["completedAt"]))


class Watcher:
    def __init__(self, manager, thread_id, socket_path, user_agent, timeout):
        self.manager, self.thread_id = manager, thread_id
        self.socket_path, self.user_agent, self.timeout = socket_path, user_agent, timeout
        self.home = manager.home
        self.client = None
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self.run, name="CAC-queue-owner", daemon=True)

    def capture(self, client):
        if self.stop.is_set() or self.home != self.manager.home or not self.manager.granted():
            return
        thread = client.thread_read(self.thread_id)
        if thread.get("id") != self.thread_id or status_type(thread) != "active":
            return
        turn = client.latest_turn(self.thread_id)
        if not turn or turn.get("status") != "inProgress":
            return
        binding = account_binding(self.home)
        for queued in client.queue_items(self.thread_id):
            with self.manager.journal.transaction(binding) as raw:
                protected = raw["threads"].get(self.thread_id, {}).get("recoveryIds", [])
                if queued.get("clientUserMessageId") in protected:
                    continue
                existing = next((r for r in raw["records"] if r["id"] == queued.get("id")), None)
                if existing and existing["phase"] != "saved":
                    continue
                collision = next((r for r in raw["records"] if r["threadId"] == self.thread_id
                    and r["clientUserMessageId"] == queued.get("clientUserMessageId") and r is not existing), None)
                if collision:
                    if collision["phase"] in {"release_requested", "submitted", "uncertain"}:
                        continue
                    raise ProtocolError("A queued client identity collides with a held input. Review is required.")
                if existing is None:
                    record = {"id": queued.get("id"), "threadId": self.thread_id,
                        "clientUserMessageId": queued.get("clientUserMessageId"), "anchorTurnId": turn["id"],
                        "input": queued.get("input"), "phase": "saved", "releasedQueueId": None}
                    if not any(r["threadId"] == self.thread_id for r in raw["records"]):
                        raw["threads"][self.thread_id] = {"authorizedTurnId": turn["id"], "recoveryIds": [], "paused": ""}
                    raw["records"].append(record)
                    self.manager.journal.save(raw)
                else:
                    record = existing
                # Only this exact owner's lock can serialize deletion against selection.
                # Recheck identity and grant after durable persistence, before mutation.
                if self.stop.is_set() or self.home != self.manager.home or not self.manager.granted() or account_binding(self.home) != binding:
                    return
                deleted = client.queue_delete(self.thread_id, record["id"])
                record["phase"] = "held" if deleted else "uncertain"
                self.manager.journal.save(raw)
                emit("holding.captured" if deleted else "holding.removal_unconfirmed",
                    threadId=self.thread_id, queuedSubmissionId=record["id"],
                    clientUserMessageId=record["clientUserMessageId"])
                self.manager.changed.set()

    def run(self):
        client = None
        try:
            client = AppServerClient.connect(self.socket_path, self.timeout)
            self.client = client
            if self.stop.is_set():
                return
            if client.user_agent != self.user_agent:
                raise ProtocolError("Owner identity changed while establishing queue holding.")
            own = client.thread_read(self.thread_id)
            if own.get("id") != self.thread_id or status_type(own) != "active":
                return
            metadata(client.full_turns(self.thread_id))
            resumed = client.resume_thread(self.thread_id)
            if resumed.get("thread", {}).get("id") != self.thread_id:
                raise ProtocolError("Queue holding did not subscribe to the exact owner thread.")
            self.capture(client)
            self.ready.set()
            while not self.stop.is_set() and self.manager.granted():
                note = client.next_notification(0.1)
                if note is None:
                    continue
                if "id" in note:
                    # An observer must not become an unattended approval/input client.
                    raise ProtocolError("Owner requested approval/input from the holding observer. "
                        "The observer disconnected without answering; use the original client.")
                params = note.get("params") or {}
                if params.get("threadId") != self.thread_id:
                    continue
                if note["method"] == "thread/queue/changed":
                    self.capture(client)
                if note["method"] == "turn/completed":
                    self.manager.changed.set()
                    return
        except Exception as exc:
            if not self.stop.is_set():
                self.manager.issue(self.thread_id, "Owner observation failed. Held inputs are preserved; "
                    "inspect Codex and local telemetry, then review held requests.")
                failure("holding.observer_failed", exc, threadId=self.thread_id)
        finally:
            if client is not None:
                client.close()
            self.ready.set()
            self.manager.changed.set()

    def cancel(self):
        self.stop.set()
        if self.client is not None:
            self.client._ws.abort()


class Holding:
    def __init__(self, directory: Path):
        self.journal = Journal(directory / "held-inputs.dpapi")
        self.changed = threading.Event()
        self.watchers = {}
        self.issues = {}
        self.home = None
        self.socket_path = None
        self.enabled = False
        self.allowed = False
        self.binary = None
        self.binary_stamp = None
        self.global_problem = ""
        self.unsupported = 0
        self.covered = 0

    def granted(self):
        if not self.enabled or not self.allowed or self.global_problem:
            return False
        if self.binary is None:
            return True  # Isolated native harnesses pin their own executable/socket.
        try:
            info = self.binary.stat()
            return (info.st_size, info.st_mtime_ns, info.st_ctime_ns) == self.binary_stamp
        except OSError:
            return False

    def issue(self, thread_id, message):
        self.issues[thread_id] = message
        self.changed.set()

    def update(self, client, threads, *, enabled, allowed, binary, timeout):
        self.changed.clear()
        self.enabled, self.allowed = enabled, allowed
        self.binary = Path(binary) if binary else None
        if self.binary:
            info = self.binary.stat()
            self.binary_stamp = (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        self.global_problem = ""
        self.covered = self.unsupported = 0
        try:
            raw = self.journal.read()
            if not enabled and not (raw and raw["records"]):
                self.stop_watchers()
                return
            socket_path = getattr(client, "socket_path", None)
            if socket_path is None or socket_path.parent.name != "app-server-control":
                raise ConfigurationError("Queue holding cannot verify the native owner's control socket/home.")
            if self.socket_path is not None and socket_path != self.socket_path:
                self.allowed = False
                self.stop_watchers()
                self.allowed = allowed
            self.socket_path = socket_path
            self.home = socket_path.parent.parent
            binding = account_binding(self.home)
            with self.journal.transaction(binding):
                pass
            if not self.granted():
                self.stop_watchers()
                return
            for identity, worker in list(self.watchers.items()):
                if identity not in {t["id"] for t in threads}:
                    worker.cancel()
                    worker.thread.join(3 * timeout + 2)
                if not worker.thread.is_alive():
                    worker.thread.join()
                    del self.watchers[identity]
            for item in threads:
                kind = status_type(item)
                identity = item["id"]
                if kind == "notLoaded":
                    self.unsupported += 1
                    continue
                self.covered += 1
                if kind == "active" and identity not in self.watchers and identity not in self.issues:
                    if len(self.watchers) >= 16:
                        self.unsupported += 1
                        continue
                    worker = Watcher(self, identity, socket_path, client.user_agent, timeout)
                    self.watchers[identity] = worker
                    worker.thread.start()
        except Exception as exc:
            self.global_problem = ("Queue holding is blocked. Preserve held-inputs.dpapi; check the original "
                "Windows/Codex account, owner connection and local telemetry.")
            failure("holding.blocked", exc)
            self.allowed = False
            self.stop_watchers()

    def stop_watchers(self):
        for worker in self.watchers.values():
            worker.cancel()
        deadline = time.monotonic() + 3 * max((w.timeout for w in self.watchers.values()), default=0) + 2
        for worker in self.watchers.values():
            worker.thread.join(max(0, deadline - time.monotonic()))
            if worker.thread.is_alive():
                raise ProtocolError("A queue holding observer did not close within its RPC deadline.")
        self.watchers.clear()

    def close(self):
        self.enabled = False
        self.stop_watchers()
        self.changed.clear()

    def blocks_dispatch(self):
        if not self.global_problem:
            return False
        try:
            raw = self.journal.read()
            return bool(raw and raw["records"])
        except ConfigurationError:
            return True

    def protect_recovery(self, thread_id, client_id):
        if not self.journal.path.exists():
            return
        with self.journal.transaction() as raw:
            info = raw["threads"].get(thread_id)
            if info is not None and client_id not in info["recoveryIds"]:
                info["recoveryIds"] = [*info["recoveryIds"][-63:], client_id]
                self.journal.save(raw)

    def reconcile(self, client, *, permission, in_scope, guard):
        if self.global_problem or not self.journal.path.exists():
            return set()
        blocked = set()
        candidates = []
        snapshot = self.journal.read()
        if snapshot is None or not snapshot["records"]:
            return set()
        # Slow history/RPC reads must not hold the journal lock: capture has a
        # short opportunity before the owner selects its next queued request.
        observations = {}
        for thread_id in snapshot["threads"]:
            thread = client.thread_read(thread_id)
            readable = thread.get("id") == thread_id and not thread.get("archived") and status_type(thread) != "notLoaded"
            observations[thread_id] = (thread, client.full_turns(thread_id) if readable else [],
                client.queue_items(thread_id) if readable else [])
        with self.journal.transaction(account_binding(self.home)) as raw:
            before = copy.deepcopy(raw)
            for thread_id in list(raw["threads"]):
                if thread_id not in observations:
                    continue  # Captured during our reads; reconcile next cycle.
                records = [r for r in raw["records"] if r["threadId"] == thread_id]
                if not records:
                    del raw["threads"][thread_id]
                    continue
                info = raw["threads"][thread_id]
                thread, turns, queue = observations[thread_id]
                if thread.get("id") != thread_id or thread.get("archived") or status_type(thread) == "notLoaded":
                    blocked.add(thread_id)
                    self.issue(thread_id, "Held requests have no controllable owner. Reopen the original owner; do not replay through a peer.")
                    continue
                matches = metadata(turns)
                latest = turns[-1] if turns else None
                active = status_type(thread) == "active"
                for record in records[:]:
                    found = matches.get(record["clientUserMessageId"], [])
                    if len(found) > 1:
                        info["paused"] = "Duplicate client identity in history. Review the original chat."
                        continue
                    if found and not active and terminal(found[0]):
                        if record["phase"] in {"submitted", "release_requested", "uncertain"}:
                            info["authorizedTurnId"] = found[0]["id"]
                        raw["records"].remove(record)
                        emit("holding.consumed", threadId=thread_id, queuedSubmissionId=record["id"],
                            clientUserMessageId=record["clientUserMessageId"])
                records = [r for r in raw["records"] if r["threadId"] == thread_id]
                if not records:
                    self.issues.pop(thread_id, None)
                    del raw["threads"][thread_id]
                    continue
                for record in records:
                    if record["phase"] in {"release_requested", "uncertain"}:
                        echoed = [q for q in queue if q.get("clientUserMessageId") == record["clientUserMessageId"]]
                        if len(echoed) == 1 and record["phase"] == "release_requested":
                            record["phase"] = "submitted"
                            record["releasedQueueId"] = echoed[0]["id"]
                ambiguous = any(r["phase"] in {"saved", "uncertain", "release_requested"} for r in records)
                if ambiguous:
                    blocked.add(thread_id)
                    self.issue(thread_id, "A held input has unconfirmed removal/delivery. No automatic replay. Inspect the chat and held requests.")
                if active or ambiguous or any(r["phase"] == "submitted" for r in records):
                    continue
                self.issues.pop(thread_id, None)
                if latest and latest["id"] != info["authorizedTurnId"]:
                    current_ids = [key for key, values in matches.items() if any(t["id"] == latest["id"] for t in values)]
                    if any(key in info["recoveryIds"] for key in current_ids) and terminal(latest):
                        info["authorizedTurnId"] = latest["id"]
                    elif info["paused"] == "review_approved" and terminal(latest):
                        info["authorizedTurnId"] = latest["id"]
                        info["paused"] = ""
                        self.issues.pop(thread_id, None)
                    elif (latest.get("status") == "failed" and isinstance(latest.get("error"), dict)
                        and latest["error"].get("codexErrorInfo") == "usageLimitExceeded"):
                        continue  # Canonical recovery sends the unchanged prompt first.
                    else:
                        info["paused"] = "Newer/manual progress. Review held requests, then approve resuming them."
                if info["paused"] == "review_approved":
                    info["paused"] = ""
                    self.issues.pop(thread_id, None)
                if info["paused"]:
                    blocked.add(thread_id)
                    self.issue(thread_id, info["paused"])
                    continue
                if terminal(latest) and latest["status"] != "completed" and not (
                    latest["status"] == "failed" and isinstance(latest.get("error"), dict)
                    and latest["error"].get("codexErrorInfo") == "usageLimitExceeded"):
                    self.issue(thread_id, "Held requests need a successful completed turn before release. "
                        "The original turn failed/interrupted for a non-quota reason; inspect Codex before continuing manually.")
                    blocked.add(thread_id)
                    continue
                if not self.granted() or not permission or not in_scope(thread) or not terminal(latest) or latest["status"] != "completed":
                    continue
                candidates.append((thread_id, latest["id"], records[0]["id"]))
            if raw != before:
                self.journal.save(raw)
        for thread_id, turn_id, record_id in candidates:
            if not self._release(client, thread_id, turn_id, record_id, guard):
                blocked.add(thread_id)
        return blocked

    def _release(self, client, thread_id, turn_id, record_id, guard):
        guard()
        fresh = client.latest_turn(thread_id)
        if (fresh is None or fresh.get("id") != turn_id or status_type(client.thread_read(thread_id)) != "idle"
            or client.rate_limits().get("ordinaryUsageAllowed") is not True or client.queue_items(thread_id)):
            return True
        binding = account_binding(self.home)
        with self.journal.transaction(binding) as raw:
            records = [r for r in raw["records"] if r["threadId"] == thread_id]
            info = raw["threads"].get(thread_id)
            if (not self.granted() or not info or info["paused"] or info["authorizedTurnId"] != turn_id
                or not records or records[0]["id"] != record_id or any(r["phase"] != "held" for r in records)):
                return True
            record = records[0]
            record["phase"] = "release_requested"
            self.journal.save(raw)
        try:
            if not self.granted() or account_binding(self.home) != binding:
                raise ConfigurationError("Account or compatibility changed before release. Review the saved intent; no retry.")
            result = client.queue_add_input(thread_id, record["input"], record["clientUserMessageId"])
            echoed = result.get("queuedSubmission", {})
            if (echoed.get("clientUserMessageId") != record["clientUserMessageId"] or
                not isinstance(echoed.get("id"), str) or not echoed["id"]):
                raise ProtocolError("Held input submission did not echo its exact identity.")
        except Exception as exc:
            self.issue(thread_id, "Held input delivery is unconfirmed. No automatic retry; inspect the original chat.")
            failure("holding.release_unconfirmed", exc, threadId=thread_id)
            return False
        with self.journal.transaction(binding) as raw:
            current = next((r for r in raw["records"] if r["id"] == record_id), None)
            if current is None or current["phase"] != "release_requested":
                raise ConfigurationError("Held input intent changed during delivery. Review the original chat; no automatic retry.")
            current["phase"] = "submitted"
            current["releasedQueueId"] = echoed["id"]
            self.journal.save(raw)
        emit("holding.released", threadId=thread_id, queuedSubmissionId=echoed["id"],
            clientUserMessageId=record["clientUserMessageId"])
        return True

    def report(self):
        try:
            raw = self.journal.read()
        except ConfigurationError:
            raw = None
            self.global_problem = "The encrypted holding journal is unreadable. Preserve it and use the original Windows/Codex account."
        records = raw["records"] if raw else []
        warnings = []
        if self.global_problem:
            warnings.append({"key": "holding-journal", "code": "holding_blocked", "message": self.global_problem})
        if self.enabled:
            warnings.append({"key": "holding-coverage", "code": "holding_unsupported", "message":
                "Queue holding covers at most 16 established active owner subscriptions, not separately owned/stdin-stdout or idle input. Standard quota recovery continues; "
                "only observed active chats on the connected owner can have queued requests held."})
        for identity, message in list(self.issues.items()):
            warnings.append({"key": hashlib.sha256(identity.encode()).hexdigest(), "code": "holding_review", "message": message})
        return {"enabled": self.enabled, "held": len(records), "observedActive": sum(w.thread.is_alive() for w in self.watchers.values()),
            "unsupported": self.unsupported, "needsAttention": bool(self.global_problem or self.issues), "warnings": warnings}
