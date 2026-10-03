from __future__ import annotations

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import sys
import os
import subprocess
import time
from pathlib import Path

from . import __version__
from .codex import codex_version, ensure_daemon, find_codex
from .config import default_config_path, load_config, lock_path, log_path, state_path, stop_path, write_config
from .errors import AutoContinuerError
from .instance_lock import SingleInstanceLock, is_running
from .state import load_state
from .startup import _pythonw, install_startup, uninstall_startup
from .supervisor import Supervisor, _parse_rate_limits, observed_interactive_sources
from .appserver import AppServerClient


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-auto-continuer")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, default=None, help="Config JSON path (default: per-user app data).")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="Run continuously.")
    run.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    sub.add_parser("once", help="Run one supervisor cycle and exit.")
    sub.add_parser("start", help="Start one hidden background supervisor on Windows.")
    sub.add_parser("stop", help="Stop the supervisor after its current cycle; keep pending obligations.")
    sub.add_parser("status", help="Read current Codex quota/source state and pending obligations.")
    sub.add_parser("config-path", help="Print the effective config path.")
    init = sub.add_parser("init", help="Write a default config file.")
    init.add_argument("--force", action="store_true")
    sub.add_parser("install-startup", help="Install per-user Windows Startup launcher.")
    sub.add_parser("uninstall-startup", help="Remove the managed Windows Startup launcher.")
    return parser


def _setup_logging(background: bool = False) -> None:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [RotatingFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8")]
    if not background:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def _status(config_path: Path | None) -> int:
    cfg = load_config(config_path)
    codex_bin = find_codex()
    cli_version = codex_version(codex_bin, cfg.codex_command_timeout_seconds)
    daemon = ensure_daemon(codex_bin, cfg.codex_command_timeout_seconds, cfg.auto_start_daemon)
    client = AppServerClient.connect(daemon.socket_path, cfg.rpc_timeout_seconds)
    try:
        limits = _parse_rate_limits(client.rate_limits())
        sources = observed_interactive_sources(client)
    finally:
        client.close()
    state = load_state(state_path())
    output = {
        "cliVersion": cli_version,
        "appServerUserAgent": client.user_agent,
        "ordinaryUsageAllowed": limits.ordinary_usage_allowed,
        "nextResetAt": limits.next_reset_at,
        "observedInteractiveSources": sources,
        "pendingObligations": [
            {
                "threadId": x.thread_id,
                "failedTurnId": x.failed_turn_id,
                "phase": x.phase,
                "resetAt": x.reset_at,
            }
            for x in state.obligations
        ],
        "configPath": str(config_path or default_config_path()),
        "statePath": str(state_path()),
        "logPath": str(log_path()),
        "lockPath": str(lock_path()),
        "supervisorRunning": is_running(lock_path()),
    }
    print(json.dumps(output, indent=2))
    return 0


def _start(config_file: Path | None) -> int:
    if os.name != "nt":
        raise AutoContinuerError("Hidden background start is supported only on Windows.")
    config_file = (config_file or default_config_path()).resolve()
    load_config(config_file)
    if is_running(lock_path()):
        print("The supervisor is already running.")
        return 0
    process = subprocess.Popen(
        [str(_pythonw()), "-m", "codex_auto_continuer", "--config", str(config_file), "run", "--background"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AutoContinuerError(f"Background supervisor exited during startup. Read {log_path()} and run `status`.")
        if is_running(lock_path()):
            print(f"Background supervisor started (PID {process.pid}). Log: {log_path()}")
            return 0
        time.sleep(0.1)
    process.terminate()
    process.wait(timeout=5)
    raise AutoContinuerError(f"Background supervisor did not acquire its instance lock in 10s. Read {log_path()}.")


def _stop() -> int:
    if not is_running(lock_path()):
        print("The supervisor is not running.")
        return 0
    stop_path().write_text("stop\n", encoding="ascii")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if not is_running(lock_path()):
            print("Supervisor stopped. Pending obligations are preserved.")
            return 0
        time.sleep(0.2)
    raise AutoContinuerError(f"Stop requested, but the current cycle is still finishing after 60s. Check {log_path()}.")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = args.command or "run"
    background = bool(getattr(args, "background", False))
    try:
        if command == "config-path":
            print(args.config or default_config_path())
            return 0
        if command == "init":
            print(write_config(args.config or default_config_path(), force=args.force))
            return 0
        if command == "install-startup":
            print(install_startup(args.config))
            return 0
        if command == "uninstall-startup":
            print(uninstall_startup())
            return 0

        _setup_logging(background)
        if command == "start":
            return _start(args.config)
        if command == "stop":
            return _stop()
        if command == "status":
            return _status(args.config)

        cfg = load_config(args.config)
        with SingleInstanceLock(lock_path()):
            stop_path().unlink(missing_ok=True)
            supervisor = Supervisor(cfg, state_path())
            try:
                if command == "once":
                    supervisor.connect()
                    result = supervisor.run_cycle()
                    print(json.dumps(result.__dict__, indent=2))
                    return 0
                supervisor.run_forever(stop_path().exists)
                return 0
            finally:
                supervisor.close()
    except KeyboardInterrupt:
        return 130
    except (AutoContinuerError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        if not background:
            print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
