from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pytest

from codex_auto_continuer import cli, config, startup, telemetry
from codex_auto_continuer.errors import ConfigurationError


def format_event(fields, *, detailed=False):
    record = logging.LogRecord("events", logging.INFO, "test", 1, "rpc.response", (), None)
    record.fields = fields
    return json.loads(telemetry.EventFormatter(detailed, b"x" * 32).format(record))


def test_rpc_telemetry_is_allowlisted_even_in_detailed_mode():
    secret = "SECRET_BEARER_AND_CONVERSATION_TEXT"
    thread = {"id": "thread", "name": "My chat", "cwd": "E:/personal", "preview": secret,
              "turns": [{"items": [secret]}], "status": {"type": "idle", "unrecognized": secret}}
    result = telemetry.rpc_summary("thread/read", {"thread": thread, "token": secret})
    assert secret not in json.dumps(result)
    private = format_event(result)["fields"]["thread"]
    assert "name" not in private and "cwd" not in private
    assert private["threadId"].startswith("id:")
    detailed = format_event(result, detailed=True)["fields"]["thread"]
    assert detailed["threadId"] == "thread" and detailed["name"] == "My chat"
    queue = telemetry.rpc_summary("thread/queue/add", {"queuedSubmission": {"id": "q", "input": [secret]}})
    assert secret not in json.dumps(queue)
    assert secret not in json.dumps(telemetry.rpc_request_fields({"threadId": "t", "input": [secret], "token": secret}))
    assert secret not in json.dumps(telemetry.turn_summary({"error": {"message": secret, "codexErrorInfo": secret}}))
    turn = telemetry.turn_summary({"error": {"message": secret,
                                 "codexErrorInfo": {"httpConnectionFailed": {"httpStatusCode": 503, "body": secret}}}})
    assert turn["httpStatusCode"] == 503 and secret not in json.dumps(turn)
    provenance = telemetry.thread_summary({"source": {"subAgent": {"thread_spawn": {
        "parent_thread_id": "private-parent", "agent_nickname": "Private agent", "agent_role": secret}}}})
    assert provenance["source"] == {"type": "subAgent"}
    assert secret not in json.dumps(provenance) and "private-parent" not in json.dumps(provenance)
    custom = telemetry.thread_summary({"source": {"custom": "Private custom client"}})
    assert "Private custom client" not in json.dumps(format_event(custom)["fields"])
    assert format_event(custom, detailed=True)["fields"]["source"]["name"] == "Private custom client"


def test_private_ids_correlate_without_recording_raw_ids():
    first = format_event({"threadId": "abc", "nested": {"threadId": "abc", "path": "private"}})["fields"]
    assert first["threadId"] == first["nested"]["threadId"]
    assert "abc" not in json.dumps(first) and "private" not in json.dumps(first)


def test_portable_config_state_are_local_but_instance_control_is_shared(tmp_path, monkeypatch):
    monkeypatch.setattr(config.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config.sys, "executable", str(tmp_path / "CodexAutoContinuer.exe"))
    assert config.default_config_path() == tmp_path / "data/settings.toml"
    assert config.state_path() == tmp_path / "data/state.json"
    assert config.lock_path().parent == config.control_dir()
    assert config.lock_path().parent != tmp_path / "data"


def test_packaged_launch_uses_correct_exe_and_absolute_config(tmp_path, monkeypatch):
    monkeypatch.setattr(startup.sys, "frozen", True, raising=False)
    monkeypatch.setattr(startup.sys, "executable", str(tmp_path / "CodexAutoContinuer-CLI.exe"))
    for name in ("CodexAutoContinuer.exe", "CodexAutoContinuer-CLI.exe"):
        (tmp_path / name).touch()
    path = tmp_path / "space % config.json"
    assert startup.launch_command(path, "tray") == [str(tmp_path / "CodexAutoContinuer.exe"), "--config", str(path), "tray"]
    assert startup.launch_command(path, "status", console=True)[0].endswith("-CLI.exe")
    (tmp_path / "CodexAutoContinuer.exe").unlink()
    with pytest.raises(ConfigurationError, match="incomplete"):
        startup.launch_command(path, "tray")


