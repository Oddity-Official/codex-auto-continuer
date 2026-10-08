"""Exercise real dark window ownership and safe confirmation dismissal."""
import ctypes as C
import os

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows dialogs")


@pytest.mark.parametrize("action,accepted", [("ok", True), ("cancel", False),
    ("close", False), ("enter", False), ("escape", False)])
def test_confirmation_defaults_to_cancel_and_closes_cleanly(action, accepted, monkeypatch):
    from codex_auto_continuer.windows_dialog import DarkDialog
    from codex_auto_continuer.windows_ui import user, bind, H, I, U
    shown, errors = [], []
    monkeypatch.setattr(user, "ShowWindow", lambda hwnd, how: shown.append(hwnd))
    dwm = C.WinDLL("dwmapi")
    bind(dwm, "DwmGetWindowAttribute", I, H, U, H, U)

    class Fixture(DarkDialog):
        def _proc(self, hwnd, message, wparam, lparam):
            if message == 0x113:
                try:
                    for attribute, expected in ((20, 1), (33, 2)):
                        value = U()
                        assert dwm.DwmGetWindowAttribute(hwnd, attribute, C.byref(value), C.sizeof(value)) == 0
                        assert value.value == expected
                    if action == "close":
                        user.PostMessageW(hwnd, 0x10, 0, 0)
                    elif action in {"enter", "escape"}:
                        user.PostMessageW(self.controls[2], 0x100, 13 if action == "enter" else 27, 0)
                    else:
                        user.PostMessageW(hwnd, 0x111, 1 if action == "ok" else 2, 0)
                except Exception as exc:
                    errors.append(exc)
                    user.PostMessageW(hwnd, 0x10, 0, 0)
                finally:
                    user.KillTimer(hwnd, 1)
                return 0
            return super()._proc(hwnd, message, wparam, lparam)

    dialog = Fixture("Synthetic confirmation. No settings or user data are changed.",
                     "CAC native dialog regression", False, True, None)
    assert dialog.run() is accepted
    assert shown and dialog.hwnd is None and dialog.failure is None
    assert not errors


def test_dialog_queue_shutdown_cancels_without_invoking_the_action(monkeypatch):
    import time
    from codex_auto_continuer.dialogs import Dialogs
    from codex_auto_continuer.windows_ui import user
    monkeypatch.setattr(user, "ShowWindow", lambda hwnd, how: 0)
    actions, errors = [], []
    dialogs = Dialogs(errors.append)
    dialogs.show("fixture", "Synthetic confirmation", confirm=True, then=lambda: actions.append(True))
    deadline = time.monotonic() + 3
    while dialogs._thread and not dialogs._thread.native_id and time.monotonic() < deadline:
        time.sleep(0.01)
    dialogs.close()
    assert not dialogs._thread.is_alive()
    assert not actions and not errors


def test_failed_dialog_setup_does_not_poison_the_next_dialog_loop(monkeypatch):
    from codex_auto_continuer import windows_dialog
    from codex_auto_continuer.windows_ui import user
    style = windows_dialog.style_window
    attempts, displayed = [], []
    def fail_once(hwnd):
        attempts.append(hwnd)
        if len(attempts) == 1:
            raise OSError("Synthetic renderer initialization failure")
        style(hwnd)
    monkeypatch.setattr(windows_dialog, "style_window", fail_once)
    monkeypatch.setattr(user, "ShowWindow", lambda hwnd, how: 0)
    class Fixture(windows_dialog.DarkDialog):
        def _proc(self, hwnd, message, wparam, lparam):
            if message == 0x113:
                displayed.append(True)
                user.PostMessageW(hwnd, 0x10, 0, 0)
            return super()._proc(hwnd, message, wparam, lparam)
    with pytest.raises(OSError, match="Synthetic renderer"):
        Fixture("Fixture", "CAC failed setup", False, True, None).run()
    assert not Fixture("Fixture", "CAC recovered setup", False, True, None).run()
    assert displayed == [True]
