"""A themed native tooltip; its text is retained only in window memory."""
from __future__ import annotations

import ctypes as C

from .windows_ui import user, kernel, bind, H, I, U, P, S, R, TEXT, SURFACE, color


class ToolInfo(C.Structure):
    _fields_ = [("size", U), ("flags", U), ("window", H), ("identity", P), ("rect", R),
                ("instance", H), ("text", S), ("data", P), ("reserved", H)]


class Tooltip:
    def __init__(self, owner, control):
        self.hwnd = user.CreateWindowExW(8, "tooltips_class32", None, 0x80000001,
            0, 0, 0, 0, owner, None, kernel.GetModuleHandleW(None), None)
        if not self.hwnd:
            raise C.WinError(C.get_last_error())
        self.info = ToolInfo(C.sizeof(ToolInfo), 0x11, owner, control, R(), None, "", 0, None)
        theme = C.WinDLL("uxtheme")
        bind(theme, "SetWindowTheme", I, H, S, S)
        result = theme.SetWindowTheme(self.hwnd, "", "")
        if result < 0:
            raise OSError(f"Cannot style CAC tooltip (HRESULT {result:#x}).")
        user.SendMessageW(self.hwnd, 0x413, color(SURFACE), 0)
        user.SendMessageW(self.hwnd, 0x414, color(TEXT), 0)
        user.SendMessageW(self.hwnd, 0x418, 0, 440)
        if not user.SendMessageW(self.hwnd, 0x432, 0, C.addressof(self.info)):
            raise C.WinError(C.get_last_error())
        self.text = ""

    def update(self, text):
        if text == self.text:
            return
        self.text = text
        self.info.text = text
        user.SendMessageW(self.hwnd, 0x439, 0, C.addressof(self.info))
        if not text:
            user.SendMessageW(self.hwnd, 0x41C, 0, 0)
