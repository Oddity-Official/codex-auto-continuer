"""Decorate CAC's native popup windows without replacing Windows' menu loop."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W

from .windows_ui import (user, gdi, kernel, bind, Canvas, H, I, U, P, L, R, S,
                         row_palette, LINE, color, style_window)

HOOK = C.WINFUNCTYPE(L, I, P, L)
SUBCLASS = C.WINFUNCTYPE(L, H, U, P, L, P, P)
common = C.WinDLL("comctl32", use_last_error=True)


class CallWindow(C.Structure):
    _fields_ = [("lparam", L), ("wparam", P), ("message", U), ("hwnd", H)]


class MenuBarInfo(C.Structure):
    _fields_ = [("size", U), ("rect", R), ("menu", H), ("window", H), ("focus", U)]


bind(user, "SetWindowsHookExW", H, I, HOOK, H, U)
bind(user, "UnhookWindowsHookEx", I, H)
bind(user, "CallNextHookEx", L, H, I, P, L)
bind(user, "GetClassNameW", I, H, S, I)
bind(user, "GetWindowRect", I, H, C.POINTER(R))
bind(user, "GetMenuBarInfo", I, H, I, I, C.POINTER(MenuBarInfo))
bind(user, "GetMenuItemRect", I, H, H, U, C.POINTER(R))
bind(user, "GetMenuState", U, H, U, U)
bind(user, "ScreenToClient", I, H, C.POINTER(W.POINT))
bind(user, "GetWindowDC", H, H)
bind(user, "SetWindowRgn", I, H, H, I)
bind(gdi, "CreateRoundRectRgn", H, I, I, I, I, I, I)
bind(gdi, "CreatePen", H, I, I, U)
bind(kernel, "GetCurrentThreadId", U)
bind(common, "SetWindowSubclass", I, H, SUBCLASS, P, P)
bind(common, "RemoveWindowSubclass", I, H, SUBCLASS, P)
bind(common, "DefSubclassProc", L, H, U, P, L)


class MenuChrome:
    def __init__(self, icon):
        self.icon = icon
        self.windows = set()
        self.sizes = {}
        self.pending_paints = set()
        self.failure = None
        self.drawing = False
        self.hook_callback = HOOK(self._hook)
        self.window_callback = SUBCLASS(self._window)

    def __enter__(self):
        self.handle = user.SetWindowsHookExW(4, self.hook_callback, None, kernel.GetCurrentThreadId())
        if not self.handle:
            raise C.WinError(C.get_last_error())
        self.icon._chrome = self
        return self

    def __exit__(self, *unused):
        user.UnhookWindowsHookEx(self.handle)
        self.icon._chrome = None
        for hwnd in tuple(self.windows):
            common.RemoveWindowSubclass(hwnd, self.window_callback, 2)
        if self.failure:
            raise self.failure

    def _hook(self, code, wparam, lparam):
        try:
            if code >= 0:
                call = C.cast(lparam, C.POINTER(CallWindow)).contents
                if call.hwnd not in self.windows and call.message == 1:
                    name = C.create_unicode_buffer(32)
                    user.GetClassNameW(call.hwnd, name, len(name))
                    if name.value == "#32768":
                        if not common.SetWindowSubclass(call.hwnd, self.window_callback, 2, 0):
                            raise C.WinError(C.get_last_error())
                        self.windows.add(call.hwnd)
                        style_window(call.hwnd, popup=True)
                        self.repaint()
        except Exception as exc:
            self.failure = exc
        return user.CallNextHookEx(self.handle, code, wparam, lparam)

    def repaint(self):
        # Native menu painting can continue after the owner's WM_DRAWITEM returns.
        # A coalesced posted message runs after that paint, not inside it.
        for hwnd in self.windows - self.pending_paints:
            if not user.PostMessageW(hwnd, 0x8002, 0, 0):
                raise C.WinError(C.get_last_error())
            self.pending_paints.add(hwnd)

    def _window(self, hwnd, message, wparam, lparam, identity, data):
        result = common.DefSubclassProc(hwnd, message, wparam, lparam)
        try:
            if message == 0x82:
                self.windows.discard(hwnd)
                self.sizes.pop(hwnd, None)
                self.pending_paints.discard(hwnd)
            elif message == 0x8002:
                self.pending_paints.discard(hwnd)
            elif message == 0x47:
                rect = R()
                user.GetWindowRect(hwnd, C.byref(rect))
                size = rect.right - rect.left, rect.bottom - rect.top
                if self.sizes.get(hwnd) == size:
                    return result
                self.sizes[hwnd] = size  # SetWindowRgn itself sends WINDOWPOSCHANGED.
                radius = round(8 * self.icon._dpi / 96)
                region = gdi.CreateRoundRectRgn(0, 0, rect.right - rect.left + 1,
                    rect.bottom - rect.top + 1, radius * 2, radius * 2)
                if not region:
                    raise C.WinError(C.get_last_error())
                if not user.SetWindowRgn(hwnd, region, True):
                    gdi.DeleteObject(region)
                    raise C.WinError(C.get_last_error())
                # Windows owns the region after a successful SetWindowRgn.
            if hwnd in self.windows and not self.drawing:
                self.drawing = True
                try:
                    self._arrows(hwnd)
                finally:
                    self.drawing = False
        except Exception as exc:
            self.failure = exc
        return result

    def _arrows(self, hwnd):
        info = MenuBarInfo(C.sizeof(MenuBarInfo))
        if not user.GetMenuBarInfo(hwnd, -4, 0, C.byref(info)):
            return  # Creation precedes attachment of the native menu.
        rows = self.icon._menu_rows.get(int(info.menu or 0), ())
        dc = user.GetDC(hwnd)
        if not dc:
            return
        canvas = Canvas(dc, dpi=self.icon._dpi)
        try:
            for index, row in enumerate(rows):
                if not row.submenu:
                    continue
                rect = R()
                if not user.GetMenuItemRect(None, info.menu, index, C.byref(rect)):
                    continue
                start, end = W.POINT(rect.left, rect.top), W.POINT(rect.right, rect.bottom)
                user.ScreenToClient(hwnd, C.byref(start))
                user.ScreenToClient(hwnd, C.byref(end))
                state = user.GetMenuState(info.menu, index, 0x400)
                bg, fg = row_palette(selected=row.checked, hovered=bool(state & 0x80), disabled=not row.enabled)
                canvas.fill((end.x - canvas.px(22), start.y, end.x, end.y), bg)
                middle = (start.y + end.y) // 2
                canvas.chevron((end.x - canvas.px(12), middle - canvas.px(4),
                                end.x - canvas.px(7), middle + canvas.px(4)), fg)
        finally:
            canvas.close()
            user.ReleaseDC(hwnd, dc)
        if rows:
            rect = R()
            user.GetWindowRect(hwnd, C.byref(rect))
            dc = user.GetWindowDC(hwnd)
            pen = gdi.CreatePen(0, max(1, round(self.icon._dpi / 96)), color(LINE))
            previous_pen = gdi.SelectObject(dc, pen)
            previous_brush = gdi.SelectObject(dc, gdi.GetStockObject(5))  # NULL_BRUSH: keep native rows.
            try:
                diameter = round(16 * self.icon._dpi / 96)
                gdi.RoundRect(dc, 0, 0, rect.right - rect.left, rect.bottom - rect.top, diameter, diameter)
            finally:
                gdi.SelectObject(dc, previous_pen)
                gdi.SelectObject(dc, previous_brush)
                gdi.DeleteObject(pen)
                user.ReleaseDC(hwnd, dc)
