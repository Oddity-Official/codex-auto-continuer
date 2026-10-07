"""An owned dark Win32 status panel; live names exist only while it is open."""
from __future__ import annotations

import ctypes as C
import queue
import threading
import time
from ctypes import wintypes as W

from . import __version__
from .dialogs import message
from .windows_ui import (user, gdi, kernel, bind, Canvas, DrawItem, H, I, U, P, L, S, R,
                         BACKGROUND, TEXT, MUTED, HOVER, LINE, color)

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
bind(user, "SendMessageW", L, H, U, P, L)
bind(user, "PostMessageW", I, H, U, P, L)
bind(user, "SetTimer", P, H, P, U, H)
bind(user, "KillTimer", I, H, P)
bind(user, "GetMessageW", I, C.POINTER(W.MSG), H, U, U)
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


class StatusWindow:
    def __init__(self, provider, title_lookup, on_error):
        self.provider, self.title_lookup, self.on_error = provider, title_lookup, on_error
        self.guard = threading.Lock()
        self.thread = None
        self.hwnd = None
        self.stop = threading.Event()
        self.updates = queue.Queue(maxsize=1)
        self.model = {}
        self.names = {}

    def show(self):
        with self.guard:
            if self.thread and self.thread.is_alive():
                if self.hwnd:
                    user.PostMessageW(self.hwnd, 0x8001, 0, 0)
                return
            self.stop = threading.Event()
            self.thread = threading.Thread(target=self._run, name="CAC-status-window", daemon=True)
            self.thread.start()

    def close(self):
        with self.guard:
            self.stop.set()
        if self.hwnd:
            user.PostMessageW(self.hwnd, 0x10, 0, 0)

    def _observe(self, stop):
        names = {}
        last_lookup = 0
        previous = ()
        while not stop.is_set():
            try:
                model = self.provider()
                ids = tuple(row["threadId"] for row in model["threads"])
                names = {identity: value for identity, value in names.items() if identity in ids}
                self._publish(model, names, stop)
                if ids and (ids != previous or time.monotonic() - last_lookup > 30):
                    names.update(self.title_lookup(sorted(ids, key=lambda identity: identity in names)))
                    last_lookup, previous = time.monotonic(), ids
                    self._publish(model, names, stop)
            except Exception as exc:
                self.on_error(exc)
                return
            stop.wait(1)

    def _publish(self, model, names, stop):
        with self.guard:
            if stop.is_set() or stop is not self.stop:
                return
            try:
                self.updates.get_nowait()
            except queue.Empty:
                pass
            self.updates.put_nowait((model, dict(names)))

    def _run(self):
        if self.stop.is_set():
            return
        old_dpi = user.SetThreadDpiAwarenessContext(H(-4))
        self.brush = gdi.CreateSolidBrush(color(BACKGROUND))
        self.font = None
        instance = kernel.GetModuleHandleW(None)
        class_name = f"CACStatus{id(self)}"
        self.callback = PROC(self._proc)
        try:
            cls = WindowClass(0, self.callback, 0, 0, instance, None,
                user.LoadCursorW(None, H(32512)), self.brush, None, class_name)
            if not user.RegisterClassW(C.byref(cls)):
                raise C.WinError(C.get_last_error())
            self.hwnd = user.CreateWindowExW(0x10000, class_name, f"Codex Auto Continuer {__version__}",
                0x80CA0000, 0, 0, 520, 300, None, None, instance, None)
            if not self.hwnd:
                raise C.WinError(C.get_last_error())
            self.dpi = user.GetDpiForWindow(self.hwnd) or 96
            self.scale = self.dpi / 96
            self.font = gdi.CreateFontW(-self.px(13), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
            try:
                dwm = C.WinDLL("dwmapi")
                bind(dwm, "DwmSetWindowAttribute", I, H, U, H, U)
                dark = I(1)
                dwm.DwmSetWindowAttribute(self.hwnd, 20, C.byref(dark), C.sizeof(dark))
            except OSError:
                pass  # Client content is always dark, independently of title-bar support.
            self.controls = {}
            for key in ("state", "clients", "scan", "compatibility", "updates", "issue", "usage", "usage5", "usage7", "waiting"):
                self.controls[key] = self._control("STATIC", "", 0, 0)
            self.listbox = self._control("LISTBOX", "Waiting Threads", 0x50810151, 101)
            self.details = self._control("BUTTON", "Details", 0x5001000B, 102)
            self.close_button = self._control("BUTTON", "Close", 0x5001000B, 103)
            self.up = self._control("BUTTON", "Previous Threads", 0x5001000B, 104)
            self.down = self._control("BUTTON", "Next Threads", 0x5001000B, 105)
            initial = self.provider()
            self._apply(initial, {})
            if self.stop.is_set():
                return
            user.ShowWindow(self.hwnd, 5)
            user.SetTimer(self.hwnd, 1, 250, None)
            threading.Thread(target=self._observe, args=(self.stop,), name="CAC-live-status", daemon=True).start()
            msg = W.MSG()
            while user.GetMessageW(C.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x100 and msg.wParam == 27:
                    user.DestroyWindow(self.hwnd)
                    continue
                if msg.message == 0x100 and msg.wParam == 13 and msg.hwnd == self.listbox:
                    self._details()
                    continue
                if not user.IsDialogMessageW(self.hwnd, C.byref(msg)):
                    user.TranslateMessage(C.byref(msg))
                    user.DispatchMessageW(C.byref(msg))
        except Exception as exc:
            self.on_error(exc)
        finally:
            with self.guard:
                self.stop.set()
                self.names.clear()
                self.list_rows = ()
                self.model = {}
                try:
                    self.updates.get_nowait()
                except queue.Empty:
                    pass
            if self.hwnd:
                user.DestroyWindow(self.hwnd)
            self.hwnd = None
            user.UnregisterClassW(class_name, instance)
            if self.font:
                gdi.DeleteObject(self.font)
            gdi.DeleteObject(self.brush)
            user.SetThreadDpiAwarenessContext(old_dpi)

    def px(self, value):
        return round(value * self.scale)

    def _control(self, kind, label, style, identity):
        control = user.CreateWindowExW(0, kind, label, style or 0x50000000, 0, 0, 1, 1,
            self.hwnd, H(identity), kernel.GetModuleHandleW(None), None)
        user.SendMessageW(control, 0x30, self.font, 0)
        return control

    def _place(self, handle, x, y, width, height, *, visible=True):
        user.SetWindowPos(handle, None, self.px(x), self.px(y), self.px(width), self.px(height), 0x14)
        user.ShowWindow(handle, 5 if visible else 0)

    def _apply(self, model, names):
        from .presentation import thread_title, thread_reason
        self.model, self.names = model, names
        labels = {"state": "Current Status: " + model["label"], "clients": "Monitoring: " + model["clients"],
                  "scan": "Last Scan: " + model["scan"], "compatibility": "Compatibility: " + model["compatibility"],
                  "updates": "Updates: " + model["updates"], "issue": model["issue"], "usage": "USAGE",
                  "waiting": f"WAITING THREADS — {len(model['threads'])}"}
        for key, text in labels.items():
            user.SetWindowTextW(self.controls[key], text)
        y = 18
        for key in ("state", "clients", "scan", "compatibility", "updates"):
            self._place(self.controls[key], 20, y, 472, 24)
            y += 25
        self._place(self.controls["issue"], 20, y + 3, 472, 60, visible=bool(model["issue"]))
        y += 70 if model["issue"] else 9
        self._place(self.controls["usage"], 20, y, 472, 22)
        y += 28
        self.meter_y = y
        for index, window in enumerate(model["usage"]):
            value = window.percentage(explicit=True) + " • " + window.reset()
            if window.stale and window.remaining is not None:
                value += " (Last Known)"
            key = "usage5" if index == 0 else "usage7"
            user.SetWindowTextW(self.controls[key], window.label + ": " + value)
            self._place(self.controls[key], 132, y, 360, 26)
            y += 32
        y += 12
        rows = model["threads"]
        self._place(self.controls["waiting"], 20, y, 472, 23, visible=bool(rows))
        y += 29 if rows else 0
        old_index = user.SendMessageW(self.listbox, 0x188, 0, 0)
        old_rows = getattr(self, "list_rows", ())
        selected_id = old_rows[old_index][0] if 0 <= old_index < len(old_rows) else None
        list_rows = [(row["threadId"], thread_title(names.get(row["threadId"]), available=row["threadId"] in names), thread_reason(row)) for row in rows]
        if list_rows != getattr(self, "list_rows", None):
            user.SendMessageW(self.listbox, 0x184, 0, 0)
            for identity, title, reason in list_rows:
                value = C.create_unicode_buffer(title + " — " + reason)
                user.SendMessageW(self.listbox, 0x180, 0, C.cast(value, H).value)
            selected = next((index for index, row in enumerate(list_rows) if row[0] == selected_id), 0)
            user.SendMessageW(self.listbox, 0x186, selected, 0)
        self.list_rows = list_rows
        height = min(6, len(rows)) * 52
        user.SendMessageW(self.listbox, 0x1A0, 0, self.px(52))
        self._place(self.listbox, 20, y, 472, height, visible=bool(rows))
        y += height + (15 if rows else 0)
        self._place(self.up, 280, y, 100, 30, visible=len(rows) > 6)
        self._place(self.down, 385, y, 107, 30, visible=len(rows) > 6)
        y += 38 if len(rows) > 6 else 0
        self._place(self.details, 20, y, 90, 30)
        self._place(self.close_button, 402, y, 90, 30)
        y += 48
        if y != getattr(self, "height", None):
            rect = R(0, 0, self.px(512), self.px(y))
            user.AdjustWindowRectExForDpi(C.byref(rect), 0x80CA0000, False, 0x10000, self.dpi)
            width, height = rect.right - rect.left, rect.bottom - rect.top
            point = W.POINT()
            user.GetCursorPos(C.byref(point))
            monitor = MonitorInfo(C.sizeof(MonitorInfo))
            user.GetMonitorInfoW(user.MonitorFromPoint(point, 2), C.byref(monitor))
            work = monitor.work
            x = max(work.left, work.right - width - self.px(20))
            top = max(work.top, work.bottom - height - self.px(20))
            user.SetWindowPos(self.hwnd, None, x, top, min(width, work.right - work.left), min(height, work.bottom - work.top), 0x14)
            self.height = y
        user.InvalidateRect(self.hwnd, None, False)

    def _details(self):
        index = user.SendMessageW(self.listbox, 0x188, 0, 0)
        selected = ""
        if 0 <= index < len(self.list_rows):
            identity, title, reason = self.list_rows[index]
            selected = f"{title}\n{reason}\nThread ID: {identity}\n\n"
        message(selected + self.model["details"], title="CAC Status Details")

    def _proc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == 0x10:
                user.DestroyWindow(hwnd)
                return 0
            if msg == 2:
                self.stop.set()
                user.PostQuitMessage(0)
                return 0
            if msg == 0x8001:
                user.ShowWindow(hwnd, 5)
                return 0
            if msg == 0x2E0 and hasattr(self, "scale"):
                self.dpi = wparam & 0xFFFF
                self.scale = self.dpi / 96
                old_font = self.font
                self.font = gdi.CreateFontW(-self.px(13), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
                for child in list(self.controls.values()) + [self.listbox, self.details, self.close_button, self.up, self.down]:
                    user.SendMessageW(child, 0x30, self.font, 1)
                if old_font:
                    gdi.DeleteObject(old_font)
                self.height = None
                self._apply(self.model, self.names)
                return 0
            if msg == 0x113:
                try:
                    self._apply(*self.updates.get_nowait())
                except queue.Empty:
                    pass
                return 0
            if msg == 0x111:
                if wparam & 0xFFFF == 103:
                    user.DestroyWindow(hwnd)
                elif wparam & 0xFFFF == 102 or (wparam & 0xFFFF == 101 and wparam >> 16 == 2):
                    self._details()
                elif wparam & 0xFFFF in (104, 105):
                    top = user.SendMessageW(self.listbox, 0x18E, 0, 0)
                    direction = -6 if wparam & 0xFFFF == 104 else 6
                    user.SendMessageW(self.listbox, 0x197, max(0, min(len(self.list_rows) - 6, top + direction)), 0)
                return 0
            if msg in (0x138, 0x134):  # native labels and list box retain accessibility text
                gdi.SetTextColor(wparam, color(TEXT))
                gdi.SetBkMode(wparam, 1)
                return self.brush
            if msg == 0x2B:
                item = C.cast(lparam, C.POINTER(DrawItem)).contents
                canvas = Canvas(item.hDC, dpi=self.dpi)
                r = item.rcItem
                try:
                    canvas.fill((r.left, r.top, r.right, r.bottom), HOVER if item.itemState & 1 else BACKGROUND)
                    if item.CtlID == 101 and item.itemID < len(self.list_rows):
                        _, title, reason = self.list_rows[item.itemID]
                        canvas.text(title, (r.left + self.px(8), r.top, r.right - self.px(8), r.top + self.px(28)))
                        canvas.text(reason, (r.left + self.px(8), r.top + self.px(27), r.right - self.px(8), r.bottom), shade=MUTED, size=12)
                    elif item.CtlID in (102, 103, 104, 105):
                        canvas.text({102: "Details", 103: "Close", 104: "↑ Previous", 105: "Next ↓"}[item.CtlID],
                                    (r.left + self.px(10), r.top, r.right, r.bottom))
                        if item.itemState & 0x10:
                            canvas.fill((r.left, r.bottom - 2, r.right, r.bottom), MUTED)
                finally:
                    canvas.close()
                return 1
            if msg == 0xF and hasattr(self, "meter_y"):
                paint = Paint()
                dc = user.BeginPaint(hwnd, C.byref(paint))
                canvas = Canvas(dc, dpi=self.dpi)
                try:
                    for index, window in enumerate(self.model["usage"]):
                        top = self.px(self.meter_y + index * 32 + 10)
                        canvas.meter((self.px(20), top, self.px(118), top + self.px(7)), window.remaining, stale=window.stale)
                finally:
                    canvas.close()
                    user.EndPaint(hwnd, C.byref(paint))
                return 0
        except Exception as exc:
            self.on_error(exc)
        return user.DefWindowProcW(hwnd, msg, wparam, lparam)
