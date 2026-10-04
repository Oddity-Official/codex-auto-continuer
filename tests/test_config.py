from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from codex_auto_continuer.config import Config, load_config, validate_config, write_config
from codex_auto_continuer.errors import ConfigurationError


def test_missing_config_uses_defaults(tmp_path: Path):
    assert load_config(tmp_path / "missing.toml") == Config()


def test_unknown_config_field_fails(tmp_path: Path):
    path = tmp_path / "settings.toml"
    path.write_text('mystery = true', encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Unknown config field"):
        load_config(path)


def test_custom_sources_round_trip(tmp_path: Path):
    path = tmp_path / "settings.toml"
    path.write_text('desktop_custom_sources = ["chatgpt"]', encoding="utf-8")
    assert load_config(path).desktop_custom_sources == ("chatgpt",)


@pytest.mark.parametrize("field,value", [
    ("poll_seconds", 0),
    ("rpc_timeout_seconds", 0.5),
    ("codex_command_timeout_seconds", 0),
    ("scan_lookback_hours", -1),
])
def test_numeric_validation(field, value):
    data = Config().__dict__ | {field: value}
    with pytest.raises(ConfigurationError):
        validate_config(Config(**data))


def test_write_config_refuses_overwrite(tmp_path: Path):
    path = tmp_path / "settings.toml"
    write_config(path)
    with pytest.raises(ConfigurationError, match="already exists"):
        write_config(path)
    write_config(path, force=True)
    assert load_config(path) == Config()

def test_nonfinite_config_rejected():
    with pytest.raises(ConfigurationError, match="finite"):
        validate_config(Config(poll_seconds=float("nan")))


def test_annotated_defaults_are_not_active_overrides(tmp_path):
    from codex_auto_continuer.config import initialize_files
    path = tmp_path / "settings.toml"
    initialize_files(path)
    assert not path.exists()
    assert (tmp_path / "continue-prompt.md").read_text().strip() == "Continue"
    write_config(path)
    text = path.read_text()
    assert "# poll_seconds = 30.0" in text and "# clients =" in text
    assert load_config(path) == Config()


def test_tray_updates_preserve_user_comments_and_explicit_defaults(tmp_path):
    from codex_auto_continuer.config import save_config
    path = tmp_path / "settings.toml"
    path.write_text('# My choices\npoll_seconds = 30 # keep this explanation\nclients = ["cli"] # terminals only\n')
    cfg = load_config(path)
    save_config(path, replace(cfg, detailed_telemetry=True))
    text = path.read_text()
    assert '# My choices' in text and '# keep this explanation' in text and '# terminals only' in text
    assert load_config(path).clients == ("cli",)
    save_config(path, replace(cfg, clients=("cli", "desktop")))
    assert '# terminals only' in path.read_text()


@pytest.mark.parametrize("value", [("exec",), ("cli", "cli"), (["cli"],)])
def test_client_selections_reject_unknown_duplicate_or_unhashable_values(value):
    with pytest.raises(ConfigurationError, match="clients"):
        validate_config(Config(clients=value))
