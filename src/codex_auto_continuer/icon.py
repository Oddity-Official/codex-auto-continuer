from __future__ import annotations

from functools import lru_cache
from pathlib import Path


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
