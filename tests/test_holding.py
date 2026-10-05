from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from codex_auto_continuer import holding, holding_journal, cli
from codex_auto_continuer.errors import ConfigurationError, TransportError
from codex_auto_continuer.holding import Holding, Watcher
from codex_auto_continuer.holding_journal import Journal

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Private held inputs use Windows account encryption")
BINDING = "a" * 64
BODY = "PRIVATE_TEST_BODY_DO_NOT_LOG"


def entry(identity="q", phase="held"):
    return {"id": identity, "threadId": "t", "clientUserMessageId": "client-" + identity,
        "anchorTurnId": "initial", "input": [{"type": "text", "text": BODY, "text_elements": []}],
        "phase": phase, "releasedQueueId": None}


def turn(identity="initial", status="completed", client_id=None):
    return {"id": identity, "status": status, "completedAt": None if status == "inProgress" else 1,
        "error": None, "items": [{"type": "userMessage", "clientId": client_id}]}


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setattr(holding, "account_binding", lambda _: BINDING)
    manager = Holding(tmp_path)
    manager.enabled = manager.allowed = True
    manager.home = tmp_path
    with manager.journal.transaction(BINDING) as raw:
        raw["records"] = [entry(), entry("q2")]
        raw["threads"] = {"t": {"authorizedTurnId": "initial", "recoveryIds": [], "paused": ""}}
        manager.journal.save(raw)
    return manager


class Owner:
    def __init__(self, manager):
        self.manager = manager
        self.turns = [turn()]
        self.kind = "idle"
        self.allowed = True
        self.queued = []
        self.sent = []

    def thread_read(self, _):
        return {"id": "t", "status": {"type": self.kind}, "archived": False}

    def latest_turn(self, _): return self.turns[-1]
    def full_turns(self, _): return self.turns
    def queue_items(self, _): return self.queued
    def rate_limits(self): return {"ordinaryUsageAllowed": self.allowed}

    def queue_add_input(self, identity, input, client_id):
        assert self.manager.journal.read()["records"][0]["phase"] == "release_requested"
        self.sent.append((identity, copy.deepcopy(input), client_id))
        return {"queuedSubmission": {"id": "released", "clientUserMessageId": client_id}}


def reconcile(manager, owner):
    return manager.reconcile(owner, permission=True, in_scope=lambda _: True, guard=lambda: None)


def test_encryption_corruption_binding_and_atomic_write_failure(manager, monkeypatch):
    path = manager.journal.path
    before = path.read_bytes()
    assert BODY.encode() not in before
    assert Journal(path).read()["records"][0]["input"][0]["text"] == BODY
    with pytest.raises(ConfigurationError, match="original"):
        with manager.journal.transaction("b" * 64):
            pass
    monkeypatch.setattr(holding_journal.os, "fsync", lambda _: (_ for _ in ()).throw(OSError("simulated disk failure")))
    with pytest.raises(OSError):
        with manager.journal.transaction() as raw:
            raw["records"].clear()
            manager.journal.save(raw)
    assert path.read_bytes() == before and not list(path.parent.glob(".held-*"))
    path.write_bytes(before[:-20] + b"corrupt synthetic tail")
    with pytest.raises(ConfigurationError, match="Preserve"):
        manager.journal.read()


def test_lost_removal_ack_never_infers_unsent_from_history_absence(manager):
    with manager.journal.transaction() as raw:
        raw["records"].clear()
        manager.journal.save(raw)
    owner = Owner(manager)
    owner.kind = "active"
    owner.turns = [turn(status="inProgress")]
    queued = {"id": "q", "clientUserMessageId": "client-q", "input": entry()["input"]}
    owner.queued = [queued]
    # Inspection inside the same transaction would deadlock; read the encrypted
    # atomic file directly to prove persistence before mutation.
    def delete(*_):
        assert manager.journal._read()["records"][0]["phase"] == "saved"
        owner.queued.clear()
        raise TransportError("Synthetic accepted delete response lost")
    owner.queue_delete = delete
    watcher = Watcher(manager, "t", Path("unused"), "fixture", 1)
    with pytest.raises(TransportError):
        watcher.capture(owner)
    owner.kind, owner.turns = "idle", [turn()]
    assert reconcile(manager, owner) == {"t"} and not owner.sent
    assert manager.journal.read()["records"][0]["phase"] == "saved"
    manager.journal.manage("confirm-unsent", "q")
    assert reconcile(manager, owner) == {"t"} and not owner.sent
    manager.journal.manage("resume", "t")
    reconcile(manager, owner)
    assert len(owner.sent) == 1


