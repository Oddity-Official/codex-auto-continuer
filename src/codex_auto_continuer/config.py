from __future__ import annotations

import json
import math
import os
import sys
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
    prompt_file: str = "continue-prompt.md"
    poll_seconds: float = 30.0
    scan_lookback_hours: float = 24.0
    dispatch_spacing_seconds: float = 2.0
    rpc_timeout_seconds: float = 12.0
    codex_command_timeout_seconds: float = 20.0
    reconnect_backoff_seconds: float = 5.0
    dispatch_recovery_seconds: float = 15.0
    thread_scope: str = "allInteractive"
    desktop_custom_sources: tuple[str, ...] = ("chatgpt", "atlas")
    desktop_originators: tuple[str, ...] = ("Codex Desktop",)
    auto_start_daemon: bool = True
    codex_executable: str | None = None
    detailed_telemetry: bool = False
    log_max_mb: int = 16
    log_backups: int = 8


def app_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    project = Path(__file__).resolve().parents[2]
    if (project / "pyproject.toml").is_file():
        return project / ".data" / "runtime"
    return control_dir()


def control_dir() -> Path:
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
    directory = app_data_dir()
    # A pip-installed CLI controls the last registered app copy. Source checkouts
    # and portable EXEs keep their own defaults and never switch data silently.
    owner = control_dir() / "owner.json"
    if directory == control_dir() and owner.exists():
        try:
            raw = json.loads(owner.read_text(encoding="utf-8"))
            path = Path(raw["configPath"])
            if not path.is_absolute() or not path.is_file():
                raise ValueError("Owner config is missing or not absolute.")
            return path
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ConfigurationError("The last app copy's config cannot be located. Launch the portable app from its new folder, or pass --config explicitly.") from exc
    return directory / "config.json"


def state_path(config_file: Path | None = None) -> Path:
    return (config_file or default_config_path()).resolve().parent / "state.json"


def log_path(config_file: Path | None = None) -> Path:
    return (config_file or default_config_path()).resolve().parent / "telemetry.jsonl"


def lock_path() -> Path:
    return control_dir() / "supervisor.lock"


def stop_path() -> Path:
    return control_dir() / "stop.request"


def scan_path() -> Path:
    return control_dir() / "scan.request"


def owner_path() -> Path:
    return control_dir() / "owner.json"


def prompt_path(cfg: Config, config_file: Path | None = None) -> Path:
    path = Path(cfg.prompt_file)
    return path if path.is_absolute() else (config_file or default_config_path()).resolve().parent / path


def read_prompt(path: Path) -> str:
    try:
        before = path.stat()
        if before.st_size > 65536:
            raise ConfigurationError("Continuation prompt exceeds 64 KiB. Shorten the Markdown file.")
        text = path.read_text(encoding="utf-8-sig")
        after = path.stat()
    except (OSError, UnicodeError) as exc:
        raise ConfigurationError(f"Cannot read UTF-8 continuation prompt {path}. Check the file and its encoding.") from exc
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise ConfigurationError("The continuation prompt changed while being read. Finish saving it and restart monitoring.")
    if not text.strip():
        raise ConfigurationError("The continuation prompt is empty. Edit the Markdown file before starting monitoring.")
    return text


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
    if not isinstance(cfg.prompt_file, str) or not cfg.prompt_file.strip() or Path(cfg.prompt_file).suffix.lower() != ".md":
        raise ConfigurationError("prompt_file must name a Markdown (.md) file.")
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
    if cfg.codex_executable is not None and (not isinstance(cfg.codex_executable, str) or not Path(cfg.codex_executable).is_absolute()):
        raise ConfigurationError("codex_executable must be an absolute native executable path or null.")
    if type(cfg.detailed_telemetry) is not bool:
        raise ConfigurationError("detailed_telemetry must be true or false.")
    if type(cfg.log_max_mb) is not int or not 1 <= cfg.log_max_mb <= 256:
        raise ConfigurationError("log_max_mb must be an integer from 1 to 256.")
    if type(cfg.log_backups) is not int or not 1 <= cfg.log_backups <= 64:
        raise ConfigurationError("log_backups must be an integer from 1 to 64.")
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
    save_config(path, Config())
    return path


def save_config(path: Path, cfg: Config) -> None:
    validate_config(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(cfg)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def initialize_files(path: Path) -> Config:
    if not path.exists():
        write_config(path)
    cfg = load_config(path)
    prompt = prompt_path(cfg, path)
    if not prompt.exists():
        prompt.parent.mkdir(parents=True, exist_ok=True)
        with prompt.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(DEFAULT_CONTINUE_PROMPT + "\n")
    read_prompt(prompt)
    return cfg
