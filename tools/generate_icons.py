"""
Generate crisp high-DPI brand icons for Coil-Architect Pro
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw

def create_coil_icon():
    res_dir = Path(__file__).resolve().parent.parent / "resources"
    res_dir.mkdir(parents=True, exist_ok=True)

    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background soft rounded square plate (Tech Deep Slate & Blue gradient border)
    margin = 24
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=96,
        fill="#0F172A",
        outline="#0284C7",
        width=12
    )

    # 2. Subtle inner glow
    draw.rounded_rectangle(
        [margin + 16, margin + 16, size - margin - 16, size - margin - 16],
        radius=80,
        outline="#1E293B",
        width=6
    )

    # 3. Outer Racetrack Coil Loops (Copper gold turns)
    copper_colors = ["#B45309", "#D97706", "#F59E0B", "#FCD34D", "#D97706"]
    
    # 4 distinct concentric racetrack windings
    for idx, col in enumerate(copper_colors):
        offset = 64 + idx * 24
        draw.rounded_rectangle(
            [offset, offset + 20, size - offset, size - offset - 20],
            radius=64 - idx * 6,
            outline=col,
            width=10
        )

    # 4. Central Magnetic Core / Sensor Window
    core_x0 = 190
    core_y0 = 170
    core_x1 = size - 190
    core_y1 = size - 170
    draw.rounded_rectangle(
        [core_x0, core_y0, core_x1, core_y1],
        radius=28,
        fill="#1E293B",
        outline="#38BDF8",
        width=8
    )

    # 5. Electric Spark / Flux Core Symbol in Center
    draw.polygon(
        [
            (size // 2, core_y0 + 18),
            (size // 2 + 36, size // 2 - 8),
            (size // 2 + 6, size // 2 - 8),
            (size // 2 + 24, core_y1 - 18),
            (size // 2 - 36, size // 2 + 8),
            (size // 2 - 6, size // 2 + 8),
        ],
        fill="#0284C7",
        outline="#38BDF8"
    )

    # Save 512x512 PNG
    png_path = res_dir / "app_icon.png"
    img.save(png_path, "PNG")
    print(f"Saved PNG to {png_path}")

    # Generate multi-resolution ICO
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [img.resize(s, Image.Resampling.LANCZOS) for s in ico_sizes]
    ico_path = res_dir / "app_icon.ico"
    ico_images[0].save(
        ico_path,
        format="ICO",
        sizes=ico_sizes,
        append_images=ico_images[1:]
    )
    print(f"Saved ICO to {ico_path}")

    # Generate down_arrow.png for dropdown menus
    arrow_img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    arrow_draw = ImageDraw.Draw(arrow_img)
    arrow_draw.polygon([(3, 5), (13, 5), (8, 11)], fill="#475569")
    arrow_path = res_dir / "down_arrow.png"
    arrow_img.save(arrow_path, "PNG")
    print(f"Saved down_arrow to {arrow_path}")

if __name__ == "__main__":
    create_coil_icon()
