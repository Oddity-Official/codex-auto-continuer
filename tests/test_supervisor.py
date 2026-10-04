from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from codex_auto_continuer.config import Config, DEFAULT_CONTINUE_PROMPT
from codex_auto_continuer.appserver import RpcError
from codex_auto_continuer.errors import ConfigurationError, ProtocolError, TransportError
from codex_auto_continuer.state import Obligation, State, load_state, save_state
from codex_auto_continuer.compatibility import Compatibility
from codex_auto_continuer.supervisor import (
    Supervisor,
    _is_usage_limit_failure,
    _parse_rate_limits,
    _session_source_label,
    _thread_status,
    observed_interactive_sources,
)


def thread(tid="t", *, updated=1000, status="idle", source=None):
    if source is None: source = {"custom":"chatgpt"}
    s = {"type": status}
    if status == "active": s["activeFlags"] = []
    return {"id":tid,"updatedAt":updated,"status":s,"source":source}


def failed_turn(tid="turn-1"):
    return {"id":tid,"status":"failed","completedAt":1000,"error":{"message":"quota","codexErrorInfo":"usageLimitExceeded"}}


class FakeClient:
    user_agent = "fake/0.160.0"
    thread_subscriptions: set[str]
    def __init__(self, threads=None, turns=None, allowed=False, reset=2000):
        self.threads = list(threads or [])
        self.turns = dict(turns or {})
        self.allowed = allowed
        self.reset = reset
        self.queue = {}
        self.added = []
        self.deleted = []
        self.resume_calls = []
        self.thread_subscriptions = set()
        self.fail_latest_once = set()
    def rate_limits(self):
        return {"ordinaryUsageAllowed":self.allowed,"rateLimits":{"limitId":"codex","primary":{"usedPercent":100 if self.allowed is False else 1,"resetsAt":self.reset}}}
    def thread_list(self, cursor=None, limit=100):
        if cursor is not None: return {"data":[],"nextCursor":None}
        return {"data":self.threads[:limit],"nextCursor":None}
    def latest_turn(self, tid):
        if tid in self.fail_latest_once:
            self.fail_latest_once.remove(tid)
            raise TransportError("transient")
        return self.turns.get(tid)
    def thread_read(self, tid):
        return next((x for x in self.threads if x["id"] == tid), None)
    def queue_items(self, tid): return list(self.queue.get(tid, []))
    def queue_add(self, tid, prompt, client_id):
        item={"id":f"q-{len(self.added)+1}","clientUserMessageId":client_id,"input":[{"type":"text","text":prompt}]}
        self.queue.setdefault(tid,[]).append(item); self.added.append((tid,prompt,client_id)); return {"queuedSubmission":item}
    def queue_delete(self, tid, queue_id):
        items=self.queue.get(tid,[])
        before=len(items); self.queue[tid]=[x for x in items if x.get("id")!=queue_id]
        self.deleted.append((tid,queue_id))
        return len(self.queue[tid]) != before
    def resume_thread(self, tid):
        self.resume_calls.append(tid); self.thread_subscriptions.add(tid)
        obj=next(x for x in self.threads if x["id"]==tid); obj["status"]={"type":"idle"}
        return {"thread":obj}
    def close(self): pass


def supervisor(tmp_path: Path, client: FakeClient, *, cfg=None, clock=lambda:1000.0):
    prompt = tmp_path / "continue-prompt.md"
    if not prompt.exists():
        prompt.write_text(DEFAULT_CONTINUE_PROMPT, encoding="utf-8")
    s=Supervisor(cfg or Config(dispatch_spacing_seconds=0), tmp_path/"state.json", clock=clock, sleep=lambda _:None)
    s.client=client
    s.compatibility = Compatibility(status="certified", reason="Unit-test fixture")
    return s


@pytest.mark.parametrize("clients", [(), ("cli",), ("vscode",), ("desktop",), ("cli", "vscode"),
                                     ("cli", "desktop"), ("vscode", "desktop"), ("vscode", "cli", "desktop")])
def test_client_selection_uses_source_and_originator_without_executor_leakage(tmp_path, clients):
    s = supervisor(tmp_path, FakeClient(), cfg=Config(clients=clients))
    examples = [
        ("cli", "Codex Desktop", "cli"), ("vscode", "VS Code extension", "vscode"),
        ("vscode", "Codex Desktop", "desktop"), ({"custom": "chatgpt"}, None, "desktop"),
        ("exec", "Codex Desktop", None), ({"subAgent": {}}, None, None), ("appServer", None, None),
    ]
    for source, originator, expected in examples:
        metadata = thread(source=source)
        metadata["originator"] = originator
        assert s._scope_accepts(metadata) == (expected in clients if expected else False)


