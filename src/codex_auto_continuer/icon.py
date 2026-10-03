from __future__ import annotations


def tray_image(state: str = "monitoring", size: int = 64):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (256, 256))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 248, 248), radius=56, fill="#101c2e")
    draw.arc((49, 48, 202, 201), 40, 322, fill="#f0fdfa", width=22)
    draw.polygon(((197, 47), (205, 108), (151, 78)), fill="#f0fdfa")
    colors = {"monitoring": "#2dd4bf", "waiting": "#fbbf24", "stopped": "#94a3b8", "failed": "#fb7185"}
    draw.ellipse((163, 163, 238, 238), fill=colors[state], outline="#101c2e", width=10)
    return image.resize((size, size), Image.Resampling.LANCZOS)
