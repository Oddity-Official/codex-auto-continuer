from __future__ import annotations

import argparse
import json
import logging
import sys
import os
import subprocess
import time
import uuid
import tempfile
from dataclasses import asdict, replace
from pathlib import Path

from . import __version__
from .codex import codex_version, ensure_daemon, find_codex
from .config import (default_config_path, load_config, lock_path, log_path, state_path, stop_path,
                     Config, ALL_CLIENTS, write_config, initialize_files, prompt_path, read_prompt, save_config, scan_path, owner_path)
from .errors import AutoContinuerError
from .instance_lock import SingleInstanceLock, is_running
from .state import load_state
from .startup import launch_command, install_startup, uninstall_startup, startup_path
from .supervisor import Supervisor, _parse_rate_limits, observed_interactive_sources
from .appserver import AppServerClient
from . import telemetry
from .actions import open_local
from .status import read_runtime, owns_monitor, phase
from .compatibility import CompatibilityGate
from .atomic import replace_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-auto-continuer")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, default=None, help="TOML settings path; state, prompt and logs use its directory.")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="Run continuously.")
    run.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    sub.add_parser("once", help="Run one supervisor cycle and exit.")
    sub.add_parser("start", help="Start one hidden background supervisor on Windows.")
    sub.add_parser("stop", help="Stop the supervisor after its current cycle; keep pending obligations.")
    sub.add_parser("restart", help="Restart monitoring with saved settings.")
    status = sub.add_parser("status", help="Read local monitoring status and pending obligations.")
    status.add_argument("--live", action="store_true", help="Also request fresh quota/source information from Codex.")
    sub.add_parser("config-path", help="Print the effective config path.")
    init = sub.add_parser("init", help="Write a default config file.")
    init.add_argument("--force", action="store_true")
    sub.add_parser("install-startup", help="Install per-user Windows Startup launcher.")
    sub.add_parser("uninstall-startup", help="Remove the managed Windows Startup launcher.")
    tray = sub.add_parser("tray", help="Open the system tray tool and start monitoring.")
    tray.add_argument("--no-monitor", action="store_true", help=argparse.SUPPRESS)
    sub.add_parser("modify-prompt", help="Open the Markdown continuation prompt with its associated editor.")
    sub.add_parser("open-config", help="Create annotated TOML settings if missing and open the editor.")
    sub.add_parser("open-logs", help="Open the local telemetry folder.")
    sub.add_parser("scan", help="Wake the running supervisor for a scan, or run one cycle if stopped.")
    clients = sub.add_parser("clients", help="Select any client combination, all, or no clients to pause.")
    clients.add_argument("values", nargs="*", choices=[*ALL_CLIENTS, "all"])
    privacy = sub.add_parser("logging", help="Select local telemetry privacy for subsequent events.")
    privacy.add_argument("value", choices=["private", "detailed"])
    reset = sub.add_parser("restore-defaults", help="Restore settings, preserving the prompt, pending work, logs and startup shortcut.")
    reset.add_argument("--prompt-file", help=argparse.SUPPRESS)
    policy = sub.add_parser("compatibility", help="Select balanced or strict Codex compatibility policy.")
    policy.add_argument("value", choices=["balanced", "strict"])
    update = sub.add_parser("update", help="Check/install signed stable portable CAC releases, or recover an interrupted update.")
    update.add_argument("action", choices=["check", "stage", "apply", "install", "recover"])
    update.add_argument("job", type=Path, nargs="?", help="Owned job.json path, required only for recover.")
    worker = sub.add_parser("_update-worker", help=argparse.SUPPRESS)
    worker.add_argument("job", type=Path)
    worker.add_argument("--recover", action="store_true")
    return parser


