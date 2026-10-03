from __future__ import annotations

import json
from pathlib import Path

import pytest

from codex_auto_continuer.errors import ProtocolError
from codex_auto_continuer.state import Obligation, State, load_state, save_state


def test_client_id_is_deterministic():
    a = Obligation.create("thread", "turn", 1, None)
    b = Obligation.create("thread", "turn", 2, 3)
    assert a.client_user_message_id == b.client_user_message_id


def test_state_round_trip(tmp_path: Path):
    path = tmp_path / "state.json"
    state = State(obligations=[Obligation.create("t", "x", 1.0, 2.0)])
    save_state(path, state)
    assert load_state(path) == state


def test_corrupt_state_fails_loud(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ProtocolError, match="Cannot read durable state"):
        load_state(path)


def test_duplicate_threads_rejected(tmp_path: Path):
    o = Obligation.create("t", "x", 1.0, None)
    payload = {"version": 1, "obligations": [o.__dict__, o.__dict__]}
    path = tmp_path / "state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ProtocolError, match="same thread"):
        load_state(path)


def test_nonfinite_timestamp_rejected(tmp_path: Path):
    o = Obligation.create("t", "x", 1.0, None).__dict__
    o["detected_at"] = float("nan")
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 1, "obligations": [o]}), encoding="utf-8")
    with pytest.raises(ProtocolError, match="finite"):
        load_state(path)


def test_submitted_requires_queue_id(tmp_path: Path):
    o = Obligation.create("t", "x", 1.0, None).__dict__
    o["phase"] = "submitted"
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 1, "obligations": [o]}), encoding="utf-8")
    with pytest.raises(ProtocolError, match="queued_submission_id"):
        load_state(path)


def test_state_cannot_claim_somebody_elses_queue_identity(tmp_path):
    obligation = Obligation.create("t", "x", 1.0, None).__dict__
    obligation["client_user_message_id"] = "another-client"
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 1, "obligations": [obligation]}))
    with pytest.raises(ProtocolError, match="refusing queue ownership"):
        load_state(path)
