#!/usr/bin/env python3
"""
Generate application icons for InnerPix Lab.

Creates:
  - assets/icon.png  (512x512 master icon)
  - assets/icon.ico  (Windows multi-resolution: 16, 32, 48, 64, 128, 256)

macOS .icns is generated in CI via iconutil (requires macOS).

Usage:
    python dev-tools/generate_icons.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def create_master_png(size: int = 512) -> Image.Image:
    """Create a 512x512 placeholder icon with gradient and 'IP' text."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background with gradient-like effect
    # Dark teal to blue gradient (simplified as solid for reliability)
    bg_color = (13, 110, 193)  # Brand blue
    corner_radius = size // 8

    # Draw rounded rectangle
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=corner_radius,
        fill=bg_color,
    )

    # Subtle lighter accent stripe
    accent_color = (30, 144, 220, 60)
    draw.rounded_rectangle(
        [(size // 6, size // 6), (size - size // 6, size - size // 6)],
        radius=corner_radius // 2,
        fill=accent_color,
    )

    # Draw "IP" initials
    font_size = size // 3
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("Arial Bold", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    text = "Innerpix Lab"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2 - bbox[1]

    # Text shadow
    draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 80), font=font)
    # Main text
    draw.text((x, y), text, fill=(255, 255, 255), font=font)

    return img


def create_ico(master: Image.Image, output: Path) -> None:
    """Create .ico with multiple resolutions from master PNG."""
    sizes = [16, 32, 48, 64, 128, 256]
    icons = []
    for s in sizes:
        resized = master.resize((s, s), Image.Resampling.LANCZOS)
        icons.append(resized)

    icons[0].save(
        output,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:],
    )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    print("Generating master icon (512x512 PNG)...")
    master = create_master_png(512)
    png_path = ASSETS / "icon.png"
    master.save(png_path, "PNG")
    print(f"  → {png_path}")

    print("Generating Windows icon (.ico)...")
    ico_path = ASSETS / "icon.ico"
    create_ico(master, ico_path)
    print(f"  → {ico_path}")

    print("Done! macOS .icns will be generated in CI.")


if __name__ == "__main__":
    main()
