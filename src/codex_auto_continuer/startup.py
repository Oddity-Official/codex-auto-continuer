from __future__ import annotations

import os
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .errors import ConfigurationError

_MARKER = "Managed by Codex Auto Continuer"

_SHORTCUT_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($data.path)
if ($data.mode -eq 'write') {
    $link.Description = $data.description
    $link.TargetPath = $data.target
    $link.Arguments = $data.arguments
    $link.WorkingDirectory = $data.directory
    $link.WindowStyle = 7
    $link.Save()
}
@{description=$link.Description; target=$link.TargetPath; arguments=$link.Arguments} | ConvertTo-Json -Compress
"""


def startup_path() -> Path:
    if os.name != "nt":
        raise ConfigurationError("Windows Startup integration is only supported on Windows.")
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise ConfigurationError("APPDATA is not set; cannot locate the Windows Startup folder.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Codex Auto Continuer.lnk"


def _pythonw() -> Path:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    if not candidate.is_file():
        raise ConfigurationError(f"pythonw.exe is required for hidden Startup launch. Reinstall standard Windows Python: {candidate}")
    return candidate


def _shortcut(path: Path, *, target: Path | None = None, arguments: str = "", directory: Path | None = None) -> dict:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        raise ConfigurationError("PowerShell 7 (pwsh) is required to manage the native Windows Startup shortcut.")
    payload = {"path": str(path), "mode": "read" if target is None else "write", "description": _MARKER,
               "target": str(target or ""), "arguments": arguments, "directory": str(directory or "")}
    try:
        result = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", _SHORTCUT_SCRIPT],
            input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode:
            raise ConfigurationError(f"Cannot manage Windows Startup shortcut: {result.stderr.strip()}")
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot manage Windows Startup shortcut {path}: {exc}") from exc


def _check_owned(target: Path) -> None:
    if target.is_symlink() or target.is_junction():
        raise ConfigurationError(f"Refusing a link/reparse Startup target: {target}")
    if target.exists() and _shortcut(target).get("description") != _MARKER:
        raise ConfigurationError(f"Refusing to change unmanaged Startup shortcut: {target}")


def install_startup(config_file: Path | None = None) -> Path:
    target = startup_path()
    _check_owned(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    from .config import default_config_path, load_config, app_data_dir
    config_file = (config_file or default_config_path()).resolve()
    load_config(config_file)
    directory = app_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    arguments = subprocess.list2cmdline(["-m", "codex_auto_continuer", "--config", str(config_file), "run", "--background"])
    with tempfile.TemporaryDirectory(prefix=".cac-", dir=target.parent) as temporary:
        link = Path(temporary) / target.name
        _shortcut(link, target=_pythonw(), arguments=arguments, directory=directory)
        if not link.is_file() or _shortcut(link).get("description") != _MARKER:
            raise ConfigurationError("Windows did not save the managed Startup shortcut.")
        os.replace(link, target)
    return target


def uninstall_startup() -> Path:
    target = startup_path()
    if not target.exists():
        return target
    _check_owned(target)
    target.unlink()
    return target
