from __future__ import annotations

import pytest
import sys


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows UTF-16 text")
def test_title_measurement_includes_emoji_and_the_complete_suffix():
    import ctypes
    from codex_auto_continuer.windows_ui import Canvas, user, gdi, R
    dc = user.GetDC(None)
    canvas = Canvas(dc)
    try:
        text = "\U0001f4bb Profile Settings"
        actual = canvas.text(text, (0, 0, 800, 40), measure=True)
        previous = gdi.SelectObject(dc, canvas.fonts[(13, False)])
        rect = R(0, 0, 800, 40)
        try:
            user.DrawTextW(dc, text, -1, ctypes.byref(rect), 0x400 | 0x20 | 0x800)
        finally:
            gdi.SelectObject(dc, previous)
        assert actual == (rect.right - rect.left, rect.bottom - rect.top)
    finally:
        canvas.close()
        user.ReleaseDC(None, dc)


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows minimized state")
def test_reopening_status_restores_a_minimized_window():
    from codex_auto_continuer.status_window import StatusWindow
    from codex_auto_continuer.windows_ui import user, bind, I, H
    bind(user, "IsIconic", I, H)
    hwnd = user.CreateWindowExW(0x08000008, "STATIC", "CAC restoration fixture",
        0xA0CA0000, -10000, -10000, 1, 1, None, None, None, None)
    assert hwnd
    try:
        assert user.IsIconic(hwnd)
        panel = StatusWindow(lambda: {}, lambda ids: {}, lambda error: None)
        panel._proc(hwnd, 0x8001, 0, 0)
        assert not user.IsIconic(hwnd)
    finally:
        user.DestroyWindow(hwnd)


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows status-window lifecycle")
def test_closed_status_reopens_with_full_layout_and_work_area_position(tmp_path, monkeypatch):
    import ctypes
    import threading
    from ctypes import wintypes
    from codex_auto_continuer.status_window import StatusWindow, MonitorInfo
    from codex_auto_continuer.windows_ui import user, bind, I, H, R
    bind(user, "GetWindowRect", I, H, ctypes.POINTER(R))
    # Exercise real layout without displaying windows or depending on mouse movement.
    monkeypatch.setattr(user, "ShowWindow", lambda *args: 0)
    def cursor(point):
        ctypes.cast(point, ctypes.POINTER(wintypes.POINT)).contents.x = 0
        ctypes.cast(point, ctypes.POINTER(wintypes.POINT)).contents.y = 0
        return 1
    monkeypatch.setattr(user, "GetCursorPos", cursor)
    laid_out = threading.Event()
    errors = []
    class Panel(StatusWindow):
        def _apply(self, *args, **kwargs):
            super()._apply(*args, **kwargs)
            laid_out.set()
    controller = TrayController(tmp_path / "settings.toml")
    panel = Panel(controller.status_model, lambda ids: {}, errors.append)
    controller.status_window = panel
    bounds = []
    for opening in range(3):
        laid_out.clear()
        controller.show_status()
        try:
            assert laid_out.wait(5), f"Status layout did not complete: {errors!r}"
            rect, client = R(), R()
            assert user.GetWindowRect(panel.hwnd, ctypes.byref(rect))
            assert user.GetClientRect(panel.hwnd, ctypes.byref(client))
            monitor = MonitorInfo(ctypes.sizeof(MonitorInfo))
            assert user.GetMonitorInfoW(user.MonitorFromPoint(wintypes.POINT(0, 0), 2), ctypes.byref(monitor))
            work = monitor.work
            assert client.bottom >= panel.px(panel.height), f"Opening {opening + 1} clipped the layout"
            assert work.left <= rect.left < rect.right <= work.right
            assert work.top <= rect.top < rect.bottom <= work.bottom
            bounds.append((rect.left, rect.top, rect.right, rect.bottom))
        finally:
            panel.close()
            panel.thread.join(5)
        assert not panel.thread.is_alive()
    assert not errors
    assert bounds[0] == bounds[1] == bounds[2]


def test_enter_on_a_thread_does_not_open_a_debug_dialog_or_end_the_panel():
    import sys
    if sys.platform != "win32":
        pytest.skip("Native Windows message structure")
    from ctypes import wintypes
    from codex_auto_continuer.status_window import StatusWindow
    panel = StatusWindow(lambda: {}, lambda ids: {}, lambda error: None)
    panel.listbox = 123
    msg = wintypes.MSG()
    msg.hWnd, msg.message, msg.wParam = panel.listbox, 0x100, 13
    assert not panel._handle_input(msg)
    msg.hWnd = 456
    assert not panel._handle_input(msg)


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows list scrolling")
def test_waiting_list_wheel_accumulates_partial_steps_and_clamps_without_scrolling_other_sections(monkeypatch):
    import ctypes
    from ctypes import wintypes
    from codex_auto_continuer.status_window import StatusWindow
    from codex_auto_continuer.windows_ui import user
    owner = user.CreateWindowExW(0, "STATIC", "CAC wheel fixture", 0, -10000, -10000, 200, 100, None, None, None, None)
    listbox = user.CreateWindowExW(0, "LISTBOX", "", 0x50010001, 0, 0, 100, 30, owner, None, None, None)
    assert owner and listbox
    try:
        panel = StatusWindow(lambda: {}, lambda ids: {}, lambda error: None)
        panel.listbox, panel.page_rows, panel.list_rows = listbox, 2, tuple(range(9))
        for index in range(9):
            text = ctypes.create_unicode_buffer(str(index))
            user.SendMessageW(listbox, 0x180, 0, ctypes.cast(text, ctypes.c_void_p).value)
        monkeypatch.setattr(user, "WindowFromPoint", lambda point: listbox)
        message = wintypes.MSG()
        message.hWnd, message.message = owner, 0x20A
        def wheel(delta):
            message.wParam = (delta & 0xFFFF) << 16
            return panel._handle_input(message)
        assert wheel(-60) and user.SendMessageW(listbox, 0x18E, 0, 0) == 0
        assert wheel(-60) and user.SendMessageW(listbox, 0x18E, 0, 0) == 3
        assert wheel(-1200) and user.SendMessageW(listbox, 0x18E, 0, 0) == 7
        assert wheel(1200) and user.SendMessageW(listbox, 0x18E, 0, 0) == 0
        monkeypatch.setattr(user, "WindowFromPoint", lambda point: owner)
        assert not wheel(-120) and user.SendMessageW(listbox, 0x18E, 0, 0) == 0
    finally:
        user.DestroyWindow(owner)

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


@pytest.mark.parametrize("status", ["schema_mismatch", "unsupported", "unverified"])
def test_compatibility_blocks_explain_the_cause_instead_of_not_checked(tmp_path, status):
    controller = TrayController(tmp_path / "settings.toml")
    controller.problem = "Monitoring stopped. Inspect telemetry."
    controller.snapshot = {"compatibility": {"status": status, "dispatch_allowed": False,
        "reason": "Consumed Codex contract changed. Update CAC; pending work is preserved."}}
    model = controller.status_model()
    assert model["compatibility"] == "Blocked (Balanced)"
    assert model["issue"] == controller.snapshot["compatibility"]["reason"]
    assert controller.problem in model["issues"]
    assert model["issue"] in model["issues"]
    assert "details" not in model


def test_status_uses_durable_pending_not_observations_and_survives_corrupt_state(tmp_path):
    controller = TrayController(tmp_path / "settings.toml")
    controller.snapshot = {"reason": None}
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
