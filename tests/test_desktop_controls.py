from __future__ import annotations

import ctypes
import hashlib
import os
import threading
import time
from pathlib import Path

import pytest

from codex_auto_continuer import actions, cli, config, telemetry


@pytest.mark.skipif(os.name != "nt", reason="Windows associated-editor actions")
def test_repair_actions_open_invalid_settings_and_prompt_without_validation(tmp_path, monkeypatch):
    settings = tmp_path / "settings.toml"
    settings.write_text("not valid = [")
    prompt = tmp_path / "continue-prompt.md"
    prompt.write_text("")
    opened = []
    monkeypatch.setattr(actions.os, "startfile", opened.append)
    assert actions.open_local("open-config", settings) == settings
    assert actions.open_local("open-logs", settings) == tmp_path
    settings.write_text("")
    assert actions.open_local("modify-prompt", settings) == prompt
    assert prompt.read_text() == ""  # Editing must not replace invalid content.
    assert opened == [settings, tmp_path, prompt]


def test_status_uses_local_snapshot_without_connecting_to_codex(tmp_path, monkeypatch, capsys):
    import json
    monkeypatch.setattr(cli, "find_codex", lambda *args: pytest.fail("Status must not start or probe Codex"))
    monkeypatch.setattr(cli, "owns_monitor", lambda path: False)
    monkeypatch.setattr(cli, "phase", lambda *args: "stopped")
    assert cli.main(["--config", str(tmp_path / "settings.toml"), "status"]) == 0
    assert json.loads(capsys.readouterr().out)["phase"] == "stopped"
    assert not (tmp_path / "settings.toml").exists()


def test_client_cli_can_pause_and_restore_defaults_preserves_selected_prompt(tmp_path, monkeypatch):
    from dataclasses import replace
    monkeypatch.setattr(cli, "is_running", lambda path: False)
    settings = tmp_path / "settings.toml"
    prompt = tmp_path / "mine.md"
    prompt.write_text("Continue")
    config.save_config(settings, replace(config.Config(), prompt_file="mine.md", detailed_telemetry=True))
    state = tmp_path / "state.json"
    state.write_text("keep exact pending bytes")
    assert cli.main(["--config", str(settings), "clients"]) == 0
    assert config.load_config(settings).clients == ()
    assert cli.main(["--config", str(settings), "restore-defaults"]) == 0
    cfg = config.load_config(settings)
    assert cfg.prompt_file == "mine.md" and not cfg.detailed_telemetry and cfg.clients == config.ALL_CLIENTS
    assert prompt.read_text() == "Continue" and state.read_text() == "keep exact pending bytes"


@pytest.mark.skipif(os.name != "nt", reason="Windows hidden background start")
def test_start_reports_invalid_prompt_before_spawning_a_hidden_child(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "is_running", lambda path: False)
    monkeypatch.setattr(cli.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("Invalid prompt must fail before spawn"))
    (tmp_path / "continue-prompt.md").write_text("")
    assert cli.main(["--config", str(tmp_path / "settings.toml"), "start"]) == 2
    assert "prompt is empty" in capsys.readouterr().err


def test_scan_acknowledges_only_its_completed_request(tmp_path, monkeypatch, capsys):
    import json
    request = tmp_path / "scan.request"
    monkeypatch.setattr(cli, "scan_path", lambda: request)
    monkeypatch.setattr(cli, "_check_owner", lambda path: None)
    monkeypatch.setattr(cli, "owns_monitor", lambda path: True)
    snapshots = []
    def read(settings):
        assert request.read_text() and len(request.read_text()) == 32
        snapshots.append(True)
        return {"phase": "monitoring", "scanRequestId": "previous" if len(snapshots) == 1 else request.read_text(),
                "lastScan": {"scanned_threads": 3, "dispatched": 0}}
    monkeypatch.setattr(cli, "read_runtime", read)
    monkeypatch.setattr(cli.time, "sleep", lambda seconds: None)
    assert cli._request_scan(tmp_path / "settings.toml") == 0
    out = capsys.readouterr().out
    assert out.startswith("Scan requested;") and json.loads(out[out.index("{"):])["scanned_threads"] == 3
    assert len(snapshots) == 2


