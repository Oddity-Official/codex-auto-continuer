"""Render the SVG master once; CAC ships PNGs, not an SVG rendering runtime."""
from __future__ import annotations

import hashlib
import io
import xml.etree.ElementTree as ET
from pathlib import Path

import resvg_py
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/codex_auto_continuer/assets"
COLORS = {"monitoring": ("#22c55e", "#e5fff0"), "stopped": ("#facc15", "#fff9df"), "failed": ("#ef4444", "#fff0ef")}


def render():
    master = (ASSETS / "cac.svg").read_bytes()
    for state, (fill, stroke) in COLORS.items():
        tree = ET.fromstring(master)
        tree.set("width", "256")
        tree.set("height", "256")
        arrow = next(element for element in tree.iter() if element.get("id") == "arrow")
        arrow.set("fill", fill)
        arrow.set("stroke", stroke)
        output = resvg_py.svg_to_bytes(svg_string=ET.tostring(tree, encoding="unicode"))
        image = Image.open(io.BytesIO(output)).convert("RGBA")
        info = PngImagePlugin.PngInfo()
        info.add_text("svg_sha256", hashlib.sha256(master).hexdigest())
        image.save(ASSETS / f"{state}.png", pnginfo=info)
    print("Rendered green, yellow and red PNGs from assets/cac.svg")


if __name__ == "__main__":
    render()
