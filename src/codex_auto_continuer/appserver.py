from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any

from .errors import ProtocolError
from .ws_unix import UnixWebSocket
from . import __version__
from .telemetry import emit, failure, rpc_completed, rpc_request_fields, notification_summary


class RpcError(ProtocolError):
    def __init__(self, method: str, error: dict[str, Any]):
        self.method = method
        self.error = error
        code = error.get("code")
        code = code if type(code) is int else "unknown"
        super().__init__(f"Codex RPC {method} failed (code {code}). Inspect Codex's own logs for details; server error bodies are not logged here.")

    def is_unavailable_quota_read(self) -> bool:
        # This read has no submission side effects. Internal server errors are
        # unavailable evidence, not an incompatible contract or permission to send.
        return self.method == "account/rateLimits/read" and type(self.error.get("code")) is int and self.error["code"] == -32603

    def is_active_writer(self, thread_id: str) -> bool:
        return (
            self.method == "thread/resume"
            and self.error.get("code") == -32600
            and self.error.get("message") == f"thread {thread_id} already has an active writer"
        )


class AppServerClient:
    def __init__(self, websocket: UnixWebSocket):
        self._ws = websocket
        self._next_id = 1
        self.notifications: deque[dict[str, Any]] = deque(maxlen=256)
        self.server_requests: deque[dict[str, Any]] = deque(maxlen=64)
        self.thread_subscriptions: set[str] = set()
        self.user_agent: str | None = None
        self.socket_path: Path | None = None

    @classmethod
    def connect(cls, socket_path: Path, timeout: float) -> "AppServerClient":
        client = cls(UnixWebSocket.connect(socket_path, timeout))
        try:
            client.socket_path = socket_path.resolve()
            client._initialize()
            return client
        except BaseException:
            client.close()
            raise

    def _initialize(self) -> None:
        result = self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex_auto_continuer",
                    "title": "Codex Auto Continuer",
                    "version": __version__,
                },
                "capabilities": {
                    "experimentalApi": True,
                    "requestAttestation": False,
                    "optOutNotificationMethods": [
                        "item/agentMessage/delta",
                        "item/reasoning/summaryTextDelta",
                        "item/reasoning/textDelta",
                        "item/commandExecution/outputDelta",
                        "item/fileChange/outputDelta",
                    ],
                },
            },
        )
        if not isinstance(result, dict) or not isinstance(result.get("userAgent"), str):
            raise ProtocolError("Codex initialize response omitted userAgent.")
        self.user_agent = result["userAgent"]
        self.notify("initialized", None)

    def close(self) -> None:
        emit("rpc.connection_closed", subscriptions=len(self.thread_subscriptions))
        self.thread_subscriptions.clear()
        self._ws.close()

    def notify(self, method: str, params: Any) -> None:
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        self._ws.send_text(json.dumps(message, separators=(",", ":")))

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        started = time.monotonic()
        request_id = self._next_id
        emit("rpc.request", method=method, requestId=request_id, **rpc_request_fields(params))
        try:
            result = self._request(method, params)
        except BaseException as exc:
            code = exc.error.get("code") if isinstance(exc, RpcError) else None
            failure("rpc.failed", exc, method=method, requestId=request_id,
                    durationMs=round((time.monotonic() - started) * 1000, 2),
                    errorCode=code if type(code) is int else None)
            raise
        rpc_completed(method, request_id, round((time.monotonic() - started) * 1000, 2), params, result)
        return result

    def _request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self._ws.begin_request()
        request_id = self._next_id
        self._next_id += 1
        message: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self._ws.send_text(json.dumps(message, separators=(",", ":")))
        while True:
            raw = self._ws.recv_text()
            try:
                incoming = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ProtocolError(f"Codex app-server emitted invalid JSON: {exc}") from exc
            if not isinstance(incoming, dict):
                raise ProtocolError("Codex app-server emitted a non-object JSON-RPC message.")
            if "id" in incoming and "method" in incoming:
                # Deliberately do not answer app-server -> client approvals/input requests.
                self.server_requests.append(incoming)
                emit("rpc.server_request_ignored", method=incoming.get("method"))
                continue
            if "method" in incoming and "id" not in incoming:
                self.notifications.append(incoming)
                payload = incoming.get("params")
                emit("rpc.notification", method=incoming.get("method"),
                     **notification_summary(incoming.get("method"), payload))
                continue
            if incoming.get("id") != request_id:
                raise ProtocolError(
                    f"Codex app-server returned response id {incoming.get('id')!r}; expected {request_id!r}."
                )
            if "error" in incoming:
                error = incoming["error"]
                if not isinstance(error, dict):
                    raise ProtocolError(f"Codex RPC {method} returned a malformed error object.")
                raise RpcError(method, error)
            if "result" not in incoming:
                raise ProtocolError(f"Codex RPC {method} response omitted both result and error.")
            return incoming["result"]

    def thread_list(self, *, cursor: str | None = None, limit: int = 100) -> dict[str, Any]:
        return self._expect_object(
            "thread/list",
            self.request(
                "thread/list",
                {
                    "cursor": cursor,
                    "limit": limit,
                    "sortKey": "updated_at",
                    "sortDirection": "desc",
                    "modelProviders": [],
                    "sourceKinds": [],
                    "archived": False,
                },
            ),
        )

    def latest_turn(self, thread_id: str) -> dict[str, Any] | None:
        result = self._expect_object(
            "thread/turns/list",
            self.request(
                "thread/turns/list",
                {
                    "threadId": thread_id,
                    "cursor": None,
                    "limit": 1,
                    "sortDirection": "desc",
                    "itemsView": "notLoaded",
                },
            ),
        )
        data = result.get("data")
        if not isinstance(data, list):
            raise ProtocolError("thread/turns/list response omitted data array.")
        if not data:
            return None
        if not isinstance(data[0], dict):
            raise ProtocolError("thread/turns/list returned a non-object turn.")
        return data[0]

    def thread_read(self, thread_id: str) -> dict[str, Any]:
        result = self._expect_object(
            "thread/read", self.request("thread/read", {"threadId": thread_id, "includeTurns": False})
        )
        thread = result.get("thread")
        if not isinstance(thread, dict) or thread.get("id") != thread_id:
            raise ProtocolError("thread/read did not return the exact requested thread.")
        return thread

    def rate_limits(self) -> dict[str, Any]:
        return self._expect_object("account/rateLimits/read", self.request("account/rateLimits/read", {}))

    def resume_thread(self, thread_id: str) -> dict[str, Any]:
        result = self._expect_object(
            "thread/resume", self.request("thread/resume", {"threadId": thread_id, "excludeTurns": True})
        )
        self.thread_subscriptions.add(thread_id)
        return result

    def queue_add(self, thread_id: str, prompt: str, client_user_message_id: str) -> dict[str, Any]:
        return self.queue_add_input(thread_id, [{"type": "text", "text": prompt, "text_elements": []}], client_user_message_id)

    def queue_add_input(self, thread_id: str, input: list[dict], client_user_message_id: str) -> dict[str, Any]:
        return self._expect_object(
            "thread/queue/add",
            self.request(
                "thread/queue/add",
                {
                    "threadId": thread_id,
                    "input": input,
                    "clientUserMessageId": client_user_message_id,
                },
            ),
        )

    def next_notification(self, timeout: float = 0.1) -> dict | None:
        """Exclusive-connection reader. Never answer approvals or user-input requests."""
        if self.server_requests:
            return self.server_requests.popleft()
        if self.notifications:
            return self.notifications.popleft()
        if not self._ws.message_ready(timeout):
            return None
        self._ws.begin_request()
        try:
            incoming = json.loads(self._ws.recv_text())
        except json.JSONDecodeError as exc:
            raise ProtocolError("Codex emitted an invalid notification.") from exc
        if not isinstance(incoming, dict) or not isinstance(incoming.get("method"), str):
            raise ProtocolError("Unexpected response on the exclusive notification connection.")
        if "id" in incoming:
            emit("rpc.server_request_ignored", method=incoming["method"])
        else:
            emit("rpc.notification", method=incoming["method"],
                 **notification_summary(incoming["method"], incoming.get("params")))
        return incoming

    def full_turns(self, thread_id: str) -> list[dict]:
        turns, cursor, seen, identities = [], None, set(), set()
        for _ in range(100):
            result = self._expect_object("thread/turns/list", self.request("thread/turns/list",
                {"threadId": thread_id, "limit": 100, "sortDirection": "asc", "itemsView": "full", "cursor": cursor}))
            data = result.get("data")
            if not isinstance(data, list) or any(not isinstance(t, dict) or not isinstance(t.get("items"), list)
                or not isinstance(t.get("id"), str) or not t["id"]
                or t.get("status") not in {"inProgress", "completed", "failed", "interrupted"}
                or any(not isinstance(i, dict) for i in t["items"]) for t in data):
                raise ProtocolError("Codex full turn history omitted items.")
            for item in data:
                if item["id"] in identities:
                    raise ProtocolError("Codex full history repeated a turn identity.")
                identities.add(item["id"])
            turns.extend(data)
            cursor = result.get("nextCursor")
            if cursor is None:
                return turns
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise ProtocolError("Codex full turn history has an invalid pagination cursor.")
            seen.add(cursor)
        raise ProtocolError("Full history exceeds the bounded holding lookup. Inputs remain held for review.")

    def queue_list_page(self, thread_id: str, cursor: str | None = None) -> dict[str, Any]:
        return self._expect_object(
            "thread/queue/list",
            self.request("thread/queue/list", {"threadId": thread_id, "cursor": cursor, "limit": 100}),
        )

    def queue_delete(self, thread_id: str, queued_submission_id: str) -> bool:
        result = self._expect_object(
            "thread/queue/delete",
            self.request(
                "thread/queue/delete",
                {"threadId": thread_id, "queuedSubmissionId": queued_submission_id},
            ),
        )
        deleted = result.get("deleted")
        if not isinstance(deleted, bool):
            raise ProtocolError("thread/queue/delete response omitted boolean deleted field.")
        return deleted

    def queue_items(self, thread_id: str) -> list[dict[str, Any]]:
        cursor: str | None = None
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        while True:
            page = self.queue_list_page(thread_id, cursor)
            data = page.get("data")
            if not isinstance(data, list):
                raise ProtocolError("thread/queue/list response omitted data array.")
            for item in data:
                if not isinstance(item, dict):
                    raise ProtocolError("thread/queue/list returned a non-object queue item.")
                out.append(item)
            next_cursor = page.get("nextCursor")
            if next_cursor is None:
                return out
            if not isinstance(next_cursor, str) or not next_cursor:
                raise ProtocolError("thread/queue/list returned an invalid nextCursor.")
            if next_cursor in seen:
                raise ProtocolError("thread/queue/list repeated a pagination cursor.")
            seen.add(next_cursor)
            cursor = next_cursor

    @staticmethod
    def _expect_object(method: str, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ProtocolError(f"Codex RPC {method} returned a non-object result.")
        return value