@pytest.mark.skipif(os.name != "nt", reason="Windows tray")
def test_editor_actions_do_not_wait_for_busy_monitor_controls(tmp_path, monkeypatch):
    from codex_auto_continuer import tray
    controller = tray.TrayController(tmp_path / "settings.toml")
    controller.busy = True
    opened = threading.Event()
    release = threading.Event()
    def editor(*args):
        opened.set()
        assert release.wait(2)
    monkeypatch.setattr(tray, "open_local", editor)
    started = time.monotonic()
    controller.open("open-config")
    try:
        assert time.monotonic() - started < 0.2
        assert opened.wait(1)
        assert controller.actions.empty()
    finally:
        release.set()


def test_compressed_rotation_preserves_exact_log_bytes(tmp_path):
    import gzip
    handler = telemetry.CompressedLogHandler(tmp_path / "test.jsonl", maxBytes=512, backupCount=2)
    try:
        handler.stream.write("Important dispatch evidence\n" * 8)
        handler.stream.flush()
        expected = (tmp_path / "test.jsonl").read_bytes()
        handler.doRollover()
        assert gzip.decompress((tmp_path / "test.jsonl.1.gz").read_bytes()) == expected
    finally:
        handler.close()


def test_normal_telemetry_keeps_changes_and_dispatches_without_repeated_rpc_payloads(tmp_path):
    import json
    log = tmp_path / "events.jsonl"
    telemetry.setup(log, config.Config(detailed_telemetry=True))
    try:
        for _ in range(10):
            telemetry.begin_cycle()
            telemetry.emit("rpc.request", method="thread/list")
            telemetry.rpc_completed("thread/list", 1, 3.0, {}, {"data": [{"id": "old-chat", "name": "unneeded older metadata"}]})
            telemetry.changed("discovery.thread", "t", threadId="t", name="Relevant chat", decision="in_scope")
            telemetry.emit("cycle.completed", scanned_threads=1)
        telemetry.changed("discovery.thread", "t", threadId="t", name="Renamed chat", decision="in_scope")
        telemetry.emit("dispatch.intent_saved", threadId="t")
        telemetry.rpc_completed("thread/queue/add", 2, 2.0, {}, {"queuedSubmission": {"id": "q", "clientUserMessageId": "own"}})
        events = [json.loads(line) for line in log.read_text().splitlines()]
        assert len([e for e in events if e["event"] == "discovery.thread"]) == 2
        assert len([e for e in events if e["event"] == "cycle.completed"]) == 10
        assert all(e["fields"]["rpc"]["thread/list"]["calls"] == 1 for e in events if e["event"] == "cycle.completed")
        assert "unneeded older metadata" not in log.read_text()
        assert any(e["event"] == "dispatch.intent_saved" for e in events)
        assert any(e["event"] == "rpc.response" and e["fields"]["method"] == "thread/queue/add" for e in events)
    finally:
        for handler in telemetry._logger.handlers[:]:
            handler.close()
            telemetry._logger.removeHandler(handler)


@pytest.mark.skipif(os.name != "nt", reason="Windows icon assets")
def test_icon_assets_match_svg_master_and_preserve_state_colors():
    from PIL import Image
    from codex_auto_continuer.icon import tray_image
    assets = Path(config.__file__).parent / "assets"
    digest = hashlib.sha256((assets / "cac.svg").read_bytes()).hexdigest()
    for state in ("monitoring", "stopped", "failed"):
        with Image.open(assets / f"{state}.png") as image:
            assert image.info["svg_sha256"] == digest
            assert image.getpixel((0, 0))[3] == 0
    assert tray_image("monitoring").tobytes() == tray_image("waiting").tobytes()
    assert tray_image("monitoring").tobytes() != tray_image("stopped").tobytes()
    assert tray_image("failed").tobytes() != tray_image("stopped").tobytes()


