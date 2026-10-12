"""Durable shared cooldown after an acknowledged recovery meets another quota stop."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import json
import math
from pathlib import Path
import re

from .errors import ProtocolError
from .presentation import usage_snapshot
from .state import save_record


@dataclass
class RetryState:
    version: int = 1
    binding: str | None = None
    streak: int = 0
    not_before: float = 0
    last_failure_at: float = 0
    resolved_at: float = 0
    reason: str = "backoff"
    failures: dict[str, str] = field(default_factory=dict)


class QuotaRetry:
    def __init__(self, path: Path):
        self.path = path
        self.state = RetryState()
        if path.exists():
            try:
                if path.stat().st_size > 1024 * 1024:
                    raise ValueError("Record exceeds its size limit")
                raw = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict) or set(raw) != set(RetryState.__dataclass_fields__):
                    raise ValueError("Unsupported fields")
                if type(raw["version"]) is not int or raw["version"] != 1:
                    raise ValueError("Unsupported version")
                if raw["binding"] is not None and (not isinstance(raw["binding"], str) or not re.fullmatch(r"[a-f0-9]{64}", raw["binding"])):
                    raise ValueError("Invalid account binding")
                if type(raw["streak"]) is not int or not 0 <= raw["streak"] <= 4:
                    raise ValueError("Invalid failure streak")
                for key in ("not_before", "last_failure_at", "resolved_at"):
                    if type(raw[key]) not in (int, float) or not math.isfinite(raw[key]) or raw[key] < 0:
                        raise ValueError("Invalid retry timestamp")
                if raw["reason"] not in {"backoff", "quota_reset"}:
                    raise ValueError("Invalid waiting reason")
                if not isinstance(raw["failures"], dict) or any(
                        not isinstance(k, str) or not k or not isinstance(v, str) or not v
                        for k, v in raw["failures"].items()):
                    raise ValueError("Invalid failure identities")
                if raw["streak"] == 0 and (raw["not_before"] or raw["last_failure_at"] or raw["failures"]):
                    raise ValueError("Inactive record carries an unresolved rejection")
                if raw["streak"] and (not raw["failures"] or raw["not_before"] <= 0
                                      or raw["last_failure_at"] <= raw["resolved_at"]):
                    raise ValueError("Active record lacks its rejection evidence")
                self.state = RetryState(**raw)
            except (OSError, ValueError, TypeError, UnicodeError) as exc:
                raise ProtocolError("Cannot read quota-retry.json. Preserve the file and repair its readability or format before restarting monitoring.") from exc

    def bind(self, identity: str | None) -> None:
        # Unavailable metadata must not silently remove an existing cooldown.
        if identity is None or identity == self.state.binding:
            return
        if self.state.binding is not None:
            state = RetryState(binding=identity)
        else:
            state = replace(self.state, binding=identity)
        if self.path.exists():
            self.save(state)
        else:
            self.state = state

    def save(self, state: RetryState) -> None:
        save_record(self.path, asdict(state))
        self.state = state

    def rejected(self, thread_id: str, turn_id: str, completed_at: float, limits: dict, now: float) -> bool:
        state = replace(self.state, failures=dict(self.state.failures))
        if completed_at <= state.resolved_at or state.failures.get(thread_id) == turn_id:
            return False
        state.failures[thread_id] = turn_id
        state.streak = min(4, state.streak + 1)
        state.last_failure_at = max(state.last_failure_at, completed_at)
        delay = min(1800, 300 * 2 ** (state.streak - 1))
        windows = usage_snapshot(limits, now)["windows"].values()
        resets = [w["resetsAt"] for w in windows if w["remaining"] == 0
                  and w["resetsAt"] is not None and w["resetsAt"] > now]
        reset = max(resets) if resets else None
        deadline = reset if reset is not None and state.streak == 1 else max(reset or 0, now + delay)
        state.not_before = max(state.not_before, deadline)
        state.reason = "quota_reset" if reset is not None and deadline == reset else "backoff"
        # Persist before removing delivery observations; replay is identity-idempotent.
        self.save(state)
        return True

    def succeeded(self, completed_at: float) -> bool:
        state = self.state
        if not state.streak or completed_at <= max(state.last_failure_at, state.resolved_at):
            return False
        self.save(RetryState(binding=state.binding, resolved_at=completed_at))
        return True

    def blocked(self, now: float) -> bool:
        return self.state.streak > 0 and now < self.state.not_before

    def report(self, now: float) -> dict:
        return {"blocked": self.blocked(now), "notBefore": self.state.not_before,
                "reason": self.state.reason, "backoffStep": self.state.streak}
