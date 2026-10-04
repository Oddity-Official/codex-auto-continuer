"""Read local monitoring status without starting Codex or requesting model work."""
from __future__ import annotations

import json
from pathlib import Path

from .config import lock_path, owner_path
from .errors import AutoContinuerError
from .instance_lock import is_running


def read_runtime(settings: Path) -> dict:
    path = settings.parent / "runtime-status.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("phase") not in {
            "starting", "scanning", "monitoring", "waiting", "paused", "reconnecting", "failed", "stopped"
        }:
            raise ValueError("Invalid phase or snapshot object.")
        return value
    except (OSError, UnicodeError, ValueError) as exc:
        raise AutoContinuerError("Cannot read runtime status. Open the data folder and inspect runtime-status.json and telemetry.") from exc


def owns_monitor(settings: Path) -> bool:
    if not is_running(lock_path()):
        return False
    try:
        owner = json.loads(owner_path().read_text(encoding="utf-8"))
        return owner.get("configPath") == str(settings.resolve())
    except (OSError, ValueError) as exc:
        raise AutoContinuerError("The running monitor's owner record is unreadable. Inspect the per-user control folder before restarting.") from exc


def phase(settings: Path, snapshot: dict, *, running: bool | None = None) -> str:
    if owns_monitor(settings) if running is None else running:
        return snapshot.get("phase", "starting")
    return "failed" if snapshot.get("phase") == "failed" else "stopped"
