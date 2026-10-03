from __future__ import annotations

import json
from pathlib import Path

import pytest

from codex_auto_continuer.config import Config, load_config, validate_config, write_config
from codex_auto_continuer.errors import ConfigurationError


def test_missing_config_uses_defaults(tmp_path: Path):
    assert load_config(tmp_path / "missing.json") == Config()


def test_unknown_config_field_fails(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text('{"mystery": true}', encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Unknown config field"):
        load_config(path)


def test_custom_sources_round_trip(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"desktop_custom_sources": ["chatgpt"]}), encoding="utf-8")
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
    path = tmp_path / "config.json"
    write_config(path)
    with pytest.raises(ConfigurationError, match="already exists"):
        write_config(path)
    write_config(path, force=True)
    assert load_config(path) == Config()

def test_nonfinite_config_rejected():
    with pytest.raises(ConfigurationError, match="finite"):
        validate_config(Config(poll_seconds=float("nan")))
