from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from codex_auto_continuer import __version__, compatibility, codex
from codex_auto_continuer.compatibility import Compatibility, CompatibilityBlocked, CompatibilityGate, _project
from codex_auto_continuer.state import load_state, save_state
from test_supervisor import FakeClient, failed_turn, supervisor, thread


@pytest.mark.parametrize("version", ["0.160.0-alpha.1", "0.160.0+custom.2", "0.160.0-alpha.1+custom.2"])
def test_version_suffix_is_not_certified_as_stable(monkeypatch, version):
    from test_codex import cp
    monkeypatch.setattr(codex, "_run", lambda *_: cp(out=f"codex-cli {version}\n"))
    assert codex.codex_version("codex", 1) == version


def test_dedicated_server_version_is_preserved_but_is_not_a_full_cli(monkeypatch):
    from test_codex import cp
    monkeypatch.setattr(codex, "_run", lambda *_: cp(out="codex-app-server 0.160.0+custom\n"))
    assert codex.binary_version("server", 1) == ("0.160.0+custom", "codex-app-server")
    from codex_auto_continuer.errors import ProtocolError
    with pytest.raises(ProtocolError, match="full Codex CLI"):
        codex.codex_version("server", 1)


def test_schema_projection_ignores_annotations_and_unconsumed_fields_but_checks_new_required_inputs():
    original = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    added = copy.deepcopy(original)
    added["description"] = "Unrelated upstream documentation"
    added["properties"]["extra"] = {"type": "string"}
    assert _project(original, {}, {"id": None}) == _project(added, {}, {"id": None})
    added["required"].append("extra")
    assert _project(original, {}, {"id": None}, request=True) != _project(added, {}, {"id": None}, request=True)
    added["properties"]["id"]["type"] = "integer"
    assert _project(original, {}, {"id": None}) != _project(added, {}, {"id": None})


def test_packaged_certificate_matches_consumer_contract_and_current_application():
    record = json.loads(compatibility.RECORD.read_text(encoding="utf-8"))
    assert record["format"] == 1 and set(record["contract"]) == set(compatibility.METHODS)
    assert record["certificates"]
    for certificate in record["certificates"]:
        assert certificate["cac_version"] == __version__
        assert certificate["schema_sha256"] == compatibility.contract_digest(record["contract"])


def test_unknown_error_variants_do_not_block_but_quota_discriminator_drift_does():
    from codex_auto_continuer.errors import ProtocolError
    consumed = {"$literal": "usageLimitExceeded"}
    known = {"type": "string", "enum": ["usageLimitExceeded", "other"]}
    baseline = _project({"oneOf": [known]}, {}, consumed)
    expanded = {"anyOf": [known, {"type": ["string", "object"]}]}
    assert _project(expanded, {}, consumed) == baseline
    with pytest.raises(ProtocolError, match="usage-limit discriminator"):
        _project({"anyOf": [{"type": "string"}, {"enum": ["other"]}]}, {}, consumed)
    assert _project(known | {"type": ["string", "null"]}, {}, consumed) != baseline


def test_text_input_projection_does_not_depend_on_unrelated_input_variants():
    schema = {"oneOf": [{"properties": {"type": {"enum": ["text"]}, "text": {"type": "string"}}, "required": ["type", "text"]}]}
    fields = {"$type": "text", "type": None, "text": None}
    original = _project(schema, {}, fields, request=True)
    schema["oneOf"].append({"properties": {"type": {"enum": ["newMediaType"]}}})
    assert _project(schema, {}, fields, request=True) == original


def gate_fixture(tmp_path, monkeypatch):
    binary = tmp_path / "codex.exe"
    binary.write_bytes(b"synthetic Codex build")
    gate = CompatibilityGate(tmp_path)
    digest = gate.binary_hash(binary)
    version = "0.160.0"
    monkeypatch.setattr(compatibility, "codex_version", lambda *_: version)
    monkeypatch.setattr(compatibility, "binary_version", lambda *_: (version, "codex-cli"))
    monkeypatch.setattr(compatibility.platform, "system", lambda: "Windows")
    monkeypatch.setattr(compatibility.platform, "machine", lambda: "AMD64")
    gate._schemas[(digest, version)] = copy.deepcopy(gate.record["contract"])
    daemon = codex.DaemonInfo("running", tmp_path / "socket", version, version, binary, version)
    certificate = {field: value for field, value in gate.record["certificates"][0].items()}
    certificate.update(cli_sha256=digest, server_sha256=digest, cac_version=__version__,
        schema_sha256=compatibility.contract_digest(gate.record["contract"]))
    gate.record["certificates"] = [certificate]
    return gate, binary, daemon


