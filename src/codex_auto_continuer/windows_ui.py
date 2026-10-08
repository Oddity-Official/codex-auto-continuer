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
PROC = C.WINFUNCTYPE(L, H, U, P, L)


class WindowClass(C.Structure):
    _fields_ = [("style", U), ("proc", PROC), ("clsExtra", I), ("wndExtra", I), ("instance", H),
                ("icon", H), ("cursor", H), ("background", H), ("menu", S), ("name", S)]


class Paint(C.Structure):
    _fields_ = [("dc", H), ("erase", I), ("rect", R), ("restore", I), ("incUpdate", I), ("reserved", C.c_byte * 32)]


class MonitorInfo(C.Structure):
    _fields_ = [("size", U), ("monitor", R), ("work", R), ("flags", U)]


bind(user, "RegisterClassW", W.ATOM, C.POINTER(WindowClass))
bind(user, "UnregisterClassW", I, S, H)
bind(user, "DefWindowProcW", L, H, U, P, L)
bind(user, "CreateWindowExW", H, U, S, S, U, I, I, I, I, H, H, H, H)
bind(user, "DestroyWindow", I, H)
bind(user, "ShowWindow", I, H, I)
bind(user, "SetWindowPos", I, H, H, I, I, I, I, U)
bind(user, "SetWindowTextW", I, H, S)
bind(user, "PostMessageW", I, H, U, P, L)
bind(user, "SetTimer", P, H, P, U, H)
bind(user, "KillTimer", I, H, P)
bind(user, "GetMessageW", I, C.POINTER(W.MSG), H, U, U)
bind(user, "PeekMessageW", I, C.POINTER(W.MSG), H, U, U, U)
bind(user, "TranslateMessage", I, C.POINTER(W.MSG))
bind(user, "DispatchMessageW", L, C.POINTER(W.MSG))
bind(user, "IsDialogMessageW", I, H, C.POINTER(W.MSG))
bind(user, "PostQuitMessage", None, I)
bind(user, "BeginPaint", H, H, C.POINTER(Paint))
bind(user, "EndPaint", I, H, C.POINTER(Paint))
bind(user, "GetClientRect", I, H, C.POINTER(R))
bind(user, "InvalidateRect", I, H, C.POINTER(R), I)
bind(user, "GetCursorPos", I, C.POINTER(W.POINT))
bind(user, "MonitorFromPoint", H, W.POINT, U)
bind(user, "GetMonitorInfoW", I, H, C.POINTER(MonitorInfo))
bind(user, "SetThreadDpiAwarenessContext", H, H)
bind(user, "AdjustWindowRectExForDpi", I, C.POINTER(R), U, I, U, U)
bind(user, "LoadCursorW", H, H, H)
bind(user, "WindowFromPoint", H, W.POINT)
bind(user, "DestroyIcon", I, H)
bind(gdi, "CreateSolidBrush", H, U)
bind(gdi, "DeleteObject", I, H)
bind(gdi, "SelectObject", H, H, H)
bind(gdi, "CreateFontW", H, I, I, I, I, I, U, U, U, U, U, U, U, U, S)
bind(gdi, "SetTextColor", U, H, U)
bind(gdi, "SetBkMode", I, H, I)
bind(gdi, "GetStockObject", H, I)
bind(gdi, "RoundRect", I, H, I, I, I, I, I, I)
bind(gdi, "Polygon", I, H, C.POINTER(W.POINT), I)
bind(gdi, "CreatePen", H, I, I, U)
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
SURFACE = "#20262e"


def style_window(hwnd, *, popup=False):
    """Use documented Windows 11 DWM attributes, never global theme switches."""
    dwm = C.WinDLL("dwmapi", use_last_error=True)
    setter = bind(dwm, "DwmSetWindowAttribute", I, H, U, H, U)
    for attribute, value in ((20, 1), (33, 3 if popup else 2), (34, color(LINE)),
                             (35, color(BACKGROUND)), (36, color(TEXT))):
        data = U(value)
        result = setter(hwnd, attribute, C.byref(data), C.sizeof(data))
        if result < 0:
            raise OSError(f"Cannot style CAC window (DWM attribute {attribute}, HRESULT {result:#x}).")


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

    def rounded(self, rectangle, shade, radius=8, *, outline=None):
        brush = gdi.CreateSolidBrush(color(shade))
        pen = gdi.CreatePen(0, self.px(1), color(outline)) if outline else None
        previous_brush = gdi.SelectObject(self.dc, brush)
        previous_pen = gdi.SelectObject(self.dc, pen or gdi.GetStockObject(8))
        try:
            gdi.RoundRect(self.dc, *rectangle, self.px(radius * 2), self.px(radius * 2))
        finally:
            gdi.SelectObject(self.dc, previous_pen)
            gdi.SelectObject(self.dc, previous_brush)
            gdi.DeleteObject(brush)
            if pen:
                gdi.DeleteObject(pen)

    def text(self, text, rectangle, *, shade=TEXT, size=13, bold=False, wrap=False, measure=False, align="left"):
        key = size, bold
        if key not in self.fonts:
            self.fonts[key] = gdi.CreateFontW(-self.px(size), 0, 0, 0, 600 if bold else 400,
                0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        previous = gdi.SelectObject(self.dc, self.fonts[key])
        gdi.SetTextColor(self.dc, color(shade))
        gdi.SetBkMode(self.dc, 1)
        rect = R(*rectangle)
        flags = 0x800 | (0x10 if wrap else 0x20 | 4 | 0x8000)  # NOPREFIX, ellipsis or wrapping
        flags |= {"left": 0, "center": 1, "right": 2}[align]
        if measure:
            flags = 0x400 | (0x10 if wrap else 0x20) | 0x800
        try:
            user.DrawTextW(self.dc, text, -1, C.byref(rect), flags)
            return rect.right - rect.left, rect.bottom - rect.top
        finally:
            gdi.SelectObject(self.dc, previous)

    def chevron(self, rectangle, shade=TEXT):
        left, top, right, bottom = rectangle
        middle = (top + bottom) // 2
        points = (W.POINT * 3)(W.POINT(left, top), W.POINT(right, middle), W.POINT(left, bottom))
        brush = gdi.CreateSolidBrush(color(shade))
        old_brush = gdi.SelectObject(self.dc, brush)
        old_pen = gdi.SelectObject(self.dc, gdi.GetStockObject(8))
        try:
            gdi.Polygon(self.dc, points, len(points))
        finally:
            gdi.SelectObject(self.dc, old_pen)
            gdi.SelectObject(self.dc, old_brush)
            gdi.DeleteObject(brush)

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
