from __future__ import annotations

from dataclasses import asdict
import json

import pytest

from codex_auto_continuer.errors import ProtocolError
from codex_auto_continuer.quota_retry import QuotaRetry, RetryState
from codex_auto_continuer.state import load_state, save_state, State, Obligation
from test_supervisor import FakeClient, failed_turn, supervisor, thread


def limits(*, allowed=True, used=100, reset=1500, weekly_used=51, weekly_reset=9000):
    return {"ordinaryUsageAllowed": allowed, "rateLimits": {"limitId": "codex",
        "primary": {"usedPercent": used, "windowDurationMins": 300, "resetsAt": reset},
        "secondary": {"usedPercent": weekly_used, "windowDurationMins": 10080, "resetsAt": weekly_reset}}}


def test_observed_loop_waits_for_the_exhausted_reset_across_turns_and_restart(tmp_path):
    clock = [1000]
    client = FakeClient([thread()], {"t": failed_turn()}, allowed=True)
    client.rate_limits = lambda: limits(used=used[0])
    used = [100]
    monitor = supervisor(tmp_path, client, clock=lambda: clock[0])
    assert monitor.run_cycle().dispatched == 1
    client.queue.clear()
    client.turns["t"] = failed_turn("rejected-recovery")
    client.turns["t"]["completedAt"] = 1002
    clock[0] = 1030
    result = monitor.run_cycle()
    assert result.dispatched == 0 and result.pending == 1
    assert result.retry == {"blocked": True, "notBefore": 1500, "reason": "quota_reset", "backoffStep": 1}
    for used[0] in (99, 100, 99):
        clock[0] += 30
        monitor = supervisor(tmp_path, client, clock=lambda: clock[0])
        assert monitor.run_cycle().dispatched == 0
    # A new/manual quota-failed turn also cannot reset the shared cooldown.
    client.turns["t"] = failed_turn("newer-failed-turn")
    assert monitor.run_cycle().dispatched == 0
    assert load_state(monitor.state_file).obligations[0].failed_turn_id == "newer-failed-turn"
    clock[0] = 1500
    assert monitor.run_cycle().dispatched == 1
    assert len(client.added) == 2


def test_cooldown_is_shared_across_pending_chats(tmp_path):
    client = FakeClient([thread("one"), thread("two")], {"one": failed_turn()}, allowed=True)
    client.rate_limits = lambda: limits()
    monitor = supervisor(tmp_path, client)
    assert monitor.run_cycle().dispatched == 1
    client.queue.clear()
    client.turns["one"] = failed_turn("rejected")
    client.turns["two"] = failed_turn("another-chat")
    result = monitor.run_cycle()
    assert result.dispatched == 0 and result.pending == 2
    assert len(client.added) == 1


def test_cooldown_does_not_hide_an_unresolved_send_or_retry_it(tmp_path):
    obligation = Obligation.create("t", "turn-1", 900, None)
    obligation.phase, obligation.phase_changed_at = "uncertain", 900
    save_state(tmp_path / "state.json", State(obligations=[obligation]))
    client = FakeClient([thread()], {"t": failed_turn()}, allowed=True)
    monitor = supervisor(tmp_path, client)
    monitor.retry.rejected("other-chat", "rejected", 999, limits(), 1000)
    result = monitor.run_cycle()
    assert result.dispatched == 0 and not client.added
    assert result.warnings[0]["code"] == "submission_uncertain"
    assert monitor.state.obligations[0].phase == "uncertain"


def test_failure_guard_write_error_keeps_the_observation_and_sends_nothing(tmp_path, monkeypatch):
    client = FakeClient([thread()], {"t": failed_turn()}, allowed=True)
    monitor = supervisor(tmp_path, client)
    assert monitor.run_cycle().dispatched == 1
    client.queue.clear(); client.turns["t"] = failed_turn("rejected")
    before = monitor.state_file.read_bytes()
    saved = monitor.retry.save
    def cannot_save(state):
        raise ProtocolError("Synthetic retry disk failure")
    monkeypatch.setattr(monitor.retry, "save", cannot_save)
    with pytest.raises(ProtocolError, match="retry disk failure"):
        monitor.run_cycle()
    assert monitor.state_file.read_bytes() == before
    assert len(client.added) == 1 and len(monitor.state.observations) == 1
    assert monitor.retry.state.streak == 0
    monkeypatch.setattr(monitor.retry, "save", saved)
    assert monitor.run_cycle().dispatched == 0
    assert monitor.retry.state.streak == 1


