from __future__ import annotations

import os
import hashlib
import json
import queue
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from . import __version__, telemetry
from .actions import open_local
from .config import ALL_CLIENTS, Config, control_dir, initialize_files, load_config
from .dialogs import Dialogs, message
from .errors import AutoContinuerError, AlreadyRunningError
from .icon import tray_image
from .instance_lock import SingleInstanceLock
from .startup import launch_command, startup_path
from .status import read_runtime, owns_monitor, phase
from .presentation import state_label, icon_state, usage_windows
from .updates import update_status, write_json

PRIVACY_TEXT = {
    "detailed": "Detailed local telemetry keeps real chat IDs, names and filesystem paths. This helps trace failures to the exact chat.\n\n",
    "private": "Private local telemetry replaces chat IDs with stable keyed identifiers and omits chat names and filesystem paths. This supports diagnostics without those personal details.\n\n",
}
PRIVACY_FOOTER = (
    "Both modes record scan summaries, changes, timings, continuations and errors. Neither records conversation bodies, prompt text, credentials or raw RPC payloads. Nothing is uploaded.\n\n"
    "Existing logs are not scrubbed or deleted. Apply this mode to future events?"
)


class TrayController:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.problem = ""
        try:
            self.cfg = initialize_files(config_file)
        except Exception as exc:
            # Defaults here are for rendering repair controls, never for dispatch.
            self.cfg = Config()
            self.problem = str(exc)
        self.done = threading.Event()
        self.actions: queue.Queue[tuple[str, tuple[str, ...]]] = queue.Queue()
        self._guard = threading.Lock()
        self._pending = 0
        self._opening: set[str] = set()
        self.busy = False
        self.state = "failed" if self.problem else "stopped"
        self.snapshot: dict = {}
        self.running = False
        self.icon = None
        self.status_window = None
        self._status_unavailable_since = None
        self._icon_state = None
        self.dialogs = Dialogs(on_error=self.dialog_failed)
        self._last_phase = None
        self._log_settings = self.log_settings(self.cfg)
        self._last_update_check = 0
        self._update_busy = False
        self._installing = False
        self._notices = set()
        notice_file = config_file.parent / "notifications.json"
        if notice_file.exists():
            try:
                self._notices = set(json.loads(notice_file.read_text(encoding="utf-8"))["keys"])
            except (OSError, ValueError, KeyError, TypeError):
                self.problem = "Notification history is unreadable. Repair notifications.json in the data folder; monitoring remains independently controlled."

    @staticmethod
    def log_settings(cfg):
        return (cfg.detailed_telemetry, cfg.diagnostic_trace, cfg.log_max_mb, cfg.log_backups)

    def dialog_failed(self, exc):
        if self.icon:
            self.icon.notify(f"A dialog could not open: {exc}. Open Data Folder for diagnostics.", "CAC")

    def command(self, *arguments: str) -> str:
        process = subprocess.Popen(launch_command(self.config_file, *arguments, console=True),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", errors="replace", cwd=self.config_file.parent,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        timeout = 300 if arguments[0] == "update" else 120 if arguments[0] in {"once", "scan"} else 90
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
            raise AutoContinuerError((stderr or stdout).strip() or "Control command failed. Open the data folder for telemetry.")
        return stdout.strip()

    def enqueue(self, label: str, *arguments: str) -> None:
        if self.done.is_set():
            return
        if label == "quit" and self._installing:
            self.icon.notify("CAC is finishing a verified update. Exit will be available after restart or rollback.", "CAC")
            return
        with self._guard:
            self._pending += 1
            self.busy = True
            self.actions.put((label, arguments))

    def worker(self) -> None:
        while not self.done.is_set():
            try:
                label, arguments = self.actions.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                if label == "quit":
                    self.command("stop")
                    self.done.set()
                    self.dialogs.close()
                    if self.status_window:
                        self.status_window.close()
                    self.icon.stop()
                    return
                telemetry.emit("tray.action", action=label)
                if label == "update":
                    self._installing = True
                output = self.command(*arguments)
                if label in {"update", "auto-update"}:
                    result = json.loads(output)
                    if result.get("status") == "staged":
                        self.icon.notify("A signed CAC update is staged. It will restart CAC after the current monitoring cycle; your data stays in place.", "CAC")
                    elif label == "update":
                        self.icon.notify(f"Updates: {result.get('status', 'unknown')}. Select Read Full Status for details.", "CAC")
                if label == "reset":
                    self.icon.notify("Default settings restored. Your prompt, pending work, logs and login shortcut were preserved.", "CAC")
            except Exception as exc:
                if label == "update":
                    self._installing = False
                try:
                    telemetry.failure("tray.action_failed", exc, action=label)
                except OSError:
                    pass  # Repair dialogs must still work when the log destination is broken.
                if label in {"update", "auto-update"}:
                    self.notify_once("update:" + str(exc), str(exc))
                else:
                    self.dialogs.show("action-error", str(exc), error=True)
            finally:
                with self._guard:
                    self._pending -= 1
                    self.busy = self._pending > 0
                if not self.done.is_set():
                    self.refresh()

    def open(self, command: str) -> None:
        with self._guard:
            if command in self._opening or self.done.is_set():
                return
            self._opening.add(command)
        def launch():
            started = time.monotonic()
            try:
                open_local(command, self.config_file)
                telemetry.emit("tray.file_opened", command=command, durationMs=round((time.monotonic() - started) * 1000, 2))
            except Exception as exc:
                try:
                    telemetry.failure("tray.file_open_failed", exc, command=command)
                except OSError:
                    pass
                self.dialogs.show("file-error", str(exc), error=True)
            finally:
                with self._guard:
                    self._opening.discard(command)
        threading.Thread(target=launch, name="CAC-editor", daemon=True).start()

    def refresh(self) -> None:
        self.problem = ""
        reading_status = False
        try:
            self.running = owns_monitor(self.config_file)
            self.cfg = load_config(self.config_file)
            log_settings = self.log_settings(self.cfg)
            if log_settings != self._log_settings:
                telemetry.setup(self.config_file.parent / "tray.jsonl", self.cfg)
                self._log_settings = log_settings
            reading_status = True
            self.snapshot = read_runtime(self.config_file)
            reading_status = False
            from .presentation import pending_threads
            from .state import load_state
            self.snapshot = self.snapshot | {"waitingThreads": pending_threads(load_state(self.config_file.parent / "state.json").obligations)}
            if self._status_unavailable_since is not None:
                telemetry.emit("tray.status_recovered", durationMs=round((time.monotonic() - self._status_unavailable_since) * 1000))
            self._status_unavailable_since = None
            self.state = phase(self.config_file, self.snapshot, running=self.running)
            if self.state == "failed":
                self.problem = self.snapshot.get("reason", "Monitoring stopped with an error. Open the data folder for telemetry, then start monitoring after repair.")
        except Exception as exc:
            from .errors import ConfigurationError
            self.state = "reconnecting" if self.running and reading_status and not isinstance(exc, ConfigurationError) else "failed"
            self.problem = str(exc)
            if self._status_unavailable_since is None:
                self._status_unavailable_since = time.monotonic()
                try:
                    cause = exc.__cause__
                    telemetry.failure("tray.status_failed", exc, causeType=type(cause).__name__ if cause else None,
                                      errorCode=getattr(cause, "winerror", None), errno=getattr(cause, "errno", None))
                except OSError:
                    pass
        if self.icon:
            self.icon.title = f"CAC {__version__}: {self.status_label()}"
            visual = icon_state(self.state, self.snapshot)
            if visual != self._icon_state:
                self.icon.icon = tray_image(visual[0], pending=visual[1])
                self._icon_state = visual
            if self.state == "failed" and self._last_phase != "failed":
                self.icon.notify(self.problem + " Select Read Full Status for details.", "CAC")
            if self.state == "reconnecting" and self._status_unavailable_since is not None and time.monotonic() - self._status_unavailable_since >= 5:
                self.notify_once("status-unavailable:" + str(self.snapshot.get("updatedAt")),
                    "CAC cannot read local status. The monitor is still running, but its progress is unavailable. "
                    "Select Read Full Status for repair details.")
            compatibility = self.snapshot.get("compatibility") or {}
            if compatibility.get("status") == "untested":
                fields = ("contract_scope", "policy", "schema_sha256") if compatibility.get("dispatch_allowed") else ("cli_sha256", "server_sha256")
                key = "compatibility:" + ":".join(str(compatibility.get(field)) for field in fields)
                self.notify_once(key, "This Codex build passes schema checks but has no exact recovery certificate. "
                    + ("Balanced mode continues with runtime checks." if compatibility.get("dispatch_allowed") else "Strict mode blocks writes.")
                    + " Select Read Full Status for details.")
            for warning in self.snapshot.get("warnings", []):
                self.notify_once(warning["key"], warning["message"])
            try:
                updates = update_status(self.config_file)
            except (OSError, AutoContinuerError):
                updates = {"status": "failed", "reason": "Update status is unreadable. Inspect update-status.json; monitoring continues."}
            if updates.get("status") in {"failed", "rolled_back"}:
                self._installing = False
                self.notify_once("update:" + str(updates.get("job")), updates.get("reason", "CAC update was rolled back. Select Read Full Status and inspect the recovery journal; runtime data was preserved."))
        self._last_phase = self.state

    def notify_once(self, key, body):
        fingerprint = hashlib.sha256(key.encode()).hexdigest()
        with self._guard:
            if fingerprint in self._notices:
                return
            # Bound notice history without storing chat names or raw identifiers.
            keys = sorted(self._notices)[-255:] + [fingerprint]
            write_json(self.config_file.parent / "notifications.json", {"keys": keys})
            self._notices = set(keys)
        self.icon.notify(body, "CAC")
        telemetry.emit("tray.notice", key=fingerprint)

    def check_updates(self, *, automatic=False):
        with self._guard:
            if self._update_busy or self.done.is_set():
                return
            self._update_busy = True
        def check():
            try:
                result = json.loads(self.command("update", "stage"))
                telemetry.emit("update.checked", status=result["status"], version=result.get("version"))
                if result["status"] == "staged" and not self.done.is_set() and (not automatic or self.cfg.auto_update):
                    self.enqueue("update", "update", "install", result["job"])
                elif not automatic and not self.done.is_set():
                    self.icon.notify(f"Updates: {result['status']}. Select Read Full Status for details.", "CAC")
            except Exception as exc:
                telemetry.failure("update.check_failed", exc)
                if not self.done.is_set():
                    self.notify_once("update:" + str(exc), str(exc))
            finally:
                with self._guard:
                    self._update_busy = False
        threading.Thread(target=check, name="CAC-updates", daemon=True).start()

    def status_label(self):
        return state_label(self.state, self.snapshot)

    def usage(self):
        return usage_windows(self.snapshot, self.state, poll_seconds=self.cfg.poll_seconds)

    def show_status(self):
        from .status_window import StatusWindow
        if self.status_window is None:
            self.status_window = StatusWindow(self.status_model, self.lookup_titles, self.dialog_failed)
        self.status_window.show()

    def status_model(self):
        from .state import load_state
        compatibility = self.snapshot.get("compatibility") or {}
        try:
            updates = update_status(self.config_file)
        except AutoContinuerError as exc:
            updates = {"status": "unavailable", "reason": str(exc)}
        # Durable obligations are the authority, including while the monitor is stopped.
        from .presentation import pending_threads
        state_problem = ""
        try:
            threads = pending_threads(load_state(self.config_file.parent / "state.json").obligations)
        except AutoContinuerError as exc:
            threads = self.snapshot.get("waitingThreads", ())
            state_problem = str(exc) + " Preserve state.json; repair its readability before restarting."
        snapshot = self.snapshot | {"waitingThreads": threads}
        stamp = snapshot.get("lastScanAt")
        when = datetime.fromtimestamp(stamp).astimezone().strftime("%I:%M:%S %p").lstrip("0") if stamp else "Not Scanned Yet"
        warnings = [warning["message"] for warning in snapshot.get("warnings", [])]
        update_issue = updates.get("reason", "") if updates.get("status") in {"failed", "rolled_back", "unavailable"} else ""
        compatibility_issue = compatibility.get("reason", "") if compatibility and not compatibility.get("dispatch_allowed") else ""
        issue = state_problem or compatibility_issue or self.problem or snapshot.get("reason") or (warnings[0] if warnings else "") or update_issue
        explanations = dict.fromkeys(value for value in warnings + [issue, self.problem, snapshot.get("reason"), updates.get("reason")] if value)
        details = (f"CLI: {compatibility.get('cli_version', 'Unknown')}\nDaemon: {compatibility.get('app_server_version', 'Unknown')}\n"
                   f"{compatibility.get('reason', '')}\n\n" + "\n\n".join(explanations))
        evidence = {"certified": "Verified", "untested": "Untested"}.get(compatibility.get("status"),
            "Blocked" if compatibility and not compatibility.get("dispatch_allowed") else "Not Checked")
        return {"label": state_label("failed" if state_problem else self.state, snapshot), "threads": threads,
                "clients": ", ".join({"vscode": "VS Code", "cli": "CLI", "desktop": "Desktop"}[c] for c in self.cfg.clients) or "None",
                "scan": when, "compatibility": evidence + f" ({self.cfg.compatibility_policy.title()})",
                "updates": updates.get("status", "Not Checked").replace("_", " ").title(), "issue": issue,
                "details": details, "usage": self.usage()}

    def lookup_titles(self, identities):
        from .appserver import AppServerClient
        from .codex import find_codex, daemon_version
        if not (self.snapshot.get("compatibility") or {}).get("read_allowed"):
            return {}
        names = {}
        client = None
        try:
            daemon = daemon_version(find_codex(self.cfg.codex_executable), min(5, self.cfg.codex_command_timeout_seconds))
            client = AppServerClient.connect(daemon.socket_path, min(2, self.cfg.rpc_timeout_seconds))
            deadline = time.monotonic() + 5
            for identity in identities:
                if time.monotonic() >= deadline:
                    break
                thread = client.thread_read(identity)
                if thread and thread.get("id") == identity and "name" in thread and (
                        thread["name"] is None or isinstance(thread["name"], str)):
                    names[identity] = thread["name"]
        except Exception as exc:
            telemetry.failure("tray.title_lookup_failed", exc)
        finally:
            if client:
                client.close()
        return names

    def select_clients(self, name: str):
        selected = set(self.cfg.clients)
        if name == "all":
            selected = set(ALL_CLIENTS)
        elif name in selected:
            selected.remove(name)
        else:
            selected.add(name)
        self.enqueue("clients", "clients", *(value for value in ALL_CLIENTS if value in selected))

    def privacy(self, mode: str):
        self.dialogs.show("privacy", PRIVACY_TEXT[mode] + PRIVACY_FOOTER,
                          title=f"CAC telemetry: {mode.title()}", confirm=True,
                          then=lambda: self.enqueue("privacy", "logging", mode))

    def restore_defaults(self):
        self.dialogs.show("reset", "Restore default settings?\n\nThe selected prompt, pending continuations, logs and Windows login shortcut stay unchanged. Future logging returns to Private mode.",
                          confirm=True, then=lambda: self.enqueue("reset", "restore-defaults", "--prompt-file", self.cfg.prompt_file))

    def about(self):
        self.dialogs.show("about", f"Codex Auto Continuer {__version__}\n\nContinues exact local Codex chats after usage recovers.\nLocal diagnostics; no analytics uploads or credential logging.\n\nIndependent tool, not an OpenAI product. MIT license.",
                          title=f"About CAC {__version__}")

    def watch(self):
        while not self.done.wait(1):
            self.refresh()
            if self.cfg.auto_update and not self.busy and (not self._last_update_check or time.monotonic() - self._last_update_check > self.cfg.update_check_hours * 3600):
                self._last_update_check = time.monotonic()
                self.check_updates(automatic=True)

    def menu(self):
        from pystray import Menu, MenuItem as Item
        def action(label, *arguments):
            return lambda icon, item: self.enqueue(label, *arguments)
        available = lambda item: not self.busy and not self._installing
        def client_action(value):
            return lambda icon, item: self.select_clients(value)
        client_items = [Item(label, client_action(value),
                             checked=lambda item, value=value: value in self.cfg.clients, enabled=available)
                        for value, label in (("vscode", "VS Code"), ("cli", "CLI"), ("desktop", "Desktop"))]
        return Menu(
            Item(lambda item: self.status_label(), lambda icon, item: self.show_status(), default=True),
            *(Item(lambda item, index=index: f"{self.usage()[index].label}: {self.usage()[index].percentage()} • {self.usage()[index].reset()}",
                   lambda: None, enabled=False) for index in range(2)),
            Item("Read Full Status", lambda icon, item: self.show_status()),
            Menu.SEPARATOR,
            Item("Start Monitoring", action("start", "start"), enabled=lambda item: available(item) and bool(self.cfg.clients) and not self.running),
            Item("Stop Monitoring", action("stop", "stop"), enabled=lambda item: available(item) and self.running),
            Item("Clients To Monitor", Menu(*client_items, Item("All", lambda icon, item: self.select_clients("all"),
                 checked=lambda item: set(self.cfg.clients) == set(ALL_CLIENTS), enabled=available))),
            Item("Start With Windows", lambda icon, item: self.enqueue("startup", "uninstall-startup" if startup_path().exists() else "install-startup"),
                 checked=lambda item: startup_path().exists(), enabled=available),
            Menu.SEPARATOR,
            Item("Modify Prompt", lambda icon, item: self.open("modify-prompt")),
            Item("Modify Settings", lambda icon, item: self.open("open-config")),
            Item("Open Data Folder", lambda icon, item: self.open("open-logs")),
            Item("Telemetry", Menu(
                Item("Detailed", lambda icon, item: self.privacy("detailed"), checked=lambda item: self.cfg.detailed_telemetry, radio=True),
                Item("Private", lambda icon, item: self.privacy("private"), checked=lambda item: not self.cfg.detailed_telemetry, radio=True))),
            Item("Restore Defaults", lambda icon, item: self.restore_defaults()),
            Menu.SEPARATOR,
            Item("Check For Updates", lambda icon, item: self.check_updates(), enabled=lambda item: not self._update_busy),
            Item(f"About CAC {__version__}", lambda icon, item: self.about()),
            Item("Exit CAC", action("quit"), enabled=lambda item: not self._installing),
        )


def run_tray(config_file: Path, *, start_monitor=True) -> int:
    if os.name != "nt":
        raise AutoContinuerError("The system tray application currently supports Windows only.")
    from .windows_tray import TrayIcon
    try:
        with SingleInstanceLock(control_dir() / "tray.lock"):
            controller = TrayController(config_file)
            telemetry.setup(config_file.parent / "tray.jsonl", controller.cfg)
            telemetry.emit("tray.started", configPath=str(config_file))
            controller.icon = TrayIcon("CodexAutoContinuer", tray_image(controller.state), "CAC", menu=controller.menu(),
                                       usage_provider=controller.usage)
            def ready(icon):
                icon.visible = True
                telemetry.emit("tray.ready", menuItems=[item.text for item in icon.menu.items])
                write_json(config_file.parent / "tray-ready.json", {"version": __version__, "pid": os.getpid(), "config": str(config_file.resolve())})
                threading.Thread(target=controller.worker, name="CAC-controls", daemon=True).start()
                threading.Thread(target=controller.watch, name="CAC-status", daemon=True).start()
                controller.refresh()
                # Historical status is not a launch veto. The start command validates
                # current settings and reports real failures without discarding work.
                if start_monitor and not controller.running:
                    controller.enqueue("start", "start")
            try:
                controller.icon.run(setup=ready)
            finally:
                controller.done.set()
                controller.dialogs.close()
                if controller.status_window:
                    controller.status_window.close()
                telemetry.emit("tray.closed")
            return 0
    except AlreadyRunningError:
        message("CAC is already in the system tray. Look in Windows' hidden tray icons if needed.")
        return 0
