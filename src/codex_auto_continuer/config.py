from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .errors import ConfigurationError
from .atomic import replace_file
import tomlkit


DEFAULT_CONTINUE_PROMPT = "Continue"
ALL_CLIENTS = ("vscode", "cli", "desktop")


def setting(default, explanation):
    return field(default=default, metadata={"help": explanation})


@dataclass(frozen=True)
class Config:
    prompt_file: str = setting("continue-prompt.md", "Markdown prompt path, relative to this folder unless absolute.")
    poll_seconds: float = setting(30.0, "Seconds between scans; settings saves wake the next cycle.")
    scan_lookback_hours: float = setting(24.0, "Discover quota failures completed within this many hours; recorded work stays pending.")
    dispatch_spacing_seconds: float = setting(2.0, "Seconds between continuations when several chats become eligible.")
    rpc_timeout_seconds: float = setting(12.0, "Total deadline in seconds for each local Codex request.")
    codex_command_timeout_seconds: float = setting(20.0, "Seconds allowed for Codex version and daemon commands.")
    reconnect_backoff_seconds: float = setting(5.0, "Seconds before retrying a lost local Codex connection.")
    dispatch_recovery_seconds: float = setting(15.0, "Seconds to reconcile an uncertain send before isolating that chat; never blindly resend.")
    compatibility_policy: str = setting("balanced", "balanced permits schema-verified stable Codex builds; strict requires exact-build certification.")
    auto_update: bool = setting(True, "Automatically install signed stable CAC releases in portable builds; never updates Codex.")
    update_use_github_cli_auth: bool = setting(False, "Use your existing gh login for private releases; token stays in memory and is never logged or bundled.")
    update_check_hours: float = setting(6.0, "Hours between GitHub release checks; checks do not upload local diagnostics.")
    clients: tuple[str, ...] = setting(ALL_CLIENTS, "Any combination of vscode, cli and desktop; [] pauses client monitoring.")
    desktop_custom_sources: tuple[str, ...] = setting(("chatgpt", "atlas"), "Codex custom source labels recognized as Desktop.")
    desktop_originators: tuple[str, ...] = setting(("Codex Desktop",), "Distinguish Desktop from the VS Code extension when both use the vscode source.")
    auto_start_daemon: bool = setting(True, "Start the local Codex daemon if absent; this does not launch CAC at login.")
    codex_executable: str | None = setting(None, "Optional absolute codex.exe path; omit to auto-detect.")
    detailed_telemetry: bool = setting(False, "Keep real IDs, chat names and paths in local logs; never bodies or credentials.")
    diagnostic_trace: bool = setting(False, "Record every allowlisted RPC summary for troubleshooting; increases log size.")
    log_max_mb: int = setting(8, "Maximum MiB per active log stream before rotation.")
    log_backups: int = setting(3, "Number of compressed backups retained per stream; older backups expire.")


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
            if not path.is_absolute() or not path.parent.is_dir():
                raise ValueError("Owner data folder is missing or not absolute.")
            return path
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ConfigurationError("The last app copy's config cannot be located. Launch the portable app from its new folder, or pass --config explicitly.") from exc
    return directory / "settings.toml"


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
    for name in ("clients", "desktop_custom_sources", "desktop_originators"):
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
        "update_check_hours": cfg.update_check_hours,
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
    if not isinstance(cfg.compatibility_policy, str) or cfg.compatibility_policy not in {"balanced", "strict"}:
        raise ConfigurationError("compatibility_policy must be balanced or strict.")
    if type(cfg.auto_update) is not bool:
        raise ConfigurationError("auto_update must be true or false.")
    if type(cfg.update_use_github_cli_auth) is not bool:
        raise ConfigurationError("update_use_github_cli_auth must be true or false.")
    if not 1 <= cfg.update_check_hours <= 168:
        raise ConfigurationError("update_check_hours must be from 1 to 168.")
    if (not isinstance(cfg.clients, tuple) or any(not isinstance(x, str) or x not in ALL_CLIENTS for x in cfg.clients)
            or len(set(cfg.clients)) != len(cfg.clients)):
        raise ConfigurationError("clients must contain unique choices from vscode, cli and desktop, or [].")
    for name in ("desktop_custom_sources", "desktop_originators"):
        values = getattr(cfg, name)
        if not isinstance(values, tuple) or not values or any(not isinstance(x, str) or not x.strip() for x in values):
            raise ConfigurationError(f"{name} must contain at least one non-empty name.")
    if not isinstance(cfg.auto_start_daemon, bool):
        raise ConfigurationError("auto_start_daemon must be true or false.")
    if cfg.codex_executable is not None and (not isinstance(cfg.codex_executable, str) or not Path(cfg.codex_executable).is_absolute()):
        raise ConfigurationError("codex_executable must be an absolute native executable path, or omitted.")
    if type(cfg.detailed_telemetry) is not bool:
        raise ConfigurationError("detailed_telemetry must be true or false.")
    if type(cfg.diagnostic_trace) is not bool:
        raise ConfigurationError("diagnostic_trace must be true or false.")
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
        raw = _read_document(path).unwrap()
    except (OSError, UnicodeError, tomlkit.exceptions.ParseError) as exc:
        raise ConfigurationError(f"Cannot read config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Settings {path} must contain TOML key/value settings.")
    return _coerce(raw)


