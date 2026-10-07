"""Keep each native popup intact for its entire Windows tracking loop."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pystray import Menu
from pystray._win32 import Icon
from pystray._util import win32
from .windows_ui import (Canvas, DrawItem, MeasureItem, MenuInfo, AccessibleMenuName, user, gdi,
                         color, row_palette, BACKGROUND, MUTED, LINE, ACCENT)


@dataclass(frozen=True)
class Row:
    text: str
    checked: bool
    enabled: bool
    default: bool
    submenu: bool
    separator: bool


class TrayIcon(Icon):
    """A pystray Win32 icon with menu snapshots built on the UI thread."""

    def __init__(self, *args, **kwargs):
        self.usage_provider = kwargs.pop("usage_provider", lambda: ())
        super().__init__(*args, **kwargs)
        self._menu_handle = None
        self._popup_open = False
        self._rows = {}
        self._names = []
        self._usage = {}
        self._dpi = user.GetDpiForSystem() or 96
        self._brush = gdi.CreateSolidBrush(color(BACKGROUND))
        self._message_handlers.update({0x2B: self._draw_item, 0x2C: self._measure_item, 0x120: self._menu_char})
        self._menu_rows = {}
        self._subclass = None

    def _attach_renderer(self):
        # pystray deliberately leaves its separate menu owner on DefWindowProc.
        # Subclass only drawing messages; preserve all native menu-loop behavior.
        if not self._menu_hwnd or self._subclass:
            return
        from .windows_ui import bind, H, U, P, L
        api = ctypes.WinDLL("comctl32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(L, H, U, P, L, P, P)
        bind(api, "DefSubclassProc", L, H, U, P, L)
        bind(api, "SetWindowSubclass", ctypes.c_int, H, callback_type, P, P)
        @callback_type
        def render(hwnd, message, wparam, lparam, identity, data):
            if message in (0x2B, 0x2C, 0x120):
                return self._message_handlers[message](wparam, lparam)
            return api.DefSubclassProc(hwnd, message, wparam, lparam)
        self._subclass = render
        if not api.SetWindowSubclass(self._menu_hwnd, render, 1, 0):
            raise ctypes.WinError(ctypes.get_last_error())

    def _create_menu(self, descriptors, callbacks):
        handle = super()._create_menu(descriptors, callbacks)
        if handle:
            self._menu_rows[int(handle)] = tuple(Row(item.text, bool(item.checked), item.enabled, item.default,
                                                     bool(item.submenu), item is Menu.SEPARATOR) for item in descriptors)
            info = MenuInfo(ctypes.sizeof(MenuInfo), 0x12, 0x80000000, 0, self._brush, 0, 0)
            if not user.SetMenuInfo(handle, ctypes.byref(info)):
                raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def _create_menu_item(self, descriptor, callbacks):
        identity = len(callbacks)
        value = super()._create_menu_item(descriptor, callbacks)
        row = Row(value.dwTypeData or "", bool(value.fState & win32.MFS_CHECKED),
                  not bool(value.fState & win32.MFS_DISABLED), bool(value.fState & win32.MFS_DEFAULT),
                  bool(value.hSubMenu), descriptor is Menu.SEPARATOR)
        accessible = AccessibleMenuName(0xAA0DF00D, len(row.text), row.text)
        self._names.append(accessible)
        address = ctypes.addressof(accessible)
        self._rows[address] = row
        value.fMask |= 0x20 | win32.MIIM_ID  # MIIM_DATA
        value.fType = 0x100 | (0x800 if row.separator else 0)  # retain native separator semantics
        value.wID = identity
        value.dwItemData = address
        return value

    def _measure_item(self, wparam, lparam):
        value = ctypes.cast(lparam, ctypes.POINTER(MeasureItem)).contents
        row = self._rows.get(value.itemData)
        if row is None:
            return 0
        dc = user.GetDC(None)
        canvas = Canvas(dc, dpi=self._dpi)
        try:
            window = self._usage.get(row.text[:2])
            if window is not None:
                width, _ = canvas.text(window.percentage() + " • " + window.reset(),
                                       (0, 0, 1000, 40), size=12, measure=True)
                value.itemWidth = max(canvas.px(232), width + canvas.px(122))
            else:
                width, _ = canvas.text(row.text, (0, 0, 1000, 40), bold=row.default, measure=True)
                value.itemWidth = max(canvas.px(190), width + canvas.px(32))
            value.itemHeight = canvas.px(9 if row.separator else 26)
        finally:
            canvas.close()
            user.ReleaseDC(None, dc)
        return 1

    def _draw_item(self, wparam, lparam):
        value = ctypes.cast(lparam, ctypes.POINTER(DrawItem)).contents
        row = self._rows.get(value.itemData)
        if row is None:
            return 0
        canvas = Canvas(value.hDC, dpi=self._dpi)
        r = value.rcItem
        bg, fg = row_palette(selected=bool(row.checked), hovered=bool(value.itemState & 1), disabled=not row.enabled)
        try:
            canvas.fill((r.left, r.top, r.right, r.bottom), bg)
            pad = canvas.px(10)
            if row.separator:
                middle = (r.top + r.bottom) // 2
                canvas.fill((r.left + pad, middle, r.right - pad, middle + 1), LINE)
            elif row.text[:2] in self._usage:
                window = self._usage[row.text[:2]]
                canvas.text(window.label + ":", (r.left + pad, r.top, r.left + canvas.px(36), r.bottom), shade=MUTED)
                canvas.meter((r.left + canvas.px(40), r.top + canvas.px(10),
                              r.left + canvas.px(102), r.top + canvas.px(16)), window.remaining, stale=window.stale)
                canvas.text(window.percentage() + " • " + window.reset(),
                            (r.left + canvas.px(112), r.top, r.right - pad, r.bottom), size=12, shade=MUTED)
            else:
                canvas.text(row.text, (r.left + pad, r.top, r.right - canvas.px(24), r.bottom), shade=fg, bold=row.default)
                if row.checked:
                    canvas.fill((r.right - canvas.px(14), r.top + canvas.px(7), r.right - canvas.px(10),
                                 r.bottom - canvas.px(7)), ACCENT)
                if row.submenu:
                    canvas.text("›", (r.right - canvas.px(20), r.top, r.right - canvas.px(4), r.bottom), shade=fg, size=18)
        finally:
            canvas.close()
        return 1

    def _menu_char(self, wparam, lparam):
        # Owner-drawn menus need documented WM_MENUCHAR handling for type-to-select.
        character = chr(wparam & 0xFFFF).casefold()
        for index, row in enumerate(self._menu_rows.get(lparam, ())):
            if row.enabled and not row.separator and row.text.casefold().startswith(character):
                return index | (3 << 16)  # MNC_SELECT
        return 0

    def _update_menu(self):
        # pystray also calls this from workers and selected-item callbacks.
        # Dynamic descriptors are evaluated immediately before the next popup;
        # destroying a tracked HMENU here breaks native hover and selection.
        pass

    def _on_notify(self, wparam, lparam):
        if lparam != win32.WM_RBUTTONUP:
            return super()._on_notify(wparam, lparam)
        if self._popup_open:
            return
        self._popup_open = True
        try:
            if self._menu_handle:
                win32.DestroyMenu(self._menu_handle[0])
                self._menu_handle = None
            self._rows.clear()
            self._names.clear()
            self._menu_rows.clear()
            self._attach_renderer()
            self._usage = {window.label: window for window in self.usage_provider()}
            if self._menu_hwnd:
                from .windows_ui import bind, H, I, U
                bind(user, "GetCursorPos", I, ctypes.POINTER(wintypes.POINT))
                bind(user, "SetWindowPos", I, H, H, I, I, I, I, U)
                point = wintypes.POINT()
                user.GetCursorPos(ctypes.byref(point))
                # Move the invisible menu owner, never another application's window.
                user.SetWindowPos(self._menu_hwnd, None, point.x, point.y, 0, 0, 0x15)
                self._dpi = user.GetDpiForWindow(self._menu_hwnd) or 96
            super()._update_menu()
            return super()._on_notify(wparam, lparam)
        finally:
            self._popup_open = False

    def _run(self):
        from .windows_ui import bind, H
        bind(user, "SetThreadDpiAwarenessContext", H, H)
        previous = user.SetThreadDpiAwarenessContext(H(-4))
        try:
            return super()._run()
        finally:
            user.SetThreadDpiAwarenessContext(previous)

    def _mainloop(self):
        try:
            return super()._mainloop()
        finally:
            gdi.DeleteObject(self._brush)
            self._brush = None
