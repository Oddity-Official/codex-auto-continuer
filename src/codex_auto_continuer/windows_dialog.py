"""Small accessible dark dialogs on the caller's dedicated UI thread."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W

from .windows_ui import (user, gdi, kernel, bind, Canvas, DrawItem, WindowClass, Paint,
    MonitorInfo, PROC, H, I, U, P, R, BACKGROUND, TEXT, MUTED, SURFACE, HOVER, ACCENT,
    color, style_window)

bind(user, "SetFocus", H, H)
bind(user, "EnableWindow", I, H, I)
bind(user, "IsWindowEnabled", I, H)


class DarkDialog:
    def __init__(self, text, title, error, confirm, owner):
        self.text, self.title, self.error, self.confirm, self.owner = text, title, error, confirm, owner
        self.accepted = False
        self.hwnd = None
        self.font = None
        self.controls = {}
        self.failure = None
        self.brand_icon = None

    def px(self, value):
        return round(value * self.dpi / 96)

    def _child(self, kind, text, style, identity):
        hwnd = user.CreateWindowExW(0, kind, text, style, 0, 0, 1, 1,
            self.hwnd, H(identity), kernel.GetModuleHandleW(None), None)
        if not hwnd:
            raise C.WinError(C.get_last_error())
        user.SendMessageW(hwnd, 0x30, self.font or 0, 0)
        self.controls[identity] = hwnd
        return hwnd

    def _place(self, identity, x, y, width, height):
        user.SetWindowPos(self.controls[identity], None, self.px(x), self.px(y),
                          self.px(width), self.px(height), 0x14)

    def _layout(self):
        old_font = self.font
        self.font = gdi.CreateFontW(-self.px(13), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        for control in self.controls.values():
            user.SendMessageW(control, 0x30, self.font, 0)
        if old_font:
            gdi.DeleteObject(old_font)
        dc = user.GetDC(self.hwnd)
        canvas = Canvas(dc, dpi=self.dpi)
        try:
            _, height = canvas.text(self.text, (0, 0, self.px(352), 0), wrap=True, measure=True)
        finally:
            canvas.close()
            user.ReleaseDC(self.hwnd, dc)
        body_height = max(50, height / (self.dpi / 96))
        footer = 28 + body_height + 24
        self._place(100, 72, 24, 352, body_height)
        self._place(1, 324, footer, 100, 32)
        if self.confirm:
            self._place(2, 216, footer, 100, 32)
        rect = R(0, 0, self.px(448), self.px(footer + 52))
        user.AdjustWindowRectExForDpi(C.byref(rect), 0x80C80000, False, 0x10000, self.dpi)
        point = W.POINT()
        user.GetCursorPos(C.byref(point))
        monitor = MonitorInfo(C.sizeof(MonitorInfo))
        if not user.GetMonitorInfoW(user.MonitorFromPoint(point, 2), C.byref(monitor)):
            raise C.WinError(C.get_last_error())
        work = monitor.work
        width, height = rect.right - rect.left, rect.bottom - rect.top
        user.SetWindowPos(self.hwnd, None, work.left + (work.right - work.left - width) // 2,
            work.top + (work.bottom - work.top - height) // 2, width, height, 0x14)

    def run(self):
        previous_dpi = user.SetThreadDpiAwarenessContext(H(-4))
        instance = kernel.GetModuleHandleW(None)
        name = f"CACDialog{id(self)}"
        brush = gdi.CreateSolidBrush(color(BACKGROUND))
        self.callback = PROC(self._proc)
        disabled_owner = bool(self.owner and user.IsWindowEnabled(self.owner))
        try:
            from .icon import native_icon
            self.brand_icon = native_icon()
            cls = WindowClass(0, self.callback, 0, 0, instance, self.brand_icon,
                              user.LoadCursorW(None, H(32512)), brush, None, name)
            if not user.RegisterClassW(C.byref(cls)):
                raise C.WinError(C.get_last_error())
            self.hwnd = user.CreateWindowExW(0x10000, name, self.title, 0x82C80000,
                0, 0, 448, 200, self.owner, None, instance, None)
            if not self.hwnd:
                raise C.WinError(C.get_last_error())
            self.brush = brush
            self.dpi = user.GetDpiForWindow(self.hwnd) or 96
            style_window(self.hwnd)
            self._child("STATIC", self.text, 0x50000080, 100)  # SS_NOPREFIX: literal paths and messages.
            self._child("BUTTON", "OK", 0x5001000B, 1)
            if self.confirm:
                self._child("BUTTON", "Cancel", 0x5001000B, 2)
            self._layout()
            if disabled_owner:
                user.EnableWindow(self.owner, False)
            user.ShowWindow(self.hwnd, 5)
            user.SetFocus(self.controls[2 if self.confirm else 1])
            user.SetTimer(self.hwnd, 1, 100, None)
            msg = W.MSG()
            while user.GetMessageW(C.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x100 and msg.wParam == 27:
                    user.DestroyWindow(self.hwnd)
                elif msg.message == 0x100 and msg.wParam == 13:
                    # Confirmation starts on Cancel; Enter must not approve accidentally.
                    self.accepted = msg.hWnd == self.controls[1]
                    user.DestroyWindow(self.hwnd)
                elif not user.IsDialogMessageW(self.hwnd, C.byref(msg)):
                    user.TranslateMessage(C.byref(msg))
                    user.DispatchMessageW(C.byref(msg))
            if self.failure:
                raise self.failure
            return self.accepted if self.confirm else True
        finally:
            if self.hwnd:
                user.DestroyWindow(self.hwnd)
            quit_message = W.MSG()
            while user.PeekMessageW(C.byref(quit_message), None, 0x12, 0x12, 1):
                pass  # A setup failure must not leave WM_QUIT for the next dialog.
            if disabled_owner:
                user.EnableWindow(self.owner, True)
            user.UnregisterClassW(name, instance)
            if self.font:
                gdi.DeleteObject(self.font)
            gdi.DeleteObject(brush)
            if self.brand_icon:
                user.DestroyIcon(self.brand_icon)
            user.SetThreadDpiAwarenessContext(previous_dpi)

    def _proc(self, hwnd, message, wparam, lparam):
        try:
            if message == 0x10:
                user.DestroyWindow(hwnd)
                return 0
            if message == 2:
                self.hwnd = None
                user.PostQuitMessage(0)
                return 0
            if message == 0x111:
                if wparam & 0xFFFF in (1, 2):
                    self.accepted = wparam & 0xFFFF == 1
                    user.DestroyWindow(hwnd)
                return 0
            if message == 0x2E0 and 100 in self.controls:
                self.dpi = wparam & 0xFFFF
                self._layout()
                return 0
            if message == 0x113:
                point = W.POINT()
                user.GetCursorPos(C.byref(point))
                hover = user.WindowFromPoint(point)
                if hover != getattr(self, "hover", None):
                    for control in self.controls.values():
                        if control in (hover, getattr(self, "hover", None)):
                            user.InvalidateRect(control, None, True)
                    self.hover = hover
                return 0
            if message == 0x138:
                gdi.SetTextColor(wparam, color(TEXT))
                gdi.SetBkMode(wparam, 1)
                return self.brush
            if message == 0x2B:
                item = C.cast(lparam, C.POINTER(DrawItem)).contents
                canvas = Canvas(item.hDC, dpi=self.dpi)
                rect = item.rcItem
                try:
                    canvas.fill((rect.left, rect.top, rect.right, rect.bottom), BACKGROUND)
                    hovered = item.hwndItem == getattr(self, "hover", None)
                    canvas.rounded((rect.left, rect.top, rect.right, rect.bottom),
                                   HOVER if hovered or item.itemState & 1 else SURFACE, 6,
                                   outline=ACCENT if item.CtlID == 1 else None)
                    canvas.text("OK" if item.CtlID == 1 else "Cancel",
                                (rect.left, rect.top, rect.right, rect.bottom), align="center")
                    if item.itemState & 0x10:
                        canvas.fill((rect.left + self.px(8), rect.bottom - self.px(2),
                                     rect.right - self.px(8), rect.bottom - self.px(1)), ACCENT)
                finally:
                    canvas.close()
                return 1
            if message == 0xF and self.controls:
                paint = Paint()
                dc = user.BeginPaint(hwnd, C.byref(paint))
                canvas = Canvas(dc, dpi=self.dpi)
                try:
                    rect = R()
                    user.GetClientRect(hwnd, C.byref(rect))
                    canvas.fill((0, 0, rect.right, rect.bottom), BACKGROUND)
                    canvas.rounded(tuple(self.px(n) for n in (24, 25, 52, 53)),
                                   "#f87171" if self.error else ACCENT, 14)
                    canvas.text("!" if self.error else "i", tuple(self.px(n) for n in (24, 25, 52, 53)),
                                shade=BACKGROUND, size=18, bold=True, align="center")
                finally:
                    canvas.close()
                    user.EndPaint(hwnd, C.byref(paint))
                return 0
        except Exception as exc:
            self.failure = exc
            user.PostMessageW(hwnd, 0x10, 0, 0)
        return user.DefWindowProcW(hwnd, message, wparam, lparam)
