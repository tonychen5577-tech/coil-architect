import os
import sys
import math
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QLinearGradient,
    QPen, QBrush, QPixmap, QPolygonF
)
from PyQt6.QtWidgets import QApplication

def create_coil_preview(width=632, height=180, save_path=None):
    pix = QPixmap(width, height)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    w, h = width, height

    # 1. 精密工程视窗背景 (极净白蓝工控调性 + 细致工程方格)
    bg_grad = QLinearGradient(0, 0, 0, h)
    bg_grad.setColorAt(0.0, QColor("#F8FAFC"))
    bg_grad.setColorAt(1.0, QColor("#F1F5F9"))
    painter.fillRect(0, 0, w, h, bg_grad)

    # 绘制细网格 (18px 步长，点线)
    painter.setPen(QPen(QColor("#E2E8F0"), 1, Qt.PenStyle.DotLine))
    grid_step = 18
    for x in range(0, w, grid_step):
        painter.drawLine(x, 0, x, h)
    for y in range(0, h, grid_step):
        painter.drawLine(0, y, w, y)

    # 中心 CAD 坐标准星
    cx, cy = w / 2.0 + 8.0, h / 2.0 + 8.0
    painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DashDotLine))
    painter.drawLine(int(cx - 240), int(cy), int(cx + 240), int(cy))
    painter.drawLine(int(cx), int(cy - 68), int(cx), int(cy + 68))

    # 2. 3D 轴测透视参数
    yaw_rad = math.radians(-14)
    pitch_rad = math.radians(26)
    cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
    cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)

    def project_3d(x, y, z):
        xr = x * cos_y - z * sin_y
        zr = x * sin_y + z * cos_y
        yr = y * cos_p - zr * sin_p
        sx = cx + xr
        sy = cy - yr
        return QPointF(sx, sy)

    L_straight = 96.0   # 跑道直线段半长
    R_out = 44.0        # 外圆角半径
    R_in = 22.0         # 内圆角半径
    H_coil = 36.0       # 绕组高度
    y_base = -H_coil / 2.0
    y_top_coil = y_base + H_coil

    # 完整跑道闭合轮廓生成
    def get_full_racetrack(r_val, n_arc=36, n_str=24):
        pts = []
        # 1. 底部直线: (-L, r) -> (+L, r)
        for i in range(n_str):
            t = i / float(n_str)
            pts.append((-L_straight + 2.0 * L_straight * t, r_val))
        # 2. 右半圆: 顺时针从 (+L, r) 经 (+L+r, 0) 到 (+L, -r)
        for i in range(n_arc):
            ang = math.pi / 2.0 - math.pi * (i / float(n_arc))
            pts.append((L_straight + r_val * math.cos(ang), r_val * math.sin(ang)))
        # 3. 顶部直线: (+L, -r) -> (-L, -r)
        for i in range(n_str):
            t = i / float(n_str)
            pts.append((L_straight - 2.0 * L_straight * t, -r_val))
        # 4. 左半圆: 顺时针从 (-L, -r) 经 (-L-r, 0) 到 (-L, r)
        for i in range(n_arc + 1):
            ang = -math.pi / 2.0 - math.pi * (i / float(n_arc))
            pts.append((-L_straight + r_val * math.cos(ang), r_val * math.sin(ang)))
        return pts

    # 单独生成正面连续外侧壁轮廓 (从左侧视线切点 -> 底部直线 -> 右侧视线切点)
    def get_front_racetrack_wall(r_val, n_arc=30, n_str=30):
        pts = []
        # 左切点到拐点: 倾角 -yaw 补偿切点
        ang_left_start = -math.pi - math.radians(20)
        ang_left_end = -math.pi / 2.0
        for i in range(n_arc):
            ang = ang_left_start + (ang_left_end - ang_left_start) * (i / float(n_arc))
            pts.append((-L_straight + r_val * math.cos(ang), -r_val * math.sin(ang)))
        # 底部直线段
        for i in range(n_str):
            t = i / float(n_str)
            pts.append((-L_straight + 2.0 * L_straight * t, r_val))
        # 右侧拐点到右切点
        ang_right_start = math.pi / 2.0
        ang_right_end = math.radians(10)
        for i in range(n_arc + 1):
            ang = ang_right_start + (ang_right_end - ang_right_start) * (i / float(n_arc))
            pts.append((L_straight + r_val * math.cos(ang), r_val * math.sin(ang)))
        return pts

    pts_outer_full = get_full_racetrack(R_out, 36, 24)
    pts_inner_full = get_full_racetrack(R_in, 36, 24)
    pts_front_wall = get_front_racetrack_wall(R_out, 32, 32)

    # 3. 底部微弱投影阴影
    shadow_path = QPainterPath()
    pts_shadow = [project_3d(x, y_base - 2.5, z) for x, z in pts_outer_full]
    shadow_path.addPolygon(QPolygonF(pts_shadow))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(15, 23, 42, 30)))
    painter.drawPath(shadow_path)

    # 4. 电磁通量线 (磁力线后半环)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(2, 132, 199, 85), 1.2, Qt.PenStyle.DashLine))
    for flux_x in [-75, -40, -5, 30, 65, 100]:
        path_flux = QPainterPath()
        p_start = project_3d(flux_x, -H_coil * 0.4, 0)
        p_c1 = project_3d(flux_x * 1.3, H_coil * 1.5, -60)
        p_c2 = project_3d(flux_x * 1.6, -H_coil * 1.3, -70)
        p_end = project_3d(flux_x * 0.8, -H_coil * 0.7, -30)
        path_flux.moveTo(p_start)
        path_flux.cubicTo(p_c1, p_c2, p_end)
        painter.drawPath(path_flux)

    # 5. 立体内孔内壁 (深色阴影景深)
    inner_wall_path = QPainterPath()
    inner_pts_bottom = [project_3d(x, y_base, z) for x, z in pts_inner_full]
    inner_pts_top = [project_3d(x, y_top_coil, z) for x, z in pts_inner_full]
    inner_poly = QPolygonF(inner_pts_bottom + inner_pts_top[::-1])
    inner_wall_path.addPolygon(inner_poly)
    inner_grad = QLinearGradient(cx - 100, cy - 20, cx + 100, cy + 20)
    inner_grad.setColorAt(0.0, QColor("#451A03"))
    inner_grad.setColorAt(0.4, QColor("#78350F"))
    inner_grad.setColorAt(0.8, QColor("#2E1002"))
    inner_grad.setColorAt(1.0, QColor("#1C0A02"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(inner_grad))
    painter.drawPath(inner_wall_path)

    # 6. 外侧立面平滑连续铜质感曲面 (Smooth Front Winding Body)
    pts_bot_front = [project_3d(x, y_base, z) for x, z in pts_front_wall]
    pts_top_front = [project_3d(x, y_top_coil, z) for x, z in pts_front_wall]

    side_hull = QPolygonF(pts_bot_front + pts_top_front[::-1])
    side_path = QPainterPath()
    side_path.addPolygon(side_hull)

    grad_side = QLinearGradient(cx - 140, cy, cx + 140, cy)
    grad_side.setColorAt(0.0, QColor("#78350F"))
    grad_side.setColorAt(0.18, QColor("#B45309"))
    grad_side.setColorAt(0.45, QColor("#F59E0B"))
    grad_side.setColorAt(0.72, QColor("#D97706"))
    grad_side.setColorAt(0.9, QColor("#92400E"))
    grad_side.setColorAt(1.0, QColor("#5C2708"))

    painter.setPen(QPen(QColor("#78350F"), 1))
    painter.setBrush(QBrush(grad_side))
    painter.drawPath(side_path)

    # 密排线层细线 (Winding Layers)
    num_strands = 14
    strand_h = H_coil / num_strands
    for s_idx in range(1, num_strands):
        y_curr = y_base + s_idx * strand_h
        pts_strand = [project_3d(x, y_curr, z) for x, z in pts_front_wall]
        painter.setPen(QPen(QColor(254, 243, 199, 130), 0.9))
        painter.drawPolyline(QPolygonF(pts_strand))

    # 7. 顶部环形镜面高光 (Golden Copper Specular Top Face)
    path_top_outer = QPainterPath()
    path_top_outer.addPolygon(QPolygonF([project_3d(x, y_top_coil, z) for x, z in pts_outer_full]))

    path_top_inner = QPainterPath()
    path_top_inner.addPolygon(QPolygonF([project_3d(x, y_top_coil, z) for x, z in pts_inner_full]))

    coil_top_ring = path_top_outer.subtracted(path_top_inner)

    grad_top = QLinearGradient(cx - 150, cy - 35, cx + 150, cy + 20)
    grad_top.setColorAt(0.0, QColor("#92400E"))
    grad_top.setColorAt(0.2, QColor("#D97706"))
    grad_top.setColorAt(0.4, QColor("#F59E0B"))
    grad_top.setColorAt(0.55, QColor("#FEF08A")) # 镜面强高光
    grad_top.setColorAt(0.75, QColor("#D97706"))
    grad_top.setColorAt(1.0, QColor("#78350F"))

    painter.setPen(QPen(QColor("#78350F"), 1.2))
    painter.setBrush(QBrush(grad_top))
    painter.drawPath(coil_top_ring)

    # 顶部多层密排同心线纹 (Concentric Top Packing Rings)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 140), 0.8))
    for r_layer in range(1, 6):
        r_curr = R_in + (R_out - R_in) * (r_layer / 6.0)
        pts_layer_all = get_full_racetrack(r_curr, 28, 20)
        p_ring = QPolygonF([project_3d(x, y_top_coil, z) for x, z in pts_layer_all])
        painter.drawPolyline(p_ring)

    # 8. 引出引脚端子 (Lead Terminal Pins - 向左上方与左平伸，优雅避开任何文字)
    p_pin1_0 = project_3d(-L_straight - 10, y_base + 6, R_out * 0.45)
    p_pin1_1 = project_3d(-L_straight - 45, y_base + 10, R_out * 0.35)
    p_pin1_2 = project_3d(-L_straight - 80, y_base + 12, R_out * 0.25)

    p_pin2_0 = project_3d(-L_straight - 10, y_base + 1, R_out * 0.7)
    p_pin2_1 = project_3d(-L_straight - 40, y_base + 3, R_out * 0.6)
    p_pin2_2 = project_3d(-L_straight - 72, y_base + 5, R_out * 0.5)

    painter.setPen(QPen(QColor("#F59E0B"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(p_pin1_0, p_pin1_1)
    painter.drawLine(p_pin1_1, p_pin1_2)
    painter.drawLine(p_pin2_0, p_pin2_1)
    painter.drawLine(p_pin2_1, p_pin2_2)

    painter.setPen(QPen(QColor("#B45309"), 1.2))
    painter.setBrush(QBrush(QColor("#FEF08A")))
    painter.drawEllipse(p_pin1_2, 3.2, 3.2)
    painter.drawEllipse(p_pin2_2, 3.2, 3.2)

    # 9. 电磁通量线 (磁力线前半环 - 纯线条 + 亮蓝微光)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for flux_x in [-60, -25, 10, 45, 80]:
        path_flux_front = QPainterPath()
        p_start = project_3d(flux_x, H_coil * 0.5, 0)
        p_c1 = project_3d(flux_x * 1.25, H_coil * 1.9, 52)
        p_c2 = project_3d(flux_x * 1.5, -H_coil * 1.1, 68)
        p_end = project_3d(flux_x * 0.9, -H_coil * 0.6, 32)
        path_flux_front.moveTo(p_start)
        path_flux_front.cubicTo(p_c1, p_c2, p_end)

        # 发光外晕
        painter.setPen(QPen(QColor(56, 189, 248, 50), 3.0))
        painter.drawPath(path_flux_front)
        # 核心亮线
        painter.setPen(QPen(QColor("#0284C7"), 1.2))
        painter.drawPath(path_flux_front)

        # 磁通方向箭头颗粒
        p_dot = path_flux_front.pointAtPercent(0.55)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#38BDF8")))
        painter.drawEllipse(p_dot, 2.0, 2.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    # 10. 专业工业 HUD 视标与工程元数据
    font_hud = QFont("Consolas", 8, QFont.Weight.Bold)
    painter.setFont(font_hud)

    # 左上角
    painter.setPen(QColor("#0369A1"))
    painter.drawText(14, 20, "MODEL: 3D Axonometric Precision Voice Coil (HCP Winding)")
    painter.setPen(QColor("#64748B"))
    painter.drawText(14, 34, "PHYSICS: Coupled Electromagnetic B-Field & Joule Heating")

    # 右上角
    painter.setPen(QColor("#059669"))
    painter.drawText(w - 180, 20, "✔ ISO 129 COMPLIANT")
    painter.setPen(QColor("#64748B"))
    painter.drawText(w - 180, 34, "MESH: 48,200 HEXA ELEMENTS")

    # 左下角
    painter.setPen(QColor("#94A3B8"))
    painter.drawText(14, h - 12, "Z=0 DATUM [A]  |  ANSV DUAL-CORE SOLVER ENGINE  |  SCALE 1:1")

    # 右下角实时解算状态药丸
    pill_rect = QRectF(w - 145, h - 26, 132, 18)
    painter.setPen(QPen(QColor("#BAE6FD"), 1))
    painter.setBrush(QBrush(QColor("#F0F9FF")))
    painter.drawRoundedRect(pill_rect, 9, 9)
    painter.setPen(QColor("#0284C7"))
    font_pill = QFont("Consolas", 7, QFont.Weight.Bold)
    painter.setFont(font_pill)
    painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, "● SIMULATION READY")

    painter.end()

    if save_path:
        pix.save(save_path)
    return pix

if __name__ == "__main__":
    app = QApplication(sys.argv)
    out_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    out_file = os.path.join(out_dir, "verify_splash_coil_preview.png")
    create_coil_preview(632, 170, out_file)
    print(f"Rendered splash coil preview to: {out_file}")