@pytest.mark.skipif(os.name != "nt", reason="Native owned Windows dialogs")
@pytest.mark.parametrize("close_action", ["ok", "close", "escape"])
def test_about_dialog_closes_and_does_not_hold_tray_popup_tracking(monkeypatch, tmp_path, close_action):
    from pystray._util import win32
    from codex_auto_continuer.tray import TrayController
    from codex_auto_continuer.windows_tray import TrayIcon

    controller = TrayController(tmp_path / "settings.toml")
    icon = controller.icon = TrayIcon("OwnedDialogTest", menu=controller.menu())
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.GetMenuItemInfoW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.POINTER(win32.MENUITEMINFO)]
    api.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    api.GetDlgItem.argtypes = [ctypes.c_void_p, ctypes.c_int]
    api.GetDlgItem.restype = ctypes.c_void_p
    api.GetDlgCtrlID.argtypes = [ctypes.c_void_p]
    api.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    api.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    api.SendMessageTimeoutW.argtypes = api.SendMessageW.argtypes + [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_size_t)]
    api.PostMessageW.argtypes = api.SendMessageW.argtypes
    api.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_ssize_t)
    api.EnumThreadWindows.argtypes = [ctypes.c_uint, callback_type, ctypes.c_ssize_t]
    monkeypatch.setattr(win32, "SetForegroundWindow", lambda hwnd: True)
    monkeypatch.setattr(win32, "GetCursorPos", lambda point: True)

    def choose_about(menu, *args):
        position = next(i for i, item in enumerate(icon.menu.items) if item.text.startswith("About CAC"))
        item = win32.MENUITEMINFO(cbSize=ctypes.sizeof(win32.MENUITEMINFO), fMask=win32.MIIM_ID)
        assert api.GetMenuItemInfoW(menu, position, True, ctypes.byref(item))
        return item.wID

    monkeypatch.setattr(win32, "TrackPopupMenuEx", choose_about)
    errors = []
    def ready(owned_icon):
        try:
            win32.PostMessage(owned_icon._hwnd, win32.WM_NOTIFY, 0, win32.WM_RBUTTONUP)
            deadline = time.monotonic() + 5
            found = []
            @callback_type
            def inspect_our_dialog(hwnd, unused):
                name = ctypes.create_unicode_buffer(32)
                api.GetClassNameW(hwnd, name, len(name))
                if name.value == "#32770":
                    found.append(hwnd)
                return 1
            while not found and time.monotonic() < deadline:
                if controller.dialogs._thread and controller.dialogs._thread.native_id:
                    api.EnumThreadWindows(controller.dialogs._thread.native_id, inspect_our_dialog, 0)
                time.sleep(0.01)
            assert found, "About never created an owned native dialog"
            assert controller.dialogs._thread.native_id != owned_icon._thread.native_id
            assert not owned_icon._popup_open, "About held the tray's popup callback open"
            hwnd = found[0]
            while not (api.GetDlgItem(hwnd, 1) or api.GetDlgItem(hwnd, 2)) and time.monotonic() < deadline:
                time.sleep(0.01)
            # Windows may give a single OK button IDCANCEL so Escape also works.
            button = api.GetDlgItem(hwnd, 1) or api.GetDlgItem(hwnd, 2)
            assert button, "About did not initialize its OK button"
            text = ctypes.create_unicode_buffer(32)
            api.GetWindowTextW(button, text, len(text))
            assert text.value == "OK"
            api.ShowWindow(hwnd, 0)  # The probe operates only its own dialog, not the user's app.
            if close_action == "ok":
                result = ctypes.c_size_t()
                assert api.SendMessageTimeoutW(button, 0xF5, 0, 0, 2, 1000, ctypes.byref(result))
            elif close_action == "close":
                api.PostMessageW(hwnd, 0x10, 0, 0)
            else:
                api.PostMessageW(hwnd, 0x100, 0x1B, 0)
            while "about" in controller.dialogs._pending and time.monotonic() < deadline:
                time.sleep(0.01)
            assert "about" not in controller.dialogs._pending, f"About did not close via {close_action}"
        except BaseException as exc:
            errors.append(exc)
        finally:
            controller.dialogs.close()
            owned_icon.stop()
    icon.run(setup=ready)
    if errors:
        raise errors[0]
