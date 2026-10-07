"""Render existing icon variants at tray sizes; no visible windows or Codex access."""
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
    sheet = Image.new("RGB", (720, 350), "#191d24")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), "Actual-size icons: 16 / 20 / 24 / 32 px; pending layers 0 through 4", fill="white")
    for row, state in enumerate(("monitoring", "waiting", "stopped", "failed")):
        y = 45 + row * 74
        draw.text((12, y), state, fill="white")
        for pending in range(5):
            x = 116 + pending * 119
            draw.text((x, y - 16), str(pending), fill="#a4afc0")
            with Image.open(root / "src/codex_auto_continuer/assets" / f"{state}-{pending}.png") as icon:
                for size in (16, 20, 24, 32):
                    small = icon.resize((size, size), Image.Resampling.LANCZOS)
                    sheet.paste(small, (x, y), small)
                    x += size + 5
    target = Path(__file__).with_name("icon-sizes.png")
    sheet.save(target)
    print(target)


if __name__ == "__main__":
    main()
