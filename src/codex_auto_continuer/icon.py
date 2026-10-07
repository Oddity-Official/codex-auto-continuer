from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def native_icon():
    """Return an owned Windows HICON; the caller must destroy it on close."""
    import ctypes
    import tempfile
    from pystray._util import win32
    with tempfile.TemporaryDirectory(prefix="cac-icon-") as directory:
        path = Path(directory) / "cac.ico"
        tray_image("monitoring", size=32).save(path, format="ICO")
        handle = win32.LoadImage(None, str(path), win32.IMAGE_ICON, 32, 32, win32.LR_LOADFROMFILE)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


@lru_cache(maxsize=20)
def _image(color, pending):
    from PIL import Image
    with Image.open(Path(__file__).parent / "assets" / f"{color}-{pending}.png") as source:
        return source.convert("RGBA")


def tray_image(state: str = "monitoring", size: int = 64, pending: int = 0):
    from PIL import Image
    colors = {"monitoring": "monitoring", "waiting": "waiting", "scanning": "monitoring",
              "stopped": "stopped", "starting": "stopped", "paused": "stopped", "reconnecting": "stopped", "failed": "failed"}
    return _image(colors[state], min(4, max(0, pending))).resize((size, size), Image.Resampling.LANCZOS)
