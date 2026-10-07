"""Exercise native owner callbacks and GDI pixels without showing any windows."""
from __future__ import annotations

import ctypes as C
import os

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Win32 owner drawing")


@pytest.mark.parametrize("dpi", [96, 144, 192])
def test_hidden_menu_owner_routes_measure_draw_and_exposes_selected_name(dpi):
    from pystray import Menu, MenuItem
    from pystray._util import win32
    from codex_auto_continuer.windows_tray import TrayIcon
    from codex_auto_continuer.windows_ui import (bind, user, gdi, H, I, U, R, DrawItem, MeasureItem,
        AccessibleMenuName, MenuInfo, Canvas, color, SELECTED, HOVER, BACKGROUND, ACCENT, LINE)
    bind(gdi, "CreateCompatibleDC", H, H)
    bind(gdi, "CreateCompatibleBitmap", H, H, I, I)
    bind(gdi, "DeleteDC", I, H)
    bind(gdi, "GetPixel", U, H, I, I)
    bind(user, "GetMenuInfo", I, H, C.POINTER(MenuInfo))
    bind(user, "DestroyWindow", I, H)
    chosen = {"selected": True}
    menu = Menu(MenuItem("Clients", Menu(MenuItem("CLI", lambda: None, checked=lambda item: chosen["selected"]))),
                Menu.SEPARATOR, MenuItem("Disabled", lambda: None, enabled=False))
    icon = TrayIcon("HiddenOwnerProof", menu=menu)
    dc = bitmap = previous = screen = None
    try:
        icon._dpi = dpi
        icon._menu_hwnd = icon._create_window(icon._atom)
        icon._attach_renderer()
        callbacks = []
        handle = icon._create_menu(menu, callbacks)
        icon._menu_handle = (handle, callbacks)
        info = MenuInfo(C.sizeof(MenuInfo), 0x12)
        assert user.GetMenuInfo(handle, C.byref(info))
        assert info.dwStyle & 0x80000000, "Native checkmark gutter must be absent"
        assert info.hbrBack
        address, row = next((address, row) for address, row in icon._rows.items() if row.text == "CLI")
        accessible = C.cast(address, C.POINTER(AccessibleMenuName)).contents
        assert accessible.signature == 0xAA0DF00D and accessible.text == "CLI"
        assert row.checked
        chosen["selected"] = False
        assert row.checked, "An open menu must keep its original state snapshot"
        measured = MeasureItem(1, 0, 2, 0, 0, address)
        assert user.SendMessageW(icon._menu_hwnd, 0x2C, 0, C.addressof(measured)) == 1
        assert measured.itemHeight == round(26 * dpi / 96)
        assert measured.itemWidth >= round(190 * dpi / 96)
        screen = user.GetDC(None)
        dc = gdi.CreateCompatibleDC(screen)
        bitmap = gdi.CreateCompatibleBitmap(screen, measured.itemWidth, measured.itemHeight)
        previous = gdi.SelectObject(dc, bitmap)
        drawn = DrawItem(1, 0, 2, 1, 0, handle, dc, R(0, 0, measured.itemWidth, measured.itemHeight), address)
        assert user.SendMessageW(icon._menu_hwnd, 0x2B, 0, C.addressof(drawn)) == 1
        assert gdi.GetPixel(dc, 2, 2) == color(SELECTED)
        drawn.itemState = 1
        assert user.SendMessageW(icon._menu_hwnd, 0x2B, 0, C.addressof(drawn)) == 1
        assert gdi.GetPixel(dc, 2, 2) == color(HOVER)
        disabled_address = next(address for address, row in icon._rows.items() if row.text == "Disabled")
        drawn.itemData = disabled_address
        assert user.SendMessageW(icon._menu_hwnd, 0x2B, 0, C.addressof(drawn)) == 1
        assert gdi.GetPixel(dc, 2, 2) == color(BACKGROUND)
        canvas = Canvas(dc, dpi=dpi)
        canvas.meter((0, 0, 100, 7), 73)
        assert gdi.GetPixel(dc, 72, 3) == color(ACCENT)
        assert gdi.GetPixel(dc, 73, 3) == color(LINE)
        canvas.meter((0, 0, 100, 7), None)
        assert gdi.GetPixel(dc, 1, 3) == color(LINE)
        canvas.close()
    finally:
        if dc:
            gdi.SelectObject(dc, previous)
            gdi.DeleteObject(bitmap)
            gdi.DeleteDC(dc)
        if screen:
            user.ReleaseDC(None, screen)
        if icon._menu_handle:
            win32.DestroyMenu(icon._menu_handle[0])
            icon._menu_handle = None
        if icon._menu_hwnd:
            user.DestroyWindow(icon._menu_hwnd)
        gdi.DeleteObject(icon._brush)
        icon._unregister_class(icon._atom)
