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
    """Create a 512x512 camera-aperture + privacy icon using supersampling.

    Design goals for small-size legibility:
      - Medium-dark navy background (not near-black) for contrast headroom.
      - Filled aperture wedges instead of thin lines — bold at any size.
      - Bright blue/violet palette with high luminance separation from bg.
      - Thick outer ring that remains visible at 16×16.
      - Emerald lock badge in bottom-right corner.
    """
    import math

    # Draw at 4× for crisp anti-aliasing, then downscale
    scale = 4
    cs = size * scale          # canvas size (e.g. 2048 for 512 output)
    img = Image.new("RGBA", (cs, cs), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Background: dark navy (not pure black → contrast with border/ring) ──
    corner_r = cs // 5
    bg_color = (18, 24, 60)    # deep navy
    draw.rounded_rectangle([(0, 0), (cs - 1, cs - 1)],
                            radius=corner_r, fill=bg_color)

    cx, cy = cs // 2, cs // 2

    # ── Outer aperture zone: filled bright circle + dark inner mask ──
    # We paint filled wedge sectors (pieslices) inside a ring zone, then
    # punch a dark disc in the centre so only the ring / blades show.
    ring_outer_r = int(cs * 0.40)
    ring_inner_r = int(cs * 0.22)   # inner boundary of blade zone

    # Blade fill colors: bright and slightly-dimmer alternate
    color_a = (160, 190, 255)       # bright periwinkle
    color_b = (100, 120, 210)       # mid indigo (still clearly visible on navy)

    # 6 blades: every other sector gets color_a vs color_b
    blade_count = 6
    sector_deg = 360 / blade_count
    # Rotate slightly so blades look like a real aperture
    rotation_offset = -15

    for k in range(blade_count):
        start_angle = rotation_offset + k * sector_deg
        end_angle = start_angle + sector_deg
        fill = color_a if k % 2 == 0 else color_b
        draw.pieslice(
            [(cx - ring_outer_r, cy - ring_outer_r),
             (cx + ring_outer_r, cy + ring_outer_r)],
            start=start_angle, end=end_angle, fill=fill
        )

    # Punch dark circle in centre to create the lens opening
    lens_mask_r = ring_inner_r
    draw.ellipse(
        [(cx - lens_mask_r, cy - lens_mask_r),
         (cx + lens_mask_r, cy + lens_mask_r)],
        fill=bg_color
    )

    # ── Thick outer ring — bright white-blue, clearly visible at 16px ──
    ring_w = max(cs // 16, 6)       # ~6% of canvas width — very thick
    ring_color = (210, 225, 255)    # near-white blue
    draw.ellipse(
        [(cx - ring_outer_r, cy - ring_outer_r),
         (cx + ring_outer_r, cy + ring_outer_r)],
        outline=ring_color, width=ring_w
    )

    # ── Inner lens circle (visible glass reflection look) ──
    lens_r = int(cs * 0.13)
    lens_outline_w = max(cs // 28, 4)
    draw.ellipse(
        [(cx - lens_r, cy - lens_r),
         (cx + lens_r, cy + lens_r)],
        fill=(10, 14, 40),
        outline=(160, 190, 255), width=lens_outline_w
    )

    # ── Highlight dot (lens flare) ──
    dot_r = max(cs // 60, 4)
    dot_cx = cx - lens_r // 3
    dot_cy = cy - lens_r // 3
    draw.ellipse(
        [(dot_cx - dot_r, dot_cy - dot_r),
         (dot_cx + dot_r, dot_cy + dot_r)],
        fill=(230, 240, 255, 200)
    )

    # ── Lock badge (bottom-right) ──
    badge_r = int(cs * 0.12)
    badge_cx = cx + int(cs * 0.27)
    badge_cy = cy + int(cs * 0.27)

    # Badge disc
    draw.ellipse(
        [(badge_cx - badge_r, badge_cy - badge_r),
         (badge_cx + badge_r, badge_cy + badge_r)],
        fill=(5, 200, 130)          # bright emerald
    )

    # Lock body (rectangle)
    lw = int(badge_r * 0.52)
    lh = int(badge_r * 0.48)
    lock_top = badge_cy - int(badge_r * 0.04)
    draw.rounded_rectangle(
        [(badge_cx - lw, lock_top),
         (badge_cx + lw, lock_top + lh)],
        radius=max(lw // 4, 2),
        fill=(255, 255, 255)
    )

    # Lock arch (shackle)
    arch_r = int(lw * 0.60)
    arch_w = max(cs // 90, 5)       # thick arch
    draw.arc(
        [(badge_cx - arch_r, lock_top - arch_r),
         (badge_cx + arch_r, lock_top + arch_r // 4)],
        start=180, end=0,
        fill=(255, 255, 255), width=arch_w
    )

    # ── Downsample with Lanczos for clean anti-aliasing ──
    final = img.resize((size, size), Image.Resampling.LANCZOS)
    return final


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