def test_invalid_saved_settings_pause_without_losing_pending_work_then_recover(tmp_path):
    client = FakeClient([thread()], {"t": failed_turn()}, allowed=False)
    s = supervisor(tmp_path, client)
    s.run_cycle()
    original = s.state_file.read_bytes()
    cycles, pauses, reloads = [], [], []
    def reload_settings():
        reloads.append(True)
        if len(reloads) < 3:
            assert s.state_file.read_bytes() == original
            raise ConfigurationError("Incomplete editor save")
        return Config(poll_seconds=1, dispatch_spacing_seconds=0)
    s.connect = lambda: setattr(s, "client", client)
    s.on_cycle = cycles.append
    s.run_forever(lambda: bool(cycles), reload_settings=reload_settings, on_pause=lambda: pauses.append(True))
    assert len(pauses) == 1 and len(reloads) == 3 and len(cycles) == 1
    assert cycles[0].pending == 1 and not client.added


def test_no_selected_clients_does_not_connect_when_no_pending_state(tmp_path):
    s = supervisor(tmp_path, FakeClient(), cfg=Config(clients=()))
    s.close()
    s.connect = lambda: pytest.fail("Disabled client monitoring must not connect")
    cycles = []
    s.on_cycle = cycles.append
    s.run_forever(lambda: bool(cycles))
    assert cycles[0].scanned_threads == 0 and cycles[0].ordinary_usage_allowed is None


def test_usage_limit_is_exact():
    assert _is_usage_limit_failure(failed_turn())
    assert not _is_usage_limit_failure({"id":"x","status":"failed","error":{"codexErrorInfo":"other"}})
    assert not _is_usage_limit_failure({"id":"x","status":"interrupted","error":{"codexErrorInfo":"usageLimitExceeded"}})


def test_undocumented_usage_limit_shape_is_not_accepted():
    turn=failed_turn(); turn["error"]["codexErrorInfo"]={"usageLimitExceeded":{}}
    assert not _is_usage_limit_failure(turn)


def test_rate_limit_permission_not_inferred_from_reset():
    state=_parse_rate_limits({"ordinaryUsageAllowed":None,"rateLimits":{"primary":{"usedPercent":100,"resetsAt":5000}}})
    assert state.ordinary_usage_allowed is None
    assert state.next_reset_at == 5000


def test_detects_obligation_but_does_not_dispatch_before_recovery(tmp_path: Path):
    c=FakeClient([thread()], {"t":failed_turn()}, allowed=False)
    s=supervisor(tmp_path,c)
    result=s.run_cycle()
    assert result.detected==1 and result.dispatched==0 and result.pending==1
    assert not c.added


def test_null_permission_never_dispatches(tmp_path: Path):
    c=FakeClient([thread()], {"t":failed_turn()}, allowed=None)
    s=supervisor(tmp_path,c)
    s.run_cycle(); assert not c.added


def test_dispatches_after_verified_recovery(tmp_path: Path):
    c=FakeClient([thread()], {"t":failed_turn()}, allowed=False)
    s=supervisor(tmp_path,c); s.run_cycle(); c.allowed=True
    result=s.run_cycle()
    assert result.dispatched==1
    assert c.added[0][0]=="t"
    state=load_state(tmp_path/"state.json")
    assert state.obligations[0].phase=="submitted"


def test_manual_progress_cancels_stale_obligation(tmp_path: Path):
    c=FakeClient([thread()], {"t":failed_turn()}, allowed=False)
    s=supervisor(tmp_path,c); s.run_cycle()
    c.turns["t"]={"id":"turn-2","status":"completed","error":None}
    r=s.run_cycle()
    assert r.cancelled==1 and not s.state.obligations and not c.added


def test_active_thread_cancels_pending_obligation(tmp_path: Path):
    ob=Obligation.create("t","turn-1",900,None); save_state(tmp_path/"state.json",State(obligations=[ob]))
    c=FakeClient([thread(status="active")], {"t":failed_turn()}, allowed=True)
    s=supervisor(tmp_path,c)
    r=s.run_cycle(); assert r.cancelled==1 and not c.added


def test_unloaded_thread_resumes_exact_thread_before_queue(tmp_path: Path):
    ob=Obligation.create("t","turn-1",900,None); save_state(tmp_path/"state.json",State(obligations=[ob]))
    c=FakeClient([thread(status="notLoaded")], {"t":failed_turn()}, allowed=True)
    s=supervisor(tmp_path,c); s.run_cycle()
    assert c.resume_calls==["t"] and c.added


