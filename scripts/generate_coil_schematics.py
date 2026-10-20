"""
生成 4 大电磁线圈拓扑工业示意图 (八角形、跑道形、圆环形、矩形圆角)
并输出高清晰度独立图与 4 合 1 工业全景图
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

# 设置中文字体与图形样式
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

out_dir = Path("docs/images")
out_dir.mkdir(parents=True, exist_ok=True)

# 颜色定义 (SolidWorks 经典工业色调 + 铜线质感)
COLOR_COPPER_FILL = "#FDE68A"      # 浅铜金填充
COLOR_COPPER_STROKE = "#B45309"    # 深铜边框
COLOR_INNER_FILL = "#F8FAFC"       # 内部空腔 (淡灰蓝)
COLOR_DIM_LINE = "#0284C7"         # 尺寸标注主色 (工业蓝)
COLOR_DIM_TEXT = "#0F172A"         # 标注文字色
COLOR_GRID = "#F1F5F9"             # 极淡工程网格


def draw_dimension(ax, p1, p2, text, offset=(0, 0), text_offset=(0, 0), arrow_style="<->", text_pos="center", color=COLOR_DIM_LINE):
    """绘制工业制图标注线与双向箭头"""
    x1, y1 = p1[0] + offset[0], p1[1] + offset[1]
    x2, y2 = p2[0] + offset[0], p2[1] + offset[1]
    
    # 标注延伸线 (如果 offset != (0,0))
    if offset[0] != 0 or offset[1] != 0:
        ax.plot([p1[0], x1], [p1[1], y1], color="#94A3B8", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.plot([p2[0], x2], [p2[1], y2], color="#94A3B8", linestyle="--", linewidth=0.8, alpha=0.7)
        
    ax.annotate(
        "", xy=(x1, y1), xytext=(x2, y2),
        arrowprops=dict(arrowstyle=arrow_style, color=color, lw=1.2, shrinkA=0, shrinkB=0)
    )
    mid_x = (x1 + x2) / 2.0 + text_offset[0]
    mid_y = (y1 + y2) / 2.0 + text_offset[1]
    ax.text(mid_x, mid_y, text, color=color, fontsize=9.5, fontweight="bold",
            ha="center", va="center", bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", edgecolor="none", alpha=0.85))


def draw_octagonal_shape(ax):
    """1. 八角形微型线圈 (Octagonal Coil)"""
    ax.set_title("1. 八角形微型线圈 (Octagonal Coil)\n【适用: 旗舰手机潜望式长焦 / VCM 镜头马达】", fontsize=11, fontweight="bold", pad=12, color="#0F172A")
    ax.set_xlim(-5.5, 5.5)
    ax.set_ylim(-5.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # 外八角与内八角多边形顶点计算
    def get_oct_vertices(r, corner_cut):
        # r 是外框半对边宽
        return [
            (r - corner_cut, r), (-(r - corner_cut), r),
            (-r, r - corner_cut), (-r, -(r - corner_cut)),
            (-(r - corner_cut), -r), (r - corner_cut, -r),
            (r, -(r - corner_cut)), (r, r - corner_cut)
        ]

    # 外轮廓与内轮廓
    poly_out = get_oct_vertices(3.8, 1.2)
    poly_in = get_oct_vertices(2.8, 0.9)

    patch_out = patches.Polygon(poly_out, closed=True, facecolor=COLOR_COPPER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=2.2)
    patch_in = patches.Polygon(poly_in, closed=True, facecolor=COLOR_INNER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=1.8)
    ax.add_patch(patch_out)
    ax.add_patch(patch_in)

    # 绘制内部铜线多层多列示意纹理
    for shrink in [0.25, 0.5, 0.75]:
        r_mid = 2.8 + shrink * (3.8 - 2.8)
        c_mid = 0.9 + shrink * (1.2 - 0.9)
        poly_m = get_oct_vertices(r_mid, c_mid)
        ax.add_patch(patches.Polygon(poly_m, closed=True, fill=False, edgecolor="#D97706", linewidth=0.8, linestyle=":", alpha=0.7))

    # 标注尺寸
    # 对边内径
    draw_dimension(ax, (-2.8, 0), (2.8, 0), "对边内径 W_opp", text_offset=(0, 0.35))
    # 对边外径
    draw_dimension(ax, (-3.8, -3.8), (3.8, -3.8), "对边外径 OD", offset=(0, -0.6))
    # 拐角斜切过渡
    ax.annotate("45° 倒角过渡 R", xy=(3.1, 3.1), xytext=(4.2, 4.3),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=1.2),
                fontsize=9, color="#059669", fontweight="bold")
    # 线圈壁厚
    draw_dimension(ax, (2.8, 1.5), (3.8, 1.5), "壁厚 t", text_offset=(0, 0.4), color="#DC2626")


def draw_racetrack_shape(ax):
    """2. 跑道形微型线圈 (Racetrack / Oblong Coil)"""
    ax.set_title("2. 跑道形线圈 (Racetrack / Oblong)\n【适用: 触觉振动马达 LRA / 狭长对称微执行器】", fontsize=11, fontweight="bold", pad=12, color="#0F172A")
    ax.set_xlim(-5.5, 5.5)
    ax.set_ylim(-5.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # 跑道形由两侧半圆和上下平直段构成
    # 外跑道: 直段长 3.2 (x from -1.6 to 1.6), 半圆半径 R_out = 2.0
    # 内跑道: 直段长 3.2, 半圆半径 R_in = 1.2
    def create_racetrack_path(L, R):
        from matplotlib.path import Path as MPath
        # 半圆顶点采样
        theta_r = np.linspace(-np.pi/2, np.pi/2, 30)
        theta_l = np.linspace(np.pi/2, 3*np.pi/2, 30)
        
        xr = L/2.0 + R * np.cos(theta_r)
        yr = R * np.sin(theta_r)
        xl = -L/2.0 + R * np.cos(theta_l)
        yl = R * np.sin(theta_l)

        xs = np.concatenate([[L/2.0, -L/2.0], xl, [-L/2.0, L/2.0], xr])
        ys = np.concatenate([[R, R], yl, [-R, -R], yr])
        return list(zip(xs, ys))

    p_out = create_racetrack_path(3.0, 2.2)
    p_in = create_racetrack_path(3.0, 1.2)

    ax.add_patch(patches.Polygon(p_out, closed=True, facecolor=COLOR_COPPER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=2.2))
    ax.add_patch(patches.Polygon(p_in, closed=True, facecolor=COLOR_INNER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=1.8))

    # 排线层理
    for s in [0.33, 0.66]:
        p_m = create_racetrack_path(3.0, 1.2 + s * 1.0)
        ax.add_patch(patches.Polygon(p_m, closed=True, fill=False, edgecolor="#D97706", linewidth=0.8, linestyle=":", alpha=0.7))

    # 标注
    draw_dimension(ax, (-1.5, 0), (1.5, 0), "直段内长 L_str", text_offset=(0, 0.35))
    draw_dimension(ax, (0, -1.2), (0, 1.2), "内宽 W_in", text_offset=(0.6, 0))
    draw_dimension(ax, (-3.7, 0), (3.7, 0), "总长度 L_total", offset=(0, -2.6))
    ax.annotate("端部圆弧 R_arc", xy=(2.7, 1.0), xytext=(3.6, 2.3),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=1.2),
                fontsize=9, color="#059669", fontweight="bold")


def draw_circular_shape(ax):
    """3. 经典圆环形线圈 (Circular Coil)"""
    ax.set_title("3. 经典圆环形线圈 (Circular / Cylindrical)\n【适用: 旋转音圈电机 / 微型对焦马达 / 电磁阀】", fontsize=11, fontweight="bold", pad=12, color="#0F172A")
    ax.set_xlim(-5.5, 5.5)
    ax.set_ylim(-5.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")

    c_out = patches.Circle((0, 0), 3.5, facecolor=COLOR_COPPER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=2.2)
    c_in = patches.Circle((0, 0), 2.2, facecolor=COLOR_INNER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=1.8)
    ax.add_patch(c_out)
    ax.add_patch(c_in)

    # 内部同心绕线纹理
    for r in [2.6, 3.05]:
        ax.add_patch(patches.Circle((0, 0), r, fill=False, edgecolor="#D97706", linewidth=0.8, linestyle=":", alpha=0.7))

    # 标注
    draw_dimension(ax, (-2.2, 0), (2.2, 0), "内径 Ø ID", text_offset=(0, 0.35))
    draw_dimension(ax, (-3.5, 0), (3.5, 0), "外径 Ø OD", offset=(0, -3.8))
    draw_dimension(ax, (2.2, 0), (3.5, 0), "径向壁厚 t", offset=(0, 1.8), color="#DC2626")
    ax.plot([0, 0], [-4.0, 4.0], color="#94A3B8", linestyle="-.", linewidth=0.7, alpha=0.6)
    ax.plot([-4.0, 4.0], [0, 0], color="#94A3B8", linestyle="-.", linewidth=0.7, alpha=0.6)


def draw_rectangular_shape(ax):
    """4. 矩形圆角线圈 (Rectangular Coil)"""
    ax.set_title("4. 矩形圆角线圈 (Rectangular / Corner R)\n【适用: 扁平电磁执行器 / 微型继电器 / 传感器】", fontsize=11, fontweight="bold", pad=12, color="#0F172A")
    ax.set_xlim(-5.5, 5.5)
    ax.set_ylim(-5.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")

    r_out = patches.FancyBboxPatch((-3.5, -2.4), 7.0, 4.8, boxstyle="round,pad=0,rounding_size=0.8",
                                   facecolor=COLOR_COPPER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=2.2)
    r_in = patches.FancyBboxPatch((-2.3, -1.3), 4.6, 2.6, boxstyle="round,pad=0,rounding_size=0.4",
                                  facecolor=COLOR_INNER_FILL, edgecolor=COLOR_COPPER_STROKE, linewidth=1.8)
    ax.add_patch(r_out)
    ax.add_patch(r_in)

    # 内部纹理
    r_mid = patches.FancyBboxPatch((-2.9, -1.85), 5.8, 3.7, boxstyle="round,pad=0,rounding_size=0.6",
                                   fill=False, edgecolor="#D97706", linewidth=0.8, linestyle=":", alpha=0.7)
    ax.add_patch(r_mid)

    # 标注
    draw_dimension(ax, (-2.3, 0), (2.3, 0), "内长 L_in", text_offset=(0, 0.35))
    draw_dimension(ax, (0, -1.3), (0, 1.3), "内宽 W_in", text_offset=(0.6, 0))
    draw_dimension(ax, (-3.5, -2.4), (3.5, -2.4), "外长 L_out", offset=(0, -1.2))
    ax.annotate("内圆角 r_corner", xy=(2.0, 1.1), xytext=(3.2, 2.1),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=1.2),
                fontsize=9, color="#059669", fontweight="bold")


def generate_all():
    # 1. 生成 4 合 1 全景总览大图
    fig, axes = plt.subplots(2, 2, figsize=(14, 13), dpi=150)
    fig.patch.set_facecolor("#FFFFFF")
    
    draw_octagonal_shape(axes[0, 0])
    draw_racetrack_shape(axes[0, 1])
    draw_circular_shape(axes[1, 0])
    draw_rectangular_shape(axes[1, 1])

    fig.suptitle("ANSV Coil-Architect Pro | 四大多物理场电磁线圈拓扑形态全景", fontsize=15, fontweight="bold", y=0.98, color="#0F172A")
    plt.tight_layout()
    overview_path = out_dir / "coil_topologies_overview.png"
    plt.savefig(str(overview_path), bbox_inches="tight", dpi=150)
    plt.close()
    print(f"✅ 已生成全景拓扑大图: {overview_path}")

    # 2. 分别生成 4 张独立的清晰卡片图
    singles = [
        ("coil_type_octagonal.png", draw_octagonal_shape),
        ("coil_type_racetrack.png", draw_racetrack_shape),
        ("coil_type_circular.png", draw_circular_shape),
        ("coil_type_rectangular.png", draw_rectangular_shape),
    ]
    for fname, draw_func in singles:
        f, ax = plt.subplots(figsize=(6.5, 6.2), dpi=150)
        f.patch.set_facecolor("#FFFFFF")
        draw_func(ax)
        plt.tight_layout()
        p = out_dir / fname
        plt.savefig(str(p), bbox_inches="tight", dpi=150)
        plt.close()
        print(f"✅ 已生成独立拓扑示意图: {p}")


if __name__ == "__main__":
    generate_all()