def test_newer_rejection_wins_over_an_older_completed_observation(tmp_path):
    client = FakeClient([thread("one"), thread("two")],
        {"one": failed_turn("first"), "two": failed_turn("second")}, allowed=True)
    monitor = supervisor(tmp_path, client)
    assert monitor.run_cycle().dispatched == 2
    client.queue.clear()
    client.turns["one"] = failed_turn("rejected"); client.turns["one"]["completedAt"] = 1010
    client.turns["two"] = {"id": "completed", "status": "completed", "completedAt": 1005}
    result = monitor.run_cycle()
    assert result.dispatched == 0 and monitor.retry.state.streak == 1


@pytest.mark.parametrize("weekly_used,expected", [(51, 1500), (100, 9000)])
def test_only_exhausted_ordinary_windows_affect_the_wait(tmp_path, weekly_used, expected):
    retry = QuotaRetry(tmp_path / "quota-retry.json")
    raw = limits(weekly_used=weekly_used)
    raw["rateLimitsByLimitId"] = {"other_model": {"primary": {"usedPercent": 100,
        "windowDurationMins": 300, "resetsAt": 99999}}}
    retry.rejected("chat", "turn", 1000, raw, 1000)
    assert retry.state.not_before == expected


def test_weekly_only_and_missing_or_elapsed_reset_use_no_percentage_buffer(tmp_path):
    retry = QuotaRetry(tmp_path / "quota-retry.json")
    raw = limits(); raw["rateLimits"]["primary"] = None
    raw["rateLimits"]["secondary"]["usedPercent"] = 100
    retry.rejected("chat", "one", 1000, raw, 1000)
    assert retry.state.not_before == 9000
    for index, delay in enumerate((600, 1200, 1800, 1800), start=2):
        now = 9000 + index * 2000
        retry.rejected("chat", str(index), now, limits(used=99, reset=None), now)
        assert retry.state.not_before == now + delay
    assert retry.report(retry.state.not_before)["blocked"] is False


def test_replayed_observation_cannot_extend_the_deadline_and_only_later_success_clears_it(tmp_path):
    path = tmp_path / "quota-retry.json"
    retry = QuotaRetry(path)
    retry.rejected("chat", "turn", 1000, limits(), 1030)
    retry = QuotaRetry(path)
    assert not retry.rejected("chat", "turn", 1000, limits(), 1100)
    assert retry.state.streak == 1 and retry.state.not_before == 1500
    assert not retry.succeeded(999)
    assert retry.succeeded(1001)
    retry = QuotaRetry(path)
    assert not retry.blocked(1100)
    assert not retry.rejected("chat", "old-observation", 1000, limits(), 1100)


def test_known_account_change_resets_only_that_scope_and_missing_metadata_preserves_wait(tmp_path):
    retry = QuotaRetry(tmp_path / "quota-retry.json")
    retry.bind("a" * 64)
    retry.rejected("chat", "turn", 1000, limits(), 1000)
    retry.bind(None)
    assert retry.blocked(1100)
    retry.bind("b" * 64)
    assert not QuotaRetry(retry.path).blocked(1100)


@pytest.mark.parametrize("field,value", [("not_before", True), ("streak", -1), ("failures", []), ("binding", "token")])
def test_corrupt_retry_record_fails_loud_without_overwriting_it(tmp_path, field, value):
    path = tmp_path / "quota-retry.json"
    raw = asdict(RetryState()); raw[field] = value
    saved = json.dumps(raw); path.write_text(saved)
    with pytest.raises(ProtocolError, match="Preserve the file"):
        QuotaRetry(path)
    assert path.read_text() == saved


def test_elapsed_timer_still_requires_permission_and_low_positive_quota_is_not_reserved(tmp_path):
    clock = [1000]
    client = FakeClient([thread()], {"t": failed_turn()}, allowed=True)
    client.rate_limits = lambda: limits(allowed=client.allowed, used=99)
    monitor = supervisor(tmp_path, client, clock=lambda: clock[0])
    monitor.retry.rejected("old", "failed", 999, limits(reset=None), 1000)
    clock[0] = 1300
    client.allowed = False
    assert monitor.run_cycle().dispatched == 0
    client.allowed = True
    assert monitor.run_cycle().dispatched == 1