def test_system_error_is_not_dispatched(tmp_path: Path):
    ob=Obligation.create("t","turn-1",900,None); save_state(tmp_path/"state.json",State(obligations=[ob]))
    c=FakeClient([thread(status="systemError")], {"t":failed_turn()}, allowed=True)
    s=supervisor(tmp_path,c); r=s.run_cycle()
    assert r.pending==1 and not c.added


def test_two_threads_dispatch_sequentially_and_recheck_limits(tmp_path: Path):
    c=FakeClient([thread("a"),thread("b")], {"a":failed_turn("ta"),"b":failed_turn("tb")}, allowed=False)
    s=supervisor(tmp_path,c); s.run_cycle(); c.allowed=True
    original=c.queue_add
    def add_then_exhaust(*args):
        out=original(*args); c.allowed=False; return out
    c.queue_add=add_then_exhaust
    r=s.run_cycle()
    assert r.dispatched==1 and len(c.added)==1 and len(s.state.obligations)==2


def test_queue_recovery_avoids_duplicate(tmp_path: Path):
    ob=Obligation.create("t","turn-1",900,None); ob.phase="uncertain"; ob.phase_changed_at=800
    save_state(tmp_path/"state.json",State(obligations=[ob]))
    c=FakeClient([thread()], {"t":failed_turn()}, allowed=True)
    c.queue["t"]=[{"id":"existing","clientUserMessageId":ob.client_user_message_id}]
    s=supervisor(tmp_path,c); s.run_cycle()
    assert not c.added
    assert s.state.obligations[0].phase=="submitted"


def test_ambiguous_send_is_isolated_while_other_chats_continue(tmp_path: Path):
    ob=Obligation.create("t","turn-1",900,None); ob.phase="uncertain"; ob.phase_changed_at=800
    save_state(tmp_path/"state.json",State(obligations=[ob]))
    c=FakeClient([thread(), thread("safe")], {"t":failed_turn(), "safe":failed_turn()}, allowed=True)
    s=supervisor(tmp_path,c)
    result = s.run_cycle()
    assert result.dispatched == 1 and len(result.warnings) == 1
    assert c.added[0][0] == "safe"
    assert s.state.by_thread()["t"].phase == "uncertain"
    assert s.run_cycle().dispatched == 0
    assert len(c.added) == 1


def test_recent_scan_does_not_cache_failed_read(tmp_path: Path):
    c=FakeClient([thread()], {"t":failed_turn()}, allowed=False); c.fail_latest_once.add("t")
    s=supervisor(tmp_path,c)
    with pytest.raises(TransportError): s.run_cycle()
    assert s.run_cycle().detected==1


def test_desktop_scope_only_desktop_custom_sources(tmp_path: Path):
    c=FakeClient([
        thread("chat",source={"custom":"chatgpt"}),
        thread("atlas",source={"custom":"atlas"}),
        thread("cli",source="cli"),
        thread("app",source="appServer"),
    ], {x:failed_turn(x) for x in ["chat","atlas","cli","app"]}, allowed=False)
    s=supervisor(tmp_path,c,cfg=Config(clients=("desktop",))); r=s.run_cycle()
    assert r.detected==2
    assert {o.thread_id for o in s.state.obligations}=={"chat","atlas"}


def test_all_interactive_includes_cli_vscode_custom_not_exec(tmp_path: Path):
    cfg=Config(dispatch_spacing_seconds=0)
    c=FakeClient([
        thread("cli",source="cli"),thread("vs",source="vscode"),thread("x",source={"custom":"chatgpt"}),thread("exec",source="exec")
    ], {x:failed_turn(x) for x in ["cli","vs","x","exec"]}, allowed=False)
    s=supervisor(tmp_path,c,cfg=cfg); s.run_cycle()
    assert {o.thread_id for o in s.state.obligations}=={"cli","vs","x"}


def test_unknown_source_fails_loud():
    with pytest.raises(ProtocolError, match="Unknown Codex session source"):
        _session_source_label("magic")


def test_unknown_status_fails_loud():
    with pytest.raises(ProtocolError, match="Unknown Codex thread status"):
        _thread_status({"status":{"type":"surprise"}})


def test_unknown_active_flag_fails_loud():
    with pytest.raises(ProtocolError, match="Unknown Codex active flag"):
        _thread_status({"status":{"type":"active","activeFlags":["mystery"]}})


