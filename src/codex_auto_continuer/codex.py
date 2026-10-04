from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import platform
from dataclasses import dataclass
from pathlib import Path

from .errors import CodexCommandError, ProtocolError

MIN_VERSION = (0, 160, 0)
_VERSION_RE = re.compile(r"(?:(codex-cli|codex-app-server)\s+)?(\d+)\.(\d+)\.(\d+)((?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)")


@dataclass(frozen=True)
class DaemonInfo:
    status: str
    socket_path: Path
    cli_version: str | None
    app_server_version: str | None
    managed_codex_path: Path | None = None
    managed_codex_version: str | None = None


def find_codex(executable: str | None = None) -> str:
    if executable is not None:
        if not Path(executable).is_file() or (os.name == "nt" and Path(executable).suffix.lower() != ".exe"):
            raise CodexCommandError("codex_executable must point to an existing native Codex executable, not an npm .cmd shim.")
        return executable
    if os.name != "nt":
        path = shutil.which("codex")
        if path:
            return path
    else:
        path = shutil.which("codex.exe")
        if path:
            return path
        local = os.environ.get("LOCALAPPDATA")
        if local:
            desktop = Path(local) / "Programs/OpenAI/Codex/bin/codex.exe"
            if desktop.is_file():
                return str(desktop)
        shim = shutil.which("codex.cmd")
        if shim:
            packages = Path(shim).parent / "node_modules/@openai"
            arch = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
            triple = "aarch64-pc-windows-msvc" if arch == "arm64" else "x86_64-pc-windows-msvc"
            roots = [packages / f"codex-win32-{arch}", packages / "codex/node_modules/@openai" / f"codex-win32-{arch}", packages / "codex"]
            for root in roots:
                for directory in ("bin", "codex"):
                    candidate = root / "vendor" / triple / directory / "codex.exe"
                    if candidate.is_file():
                        return str(candidate)
    raise CodexCommandError("Cannot locate native Codex. Install and sign in to Codex, or set codex_executable to its absolute executable path in settings.")


def _run(codex_bin: str, args: list[str], timeout: float, *, env: dict | None = None) -> subprocess.CompletedProcess[str]:
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
            env=env,
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


def binary_version(codex_bin: str, timeout: float) -> tuple[str, str]:
    cp = _run(codex_bin, ["--version"], timeout)
    if cp.returncode != 0:
        raise CodexCommandError(f"`codex --version` failed ({cp.returncode}): {cp.stderr.strip()}")
    match = _VERSION_RE.fullmatch(cp.stdout.strip())
    if not match:
        raise ProtocolError(f"Unrecognized Codex version output: {cp.stdout.strip()!r}")
    version_tuple = tuple(int(x) for x in match.groups()[1:4])
    if version_tuple < MIN_VERSION:
        required = ".".join(map(str, MIN_VERSION))
        raise ProtocolError(f"Codex {match.group(0)} is too old; this build requires Codex >= {required}.")
    return ".".join(match.groups()[1:4]) + match.group(5), match.group(1) or "codex-cli"


def codex_version(codex_bin: str, timeout: float) -> str:
    version, kind = binary_version(codex_bin, timeout)
    if kind != "codex-cli":
        raise ProtocolError("codex_executable must select the full Codex CLI, not the dedicated app-server executable.")
    return version


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
    for name in ("cliVersion", "appServerVersion", "managedCodexPath", "managedCodexVersion"):
        if name in data and data[name] is not None and not isinstance(data[name], str):
            raise ProtocolError(f"Daemon {command} response field {name} has an invalid type.")
    return DaemonInfo(
        status=status,
        socket_path=Path(socket_path),
        cli_version=data.get("cliVersion"),
        app_server_version=data.get("appServerVersion"),
        managed_codex_path=Path(data["managedCodexPath"]) if data.get("managedCodexPath") else None,
        managed_codex_version=data.get("managedCodexVersion"),
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
