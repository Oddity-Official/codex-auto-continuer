from __future__ import annotations

import pytest


def test_native_enter_opens_selected_thread_details_without_ending_the_panel():
    import sys
    if sys.platform != "win32":
        pytest.skip("Native Windows message structure")
    from ctypes import wintypes
    from codex_auto_continuer.status_window import StatusWindow
    panel = StatusWindow(lambda: {}, lambda ids: {}, lambda error: None)
    panel.listbox = 123
    opened = []
    panel._details = lambda: opened.append(True)
    msg = wintypes.MSG()
    msg.hWnd, msg.message, msg.wParam = panel.listbox, 0x100, 13
    assert panel._handle_key(msg) and opened == [True]
    msg.hWnd = 456
    assert not panel._handle_key(msg) and opened == [True]

from codex_auto_continuer import config, telemetry
from codex_auto_continuer.errors import AutoContinuerError
from codex_auto_continuer.state import State, Obligation, save_state
from codex_auto_continuer.tray import TrayController


def test_transient_status_read_failure_does_not_claim_monitor_is_blocked(tmp_path, monkeypatch):
    from codex_auto_continuer import tray
    controller = TrayController(tmp_path / "settings.toml")
    notices = []
    class Icon:
        def notify(self, body, title):
            notices.append(body)
    controller.icon = Icon()
    monkeypatch.setattr(tray, "owns_monitor", lambda path: True)
    clock = [10]
    monkeypatch.setattr(tray.time, "monotonic", lambda: clock[0])
    def unavailable(path):
        raise AutoContinuerError("Local status temporarily unreadable") from PermissionError(13, "sharing lock")
    monkeypatch.setattr(tray, "read_runtime", unavailable)
    controller.refresh()
    assert controller.running and controller.state == "reconnecting"
    assert not notices
    clock[0] = 16
    controller.refresh()
    controller.refresh()
    assert len(notices) == 1 and "monitor is still running" in notices[0]
    assert "blocked" not in notices[0]
    monkeypatch.setattr(tray, "read_runtime", lambda path: {"phase": "monitoring", "pending": 0})
    controller.refresh()
    assert controller.state == "monitoring" and not controller.problem
    assert len(notices) == 1 and controller._status_unavailable_since is None


def test_corrupt_recovery_state_remains_an_actionable_error(tmp_path, monkeypatch):
    from codex_auto_continuer import tray
    controller = TrayController(tmp_path / "settings.toml")
    monkeypatch.setattr(tray, "owns_monitor", lambda path: True)
    monkeypatch.setattr(tray, "read_runtime", lambda path: {"phase": "monitoring"})
    (tmp_path / "state.json").write_text("broken")
    controller.refresh()
    assert controller.state == "failed" and "state.json" in controller.problem


def test_status_uses_durable_pending_not_observations_and_survives_corrupt_state(tmp_path):
    controller = TrayController(tmp_path / "settings.toml")
    obligation = Obligation.create("private-thread", "failed", 1, None)
    observed = Obligation.create("observed", "old", 1, None)
    observed.phase, observed.queued_submission_id = "submitted", "q"
    save_state(tmp_path / "state.json", State(obligations=[obligation], observations=[observed]))
    model = controller.status_model()
    assert model["threads"] == ({"threadId": "private-thread", "phase": "pending"},)
    assert model["label"] == "Stopped"
    (tmp_path / "state.json").write_text("broken")
    model = controller.status_model()
    assert model["label"] == "Needs Attention"
    assert "Preserve state.json" in model["issue"]


def test_status_title_lookup_is_read_only_and_does_not_persist_names(tmp_path, monkeypatch):
    from codex_auto_continuer import appserver, codex
    from types import SimpleNamespace
    controller = TrayController(tmp_path / "settings.toml")
    controller.snapshot = {"compatibility": {"read_allowed": True}}
    calls = []
    class Client:
        def thread_read(self, identity):
            calls.append(("read", identity))
            return {"id": identity, "name": None if identity == "unnamed" else "PRIVATE TITLE", "preview": "NEVER USE THIS"}
        def close(self):
            calls.append(("closed",))
    monkeypatch.setattr(codex, "find_codex", lambda path: "fixture")
    monkeypatch.setattr(codex, "daemon_version", lambda *args: SimpleNamespace(socket_path=tmp_path / "socket"))
    monkeypatch.setattr(appserver.AppServerClient, "connect", lambda *args: Client())
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    names = controller.lookup_titles(("named", "unnamed"))
    assert names == {"named": "PRIVATE TITLE", "unnamed": None}
    assert calls == [("read", "named"), ("read", "unnamed"), ("closed",)]
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    controller.snapshot = {"compatibility": {"read_allowed": False}}
    assert controller.lookup_titles(("named",)) == {}
