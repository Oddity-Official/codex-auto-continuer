"""Real owner capture, DPAPI restart and ordered replay against unmodified Codex."""
from dataclasses import replace
import json
import shutil
import threading
import time

import pytest

import native_support
from codex_auto_continuer.holding import Holding, metadata
from codex_auto_continuer.errors import TransportError
from native_support import LostQueueAck


class GatedService(native_support.Service):
    def __init__(self):
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()
        self.gate = True

    def handler(self):
        parent = super().handler()
        service = self
        class Handler(parent):
            def reply(self, status, body, content_type="application/json"):
                if self.path == "/v1/responses" and service.gate:
                    service.gate = False
                    service.entered.set()
                    if not service.release.wait(15):
                        service.errors.append("Holding setup exceeded 15 seconds")
                try:
                    super().reply(status, body, content_type)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass  # Teardown can terminate an intentionally gated response.
        return Handler

    def __exit__(self, *args):
        self.release.set()
        super().__exit__(*args)


def wait_for(predicate, seconds=8, diagnostic=None):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.03)
    detail = f": {diagnostic()}" if diagnostic is not None else ""
    raise AssertionError("Holding state did not settle before its deadline" + detail)


@pytest.mark.parametrize("quota,lost_release_ack", [(False, False), (True, False), (False, True)])
def test_native_holder_restart_continue_then_ordered_inputs(codex_binary, monkeypatch, quota, lost_release_ack):
    monkeypatch.setattr(native_support, "Service", GatedService)
    with native_support.NativeFixture(native_support.Path(__file__).resolve().parents[1], codex_binary) as native:
        native.service.fail_inference = quota
        native.service.allowed = not quota
        thread = native.owner.request("thread/start", {"cwd": str(native.home),
            "approvalPolicy": "never", "sandbox": "read-only",
            "baseInstructions": "Do not use tools. Reply CAC_FIXTURE_OK."})["thread"]
        identity = thread["id"]
        initial = native.start_turn(identity, "Synthetic held-input initial task")
        assert native.service.entered.wait(5)
        supervisor = native.supervisor()
        supervisor.client.close()
        supervisor.client = native.client(native.owner_socket)
        supervisor.config = replace(supervisor.config, queue_holding=True)
        supervisor.run_cycle()
        watcher = supervisor.holding.watchers[identity]
        assert watcher.ready.wait(5)
        assert not supervisor.holding.issues, supervisor.holding.issues
        for index in range(2):
            input = [{"type": "text", "text": f"PRIVATE_SYNTHETIC_FOLLOW_UP_{index}", "text_elements": []}]
            if index == 1:
                image = native.home / "synthetic-image.png"
                shutil.copyfile(native_support.Path(__file__).resolve().parents[1] / "src/codex_auto_continuer/assets/monitoring-0.png", image)
                input.append({"type": "localImage", "path": str(image)})
            native.owner.queue_add_input(identity, input, f"holding-fixture-{index}")
        wait_for(lambda: len((supervisor.holding.journal.read() or {}).get("records", [])) == 2
            and all(r["phase"] == "held" for r in supervisor.holding.journal.read()["records"]),
            diagnostic=lambda: {"holding": supervisor.holding.report(),
                "phases": [r["phase"] for r in (supervisor.holding.journal.read() or {}).get("records", [])],
                "watcherAlive": watcher.thread.is_alive(), "serviceErrors": native.service.errors,
                "observerFailures": [e for e in native.events() if e["event"] == "holding.observer_failed"],
                "ownerStatus": native.owner.thread_read(identity)["status"]["type"],
                "queued": len(native.owner.queue_items(identity))})
        assert not native.owner.queue_items(identity)
        ciphertext = supervisor.holding.journal.path.read_bytes()
        assert b"PRIVATE_SYNTHETIC" not in ciphertext
        image_input = supervisor.holding.journal.read()["records"][1]["input"][1]
        assert image_input["type"] == "image" and image_input["url"].startswith("data:image/")
        image.unlink()  # Replay must not depend on the deleted original image path.
        native.service.release.set()
        native.wait_turn(identity)
        supervisor.close()
        # A new engine opens encrypted inputs, without relying on the capture worker's RAM.
        supervisor = native.supervisor()
        supervisor.client.close()
        supervisor.client = native.client(native.owner_socket)
        supervisor.config = replace(supervisor.config, queue_holding=True)
        if lost_release_ack:
            supervisor.client._ws = LostQueueAck(supervisor.client._ws, accepted=True)
            with pytest.raises(TransportError):
                supervisor.run_cycle()
            assert supervisor.holding.journal.read()["records"][0]["phase"] == "release_requested"
            supervisor.client.close()
            supervisor.client = native.client(native.owner_socket)
        else:
            supervisor.run_cycle()
        if quota:
            assert len(native.turns(identity)) == 1
            assert len(supervisor.holding.journal.read()["records"]) == 2
            native.service.allowed = True
            native.service.fail_inference = False
            result = supervisor.run_cycle()
            assert result.dispatched == 1
            native.wait_turn(identity, after=initial["id"])
            assert native.service.user_messages[-1] == "Continue"
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                supervisor.run_cycle()
            except TransportError:
                supervisor.client.close()
                supervisor.client = native.client(native.owner_socket)
            if not supervisor.holding.journal.read()["records"]:
                break
            time.sleep(0.08)
        assert not supervisor.holding.journal.read()["records"], supervisor.holding.report()
        ids = metadata(native.owner.full_turns(identity))
        assert all(len(ids[f"holding-fixture-{index}"]) == 1 for index in range(2))
        assert native.service.user_messages == ["Synthetic held-input initial task", *(["Continue"] if quota else []),
            "PRIVATE_SYNTHETIC_FOLLOW_UP_0", "PRIVATE_SYNTHETIC_FOLLOW_UP_1"]
        assert "PRIVATE_SYNTHETIC" not in native.telemetry_file.read_text(encoding="utf-8")
        assert not native.service.errors


