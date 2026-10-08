from __future__ import annotations

import hashlib
import json
from pathlib import Path
from dataclasses import replace
import pytest

from codex_auto_continuer import codex, compatibility
from codex_auto_continuer.compatibility import Compatibility, CompatibilityGate
from codex_auto_continuer.config import Config
from codex_auto_continuer.supervisor import Supervisor
from native_support import NativeFixture
from conftest import ROOT


@pytest.mark.parametrize("holding", [False, True])
def test_native_schema_and_connected_build(codex_binary, native, holding):
    cli_version = codex.codex_version(codex_binary, 10)
    server_version, _kind = codex.binary_version(native.binary, 10)
    info = codex.DaemonInfo("running", native.socket, cli_version, server_version, Path(native.binary), server_version)
    client = native.client()
    report = CompatibilityGate(native.data).inspect(codex_binary, info, client.user_agent, 20, holding=holding)
    assert report.status in {"certified", "untested"}, report.reason
    assert report.schema_sha256 is not None and report.schema_source == "managed_binary"
    assert report.contract_scope == ("holding" if holding else "recovery")
    print(json.dumps(report.report(), sort_keys=True))


@pytest.mark.parametrize("policy", ["strict", "balanced"])
def test_managed_daemon_restart_reconnect_and_unknown_tuple_preserve_pending(codex_binary, monkeypatch, request, policy):
    original_run = codex._run
    daemon_binary = request.config.getoption("--daemon-executable") or codex_binary
    expected = {"cli_version": codex.codex_version(codex_binary, 10),
                "app_server_version": codex.codex_version(daemon_binary, 10)}
    for key, binary in (("cli_sha256", codex_binary), ("server_sha256", daemon_binary)):
        with Path(binary).open("rb") as stream:
            expected[key] = hashlib.file_digest(stream, "sha256").hexdigest()
    with NativeFixture(ROOT, codex_binary, managed=True, daemon_binary=daemon_binary) as native:
        def isolated_run(binary, args, timeout, **kwargs):
            return original_run(binary, args, timeout, env=native.env)
        monkeypatch.setattr(codex, "_run", isolated_run)
        monkeypatch.setattr(compatibility, "_run", isolated_run)
        tid, failed = native.start_thread()
        native.assert_quota_failure(failed)
        supervisor = Supervisor(Config(codex_executable=codex_binary, dispatch_spacing_seconds=0, compatibility_policy="strict"), native.data / "state.json")
        native.supervisors.append(supervisor)
        def connect_candidate():
            supervisor.connect()
            report = supervisor.compatibility.report()
            assert {key: report[key] for key in expected} == expected, "Bootstrap/restart must run the requested candidate, not silently replace it with the invoking CLI"
        connect_candidate()
        assert supervisor.compatibility.status in {"certified", "untested"}, supervisor.compatibility.reason
        result = supervisor.run_cycle()
        assert result.detected == result.pending == 1 and result.dispatched == 0
        saved = supervisor.state_file.read_bytes()
        supervisor.close()
        restart = isolated_run(codex_binary, ["app-server", "daemon", "restart"], 25)
        assert restart.returncode == 0
        connect_candidate()
        assert supervisor.state_file.read_bytes() == saved
        assert supervisor.compatibility.status in {"certified", "untested"}
        native.service.allowed = True
        native.service.fail_inference = False
        supervisor.compatibility_gate.record["certificates"] = []
        supervisor.close(); connect_candidate()
        assert supervisor.compatibility.status == "untested"
        result = supervisor.run_cycle()
        assert result.dispatched == 0 and result.pending == 1
        assert supervisor.state_file.read_bytes() == saved
        assert native.service.inference_count == 1
        supervisor.config = replace(supervisor.config, compatibility_policy=policy)
        supervisor.close(); connect_candidate()
        assert supervisor.compatibility.policy == policy
        if policy == "balanced":
            assert supervisor.compatibility.status == "untested" and supervisor.compatibility.dispatch_allowed
        else:
            assert not supervisor.compatibility.dispatch_allowed
        supervisor.compatibility_gate = CompatibilityGate(native.data)
        if policy == "balanced":
            supervisor.compatibility_gate.record["certificates"] = []
        supervisor.close(); connect_candidate()
        if not supervisor.compatibility.dispatch_allowed:
            # Candidate evidence is established inside the isolated test, never granted to a user daemon.
            supervisor.compatibility = Compatibility(status="certified", reason="Isolated candidate behavioral probe")
            supervisor.codex_bin = None
        assert supervisor.run_cycle().dispatched == 1
        assert native.wait_turn(tid, after=failed["id"])["status"] == "completed"
        assert native.service.user_messages[-1] == "Continue"
        for _ in range(3):
            assert supervisor.run_cycle().dispatched == 0
        assert len(native.turns(tid)) == 2 and native.service.inference_count == 2
        print("Managed daemon: production connect, restart, unknown-tuple block, recovery and duplicate checks passed")
