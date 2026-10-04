from __future__ import annotations

from dataclasses import replace
import time

import pytest

from codex_auto_continuer.errors import ConfigurationError, ProtocolError, TransportError
from codex_auto_continuer.state import load_state
from native_support import LostQueueAck


def record_failure(native):
    thread_id, failed = native.start_thread()
    native.assert_quota_failure(failed)
    supervisor = native.supervisor()
    result = supervisor.run_cycle()
    assert (result.detected, result.dispatched, result.pending) == (1, 0, 1)
    saved = load_state(supervisor.state_file).obligations
    assert len(saved) == 1 and saved[0].failed_turn_id == failed["id"]
    assert saved[0].thread_id == thread_id
    assert native.service.inference_count == 1
    assert not native.service.errors
    return thread_id, failed, supervisor


def assert_no_duplicates(native, thread_id, count, *, total_inferences=None):
    supervisor = native.supervisor()
    for _ in range(3):
        result = supervisor.run_cycle()
        assert result.dispatched == result.pending == 0
    assert not supervisor.client.queue_items(thread_id)
    assert len(native.turns(thread_id)) == count
    assert native.service.inference_count == (count if total_inferences is None else total_inferences)
    assert not native.service.errors


def test_native_queued_quota_failures_and_usage_read_outage_recover(native):
    thread_id, failed, supervisor = record_failure(native)
    native.owner.queue_add(thread_id, "Synthetic follow-up one", "fixture-follow-up-one")
    native.owner.queue_add(thread_id, "Synthetic follow-up two", "fixture-follow-up-two")
    deadline = time.monotonic() + 20
    while len(native.turns(thread_id)) < 3 and time.monotonic() < deadline:
        time.sleep(0.1)
    latest = native.wait_turn(thread_id, after=failed["id"])
    turns = native.turns(thread_id)
    assert len(turns) == 3
    for turn in turns:
        native.assert_quota_failure(turn)
    # A newer failed follow-up replaces stale work, rather than dropping recovery.
    supervisor.run_cycle()
    result = supervisor.run_cycle()
    assert result.pending == 1
    assert supervisor.state.obligations[0].failed_turn_id == latest["id"]
    before = supervisor.state_file.read_bytes()
    native.service.fail_usage = True
    phases, cycles, waits = [], [], []
    def sleep(seconds):
        assert supervisor.client is None
        assert supervisor.state_file.read_bytes() == before
        assert native.service.inference_count == 3
        assert supervisor.read_problem["errorMethod"] == "account/rateLimits/read"
        assert supervisor.read_problem["errorCode"] == -32603
        waits.append(seconds)
        native.service.fail_usage = False
    supervisor.sleep = sleep
    supervisor.on_cycle = cycles.append
    supervisor.run_forever(lambda: bool(cycles), on_phase=phases.append)
    assert "reconnecting" in phases and waits and cycles[0].pending == 1
    assert cycles[0].ordinary_usage_allowed is False
    native.service.allowed = True
    native.service.fail_inference = False
    supervisor.connect()
    assert supervisor.run_cycle().dispatched == 1
    completed = native.wait_turn(thread_id, after=latest["id"])
    assert completed["status"] == "completed"
    assert native.service.user_messages[-1] == "Continue"
    assert_no_duplicates(native, thread_id, 4)


def test_native_quota_recovery_exact_chat_and_restart(native):
    # An unrelated successful chat must remain untouched.
    native.service.fail_inference = False
    unrelated, untouched = native.start_thread("Unrelated fixture task")
    native.service.fail_inference = True
    thread_id, failed = native.start_thread()
    native.assert_quota_failure(failed)
    supervisor = native.supervisor()
    for cycle in range(3):
        result = supervisor.run_cycle()
        assert result.ordinary_usage_allowed is False
        assert result.next_reset_at < supervisor.clock()
        assert result.detected == (1 if cycle == 0 else 0)
        assert result.dispatched == 0 and result.pending == 1
        assert not supervisor.client.queue_items(thread_id)
    supervisor.close()
    supervisor = native.supervisor()  # Durable pending state survives a new engine/connection.
    assert len(supervisor.state.obligations) == 1
    assert supervisor.client.thread_read(thread_id)["status"]["type"] == "notLoaded"
    native.service.allowed = True
    native.service.fail_inference = False
    result = supervisor.run_cycle()
    assert result.dispatched == 1 and result.ordinary_usage_allowed is True
    completed = native.wait_turn(thread_id, after=failed["id"])
    assert completed["status"] == "completed"
    assert native.service.user_messages[-1] == "Continue"
    assert native.owner.latest_turn(unrelated)["id"] == untouched["id"]
    assert len(native.turns(unrelated)) == 1
    assert_no_duplicates(native, thread_id, 2, total_inferences=3)
    events = native.events()
    names = [event["event"] for event in events]
    for expected in ("obligation.detected", "dispatch.separate_owner", "dispatch.intent_saved",
                     "dispatch.submitted", "delivery.subsequent_turn"):
        assert expected in names
    assert names.count("dispatch.submitted") == 1
    permissions = [event["fields"].get("ordinaryUsageAllowed")
        for event in events if event["event"] == "quota.changed"]
    assert False in permissions and True in permissions
    assert any(event["fields"].get("status") == "completed"
        for event in events if event["event"] == "delivery.subsequent_turn")
    log = native.telemetry_file.read_text(encoding="utf-8")
    for secret_or_body in (thread_id, failed["id"], "cac-local-fixture-not-a-real-token",
                           "Fixture initial task", "CAC_FIXTURE_OK"):
        assert secret_or_body not in log
    assert all(event["privacy"] == "private" for event in events)