def write_config(path: Path | None = None, *, force: bool = False) -> Path:
    path = path or default_config_path()
    if path.exists() and not force:
        raise ConfigurationError(f"Config already exists: {path}. Use --force to replace it.")
    _write_document(path, settings_template())
    return path


def save_config(path: Path, cfg: Config) -> None:
    validate_config(cfg)
    try:
        document = _read_document(path) if path.exists() else settings_template()
    except (OSError, UnicodeError, tomlkit.exceptions.ParseError) as exc:
        raise ConfigurationError(f"Cannot edit settings {path}: {exc}") from exc
    defaults = Config()
    for spec in fields(Config):
        value = getattr(cfg, spec.name)
        toml_value = list(value) if isinstance(value, tuple) else value
        if value == getattr(defaults, spec.name):
            if spec.name in document and document[spec.name] != toml_value:
                document.pop(spec.name)
        else:
            if spec.name in document:
                document[spec.name] = toml_value
            else:
                document.add(spec.name, tomlkit.item(list(value) if isinstance(value, tuple) else value).comment(spec.metadata["help"]))
    _write_document(path, document)


def _read_document(path: Path):
    if path.stat().st_size > 65536:
        raise ConfigurationError("Settings exceed 64 KiB. Keep only configuration and short comments in this file.")
    return tomlkit.parse(path.read_text(encoding="utf-8-sig"))


def settings_template():
    document = tomlkit.document()
    document.add(tomlkit.comment("CAC settings: uncomment a line to override the built-in default."))
    document.add(tomlkit.comment("Saved changes apply automatically. Invalid settings pause continuation until repaired."))
    document.add(tomlkit.nl())
    defaults = Config()
    for spec in fields(Config):
        value = getattr(defaults, spec.name)
        if value is None:
            value = "C:/Path/To/codex.exe"
        line = tomlkit.dumps({spec.name: list(value) if isinstance(value, tuple) else value}).strip()
        document.add(tomlkit.comment(f"{line}  # {spec.metadata['help']}"))
    return document


def _write_document(path: Path, document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=".settings-", suffix=".tmp", delete=False) as handle:
        tmp = Path(handle.name)
        try:
            handle.write(tomlkit.dumps(document))
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            handle.close()
            tmp.unlink(missing_ok=True)
            raise
    try:
        replace_file(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def initialize_files(path: Path) -> Config:
    cfg = load_config(path)
    prompt = prompt_path(cfg, path)
    if not prompt.exists():
        if cfg.prompt_file != Config().prompt_file:
            raise ConfigurationError("The configured custom prompt is missing. Use Modify Prompt to create it, or repair its path in settings.")
        prompt.parent.mkdir(parents=True, exist_ok=True)
        with prompt.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(DEFAULT_CONTINUE_PROMPT + "\n")
    read_prompt(prompt)
    return cfg