def _setup_logging(background: bool = False) -> None:
    handlers: list[logging.Handler] = [] if background else [logging.StreamHandler()]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def _status(config_path: Path, live: bool = False) -> int:
    cfg = load_config(config_path)
    snapshot = read_runtime(config_path)
    state = load_state(state_path(config_path))
    output = {
        "version": __version__, "phase": phase(config_path, snapshot),
        "compatibility": snapshot.get("compatibility"),
        "reason": snapshot.get("reason"),
        "ordinaryUsageAllowed": snapshot.get("ordinary_usage_allowed"),
        "nextResetAt": snapshot.get("next_reset_at"),
        "lastScanAt": snapshot.get("lastScanAt"), "lastScan": snapshot.get("lastScan"),
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
        "supervisorRunning": owns_monitor(config_path),
        "clients": list(cfg.clients),
        "detailedTelemetry": cfg.detailed_telemetry,
        "promptPath": str(prompt_path(cfg, config_path)),
        "startupInstalled": startup_path().exists() if os.name == "nt" else False,
        "deliveryObservations": len(state.observations),
        "warnings": snapshot.get("warnings", []),
    }
    from .updates import update_status
    output["updates"] = update_status(config_path)
    if live:
        codex_bin = find_codex(cfg.codex_executable)
        output["cliVersion"] = codex_version(codex_bin, cfg.codex_command_timeout_seconds)
        daemon = ensure_daemon(codex_bin, cfg.codex_command_timeout_seconds, cfg.auto_start_daemon)
        client = AppServerClient.connect(daemon.socket_path, cfg.rpc_timeout_seconds)
        try:
            report = CompatibilityGate(config_path.parent / "compatibility-cache").recheck(
                codex_bin, client.user_agent, cfg.codex_command_timeout_seconds, cfg.compatibility_policy)
            output["compatibility"] = report.report()
            if report.read_allowed:
                limits = _parse_rate_limits(client.rate_limits())
                output.update(ordinaryUsageAllowed=limits.ordinary_usage_allowed, nextResetAt=limits.next_reset_at,
                              observedInteractiveSources=observed_interactive_sources(client), appServerUserAgent=client.user_agent)
        finally:
            client.close()
    print(json.dumps(output, indent=2))
    return 2 if live and not output["compatibility"]["dispatch_allowed"] else 0


def _start(config_file: Path | None) -> int:
    if os.name != "nt":
        raise AutoContinuerError("Hidden background start is supported only on Windows.")
    config_file = (config_file or default_config_path()).resolve()
    load_config(config_file)
    if is_running(lock_path()):
        _check_owner(config_file)
        print("The supervisor is already running.")
        return 0
    initialize_files(config_file)
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
    replace_file(temporary, target)


def _update_setting(config_file: Path, **changes) -> int:
    running = is_running(lock_path())
    if running:
        _check_owner(config_file)
    cfg = load_config(config_file)
    save_config(config_file, replace(cfg, **changes))
    print("Settings saved; monitoring applies valid changes automatically." if running else "Settings saved.")
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


