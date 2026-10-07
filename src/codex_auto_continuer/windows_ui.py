"""Small documented Win32/GDI rendering surface shared by menu and status."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W

user = C.WinDLL("user32", use_last_error=True)
gdi = C.WinDLL("gdi32", use_last_error=True)
kernel = C.WinDLL("kernel32", use_last_error=True)


def bind(dll, name, result, *args):
    function = getattr(dll, name)
    function.restype, function.argtypes = result, args
    return function


H = C.c_void_p
I = C.c_int
U = C.c_uint
P = C.c_size_t
L = C.c_ssize_t
S = C.c_wchar_p
R = W.RECT
bind(gdi, "CreateSolidBrush", H, U)
bind(gdi, "DeleteObject", I, H)
bind(gdi, "SelectObject", H, H, H)
bind(gdi, "CreateFontW", H, I, I, I, I, I, U, U, U, U, U, U, U, U, S)
bind(gdi, "SetTextColor", U, H, U)
bind(gdi, "SetBkMode", I, H, I)
bind(user, "FillRect", I, H, C.POINTER(R), H)
bind(user, "DrawTextW", I, H, S, I, C.POINTER(R), U)
bind(user, "GetDC", H, H)
bind(user, "ReleaseDC", I, H, H)
bind(user, "GetDpiForWindow", U, H)
bind(user, "GetDpiForSystem", U)
bind(user, "SendMessageW", L, H, U, P, L)
bind(kernel, "GetModuleHandleW", H, S)

BACKGROUND = "#191d24"
TEXT = "#edf1f7"
MUTED = "#a4afc0"
DISABLED = "#8490a2"
SELECTED = "#253f3b"
HOVER = "#365c52"
ACCENT = "#72dfb0"
LINE = "#343c49"


def color(hex_value):
    r, g, b = (int(hex_value[index:index + 2], 16) for index in (1, 3, 5))
    return r | g << 8 | b << 16


def row_palette(*, selected=False, hovered=False, disabled=False):
    return (HOVER if hovered and not disabled else SELECTED if selected else BACKGROUND,
            DISABLED if disabled else TEXT)


class Canvas:
    def __init__(self, dc, *, dpi=96):
        self.dc = dc
        self.scale = dpi / 96
        self.fonts = {}

    def px(self, value):
        return round(value * self.scale)

    def fill(self, rectangle, shade):
        brush = gdi.CreateSolidBrush(color(shade))
        try:
            user.FillRect(self.dc, C.byref(R(*rectangle)), brush)
        finally:
            gdi.DeleteObject(brush)

    def text(self, text, rectangle, *, shade=TEXT, size=13, bold=False, wrap=False, measure=False):
        key = size, bold
        if key not in self.fonts:
            self.fonts[key] = gdi.CreateFontW(-self.px(size), 0, 0, 0, 600 if bold else 400,
                0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        previous = gdi.SelectObject(self.dc, self.fonts[key])
        gdi.SetTextColor(self.dc, color(shade))
        gdi.SetBkMode(self.dc, 1)
        rect = R(*rectangle)
        flags = 0x800 | (0x10 if wrap else 0x20 | 4 | 0x8000)  # NOPREFIX, ellipsis or wrapping
        if measure:
            flags = 0x400 | 0x20 | 0x800
        try:
            user.DrawTextW(self.dc, text, len(text), C.byref(rect), flags)
            return rect.right - rect.left, rect.bottom - rect.top
        finally:
            gdi.SelectObject(self.dc, previous)

    def meter(self, rectangle, remaining, *, stale=False):
        self.fill(rectangle, LINE)
        if remaining is not None:
            left, top, right, bottom = rectangle
            self.fill((left, top, left + round((right - left) * remaining / 100), bottom),
                      MUTED if stale else ACCENT if remaining > 15 else "#facc15")

    def close(self):
        for font in self.fonts.values():
            gdi.DeleteObject(font)


class MeasureItem(C.Structure):
    _fields_ = [("CtlType", U), ("CtlID", U), ("itemID", U), ("itemWidth", U),
                ("itemHeight", U), ("itemData", P)]


class DrawItem(C.Structure):
    _fields_ = [("CtlType", U), ("CtlID", U), ("itemID", U), ("itemAction", U), ("itemState", U),
                ("hwndItem", H), ("hDC", H), ("rcItem", R), ("itemData", P)]


class MenuInfo(C.Structure):
    _fields_ = [("cbSize", U), ("fMask", U), ("dwStyle", U), ("cyMax", U),
                ("hbrBack", H), ("dwContextHelpID", U), ("dwMenuData", P)]


bind(user, "SetMenuInfo", I, H, C.POINTER(MenuInfo))


class AccessibleMenuName(C.Structure):
    _fields_ = [("signature", U), ("length", U), ("text", S)]