def test_fresh_permission_rechecks_and_only_one_input_released(manager):
    owner = Owner(manager)
    owner.allowed = False
    reconcile(manager, owner)
    assert not owner.sent
    owner.allowed = True
    reconcile(manager, owner)
    assert len(owner.sent) == 1
    reconcile(manager, owner)
    assert len(owner.sent) == 1  # Acceptance is not terminal completion.
    owner.kind, owner.turns = "active", [turn(), turn("replayed", "inProgress", "client-q")]
    reconcile(manager, owner)
    assert len(owner.sent) == 1 and len(manager.journal.read()["records"]) == 2
    owner.kind = "idle"
    owner.turns[-1] = turn("replayed", client_id="client-q")
    reconcile(manager, owner)
    assert len(owner.sent) == 2 and len(manager.journal.read()["records"]) == 1


def test_manual_progress_requires_explicit_review_and_disabled_preserves(manager):
    owner = Owner(manager)
    owner.turns.append(turn("manual", client_id="manual-client"))
    assert reconcile(manager, owner) == {"t"} and not owner.sent
    manager.journal.manage("resume", "t")
    manager.enabled = False
    reconcile(manager, owner)
    assert not owner.sent and len(manager.journal.read()["records"]) == 2
    manager.enabled = True
    reconcile(manager, owner)
    assert len(owner.sent) == 1


def test_duplicate_client_identity_is_not_success(manager):
    owner = Owner(manager)
    owner.turns.extend([turn("first", client_id="client-q"), turn("duplicate", client_id="client-q")])
    assert reconcile(manager, owner) == {"t"} and not owner.sent
    assert len(manager.journal.read()["records"]) == 2


def test_cli_body_access_is_explicit_and_uncertainty_needs_confirmation(manager, capsys):
    config = manager.journal.path.parent / "settings.toml"
    assert cli.main(["--config", str(config), "held", "list"]) == 0
    assert BODY not in capsys.readouterr().out
    assert cli.main(["--config", str(config), "held", "list", "--show-input"]) == 0
    assert BODY in capsys.readouterr().out
    assert cli.main(["--config", str(config), "held", "confirm-unsent", "q"]) == 2
    assert "--confirm" in capsys.readouterr().err


def test_unconfirmed_input_cannot_be_discarded(manager):
    with manager.journal.transaction() as raw:
        raw["records"][0]["phase"] = "release_requested"
        manager.journal.save(raw)
    with pytest.raises(ConfigurationError, match="confirmed"):
        manager.journal.manage("discard", "q")


def test_empty_disabled_journal_needs_no_owner_or_codex_connection(manager):
    from codex_auto_continuer.config import Config
    from codex_auto_continuer.supervisor import Supervisor
    manager.journal.manage("discard", "q")
    manager.journal.manage("discard", "q2")
    manager.enabled = False
    manager.home = None
    assert manager.reconcile(None, permission=False, in_scope=lambda _: False, guard=lambda: None) == set()
    engine = Supervisor(Config(clients=()), manager.journal.path.parent / "state.json")
    cycles = []
    engine.on_cycle = cycles.append
    engine.connect = lambda: pytest.fail("No clients or held inputs must not connect to Codex")
    try:
        engine.run_forever(lambda: bool(cycles))
        assert cycles[0].scanned_threads == 0
    finally:
        engine.close()
