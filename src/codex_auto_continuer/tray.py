from __future__ import annotations

import ctypes
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

from . import __version__, telemetry
from .config import Config, control_dir, initialize_files, load_config, lock_path
from .errors import AutoContinuerError, AlreadyRunningError
from .icon import tray_image
from .instance_lock import SingleInstanceLock, is_running
from .startup import launch_command, startup_path


def message(text: str, *, error: bool = False, confirm: bool = False) -> bool:
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    flags = 0x24 if confirm else 0x10 if error else 0x40
    return api.MessageBoxW(None, text, "Codex Auto Continuer", flags) == 6


class TrayController:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.cfg = initialize_files(config_file)
        self.busy = False
        self.done = threading.Event()
        self.actions: queue.Queue[tuple[str, tuple[str, ...]]] = queue.Queue()
        self.state = "stopped"
        self.icon = None
        self._last_phase = None
        self._log_settings = (self.cfg.detailed_telemetry, self.cfg.log_max_mb, self.cfg.log_backups)

    def command(self, *arguments: str) -> str:
        process = subprocess.Popen(launch_command(self.config_file, *arguments, console=True),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", errors="replace", cwd=self.config_file.parent,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        timeout = 120 if arguments[0] in {"once", "scan"} else 90
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                           timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
            raise AutoContinuerError("Control command timed out; its process tree was stopped. Check local telemetry before retrying.") from exc
        telemetry.emit("tray.command_completed", command=arguments[0], exitCode=process.returncode)
        if process.returncode:
            raise AutoContinuerError((stderr or stdout).strip() or "Control command failed. Open the telemetry folder for details.")
        return stdout.strip()

    def enqueue(self, label: str, *arguments: str) -> None:
        if not self.busy:
            self.busy = True
            self.actions.put((label, arguments))
            if self.icon:
                self.icon.update_menu()

    def worker(self) -> None:
        while not self.done.is_set():
            try:
                label, arguments = self.actions.get(timeout=0.5)
            except queue.Empty:
                continue
            telemetry.emit("tray.action", action=label)
            try:
                if label == "quit":
                    self.command("stop")
                    self.done.set()
                    self.icon.stop()
                    return
                if label == "reset" and not message("Restore default settings? Your Markdown prompt and pending obligations will be preserved.", confirm=True):
                    continue
                output = self.command(*arguments)
                if label in {"status", "locations", "once", "init", "reset"}:
                    if label == "status":
                        value = json.loads(output)
                        output = (f"Monitoring: {'running' if value['supervisorRunning'] else 'stopped'}\n"
                                  f"Ordinary usage allowed: {value['ordinaryUsageAllowed']}\n"
                                  f"Pending continuations: {len(value['pendingObligations'])}\n"
                                  f"Scope: {value['threadScope']}\n"
                                  f"Detailed local telemetry: {value['detailedTelemetry']}\n\n"
                                  f"Prompt: {value['promptPath']}\nTelemetry: {value['logPath']}\n\n"
                                  "Full status is available through the companion CLI EXE.")
                    message(output)
                self.cfg = load_config(self.config_file)
            except Exception as exc:
                telemetry.failure("tray.action_failed", exc, action=label)
                message(str(exc), error=True)
            finally:
                self.busy = False
                if self.icon and not self.done.is_set():
                    self.refresh()

    def refresh(self) -> None:
        phase = "stopped"
        waiting = 0
        try:
            self.cfg = load_config(self.config_file)
            log_settings = (self.cfg.detailed_telemetry, self.cfg.log_max_mb, self.cfg.log_backups)
            if log_settings != self._log_settings:
                telemetry.setup(self.config_file.parent / "tray.jsonl", self.cfg)
                self._log_settings = log_settings
            snapshot_path = self.config_file.parent / "runtime-status.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else {}
            if is_running(lock_path()):
                phase = "monitoring"
                waiting = snapshot.get("pending", 0)
                if waiting:
                    phase = "waiting"
            elif snapshot.get("phase") == "failed":
                phase = "failed"
        except Exception as exc:
            phase = "failed"
            if self._last_phase != phase:
                telemetry.failure("tray.status_failed", exc)
        if self.icon:
            self.icon.title = f"Codex Auto Continuer {__version__}: {phase}; {waiting} pending"
            if phase != self.state:
                self.icon.icon = tray_image(phase)
            if phase == "failed" and self._last_phase != "failed":
                self.icon.notify("Monitoring stopped or settings could not be read. Open telemetry and settings, then restart monitoring.")
            self.icon.update_menu()
        self.state = phase
        self._last_phase = phase

    def watch(self) -> None:
        while not self.done.wait(2):
            self.refresh()

    def menu(self):
        from pystray import Menu, MenuItem as Item
        def action(label, *arguments):
            return lambda icon, item: self.enqueue(label, *arguments)
        available = lambda item: not self.busy
        return Menu(
            Item(lambda item: f"Monitoring: {self.state}", None, enabled=False),
            Item("Status", action("status", "status"), default=True, enabled=available),
            Menu.SEPARATOR,
            Item("Start monitoring", action("start", "start"), enabled=lambda item: not self.busy and not is_running(lock_path())),
            Item("Stop monitoring", action("stop", "stop"), enabled=lambda item: not self.busy and is_running(lock_path())),
            Item("Restart monitoring", action("restart", "restart"), enabled=available),
            Item("Scan now", action("scan", "scan"), enabled=available),
            Item("Run one cycle", action("once", "once"), enabled=lambda item: not self.busy and not is_running(lock_path())),
            Menu.SEPARATOR,
            Item("Modify prompt", action("prompt", "modify-prompt"), enabled=available),
            Item("Open settings", action("settings", "open-config"), enabled=available),
            Item("Open telemetry folder", action("logs", "open-logs"), enabled=available),
            Item("Show config location", action("locations", "config-path"), enabled=available),
            Item("Initialize missing files", action("init", "init"), enabled=available),
            Item("Restore default settings", action("reset", "init", "--force"), enabled=lambda item: not self.busy and not is_running(lock_path())),
            Item("Monitor clients", Menu(
                Item("CLI, VS Code and Desktop", action("scope", "scope", "allInteractive"), radio=True,
                     checked=lambda item: self.cfg.thread_scope == "allInteractive", enabled=available),
                Item("Desktop only", action("scope", "scope", "desktop"), radio=True,
                     checked=lambda item: self.cfg.thread_scope == "desktop", enabled=available))),
            Item("Detailed local telemetry", lambda icon, item: self.enqueue("privacy", "logging", "private" if self.cfg.detailed_telemetry else "detailed"),
                 checked=lambda item: self.cfg.detailed_telemetry, enabled=available),
            Item("Start with Windows", lambda icon, item: self.enqueue("startup", "uninstall-startup" if startup_path().exists() else "install-startup"),
                 checked=lambda item: startup_path().exists(), enabled=available),
            Menu.SEPARATOR,
            Item(f"About {__version__}", lambda icon, item: message("Codex Auto Continuer\nLocal quota-recovery supervisor.\nNo remote telemetry or credential collection.")),
            Item("Quit (stop monitoring)", action("quit"), enabled=available),
        )


def run_tray(config_file: Path) -> int:
    if os.name != "nt":
        raise AutoContinuerError("The system tray application currently supports Windows only.")
    from pystray import Icon
    try:
        with SingleInstanceLock(control_dir() / "tray.lock"):
            controller = TrayController(config_file)
            telemetry.setup(config_file.parent / "tray.jsonl", controller.cfg)
            telemetry.emit("tray.started", configPath=str(config_file))
            controller.icon = Icon("CodexAutoContinuer", tray_image("stopped"), "Codex Auto Continuer", menu=controller.menu())
            def ready(icon):
                icon.visible = True
                telemetry.emit("tray.ready", menuItems=[item.text for item in icon.menu.items])
                threading.Thread(target=controller.worker, name="tray-controls", daemon=True).start()
                threading.Thread(target=controller.watch, name="tray-status", daemon=True).start()
                controller.enqueue("start", "start")
            try:
                controller.icon.run(setup=ready)
            finally:
                controller.done.set()
                telemetry.emit("tray.closed")
            return 0
    except AlreadyRunningError:
        message("Codex Auto Continuer is already in the system tray. Look in Windows' hidden tray icons if it is not visible.")
        return 0
