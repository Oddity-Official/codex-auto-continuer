from __future__ import annotations

from pathlib import Path

import pytest

import codex_auto_continuer.startup as startup
from codex_auto_continuer.errors import ConfigurationError


def test_non_windows_rejected(monkeypatch):
    monkeypatch.setattr(startup.os, "name", "posix", raising=False)
    with pytest.raises(ConfigurationError, match="only supported on Windows"):
        startup.startup_path()


def test_startup_command_places_global_config_before_subcommand(tmp_path: Path, monkeypatch):
    target = tmp_path / "Codex Auto Continuer.cmd"
    monkeypatch.setattr(startup, "startup_path", lambda: target)
    monkeypatch.setattr(startup, "_pythonw", lambda: Path(r"C:\Python\pythonw.exe"))
    startup.install_startup(Path(r"C:\Cfg\cac.json"))
    text = target.read_text(encoding="utf-8")
    assert '-m codex_auto_continuer --config "C:\\Cfg\\cac.json" run --background' in text
    startup.uninstall_startup()
    assert not target.exists()


def test_uninstall_refuses_unmanaged_file(tmp_path: Path, monkeypatch):
    target = tmp_path / "Codex Auto Continuer.cmd"
    monkeypatch.setattr(startup, "startup_path", lambda: target)
    target.write_text("not ours", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="unmanaged"):
        startup.uninstall_startup()
