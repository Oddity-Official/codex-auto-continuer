from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .codex import codex_version, ensure_daemon, find_codex
from .config import default_config_path, load_config, lock_path, log_path, state_path, write_config
from .errors import AutoContinuerError
from .instance_lock import SingleInstanceLock
from .state import load_state
from .startup import install_startup, uninstall_startup
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
    handlers: list[logging.Handler] = [logging.FileHandler(path, encoding="utf-8")]
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
    }
    print(json.dumps(output, indent=2))
    return 0


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
        if command == "status":
            return _status(args.config)

        cfg = load_config(args.config)
        supervisor = Supervisor(cfg, state_path())
        with SingleInstanceLock(lock_path()):
            try:
                if command == "once":
                    supervisor.connect()
                    result = supervisor.run_cycle()
                    print(json.dumps(result.__dict__, indent=2))
                    return 0
                supervisor.run_forever()
                return 0
            finally:
                supervisor.close()
    except KeyboardInterrupt:
        return 130
    except AutoContinuerError as exc:
        logging.getLogger(__name__).error("%s", exc)
        if not background:
            print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
