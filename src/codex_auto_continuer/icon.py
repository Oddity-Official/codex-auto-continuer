from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=3)
def _image(color):
    from PIL import Image
    with Image.open(Path(__file__).parent / "assets" / f"{color}.png") as source:
        return source.convert("RGBA")


def tray_image(state: str = "monitoring", size: int = 64):
    from PIL import Image
    colors = {"monitoring": "monitoring", "waiting": "monitoring", "scanning": "monitoring",
              "stopped": "stopped", "starting": "stopped", "paused": "stopped", "reconnecting": "stopped", "failed": "failed"}
    return _image(colors[state]).resize((size, size), Image.Resampling.LANCZOS)
