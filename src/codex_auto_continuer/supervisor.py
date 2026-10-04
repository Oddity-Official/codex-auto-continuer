from __future__ import annotations

import logging
import math
import time
import hashlib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

from .appserver import AppServerClient, RpcError
from .codex import codex_version, ensure_daemon, find_codex
from .compatibility import Compatibility, CompatibilityGate, CompatibilityBlocked
from .config import Config, read_prompt
from .errors import ConfigurationError, ProtocolError, TransportError
from .state import Obligation, State, load_state, save_state
from .telemetry import emit, failure, changed, begin_cycle, thread_summary, turn_summary

LOG = logging.getLogger(__name__)
_ALLOWED_ACTIVE_FLAGS = {"waitingOnApproval", "waitingOnUserInput"}
_ALLOWED_THREAD_STATUS = {"notLoaded", "idle", "systemError", "active"}


class SubmissionUncertain(ProtocolError):
    """Chat-local ambiguity: retain its intent while other chats can proceed."""


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
    compatibility: dict | None = None
    warnings: list[dict] = field(default_factory=list)


class Supervisor:
    def __init__(
        self,
        config: Config,
        state_file: Path,
        *,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        prompt_file: Path | None = None,
        on_cycle: Callable[[CycleResult], None] | None = None,
    ):
        self.config = config
        self.state_file = state_file
        self.clock = clock
        self.sleep = sleep
        self.prompt_file = prompt_file or state_file.parent / config.prompt_file
        self.on_cycle = on_cycle
        self.state: State = load_state(state_file)
        self.client: AppServerClient | None = None
        self.codex_bin: str | None = None
        self._cli_version: str | None = None
        self.compatibility = Compatibility()
        self.compatibility_gate = CompatibilityGate(state_file.parent / "compatibility-cache")

    def connect(self) -> None:
        if self.client is not None:
            return
        codex_bin = self.codex_bin or find_codex(self.config.codex_executable)
        cli_version = codex_version(codex_bin, self.config.codex_command_timeout_seconds)
        daemon = ensure_daemon(codex_bin, self.config.codex_command_timeout_seconds, self.config.auto_start_daemon)
        client = AppServerClient.connect(daemon.socket_path, self.config.rpc_timeout_seconds)
        self.codex_bin = codex_bin
        self._cli_version = cli_version
        self.client = client
        self.compatibility = self.compatibility_gate.recheck(codex_bin, client.user_agent, self.config.codex_command_timeout_seconds, self.config.compatibility_policy)
        changed("compatibility.checked", "compatibility", **self.compatibility.report())
        LOG.info("Connected to Codex %s app-server %s", cli_version, client.user_agent)
        changed("codex.connected", "connection", cliVersion=cli_version, daemonVersion=daemon.app_server_version,
             socketPath=str(daemon.socket_path), userAgent=client.user_agent)
        if self.compatibility.read_allowed:
            self._probe_required_methods()

    def _check_dispatch_compatibility(self) -> None:
        if self.codex_bin is not None:
            self.compatibility = self.compatibility_gate.recheck(
                self.codex_bin, self._require_client().user_agent, self.config.codex_command_timeout_seconds, self.config.compatibility_policy)
            changed("compatibility.checked", "compatibility", **self.compatibility.report())
        if not self.compatibility.dispatch_allowed:
            raise CompatibilityBlocked(self.compatibility.reason)

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

    def run_forever(self, stop_requested: Callable[[], bool] = lambda: False,
                    wake_requested: Callable[[], bool] = lambda: False,
                    reload_settings: Callable[[], Config] | None = None,
                    on_pause: Callable[[], None] | None = None,
                    on_phase: Callable[[str], None] | None = None) -> None:
        def wait(seconds: float) -> None:
            remaining = seconds
            while remaining > 0 and not stop_requested():
                if wake_requested():
                    return
                step = min(1.0, remaining)
                self.sleep(step)
                remaining -= step

        settings_failed = False
        while not stop_requested():
            try:
                if reload_settings:
                    try:
                        updated = reload_settings()
                        if updated.codex_executable != self.config.codex_executable:
                            self.codex_bin = self._cli_version = None
                        self.config = updated
                    except ConfigurationError as exc:
                        if not settings_failed:
                            failure("settings.invalid", exc)
                            if on_pause:
                                on_pause()
                        settings_failed = True
                        self.close()
                        wait(1)
                        continue
                    if settings_failed:
                        emit("settings.recovered")
                        settings_failed = False
                if reload_settings:
                    self.prompt_file = self.state_file.parent / self.config.prompt_file
                if not self.config.clients and not self.state.obligations and not self.state.observations:
                    result = CycleResult()
                    begin_cycle()
                    emit("cycle.completed", **result.__dict__, observations=0)
                else:
                    if on_phase and self.compatibility.dispatch_allowed:
                        on_phase("scanning")
                    self.connect()
                    result = self.run_cycle()
                if self.on_cycle:
                    self.on_cycle(result)
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
            except CompatibilityBlocked:
                if self.on_cycle:
                    self.on_cycle(CycleResult(pending=len(self.state.obligations), compatibility=self.compatibility.report()))
                self.close()
                wait(max(1.0, self.config.poll_seconds))
            except TransportError as exc:
                if on_phase:
                    on_phase("reconnecting")
                failure("transport.reconnecting", exc, delaySeconds=self.config.reconnect_backoff_seconds)
                LOG.warning("Codex transport lost: %s; reconnecting in %.1fs", exc, self.config.reconnect_backoff_seconds)
                self.close()
                wait(max(1.0, self.config.reconnect_backoff_seconds))

    def run_cycle(self) -> CycleResult:
        begin_cycle()
        client = self._require_client()
        if not self.compatibility.read_allowed:
            result = CycleResult(pending=len(self.state.obligations), compatibility=self.compatibility.report())
            emit("cycle.completed", **result.__dict__, observations=len(self.state.observations))
            return result
        now = self.clock()
        limits = _parse_rate_limits(client.rate_limits())
        result = CycleResult(
            ordinary_usage_allowed=limits.ordinary_usage_allowed,
            next_reset_at=limits.next_reset_at,
            compatibility=self.compatibility.report(),
        )
        self._observe_deliveries()

        threads = self._recent_threads(now)
        result.scanned_threads = len(threads)
        by_id = {thread["id"]: thread for thread in threads}

        # Resolve existing obligations first. Manual progress always wins, even before reset.
        for obligation in list(self.state.obligations):
            if not self.compatibility.dispatch_allowed:
                continue  # Keep potentially submitted work intact until queue reconciliation is certified.
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
                emit("obligation.detected", threadId=thread_id, failedTurnId=turn_id,
                     completedAt=completed, detectedAt=now, resetAt=limits.next_reset_at)

        if limits.ordinary_usage_allowed is True and self.compatibility.dispatch_allowed:
            for obligation in sorted(list(self.state.obligations), key=lambda item: item.detected_at):
                try:
                    dispatched = self._dispatch_if_still_valid(obligation, now)
                except SubmissionUncertain:
                    warning = {"key": hashlib.sha256(obligation.client_user_message_id.encode()).hexdigest(),
                               "code": "submission_uncertain",
                               "message": "A chat has an unresolved send. It is isolated without a retry; other chats continue. Inspect local telemetry and the chat before making manual progress."}
                    result.warnings.append(warning)
                    changed("dispatch.quarantined", obligation.client_user_message_id,
                            threadId=obligation.thread_id, failedTurnId=obligation.failed_turn_id, phase=obligation.phase)
                    dispatched = False
                if dispatched:
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
        emit("cycle.completed", **result.__dict__, observations=len(self.state.observations))
        return result

    def _observe_deliveries(self) -> None:
        client = self._require_client()
        for observation in self.state.observations[:]:
            thread = client.thread_read(observation.thread_id)
            if thread is None or thread.get("archived") is True:
                emit("delivery.observation_ended", threadId=observation.thread_id, reason="missing_or_archived")
                self.state.observations.remove(observation)
                save_state(self.state_file, self.state)
                continue
            turn = client.latest_turn(observation.thread_id)
            if turn is None or turn.get("id") == observation.failed_turn_id:
                changed("delivery.waiting_for_next_turn", observation.client_user_message_id, threadId=observation.thread_id,
                     queuedSubmissionId=observation.queued_submission_id)
                continue
            changed("delivery.subsequent_turn", observation.client_user_message_id, threadId=observation.thread_id,
                 failedTurnId=observation.failed_turn_id, queuedSubmissionId=observation.queued_submission_id,
                 runtimeStatus=_thread_status(thread)[0], **turn_summary(turn))
            completed_at = turn.get("completedAt")
            if completed_at is not None:
                _required_timestamp(turn, "completedAt", "delivery thread/turns/list")
            if (_thread_status(thread)[0] != "active" and completed_at is not None
                    and turn.get("status") in {"completed", "failed", "interrupted"}):
                self.state.observations.remove(observation)
                save_state(self.state_file, self.state)

    def _track_delivery(self, obligation: Obligation) -> None:
        if not any(item.client_user_message_id == obligation.client_user_message_id for item in self.state.observations):
            self.state.observations.append(replace(obligation))

    def _recent_threads(self, now: float) -> list[dict[str, Any]]:
        if not self.config.clients:
            return []
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
                    changed("discovery.thread", thread["id"], **thread_summary(thread), decision="in_scope")
                else:
                    changed("discovery.thread", thread["id"], **thread_summary(thread), decision="out_of_scope")
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
        if label == "cli":
            return "cli" in self.config.clients
        if custom or (label == "vscode" and thread.get("originator") in self.config.desktop_originators):
            return "desktop" in self.config.clients
        return label == "vscode" and "vscode" in self.config.clients

    def _find_thread_by_id(self, thread_id: str) -> dict[str, Any] | None:
        return self._require_client().thread_read(thread_id)

    def _revalidate_obligation(self, obligation: Obligation, thread: dict[str, Any] | None) -> bool:
        emit("obligation.revalidate", threadId=obligation.thread_id, failedTurnId=obligation.failed_turn_id,
             phase=obligation.phase, thread=thread_summary(thread) if thread else None)
        if thread is None:
            emit("obligation.stale", threadId=obligation.thread_id, reason="missing_thread")
            LOG.info("Cancelling obligation for missing thread %s", obligation.thread_id)
            return False
        if thread.get("archived") is True or not self._scope_accepts(thread):
            emit("obligation.stale", threadId=obligation.thread_id, reason="archived_or_out_of_scope")
            LOG.info("Cancelling obligation because thread %s is no longer in configured scope", obligation.thread_id)
            return False
        status_type, _ = _thread_status(thread)
        if status_type == "active" and obligation.phase == "pending":
            emit("obligation.stale", threadId=obligation.thread_id, reason="active_thread")
            LOG.info("Cancelling obligation because thread %s is active", obligation.thread_id)
            return False
        turn = self._require_client().latest_turn(obligation.thread_id)
        if turn is None:
            emit("obligation.stale", threadId=obligation.thread_id, reason="missing_latest_turn")
            LOG.info("Cancelling obligation because thread %s has no latest turn", obligation.thread_id)
            return False
        turn_id = _required_string(turn, "id", "thread/turns/list")
        if turn_id != obligation.failed_turn_id or not _is_usage_limit_failure(turn):
            emit("obligation.stale", threadId=obligation.thread_id, failedTurnId=obligation.failed_turn_id,
                 phase=obligation.phase, latestTurn=turn_summary(turn), reason="latest_turn_changed")
            LOG.info("Cancelling stale obligation thread=%s failedTurn=%s latest=%s", obligation.thread_id, obligation.failed_turn_id, turn_id)
            return False
        return True

    def _dispatch_if_still_valid(self, obligation: Obligation, now: float) -> bool:
        self._check_dispatch_compatibility()
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
            self._check_dispatch_compatibility()
            try:
                resumed = client.resume_thread(obligation.thread_id)
            except RpcError as exc:
                if not exc.is_active_writer(obligation.thread_id):
                    raise
                # The Desktop app has a separate server. Its verified writer
                # consumes the shared queue; never steal or duplicate ownership.
                LOG.info("Thread %s is owned by another Codex server; dispatching through its shared queue.", obligation.thread_id)
                status_type = "idle"
                emit("dispatch.separate_owner", threadId=obligation.thread_id)
            else:
                resumed_thread = resumed.get("thread")
                if not isinstance(resumed_thread, dict) or resumed_thread.get("id") != obligation.thread_id:
                    raise ProtocolError("thread/resume did not return the exact requested thread.")
                status_type, _ = _thread_status(resumed_thread)
        if status_type == "active":
            emit("dispatch.cancelled", threadId=obligation.thread_id, reason="active_after_resume")
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return False
        if status_type == "systemError":
            emit("dispatch.deferred", threadId=obligation.thread_id, reason="runtime_system_error")
            LOG.warning("Thread %s is in systemError; leaving obligation pending.", obligation.thread_id)
            return False
        if status_type != "idle":
            raise ProtocolError(f"Thread {obligation.thread_id} is in unsupported dispatch state {status_type!r}.")

        # Resuming and other RPCs take time. Both quota and the exact failed turn
        # must still be valid immediately before the non-idempotent queue send.
        self._check_dispatch_compatibility()
        if not self._revalidate_obligation(obligation, client.thread_read(obligation.thread_id)):
            self._cancel_queued_continuations(obligation)
            self.state.obligations.remove(obligation)
            save_state(self.state_file, self.state)
            return False
        if _parse_rate_limits(client.rate_limits()).ordinary_usage_allowed is not True:
            emit("dispatch.deferred", threadId=obligation.thread_id, reason="quota_recheck_denied")
            return False

        prompt = read_prompt(self.prompt_file)
        emit("prompt.loaded", sha256=hashlib.sha256(prompt.encode()).hexdigest(), characters=len(prompt), path=str(self.prompt_file))
        obligation.phase = "dispatching"
        obligation.phase_changed_at = now
        obligation.queued_submission_id = None
        save_state(self.state_file, self.state)
        emit("dispatch.intent_saved", threadId=obligation.thread_id, failedTurnId=obligation.failed_turn_id,
             clientUserMessageId=obligation.client_user_message_id)
        try:
            response = client.queue_add(
                obligation.thread_id,
                prompt,
                obligation.client_user_message_id,
            )
        except (TransportError, RpcError):
            obligation.phase = "uncertain"
            obligation.phase_changed_at = self.clock()
            save_state(self.state_file, self.state)
            emit("dispatch.uncertain", threadId=obligation.thread_id, failedTurnId=obligation.failed_turn_id)
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
        self._track_delivery(obligation)
        save_state(self.state_file, self.state)
        emit("dispatch.submitted", threadId=obligation.thread_id, failedTurnId=obligation.failed_turn_id,
             queuedSubmissionId=queue_id, clientUserMessageId=obligation.client_user_message_id)
        LOG.info("Submitted continuation thread=%s queuedSubmission=%s", obligation.thread_id, queue_id)
        return True

    def _cancel_queued_continuations(self, obligation: Obligation) -> None:
        if obligation.phase == "pending" and obligation.queued_submission_id is None:
            return
        client = self._require_client()
        self._check_dispatch_compatibility()
        matches = [
            item
            for item in client.queue_items(obligation.thread_id)
            if item.get("clientUserMessageId") == obligation.client_user_message_id
        ]
        for item in matches:
            self._check_dispatch_compatibility()
            queue_id = _required_string(item, "id", "thread/queue/list")
            deleted = client.queue_delete(obligation.thread_id, queue_id)
            emit("queue.stale_item_deleted", threadId=obligation.thread_id, queuedSubmissionId=queue_id, deleted=deleted)
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
                self._track_delivery(obligation)
                save_state(self.state_file, self.state)
                emit("dispatch.reconciled", threadId=obligation.thread_id, queuedSubmissionId=queue_id,
                     clientUserMessageId=obligation.client_user_message_id)
                return
        if now - obligation.phase_changed_at < self.config.dispatch_recovery_seconds:
            return
        # There is no verified idempotency contract for clientUserMessageId. Once a send is
        # ambiguous, retrying can duplicate a continuation. Isolate only this chat.
        raise SubmissionUncertain(
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