def test_exact_tuple_requires_behavioral_certificate_not_just_matching_schema(tmp_path, monkeypatch):
    gate, binary, daemon = gate_fixture(tmp_path, monkeypatch)
    assert gate.inspect(str(binary), daemon, "cac/0.160.0 (Windows)", 1).dispatch_allowed
    gate.record["certificates"] = []
    result = gate.inspect(str(binary), daemon, "cac/0.160.0 (Windows)", 1)
    assert result.status == "untested" and result.read_allowed and not result.dispatch_allowed
    balanced = gate.inspect(str(binary), daemon, "cac/0.160.0 (Windows)", 1, "balanced")
    assert balanced.dispatch_allowed and balanced.status == "untested" and balanced.policy == "balanced"


def test_balanced_does_not_allow_prereleases_or_invalid_identity():
    for version in ("0.173.0-beta.1", "", "0.173"):
        assert not Compatibility(status="untested", policy="balanced", cli_version=version,
                                 app_server_version=version).dispatch_allowed


def test_standalone_server_never_borrows_a_matching_cli_schema_or_certificate(tmp_path, monkeypatch):
    gate, binary, daemon = gate_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(compatibility, "binary_version", lambda *_: ("0.160.0", "codex-app-server"))
    result = gate.inspect(str(binary), daemon, "cac/0.160.0 (Windows)", 1)
    assert not result.read_allowed and not result.dispatch_allowed and result.schema_sha256 is None
    assert result.schema_source is None and "standalone" in result.reason


@pytest.mark.parametrize("change", ["connection", "daemon", "managed", "cli", "path"])
def test_mixed_or_missing_identity_blocks_dispatch(tmp_path, monkeypatch, change):
    from dataclasses import replace
    gate, binary, daemon = gate_fixture(tmp_path, monkeypatch)
    agent = "cac/0.160.0 (Windows)"
    if change == "connection": agent = "cac/0.161.0 (Windows)"
    if change == "daemon": daemon = replace(daemon, app_server_version="0.161.0")
    if change == "managed": daemon = replace(daemon, managed_codex_version="0.161.0")
    if change == "cli": daemon = replace(daemon, cli_version="0.161.0")
    if change == "path": daemon = replace(daemon, managed_codex_path=None)
    assert not gate.inspect(str(binary), daemon, agent, 1).dispatch_allowed


@pytest.mark.parametrize("method,reads", [("thread/queue/add", True), ("thread/list", False)])
def test_schema_drift_blocks_mutations_and_only_affected_read_contract(tmp_path, monkeypatch, method, reads):
    gate, binary, daemon = gate_fixture(tmp_path, monkeypatch)
    gate._schemas[(gate.binary_hash(binary), "0.160.0")][method]["request"]["required"].append("newField")
    result = gate.inspect(str(binary), daemon, "cac/0.160.0 (Windows)", 1)
    assert result.status == "schema_mismatch" and result.read_allowed is reads
    assert not result.dispatch_allowed and method in result.reason


def test_same_version_binary_replacement_invalidates_schema_and_certificate(tmp_path, monkeypatch):
    gate, binary, daemon = gate_fixture(tmp_path, monkeypatch)
    original = gate.binary_hash(binary)
    binary.write_bytes(b"different same-version build")
    assert gate.binary_hash(binary) != original
    from test_codex import cp
    monkeypatch.setattr(compatibility, "_run", lambda *_: cp(1))
    assert not gate.inspect(str(binary), daemon, "cac/0.160.0 (Windows)", 1).dispatch_allowed
    assert not list(tmp_path.glob("schema-*"))


def test_unknown_build_records_new_failure_without_queue_write_or_forgetting_submitted_work(tmp_path):
    client = FakeClient([thread(), thread("other")], {"t": failed_turn(), "other": failed_turn()}, allowed=False)
    s = supervisor(tmp_path, client)
    s.run_cycle()
    obligation = s.state.obligations[0]
    obligation.phase = "uncertain"
    save_state(s.state_file, s.state)
    client.turns["t"] = {"id": "manual", "status": "completed"}
    client.allowed = True
    client.threads.append(thread("new"))
    client.turns["new"] = failed_turn()
    s.compatibility = Compatibility(status="untested", reason="Untested build")
    result = s.run_cycle()
    assert result.detected == 1 and result.dispatched == result.cancelled == 0
    assert result.pending == 3 and load_state(s.state_file).obligations[0].phase == "uncertain"
    assert not client.added and not client.deleted and not client.resume_calls
    with pytest.raises(CompatibilityBlocked):
        s._cancel_queued_continuations(obligation)