def test_observed_sources_counts_without_conversation_content():
    c=FakeClient([thread("a",source={"custom":"chatgpt"}),thread("b",source="cli")])
    assert observed_interactive_sources(c)=={"cli":1,"custom:chatgpt":1}


def test_reset_hint_sleep_is_advisory_only(tmp_path: Path):
    c=FakeClient()
    s=supervisor(tmp_path,c,cfg=Config(poll_seconds=30),clock=lambda:1000)
    from codex_auto_continuer.supervisor import CycleResult
    assert s._next_sleep_seconds(CycleResult(pending=1,ordinary_usage_allowed=False,next_reset_at=1005))==5
    assert s._next_sleep_seconds(CycleResult(pending=1,ordinary_usage_allowed=None,next_reset_at=1005))==30


def test_manual_progress_deletes_our_still_queued_submission(tmp_path: Path):
    ob=Obligation.create("t","turn-1",900,None)
    ob.phase="submitted"; ob.phase_changed_at=950; ob.queued_submission_id="q-own"
    save_state(tmp_path/"state.json",State(obligations=[ob]))
    c=FakeClient([thread()], {"t":{"id":"turn-2","status":"completed","error":None}}, allowed=True)
    c.queue["t"]=[
        {"id":"q-own","clientUserMessageId":ob.client_user_message_id},
        {"id":"q-user","clientUserMessageId":"somebody-else"},
    ]
    s=supervisor(tmp_path,c)
    r=s.run_cycle()
    assert r.cancelled==1
    assert c.deleted==[("t","q-own")]
    assert [x["id"] for x in c.queue["t"]]==["q-user"]
    assert not s.state.obligations

def test_nonfinite_updated_timestamp_rejected(tmp_path: Path):
    c=FakeClient([thread(updated=float("nan"))], {"t":failed_turn()}, allowed=False)
    s=supervisor(tmp_path,c)
    with pytest.raises(ProtocolError, match="finite numeric timestamp"):
        s.run_cycle()


def test_scope_change_cancels_existing_out_of_scope_obligation(tmp_path: Path):
    ob=Obligation.create("cli","turn-1",900,None)
    save_state(tmp_path/"state.json",State(obligations=[ob]))
    c=FakeClient([thread("cli",source="cli")], {"cli":failed_turn()}, allowed=False)
    s=supervisor(tmp_path,c,cfg=Config(clients=("desktop",)))
    r=s.run_cycle()
    assert r.cancelled==1 and not s.state.obligations


def test_rate_limits_requires_protocol_rate_limits_object():
    with pytest.raises(ProtocolError, match="required rateLimits object"):
        _parse_rate_limits({"ordinaryUsageAllowed":False})


def test_desktop_originator_is_not_confused_with_vscode_extension(tmp_path):
    desktop = thread("desktop", source="vscode") | {"originator": "Codex Desktop"}
    extension = thread("extension", source="vscode") | {"originator": "codex_vscode"}
    c = FakeClient([desktop, extension], {x: failed_turn(x) for x in ("desktop", "extension")})
    s = supervisor(tmp_path, c, cfg=Config(clients=("desktop",)))
    assert s.run_cycle().detected == 1
    assert s.state.obligations[0].thread_id == "desktop"


def test_prompt_saved_after_start_is_used_and_empty_prompt_never_dispatches(tmp_path):
    from codex_auto_continuer.errors import ConfigurationError
    c = FakeClient([thread()], {"t": failed_turn()}, allowed=False)
    s = supervisor(tmp_path, c)
    s.run_cycle()
    prompt = tmp_path / "continue-prompt.md"
    prompt.write_text("", encoding="utf-8")
    c.allowed = True
    with pytest.raises(ConfigurationError, match="empty"):
        s.run_cycle()
    assert not c.added
    assert s.state.obligations[0].phase == "pending"
    prompt.write_text("Continue with the saved instruction.\n", encoding="utf-8")
    s.run_cycle()
    assert c.added[0][1] == "Continue with the saved instruction.\n"


def test_delivery_observation_survives_restart_and_waits_for_runtime_completion(tmp_path):
    c = FakeClient([thread()], {"t": failed_turn()}, allowed=True)
    s = supervisor(tmp_path, c)
    s.run_cycle()
    assert len(load_state(tmp_path / "state.json").observations) == 1
    c.threads[0]["status"] = {"type": "active", "activeFlags": []}
    c.turns["t"] = {"id": "next", "status": "interrupted"}
    restarted = supervisor(tmp_path, c)
    restarted.run_cycle()
    assert len(restarted.state.observations) == 1
    c.threads[0]["status"] = {"type": "idle"}
    c.turns["t"]["status"] = "completed"
    c.turns["t"]["completedAt"] = 1000
    restarted.run_cycle()
    assert not load_state(tmp_path / "state.json").observations