@pytest.mark.skipif(os.name != "nt", reason="Windows associated-editor action")
def test_modify_prompt_opens_exact_markdown_file(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(cli.os, "startfile", lambda path: opened.append(path))
    path = tmp_path / "settings.toml"
    assert cli.main(["--config", str(path), "modify-prompt"]) == 0
    assert opened == [tmp_path / "continue-prompt.md"]
    assert config.read_prompt(opened[0]).strip() == config.DEFAULT_CONTINUE_PROMPT


@pytest.mark.skipif(os.name != "nt", reason="Windows tray dependency and menu")
def test_tray_menu_actions_match_cli_controls(tmp_path, monkeypatch):
    from codex_auto_continuer.tray import TrayController
    controller = TrayController(tmp_path / "settings.toml")
    actions = []
    monkeypatch.setattr(controller, "enqueue", lambda label, *args: actions.append(args))
    items = {item.text: item for item in controller.menu().items}
    expected = {"Start Monitoring": ("start",), "Stop Monitoring": ("stop",), "Exit CAC": ()}
    for label, command in expected.items():
        items[label](None)
        assert actions[-1] == command
    opened = []
    monkeypatch.setattr(controller, "open", opened.append)
    for label, command in (("Modify Prompt", "modify-prompt"), ("Modify Settings", "open-config"), ("Open Data Folder", "open-logs")):
        items[label](None)
        assert opened[-1] == command
    assert not {"Scan now", "Run one cycle", "Initialize missing files", "Restart monitoring"} & set(items)
    assert "Queue Holding" not in items
    assert "Read Full Status" in items
    labels = list(items)
    assert labels.index("Check For Updates") + 1 == next(index for index, label in enumerate(labels) if label.startswith("About CAC"))


@pytest.mark.skipif(os.name != "nt", reason="Windows tray launch")
@pytest.mark.parametrize("running,no_monitor,expected", [(False, False, [("start",)]),
    (True, False, []), (False, True, [])])
def test_tray_launch_starts_despite_historical_failed_status(tmp_path, monkeypatch, running, no_monitor, expected):
    from codex_auto_continuer import tray, windows_tray
    actions = []

    class Icon:
        def __init__(self, *args, menu, **kwargs):
            self.menu = menu

        def run(self, setup):
            setup(self)

    def refresh(controller):
        controller.problem = "Monitoring stopped during the previous login"
        controller.state = "failed"
        controller.running = running

    monkeypatch.setattr(windows_tray, "TrayIcon", Icon)
    monkeypatch.setattr(tray, "control_dir", lambda: tmp_path / "control")
    monkeypatch.setattr(tray.TrayController, "refresh", refresh)
    monkeypatch.setattr(tray.TrayController, "enqueue", lambda self, label, *args: actions.append(args))
    monkeypatch.setattr(tray.TrayController, "worker", lambda self: None)
    monkeypatch.setattr(tray.TrayController, "watch", lambda self: None)
    assert tray.run_tray(tmp_path / "settings.toml", start_monitor=not no_monitor) == 0
    assert actions == expected


def test_installed_cli_uses_registered_app_config_and_never_guesses_after_move(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "control_dir", lambda: tmp_path)
    registered = tmp_path / "App/data/settings.toml"
    registered.parent.mkdir(parents=True)
    registered.write_text("")
    (tmp_path / "owner.json").write_text(json.dumps({"configPath": str(registered)}))
    assert config.default_config_path() == registered
    registered.unlink()
    assert config.default_config_path() == registered
    registered.parent.rmdir()
    with pytest.raises(ConfigurationError, match="cannot be located"):
        config.default_config_path()


@pytest.mark.skipif(os.name != "nt", reason="Windows tray dependency and telemetry")
def test_tray_privacy_change_reconfigures_its_own_log_stream(tmp_path, monkeypatch):
    from dataclasses import replace
    from codex_auto_continuer.tray import TrayController
    controller = TrayController(tmp_path / "settings.toml")
    settings = []
    monkeypatch.setattr(telemetry, "setup", lambda path, cfg: settings.append((path, cfg.detailed_telemetry)))
    config.save_config(controller.config_file, replace(controller.cfg, detailed_telemetry=True))
    controller.refresh()
    assert settings == [(tmp_path / "tray.jsonl", True)]
    controller.refresh()
    assert len(settings) == 1
