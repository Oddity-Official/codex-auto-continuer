"""Exercise native tray/menu creation and real controls without automating the user's UI."""
from __future__ import annotations

import ctypes
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from pystray import Icon
from codex_auto_continuer import telemetry, tray
from codex_auto_continuer.config import lock_path
from codex_auto_continuer.icon import tray_image
from codex_auto_continuer.instance_lock import is_running


def wait_for(predicate, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise TimeoutError("Native tray probe did not reach its expected state.")


def main():
    if is_running(lock_path()):
        raise RuntimeError("Stop the supervisor before this owned native tray probe.")
    with tempfile.TemporaryDirectory(prefix="tray-owned-", dir=ROOT / ".data") as directory:
        path = Path(directory)
        controller = tray.TrayController(path / "config.json")
        telemetry.setup(path / "tray.jsonl", controller.cfg)
        dialogs = []
        tray.message = lambda text, **kwargs: dialogs.append(bool(kwargs.get("error")))
        controller.icon = Icon("CACProbe", tray_image("stopped"), "Owned tray validation", menu=controller.menu())
        result = {}
        errors = []
        def ready(icon):
            try:
                icon.visible = True
                menu_handle = icon._menu_handle[0]
                api = ctypes.WinDLL("user32")
                api.GetMenuItemCount.argtypes = [ctypes.c_void_p]
                api.GetMenuItemCount.restype = ctypes.c_int
                result["nativeMenuItems"] = api.GetMenuItemCount(menu_handle)
                if result["nativeMenuItems"] < 20:
                    raise RuntimeError("Native menu omitted required controls.")
                threading.Thread(target=controller.worker, daemon=True).start()
                threading.Thread(target=controller.watch, daemon=True).start()
                items = {item.text: item for item in icon.menu.items}
                items["Start monitoring"](icon)
                wait_for(lambda: not controller.busy and is_running(lock_path()), 15)
                wait_for(lambda: (path / "telemetry.jsonl").exists() and '"cycle.completed"' in (path / "telemetry.jsonl").read_text(), 20)
                before = (path / "telemetry.jsonl").read_text().count('"cycle.completed"')
                items["Scan now"](icon)
                wait_for(lambda: (path / "telemetry.jsonl").read_text().count('"cycle.completed"') > before, 10)
                result["scanWokeSupervisor"] = True
                wait_for(lambda: not controller.busy, 5)
                items["Stop monitoring"](icon)
                wait_for(lambda: not controller.busy and not is_running(lock_path()), 65)
                result["gracefulStop"] = True
                items["Run one cycle"](icon)
                wait_for(lambda: not controller.busy, 35)
                result["oneCycleDialog"] = dialogs == [False]
                items["Quit (stop monitoring)"](icon)
                wait_for(controller.done.is_set, 10)
            except BaseException as exc:
                errors.append(exc)
                try:
                    controller.command("stop")
                finally:
                    controller.done.set()
                    icon.stop()
        controller.icon.run(setup=ready)
        if errors:
            raise errors[0]
        assert result["oneCycleDialog"]
        print(json.dumps(result, indent=2))
        for handler in telemetry._logger.handlers[:]:
            handler.close()
            telemetry._logger.removeHandler(handler)


if __name__ == "__main__":
    main()
