"""Measure native queue interception races in disposable homes, never real chats."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import threading
import time

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "integration"), str(ROOT / "scripts")]
import native_support
from codex_auto_continuer.codex import codex_version
from codex_auto_continuer.errors import TransportError
from release import dpapi

RESULTS = json.loads(os.environ.get("CAC_INTERCEPT_METADATA", "{}"))
TRIALS = int(os.environ.get("CAC_INTERCEPT_TRIALS", "10"))
ENCRYPTED = os.environ.get("CAC_INTERCEPT_ENCRYPTED") == "1"


class TimingService(native_support.Service):
    def __init__(self):
        super().__init__()
        self.arm_next = False
        self.entered = threading.Event()
        self.release = threading.Event()

    def arm(self):
        self.entered.clear()
        self.release.clear()
        self.arm_next = True

    def handler(self):
        parent = super().handler()
        service = self

        class Handler(parent):
            def reply(self, status, body, content_type="application/json"):
                if self.path == "/v1/responses" and service.arm_next:
                    service.arm_next = False
                    service.entered.set()
                    if not service.release.wait(15):
                        service.errors.append("Initial response setup gate exceeded 15 seconds")
                try:
                    super().reply(status, body, content_type)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    # Fixture teardown can terminate a held native inference connection.
                    pass

        return Handler

    def __exit__(self, *args):
        self.release.set()
        super().__exit__(*args)


@pytest.fixture
def native(monkeypatch):
    monkeypatch.setattr(native_support, "Service", TimingService)
    with native_support.NativeFixture(ROOT, os.environ["CAC_INTERCEPT_CODEX"]) as fixture:
        fixture.service.fail_inference = False
        yield fixture


def history(client, thread_id):
    turns = client.request("thread/turns/list", {"threadId": thread_id, "limit": 100,
        "sortDirection": "asc", "itemsView": "full"})["data"]
    ids = [item.get("clientId") for turn in turns for item in turn["items"]
        if item["type"] == "userMessage"]
    return turns, ids


class Capture:
    def __init__(self, client, thread_id, journal, *, events, delay_ms):
        self.client = client
        self.thread_id = thread_id
        self.journal = journal
        self.events = events
        self.delay_ms = delay_ms
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.saved = {}
        self.errors = []
        self.thread = threading.Thread(target=self.run, daemon=True)

    def capture(self):
        for item in self.client.queue_items(self.thread_id):
            key = item["clientUserMessageId"]
            if key in self.saved:
                continue
            record = {"item": item, "observed": time.perf_counter()}
            # Persist the entire synthetic input before deletion, including a real fsync.
            payload = json.dumps(item).encode("utf-8")
            if ENCRYPTED:
                payload = dpapi(payload)
            with self.journal.open("ab") as stream:
                stream.write(len(payload).to_bytes(4, "little") + payload)
                stream.flush()
                os.fsync(stream.fileno())
            if self.delay_ms:
                time.sleep(self.delay_ms / 1000)
            record["deleted"] = self.client.queue_delete(self.thread_id, item["id"])
            record["finished"] = time.perf_counter()
            self.saved[key] = record

    def run(self):
        try:
            self.capture()
            self.ready.set()
            if not self.events:
                while not self.stop.wait(0.01):
                    self.capture()
                return
            while not self.stop.is_set():
                self.client._ws.begin_request()
                note = json.loads(self.client._ws.recv_text())
                if "id" in note:
                    raise AssertionError("Unexpected response/request on exclusive event connection")
                if note.get("method") == "thread/queue/changed":
                    self.capture()
                    buffered = list(self.client.notifications)
                    self.client.notifications.clear()
                    if any(n.get("method") == "thread/queue/changed" for n in buffered):
                        self.capture()
        except (TransportError, OSError) as error:
            if not self.stop.is_set():
                self.errors.append(type(error).__name__)
        except BaseException as error:
            self.errors.append(f"{type(error).__name__}: {error}")
        finally:
            self.ready.set()

    def close(self):
        self.stop.set()
        self.client.close()
        self.thread.join(3)
        assert not self.thread.is_alive(), "Capture worker did not stop"
        assert not self.errors, self.errors


def settle(client, thread_id, ids):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        turns, consumed = history(client, thread_id)
        queue = client.queue_items(thread_id)
        if not queue and all(t["status"] in {"completed", "failed"} for t in turns):
            # Read once more after a scheduling interval: do not mistake delayed persistence for absence.
            time.sleep(0.04)
            turns, consumed = history(client, thread_id)
            return {key: consumed.count(key) for key in ids}
        time.sleep(0.02)
    raise AssertionError("Native race did not settle within five seconds")


@pytest.mark.parametrize("mode", ["owner-events", "peer-poll"])
@pytest.mark.parametrize("timing,delay_ms", [
    ("busy-250ms", 0), ("completion-boundary", 0), ("idle", 0),
    ("quota-boundary", 0), ("completion-boundary", 25), ("busy-250ms", 25),
])
def test_capture_race(native, mode, timing, delay_ms):
    samples = []
    for index in range(TRIALS):
        thread = native.owner.request("thread/start", {"cwd": str(native.home),
            "approvalPolicy": "never", "sandbox": "read-only",
            "baseInstructions": "Do not use tools. Reply CAC_FIXTURE_OK."})["thread"]
        thread_id = thread["id"]
        native.service.fail_inference = timing == "quota-boundary"
        native.service.arm()
        native.start_turn(thread_id, "Synthetic initial task")
        assert native.service.entered.wait(5)
        if timing == "idle":
            native.service.release.set()
            native.wait_turn(thread_id)
        observer = native.client(native.owner_socket if mode == "owner-events" else native.socket)
        if mode == "owner-events":
            observer.resume_thread(thread_id)
            observer.notifications.clear()
        capture = Capture(observer, thread_id, native.home / f"journal-{index}.jsonl",
            events=mode == "owner-events", delay_ms=delay_ms)
        capture.thread.start()
        assert capture.ready.wait(5)
        timer = None
        try:
            if timing != "idle":
                seconds = 0.25 if timing == "busy-250ms" else 0
                timer = threading.Timer(seconds, native.service.release.set)
                timer.start()
            started = time.perf_counter()
            key = f"synthetic-race-{index}"
            native.owner.queue_add(thread_id, "Synthetic queued task", key)
            counts = settle(native.owner, thread_id, [key])
        finally:
            native.service.release.set()
            if timer:
                timer.join(1)
            capture.close()
        record = capture.saved.get(key)
        consumed = counts[key]
        assert consumed in (0, 1), "Native queue duplicated the synthetic input"
        if consumed == 0:
            assert record and record["deleted"], "Input disappeared without capture or consumption"
        persisted = []
        if capture.journal.exists():
            with capture.journal.open("rb") as stream:
                while header := stream.read(4):
                    assert len(header) == 4
                    payload = stream.read(int.from_bytes(header, "little"))
                    persisted.append(json.loads(dpapi(payload, decrypt=True) if ENCRYPTED else payload))
        assert bool(persisted) == bool(record)
        if record:
            assert persisted == [record["item"]]
        samples.append({"consumed": bool(consumed), "observed": bool(record),
            "deleteAccepted": bool(record and record["deleted"]),
            "observedMs": round((record["observed"] - started) * 1000, 3) if record else None,
            "deleteMs": round((record["finished"] - started) * 1000, 3) if record else None})
    observed = [s["observedMs"] for s in samples if s["observed"]]
    RESULTS[f"{mode}/{timing}/delay-{delay_ms}ms"] = {"trials": TRIALS,
        "intercepted": sum(not s["consumed"] for s in samples),
        "consumed": sum(s["consumed"] for s in samples),
        "acceptedDeleteButConsumed": sum(s["deleteAccepted"] and s["consumed"] for s in samples),
        "medianObservedMs": round(statistics.median(observed), 3) if observed else None,
        "samples": samples}


def test_observer_offline_then_reconciliation(native):
    thread_id, initial = native.start_thread()
    key = "synthetic-offline-input"
    queued = native.owner.queue_add(thread_id, "Synthetic task while observer offline", key)["queuedSubmission"]
    native.wait_turn(thread_id, after=initial["id"])
    peer = native.client()
    turns, ids = history(peer, thread_id)
    assert ids.count(key) == 1
    assert not peer.queue_delete(thread_id, queued["id"])
    assert not peer.queue_items(thread_id)
    RESULTS["offline"] = {"consumedMatches": 1, "deleteAccepted": False,
        "replayRequired": False, "turns": len(turns)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--select", help="Optional pytest -k expression for a targeted follow-up")
    parser.add_argument("--output", default="RESULTS.json", help="JSON basename within this audit folder")
    parser.add_argument("--encrypted", action="store_true", help="DPAPI-encrypt each record before fsync/deletion")
    args = parser.parse_args()
    if not 1 <= args.trials <= 100:
        parser.error("--trials must be between 1 and 100")
    if Path(args.output).name != args.output or not args.output.endswith(".json"):
        parser.error("--output must be a JSON basename, not a path")
    binary = args.codex.resolve(strict=True)
    metadata = {"runId": time.time_ns(), "environment": {"version": codex_version(str(binary), 10),
        "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "trialsPerCell": args.trials,
        "pollSeconds": 0.01, "responseSetupGateSeconds": 15, "settleSeconds": 5,
        "durableWriteBeforeDelete": True, "encryptedJournal": args.encrypted,
        "replayedInputs": 0, "selection": args.select}}
    os.environ["CAC_INTERCEPT_CODEX"] = str(binary)
    os.environ["CAC_INTERCEPT_TRIALS"] = str(args.trials)
    os.environ["CAC_INTERCEPT_METADATA"] = json.dumps(metadata)
    os.environ["CAC_INTERCEPT_OUTPUT"] = args.output
    os.environ["CAC_INTERCEPT_ENCRYPTED"] = "1" if args.encrypted else "0"
    pytest_args = [str(Path(__file__)), "-q", "-s", "--tb=short"]
    if args.select:
        pytest_args += ["-k", args.select]
    result = pytest.main(pytest_args)
    report = Path(__file__).with_name(args.output)
    collected = json.loads(report.read_text(encoding="utf-8"))
    assert collected["runId"] == metadata["runId"], "Results are not from this invocation"
    collected["pytestExit"] = result
    report.write_text(json.dumps(collected, indent=2) + "\n", encoding="utf-8")
    return result


def teardown_module():
    Path(__file__).with_name(os.environ.get("CAC_INTERCEPT_OUTPUT", "RESULTS.json")).write_text(
        json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")
    print("INTERCEPTION_RESULTS=" + json.dumps({k: {x: y for x, y in v.items() if x != "samples"}
        if isinstance(v, dict) else v for k, v in RESULTS.items()}, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
