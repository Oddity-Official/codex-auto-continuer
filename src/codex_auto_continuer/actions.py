"""Local editor and folder actions shared by tray and CLI."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .config import DEFAULT_CONTINUE_PROMPT, load_config, prompt_path, write_config
from .errors import AutoContinuerError


def open_local(command: str, settings: Path) -> Path:
    if os.name != "nt":
        raise AutoContinuerError("Associated-editor actions require Windows.")
    if command == "open-config":
        if not settings.exists():
            write_config(settings)
        path = settings
    elif command == "open-logs":
        path = settings.parent
        path.mkdir(parents=True, exist_ok=True)
    elif command == "modify-prompt":
        path = prompt_path(load_config(settings), settings)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(DEFAULT_CONTINUE_PROMPT + "\n")
    else:
        raise ValueError(f"Unknown local action: {command}")
    try:
        os.startfile(path)
    except OSError as exc:
        if getattr(exc, "winerror", None) != 1155 or path.is_dir():
            raise AutoContinuerError(f"Windows could not open {path}. Check its editor association and permissions.") from exc
        notepad = Path(os.environ["WINDIR"]) / "System32/notepad.exe"
        if not notepad.is_file():
            raise AutoContinuerError(f"No editor is associated with {path.suffix}. Associate a text editor in Windows Settings.") from exc
        subprocess.Popen([str(notepad), str(path)], creationflags=subprocess.CREATE_NO_WINDOW)
    return path
