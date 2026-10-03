from __future__ import annotations

import json
import math
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .errors import ProtocolError

STATE_VERSION = 1
CLIENT_ID_NAMESPACE = uuid.UUID("64277943-c127-56b7-aaaf-bf6f761767b7")
VALID_PHASES = {"pending", "dispatching", "submitted", "uncertain"}


@dataclass
class Obligation:
    thread_id: str
    failed_turn_id: str
    detected_at: float
    reset_at: float | None
    client_user_message_id: str
    phase: str = "pending"
    phase_changed_at: float = 0.0
    queued_submission_id: str | None = None

    @classmethod
    def create(cls, thread_id: str, failed_turn_id: str, detected_at: float, reset_at: float | None) -> "Obligation":
        client_id = str(uuid.uuid5(CLIENT_ID_NAMESPACE, f"{thread_id}:{failed_turn_id}"))
        return cls(
            thread_id=thread_id,
            failed_turn_id=failed_turn_id,
            detected_at=detected_at,
            reset_at=reset_at,
            client_user_message_id=client_id,
            phase="pending",
            phase_changed_at=detected_at,
        )


@dataclass
class State:
    version: int = STATE_VERSION
    obligations: list[Obligation] = field(default_factory=list)

    def by_thread(self) -> dict[str, Obligation]:
        return {item.thread_id: item for item in self.obligations}


def _finite_number(name: str, value: Any, *, optional: bool = False) -> float | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ProtocolError(f"State field {name} must be a finite number{' or null' if optional else ''}.")
    return float(value)


def _nonempty_string(name: str, value: Any, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"State field {name} must be a non-empty string{' or null' if optional else ''}.")
    return value


def _parse_obligation(raw: Any) -> Obligation:
    if not isinstance(raw, dict):
        raise ProtocolError("Each state obligation must be an object.")
    expected = {f.name for f in Obligation.__dataclass_fields__.values()}
    unknown = sorted(set(raw) - expected)
    missing = sorted(expected - set(raw))
    if unknown:
        raise ProtocolError(f"Unknown obligation field(s): {', '.join(unknown)}")
    if missing:
        raise ProtocolError(f"Missing obligation field(s): {', '.join(missing)}")
    phase = _nonempty_string("phase", raw["phase"])
    if phase not in VALID_PHASES:
        raise ProtocolError(f"Unknown obligation phase: {phase}")
    queued = _nonempty_string("queued_submission_id", raw["queued_submission_id"], optional=True)
    if phase == "submitted" and queued is None:
        raise ProtocolError("A submitted obligation must have queued_submission_id.")
    return Obligation(
        thread_id=_nonempty_string("thread_id", raw["thread_id"]),
        failed_turn_id=_nonempty_string("failed_turn_id", raw["failed_turn_id"]),
        detected_at=_finite_number("detected_at", raw["detected_at"]),
        reset_at=_finite_number("reset_at", raw["reset_at"], optional=True),
        client_user_message_id=_nonempty_string("client_user_message_id", raw["client_user_message_id"]),
        phase=phase,
        phase_changed_at=_finite_number("phase_changed_at", raw["phase_changed_at"]),
        queued_submission_id=queued,
    )


def load_state(path: Path) -> State:
    if not path.exists():
        return State()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"Cannot read durable state {path}: {exc}") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "obligations"}:
        raise ProtocolError(f"State {path} has an unsupported shape.")
    if raw["version"] != STATE_VERSION:
        raise ProtocolError(f"Unsupported state version {raw['version']!r}; expected {STATE_VERSION}.")
    if not isinstance(raw["obligations"], list):
        raise ProtocolError("State obligations must be an array.")
    obligations = [_parse_obligation(item) for item in raw["obligations"]]
    ids = [item.thread_id for item in obligations]
    if len(ids) != len(set(ids)):
        raise ProtocolError("State contains more than one obligation for the same thread.")
    return State(version=STATE_VERSION, obligations=obligations)


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": STATE_VERSION, "obligations": [asdict(item) for item in state.obligations]}
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ProtocolError(f"Cannot persist durable state {path}: {exc}") from exc