def _request_scan(config_file: Path) -> int:
    # Serialize requesters, not the monitor, so no caller's acknowledgement is overwritten.
    with SingleInstanceLock(scan_path().with_suffix(".lock")):
        _check_owner(config_file)
        request_id = uuid.uuid4().hex
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=scan_path().parent,
                                         prefix=".scan-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(request_id)
        try:
            os.replace(temporary, scan_path())
        finally:
            temporary.unlink(missing_ok=True)
        print("Scan requested; waiting for completion.", flush=True)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            snapshot = read_runtime(config_file)
            if snapshot.get("scanRequestId") == request_id:
                print(json.dumps(snapshot.get("lastScan", {}), indent=2))
                compatibility = snapshot.get("compatibility") or {}
                return 2 if compatibility and not compatibility.get("dispatch_allowed") else 0
            if not owns_monitor(config_file) or (snapshot.get("phase") == "failed" and not snapshot.get("compatibility")):
                raise AutoContinuerError("The scan could not complete. Read Status for the blocking issue and local telemetry for diagnostics.")
            time.sleep(0.1)
        raise AutoContinuerError("Scan was requested but completion was not observed within 60 seconds. Read status and telemetry; do not assume it completed.")


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
        if command == "_update-worker":
            from .update_install import run_worker
            return run_worker(args.job.resolve(), recover=args.recover)
        if command == "update":
            from .updates import check_release, launch_update, update_status, write_json, UpdateError
            from .config import control_dir
            if args.action == "recover":
                if args.job is None:
                    raise UpdateError("Use update recover with the owned job.json path shown in update-status.json.")
                from .update_install import run_worker
                return run_worker(args.job.resolve(), recover=True)
            if args.action == "install":
                if args.job is None:
                    raise UpdateError("update install requires a verified staged job.json path.")
                from .update_install import validate_job
                request, app, config, bundle, manifest = validate_job(args.job.resolve())
                if config != args.config or app != Path(sys.executable).resolve().parent or request.get("status") != "staged":
                    raise UpdateError("Staged update does not belong to this app/config or was already started.")
                ready = args.config.parent / "tray-ready.json"
                tray_pid = json.loads(ready.read_text(encoding="utf-8")).get("pid") if ready.exists() else None
                launch_update(args.job.resolve(), tray_pid)
                print(json.dumps({"status": "installing", "version": request["version"]}))
                return 0
            if args.job is not None:
                raise UpdateError("A job path is only accepted for update install or recover.")
            with SingleInstanceLock(control_dir() / "update.lock"):
                try:
                    result = check_release(args.config, load_config(args.config), stage=args.action in {"apply", "stage"})
                except UpdateError as exc:
                    write_json(args.config.parent / "update-status.json", {"status": "unavailable", "reason": str(exc), "checkedAt": time.time()})
                    raise
                write_json(args.config.parent / "update-status.json", result)
                if result["status"] == "staged" and args.action == "apply":
                    ready = args.config.parent / "tray-ready.json"
                    tray_pid = json.loads(ready.read_text(encoding="utf-8")).get("pid") if ready.exists() else None
                    launch_update(Path(result["job"]), tray_pid)
                print(json.dumps(result, indent=2))
            return 0
        if command == "init":
            if args.force or not args.config.exists():
                write_config(args.config, force=args.force)
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
            return run_tray(args.config, start_monitor=not args.no_monitor)
        if command in {"modify-prompt", "open-config", "open-logs"}:
            open_local(command, args.config)
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
            return _status(args.config, args.live)
        if command == "clients":
            if "all" in args.values and len(args.values) != 1:
                raise AutoContinuerError("Use clients all alone, or a combination of vscode, cli and desktop.")
            return _update_setting(args.config, clients=ALL_CLIENTS if args.values == ["all"] else tuple(args.values))
        if command == "logging":
            return _update_setting(args.config, detailed_telemetry=args.value == "detailed")
        if command == "compatibility":
            return _update_setting(args.config, compatibility_policy=args.value)
        if command == "restore-defaults":
            if is_running(lock_path()):
                _check_owner(args.config)
            selected_prompt = args.prompt_file or load_config(args.config).prompt_file
            write_config(args.config, force=True)
            save_config(args.config, replace(Config(), prompt_file=selected_prompt))
            print("Default settings restored. Prompt, pending work, logs and login shortcut are unchanged.")
            return 0
        if command == "scan" and is_running(lock_path()):
            return _request_scan(args.config)

        cfg = initialize_files(args.config)
        read_prompt(prompt_path(cfg, args.config))
        with SingleInstanceLock(lock_path()):
            owns_runtime = True
            stop_path().unlink(missing_ok=True)
            scan_path().unlink(missing_ok=True)
            owner_path().write_text(json.dumps({"pid": os.getpid(), "configPath": str(args.config)}), encoding="utf-8")
            telemetry.setup(log_path(args.config), cfg)
            telemetry.emit("monitor.settings", **asdict(cfg), configPath=str(args.config))
            last_result = {}
            last_scan_at = None
            completed_scan = None
            requested_scan = None
            def on_cycle(result):
                nonlocal last_result, last_scan_at, completed_scan, requested_scan
                last_result = result.__dict__
                last_scan_at = time.time()
                completed_scan = requested_scan or completed_scan
                requested_scan = None
                current_phase = "paused" if not supervisor.config.clients else "waiting" if result.pending else "monitoring"
                compatibility = result.compatibility or {}
                if compatibility and not compatibility.get("dispatch_allowed"):
                    current_phase = "failed"
                _snapshot(args.config, phase=current_phase, **last_result, lastScan=dict(last_result),
                          lastScanAt=last_scan_at, scanRequestId=completed_scan,
                          reason=compatibility.get("reason") if current_phase == "failed" else None)
            def settings_stamp():
                paths = (args.config, prompt_path(cfg, args.config))
                signatures = []
                for path in paths:
                    try:
                        stat = path.stat()
                        signatures.append((stat.st_mtime_ns, stat.st_size))
                    except FileNotFoundError:
                        signatures.append(None)
                return tuple(signatures)
            stamp = settings_stamp()
            def wake_requested():
                nonlocal stamp, requested_scan
                if scan_path().exists():
                    requested_scan = scan_path().read_text(encoding="ascii").strip()
                    scan_path().unlink(missing_ok=True)
                    telemetry.emit("monitor.scan_requested")
                    return True
                current_stamp = settings_stamp()
                if current_stamp != stamp:
                    stamp = current_stamp
                    return True
                return False
            def reload_settings():
                nonlocal cfg
                updated = load_config(args.config)
                read_prompt(prompt_path(updated, args.config))
                if updated != cfg:
                    log_settings = (updated.detailed_telemetry, updated.diagnostic_trace, updated.log_max_mb, updated.log_backups)
                    previous = (cfg.detailed_telemetry, cfg.diagnostic_trace, cfg.log_max_mb, cfg.log_backups)
                    if log_settings != previous:
                        telemetry.setup(log_path(args.config), updated)
                    cfg = updated
                    telemetry.emit("monitor.settings_changed", **asdict(cfg))
                return updated
            def on_pause():
                _snapshot(args.config, phase="failed", errorType="ConfigurationError", lastScan=last_result,
                          lastScanAt=last_scan_at, reason="Settings or prompt need repair. Modify Settings or Modify Prompt, then save.")
            def on_phase(value):
                _snapshot(args.config, phase=value, lastScan=last_result, lastScanAt=last_scan_at,
                          scanRequestId=completed_scan)
            supervisor = Supervisor(cfg, state_path(args.config), prompt_file=prompt_path(cfg, args.config), on_cycle=on_cycle)
            try:
                _snapshot(args.config, phase="starting")
                if command in {"once", "scan"}:
                    supervisor.connect()
                    result = supervisor.run_cycle()
                    on_cycle(result)
                    print(json.dumps(result.__dict__, indent=2))
                    return 0 if supervisor.compatibility.dispatch_allowed else 2
                supervisor.run_forever(stop_path().exists, wake_requested, reload_settings, on_pause, on_phase)
                return 0
            finally:
                supervisor.close()
                try:
                    telemetry.emit("monitor.stopped")
                finally:
                    _snapshot(args.config, phase="stopped", lastScan=last_result, lastScanAt=last_scan_at,
                              scanRequestId=completed_scan)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        try:
            telemetry.failure("command.failed", exc, command=command)
        except OSError:
            pass  # The independent runtime snapshot and stderr report logging failures too.
        if owns_runtime:
            try:
                _snapshot(args.config, phase="failed", errorType=type(exc).__name__,
                          reason="Monitoring stopped. Check settings, free space, permissions and local telemetry, then start after repair.")
            except OSError:
                pass  # Do not hide the original failure if the entire data folder is unwritable.
        logging.getLogger(__name__).error("%s", exc)
        if command == "tray" and os.name == "nt":
            from .tray import message
            message(str(exc), error=True)
        if not background:
            print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
