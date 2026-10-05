"""Native restart/identity probes with synthetic DPAPI-encrypted queue records."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "integration"), str(ROOT / "scripts"), str(Path(__file__).parent)]
import native_support
from codex_auto_continuer.appserver import RpcError
from codex_auto_continuer.errors import TransportError
from probe_interception import TimingService, history
from release import dpapi

RESULTS = {}


@pytest.fixture
def native(monkeypatch):
    monkeypatch.setattr(native_support, "Service", TimingService)
    with native_support.NativeFixture(ROOT, os.environ["CAC_DURABILITY_CODEX"]) as fixture:
        fixture.service.fail_inference = False
        yield fixture


def encrypted_write(path, value):
    encrypted = dpapi(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    with path.open("wb") as stream:
        stream.write(encrypted)
        stream.flush()
        os.fsync(stream.fileno())
    assert b"Synthetic held" not in path.read_bytes()


def fresh_process_read(native, journal):
    child = subprocess.run([sys.executable, str(Path(__file__)), "--read", str(journal)],
        env=native.env, cwd=native.home, capture_output=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW)
    assert child.returncode == 0, "Fresh-process DPAPI decrypt failed"
    return json.loads(child.stdout)


class DeleteFault(native_support.LostQueueAck):
    def send_text(self, data):
        message = json.loads(data)
        if message.get("method") == "thread/queue/delete":
            self.request_id = message["id"]
            if not self.accepted:
                self.websocket.close()
                raise TransportError("Synthetic disconnect before deletion")
        self.websocket.send_text(data)


@pytest.mark.parametrize("phase", ["saved-before-delete", "delete-not-sent", "delete-accepted-ack-lost"])
def test_restart_reconciles_durable_record(native, phase):
    thread = native.owner.request("thread/start", {"cwd": str(native.home),
        "approvalPolicy": "never", "sandbox": "read-only",
        "baseInstructions": "Do not use tools. Reply CAC_FIXTURE_OK."})["thread"]
    thread_id = thread["id"]
    native.service.arm()
    native.start_turn(thread_id, "Synthetic initial task")
    assert native.service.entered.wait(5)
    key = "synthetic-journal-message"
    item = native.owner.queue_add(thread_id, "Synthetic held request", key)["queuedSubmission"]
    journal = native.home / "held-input.dpapi"
    encrypted_write(journal, {"phase": "saved", "items": [item]})
    client = native.client(native.owner_socket)
    if phase != "saved-before-delete":
        client._ws = DeleteFault(client._ws, accepted=phase == "delete-accepted-ack-lost")
        with pytest.raises(TransportError):
            client.queue_delete(thread_id, item["id"])
    recovered = fresh_process_read(native, journal)
    assert recovered["items"] == [item]
    fresh = native.client(native.owner_socket)
    pending = fresh.queue_items(thread_id)
    _, consumed = history(fresh, thread_id)
    assert key not in consumed
    if phase == "delete-accepted-ack-lost":
        assert not pending
    else:
        assert [p["clientUserMessageId"] for p in pending] == [key]
        assert fresh.queue_delete(thread_id, item["id"])
    native.service.release.set()
    native.wait_turn(thread_id)
    restored = fresh.request("thread/queue/add", {"threadId": thread_id,
        "input": recovered["items"][0]["input"], "clientUserMessageId": key})["queuedSubmission"]
    native.wait_turn(thread_id, after=native.turns(thread_id)[0]["id"])
    _, consumed = history(fresh, thread_id)
    assert consumed.count(key) == 1
    assert restored["input"] == item["input"]
    corrupted = bytearray(journal.read_bytes())
    corrupted[-1] ^= 1
    with pytest.raises(RuntimeError):
        dpapi(bytes(corrupted), decrypt=True)
    RESULTS[phase] = {"freshProcessDecrypted": True, "inputRoundTripExact": True,
        "originalStillQueued": bool(pending), "finalConsumedMatches": 1,
        "corruptionRejected": True, "duplicateReplay": False}


def test_lost_replay_ack_uses_identity_not_prompt_equality(native):
    thread_id, initial = native.start_thread("Continue")
    key = "synthetic-replay-identity"
    item = {"input": [{"type": "text", "text": "Continue", "text_elements": []}],
        "clientUserMessageId": key}
    journal = native.home / "replay.dpapi"
    encrypted_write(journal, {"phase": "release-requested", "items": [item]})
    client = native.client(native.owner_socket)
    client._ws = native_support.LostQueueAck(client._ws, accepted=True)
    with pytest.raises(TransportError):
        client.queue_add(thread_id, "Continue", key)
    native.wait_turn(thread_id, after=initial["id"])
    fresh = native.client(native.owner_socket)
    saved = fresh_process_read(native, journal)
    turns, consumed = history(fresh, thread_id)
    assert consumed.count(saved["items"][0]["clientUserMessageId"]) == 1
    assert len(turns) == 2 and not fresh.queue_items(thread_id)
    RESULTS["lostReplayAck"] = {"sameTextTurns": 2, "matchingClientIds": 1,
        "automaticRetry": False, "literalContinue": True}


def test_local_attachment_is_snapshotted_and_survives_delete(native):
    thread = native.owner.request("thread/start", {"cwd": str(native.home),
        "approvalPolicy": "never", "sandbox": "read-only",
        "baseInstructions": "Do not use tools. Reply CAC_FIXTURE_OK."})["thread"]
    native.service.arm()
    native.start_turn(thread["id"], "Synthetic initial task")
    assert native.service.entered.wait(5)
    image = native.home / "synthetic.png"
    image.write_bytes((ROOT / "src/codex_auto_continuer/assets/monitoring.png").read_bytes())
    original = [{"type": "text", "text": "Synthetic held image", "text_elements": []},
        {"type": "localImage", "path": str(image)}]
    queued = native.owner.request("thread/queue/add", {"threadId": thread["id"],
        "input": original, "clientUserMessageId": "synthetic-attachment"})["queuedSubmission"]
    journal = native.home / "image.dpapi"
    encrypted_write(journal, queued)
    assert native.owner.queue_delete(thread["id"], queued["id"])
    restored = fresh_process_read(native, journal)
    saved_image = restored["input"][1]
    assert saved_image["type"] == "image" and saved_image["url"].startswith("data:image/")
    replay = native.owner.request("thread/queue/add", {"threadId": thread["id"],
        "input": restored["input"], "clientUserMessageId": "synthetic-attachment"})["queuedSubmission"]
    assert replay["input"] == restored["input"]
    assert native.owner.queue_delete(thread["id"], replay["id"])
    native.service.release.set()
    native.wait_turn(thread["id"])
    RESULTS["attachment"] = {"nativeSnapshotEmbedsImage": True,
        "encryptedFreshProcessRoundTrip": True, "restoredQueueInputExact": True,
        "attachmentInference": False}


class StdioClient:
    def __init__(self, native):
        self.messages = queue.Queue()
        self.notes = []
        self.sequence = 0
        stderr = native.stack.enter_context((native.home / "stdio.stderr").open("wb"))
        self.process = subprocess.Popen([native.binary, "app-server"], cwd=native.home,
            env=native.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW)
        native.stack.callback(self.close)
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()
        self.request("initialize", {"clientInfo": {"name": "cac_isolated_stdio_probe", "version": "0.1"},
            "capabilities": {"experimentalApi": True}})
        self.process.stdin.write(b'{"method":"initialized"}\n')
        self.process.stdin.flush()

    def read(self):
        for line in self.process.stdout:
            self.messages.put(json.loads(line))
        self.messages.put(None)

    def request(self, method, params):
        self.sequence += 1
        identity = self.sequence
        self.process.stdin.write((json.dumps({"id": identity, "method": method, "params": params}) + "\n").encode())
        self.process.stdin.flush()
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            reply = self.messages.get(timeout=max(0.001, deadline - time.monotonic()))
            assert reply is not None, "Isolated stdio owner exited"
            if "method" in reply:
                assert "id" not in reply, "Unexpected approval/input request"
                self.notes.append(reply)
                continue
            assert reply["id"] == identity
            assert "error" not in reply, f"Synthetic stdio RPC rejected: {method}"
            return reply["result"]
        raise AssertionError("Isolated stdio RPC exceeded 12 seconds")

    def close(self):
        if self.process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        self.process.wait(timeout=5)
        self.reader.join(3)
        assert not self.reader.is_alive()
        self.process.stdin.close()
        self.process.stdout.close()


def test_stdio_owner_does_not_expose_same_owner_event_connection(native):
    owner = StdioClient(native)
    thread = owner.request("thread/start", {"cwd": str(native.home),
        "approvalPolicy": "never", "sandbox": "read-only",
        "baseInstructions": "Do not use tools. Reply CAC_FIXTURE_OK."})["thread"]
    native.service.arm()
    owner.request("turn/start", {"threadId": thread["id"],
        "input": [{"type": "text", "text": "Synthetic stdio task"}]})
    assert native.service.entered.wait(5)
    peer = native.client()
    with pytest.raises(RpcError) as failure:
        peer.resume_thread(thread["id"])
    assert failure.value.is_active_writer(thread["id"])
    queued = owner.request("thread/queue/add", {"threadId": thread["id"],
        "input": [{"type": "text", "text": "Synthetic stdio queued task"}],
        "clientUserMessageId": "synthetic-stdio-queued"})["queuedSubmission"]
    owner.request("account/read", {})
    assert any(n["method"] == "thread/queue/changed" for n in owner.notes)
    assert [p["id"] for p in peer.queue_items(thread["id"])] == [queued["id"]]
    assert not any(n["method"] == "thread/queue/changed" for n in peer.notifications)
    assert peer.queue_delete(thread["id"], queued["id"])
    native.service.release.set()
    deadline = time.monotonic() + 5
    while peer.latest_turn(thread["id"])["status"] == "inProgress":
        assert time.monotonic() < deadline
        time.sleep(0.02)
    _, consumed = history(peer, thread["id"])
    assert "synthetic-stdio-queued" not in consumed
    RESULTS["stdioOwner"] = {"ownerQueueNotification": True, "peerQueueNotification": False,
        "peerResumeRejectedActiveWriter": True, "peerPolledAndRemovedWhileBusy": True,
        "sameOwnerTransport": "Exclusive child stdin/stdout, not an additional local socket"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", type=Path)
    parser.add_argument("--read", type=Path)
    args = parser.parse_args()
    if args.read:
        sys.stdout.buffer.write(dpapi(args.read.read_bytes(), decrypt=True))
        return 0
    if not args.codex:
        parser.error("--codex is required unless --read is supplied")
    os.environ["CAC_DURABILITY_CODEX"] = str(args.codex.resolve(strict=True))
    return pytest.main([str(Path(__file__)), "-q", "-s", "--tb=short"])


def teardown_module():
    Path(__file__).with_name("DURABILITY.json").write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")
    print("DURABILITY_RESULTS=" + json.dumps(RESULTS, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
