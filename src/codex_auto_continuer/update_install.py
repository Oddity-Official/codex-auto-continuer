"""Out-of-process portable replacement, preserving data and a recoverable code backup."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import time
from pathlib import Path

from .config import control_dir, load_config, lock_path
from .instance_lock import SingleInstanceLock, is_running
from .status import owns_monitor
from .telemetry import emit, setup, failure
from .updates import (ROOT_ITEMS, TRUST, UpdateError, parse_json, signed_release, verify_zip,
                      verify_bundle, version, write_json)


def no_links(path: Path) -> None:
    for current in (path, *path.parents):
        if current.is_symlink() or current.is_junction():
            raise UpdateError("Update paths must not contain links or reparse points.")


def process_path(pid: int) -> Path | None:
    if os.name != "nt" or type(pid) is not int or pid <= 0:
        raise UpdateError("Updates require a valid native Windows process identity.")
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:
            return None
        raise UpdateError("Cannot verify the running CAC process. Stop it manually before updating.")
    try:
        size = wintypes.DWORD(32768)
        text = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, text, ctypes.byref(size)):
            raise UpdateError("Cannot read the CAC process executable identity.")
        return Path(text.value).resolve()
    finally:
        kernel.CloseHandle(handle)


def stop_tray(pid: int | None, app: Path) -> None:
    if pid is None:
        if is_running(control_dir() / "tray.lock"):
            raise UpdateError("A tray is running but its identity is unavailable. Update from its Check For Updates control, or exit it first.")
        return
    expected = app / "CodexAutoContinuer.exe"
    actual = process_path(pid)
    if actual is None:
        return
    if actual != expected:
        raise UpdateError("The tray PID no longer belongs to this exact CAC executable. No process was stopped.")
    # Query and terminate through one handle, so PID reuse cannot target another process.
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x1 | 0x100000, False, pid)
    if not handle:
        raise UpdateError("CAC tray could not be opened for a verified update shutdown.")
    try:
        size = wintypes.DWORD(32768)
        name = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)) or Path(name.value).resolve() != expected:
            raise UpdateError("CAC tray identity changed before shutdown. No process was stopped.")
        if not kernel.TerminateProcess(handle, 0) or kernel.WaitForSingleObject(handle, 10000) != 0:
            raise UpdateError("CAC tray did not stop within its update deadline.")
    finally:
        kernel.CloseHandle(handle)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process_path(pid) is None and not is_running(control_dir() / "tray.lock"):
            return
        time.sleep(0.1)
    raise UpdateError("CAC tray did not exit within 10 seconds. Code was not replaced.")


def stop_monitor(app: Path, config: Path) -> None:
    if not is_running(lock_path()):
        return
    if is_running(lock_path()) and not owns_monitor(config):
        raise UpdateError("Another app copy owns monitoring. Stop that copy before updating this one.")
    result = subprocess.run([str(app / "CodexAutoContinuer-CLI.exe"), "--config", str(config), "stop"],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=70, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or is_running(lock_path()):
        raise UpdateError("CAC could not finish its current cycle within the update stop deadline. Pending work and code remain unchanged.")


def start_and_check(app: Path, config: Path, expected: str, *, start_monitor=True) -> None:
    ready = config.parent / "tray-ready.json"
    ready.unlink(missing_ok=True)
    arguments = [str(app / "CodexAutoContinuer.exe"), "--config", str(config), "tray"]
    if not start_monitor and version(expected) >= (0, 5, 0):
        arguments.append("--no-monitor")
    process = subprocess.Popen(arguments,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + 30
    started = time.monotonic()
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        if ready.exists() or (version(expected) < (0, 5, 0) and time.monotonic() - started > 2):
            record = parse_json(ready.read_bytes()) if ready.exists() else {"pid": process.pid, "version": expected, "config": str(config)}
            if (record.get("pid") == process.pid and record.get("version") == expected
                    and record.get("config") == str(config) and process_path(process.pid) == app / "CodexAutoContinuer.exe"
                    and is_running(control_dir() / "tray.lock")):
                # Parsing settings/state and loading the new EXE must work. A Codex compatibility block
                # is not an installation failure and cannot justify restoring older queue obligations.
                check = subprocess.run([str(app / "CodexAutoContinuer-CLI.exe"), "--config", str(config), "status"],
                    capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                if check.returncode == 0 and parse_json(check.stdout).get("version") == expected:
                    return
                break
        time.sleep(0.2)
    if process_path(process.pid) == app / "CodexAutoContinuer.exe":
        stop_monitor(app, config)
        stop_tray(process.pid, app)
    raise UpdateError("The new CAC build failed its startup health check. Restoring the previous code without restoring old runtime state.")


def validate_job(job: Path) -> tuple[dict, Path, Path, Path, dict]:
    no_links(job)
    if (job.name != "job.json" or job.parent.parent.resolve() != (control_dir() / "updates").resolve()
            or len(job.parent.name) != 32 or any(c not in "0123456789abcdef" for c in job.parent.name)):
        raise UpdateError("Update job is outside CAC's owned staging directory.")
    request = parse_json(job.read_bytes())
    app = Path(request.get("app", ""))
    config = Path(request.get("config", ""))
    if not app.is_absolute() or app == Path(app.anchor) or not config.is_absolute():
        raise UpdateError("Update job must identify an exact app folder and settings file.")
    no_links(app)
    no_links(config)
    app, config = app.resolve(), config.resolve()
    if not app.is_dir() or not config.parent.is_dir() or app == job.parent or app in job.parents:
        raise UpdateError("Unsafe app or settings target in update job.")
    if config == app or config in (app / item for item in ROOT_ITEMS) or any(app / item in config.parents for item in ROOT_ITEMS):
        raise UpdateError("Settings cannot live inside replaceable release components.")
    load_config(config)
    record = signed_release((job.parent / "UPDATE.json").read_bytes(), (job.parent / "UPDATE.sig").read_bytes(), parse_json(TRUST.read_bytes()))
    if request.get("version") != record["version"] or version(request["old_version"]) >= version(record["version"]):
        raise UpdateError("Update job version ordering or signature is invalid.")
    manifest = verify_zip(job.parent / "release.zip", record)
    bundle = job.parent / "bundle/CodexAutoContinuer"
    no_links(bundle)
    verify_bundle(bundle, manifest)
    for item in ROOT_ITEMS:
        no_links(app / item)
    return request, app, config, bundle, manifest


class Replacement:
    def __init__(self, job: Path, request: dict, app: Path, bundle: Path):
        self.job, self.request, self.app, self.bundle = job, request, app, bundle
        self.recovery = app.parent / ".cac-updates" / job.parent.name
        no_links(self.recovery)
        self.backup = self.recovery / "previous"
        self.failed = self.recovery / "failed-new"

    def apply(self) -> None:
        if self.recovery.exists():
            raise UpdateError("This update has an existing recovery folder. Use update recover rather than overwriting it.")
        old = parse_json((self.app / "RELEASE-MANIFEST.json").read_bytes())
        if old.get("version") != self.request["old_version"]:
            raise UpdateError("Installed version changed since the update was staged. Check for updates again.")
        self.backup.mkdir(parents=True)
        self.request.update(status="applying", original_items=sorted(item for item in ROOT_ITEMS if (self.app / item).exists()), installed_items=[])
        self.save()
        for item in self.request["original_items"]:
            os.replace(self.app / item, self.backup / item)
        for item in sorted(ROOT_ITEMS):
            source = self.bundle / item
            if not source.exists():
                continue
            self.request["installed_items"].append(item)
            self.save()  # Intent is durable before each non-atomic component copy.
            if source.is_dir():
                shutil.copytree(source, self.app / item)
            else:
                shutil.copy2(source, self.app / item)
        self.request["status"] = "health_check"
        self.save()

    def save(self):
        write_json(self.job, self.request)
        write_json(self.recovery / "recovery.json", self.request)
        emit("update.install_phase", status=self.request["status"], version=self.request["version"], components=len(self.request.get("installed_items", [])))

    def restore(self):
        self.failed.mkdir(parents=True, exist_ok=True)
        original = self.request.get("original_items", [])
        installed = self.request.get("installed_items", [])
        if not set(original) <= ROOT_ITEMS or not set(installed) <= ROOT_ITEMS:
            raise UpdateError("Recovery journal contains an unexpected component. No recovery paths were moved.")
        for item in sorted(ROOT_ITEMS):
            current, backup = self.app / item, self.backup / item
            no_links(current)
            no_links(backup)
            if backup.exists():
                if current.exists():
                    os.replace(current, self.failed / item)
                os.replace(backup, current)
            elif item not in original and item in installed and current.exists():
                os.replace(current, self.failed / item)
        self.request["status"] = "rolled_back"
        self.save()


def run_worker(job: Path, *, recover=False) -> int:
    config = None
    try:
        with SingleInstanceLock(control_dir() / "update.lock"):
            request, app, config, bundle, manifest = validate_job(job)
            replacement = Replacement(job, request, app, bundle)
            if request.get("status") != "staged" and not recover:
                raise UpdateError("This update was already started. Use update recover for an interrupted installation.")
            requester = request.get("requester_pid")
            if requester:
                deadline = time.monotonic() + 10
                while process_path(requester) == app / "CodexAutoContinuer-CLI.exe":
                    if time.monotonic() > deadline:
                        raise UpdateError("The requesting CAC command did not exit; code was not replaced.")
                    time.sleep(0.1)
            if "restart_monitor" not in request:
                request["restart_monitor"] = owns_monitor(config)
                write_json(job, request)
            stop_monitor(app, config)
            stop_tray(request.get("tray_pid"), app)
            setup(config.parent / "updates.jsonl", load_config(config))
            emit("update.cycle_finished", oldVersion=request["old_version"], newVersion=request["version"])
            if recover:
                replacement.restore()
                start_and_check(app, config, request["old_version"], start_monitor=request["restart_monitor"])
            else:
                try:
                    replacement.apply()
                    verify_bundle_code(app, manifest)
                    start_and_check(app, config, request["version"], start_monitor=request["restart_monitor"])
                    request["status"] = "completed"
                    replacement.save()
                except Exception:
                    if request.get("status") in {"applying", "health_check"}:
                        replacement.restore()
                        start_and_check(app, config, request["old_version"], start_monitor=request["restart_monitor"])
                    raise
            write_json(config.parent / "update-status.json", {"status": request["status"], "version": request["version"] if request["status"] == "completed" else request["old_version"],
                "checkedAt": time.time(), "job": str(job), "recovery": str(replacement.recovery)})
            return 0
    except Exception as exc:
        try:
            failure("update.install_failed", exc)
        except OSError:
            pass
        reason = str(exc) if isinstance(exc, UpdateError) else "Update failed locally. Inspect the recovery journal; pending state was not restored or discarded."
        if job.name == "job.json" and job.parent.parent.resolve() == (control_dir() / "updates").resolve():
            write_json(job.parent / "failure.json", {"status": "failed", "reason": reason, "errorType": type(exc).__name__})
        if config:
            # Exception text from network/native subprocesses can contain credentials or paths.
            write_json(config.parent / "update-status.json", {"status": "failed", "reason": reason,
                       "errorType": type(exc).__name__, "checkedAt": time.time(), "job": str(job)})
        return 1


def verify_bundle_code(app: Path, manifest: dict):
    # Runtime data and user-owned files are intentionally outside the release file set.
    for name, entry in manifest["files"].items():
        path = app / name
        no_links(path)
        import hashlib
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if path.stat().st_size != entry["bytes"] or digest != entry["sha256"]:
            raise UpdateError("Installed code failed its release checksum check.")
