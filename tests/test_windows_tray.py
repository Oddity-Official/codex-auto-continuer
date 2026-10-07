from __future__ import annotations

import ctypes
import os
import threading

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows popup menu lifecycle")


def test_popup_keeps_its_native_highlight_during_background_and_callback_updates(monkeypatch):
    from pystray import Menu, MenuItem
    from codex_auto_continuer.windows_tray import TrayIcon
    from pystray._util import win32

    # Use real HMENUs, but intercept tracking so no popup or focus change reaches the desktop.
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetMenuItemInfoW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.POINTER(win32.MENUITEMINFO)]
    user32.SetMenuItemInfoW.restype = ctypes.c_int
    user32.GetMenuState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    user32.GetMenuState.restype = ctypes.c_uint
    destroyed = []
    destroy = win32.DestroyMenu

    def record_destroy(handle):
        destroyed.append(handle)
        return destroy(handle)

    monkeypatch.setattr(win32, "DestroyMenu", record_destroy)
    monkeypatch.setattr(win32, "SetForegroundWindow", lambda hwnd: True)
    monkeypatch.setattr(win32, "GetCursorPos", lambda point: True)
    calls = []
    icon = TrayIcon("PopupRegression", menu=Menu(MenuItem("Status", lambda icon: calls.append("status"))))

    def track(handle, *args):
        state = win32.MENUITEMINFO(cbSize=ctypes.sizeof(win32.MENUITEMINFO), fMask=win32.MIIM_STATE, fState=0x80)
        assert user32.SetMenuItemInfoW(handle, 0, True, ctypes.byref(state))
        assert user32.GetMenuState(handle, 0, 0x400) & 0x80
        updates = threading.Thread(target=lambda: [icon.update_menu() for _ in range(5)])
        updates.start()
        updates.join(timeout=2)
        assert not updates.is_alive()
        assert destroyed == [], "A background update destroyed the popup Windows is tracking"
        assert user32.GetMenuState(handle, 0, 0x400) & 0x80
        icon._on_notify(0, win32.WM_RBUTTONUP)
        assert destroyed == [], "A reentrant right-click replaced the tracked popup"
        return 1

    monkeypatch.setattr(win32, "TrackPopupMenuEx", track)
    try:
        icon.update_menu()
        icon._on_notify(0, win32.WM_RBUTTONUP)
        assert calls == ["status"]
        assert destroyed == [], "The selected-item callback rebuilt a still-tracked menu"
    finally:
        if icon._menu_handle:
            destroy(icon._menu_handle[0])
            icon._menu_handle = None
        icon._unregister_class(icon._atom)


def test_next_popup_reads_current_labels_checks_and_enabled_state(monkeypatch):
    from pystray import Menu, MenuItem
    from pystray._util import win32
    from codex_auto_continuer.windows_tray import TrayIcon

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetMenuStringW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_uint]
    user32.GetMenuStringW.restype = ctypes.c_int
    user32.GetMenuState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    user32.GetMenuState.restype = ctypes.c_uint
    monkeypatch.setattr(win32, "SetForegroundWindow", lambda hwnd: True)
    monkeypatch.setattr(win32, "GetCursorPos", lambda point: True)
    value = {"text": "Before", "checked": False, "enabled": True}
    icon = TrayIcon("FreshPopup", menu=Menu(MenuItem(
        lambda item: value["text"], lambda: None,
        checked=lambda item: value["checked"], enabled=lambda item: value["enabled"])))
    snapshots = []

    def track(handle, *args):
        text = ctypes.create_unicode_buffer(128)
        assert user32.GetMenuStringW(handle, 0, text, len(text), 0x400)
        snapshots.append((text.value, user32.GetMenuState(handle, 0, 0x400)))
        return 0

    monkeypatch.setattr(win32, "TrackPopupMenuEx", track)
    try:
        icon._on_notify(0, win32.WM_RBUTTONUP)
        value.update(text="After", checked=True, enabled=False)
        icon.update_menu()
        icon._on_notify(0, win32.WM_RBUTTONUP)
        assert snapshots[0] == ("Before", 0x100)  # MFT_OWNERDRAW, no state flags
        assert snapshots[1][0] == "After"
        assert snapshots[1][1] & win32.MFS_CHECKED
        assert snapshots[1][1] & win32.MFS_DISABLED
    finally:
        if icon._menu_handle:
            win32.DestroyMenu(icon._menu_handle[0])
            icon._menu_handle = None
        icon._unregister_class(icon._atom)