def test_separate_owner_incomplete_terminal_history_keeps_observation(tmp_path):
    c = FakeClient([thread()], {"t": failed_turn()}, allowed=True)
    supervisor(tmp_path, c).run_cycle()
    c.threads[0]["status"] = {"type": "notLoaded"}
    c.turns["t"] = {"id": "next", "status": "interrupted", "completedAt": None}
    restarted = supervisor(tmp_path, c)
    restarted.run_cycle()
    assert len(load_state(tmp_path / "state.json").observations) == 1
    c.turns["t"].update(status="completed", completedAt=1000)
    restarted.run_cycle()
    assert not load_state(tmp_path / "state.json").observations


def test_recent_metadata_cannot_revive_old_failure(tmp_path):
    now = 100000
    old = failed_turn() | {"completedAt": now - 86401}
    c = FakeClient([thread(updated=now)], {"t": old}, allowed=True)
    s = supervisor(tmp_path, c, clock=lambda: now)
    assert s.run_cycle().detected == 0
    assert not c.added


def test_recorded_obligation_survives_discovery_lookback(tmp_path):
    now = 100000
    ob = Obligation.create("t", "turn-1", 1000, None)
    save_state(tmp_path / "state.json", State(obligations=[ob]))
    c = FakeClient([thread(updated=1000)], {"t": failed_turn()}, allowed=True)
    s = supervisor(tmp_path, c, clock=lambda: now)
    assert s.run_cycle().dispatched == 1


def test_second_granularity_timestamp_cannot_hide_new_failure(tmp_path):
    c = FakeClient([thread()], {"t": {"id": "old", "status": "completed"}})
    s = supervisor(tmp_path, c)
    assert s.run_cycle().detected == 0
    c.turns["t"] = failed_turn()
    assert s.run_cycle().detected == 1


@pytest.mark.parametrize("change", ["quota", "manual"])
def test_resume_revalidates_before_dispatch(tmp_path, change):
    c = FakeClient([thread(status="notLoaded")], {"t": failed_turn()}, allowed=True)
    original = c.resume_thread
    def resume(tid):
        response = original(tid)
        if change == "quota":
            c.allowed = False
        else:
            c.turns[tid] = {"id": "new", "status": "completed"}
        return response
    c.resume_thread = resume
    s = supervisor(tmp_path, c)
    assert s.run_cycle().dispatched == 0
    assert not c.added


@pytest.mark.parametrize("owned", [True, False])
def test_other_server_ownership_queues_but_unrelated_resume_errors_stop(tmp_path, owned):
    c = FakeClient([thread(status="notLoaded")], {"t": failed_turn()}, allowed=True)
    def resume(tid):
        message = f"thread {tid} already has an active writer" if owned else "unrelated resume failure"
        raise RpcError("thread/resume", {"code": -32600, "message": message})
    c.resume_thread = resume
    s = supervisor(tmp_path, c)
    if owned:
        assert s.run_cycle().dispatched == 1
        assert len(c.added) == 1
    else:
        with pytest.raises(RpcError):
            s.run_cycle()
        assert not c.added


def test_stale_queue_deletion_must_be_verified_before_forgetting(tmp_path):
    ob = Obligation.create("t", "turn-1", 900, None)
    ob.phase = "submitted"
    ob.queued_submission_id = "own"
    save_state(tmp_path / "state.json", State(obligations=[ob]))
    c = FakeClient([thread()], {"t": {"id": "new", "status": "completed"}})
    c.queue["t"] = [{"id": "own", "clientUserMessageId": ob.client_user_message_id}]
    c.queue_delete = lambda *_: False
    s = supervisor(tmp_path, c)
    with pytest.raises(ProtocolError, match="retaining the obligation"):
        s.run_cycle()
    assert len(load_state(tmp_path / "state.json").obligations) == 1


def test_loop_closes_subscription_before_sleep_and_stops_gracefully(tmp_path):
    c = FakeClient()
    closed = []
    c.close = lambda: closed.append(True)
    s = supervisor(tmp_path, c)
    stopped = []
    def sleep(seconds):
        assert closed
        assert s.client is None
        stopped.append(True)
    s.sleep = sleep
    s.run_forever(lambda: bool(stopped))
    assert len(closed) == 1