@pytest.mark.parametrize("field", ["account", "user"])
def test_native_identity_mismatch_denies_permission(native, field):
    thread_id, failed, supervisor = record_failure(native)
    native.service.allowed = True
    setattr(native.service, field, "wrong-fixture-identity")
    result = supervisor.run_cycle()
    assert result.ordinary_usage_allowed is None
    assert result.dispatched == 0 and result.pending == 1
    assert native.service.inference_count == 1
    assert native.owner.latest_turn(thread_id)["id"] == failed["id"]
    assert not native.service.errors


def test_native_manual_progress_cancels_before_recovery(native):
    thread_id, failed, supervisor = record_failure(native)
    native.service.fail_inference = False
    native.start_turn(thread_id, "Manual fixture continuation")
    completed = native.wait_turn(thread_id, after=failed["id"])
    assert completed["status"] == "completed"
    result = supervisor.run_cycle()
    assert result.cancelled == 1 and result.dispatched == result.pending == 0
    native.service.allowed = True
    assert_no_duplicates(native, thread_id, 2)


def test_native_permission_rechecked_between_two_failed_chats(native):
    first, first_failed = native.start_thread("First quota fixture")
    second, second_failed = native.start_thread("Second quota fixture")
    native.assert_quota_failure(first_failed)
    native.assert_quota_failure(second_failed)
    supervisor = native.supervisor()
    result = supervisor.run_cycle()
    assert result.detected == result.pending == 2 and result.dispatched == 0
    native.service.fail_inference = False
    # Initial scan permission, first chat's immediate recheck, post-dispatch denial.
    native.service.permission_sequence = [True, True, False]
    result = supervisor.run_cycle()
    assert result.dispatched == 1 and result.ordinary_usage_allowed is False
    submitted = [item for item in supervisor.state.obligations if item.phase == "submitted"]
    pending = [item for item in supervisor.state.obligations if item.phase == "pending"]
    assert len(submitted) == len(pending) == 1
    sent_id, waiting_id = submitted[0].thread_id, pending[0].thread_id
    failures = {first: first_failed, second: second_failed}
    assert native.wait_turn(sent_id, after=failures[sent_id]["id"])["status"] == "completed"
    assert native.owner.latest_turn(waiting_id)["id"] == failures[waiting_id]["id"]
    result = supervisor.run_cycle()
    assert result.dispatched == 0 and result.pending == 1
    assert native.service.inference_count == 3
    native.service.allowed = True
    assert supervisor.run_cycle().dispatched == 1
    assert native.wait_turn(waiting_id, after=failures[waiting_id]["id"])["status"] == "completed"
    assert_no_duplicates(native, first, 2, total_inferences=4)
    assert_no_duplicates(native, second, 2, total_inferences=4)
    assert native.service.user_messages.count("Continue") == 2


def test_native_invalid_then_edited_prompt(native):
    thread_id, failed, supervisor = record_failure(native)
    native.service.allowed = True
    native.service.fail_inference = False
    native.prompt.write_text(" \n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="empty"):
        supervisor.run_cycle()
    assert load_state(supervisor.state_file).obligations[0].phase == "pending"
    assert not supervisor.client.queue_items(thread_id)
    assert native.service.inference_count == 1
    native.prompt.write_text("Continue edited fixture", encoding="utf-8")
    assert supervisor.run_cycle().dispatched == 1
    assert native.wait_turn(thread_id, after=failed["id"])["status"] == "completed"
    assert native.service.user_messages[-1] == "Continue edited fixture"
    assert_no_duplicates(native, thread_id, 2)


@pytest.mark.parametrize("accepted", [True, False], ids=["accepted-response-lost", "write-not-accepted"])
def test_native_uncertain_queue_never_blindly_resends(native, accepted):
    thread_id, failed, supervisor = record_failure(native)
    native.service.allowed = True
    native.service.fail_inference = False
    supervisor.client._ws = LostQueueAck(supervisor.client._ws, accepted=accepted)
    with pytest.raises(TransportError, match="Fixture"):
        supervisor.run_cycle()
    assert load_state(supervisor.state_file).obligations[0].phase == "uncertain"
    supervisor.close()
    supervisor = native.supervisor()
    if accepted:
        assert native.wait_turn(thread_id, after=failed["id"])["status"] == "completed"
        assert native.service.user_messages[-1] == "Continue"
        assert_no_duplicates(native, thread_id, 2)
    else:
        supervisor.config = replace(supervisor.config, dispatch_recovery_seconds=0)
        for _ in range(2):
            result = supervisor.run_cycle()
            assert result.dispatched == 0 and len(result.warnings) == 1
        assert native.owner.latest_turn(thread_id)["id"] == failed["id"]
        assert native.service.inference_count == 1
        assert load_state(supervisor.state_file).obligations[0].phase == "uncertain"
        assert not native.service.errors
