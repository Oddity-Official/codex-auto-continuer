"""Owned native dialogs, isolated from the tray and monitoring command queues."""
from __future__ import annotations

import ctypes
import queue
import threading
import time
from collections.abc import Callable

from . import telemetry


def message(text: str, *, title: str = "Codex Auto Continuer", error: bool = False, confirm: bool = False) -> bool:
    api = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    api.CreateWindowExW.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    api.CreateWindowExW.restype = ctypes.c_void_p
    api.DestroyWindow.argtypes = [ctypes.c_void_p]
    api.DestroyWindow.restype = ctypes.c_int
    api.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    api.MessageBoxW.restype = ctypes.c_int
    # A dedicated STATIC owner uses Windows' window procedure, not pystray's
    # notification dispatcher, and belongs to this dialog's UI thread.
    owner = api.CreateWindowExW(0, "STATIC", "CAC dialog owner", 0x80000000,
                               0, 0, 0, 0, None, None, kernel.GetModuleHandleW(None), None)
    if not owner:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        flags = 0x121 if confirm else 0x10 if error else 0x40
        result = api.MessageBoxW(owner, text, title, flags)
        if result == 0:
            raise ctypes.WinError(ctypes.get_last_error())
        return result == 1 if confirm else True
    finally:
        api.DestroyWindow(owner)


class Dialogs:
    def __init__(self, on_error: Callable[[Exception], None] | None = None):
        self._queue: queue.Queue = queue.Queue()
        self._pending: set[str] = set()
        self._guard = threading.Lock()
        self._thread: threading.Thread | None = None
        self._closed = False
        self._on_error = on_error

    def show(self, key: str, text: str, *, title: str = "Codex Auto Continuer",
             error: bool = False, confirm: bool = False, then: Callable[[], None] | None = None) -> None:
        with self._guard:
            if self._closed or key in self._pending:
                return
            self._pending.add(key)
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="CAC-dialogs", daemon=True)
                self._thread.start()
            self._queue.put((key, text, title, error, confirm, then))

    def _run(self):
        while True:
            request = self._queue.get()
            if request is None:
                return
            key, text, title, error, confirm, then = request
            try:
                if self._closed:
                    continue
                try:
                    telemetry.emit("dialog.opened", dialog=key)
                except OSError:
                    pass  # A broken log must not make its repair controls unusable.
                accepted = message(text, title=title, error=error, confirm=confirm)
                try:
                    telemetry.emit("dialog.closed", dialog=key, accepted=accepted)
                except OSError:
                    pass
                if accepted and then and not self._closed:
                    then()
            except Exception as exc:
                try:
                    telemetry.failure("dialog.failed", exc, dialog=key)
                except OSError:
                    pass
                if self._on_error:
                    self._on_error(exc)
            finally:
                with self._guard:
                    self._pending.discard(key)

    def close(self):
        with self._guard:
            self._closed = True
            self._queue.put(None)
        if not self._thread or not self._thread.native_id:
            return
        api = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_ssize_t)
        api.EnumThreadWindows.argtypes = [ctypes.c_uint, callback_type, ctypes.c_ssize_t]
        api.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        api.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]

        @callback_type
        def dismiss_owned(hwnd, unused):
            name = ctypes.create_unicode_buffer(32)
            api.GetClassNameW(hwnd, name, len(name))
            if name.value == "#32770":
                api.PostMessageW(hwnd, 0x111, 2, 0)  # IDCANCEL closes only our dialog thread's window.
            return 1

        deadline = time.monotonic() + 2
        while self._thread.is_alive() and time.monotonic() < deadline:
            api.EnumThreadWindows(self._thread.native_id, dismiss_owned, 0)
            self._thread.join(timeout=0.05)
