"""Isolated native queue/history/cancellation probes; never use the user's Codex home."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "integration")]
import native_support
from codex_auto_continuer.appserver import RpcError
from codex_auto_continuer.codex import codex_version
from codex_auto_continuer.errors import TransportError
from native_support import LostQueueAck

RESULTS = {}


class GatedService(native_support.Service):
    def __init__(self):
        super().__init__()
        self.block_next = False
        self.blocked = threading.Event()
        self.release = threading.Event()

    def arm(self):
        self.blocked.clear()
        self.release.clear()
        self.block_next = True

    def handler(self):
        parent = super().handler()
        service = self

        class Handler(parent):
            def reply(self, status, body, content_type="application/json"):
                if self.path == "/v1/responses" and service.block_next:
                    service.block_next = False
                    service.blocked.set()
                    if not service.release.wait(15):
                        service.errors.append("Synthetic inference gate timed out")
                try:
                    super().reply(status, body, content_type)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    # Cancelling the native turn closes its synthetic HTTP stream.
                    pass

        return Handler

    def __exit__(self, *args):
        self.release.set()
        super().__exit__(*args)


@pytest.fixture
def native(monkeypatch):
    monkeypatch.setattr(native_support, "Service", GatedService)
    with native_support.NativeFixture(ROOT, os.environ["CAC_QUEUE_PROBE_CODEX"]) as fixture:
        yield fixture


def wait(predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("Synthetic queue probe did not reach its expected state")


def full_turns(client, thread_id):
    return client.request("thread/turns/list", {"threadId": thread_id, "limit": 100,
        "sortDirection": "asc", "itemsView": "full"})["data"]


def user_items(turns):
    return [item for turn in turns for item in turn["items"] if item["type"] == "userMessage"]


def text(item):
    return "".join(part.get("text", "") for part in item["content"])


def rpc_outcome(client, method, params):
    try:
        result = client.request(method, params)
    except RpcError as error:
        return {"accepted": False, "code": error.error.get("code")}
    return {"accepted": True, "resultKeys": sorted(result)}


def consumed(native, prompt="Synthetic consumed follow-up"):
    thread_id, failed = native.start_thread()
    native.assert_quota_failure(failed)
    native.service.arm()
    queued = native.owner.queue_add(thread_id, prompt, "probe-consumed-message")["queuedSubmission"]
    assert native.service.blocked.wait(10), "Queued input did not reach synthetic inference"
    active = wait(lambda: native.owner.latest_turn(thread_id))
    assert active["id"] != failed["id"] and active["status"] == "inProgress"
    return thread_id, queued, active


def interrupt(native, thread_id, active, controller=None):
    controller = controller or native.owner
    assert controller.request("turn/interrupt", {"threadId": thread_id, "turnId": active["id"]}) == {}
    native.service.release.set()
    wait(lambda: native.owner.latest_turn(thread_id)["status"] == "interrupted")


def test_history_identity_and_cross_owner_controls(native):
    same = "Identical synthetic input"
    thread_id, first = native.start_thread(same)
    native.assert_quota_failure(first)
    native.service.arm()
    queued = native.owner.queue_add(thread_id, same, "probe-consumed-message")["queuedSubmission"]
    assert native.service.blocked.wait(10)
    active = native.owner.latest_turn(thread_id)
    peer = native.client()
    owner_items = user_items(full_turns(native.owner, thread_id))
    peer_items = user_items(full_turns(peer, thread_id))
    owner_matches = [item for item in owner_items if text(item) == same]
    peer_matches = [item for item in peer_items if text(item) == same]
    outcome = rpc_outcome(peer, "turn/interrupt", {"threadId": thread_id, "turnId": active["id"]})
    assert not outcome["accepted"]
    assert native.owner.latest_turn(thread_id)["status"] == "inProgress"
    deleted = peer.queue_delete(thread_id, queued["id"])
    assert deleted is False
    RESULTS["consumedHistory"] = {"ownerVerbatimMatches": len(owner_matches),
        "peerVerbatimMatches": len(peer_matches),
        "ownerClientIdMatches": sum(item.get("clientId") == queued["clientUserMessageId"] for item in owner_items),
        "peerClientIdMatches": sum(item.get("clientId") == queued["clientUserMessageId"] for item in peer_items),
        "distinctMatchingIds": len({item["id"] for item in owner_matches}),
        "userItemKeys": sorted(owner_matches[-1]),
        "crossOwnerInterrupt": outcome, "deleteConsumedEntry": deleted}
    assert len(owner_matches) == 2 and len({item["id"] for item in owner_matches}) == 2
    assert RESULTS["consumedHistory"]["ownerClientIdMatches"] == 1
    assert RESULTS["consumedHistory"]["peerClientIdMatches"] == 1
    interrupt(native, thread_id, active)


def test_same_owner_interruption_holds_queue(native):
    thread_id, _, active = consumed(native)
    saved = native.owner.queue_add(thread_id, "Synthetic waiting follow-up", "probe-waiting-message")["queuedSubmission"]
    controller = native.client(native.owner_socket)
    interrupt(native, thread_id, active, controller)
    count = native.service.inference_count
    # Cross an external-queue watcher's actual ten-second interval.
    time.sleep(11)
    items = native.owner.queue_items(thread_id)
    assert [item["id"] for item in items] == [saved["id"]]
    assert native.service.inference_count == count
    history = user_items(full_turns(native.owner, thread_id))
    assert any(text(item) == "Synthetic consumed follow-up" for item in history)
    RESULTS["interruption"] = {"sameOwnerSecondConnectionAccepted": True,
        "queuedAfterElevenSeconds": len(items), "newInferenceAfterInterrupt": 0,
        "consumedInputStillInHistory": True}


def test_removal_endpoints_are_not_available(native):
    thread_id, _, active = consumed(native)
    interrupt(native, thread_id, active)
    before = full_turns(native.owner, thread_id)
    outcomes = {}
    for method, params in (
        ("thread/rollback", {"threadId": thread_id, "numTurns": 1}),
        ("turn/delete", {"threadId": thread_id, "turnId": active["id"]}),
        ("item/delete", {"threadId": thread_id, "itemId": "probe-consumed-message"}),
    ):
        outcomes[method] = rpc_outcome(native.owner, method, params)
        assert not outcomes[method]["accepted"]
    assert full_turns(native.owner, thread_id) == before
    RESULTS["historyRemoval"] = outcomes


def test_selected_continue_can_precede_remaining_queue_on_owner(native):
    thread_id, _, active = consumed(native)
    later = native.owner.queue_add(thread_id, "Synthetic later follow-up", "probe-later-message")["queuedSubmission"]
    interrupt(native, thread_id, active)
    continuation = native.owner.queue_add(thread_id, "Continue", "probe-continue-message")["queuedSubmission"]
    peer = native.client()
    denied = rpc_outcome(peer, "thread/queue/start", {"threadId": thread_id,
        "queuedSubmissionId": continuation["id"]})
    assert not denied["accepted"]
    assert [item["id"] for item in peer.queue_items(thread_id)] == [later["id"], continuation["id"]]
    native.service.allowed = True
    native.service.fail_inference = False
    response = native.owner.request("thread/queue/start", {"threadId": thread_id,
        "queuedSubmissionId": continuation["id"]})
    wait(lambda: len(native.turns(thread_id)) == 4 and
        native.owner.latest_turn(thread_id)["status"] == "completed")
    assert native.service.user_messages == ["Fixture initial task", "Synthetic consumed follow-up",
        "Continue", "Synthetic later follow-up"]
    assert not peer.queue_items(thread_id)
    RESULTS["selectedStart"] = {"crossOwnerStart": denied, "ownerStartAccepted": True,
        "responseKeys": sorted(response), "continueBeforeWaitingFollowup": True,
        "continuationPromptExact": native.service.user_messages[2] == "Continue",
        "totalTurns": len(native.turns(thread_id)), "remainingQueue": 0}


class LostDeleteAck(LostQueueAck):
    def send_text(self, data):
        message = json.loads(data)
        if message.get("method") == "thread/queue/delete":
            self.request_id = message["id"]
        self.websocket.send_text(data)


def test_lost_delete_response_can_be_reconciled_after_owner_pause(native):
    thread_id, _, active = consumed(native)
    later = native.owner.queue_add(thread_id, "Synthetic held input", "probe-held-message")["queuedSubmission"]
    interrupt(native, thread_id, active)
    peer = native.client()
    peer._ws = LostDeleteAck(peer._ws, accepted=True)
    with pytest.raises(TransportError):
        peer.queue_delete(thread_id, later["id"])
    fresh = native.client()
    assert not fresh.queue_items(thread_id)
    assert not any(text(item) == "Synthetic held input" for item in user_items(full_turns(fresh, thread_id)))
    count = native.service.inference_count
    replayed = fresh.queue_add(thread_id, "Synthetic held input", "probe-replayed-held-message")["queuedSubmission"]
    assert replayed["id"] != later["id"]
    assert native.service.inference_count == count
    RESULTS["lostDeleteAck"] = {"responseLost": True, "queueAbsent": True,
        "inputAbsentFromHistory": True, "savedInputRestoredToPausedQueue": True}


def test_fork_before_consumed_turn_excludes_input_without_editing_source(native):
    thread_id, _, active = consumed(native)
    later = native.owner.queue_add(thread_id, "Synthetic fork follow-up", "probe-fork-later")["queuedSubmission"]
    interrupt(native, thread_id, active)
    peer = native.client()
    original = full_turns(peer, thread_id)
    fork = peer.request("thread/fork", {"threadId": thread_id, "beforeTurnId": active["id"],
        "excludeTurns": False, "deferGoalContinuation": True})["thread"]
    fork_id = fork["id"]
    assert fork_id != thread_id
    fork_history = full_turns(peer, fork_id)
    assert len(fork_history) == 1
    assert not any(text(item) == "Synthetic consumed follow-up" for item in user_items(fork_history))
    native.service.fail_inference = False
    native.service.allowed = True
    for prompt in ("Continue", "Synthetic consumed follow-up", "Synthetic fork follow-up"):
        started = peer.request("turn/start", {"threadId": fork_id,
            "input": [{"type": "text", "text": prompt}]})["turn"]
        wait(lambda: peer.latest_turn(fork_id)["id"] == started["id"] and
            peer.latest_turn(fork_id)["status"] == "completed")
    assert full_turns(peer, thread_id) == original
    assert [item["id"] for item in peer.queue_items(thread_id)] == [later["id"]]
    assert native.service.user_messages[-3:] == ["Continue", "Synthetic consumed follow-up", "Synthetic fork follow-up"]
    RESULTS["fork"] = {"newThread": True, "sourceHistoryUnchanged": True,
        "consumedInputExcludedInitially": True, "continueThenFollowups": True,
        "forkTurns": len(full_turns(peer, fork_id)), "sourceQueueStillHeld": 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", type=Path, required=True)
    args = parser.parse_args()
    binary = args.codex.resolve(strict=True)
    print("Native queue probe version:", codex_version(str(binary), 10))
    os.environ["CAC_QUEUE_PROBE_CODEX"] = str(binary)
    return pytest.main([str(Path(__file__)), "-q", "-s", "--tb=short"])


def teardown_module():
    print("QUEUE_PROBE_RESULTS=" + json.dumps(RESULTS, sort_keys=True))
    Path(__file__).with_name("RESULTS.json").write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
