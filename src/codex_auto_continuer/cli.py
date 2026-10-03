from __future__ import annotations

import argparse
import json
import logging
import sys
import os
import subprocess
import time
from dataclasses import asdict, replace
from pathlib import Path

from . import __version__
from .codex import codex_version, ensure_daemon, find_codex
from .config import (default_config_path, load_config, lock_path, log_path, state_path, stop_path,
                     write_config, initialize_files, prompt_path, read_prompt, save_config, scan_path, owner_path)
from .errors import AutoContinuerError
from .instance_lock import SingleInstanceLock, is_running
from .state import load_state
from .startup import launch_command, install_startup, uninstall_startup, startup_path
from .supervisor import Supervisor, _parse_rate_limits, observed_interactive_sources
from .appserver import AppServerClient
from . import telemetry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-auto-continuer")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, default=None, help="Config JSON path; state, prompt and logs use its directory.")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="Run continuously.")
    run.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    sub.add_parser("once", help="Run one supervisor cycle and exit.")
    sub.add_parser("start", help="Start one hidden background supervisor on Windows.")
    sub.add_parser("stop", help="Stop the supervisor after its current cycle; keep pending obligations.")
    sub.add_parser("restart", help="Restart monitoring with saved settings.")
    sub.add_parser("status", help="Read current Codex quota/source state and pending obligations.")
    sub.add_parser("config-path", help="Print the effective config path.")
    init = sub.add_parser("init", help="Write a default config file.")
    init.add_argument("--force", action="store_true")
    sub.add_parser("install-startup", help="Install per-user Windows Startup launcher.")
    sub.add_parser("uninstall-startup", help="Remove the managed Windows Startup launcher.")
    sub.add_parser("tray", help="Open the system tray tool and start monitoring.")
    sub.add_parser("modify-prompt", help="Open the Markdown continuation prompt with its associated editor.")
    sub.add_parser("open-config", help="Open settings with the associated JSON editor.")
    sub.add_parser("open-logs", help="Open the local telemetry folder.")
    sub.add_parser("scan", help="Wake the running supervisor for a scan, or run one cycle if stopped.")
    scope = sub.add_parser("scope", help="Select clients and restart the running supervisor.")
    scope.add_argument("value", choices=["allInteractive", "desktop"])
    privacy = sub.add_parser("logging", help="Select local telemetry privacy and restart the running supervisor.")
    privacy.add_argument("value", choices=["private", "detailed"])
    return parser


def _setup_logging(background: bool = False) -> None:
    handlers: list[logging.Handler] = [] if background else [logging.StreamHandler()]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def _status(config_path: Path | None) -> int:
    cfg = load_config(config_path)
    codex_bin = find_codex(cfg.codex_executable)
    cli_version = codex_version(codex_bin, cfg.codex_command_timeout_seconds)
    daemon = ensure_daemon(codex_bin, cfg.codex_command_timeout_seconds, cfg.auto_start_daemon)
    client = AppServerClient.connect(daemon.socket_path, cfg.rpc_timeout_seconds)
    try:
        limits = _parse_rate_limits(client.rate_limits())
        sources = observed_interactive_sources(client)
    finally:
        client.close()
    state = load_state(state_path(config_path))
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
        "statePath": str(state_path(config_path)),
        "logPath": str(log_path(config_path)),
        "lockPath": str(lock_path()),
        "supervisorRunning": is_running(lock_path()),
        "threadScope": cfg.thread_scope,
        "detailedTelemetry": cfg.detailed_telemetry,
        "promptPath": str(prompt_path(cfg, config_path)),
        "startupInstalled": startup_path().exists() if os.name == "nt" else False,
        "deliveryObservations": len(state.observations),
    }
    print(json.dumps(output, indent=2))
    return 0


