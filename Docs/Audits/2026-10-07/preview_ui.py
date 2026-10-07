"""Bounded, synthetic native UI inspection. Never connects to Codex or changes login."""
from __future__ import annotations

import sys
import ctypes
import argparse
import tempfile
import threading
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer.tray import TrayController
from codex_auto_continuer.windows_tray import TrayIcon
from codex_auto_continuer.status_window import StatusWindow
from codex_auto_continuer.state import State, Obligation, save_state
from codex_auto_continuer.icon import tray_image
from codex_auto_continuer.presentation import usage_snapshot
from codex_auto_continuer.windows_ui import user


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("many", "empty", "menu", "unknown", "error"):
        parser.add_argument("--" + flag, action="store_true")
    parser.add_argument("--dpi", type=int, choices=(96, 144, 192))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="cac-ui-") as directory:
        controller = TrayController(Path(directory) / "settings.toml")
        count = 9 if args.many else 0 if args.empty else 3
        obligations = [Obligation.create(f"fixture-{index}", f"failed-{index}", time.time(), None) for index in range(count)]
        save_state(controller.config_file.parent / "state.json", State(obligations=obligations))
        controller.snapshot = {"pending": count, "ordinary_usage_allowed": False, "lastScanAt": time.time(),
            "usage": usage_snapshot({"rateLimits": {"primary": {"usedPercent": 27, "windowDurationMins": 300, "resetsAt": time.time() + 3600},
                                                    "secondary": {"usedPercent": 59, "windowDurationMins": 10080, "resetsAt": time.time() + 172800}}}, time.time()),
            "compatibility": {"status": "untested", "read_allowed": True, "dispatch_allowed": True}}
        controller.running = True
        controller.state = "waiting" if count else "monitoring"
        if args.unknown:
            controller.snapshot["usage"] = usage_snapshot({}, time.time())
        if args.error:
            controller.state = "failed"
            controller.problem = "Synthetic compatibility block. Read Details for the exact build; pending work is preserved."
        controller.enqueue = lambda *args: print("Fixture action:", args, flush=True)
        controller.open = lambda *args: print("Fixture file action:", args, flush=True)
        controller.lookup_titles = lambda identities: {identity: (
            "Story Linter — Performance Pass" if index == 0 else None if index == 1 else
            "A Very Long Authoritative Thread Title That Must Not Widen The Status Panel " * 3)
            for index, identity in enumerate(identities)}
        errors = []
        def failed(exc):
            errors.append(exc)
            print("UI ERROR:", repr(exc), flush=True)
        class PreviewPanel(StatusWindow):
            def _details(self):
                print("Fixture details opened", flush=True)
                return super()._details()

            def _proc(self, hwnd, message, wparam, lparam):
                if message in (0x10, 0x111):
                    print("Fixture window action:", hex(message), wparam, flush=True)
                return super()._proc(hwnd, message, wparam, lparam)

            def _apply(self, *values, **options):
                if args.dpi:
                    self.dpi, self.scale = args.dpi, args.dpi / 96
                return super()._apply(*values, **options)
        panel = PreviewPanel(controller.status_model, controller.lookup_titles, failed)
        controller.status_window = panel
        icon = TrayIcon("CACPreview", tray_image("waiting" if count else "monitoring", pending=count),
                        "CAC UI Preview", menu=controller.menu(), usage_provider=controller.usage)
        controller.icon = icon
        if args.menu:
            from pystray._util import win32
            # A visible owner lets window-scoped Computer Use target native menus.
            # Rendering, callbacks and the tracking loop remain production code.
            def preview_menu():
                original = icon._hwnd, icon._menu_hwnd, icon._subclass
                icon._hwnd = icon._menu_hwnd = panel.hwnd
                icon._subclass = None
                try:
                    icon._on_notify(0, win32.WM_RBUTTONUP)
                finally:
                    from codex_auto_continuer.windows_ui import bind, H, P
                    api = ctypes.WinDLL("comctl32")
                    bind(api, "RemoveWindowSubclass", ctypes.c_int, H, H, P)
                    if icon._subclass:
                        api.RemoveWindowSubclass(panel.hwnd, ctypes.cast(icon._subclass, H), 1)
                    icon._hwnd, icon._menu_hwnd, icon._subclass = original
            panel._details = preview_menu
        def ready(unused):
            icon.visible = True
            panel.show()
        def stop():
            panel.close()
            icon.stop()
        timer = threading.Timer(300, stop)
        timer.start()
        try:
            icon.run(setup=ready)
        finally:
            timer.cancel()
            panel.close()
        if errors:
            raise RuntimeError(f"Native UI errors: {errors!r}")


if __name__ == "__main__":
    main()