def test_foreign_owner_is_explicitly_uncovered(native):
    native.service.fail_inference = False
    identity, _ = native.start_thread()
    holder = Holding(native.data)
    try:
        peer = native.client()
        holder.update(peer, [peer.thread_read(identity)], enabled=True, allowed=True, binary=None, timeout=2)
        report = holder.report()
        assert report["unsupported"] == 1 and report["observedActive"] == 0
        assert report["warnings"] and not holder.journal.path.exists()
    finally:
        holder.close()


def test_native_observer_never_answers_approval(codex_binary, monkeypatch):
    monkeypatch.setattr(native_support, "Service", GatedService)
    with native_support.NativeFixture(native_support.Path(__file__).resolve().parents[1], codex_binary) as native:
        native.service.fail_inference = False
        native.service.output_item = {"type": "function_call", "name": "exec_command", "call_id": "fixture-approval",
            "arguments": json.dumps({"cmd": "Write-Output 'CAC_APPROVAL_FIXTURE'",
                "sandbox_permissions": "require_escalated", "justification": "Synthetic approval routing probe"})}
        identity = native.owner.request("thread/start", {"cwd": str(native.home), "approvalPolicy": "on-request",
            "sandbox": "read-only", "baseInstructions": "Synthetic approval fixture."})["thread"]["id"]
        native.start_turn(identity, "Synthetic approval task")
        assert native.service.entered.wait(5)
        holder = Holding(native.data)
        try:
            holder.update(native.owner, [native.owner.thread_read(identity)], enabled=True, allowed=True, binary=None, timeout=2)
            assert holder.watchers[identity].ready.wait(5)
            native.service.release.set()
            def requested():
                native.owner.request("account/read", {})
                return bool(native.owner.server_requests)
            try:
                wait_for(requested)
            except AssertionError:
                latest = native.owner.latest_turn(identity)
                raise AssertionError(f"Approval not emitted: latest={latest}, tools={native.service.tool_names}")
            wait_for(lambda: bool(holder.issues))
            approval = native.owner.server_requests.popleft()
            assert approval["method"] == "item/commandExecution/requestApproval"
            assert holder.report()["needsAttention"]
            # Only the original interactive fixture client answers. Product CAC never does.
            native.service.output_item = None
            native.owner._ws.send_text(json.dumps({"id": approval["id"], "result": {"decision": "decline"}}))
            assert native.wait_turn(identity)["status"] == "completed"
            assert not native.service.errors
        finally:
            holder.close()
