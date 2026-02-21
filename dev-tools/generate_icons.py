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
    """Create a premium 512x512 SafeToolHub logo using supersampling for perfect antialiasing."""
    # Draw at 4x resolution
    scale = 4
    canvas_size = size * scale
    
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    corner_radius = canvas_size // 4

    # Base background: Deep sleek gradient simulation
    bg_color = (8, 10, 15)
    draw.rounded_rectangle(
        [(0, 0), (canvas_size - 1, canvas_size - 1)],
        radius=corner_radius,
        fill=bg_color,
    )

    # Outer elegant thin ring
    center = canvas_size // 2
    ring_radius = int(canvas_size * 0.35)
    ring_width = canvas_size // 50
    
    draw.ellipse(
        [(center - ring_radius, center - ring_radius), 
         (center + ring_radius, center + ring_radius)],
        outline=(99, 102, 241), width=ring_width
    )

    # Inner minimalistic lock/shield geometric shape
    inner_w = int(canvas_size * 0.15)
    inner_h = int(canvas_size * 0.18)
    
    # The lock body
    draw.rounded_rectangle(
        [(center - inner_w, center), (center + inner_w, center + inner_h)],
        radius=canvas_size // 60,
        fill=(168, 85, 247)
    )

    # The lock arch
    arch_radius = inner_w
    draw.arc(
        [(center - arch_radius, center - arch_radius - inner_h//2),
         (center + arch_radius, center + arch_radius - inner_h//2)],
        start=180, end=0, fill=(168, 85, 247), width=ring_width
    )
    
    # Small dot in the lock
    dot_r = canvas_size // 80
    draw.ellipse(
        [(center - dot_r, center + inner_h//2 - dot_r),
         (center + dot_r, center + inner_h//2 + dot_r)],
        fill=(8, 10, 15)
    )

    # Downsample with high-quality Lanczos filter
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


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
