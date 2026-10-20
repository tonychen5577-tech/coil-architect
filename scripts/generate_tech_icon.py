"""
Generate ultra-high-definition, multi-resolution modern industrial tech icon for Coil-Architect Pro.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def draw_master_icon(size: int = 1024) -> Image.Image:
    # 4x super-sampling for pristine antialiasing (canvas 2048 -> 1024)
    canvas_size = 2048
    scale = canvas_size / 1024.0

    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background Squircle
    margin = int(50 * scale)
    corner_r = int(220 * scale)
    box = (margin, margin, canvas_size - margin, canvas_size - margin)

    # Create background mask with rounded rectangle
    mask = Image.new("L", (canvas_size, canvas_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(box, radius=corner_r, fill=255)

    # Create gradient background
    bg = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)

    # Deep space titanium navy gradient
    for y in range(margin, canvas_size - margin):
        ratio = (y - margin) / (canvas_size - 2 * margin)
        # Gradient from (20, 32, 54) to (10, 16, 28)
        r = int(22 * (1 - ratio) + 9 * ratio)
        g = int(36 * (1 - ratio) + 14 * ratio)
        b = int(58 * (1 - ratio) + 26 * ratio)
        bg_draw.line([(margin, y), (canvas_size - margin, y)], fill=(r, g, b, 255))

    # Apply radial center highlight (subtle glow behind the coil)
    center_glow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    cg_draw = ImageDraw.Draw(center_glow)
    cx, cy = canvas_size // 2, canvas_size // 2 - int(30 * scale)
    max_radius = int(550 * scale)
    for rad in range(max_radius, 0, -8):
        alpha = int(45 * (1.0 - rad / max_radius) ** 1.8)
        cg_draw.ellipse(
            (cx - rad, cy - rad, cx + rad, cy + rad),
            fill=(14, 116, 204, alpha)
        )
    bg.alpha_composite(center_glow)

    # High-tech CAD engineering grid
    grid_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_img)
    step = int(64 * scale)
    for x in range(margin, canvas_size - margin, step):
        grid_draw.line([(x, margin), (x, canvas_size - margin)], fill=(56, 189, 248, 16), width=1)
    for y in range(margin, canvas_size - margin, step):
        grid_draw.line([(margin, y), (canvas_size - margin, y)], fill=(56, 189, 248, 16), width=1)

    # Reticle crosshairs
    for px, py in [
        (margin + int(120 * scale), margin + int(120 * scale)),
        (canvas_size - margin - int(120 * scale), margin + int(120 * scale)),
        (margin + int(120 * scale), canvas_size - margin - int(120 * scale)),
        (canvas_size - margin - int(120 * scale), canvas_size - margin - int(120 * scale)),
    ]:
        arm = int(24 * scale)
        grid_draw.line([(px - arm, py), (px + arm, py)], fill=(0, 220, 255, 60), width=int(2 * scale))
        grid_draw.line([(px, py - arm), (px, py + arm)], fill=(0, 220, 255, 60), width=int(2 * scale))
        grid_draw.ellipse([(px - 6 * scale, py - 6 * scale), (px + 6 * scale, py + 6 * scale)], outline=(0, 220, 255, 80), width=1)

    bg.alpha_composite(grid_img)

    # Composite bg onto img via squircle mask
    img.paste(bg, (0, 0), mask)

    # 2. Glowing Outer Squircle Rim
    rim_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    rim_draw = ImageDraw.Draw(rim_img)

    # Outer cyan neon glow
    rim_draw.rounded_rectangle(box, radius=corner_r, outline=(0, 210, 255, 140), width=int(8 * scale))
    rim_blur = rim_img.filter(ImageFilter.GaussianBlur(radius=int(14 * scale)))
    img.alpha_composite(rim_blur)

    # Sharp boundary stroke with top-left highlight
    rim_sharp = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    rs_draw = ImageDraw.Draw(rim_sharp)
    rs_draw.rounded_rectangle(box, radius=corner_r, outline=(0, 229, 255, 230), width=int(4 * scale))
    # Inner subtle bevel
    inner_box = (margin + int(4 * scale), margin + int(4 * scale), canvas_size - margin - int(4 * scale), canvas_size - margin - int(4 * scale))
    rs_draw.rounded_rectangle(inner_box, radius=corner_r - int(4 * scale), outline=(255, 255, 255, 45), width=int(2 * scale))
    img.alpha_composite(rs_sharp:=rim_sharp)

    # 3. Main Subject: Precision Electromagnetic Coil & Magnetic Flux Field
    # Coil is placed slightly tilted/isometric for maximum 3D industrial presence
    coil_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(coil_layer)

    coil_cx = canvas_size // 2
    coil_cy = canvas_size // 2 + int(10 * scale)

    # 3.1 Back Flux Vector Beam (emanating through the core)
    beam_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(beam_img)
    b_top = coil_cy - int(380 * scale)
    b_bot = coil_cy + int(360 * scale)
    b_w = int(140 * scale)

    for i in range(b_w, 0, -4):
        p = 1.0 - (i / b_w)
        alpha = int(90 * p)
        # Vertical cyan energy core
        b_draw.rectangle(
            (coil_cx - i, b_top, coil_cx + i, b_bot),
            fill=(0, int(200 + 55 * p), 255, alpha)
        )
    beam_blur = beam_img.filter(ImageFilter.GaussianBlur(radius=int(20 * scale)))
    img.alpha_composite(beam_blur)

    # 3.2 Toroidal Magnetic Flux Loops (Cyan glowing magnetic lines circling the coil)
    flux_lines = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    fl_draw = ImageDraw.Draw(flux_lines)

    # Outer magnetic flux oval loops (left & right lobes)
    for side in (-1, 1):
        lobe_cx = coil_cx + side * int(380 * scale)
        lobe_cy = coil_cy
        rx = int(220 * scale)
        ry = int(320 * scale)
        fl_draw.ellipse(
            (lobe_cx - rx, lobe_cy - ry, lobe_cx + rx, lobe_cy + ry),
            outline=(0, 225, 255, 90),
            width=int(4 * scale)
        )
        # Magnetic flux direction arrows / markers
        arrow_y = lobe_cy + int(side * 80 * scale)
        arrow_x = lobe_cx - side * rx
        fl_draw.polygon(
            [
                (arrow_x - 12 * scale, arrow_y + 16 * scale),
                (arrow_x + 12 * scale, arrow_y + 16 * scale),
                (arrow_x, arrow_y - 20 * scale)
            ],
            fill=(0, 240, 255, 180)
        )

    flux_blur = flux_lines.filter(ImageFilter.GaussianBlur(radius=int(6 * scale)))
    img.alpha_composite(flux_blur)
    img.alpha_composite(flux_lines)

    # 3.3 Multi-Turn Precision Winding Layers (Golden / Copper Coils)
    # Racetrack / Toroid in 2.5D Isometric view
    # Layers stack from bottom to top, outer to inner
    # Coil outer dimension: w ~ 640px, h ~ 380px in 2D perspective
    w_outer = int(360 * scale)
    h_outer = int(220 * scale)
    straight_l = int(180 * scale)  # racetrack straight edge

    # Draw 3D Coil Depth (bottom shadow/extrusion)
    depth_layers = int(48 * scale)
    for dz in range(depth_layers, 0, -int(3 * scale)):
        cur_y = coil_cy + dz
        # Dark copper bronze base
        c_draw.rounded_rectangle(
            (coil_cx - w_outer, cur_y - h_outer, coil_cx + w_outer, cur_y + h_outer),
            radius=h_outer,
            fill=(100, 40, 10, 220),
            outline=(60, 25, 8, 255),
            width=int(2 * scale)
        )

    # Render distinct precision turns (Concentric Racetrack rings)
    num_turns = 8
    turn_thickness = int(24 * scale)

    for turn_idx in range(num_turns):
        t_factor = turn_idx / (num_turns - 1)  # 0: outermost, 1: innermost
        cur_w = int(w_outer - turn_idx * turn_thickness)
        cur_h = int(h_outer - turn_idx * (turn_thickness * 0.72))

        if cur_w <= int(70 * scale) or cur_h <= int(40 * scale):
            break

        # Copper gradient color along the circumference:
        # Top-left gets bright reflective gold (highlight), bottom gets rich warm amber copper
        top_color = (
            int(255 * (1 - 0.1 * t_factor)),
            int(215 * (1 - 0.1 * t_factor)),
            int(80 * (1 - 0.1 * t_factor)),
            255
        )
        base_color = (
            int(217 - 30 * t_factor),
            int(119 - 25 * t_factor),
            int(6 + 10 * t_factor),
            255
        )

        # Draw turn body
        c_draw.rounded_rectangle(
            (coil_cx - cur_w, coil_cy - cur_h, coil_cx + cur_w, coil_cy + cur_h),
            radius=cur_h,
            outline=base_color,
            width=int(18 * scale)
        )

        # Highlight sheen on top rim of wire turn
        sheen_color = (255, 245, 180, int(200 - 60 * t_factor))
        c_draw.arc(
            (coil_cx - cur_w, coil_cy - cur_h, coil_cx + cur_w, coil_cy + cur_h),
            start=190, end=350,
            fill=sheen_color,
            width=int(4 * scale)
        )

        # Dark wire boundary groove for high-precision micro-winding definition
        c_draw.rounded_rectangle(
            (coil_cx - cur_w, coil_cy - cur_h, coil_cx + cur_w, coil_cy + cur_h),
            radius=cur_h,
            outline=(45, 20, 5, 120),
            width=int(2 * scale)
        )

    # 3.4 Inner Aperture: Hollow core with intense magnetic vortex glow
    core_w = int(w_outer - num_turns * turn_thickness)
    core_h = int(h_outer - num_turns * (turn_thickness * 0.72))
    c_draw.rounded_rectangle(
        (coil_cx - core_w, coil_cy - core_h, coil_cx + core_w, coil_cy + core_h),
        radius=core_h,
        fill=(8, 14, 26, 255),
        outline=(0, 200, 255, 200),
        width=int(4 * scale)
    )

    # Core luminous flux beam (passing out through the coil center)
    core_glow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    cg_draw = ImageDraw.Draw(core_glow)
    for cr in range(core_h, 0, -int(4 * scale)):
        ratio = 1.0 - (cr / core_h)
        alpha = int(180 * ratio)
        cg_draw.rounded_rectangle(
            (coil_cx - int(core_w * cr / core_h), coil_cy - cr, coil_cx + int(core_w * cr / core_h), coil_cy + cr),
            radius=cr,
            fill=(0, int(220 + 35 * ratio), 255, alpha)
        )
    core_glow_blur = core_glow.filter(ImageFilter.GaussianBlur(radius=int(12 * scale)))
    c_draw_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    c_draw_img.alpha_composite(coil_layer)
    c_draw_img.alpha_composite(core_glow_blur)

    img.alpha_composite(c_draw_img)

    # 4. Front Magnetic Flux Field Lines (Passing over the front of the coil)
    front_fx = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    ff_draw = ImageDraw.Draw(front_fx)

    # High-energy central magnetic induction vector arrow (pointing upward from core)
    arrow_tip_y = coil_cy - int(240 * scale)
    arrow_bot_y = coil_cy - int(70 * scale)
    arrow_w = int(28 * scale)

    # Glowing vector shaft
    ff_draw.line(
        [(coil_cx, arrow_bot_y), (coil_cx, arrow_tip_y)],
        fill=(0, 255, 255, 255),
        width=int(10 * scale)
    )
    # Glowing vector arrowhead
    ff_draw.polygon(
        [
            (coil_cx - arrow_w, arrow_tip_y + int(36 * scale)),
            (coil_cx + arrow_w, arrow_tip_y + int(36 * scale)),
            (coil_cx, arrow_tip_y)
        ],
        fill=(0, 255, 255, 255)
    )
    # Vector symbol text B with arrow
    # Add energy particles / sparkles
    for px, py, sz in [
        (coil_cx - int(120 * scale), coil_cy - int(160 * scale), 8),
        (coil_cx + int(140 * scale), coil_cy - int(140 * scale), 6),
        (coil_cx - int(180 * scale), coil_cy + int(110 * scale), 7),
        (coil_cx + int(210 * scale), coil_cy + int(90 * scale), 9),
        (coil_cx, coil_cy + int(200 * scale), 8),
    ]:
        ff_draw.ellipse(
            (px - sz * scale, py - sz * scale, px + sz * scale, py + sz * scale),
            fill=(255, 255, 255, 240)
        )

    front_blur = front_fx.filter(ImageFilter.GaussianBlur(radius=int(10 * scale)))
    img.alpha_composite(front_blur)
    img.alpha_composite(front_fx)

    # 5. Bottom Brand & Tech Monogram Badge: "COIL ARCHITECT" / "ANSV"
    # Modern sleek tech badge centered at bottom
    badge_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_layer)

    badge_w = int(320 * scale)
    badge_h = int(64 * scale)
    badge_x = coil_cx - badge_w // 2
    badge_y = canvas_size - margin - int(130 * scale)

    # Badge pill background
    b_draw.rounded_rectangle(
        (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
        radius=badge_h // 2,
        fill=(15, 23, 42, 230),
        outline=(0, 210, 255, 180),
        width=int(3 * scale)
    )

    # Draw technical monogram letters "COIL ARCHITECT"
    try:
        # Try loading system font (Segoe UI or Arial or Microsoft YaHei)
        font_path = "C:/Windows/Fonts/segoeuib.ttf"
        if not Path(font_path).exists():
            font_path = "C:/Windows/Fonts/arialbd.ttf"
        font = ImageFont.truetype(font_path, size=int(28 * scale))
        text = "COIL ARCHITECT"
        bbox = b_draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = coil_cx - tw // 2
        ty = badge_y + (badge_h - th) // 2 - int(4 * scale)
        b_draw.text((tx, ty), text, font=font, fill=(240, 249, 255, 255))
    except Exception:
        # Fallback without font
        pass

    img.alpha_composite(badge_layer)

    # Downsample from 2048x2048 to 1024x1024 with high-precision Lanczos
    final_master = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_master


def export_multi_res_icons():
    print("[*] Generating 1024x1024 Master Tech Icon...")
    master = draw_master_icon(1024)

    # Save High-Res PNG (512x512)
    png_512 = master.resize((512, 512), Image.Resampling.LANCZOS)
    res_dir = Path("resources")
    res_dir.mkdir(parents=True, exist_ok=True)

    png_target = res_dir / "app_icon.png"
    png_512.save(png_target, "PNG", optimize=True)
    print(f"[OK] Saved HD PNG to {png_target} ({png_target.stat().st_size / 1024:.1f} KB)")

    # Save Multi-Resolution Windows ICO
    # Windows 10/11 standard sizes: 256, 128, 64, 48, 32, 24, 16
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    ico_target = res_dir / "app_icon.ico"

    # Pillow can save ICO with multiple sizes embedded!
    # The image to save as ICO must have sizes passed
    master.save(
        ico_target,
        format="ICO",
        sizes=ico_sizes
    )
    print(f"[OK] Saved Multi-Res ICO to {ico_target} ({ico_target.stat().st_size / 1024:.1f} KB, {len(ico_sizes)} layers)")

    # Also save a preview in brain directory for artifact viewing
    preview_path = Path(r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b\new_tech_icon_preview.png")
    master.resize((512, 512), Image.Resampling.LANCZOS).save(preview_path)
    print(f"[OK] Saved preview to {preview_path}")


if __name__ == "__main__":
    export_multi_res_icons()
