"""An owned dark Win32 status panel; live names exist only while it is open."""
from __future__ import annotations

import ctypes as C
import queue
import threading
import time
from ctypes import wintypes as W

from . import __version__
from .windows_ui import (user, gdi, kernel, bind, Canvas, DrawItem, H, I, U, P, L, S, R,
                         BACKGROUND, TEXT, MUTED, HOVER, SELECTED, SURFACE, ACCENT, color,
                         style_window, PROC, WindowClass, Paint, MonitorInfo)


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
        self.surface_brush = gdi.CreateSolidBrush(color(SURFACE))
        self.fonts = {}
        self.font = None
        self.brand_icon = None
        instance = kernel.GetModuleHandleW(None)
        class_name = f"CACStatus{id(self)}"
        self.callback = PROC(self._proc)
        try:
            from .icon import native_icon
            self.brand_icon = native_icon()
            cls = WindowClass(0, self.callback, 0, 0, instance, self.brand_icon,
                user.LoadCursorW(None, H(32512)), self.brush, None, class_name)
            if not user.RegisterClassW(C.byref(cls)):
                raise C.WinError(C.get_last_error())
            self.hwnd = user.CreateWindowExW(0x10000, class_name, f"Codex Auto Continuer {__version__}",
                0x82CA0000, 0, 0, 520, 300, None, None, instance, None)
            if not self.hwnd:
                raise C.WinError(C.get_last_error())
            self.dpi = user.GetDpiForWindow(self.hwnd) or 96
            self.scale = self.dpi / 96
            self.font = gdi.CreateFontW(-self.px(13), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
            style_window(self.hwnd)
            self.controls = {}
            for key in ("heading", "state", "clients", "scan", "compatibility", "updates", "issue", "usage",
                        "usage5", "usage7", "value5", "value7", "reset5", "reset7", "waiting"):
                self.controls[key] = self._control("STATIC", "", 0, 0)
            self.listbox = self._control("LISTBOX", "Waiting Threads", 0x50010151, 101)
            from .windows_tooltip import Tooltip
            self.tooltip = Tooltip(self.hwnd, self.listbox)
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
                if self._handle_key(msg):
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
                if hasattr(self, "tooltip"):
                    self.tooltip.text = ""
                    self.tooltip.info.text = ""
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
            for font in self.fonts.values():
                gdi.DeleteObject(font)
            gdi.DeleteObject(self.brush)
            gdi.DeleteObject(self.surface_brush)
            if self.brand_icon:
                user.DestroyIcon(self.brand_icon)
            user.SetThreadDpiAwarenessContext(old_dpi)

    def px(self, value):
        return round(value * self.scale)

    def _handle_key(self, msg):
        if msg.message != 0x100:
            return False
        if msg.wParam == 27:
            user.DestroyWindow(self.hwnd)
            return True
        return False

    def _control(self, kind, label, style, identity):
        control = user.CreateWindowExW(0, kind, label, style or 0x50000080, 0, 0, 1, 1,
            self.hwnd, H(identity), kernel.GetModuleHandleW(None), None)
        user.SendMessageW(control, 0x30, self.font, 0)
        return control

    def _place(self, handle, x, y, width, height, *, visible=True):
        user.SetWindowPos(handle, None, self.px(x), self.px(y), self.px(width), self.px(height), 0x14)
        user.ShowWindow(handle, 5 if visible else 0)

    def _label(self, key, text, size=12, bold=False):
        spec = (self.dpi, size, bold)
        if spec not in self.fonts:
            self.fonts[spec] = gdi.CreateFontW(-self.px(size), 0, 0, 0, 600 if bold else 400,
                                             0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        user.SetWindowTextW(self.controls[key], text)
        user.SendMessageW(self.controls[key], 0x30, self.fonts[spec], 0)

    def _apply(self, model, names, *, force=False):
        from .presentation import thread_title, thread_reason, thread_list_capacity
        if not force and model == self.model and names == self.names:
            return
        self.model, self.names = model, names
        point = W.POINT()
        user.GetCursorPos(C.byref(point))
        monitor = MonitorInfo(C.sizeof(MonitorInfo))
        if not user.GetMonitorInfoW(user.MonitorFromPoint(point, 2), C.byref(monitor)):
            raise C.WinError(C.get_last_error())
        work = monitor.work
        self.compact = (work.bottom - work.top) / self.scale < 600
        self.row_height = 48 if self.compact else 56
        self._label("heading", "CURRENT STATE", 11, True)
        self._label("state", model["label"].split(" • ", 1)[0], 21 if self.compact else 23, True)
        self._label("clients", "Monitoring: " + model["clients"], 13)
        self._label("scan", "Last Scan: " + model["scan"])
        self._label("compatibility", "Compatibility: " + model["compatibility"])
        self._label("updates", "Updates: " + model["updates"])
        issues = "\n\n".join(model["issues"])
        self._label("issue", issues, 13)
        self._label("usage", "USAGE" + ("  ·  LAST KNOWN" if any(w.stale for w in model["usage"]) else ""), 11, True)
        self._label("waiting", f"WAITING THREADS  ·  {len(model['threads'])}", 11, True)
        self._place(self.controls["heading"], 24, 20, 464, 18)
        self._place(self.controls["state"], 44, 43, 444, 32)
        self._place(self.controls["clients"], 24, 76 if self.compact else 86, 464, 22)
        self._place(self.controls["scan"], 24, 99 if self.compact else 112, 464, 20)
        self._place(self.controls["compatibility"], 24, 121 if self.compact else 139, 250, 20)
        self._place(self.controls["updates"], 282, 121 if self.compact else 139, 206, 20)
        y = 149 if self.compact else 169
        dc = user.GetDC(self.hwnd)
        canvas = Canvas(dc, dpi=self.dpi)
        try:
            _, issue_height = canvas.text(issues, (0, 0, self.px(464), 0), wrap=True, measure=True)
        finally:
            canvas.close()
            user.ReleaseDC(self.hwnd, dc)
        self._place(self.controls["issue"], 24, y, 464, issue_height / self.scale, visible=bool(issues))
        y += issue_height / self.scale + 14 if issues else 0
        self._place(self.controls["usage"], 24, y, 464, 18)
        y += 27
        self.usage_y = y
        for index, window in enumerate(model["usage"]):
            suffix = "5" if index == 0 else "7"
            x = 38 + index * 238
            self._label("usage" + suffix, "5-Hour" if index == 0 else "7-Day", 12)
            self._label("value" + suffix, window.percentage(explicit=True), (20 if self.compact else 22) if window.remaining is not None else 19, True)
            reset = window.reset()
            self._label("reset" + suffix, reset if reset == "Reset Unknown" else "Resets " + reset, 12)
            self._place(self.controls["usage" + suffix], x, y + 10, 198, 18)
            self._place(self.controls["value" + suffix], x, y + (28 if self.compact else 31), 198, 30)
            self._place(self.controls["reset" + suffix], x, y + (69 if self.compact else 79), 198, 18)
        y += 107 if self.compact else 125
        rows = model["threads"]
        self._place(self.controls["waiting"], 24, y, 464, 18, visible=bool(rows))
        y += 27 if rows else 0
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
        self.page_rows = thread_list_capacity(work.bottom - work.top, self.scale, y, self.row_height)
        height = min(self.page_rows, len(rows)) * self.row_height
        self.list_rect = (24, y, 488, y + height + 8)
        user.SendMessageW(self.listbox, 0x1A0, 0, self.px(self.row_height))
        self._place(self.listbox, 28, y + 4, 456, height, visible=bool(rows))
        y += height + (23 if rows else 0)
        self._place(self.up, 132, y, 96, 32, visible=len(rows) > self.page_rows)
        self._place(self.down, 236, y, 96, 32, visible=len(rows) > self.page_rows)
        y += 52 if len(rows) > self.page_rows else 12
        if y != getattr(self, "height", None):
            rect = R(0, 0, self.px(512), self.px(y))
            user.AdjustWindowRectExForDpi(C.byref(rect), 0x80CA0000, False, 0x10000, self.dpi)
            width, height = rect.right - rect.left, rect.bottom - rect.top
            x = max(work.left, work.right - width - self.px(20))
            top = max(work.top, work.bottom - height - self.px(20))
            user.SetWindowPos(self.hwnd, None, x, top, min(width, work.right - work.left), min(height, work.bottom - work.top), 0x14)
            self.height = y
        user.InvalidateRect(self.hwnd, None, True)

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
                user.ShowWindow(hwnd, 9)
                return 0
            if msg == 0x2E0 and hasattr(self, "scale"):
                self.dpi = wparam & 0xFFFF
                self.scale = self.dpi / 96
                old_font = self.font
                self.font = gdi.CreateFontW(-self.px(13), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
                for child in list(self.controls.values()) + [self.listbox, self.up, self.down]:
                    user.SendMessageW(child, 0x30, self.font, 1)
                if old_font:
                    gdi.DeleteObject(old_font)
                self.height = None
                previous_fonts, self.fonts = self.fonts, {}
                self._apply(self.model, self.names, force=True)
                for font in previous_fonts.values():
                    gdi.DeleteObject(font)
                return 0
            if msg == 0x113:
                try:
                    self._apply(*self.updates.get_nowait())
                except queue.Empty:
                    pass
                point = W.POINT()
                user.GetCursorPos(C.byref(point))
                hover = user.WindowFromPoint(point)
                title = ""
                if hover == self.listbox and self.list_rows:
                    bind(user, "ScreenToClient", I, H, C.POINTER(W.POINT))
                    local = W.POINT(point.x, point.y)
                    user.ScreenToClient(self.listbox, C.byref(local))
                    hit = user.SendMessageW(self.listbox, 0x1A9, 0, (local.y & 0xFFFF) << 16 | local.x & 0xFFFF)
                    index = hit & 0xFFFF
                    if not hit >> 16 and index < len(self.list_rows):
                        title = self.list_rows[index][1]
                self.tooltip.update(title)
                if hover != getattr(self, "hover", None):
                    for child in (self.up, self.down):
                        if child in (hover, getattr(self, "hover", None)):
                            user.InvalidateRect(child, None, True)
                    self.hover = hover
                return 0
            if msg == 0x111:
                if wparam & 0xFFFF in (104, 105):
                    top = user.SendMessageW(self.listbox, 0x18E, 0, 0)
                    direction = -self.page_rows if wparam & 0xFFFF == 104 else self.page_rows
                    user.SendMessageW(self.listbox, 0x197, max(0, min(len(self.list_rows) - self.page_rows, top + direction)), 0)
                return 0
            if msg in (0x138, 0x134):  # native labels and list box retain accessibility text
                key = next((key for key, control in self.controls.items() if control == lparam), "")
                gdi.SetTextColor(wparam, color(TEXT if key in ("state", "clients", "value5", "value7", "issue") else MUTED))
                gdi.SetBkMode(wparam, 1)
                return self.surface_brush if key in {"usage5", "usage7", "value5", "value7", "reset5", "reset7"} or lparam == self.listbox else self.brush
            if msg == 0x2B:
                item = C.cast(lparam, C.POINTER(DrawItem)).contents
                canvas = Canvas(item.hDC, dpi=self.dpi)
                r = item.rcItem
                try:
                    canvas.fill((r.left, r.top, r.right, r.bottom), SURFACE if item.CtlID == 101 else BACKGROUND)
                    if item.CtlID == 101 and item.itemID < len(self.list_rows):
                        if item.itemState & 1:
                            canvas.rounded((r.left, r.top, r.right, r.bottom), SELECTED, 5)
                        _, title, reason = self.list_rows[item.itemID]
                        split = 25 if self.compact else 31
                        canvas.text(title, (r.left + self.px(12), r.top + self.px(3), r.right - self.px(12), r.top + self.px(split)), size=13 if self.compact else 14)
                        canvas.text(reason, (r.left + self.px(12), r.top + self.px(split - 2), r.right - self.px(12), r.bottom - self.px(3)), shade=MUTED, size=11 if self.compact else 12)
                    elif item.CtlID in (104, 105):
                        hovered = item.hwndItem == getattr(self, "hover", None)
                        canvas.rounded((r.left, r.top, r.right, r.bottom), HOVER if hovered or item.itemState & 1 else SURFACE, 6)
                        canvas.text({104: "↑ Previous", 105: "Next ↓"}[item.CtlID],
                                    (r.left, r.top, r.right, r.bottom), align="center")
                        if item.itemState & 0x10:
                            canvas.fill((r.left, r.bottom - 2, r.right, r.bottom), MUTED)
                finally:
                    canvas.close()
                return 1
            if msg == 0xF and hasattr(self, "usage_y"):
                paint = Paint()
                dc = user.BeginPaint(hwnd, C.byref(paint))
                canvas = Canvas(dc, dpi=self.dpi)
                try:
                    rect = R()
                    user.GetClientRect(hwnd, C.byref(rect))
                    canvas.fill((0, 0, rect.right, rect.bottom), BACKGROUND)
                    label = self.model["label"]
                    shade = "#f87171" if label.startswith("Needs Attention") else "#facc15" if self.model["threads"] else ACCENT
                    if label in {"Stopped", "Starting", "Reconnecting"}:
                        shade = MUTED
                    canvas.rounded((self.px(24), self.px(54), self.px(32), self.px(62)), shade, 4)
                    for index, window in enumerate(self.model["usage"]):
                        x = 24 + index * 238
                        canvas.rounded((self.px(x), self.px(self.usage_y), self.px(x + 226), self.px(self.usage_y + (91 if self.compact else 109))), SURFACE, 9)
                        top = self.px(self.usage_y + (59 if self.compact else 67))
                        canvas.meter((self.px(x + 14), top, self.px(x + 212), top + self.px(5)), window.remaining, stale=window.stale)
                    if self.model["threads"]:
                        canvas.rounded(tuple(self.px(value) for value in self.list_rect), SURFACE, 8)
                finally:
                    canvas.close()
                    user.EndPaint(hwnd, C.byref(paint))
                return 0
        except Exception as exc:
            self.on_error(exc)
        return user.DefWindowProcW(hwnd, msg, wparam, lparam)
