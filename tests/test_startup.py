from __future__ import annotations

from pathlib import Path
import os

import pytest

import codex_auto_continuer.startup as startup
from codex_auto_continuer.errors import ConfigurationError


def test_non_windows_rejected(monkeypatch):
    monkeypatch.setattr(startup.os, "name", "posix", raising=False)
    with pytest.raises(ConfigurationError, match="only supported on Windows"):
        startup.startup_path()


def test_startup_pins_absolute_config(tmp_path: Path, monkeypatch):
    target = tmp_path / "Codex Auto Continuer.lnk"
    saved = []
    monkeypatch.setattr(startup, "startup_path", lambda: target)
    monkeypatch.setattr(startup, "_pythonw", lambda: Path(r"C:\Python\pythonw.exe"))
    def shortcut(path, **values):
        if values:
            saved.append(values)
            path.write_text(startup._MARKER)
        return {"description": path.read_text()}
    monkeypatch.setattr(startup, "_shortcut", shortcut)
    config = tmp_path / "Config with spaces.json"
    startup.install_startup(config)
    assert '--config "' + str(config) + '" tray' in saved[0]["arguments"]
    startup.uninstall_startup()
    assert not target.exists()


def test_uninstall_refuses_unmanaged_file(tmp_path: Path, monkeypatch):
    target = tmp_path / "Codex Auto Continuer.lnk"
    monkeypatch.setattr(startup, "startup_path", lambda: target)
    target.write_text("not ours", encoding="utf-8")
    monkeypatch.setattr(startup, "_shortcut", lambda path: {"description": path.read_text()})
    with pytest.raises(ConfigurationError, match="unmanaged"):
        startup.uninstall_startup()
    with pytest.raises(ConfigurationError, match="unmanaged"):
        startup.install_startup()
    assert target.read_text() == "not ours"


@pytest.mark.skipif(os.name != "nt", reason="Native Windows shortcut integration")
@pytest.mark.parametrize("shell_name", ["pwsh", "powershell.exe"])
def test_native_shortcut_with_unicode_spaces_and_percent_path(tmp_path, monkeypatch, shell_name):
    executable = startup.shutil.which(shell_name)
    assert executable, f"Required native shell is unavailable: {shell_name}"
    monkeypatch.setattr(startup.shutil, "which", lambda name: executable if name == shell_name else None)
    target = tmp_path / "Codex Auto Continuer.lnk"
    monkeypatch.setattr(startup, "startup_path", lambda: target)
    config = tmp_path / "caf\u00e9 100% config.json"
    startup.install_startup(config)
    data = startup._shortcut(target)
    assert data["description"] == startup._MARKER
    assert str(config) in data["arguments"]
    assert Path(data["target"]) == startup._pythonw()
    startup.uninstall_startup()
    assert not target.exists()
