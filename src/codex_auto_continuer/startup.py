from __future__ import annotations

import os
import sys
from pathlib import Path

from .errors import ConfigurationError

_MARKER = "REM Managed by Codex Auto Continuer"


def startup_path() -> Path:
    if os.name != "nt":
        raise ConfigurationError("Windows Startup integration is only supported on Windows.")
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise ConfigurationError("APPDATA is not set; cannot locate the Windows Startup folder.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Codex Auto Continuer.cmd"


def _pythonw() -> Path:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def install_startup(config_file: Path | None = None) -> Path:
    target = startup_path()
    if target.exists():
        current = target.read_text(encoding="utf-8", errors="replace")
        if not current.startswith(_MARKER):
            raise ConfigurationError(f"Refusing to overwrite unmanaged Startup file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    config_arg = ""
    if config_file is not None:
        config_arg = f' --config "{config_file}"'
    content = (
        f"{_MARKER}\r\n"
        "@echo off\r\n"
        f'start "" /b "{_pythonw()}" -m codex_auto_continuer{config_arg} run --background\r\n'
    )
    target.write_text(content, encoding="utf-8", newline="")
    return target


def uninstall_startup() -> Path:
    target = startup_path()
    if not target.exists():
        return target
    current = target.read_text(encoding="utf-8", errors="replace")
    if not current.startswith(_MARKER):
        raise ConfigurationError(f"Refusing to delete unmanaged Startup file: {target}")
    target.unlink()
    return target
