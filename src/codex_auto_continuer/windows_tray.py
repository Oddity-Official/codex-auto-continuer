"""Keep each native popup intact for its entire Windows tracking loop."""
from __future__ import annotations

from pystray._win32 import Icon
from pystray._util import win32


class TrayIcon(Icon):
    """A pystray Win32 icon with menu snapshots built on the UI thread."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._menu_handle = None
        self._popup_open = False

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
            super()._update_menu()
            return super()._on_notify(wparam, lparam)
        finally:
            self._popup_open = False
