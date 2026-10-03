from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .appserver import AppServerClient, RpcError
from .codex import codex_version, ensure_daemon, find_codex
from .config import Config
from .errors import ProtocolError, TransportError
from .state import Obligation, State, load_state, save_state

LOG = logging.getLogger(__name__)
_ALLOWED_ACTIVE_FLAGS = {"waitingOnApproval", "waitingOnUserInput"}
_ALLOWED_THREAD_STATUS = {"notLoaded", "idle", "systemError", "active"}


@dataclass(frozen=True)
class RateLimitState:
    ordinary_usage_allowed: bool | None
    next_reset_at: float | None


@dataclass
class CycleResult:
    scanned_threads: int = 0
    detected: int = 0
    cancelled: int = 0
    dispatched: int = 0
    pending: int = 0
    ordinary_usage_allowed: bool | None = None
    next_reset_at: float | None = None


class Supervisor:
    def __init__(
        self,
        config: Config,
        state_file: Path,
        *,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.config = config
        self.state_file = state_file
        self.clock = clock
        self.sleep = sleep
        self.state: State = load_state(state_file)
        self.client: AppServerClient | None = None
        self.codex_bin: str | None = None
        self._cli_version: str | None = None

    def connect(self) -> None:
        if self.client is not None:
            return
        codex_bin = self.codex_bin or find_codex()
        cli_version = self._cli_version or codex_version(codex_bin, self.config.codex_command_timeout_seconds)
        daemon = ensure_daemon(codex_bin, self.config.codex_command_timeout_seconds, self.config.auto_start_daemon)
        client = AppServerClient.connect(daemon.socket_path, self.config.rpc_timeout_seconds)
        self.codex_bin = codex_bin
        self._cli_version = cli_version
        self.client = client
        LOG.info("Connected to Codex %s app-server %s", cli_version, client.user_agent)
        self._probe_required_methods()

    def close(self) -> None:
        client, self.client = self.client, None
        if client is not None:
            client.close()

    def _require_client(self) -> AppServerClient:
        if self.client is None:
            raise ProtocolError("Supervisor is not connected to Codex app-server.")
        return self.client

    def _probe_required_methods(self) -> None:
        client = self._require_client()
        page = client.thread_list(limit=1)
        if not isinstance(page.get("data"), list):
            raise ProtocolError("thread/list capability probe returned no data array.")
        limits = client.rate_limits()
        if "ordinaryUsageAllowed" not in limits:
            raise ProtocolError(
                "account/rateLimits/read does not expose ordinaryUsageAllowed. Refusing to infer quota recovery."
            )
        _parse_rate_limits(limits)

    def run_forever(self, stop_requested: Callable[[], bool] = lambda: False) -> None:
        def wait(seconds: float) -> None:
            remaining = seconds
            while remaining > 0 and not stop_requested():
                step = min(1.0, remaining)
                self.sleep(step)
                remaining -= step

        while not stop_requested():
            try:
                self.connect()
                result = self.run_cycle()
                LOG.info(
                    "cycle scanned=%d detected=%d cancelled=%d dispatched=%d pending=%d usageAllowed=%r",
                    result.scanned_threads,
                    result.detected,
                    result.cancelled,
                    result.dispatched,
                    result.pending,
                    result.ordinary_usage_allowed,
                )
                delay = self._next_sleep_seconds(result)
                # Every cycle uses a fresh client. This guarantees a thread/resume subscription
                # cannot linger and receive approval or requestUserInput traffic while sleeping.
                self.close()
                wait(delay)
            except TransportError as exc:
                LOG.warning("Codex transport lost: %s; reconnecting in %.1fs", exc, self.config.reconnect_backoff_seconds)
                self.close()
                wait(max(1.0, self.config.reconnect_backoff_seconds))

    def run_cycle(self) -> CycleResult:
        client = self._require_client()
        now = self.clock()
        limits = _parse_rate_limits(client.rate_limits())
        result = CycleResult(
            ordinary_usage_allowed=limits.ordinary_usage_allowed,
            next_reset_at=limits.next_reset_at,
        )

        threads = self._recent_threads(now)
        result.scanned_threads = len(threads)
        by_id = {thread["id"]: thread for thread in threads}

        # Resolve existing obligations first. Manual progress always wins, even before reset.
        for obligation in list(self.state.obligations):
            if limits.next_reset_at is not None:
                obligation.reset_at = limits.next_reset_at
            thread = by_id.get(obligation.thread_id) or self._find_thread_by_id(obligation.thread_id)
            if not self._revalidate_obligation(obligation, thread):
                if thread is not None:
                    self._cancel_queued_continuations(obligation)
                self.state.obligations.remove(obligation)
                result.cancelled += 1
                save_state(self.state_file, self.state)

        existing = self.state.by_thread()
        for thread in threads:
            thread_id = _required_string(thread, "id", "thread/list")
            if thread_id in existing:
                continue
            status_type, _flags = _thread_status(thread)
            if status_type == "active":
                continue
            turn = client.latest_turn(thread_id)
            if turn is not None and _is_usage_limit_failure(turn):
                completed = _required_timestamp(turn, "completedAt", "failed thread/turns/list")
                if completed < now - self.config.scan_lookback_hours * 3600:
                    continue
                turn_id = _required_string(turn, "id", "thread/turns/list")
                obligation = Obligation.create(thread_id, turn_id, now, limits.next_reset_at)
                self.state.obligations.append(obligation)
                existing[thread_id] = obligation
                result.detected += 1
                save_state(self.state_file, self.state)
                LOG.info("Recorded usage-limit obligation thread=%s turn=%s", thread_id, turn_id)

        if limits.ordinary_usage_allowed is True:
            for obligation in sorted(list(self.state.obligations), key=lambda item: item.detected_at):
                if self._dispatch_if_still_valid(obligation, now):
                    result.dispatched += 1
                    if self.config.dispatch_spacing_seconds > 0:
                        self.sleep(self.config.dispatch_spacing_seconds)
                # Re-check account permission between multiple threads so one reset does not fan out blindly.
                limits = _parse_rate_limits(client.rate_limits())
                result.ordinary_usage_allowed = limits.ordinary_usage_allowed
                result.next_reset_at = limits.next_reset_at
                if limits.ordinary_usage_allowed is not True:
                    break
        elif limits.ordinary_usage_allowed is None and self.state.obligations:
            LOG.warning("Codex did not verify ordinary usage availability; pending obligations will not dispatch.")

        result.pending = len(self.state.obligations)
        return result

    def _recent_threads(self, now: float) -> list[dict[str, Any]]:
        client = self._require_client()
        cutoff = now - self.config.scan_lookback_hours * 3600
        cursor: str | None = None
        seen_cursors: set[str] = set()
        out: list[dict[str, Any]] = []
        while True:
            page = client.thread_list(cursor=cursor, limit=100)
            data = page.get("data")
            if not isinstance(data, list):
                raise ProtocolError("thread/list response omitted data array.")
            stop = False
            for thread in data:
                if not isinstance(thread, dict):
                    raise ProtocolError("thread/list returned a non-object thread.")
                _thread_status(thread)
                updated = _required_timestamp(thread, "updatedAt", "thread/list")
                if updated < cutoff:
                    stop = True
                    break
                if self._scope_accepts(thread):
                    out.append(thread)
            if stop:
                return out
            next_cursor = page.get("nextCursor")
            if next_cursor is None:
                return out
            if not isinstance(next_cursor, str) or not next_cursor:
                raise ProtocolError("thread/list returned an invalid nextCursor.")
            if next_cursor in seen_cursors:
                raise ProtocolError("thread/list repeated a pagination cursor.")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def _scope_accepts(self, thread: dict[str, Any]) -> bool:
        label = _session_source_label(thread.get("source"))
        custom = label in {f"custom:{x}" for x in self.config.desktop_custom_sources}
        if self.config.thread_scope == "desktop":
            return custom or (label == "vscode" and thread.get("originator") in self.config.desktop_originators)
        return label in {"cli", "vscode"} or custom

    def _find_thread_by_id(self, thread_id: str) -> dict[str, Any] | None:
        return self._require_client().thread_read(thread_id)

    def _revalidate_obligation(self, obligation: Obligation, thread: dict[str, Any] | None) -> bool:
        if thread is None:
            LOG.info("Cancelling obligation for missing thread %s", obligation.thread_id)
            return False
        if thread.get("archived") is True or not self._scope_accepts(thread):
            LOG.info("Cancelling obligation because thread %s is no longer in configured scope", obligation.thread_id)
            return False
        status_type, _ = _thread_status(thread)
        if status_type == "active" and obligation.phase == "pending":
            LOG.info("Cancelling obligation because thread %s is active", obligation.thread_id)
            return False
        turn = self._require_client().latest_turn(obligation.thread_id)
        if turn is None:
            LOG.info("Cancelling obligation because thread %s has no latest turn", obligation.thread_id)
            return False
        turn_id = _required_string(turn, "id", "thread/turns/list")
        if turn_id != obligation.failed_turn_id or not _is_usage_limit_failure(turn):
            LOG.info("Cancelling stale obligation thread=%s failedTurn=%s latest=%s", obligation.thread_id, obligation.failed_turn_id, turn_id)
            return False
        return True

    def _dispatch_if_still_valid(self, obligation: Obligation, now: float) -> bool:
        client = self._require_client()
        thread = self._find_thread_by_id(obligation.thread_id)
        if not self._revalidate_obligation(obligation, thread):
            if thread is not None:
                self._cancel_queued_continuations(obligation)
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return False

        if obligation.phase in {"dispatching", "uncertain", "submitted"}:
            self._recover_submission_state(obligation, now)
            return False

        assert thread is not None
        status_type, _ = _thread_status(thread)
        if status_type == "notLoaded":
            try:
                resumed = client.resume_thread(obligation.thread_id)
            except RpcError as exc:
                if not exc.is_active_writer(obligation.thread_id):
                    raise
                # The Desktop app has a separate server. Its verified writer
                # consumes the shared queue; never steal or duplicate ownership.
                LOG.info("Thread %s is owned by another Codex server; dispatching through its shared queue.", obligation.thread_id)
                status_type = "idle"
            else:
                resumed_thread = resumed.get("thread")
                if not isinstance(resumed_thread, dict) or resumed_thread.get("id") != obligation.thread_id:
                    raise ProtocolError("thread/resume did not return the exact requested thread.")
                status_type, _ = _thread_status(resumed_thread)
        if status_type == "active":
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return False
        if status_type == "systemError":
            LOG.warning("Thread %s is in systemError; leaving obligation pending.", obligation.thread_id)
            return False
        if status_type != "idle":
            raise ProtocolError(f"Thread {obligation.thread_id} is in unsupported dispatch state {status_type!r}.")

        # Resuming and other RPCs take time. Both quota and the exact failed turn
        # must still be valid immediately before the non-idempotent queue send.
        if not self._revalidate_obligation(obligation, client.thread_read(obligation.thread_id)):
            self._cancel_queued_continuations(obligation)
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return False
        if _parse_rate_limits(client.rate_limits()).ordinary_usage_allowed is not True:
            return False

        obligation.phase = "dispatching"
        obligation.phase_changed_at = now
        obligation.queued_submission_id = None
        save_state(self.state_file, self.state)
        try:
            response = client.queue_add(
                obligation.thread_id,
                self.config.continue_prompt,
                obligation.client_user_message_id,
            )
        except (TransportError, RpcError):
            obligation.phase = "uncertain"
            obligation.phase_changed_at = self.clock()
            save_state(self.state_file, self.state)
            raise
        queued = response.get("queuedSubmission")
        if not isinstance(queued, dict):
            raise ProtocolError("thread/queue/add response omitted queuedSubmission.")
        queue_id = _required_string(queued, "id", "thread/queue/add")
        echoed_client_id = _required_string(queued, "clientUserMessageId", "thread/queue/add")
        if echoed_client_id != obligation.client_user_message_id:
            raise ProtocolError("thread/queue/add echoed a different clientUserMessageId; refusing to mark dispatch successful.")
        obligation.phase = "submitted"
        obligation.phase_changed_at = self.clock()
        obligation.queued_submission_id = queue_id
        save_state(self.state_file, self.state)
        LOG.info("Submitted continuation thread=%s queuedSubmission=%s", obligation.thread_id, queue_id)
        return True

    def _cancel_queued_continuations(self, obligation: Obligation) -> None:
        if obligation.phase == "pending" and obligation.queued_submission_id is None:
            return
        client = self._require_client()
        matches = [
            item
            for item in client.queue_items(obligation.thread_id)
            if item.get("clientUserMessageId") == obligation.client_user_message_id
        ]
        for item in matches:
            queue_id = _required_string(item, "id", "thread/queue/list")
            deleted = client.queue_delete(obligation.thread_id, queue_id)
            LOG.info(
                "Stale continuation queue cancellation thread=%s queuedSubmission=%s deleted=%s",
                obligation.thread_id,
                queue_id,
                deleted,
            )
        if matches and any(
            item.get("clientUserMessageId") == obligation.client_user_message_id
            for item in client.queue_items(obligation.thread_id)
        ):
            raise ProtocolError("Codex still has this tool's stale queue item after deletion; retaining the obligation.")

    def _recover_submission_state(self, obligation: Obligation, now: float) -> None:
        client = self._require_client()
        turn = client.latest_turn(obligation.thread_id)
        if turn is None:
            self._cancel_queued_continuations(obligation)
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return
        turn_id = _required_string(turn, "id", "thread/turns/list")
        if turn_id != obligation.failed_turn_id:
            self._cancel_queued_continuations(obligation)
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return
        thread = self._find_thread_by_id(obligation.thread_id)
        if thread is not None and _thread_status(thread)[0] == "active":
            self._cancel_queued_continuations(obligation)
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return
        for item in client.queue_items(obligation.thread_id):
            if item.get("clientUserMessageId") == obligation.client_user_message_id:
                queue_id = _required_string(item, "id", "thread/queue/list")
                obligation.phase = "submitted"
                obligation.queued_submission_id = queue_id
                obligation.phase_changed_at = now
                save_state(self.state_file, self.state)
                return
        if now - obligation.phase_changed_at < self.config.dispatch_recovery_seconds:
            return
        # There is no verified idempotency contract for clientUserMessageId. Once a send is
        # ambiguous, retrying can duplicate a continuation. Fail loud instead.
        raise ProtocolError(
            f"Dispatch for thread {obligation.thread_id} is {obligation.phase!r} but no queued item or "
            "advanced turn can be verified. Refusing an automatic retry because Codex does not expose a "
            "verified idempotency contract for this submission. Inspect the thread and state file manually."
        )

    def _next_sleep_seconds(self, result: CycleResult) -> float:
        delay = max(1.0, self.config.poll_seconds)
        if result.pending and result.ordinary_usage_allowed is False and result.next_reset_at is not None:
            remaining = result.next_reset_at - self.clock()
            if remaining > 0:
                delay = min(delay, max(1.0, remaining))
        return delay


def _required_string(obj: dict[str, Any], field: str, context: str) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value:
        raise ProtocolError(f"{context} field {field} must be a non-empty string.")
    return value


def _required_timestamp(obj: dict[str, Any], field: str, context: str) -> float:
    value = obj.get(field)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ProtocolError(f"{context} field {field} must be a finite numeric timestamp.")
    return float(value)


def _thread_status(thread: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    raw = thread.get("status")
    if not isinstance(raw, dict):
        raise ProtocolError("Thread status is missing or not an object.")
    status_type = raw.get("type")
    if status_type not in _ALLOWED_THREAD_STATUS:
        raise ProtocolError(f"Unknown Codex thread status {status_type!r}.")
    flags: tuple[str, ...] = ()
    if status_type == "active":
        raw_flags = raw.get("activeFlags")
        if not isinstance(raw_flags, list) or not all(isinstance(x, str) for x in raw_flags):
            raise ProtocolError("Active Codex thread status omitted a valid activeFlags array.")
        unknown = sorted(set(raw_flags) - _ALLOWED_ACTIVE_FLAGS)
        if unknown:
            raise ProtocolError(f"Unknown Codex active flag(s): {', '.join(unknown)}")
        flags = tuple(raw_flags)
    return status_type, flags


def _is_usage_limit_failure(turn: dict[str, Any]) -> bool:
    if turn.get("status") != "failed":
        return False
    error = turn.get("error")
    if not isinstance(error, dict):
        return False
    return error.get("codexErrorInfo") == "usageLimitExceeded"


def _parse_rate_limits(raw: dict[str, Any]) -> RateLimitState:
    if "ordinaryUsageAllowed" not in raw:
        raise ProtocolError("account/rateLimits/read response omitted ordinaryUsageAllowed.")
    allowed = raw["ordinaryUsageAllowed"]
    if allowed is not None and not isinstance(allowed, bool):
        raise ProtocolError("ordinaryUsageAllowed must be true, false, or null.")
    rate_limits = raw.get("rateLimits")
    if not isinstance(rate_limits, dict):
        raise ProtocolError("account/rateLimits/read response omitted required rateLimits object.")
    by_id = raw.get("rateLimitsByLimitId")
    if by_id is not None and not isinstance(by_id, dict):
        raise ProtocolError("rateLimitsByLimitId must be an object or null.")
    reset_candidates: list[float] = []

    def visit(snapshot: Any) -> None:
        if not isinstance(snapshot, dict):
            return
        for key in ("primary", "secondary"):
            window = snapshot.get(key)
            if not isinstance(window, dict):
                continue
            used = window.get("usedPercent")
            reset = window.get("resetsAt")
            if (
                isinstance(used, (int, float))
                and not isinstance(used, bool)
                and math.isfinite(float(used))
                and used >= 100
            ):
                if (
                    isinstance(reset, (int, float))
                    and not isinstance(reset, bool)
                    and math.isfinite(float(reset))
                ):
                    reset_candidates.append(float(reset))

    visit(rate_limits)
    if isinstance(by_id, dict):
        for snapshot in by_id.values():
            visit(snapshot)
    return RateLimitState(allowed, max(reset_candidates) if reset_candidates else None)


def _session_source_label(source: Any) -> str:
    if isinstance(source, str):
        if source in {"cli", "vscode", "exec", "appServer", "unknown"}:
            return source
        raise ProtocolError(f"Unknown Codex session source {source!r}.")
    if isinstance(source, dict) and len(source) == 1:
        if "custom" in source and isinstance(source["custom"], str) and source["custom"]:
            return f"custom:{source['custom']}"
        if "subAgent" in source:
            return "subAgent"
    raise ProtocolError(f"Malformed Codex session source: {source!r}")


def observed_interactive_sources(client: AppServerClient, limit: int = 500) -> dict[str, int]:
    cursor: str | None = None
    seen: set[str] = set()
    counts: dict[str, int] = {}
    remaining = limit
    while remaining > 0:
        page = client.thread_list(cursor=cursor, limit=min(100, remaining))
        data = page.get("data")
        if not isinstance(data, list):
            raise ProtocolError("thread/list response omitted data array.")
        for thread in data:
            if not isinstance(thread, dict):
                raise ProtocolError("thread/list returned a non-object thread.")
            label = _session_source_label(thread.get("source"))
            counts[label] = counts.get(label, 0) + 1
            remaining -= 1
            if remaining == 0:
                break
        next_cursor = page.get("nextCursor")
        if remaining == 0 or next_cursor is None:
            break
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen:
            raise ProtocolError("thread/list pagination is invalid while sampling source labels.")
        seen.add(next_cursor)
        cursor = next_cursor
    return dict(sorted(counts.items()))
