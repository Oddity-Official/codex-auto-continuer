from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import CodexCommandError, ProtocolError

MIN_VERSION = (0, 160, 0)
_VERSION_RE = re.compile(r"(?:codex-cli\s+)?(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True)
class DaemonInfo:
    status: str
    socket_path: Path
    cli_version: str | None
    app_server_version: str | None


def find_codex() -> str:
    path = shutil.which("codex")
    if not path:
        raise CodexCommandError("Could not find `codex` on PATH. Install or expose Codex CLI first.")
    return path


def _run(codex_bin: str, args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    process = None
    try:
        process = subprocess.Popen(
            [codex_bin, *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired as exc:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=5, check=False,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
        raise CodexCommandError(
            f"`codex {' '.join(args)}` exceeded {timeout}s; its process was stopped. Check Codex installation and daemon health."
        ) from exc
    except OSError as exc:
        raise CodexCommandError(f"Failed to run `codex {' '.join(args)}`: {exc}") from exc


def codex_version(codex_bin: str, timeout: float) -> str:
    cp = _run(codex_bin, ["--version"], timeout)
    if cp.returncode != 0:
        raise CodexCommandError(f"`codex --version` failed ({cp.returncode}): {cp.stderr.strip()}")
    match = _VERSION_RE.search(cp.stdout.strip())
    if not match:
        raise ProtocolError(f"Unrecognized Codex version output: {cp.stdout.strip()!r}")
    version_tuple = tuple(int(x) for x in match.groups())
    if version_tuple < MIN_VERSION:
        required = ".".join(map(str, MIN_VERSION))
        raise ProtocolError(f"Codex {match.group(0)} is too old; this build requires Codex >= {required}.")
    return ".".join(match.groups())


def _parse_daemon_json(cp: subprocess.CompletedProcess[str], command: str) -> DaemonInfo:
    if cp.returncode != 0:
        detail = cp.stderr.strip() or cp.stdout.strip() or "no diagnostic output"
        raise CodexCommandError(f"`codex app-server daemon {command}` failed ({cp.returncode}): {detail}")
    try:
        data = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"Daemon {command} returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProtocolError(f"Daemon {command} response is not a JSON object.")
    status = data.get("status")
    socket_path = data.get("socketPath")
    if not isinstance(status, str) or not status:
        raise ProtocolError(f"Daemon {command} response omitted status.")
    if not isinstance(socket_path, str) or not socket_path:
        raise ProtocolError(f"Daemon {command} response omitted socketPath.")
    for name in ("cliVersion", "appServerVersion"):
        if name in data and data[name] is not None and not isinstance(data[name], str):
            raise ProtocolError(f"Daemon {command} response field {name} has an invalid type.")
    return DaemonInfo(
        status=status,
        socket_path=Path(socket_path),
        cli_version=data.get("cliVersion"),
        app_server_version=data.get("appServerVersion"),
    )


def daemon_version(codex_bin: str, timeout: float) -> DaemonInfo:
    return _parse_daemon_json(_run(codex_bin, ["app-server", "daemon", "version"], timeout), "version")


def daemon_start(codex_bin: str, timeout: float) -> DaemonInfo:
    return _parse_daemon_json(_run(codex_bin, ["app-server", "daemon", "start"], timeout), "start")


def ensure_daemon(codex_bin: str, timeout: float, auto_start: bool) -> DaemonInfo:
    try:
        return daemon_version(codex_bin, timeout)
    except CodexCommandError:
        if not auto_start:
            raise CodexCommandError(
                "The shared Codex app-server daemon is not reachable and auto_start_daemon is disabled. "
                "Start it with `codex app-server daemon start`."
            )
    return daemon_start(codex_bin, timeout)