def _start(config_file: Path | None) -> int:
    if os.name != "nt":
        raise AutoContinuerError("Hidden background start is supported only on Windows.")
    config_file = (config_file or default_config_path()).resolve()
    load_config(config_file)
    if is_running(lock_path()):
        _check_owner(config_file)
        print("The supervisor is already running.")
        return 0
    process = subprocess.Popen(
        launch_command(config_file, "run", "--background"),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AutoContinuerError(f"Background supervisor exited during startup. Read {log_path(config_file)} and run `status`.")
        if is_running(lock_path()):
            print(f"Background supervisor started (PID {process.pid}). Log: {log_path(config_file)}")
            return 0
        time.sleep(0.1)
    process.terminate()
    process.wait(timeout=5)
    raise AutoContinuerError(f"Background supervisor did not acquire its instance lock in 10s. Read {log_path(config_file)}.")


def _check_owner(config_file: Path) -> None:
    try:
        owner = json.loads(owner_path().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AutoContinuerError("A supervisor is running but its owner record cannot be verified. Stop it before starting another copy.") from exc
    if owner.get("configPath") != str(config_file.resolve()):
        raise AutoContinuerError(f"Another copy is monitoring with {owner.get('configPath')}. Stop that copy before starting this one.")


def _snapshot(config_file: Path, **fields) -> None:
    target = config_file.parent / "runtime-status.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps({"pid": os.getpid(), "updatedAt": time.time(), **fields}, indent=2), encoding="utf-8")
    os.replace(temporary, target)


def _update_setting(config_file: Path, **changes) -> int:
    running = is_running(lock_path())
    if running:
        _check_owner(config_file)
        _stop()
    cfg = load_config(config_file)
    save_config(config_file, replace(cfg, **changes))
    if running:
        return _start(config_file)
    print("Settings saved.")
    return 0


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
    owns_runtime = False
    try:
        args.config = (args.config or default_config_path()).resolve()
        if command == "config-path":
            print(args.config or default_config_path())
            return 0
        if command == "init":
            if args.force:
                write_config(args.config, force=True)
            initialize_files(args.config)
            print(args.config)
            return 0
        if command == "install-startup":
            print(install_startup(args.config))
            return 0
        if command == "uninstall-startup":
            print(uninstall_startup())
            return 0
        if command == "tray":
            from .tray import run_tray
            return run_tray(args.config)
        if command in {"modify-prompt", "open-config", "open-logs"}:
            cfg = initialize_files(args.config)
            path = {"modify-prompt": prompt_path(cfg, args.config), "open-config": args.config,
                    "open-logs": args.config.parent}[command]
            if os.name != "nt":
                raise AutoContinuerError("Associated-editor actions require Windows.")
            os.startfile(path)
            return 0

        _setup_logging(background)
        if command == "start":
            return _start(args.config)
        if command == "stop":
            return _stop()
        if command == "restart":
            if is_running(lock_path()):
                _check_owner(args.config)
                _stop()
            return _start(args.config)
        if command == "status":
            return _status(args.config)
        if command == "scope":
            return _update_setting(args.config, thread_scope=args.value)
        if command == "logging":
            return _update_setting(args.config, detailed_telemetry=args.value == "detailed")
        if command == "scan" and is_running(lock_path()):
            _check_owner(args.config)
            scan_path().write_text("scan\n", encoding="ascii")
            print("Scan requested.")
            return 0

        cfg = initialize_files(args.config) if not args.config.exists() else load_config(args.config)
        read_prompt(prompt_path(cfg, args.config))
        with SingleInstanceLock(lock_path()):
            owns_runtime = True
            stop_path().unlink(missing_ok=True)
            scan_path().unlink(missing_ok=True)
            owner_path().write_text(json.dumps({"pid": os.getpid(), "configPath": str(args.config)}), encoding="utf-8")
            telemetry.setup(log_path(args.config), cfg)
            telemetry.emit("monitor.settings", **asdict(cfg), configPath=str(args.config))
            def on_cycle(result):
                _snapshot(args.config, phase="monitoring", **result.__dict__)
            def wake_requested():
                if scan_path().exists():
                    scan_path().unlink(missing_ok=True)
                    telemetry.emit("monitor.scan_requested")
                    return True
                return False
            supervisor = Supervisor(cfg, state_path(args.config), prompt_file=prompt_path(cfg, args.config), on_cycle=on_cycle)
            try:
                _snapshot(args.config, phase="starting")
                if command in {"once", "scan"}:
                    supervisor.connect()
                    result = supervisor.run_cycle()
                    print(json.dumps(result.__dict__, indent=2))
                    return 0
                supervisor.run_forever(stop_path().exists, wake_requested)
                return 0
            finally:
                supervisor.close()
                telemetry.emit("monitor.stopped")
                _snapshot(args.config, phase="stopped")
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        telemetry.failure("command.failed", exc, command=command)
        if owns_runtime:
            _snapshot(args.config, phase="failed", errorType=type(exc).__name__)
        logging.getLogger(__name__).error("%s", exc)
        if command == "tray" and os.name == "nt":
            from .tray import message
            message(str(exc), error=True)
        if not background:
            print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
