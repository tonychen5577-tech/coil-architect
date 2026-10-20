import os
import sys
import math
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QLinearGradient,
    QPen, QBrush, QPixmap, QPolygonF
)
from PyQt6.QtWidgets import QApplication

def draw_iso_arrow(painter: QPainter, tip_x: float, tip_y: float, dir_x: float, dir_y: float, length: float = 7.0, half_width: float = 2.4):
    norm = math.hypot(dir_x, dir_y)
    if norm == 0:
        return
    dx = dir_x / norm
    dy = dir_y / norm
    px = -dy
    py = dx
    bx = tip_x - dx * length
    by = tip_y - dy * length
    p1 = QPointF(tip_x, tip_y)
    p2 = QPointF(bx + px * half_width, by + py * half_width)
    p3 = QPointF(bx - px * half_width, by - py * half_width)
    path = QPainterPath()
    path.moveTo(p1)
    path.lineTo(p2)
    path.lineTo(p3)
    path.closeSubpath()
    painter.drawPath(path)

def render_section_canvas(width=680, height=280, save_path=None):
    pix = QPixmap(width, height)
    pix.fill(Qt.GlobalColor.white)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    w, h = width, height

    # 1. 标题与药丸按钮
    painter.setPen(QColor("#0F172A"))
    painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
    painter.drawText(14, 24, "跑道型 2D 截面剖视工程图 (ISO 129 标准制图与 DFM 卡控)")

    # 药丸切换
    pill_zx = QRectF(w - 225, 10, 100, 22)
    pill_zy = QRectF(w - 115, 10, 100, 22)
    painter.setPen(QPen(QColor("#0284C7"), 1.2))
    painter.setBrush(QBrush(QColor("#E0F2FE")))
    painter.drawRoundedRect(pill_zx, 11, 11)
    painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Bold))
    painter.setPen(QColor("#0284C7"))
    painter.drawText(pill_zx, Qt.AlignmentFlag.AlignCenter, "● Z-X 长向剖面")

    painter.setPen(QPen(QColor("#CBD5E1"), 1))
    painter.setBrush(QBrush(QColor("#F8FAFC")))
    painter.drawRoundedRect(pill_zy, 11, 11)
    painter.setPen(QColor("#64748B"))
    painter.drawText(pill_zy, Qt.AlignmentFlag.AlignCenter, "○ Z-Y 宽向剖面")

    # 参数定义
    in_dim = 0.920       # 内宽 w (IW)
    out_dim = 2.175      # 外宽 W (OW)
    f_thk = 0.660        # 成型高度 H (F)
    e_env = (out_dim - in_dim) / 2.0  # 单边壁厚 t = 0.6275 mm
    lim_z = 0.850        # 空间限高
    lim_dim = 3.000      # 空间限宽
    delta_z = lim_z - f_thk
    is_dfm_active = False

    phys_w = max(out_dim, lim_dim) * 1.35 + 0.6
    phys_h = max(f_thk, lim_z) * 1.35 + 0.4
    cx = w / 2.0

    bottom_card_h = 32.0
    rect_bottom_card = QRectF(6, h - bottom_card_h - 4, w - 12, bottom_card_h)

    badge_h = 18.0
    badge_y = rect_bottom_card.top() - badge_h - 6.0
    badge_w = min(w - 40, 440)
    rect_badge = QRectF(cx - badge_w / 2.0, badge_y, badge_w, badge_h)

    # 尺寸标注位置
    y_dim_out = badge_y - 14.0
    base_y = y_dim_out - 22.0

    view_w = w - 100
    view_h = max(30.0, base_y - 65.0)
    scale = min(view_w / max(0.1, phys_w), view_h / max(0.1, phys_h))

    # 2. Z=0 基准线
    w_base_px = max(out_dim, lim_dim) * scale * 1.4
    x_base_left = cx - w_base_px / 2.0
    x_base_right = cx + w_base_px / 2.0

    painter.setPen(QPen(QColor("#64748B"), 1.2))
    painter.drawLine(int(x_base_left), int(base_y), int(x_base_right), int(base_y))

    # 地线小斜线 (阴影剖面线)
    painter.setPen(QPen(QColor("#CBD5E1"), 1))
    hatch_step = 16
    for hx in range(int(x_base_left), int(x_base_right), hatch_step):
        painter.drawLine(hx, int(base_y), hx - 5, int(base_y + 5))

    # 3. 对称中心轴 (ISO 128 Dash-Dot Centerline)
    painter.setPen(QPen(QColor("#94A3B8"), 1, Qt.PenStyle.DashDotLine))
    y_top_axis = base_y - max(f_thk, lim_z) * scale - 28
    painter.drawLine(int(cx), int(base_y + 14), int(cx), int(y_top_axis))

    # ISO ℄ (Centerline Symbol)
    painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    painter.setPen(QColor("#64748B"))
    painter.drawText(int(cx + 4), int(y_top_axis + 10), "℄")

    # 4. DFM 空间包络虚线框
    w_lim_px = lim_dim * scale
    h_lim_px = lim_z * scale
    x_lim_left = cx - w_lim_px / 2.0
    x_lim_right = cx + w_lim_px / 2.0
    y_lim_top = base_y - h_lim_px
    rect_dfm_box = QRectF(x_lim_left, y_lim_top, w_lim_px, h_lim_px)
    painter.setPen(QPen(QColor("#CBD5E1"), 1.2, Qt.PenStyle.DashLine))
    painter.setBrush(QBrush(QColor(241, 245, 249, 20)))
    painter.drawRect(rect_dfm_box)

    # 顶部限高提示
    rect_lim_z_tag = QRectF(14, 38, 280, 16)
    painter.setPen(QPen(QColor("#0284C7"), 1))
    painter.setBrush(QBrush(QColor("#F0F9FF")))
    painter.drawRoundedRect(rect_lim_z_tag, 3, 3)
    painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
    painter.setPen(QColor("#0284C7"))
    painter.drawText(rect_lim_z_tag, Qt.AlignmentFlag.AlignCenter, f"▲ 参考限高 Max_Z: {lim_z:.2f} mm (余量 ΔZ: {delta_z:+.3f} mm)")

    # 5. 线圈截面导电实体
    w_inner_px = in_dim * scale
    w_coil_px = e_env * scale
    h_coil_px = f_thk * scale

    x_l_coil = cx - (w_inner_px / 2.0) - w_coil_px
    x_r_coil = cx + (w_inner_px / 2.0)
    y_coil_top = base_y - h_coil_px

    rect_l_coil = QRectF(x_l_coil, y_coil_top, w_coil_px, h_coil_px)
    rect_r_coil = QRectF(x_r_coil, y_coil_top, w_coil_px, h_coil_px)

    grad_coil = QLinearGradient(0, y_coil_top, 0, base_y)
    grad_coil.setColorAt(0.0, QColor("#FED7AA"))
    grad_coil.setColorAt(0.5, QColor("#FB923C"))
    grad_coil.setColorAt(1.0, QColor("#EA580C"))

    for c_rect, c_dir in [(rect_l_coil, "out"), (rect_r_coil, "in")]:
        painter.setPen(QPen(QColor("#C2410C"), 1.4))
        painter.setBrush(QBrush(grad_coil))
        painter.drawRect(c_rect)

        # 漆包线同数密排层理
        layers_count = 12
        painter.setPen(QPen(QColor(255, 255, 255, 120), 0.8))
        for l_idx in range(1, layers_count):
            y_layer = y_coil_top + (h_coil_px / layers_count) * l_idx
            painter.drawLine(int(c_rect.left() + 1), int(y_layer), int(c_rect.right() - 1), int(y_layer))

        # 电流方向标记 (⊙ / ⊗)
        c_x = c_rect.center().x()
        c_y = c_rect.center().y()
        painter.setPen(QPen(QColor("#1E293B"), 1.2))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(c_x, c_y), 5, 5)
        painter.setPen(QPen(QColor("#0F172A"), 1.5))
        if c_dir == "out":
            painter.setBrush(QBrush(QColor("#0F172A")))
            painter.drawEllipse(QPointF(c_x, c_y), 1.8, 1.8)
        else:
            painter.drawLine(int(c_x - 2.5), int(c_y - 2.5), int(c_x + 2.5), int(c_y + 2.5))
            painter.drawLine(int(c_x - 2.5), int(c_y + 2.5), int(c_x + 2.5), int(c_y - 2.5))

    # ISO 5459 基准特征符号 [ A ] (置于左外侧安全区域，不与外宽尺寸界线冲突)
    x_datum = max(x_base_left + 16, x_l_coil - 32)
    tri_path = QPainterPath()
    tri_path.moveTo(x_datum, base_y)
    tri_path.lineTo(x_datum - 5, base_y + 8)
    tri_path.lineTo(x_datum + 5, base_y + 8)
    tri_path.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#1E293B")))
    painter.drawPath(tri_path)

    painter.setPen(QPen(QColor("#1E293B"), 1.2))
    painter.drawLine(int(x_datum), int(base_y + 8), int(x_datum), int(base_y + 16))
    rect_datum_box = QRectF(x_datum - 7, base_y + 16, 14, 14)
    painter.setBrush(QBrush(QColor("#FFFFFF")))
    painter.drawRect(rect_datum_box)
    painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
    painter.drawText(rect_datum_box, Qt.AlignmentFlag.AlignCenter, "A")

    painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
    painter.setPen(QColor("#64748B"))
    painter.drawText(int(x_datum - 32), int(base_y + 38), "DATUM [A]")

    # =========================================================================
    # 6. 【核心】严格遵循 ISO 129 标准工程尺寸标注 (Dimensioning & Tolerancing)
    # =========================================================================
    pen_iso_dim = QPen(QColor("#0369A1"), 1.2)
    pen_iso_ext = QPen(QColor("#64748B"), 1.0)
    brush_iso_arrow = QBrush(QColor("#0369A1"))

    # 6.1 内宽 (Inner Width): w = 0.920 mm (或 IW = 0.920 mm)
    y_dim_in = base_y - h_coil_px / 2.0
    x_in_l = rect_l_coil.right()
    x_in_r = rect_r_coil.left()

    # 尺寸线
    painter.setPen(pen_iso_dim)
    painter.drawLine(int(x_in_l), int(y_dim_in), int(x_in_r), int(y_dim_in))

    # 闭合实心箭头 (指向左右内壁)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(brush_iso_arrow)
    draw_iso_arrow(painter, x_in_l, y_dim_in, -1.0, 0.0, 7.0, 2.5)
    draw_iso_arrow(painter, x_in_r, y_dim_in, 1.0, 0.0, 7.0, 2.5)

    # 尺寸文字
    text_in = f"w (IW) = {in_dim:.2f} mm"
    font_dim = QFont("Consolas", 8, QFont.Weight.Bold)
    painter.setFont(font_dim)
    metrics_in = painter.fontMetrics()
    tw_in = metrics_in.horizontalAdvance(text_in)
    th_in = metrics_in.height()

    rect_text_in_bg = QRectF(cx - tw_in / 2.0 - 4, y_dim_in - th_in - 2, tw_in + 8, th_in)
    painter.fillRect(rect_text_in_bg, QColor(255, 255, 255, 230))
    painter.setPen(QColor("#0369A1"))
    painter.drawText(rect_text_in_bg, Qt.AlignmentFlag.AlignCenter, text_in)

    # 6.2 外宽 (Outer Width): W = 2.175 mm (或 OW = 2.175 mm)
    x_out_l = rect_l_coil.left()
    x_out_r = rect_r_coil.right()

    # 尺寸界线 (Extension lines)
    painter.setPen(pen_iso_ext)
    painter.drawLine(int(x_out_l), int(base_y + 1), int(x_out_l), int(y_dim_out + 5))
    painter.drawLine(int(x_out_r), int(base_y + 1), int(x_out_r), int(y_dim_out + 5))

    # 水平尺寸线
    painter.setPen(pen_iso_dim)
    painter.drawLine(int(x_out_l), int(y_dim_out), int(x_out_r), int(y_dim_out))

    # 闭合实心箭头
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(brush_iso_arrow)
    draw_iso_arrow(painter, x_out_l, y_dim_out, -1.0, 0.0, 7.0, 2.5)
    draw_iso_arrow(painter, x_out_r, y_dim_out, 1.0, 0.0, 7.0, 2.5)

    # 外宽文字
    text_out = f"W (OW) = {out_dim:.3f} mm"
    tw_out = metrics_in.horizontalAdvance(text_out)
    th_out = th_in
    rect_text_out_bg = QRectF(cx - tw_out / 2.0 - 4, y_dim_out - th_out - 1, tw_out + 8, th_out)
    painter.fillRect(rect_text_out_bg, QColor(255, 255, 255, 235))
    painter.setPen(QColor("#0F172A"))
    painter.drawText(rect_text_out_bg, Qt.AlignmentFlag.AlignCenter, text_out)

    # 6.3 成型高度 (Forming Height): H = 0.660 mm (或 F = 0.660 mm)
    x_dim_h = rect_r_coil.right() + 24.0
    painter.setPen(pen_iso_ext)
    painter.drawLine(int(rect_r_coil.right() + 2), int(y_coil_top), int(x_dim_h + 5), int(y_coil_top))
    painter.drawLine(int(rect_r_coil.right() + 2), int(base_y), int(x_dim_h + 5), int(base_y))

    # 竖直尺寸线
    painter.setPen(QPen(QColor("#C2410C"), 1.2))
    painter.drawLine(int(x_dim_h), int(y_coil_top), int(x_dim_h), int(base_y))

    # 上下实心箭头
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#C2410C")))
    draw_iso_arrow(painter, x_dim_h, y_coil_top, 0.0, -1.0, 7.0, 2.5)
    draw_iso_arrow(painter, x_dim_h, base_y, 0.0, 1.0, 7.0, 2.5)

    # 高度文字置于尺寸线右侧
    text_h = f"H (F) = {f_thk:.3f} mm"
    painter.setFont(font_dim)
    painter.setPen(QColor("#C2410C"))
    painter.drawText(int(x_dim_h + 6), int((y_coil_top + base_y) / 2.0 + 4), text_h)

    # 6.4 单边壁厚 (Wall Thickness): t = 0.628 mm (或 E = 0.628 mm)
    y_dim_t = y_coil_top - 12.0
    painter.setPen(pen_iso_ext)
    painter.drawLine(int(rect_l_coil.left()), int(y_coil_top - 1), int(rect_l_coil.left()), int(y_dim_t - 3))
    painter.drawLine(int(rect_l_coil.right()), int(y_coil_top - 1), int(rect_l_coil.right()), int(y_dim_t - 3))

    painter.setPen(QPen(QColor("#C2410C"), 1.0))
    painter.drawLine(int(rect_l_coil.left()), int(y_dim_t), int(rect_l_coil.right()), int(y_dim_t))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#C2410C")))
    draw_iso_arrow(painter, rect_l_coil.left(), y_dim_t, -1.0, 0.0, 5.0, 2.0)
    draw_iso_arrow(painter, rect_l_coil.right(), y_dim_t, 1.0, 0.0, 5.0, 2.0)

    text_t = f"t (E) = {e_env:.3f}"
    painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
    painter.setPen(QColor("#C2410C"))
    tw_t = painter.fontMetrics().horizontalAdvance(text_t)
    painter.drawText(QRectF(rect_l_coil.center().x() - tw_t / 2.0, y_dim_t - 11, tw_t, 11), Qt.AlignmentFlag.AlignCenter, text_t)

    # 7. 底部状态指示胶囊
    badge_text = "ℹ DFM 模具卡限已关闭 (自由仿真设计模式: 专注于电阻与匝数寻优)"
    painter.setPen(QPen(QColor("#BAE6FD"), 1))
    painter.setBrush(QBrush(QColor("#F0F9FF")))
    painter.drawRoundedRect(rect_badge, 4, 4)
    painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Bold))
    painter.setPen(QColor("#0284C7"))
    painter.drawText(rect_badge, Qt.AlignmentFlag.AlignCenter, badge_text)

    # 底部说明卡
    painter.setPen(QPen(QColor("#E2E8F0"), 1))
    painter.setBrush(QBrush(QColor("#F8FAFC")))
    painter.drawRoundedRect(rect_bottom_card, 6, 6)
    painter.setFont(QFont("Microsoft YaHei", 7))
    painter.setPen(QColor("#475569"))
    painter.drawText(rect_bottom_card, Qt.AlignmentFlag.AlignCenter,
                     f"【自由设计】成型高度 H: {f_thk:.3f} mm | 单边壁厚 t: {e_env:.3f} mm | 内腔基准: {in_dim:.2f} mm | 实际外廓: {out_dim:.3f} mm")

    painter.end()
    if save_path:
        pix.save(save_path)
    return pix

if __name__ == "__main__":
    app = QApplication(sys.argv)
    out_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    out_file = os.path.join(out_dir, "verify_iso_section_canvas.png")
    render_section_canvas(680, 280, out_file)
    print(f"Rendered ISO section canvas to: {out_file}")
