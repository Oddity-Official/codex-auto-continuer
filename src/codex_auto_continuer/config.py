from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from .errors import ConfigurationError


DEFAULT_CONTINUE_PROMPT = (
    "Continue the current task from where you left off. Re-read the current thread state "
    "and keep working toward the existing task; do not restart work that is already complete."
)


@dataclass(frozen=True)
class Config:
    continue_prompt: str = DEFAULT_CONTINUE_PROMPT
    poll_seconds: float = 30.0
    scan_lookback_hours: float = 24.0
    dispatch_spacing_seconds: float = 2.0
    rpc_timeout_seconds: float = 12.0
    codex_command_timeout_seconds: float = 20.0
    reconnect_backoff_seconds: float = 5.0
    dispatch_recovery_seconds: float = 15.0
    thread_scope: str = "desktop"
    desktop_custom_sources: tuple[str, ...] = ("chatgpt", "atlas")
    desktop_originators: tuple[str, ...] = ("Codex Desktop",)
    auto_start_daemon: bool = True


def app_data_dir() -> Path:
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA")
        if not root:
            raise ConfigurationError("LOCALAPPDATA is not set; cannot locate per-user runtime state.")
        return Path(root) / "CodexAutoContinuer"
    root = os.environ.get("XDG_STATE_HOME")
    if root:
        return Path(root) / "codex-auto-continuer"
    return Path.home() / ".local" / "state" / "codex-auto-continuer"


def default_config_path() -> Path:
    return app_data_dir() / "config.json"


def state_path() -> Path:
    return app_data_dir() / "state.json"


def log_path() -> Path:
    return app_data_dir() / "auto-continuer.log"


def lock_path() -> Path:
    return app_data_dir() / "supervisor.lock"


def stop_path() -> Path:
    return app_data_dir() / "stop.request"


def _coerce(data: dict[str, Any]) -> Config:
    valid = {f.name for f in fields(Config)}
    unknown = sorted(set(data) - valid)
    if unknown:
        raise ConfigurationError(f"Unknown config field(s): {', '.join(unknown)}")
    data = dict(data)
    for name in ("desktop_custom_sources", "desktop_originators"):
        if name in data:
            value = data[name]
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ConfigurationError(f"{name} must be an array of strings.")
            data[name] = tuple(value)
    try:
        cfg = Config(**data)
    except TypeError as exc:
        raise ConfigurationError(f"Invalid configuration: {exc}") from exc
    return validate_config(cfg)


def validate_config(cfg: Config) -> Config:
    if not isinstance(cfg.continue_prompt, str) or not cfg.continue_prompt.strip():
        raise ConfigurationError("continue_prompt must be a non-empty string.")
    numeric = {
        "poll_seconds": cfg.poll_seconds,
        "scan_lookback_hours": cfg.scan_lookback_hours,
        "dispatch_spacing_seconds": cfg.dispatch_spacing_seconds,
        "rpc_timeout_seconds": cfg.rpc_timeout_seconds,
        "codex_command_timeout_seconds": cfg.codex_command_timeout_seconds,
        "reconnect_backoff_seconds": cfg.reconnect_backoff_seconds,
        "dispatch_recovery_seconds": cfg.dispatch_recovery_seconds,
    }
    for name, value in numeric.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value < 0
        ):
            raise ConfigurationError(f"{name} must be a finite non-negative number.")
    if cfg.poll_seconds < 1:
        raise ConfigurationError("poll_seconds must be at least 1 second.")
    if cfg.rpc_timeout_seconds < 1:
        raise ConfigurationError("rpc_timeout_seconds must be at least 1 second.")
    if cfg.codex_command_timeout_seconds < 1:
        raise ConfigurationError("codex_command_timeout_seconds must be at least 1 second.")
    if not isinstance(cfg.thread_scope, str) or cfg.thread_scope not in {"desktop", "allInteractive"}:
        raise ConfigurationError("thread_scope must be 'desktop' or 'allInteractive'.")
    for name in ("desktop_custom_sources", "desktop_originators"):
        values = getattr(cfg, name)
        if not isinstance(values, tuple) or not values or any(not isinstance(x, str) or not x.strip() for x in values):
            raise ConfigurationError(f"{name} must contain at least one non-empty name.")
    if not isinstance(cfg.auto_start_daemon, bool):
        raise ConfigurationError("auto_start_daemon must be true or false.")
    return cfg


def load_config(path: Path | None = None) -> Config:
    path = path or default_config_path()
    if not path.exists():
        return Config()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot read config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Config {path} must contain a JSON object.")
    return _coerce(raw)


def write_config(path: Path | None = None, *, force: bool = False) -> Path:
    path = path or default_config_path()
    if path.exists() and not force:
        raise ConfigurationError(f"Config already exists: {path}. Use --force to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(Config())
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path