@pytest.mark.parametrize("changed_check", [1, 2, 3])
def test_version_change_before_resume_or_send_preserves_intent_and_never_submits(tmp_path, monkeypatch, changed_check):
    client = FakeClient([thread(status="notLoaded")], {"t": failed_turn()}, allowed=False)
    s = supervisor(tmp_path, client)
    s.run_cycle()
    before = s.state_file.read_bytes()
    client.allowed = True
    s.codex_bin = "fixture.exe"
    checks = []
    def recheck(*_):
        checks.append(True)
        return Compatibility(status="untested" if len(checks) == changed_check else "certified", reason="Changed binary")
    monkeypatch.setattr(s.compatibility_gate, "recheck", recheck)
    with pytest.raises(CompatibilityBlocked):
        s.run_cycle()
    assert not client.added and s.state_file.read_bytes() == before


def test_read_contract_drift_does_not_touch_state_or_read_threads(tmp_path):
    client = FakeClient([thread()], {"t": failed_turn()}, allowed=False)
    s = supervisor(tmp_path, client)
    s.run_cycle()
    before = s.state_file.read_bytes()
    s.compatibility = Compatibility(status="schema_mismatch", read_allowed=False)
    client.rate_limits = lambda: pytest.fail("Drifted read contract must not be used")
    assert s.run_cycle().pending == 1
    assert s.state_file.read_bytes() == before


def test_live_status_reports_block_without_using_changed_read_methods(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    from codex_auto_continuer import cli
    closed = []
    def changed_read():
        pytest.fail("A blocked read contract must not be queried by live status")
    client = SimpleNamespace(user_agent="cac/0.160.0 (Windows)", rate_limits=changed_read,
                             close=lambda: closed.append(True))
    monkeypatch.setattr(cli, "owns_monitor", lambda *_: False)
    monkeypatch.setattr(cli, "phase", lambda *_: "stopped")
    monkeypatch.setattr(cli, "find_codex", lambda *_: "fixture.exe")
    monkeypatch.setattr(cli, "codex_version", lambda *_: "0.160.0")
    monkeypatch.setattr(cli, "ensure_daemon", lambda *_: SimpleNamespace(socket_path=tmp_path / "socket"))
    monkeypatch.setattr(cli.AppServerClient, "connect", lambda *_: client)
    monkeypatch.setattr(cli, "observed_interactive_sources", lambda *_: changed_read())
    monkeypatch.setattr(cli.CompatibilityGate, "recheck", lambda *_: Compatibility(read_allowed=False))
    assert cli._status(tmp_path / "settings.toml", live=True) == 2
    report = json.loads(capsys.readouterr().out)["compatibility"]
    assert not report["dispatch_allowed"] and not report["read_allowed"] and closed == [True]


def test_connect_rechecks_versions_and_identity_on_each_connection(tmp_path, monkeypatch):
    client = FakeClient()
    s = supervisor(tmp_path, client)
    s.close()
    calls = []
    import codex_auto_continuer.supervisor as module
    monkeypatch.setattr(module, "find_codex", lambda *_: "fixture.exe")
    monkeypatch.setattr(module, "codex_version", lambda *_: calls.append("version") or "0.160.0")
    monkeypatch.setattr(module, "ensure_daemon", lambda *_: codex.DaemonInfo("running", Path("fixture.sock"), "0.160.0", "0.160.0"))
    monkeypatch.setattr(module.AppServerClient, "connect", lambda *_: client)
    client.thread_list = lambda **_: pytest.fail("Read-contract failure must not probe a changed method")
    monkeypatch.setattr(s.compatibility_gate, "recheck", lambda *_: calls.append("identity") or Compatibility(read_allowed=False))
    s.connect(); s.close(); s.connect(); s.close()
    assert calls == ["version", "identity", "version", "identity"]


def test_daemon_restart_during_prewrite_recheck_is_retryable_not_an_uncertain_send(tmp_path, monkeypatch):
    from codex_auto_continuer.errors import CodexCommandError
    gate = CompatibilityGate(tmp_path)
    def unavailable(*_):
        raise CodexCommandError("Fixture daemon is restarting")
    monkeypatch.setattr(compatibility, "daemon_version", unavailable)
    report = gate.recheck("fixture.exe", "cac/0.160.0 (Windows)", 1)
    assert not report.dispatch_allowed and not report.read_allowed
    assert "recheck" in report.reason
