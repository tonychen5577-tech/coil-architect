"""
Coil-Architect Pro - High-Performance QPainter Vector Canvas
多核物理矢量工程画布：
1. 左视口：微观排线截面图 (自粘脱胎空心结构，支持 Z-X 长向截面、Z-Y 宽向截面与单侧放大 3 档交互切换，严密卡控 X/Y/Z 空间边界)
2. 右视口：选项卡三重工程孪生视图：
   - 选项卡 1: 2D 跑道外廓 (X-Y) (2D Racetrack Top View，含 Max_X × Max_Y 装配包络框与长宽双向余量)
   - 选项卡 2: Z 剖面与磁路 (Gap) (真实 VCM 径向侧置磁钢与轴向作动剖面，顶盖限高 Max_Z 基准，彻底消除磁铁错误碰撞误解)
   - 选项卡 3: 3D 空间斜视 (Y-Space) (3D Isometric Space Envelope，重点高亮呈现 Y 空间配合余量与三维立体空间笼)
"""

import math
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, 
    QLinearGradient, QPainterPath, QPolygonF
)
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QTabWidget
from ...core.models import CoilInputs, CoilOutputs, WindingMode, CoilType, WireShape, WindingDirection
from src.core.i18n import i18n, t


def draw_iso_arrow(painter: QPainter, tip_x: float, tip_y: float, dir_x: float, dir_y: float, length: float = 7.0, half_width: float = 2.4):
    """绘制符合 ISO 129 标准的实心闭合工程尺寸箭头 (Closed & Filled Arrowhead)"""
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


def generate_octagonal_polygon_points(id1: float, id2: float, l1: float, l2: float, r1: float, num_arc_pts: int = 8):
    """
    生成 8 折对称倒角八边形的封闭轮廓采样点及单位法向量 [((x, y), (nx, ny)), ...]
    严格基于图4闭合几何方程 (4平边L1 + 4斜边L2 + 8圆角R1)
    """
    sqrt2 = math.sqrt(2.0)
    x0 = max(0.1, id1 / 2.0)
    y0 = max(0.02, l1 / 2.0 if l1 > 0 else (sqrt2 * id2 - id1 - 2.0 * (sqrt2 - 1.0) * r1) / 2.0)
    r = max(0.01, min(r1, x0 * 0.45))

    xc1 = x0 - r
    yc1 = y0
    xc2 = y0
    yc2 = x0 - r

    pts = []

    # 1. 右竖直平边: (x0, -y0) -> (x0, y0)
    pts.append(((x0, -y0), (1.0, 0.0)))
    pts.append(((x0, y0), (1.0, 0.0)))

    # 2. 第一圆角 (0 -> pi/4)
    for k in range(1, num_arc_pts + 1):
        ang = (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((xc1 + r * ca, yc1 + r * sa), (ca, sa)))

    # 3. 第二圆角 (pi/4 -> pi/2)
    for k in range(1, num_arc_pts + 1):
        ang = math.pi / 4.0 + (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((xc2 + r * ca, yc2 + r * sa), (ca, sa)))

    # 4. 上水平平边: (y0, x0) -> (-y0, x0)
    pts.append(((-y0, x0), (0.0, 1.0)))

    # 5. 第三圆角 (pi/2 -> 3*pi/4)
    for k in range(1, num_arc_pts + 1):
        ang = math.pi / 2.0 + (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((-xc2 + r * ca, yc2 + r * sa), (ca, sa)))

    # 6. 第四圆角 (3*pi/4 -> pi)
    for k in range(1, num_arc_pts + 1):
        ang = 3.0 * math.pi / 4.0 + (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((-xc1 + r * ca, yc1 + r * sa), (ca, sa)))

    # 7. 左竖直平边: (-x0, y0) -> (-x0, -y0)
    pts.append(((-x0, -y0), (-1.0, 0.0)))

    # 8. 第五圆角 (pi -> 5*pi/4)
    for k in range(1, num_arc_pts + 1):
        ang = math.pi + (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((-xc1 + r * ca, -yc1 + r * sa), (ca, sa)))

    # 9. 第六圆角 (5*pi/4 -> 3*pi/2)
    for k in range(1, num_arc_pts + 1):
        ang = 5.0 * math.pi / 4.0 + (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((-xc2 + r * ca, -yc2 + r * sa), (ca, sa)))

    # 10. 下水平平边: (-y0, -x0) -> (y0, -x0)
    pts.append(((y0, -x0), (0.0, -1.0)))

    # 11. 第七圆角 (3*pi/2 -> 7*pi/4)
    for k in range(1, num_arc_pts + 1):
        ang = 3.0 * math.pi / 2.0 + (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((xc2 + r * ca, -yc2 + r * sa), (ca, sa)))

    # 12. 第八圆角 (7*pi/4 -> 2*pi)
    for k in range(1, num_arc_pts + 1):
        ang = 7.0 * math.pi / 4.0 + (math.pi / 4.0) * (k / num_arc_pts)
        ca = math.cos(ang)
        sa = math.sin(ang)
        pts.append(((xc1 + r * ca, -yc1 + r * sa), (ca, sa)))

    return pts


class MicroPackingCanvas(QWidget):
    """
    微观排线截面矢量画布 (自粘脱胎空心线圈高精度工程渲染)
    支持 3 种方向视图无缝切换：
    1. 'zx': Z-X 长向剖面 (沿长向剖切，严格卡控 X 空间边界 Max_X 与 Z 空间限高 Max_Z)
    2. 'zy': Z-Y 宽向剖面 (沿宽向剖切，严格卡控 Y 空间边界 Max_Y 与 Z 空间限高 Max_Z)
    3. 'single': 单侧微观放大详图 (高倍呈现漆膜厚度、铜线密排与单边物理壁厚 E)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs = CoilInputs()
        self.outputs = CoilOutputs()
        self.view_mode = "zx"  # "zx": Z-X长向剖面; "zy": Z-Y宽向剖面; "single": 单侧放大
        self.setMinimumSize(320, 220)
        self.setMouseTracking(True)

    def updateData(self, inputs: CoilInputs, outputs: CoilOutputs):
        self.inputs = inputs
        self.outputs = outputs
        self.update()

    def mousePressEvent(self, event):
        w = self.width()
        pill_w = 210
        pill_rect = QRectF(w - pill_w - 14, 8, pill_w, 24)
        if pill_rect.contains(event.pos().x(), event.pos().y()):
            rel_x = event.pos().x() - (w - pill_w - 14)
            slot_w = pill_w / 3.0
            if rel_x < slot_w:
                self.view_mode = "zx"
            elif rel_x < slot_w * 2:
                self.view_mode = "zy"
            else:
                self.view_mode = "single"
            self.update()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景与圆角边框
        painter.fillRect(0, 0, w, h, QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        # 1. 简洁标题与右上角 3 档药丸按钮
        painter.setPen(QColor("#0284C7"))
        font_title = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_title)

        is_en = i18n.is_english()
        if self.view_mode == "zx":
            view_title = "Z-X Long Section (X-Axis Clearance)" if is_en else "Z-X 长向剖面 (X向装配公差)"
        elif self.view_mode == "zy":
            view_title = "Z-Y Width Section (Y-Axis Clearance)" if is_en else "Z-Y 宽向剖面 (Y向装配公差)"
        else:
            view_title = "Single-Side Micro Detail Zoom" if is_en else "单侧微观高倍详图"

        painter.drawText(14, 24, view_title)

        # 3档切换药丸
        pill_w = 210
        pill_rect = QRectF(w - pill_w - 14, 8, pill_w, 24)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.setBrush(QBrush(QColor("#F8FAFC")))
        painter.drawRoundedRect(pill_rect, 12, 12)

        font_pill = QFont("Microsoft YaHei", 7, QFont.Weight.Bold)
        painter.setFont(font_pill)

        slot_w = pill_w / 3.0
        if is_en:
            tabs = [("zx", "Z-X Long", 0), ("zy", "Z-Y Width", 1), ("single", "Detail Zoom", 2)]
        else:
            tabs = [("zx", "Z-X 长向", 0), ("zy", "Z-Y 宽向", 1), ("single", "单侧放大", 2)]
        for mode_key, text, idx in tabs:
            slot_rect = QRectF(w - pill_w - 14 + idx * slot_w, 8, slot_w, 24)
            if self.view_mode == mode_key:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor("#0284C7")))
                painter.drawRoundedRect(slot_rect, 12, 12)
                painter.setPen(QColor("#FFFFFF"))
            else:
                painter.setPen(QColor("#64748B"))
            painter.drawText(slot_rect, Qt.AlignmentFlag.AlignCenter, text)

        layers = self.inputs.radial_layers
        turns = self.inputs.axial_turns
        if layers <= 0 or turns <= 0:
            return

        b_act = max(0.01, self.outputs.b_actual if self.outputs.b_actual > 0 else self.inputs.max_od)
        d_act = max(0.005, self.outputs.d_actual if self.outputs.d_actual > 0 else self.inputs.bare_dia)
        phys_w = max(0.1, self.outputs.e_env)
        phys_h = max(0.1, self.outputs.thickness_h)
        hcp_dx = b_act * (math.sqrt(3.0) / 2.0)

        # -------------------------------------------------------------
        # 模式 A (Z-X 长向剖面) 或 模式 B (Z-Y 宽向剖面)
        # -------------------------------------------------------------
        if self.view_mode in ("zx", "zy"):
            is_zx = (self.view_mode == "zx")
            c_type = self.inputs.coil_type

            if is_zx:
                # X 向参数: 内长 IL / 对边 ID1, 外长 OL / OD1, 限制 Max_X
                if c_type == CoilType.OCTAGONAL:
                    span_inner = max(0.2, self.inputs.oct_id1)
                    span_outer = self.outputs.oct_od1 if self.outputs.oct_od1 > 0 else span_inner + 2.0 * phys_w
                    lim_span = self.inputs.max_x_len_limit
                    axis_name = "X"
                    span_name = "Flat" if is_en else "对边跨"
                    outer_label = (f"Outer OD1: {span_outer:.3f} mm" if is_en else f"外跨 OD1: {span_outer:.3f} mm")
                    inner_label = (f"Inner ID1: {span_inner:.2f}" if is_en else f"内跨 ID1: {span_inner:.2f}")
                elif c_type == CoilType.ARBITRARY_PERIMETER:
                    span_outer = max(1.0, self.outputs.outer_len)
                    span_inner = max(0.3, span_outer - 2.0 * phys_w)
                    lim_span = self.inputs.max_x_len_limit
                    axis_name = "X"
                    span_name = "Len" if is_en else "长"
                    outer_label = (f"Outer OL: {span_outer:.3f} mm" if is_en else f"外长 OL: {span_outer:.3f} mm")
                    inner_label = (f"Ref IL: {span_inner:.2f}" if is_en else f"参考内长: {span_inner:.2f}")
                else:
                    span_inner = self.inputs.inner_len
                    span_outer = self.outputs.outer_len if self.outputs.outer_len > 0 else span_inner + 2.0 * phys_w
                    lim_span = self.inputs.max_x_len_limit
                    axis_name = "X"
                    span_name = "Len" if is_en else "长"
                    outer_label = (f"Outer OL: {span_outer:.3f} mm" if is_en else f"外长 OL: {span_outer:.3f} mm")
                    inner_label = (f"Inner IL: {span_inner:.2f}" if is_en else f"内长 IL: {span_inner:.2f}")
            else:
                # Y 向参数: 内宽 IW / 对角 ID2, 外宽 OW / OD2, 限制 Max_Y
                if c_type == CoilType.OCTAGONAL:
                    span_inner = max(0.2, self.inputs.oct_id2)
                    span_outer = self.outputs.oct_od2 if self.outputs.oct_od2 > 0 else span_inner + 2.0 * phys_w
                    lim_span = self.inputs.max_y_wid_limit
                    axis_name = "Y"
                    span_name = "Diag" if is_en else "对角跨"
                    outer_label = (f"Diag OD2: {span_outer:.3f} mm" if is_en else f"对角 OD2: {span_outer:.3f} mm")
                    inner_label = (f"Diag ID2: {span_inner:.2f}" if is_en else f"对角 ID2: {span_inner:.2f}")
                elif c_type == CoilType.ARBITRARY_PERIMETER:
                    span_outer = max(1.0, self.outputs.outer_wid)
                    span_inner = max(0.3, span_outer - 2.0 * phys_w)
                    lim_span = self.inputs.max_y_wid_limit
                    axis_name = "Y"
                    span_name = "Wid" if is_en else "宽"
                    outer_label = (f"Outer OW: {span_outer:.3f} mm" if is_en else f"外宽 OW: {span_outer:.3f} mm")
                    inner_label = (f"Ref IW: {span_inner:.2f}" if is_en else f"参考内宽: {span_inner:.2f}")
                elif c_type == CoilType.CIRCULAR:
                    span_inner = max(0.3, self.inputs.inner_len)
                    span_outer = max(span_inner + 2.0 * phys_w, self.outputs.outer_len)
                    lim_span = self.inputs.max_x_len_limit
                    axis_name = "Y"
                    span_name = "Dia" if is_en else "径"
                    outer_label = (f"Outer OD: {span_outer:.3f} mm" if is_en else f"外径 OD: {span_outer:.3f} mm")
                    inner_label = (f"Inner ID: {span_inner:.2f}" if is_en else f"内径 ID: {span_inner:.2f}")
                else:
                    span_inner = max(0.3, self.inputs.inner_wid)
                    span_outer = max(span_inner + 2.0 * phys_w, self.outputs.outer_wid)
                    lim_span = self.inputs.max_y_wid_limit
                    axis_name = "Y"
                    span_name = "Wid" if is_en else "宽"
                    outer_label = (f"Outer OW: {span_outer:.3f} mm" if is_en else f"外宽 OW: {span_outer:.3f} mm")
                    inner_label = (f"Inner IW: {span_inner:.2f}" if is_en else f"内宽 IW: {span_inner:.2f}")

            lim_z = self.inputs.max_z_h_limit

            margin_left = 34
            margin_right = 54
            margin_bottom = 44
            margin_top = 48

            view_w = w - margin_left - margin_right
            view_h = h - margin_top - margin_bottom

            scale_x = view_w / (max(span_outer, lim_span) * 1.18)
            scale_z = view_h / (max(phys_h, lim_z) * 1.45)
            scale = min(scale_x, scale_z)

            cx = (w - margin_right + margin_left) / 2.0
            cy = (margin_top + h - margin_bottom) / 2.0 + 8
            origin_y = cy + (phys_h * scale) / 2.0

            w_coil_px = phys_w * scale
            h_coil_px = phys_h * scale
            w_inner_px = span_inner * scale
            w_outer_px = span_outer * scale

            x_left_outer = cx - w_outer_px / 2.0
            x_left_inner = cx - w_inner_px / 2.0
            x_right_inner = cx + w_inner_px / 2.0
            x_right_outer = cx + w_outer_px / 2.0

            # 1. 绘制 Z=0 基准装配基面线 (无外部塑料骨架挡墙)
            datum_extend = 24
            painter.setPen(QPen(QColor("#94A3B8"), 1.2, Qt.PenStyle.SolidLine))
            painter.drawLine(int(x_left_outer - datum_extend), int(origin_y), int(x_right_outer + datum_extend), int(origin_y))

            painter.setPen(QColor("#64748B"))
            font_datum = QFont("Segoe UI", 7, QFont.Weight.Bold)
            painter.setFont(font_datum)
            painter.drawText(int(x_left_outer - datum_extend - 64), int(origin_y + 3), "▼ Z=0 Datum" if is_en else "▼ Z=0 基准")

            # 2. 中孔轴心点划线 (空心内腔)
            painter.setPen(QPen(QColor("#94A3B8"), 1, Qt.PenStyle.DashDotLine))
            painter.drawLine(int(cx), int(origin_y - h_coil_px - 22), int(cx), int(origin_y + 16))

            # 3. 绘制 Max_Z 空间限高线 (水平虚线)
            is_dfm_active = getattr(self.inputs, "dfm_enabled", False)
            y_lim_z = origin_y - lim_z * scale
            z_safe = (phys_h <= lim_z + 1e-4) if is_dfm_active else True
            pen_lim_z = QPen(
                QColor("#CBD5E1") if not is_dfm_active else (QColor("#10B981") if z_safe else QColor("#EF4444")),
                1.2, 
                Qt.PenStyle.DashLine
            )
            painter.setPen(pen_lim_z)
            painter.drawLine(int(x_left_outer - datum_extend), int(y_lim_z), int(x_right_outer + datum_extend), int(y_lim_z))

            # 空心内腔中心标识文字 (在网格线之上绘制，带白色保护底色胶囊，防穿透遮挡)
            font_core = QFont("Microsoft YaHei", 7, QFont.Weight.Bold)
            painter.setFont(font_core)
            painter.setPen(QColor("#64748B"))
            y_core_text = min(origin_y - h_coil_px / 2.0 - 8, y_lim_z - 18)
            painter.fillRect(QRectF(cx - 38, y_core_text, 76, 16), QColor(255, 255, 255, 240))
            painter.drawText(QRectF(cx - 56, y_core_text, 112, 16), Qt.AlignmentFlag.AlignCenter, "Air-Core Winding" if is_en else "自粘脱胎空心")

            # 4. 绘制横向空间上限边界线 (Max_X 或 Max_Y 垂直虚线，卡控边界)
            w_lim_span_px = lim_span * scale
            x_lim_left = cx - w_lim_span_px / 2.0
            x_lim_right = cx + w_lim_span_px / 2.0
            span_safe = (span_outer <= lim_span + 1e-4) if is_dfm_active else True

            pen_lim_span = QPen(
                QColor("#CBD5E1") if not is_dfm_active else (QColor("#10B981") if span_safe else QColor("#EF4444")),
                1.2, 
                Qt.PenStyle.DashDotLine
            )
            painter.setPen(pen_lim_span)
            painter.drawLine(int(x_lim_left), int(origin_y + 14), int(x_lim_left), int(y_lim_z - 6))
            painter.drawLine(int(x_lim_right), int(origin_y + 14), int(x_lim_right), int(y_lim_z - 6))

            # 边界线指示文字 (水平与垂直坐标彻底错开，两端锚定，杜绝内孔收缩重叠遮挡)
            font_lim = QFont("Consolas", 7, QFont.Weight.Bold)
            painter.setFont(font_lim)

            delta_span = lim_span - span_outer
            color_span = QColor("#0284C7") if not is_dfm_active else (QColor("#059669") if span_safe else QColor("#DC2626"))
            painter.setPen(color_span)
            if is_dfm_active:
                t_span = (f"◀ {axis_name}-Limit Max_{axis_name}: {lim_span:.2f} (Margin: {delta_span:+.3f}) ▶" if is_en else f"◀ {axis_name}向边界 Max_{axis_name}: {lim_span:.2f} (余量: {delta_span:+.3f}) ▶")
            else:
                t_span = (f"◀ Ref {axis_name}-Limit: {lim_span:.2f} (Margin: {delta_span:+.3f}) ▶" if is_en else f"◀ 参考边界 {axis_name}: {lim_span:.2f} (余量: {delta_span:+.3f}) ▶")
            painter.drawText(
                QRectF(10, y_lim_z - 16, 280, 14), 
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                t_span
            )

            delta_z = lim_z - phys_h
            color_z = QColor("#0284C7") if not is_dfm_active else (QColor("#059669") if z_safe else QColor("#DC2626"))
            painter.setPen(color_z)
            if is_dfm_active:
                t_z = (f"Max Z Limit: {lim_z:.2f} mm (ΔZ: {delta_z:+.3f})" if is_en else f"Max Z 限高: {lim_z:.2f} mm (余量 ΔZ: {delta_z:+.3f})")
            else:
                t_z = (f"Ref Z Limit: {lim_z:.2f} mm (ΔZ: {delta_z:+.3f})" if is_en else f"参考限高 Z: {lim_z:.2f} mm (余量 ΔZ: {delta_z:+.3f})")
            painter.drawText(
                QRectF(w - 230, y_lim_z - 16, 218, 14), 
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 
                t_z
            )

            # 5. 渲染双侧微观漆包线 (支持圆线与方线/扁线真实形态与倒角排布)
            is_flat = (getattr(self.inputs, "wire_shape", WireShape.ROUND) in (WireShape.SQUARE, WireShape.RECTANGULAR))
            pen_ins = QPen(QColor("#D97706"), 0.8)
            brush_ins = QBrush(QColor(254, 215, 170, 220))
            brush_cu = QBrush(QColor("#C2410C"))

            full_layers = int(math.floor(layers))
            has_half = (layers - full_layers) >= 0.25
            ceil_layers = int(math.ceil(layers))

            if is_flat:
                # 方线与扁线截面尺寸及平立绕排布步距
                raw_w = max(0.02, float(self.inputs.flat_w))
                raw_h = raw_w if self.inputs.wire_shape == WireShape.SQUARE else max(0.02, float(self.inputs.flat_h))
                fw = max(raw_w, raw_h)
                fh = min(raw_w, raw_h)
                t_ins = max(0.001, (self.outputs.b_actual - self.outputs.d_actual) / 2.0) if (hasattr(self.outputs, "b_actual") and self.outputs.b_actual > self.outputs.d_actual) else 0.005
                fw_out = fw + 2.0 * t_ins
                fh_out = fh + 2.0 * t_ins
                fr = (fh / 4.0) if (self.inputs.flat_r_auto or self.inputs.flat_r <= 0) else min(float(self.inputs.flat_r), fh / 2.0)
                r_out = fr + t_ins
                eta = max(0.7, min(1.0, float(getattr(self.inputs, "tension_factor", 1.0))))

                if getattr(self.inputs, "flat_winding_dir", WindingDirection.FLATWISE) == WindingDirection.FLATWISE:
                    # 平绕: 宽面沿轴向，薄面沿径向
                    w_step_mm = fh_out * eta
                    h_step_mm = fw_out * eta
                    w_bare_mm = fh * eta
                    h_bare_mm = fw * eta
                else:
                    # 立绕: 宽面沿径向，薄面沿轴向
                    w_step_mm = fw_out * eta
                    h_step_mm = fh_out * eta
                    w_bare_mm = fw * eta
                    h_bare_mm = fh * eta

                delta_nest_mm = 0.0
                if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and r_out > (h_step_mm / 4.0):
                    term = max(0.0, (2.0 * r_out) ** 2 - (2.0 * r_out - h_step_mm / 2.0) ** 2)
                    delta_nest_mm = 2.0 * r_out - math.sqrt(term)
                rad_pitch_mm = w_step_mm - delta_nest_mm

                w_wire_px = max(1.5, w_step_mm * scale)
                h_wire_px = max(1.5, h_step_mm * scale)
                w_cu_px = max(0.8, w_bare_mm * scale)
                h_cu_px = max(0.8, h_bare_mm * scale)
                r_out_px = max(0.0, r_out * scale)
                r_cu_px = max(0.0, fr * scale)

                def render_pack(base_inner_x: float, direction: float):
                    for i in range(ceil_layers):
                        is_odd_layer = (i % 2 == 1)
                        layer_dx = (w_step_mm / 2.0 + i * rad_pitch_mm) * scale
                        cur_layer_turns = int(turns)
                        if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and is_odd_layer:
                            cur_layer_turns = max(1, int(turns) - 1)
                        if i == ceil_layers - 1 and has_half:
                            cur_layer_turns = max(1, int(round(cur_layer_turns * (layers - full_layers))))

                        for j in range(cur_layer_turns):
                            if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and is_odd_layer:
                                cz_mm = (h_step_mm / 2.0) + (j + 0.5) * h_step_mm
                            else:
                                cz_mm = (h_step_mm / 2.0) + j * h_step_mm

                            px = base_inner_x + direction * layer_dx
                            py = origin_y - cz_mm * scale

                            # 绘制方线/扁线带倒角外廓漆膜
                            painter.setPen(pen_ins)
                            painter.setBrush(brush_ins)
                            painter.drawRoundedRect(QRectF(px - w_wire_px / 2.0, py - h_wire_px / 2.0, w_wire_px, h_wire_px), r_out_px, r_out_px)

                            # 绘制方线/扁线导电铜芯
                            painter.setPen(Qt.PenStyle.NoPen)
                            painter.setBrush(brush_cu)
                            painter.drawRoundedRect(QRectF(px - w_cu_px / 2.0, py - h_cu_px / 2.0, w_cu_px, h_cu_px), r_cu_px, r_cu_px)
            else:
                # 经典圆线渲染
                wire_r_px = max(1.2, (b_act * scale) / 2.0)
                cu_r_px = max(0.8, (d_act * scale) / 2.0)

                def render_pack(base_inner_x: float, direction: float):
                    for i in range(ceil_layers):
                        is_odd_layer = (i % 2 == 1)
                        layer_dx = (b_act / 2.0 + i * hcp_dx) * scale

                        cur_layer_turns = int(turns)
                        if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and is_odd_layer:
                            cur_layer_turns = max(1, int(turns) - 1)
                        if i == ceil_layers - 1 and has_half:
                            cur_layer_turns = max(1, int(round(cur_layer_turns * (layers - full_layers))))

                        for j in range(cur_layer_turns):
                            if is_odd_layer:
                                cz_mm = (b_act / 2.0) + (j + 0.5) * b_act
                            else:
                                cz_mm = (b_act / 2.0) + j * b_act

                            px = base_inner_x + direction * layer_dx
                            py = origin_y - cz_mm * scale

                            # 漆膜
                            painter.setPen(pen_ins)
                            painter.setBrush(brush_ins)
                            painter.drawEllipse(QPointF(px, py), wire_r_px, wire_r_px)

                            # 铜芯
                            painter.setPen(Qt.PenStyle.NoPen)
                            painter.setBrush(brush_cu)
                            painter.drawEllipse(QPointF(px, py), cu_r_px, cu_r_px)

            render_pack(x_left_inner, -1.0)
            render_pack(x_right_inner, 1.0)

            # 6. ISO 129 标准几何尺寸标注
            dim_y1 = origin_y + 14
            dim_y2 = origin_y + 30
            painter.setPen(QPen(QColor("#0284C7"), 1, Qt.PenStyle.DashLine))

            painter.drawLine(int(x_left_outer), int(dim_y1), int(x_left_inner), int(dim_y1))
            painter.drawLine(int(x_left_inner), int(dim_y1), int(x_right_inner), int(dim_y1))
            painter.drawLine(int(x_right_inner), int(dim_y1), int(x_right_outer), int(dim_y1))

            painter.setPen(QColor("#0284C7"))
            font_subdim = QFont("Consolas", 7, QFont.Weight.Bold)
            painter.setFont(font_subdim)
            w_e_box = max(w_coil_px, 44.0)
            rect_e_left = QRectF(x_left_outer + (w_coil_px - w_e_box) / 2.0, dim_y1 - 12, w_e_box, 12)
            rect_e_right = QRectF(x_right_inner + (w_coil_px - w_e_box) / 2.0, dim_y1 - 12, w_e_box, 12)
            painter.drawText(rect_e_left, Qt.AlignmentFlag.AlignCenter, f"t (E)={phys_w:.2f}")
            painter.drawText(QRectF(x_left_inner, dim_y1 - 12, w_inner_px, 12), Qt.AlignmentFlag.AlignCenter, inner_label)
            painter.drawText(rect_e_right, Qt.AlignmentFlag.AlignCenter, f"t (E)={phys_w:.2f}")

            # 总外轮廓横向尺寸标注 (ISO 129 延伸界线 + 闭合实心箭头)
            painter.setPen(QPen(QColor("#64748B"), 1))
            painter.drawLine(int(x_left_outer), int(origin_y + 1), int(x_left_outer), int(dim_y2 + 4))
            painter.drawLine(int(x_right_outer), int(origin_y + 1), int(x_right_outer), int(dim_y2 + 4))

            painter.setPen(QPen(QColor("#0284C7"), 1.2))
            painter.drawLine(int(x_left_outer), int(dim_y2), int(x_right_outer), int(dim_y2))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#0284C7")))
            draw_iso_arrow(painter, x_left_outer, dim_y2, -1.0, 0.0, 6.0, 2.2)
            draw_iso_arrow(painter, x_right_outer, dim_y2, 1.0, 0.0, 6.0, 2.2)

            font_dim = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font_dim)
            painter.setPen(QColor("#0F172A"))
            painter.drawText(
                QRectF(10, dim_y2 + 2, w - 20, 14), 
                Qt.AlignmentFlag.AlignCenter, 
                (f"{outer_label} (Max_{axis_name}: {lim_span:.2f}, Margin: {delta_span:+.3f})" if is_en else f"{outer_label} (Max_{axis_name}: {lim_span:.2f}, 余量: {delta_span:+.3f})") if is_dfm_active else (f"{outer_label} (Ref: {lim_span:.2f}, Margin: {delta_span:+.3f})" if is_en else f"{outer_label} (参考: {lim_span:.2f}, 余量: {delta_span:+.3f})")
            )

            # 右侧高度标注 H (ISO 129 延伸界线 + 闭合实心箭头)
            z_line_x = int(x_right_outer + 18)
            z_bottom = int(origin_y)
            z_top = int(origin_y - h_coil_px)
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
            painter.drawLine(int(x_right_outer + 2), z_bottom, z_line_x + 4, z_bottom)
            painter.drawLine(int(x_right_outer + 2), z_top, z_line_x + 4, z_top)

            painter.setPen(QPen(QColor("#0284C7"), 1.2))
            painter.drawLine(z_line_x, z_bottom, z_line_x, z_top)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#0284C7")))
            draw_iso_arrow(painter, z_line_x, z_top, 0.0, -1.0, 6.0, 2.2)
            draw_iso_arrow(painter, z_line_x, z_bottom, 0.0, 1.0, 6.0, 2.2)

            painter.setPen(QColor("#0284C7"))
            painter.setFont(font_subdim)
            painter.drawText(z_line_x + 5, int((z_bottom + z_top) / 2.0 - 2), "Height H" if is_en else "高度 H")
            painter.drawText(z_line_x + 5, int((z_bottom + z_top) / 2.0 + 12), f"{phys_h:.3f} mm")

        # -------------------------------------------------------------
        # 模式 C: 单侧微观放大详图 (Zoom In, 无骨架挡墙)
        # -------------------------------------------------------------
        else:
            margin_left = 65
            margin_bottom = 45
            margin_top = 45
            margin_right = 40

            view_w = w - margin_left - margin_right
            view_h = h - margin_top - margin_bottom

            scale_x = view_w / (phys_w * 1.25)
            scale_z = view_h / (max(phys_h, self.inputs.max_z_h_limit) * 1.35)
            scale = min(scale_x, scale_z)

            origin_x = margin_left + 10
            cy = (margin_top + h - margin_bottom) / 2.0 + 8
            origin_y = cy + (phys_h * scale) / 2.0

            # 1. 绘制 Z=0 基准线与内壁对齐线
            painter.setPen(QPen(QColor("#94A3B8"), 1.2, Qt.PenStyle.SolidLine))
            painter.drawLine(int(origin_x - 14), int(origin_y), int(origin_x + phys_w * scale + 18), int(origin_y))
            painter.drawLine(int(origin_x), int(origin_y + 10), int(origin_x), int(origin_y - phys_h * scale - 14))

            font_sub = QFont("Segoe UI", 7, QFont.Weight.Bold)
            painter.setFont(font_sub)
            painter.setPen(QColor("#64748B"))
            painter.drawText(int(origin_x - 56), int(origin_y - (phys_h * scale) / 2), "Inner Wall" if is_en else "内壁边界")
            painter.drawText(int(origin_x - 56), int(origin_y + 11), "Z=0 Datum" if is_en else "Z=0 基准")

            # Max_Z 限高线
            is_dfm_active = getattr(self.inputs, "dfm_enabled", False)
            lim_z = self.inputs.max_z_h_limit
            y_lim_z = origin_y - lim_z * scale
            z_safe = (phys_h <= lim_z + 1e-4) if is_dfm_active else True
            pen_lim = QPen(
                QColor("#CBD5E1") if not is_dfm_active else (QColor("#10B981") if z_safe else QColor("#EF4444")),
                1.2, 
                Qt.PenStyle.DashLine
            )
            painter.setPen(pen_lim)
            painter.drawLine(int(origin_x - 14), int(y_lim_z), int(origin_x + phys_w * scale + 18), int(y_lim_z))
            color_z_txt = QColor("#0284C7") if not is_dfm_active else (QColor("#059669") if z_safe else QColor("#DC2626"))
            painter.setPen(color_z_txt)
            painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            if is_dfm_active:
                painter.drawText(int(origin_x), int(y_lim_z - 3), f"Max Z Limit: {lim_z:.2f} mm (ΔZ: {lim_z - phys_h:+.3f})" if is_en else f"Max Z 限高: {lim_z:.2f} mm (ΔZ: {lim_z - phys_h:+.3f})")
            else:
                painter.drawText(int(origin_x), int(y_lim_z - 3), f"Ref Z Limit: {lim_z:.2f} mm (ΔZ: {lim_z - phys_h:+.3f})" if is_en else f"参考限高 Z: {lim_z:.2f} mm (ΔZ: {lim_z - phys_h:+.3f})")

            # 2. 渲染微观线圈排布
            wire_r_px = max(1.5, (b_act * scale) / 2.0)
            cu_r_px = max(1.0, (d_act * scale) / 2.0)
            pen_ins = QPen(QColor("#D97706"), 1)
            brush_ins = QBrush(QColor(254, 215, 170, 220))
            brush_cu = QBrush(QColor("#C2410C"))

            full_layers = int(math.floor(layers))
            has_half = (layers - full_layers) >= 0.25
            ceil_layers = int(math.ceil(layers))

            is_flat = (getattr(self.inputs, "wire_shape", WireShape.ROUND) in (WireShape.SQUARE, WireShape.RECTANGULAR))

            if is_flat:
                raw_w = max(0.02, float(self.inputs.flat_w))
                raw_h = raw_w if self.inputs.wire_shape == WireShape.SQUARE else max(0.02, float(self.inputs.flat_h))
                fw = max(raw_w, raw_h)
                fh = min(raw_w, raw_h)
                t_ins = max(0.001, (self.outputs.b_actual - self.outputs.d_actual) / 2.0) if (hasattr(self.outputs, "b_actual") and self.outputs.b_actual > self.outputs.d_actual) else 0.005
                fw_out = fw + 2.0 * t_ins
                fh_out = fh + 2.0 * t_ins
                fr = (fh / 4.0) if (self.inputs.flat_r_auto or self.inputs.flat_r <= 0) else min(float(self.inputs.flat_r), fh / 2.0)
                r_out = fr + t_ins
                eta = max(0.7, min(1.0, float(getattr(self.inputs, "tension_factor", 1.0))))

                if getattr(self.inputs, "flat_winding_dir", WindingDirection.FLATWISE) == WindingDirection.FLATWISE:
                    w_step_mm = fh_out * eta
                    h_step_mm = fw_out * eta
                    w_bare_mm = fh * eta
                    h_bare_mm = fw * eta
                else:
                    w_step_mm = fw_out * eta
                    h_step_mm = fh_out * eta
                    w_bare_mm = fw * eta
                    h_bare_mm = fh * eta

                delta_nest_mm = 0.0
                if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and r_out > (h_step_mm / 4.0):
                    term = max(0.0, (2.0 * r_out) ** 2 - (2.0 * r_out - h_step_mm / 2.0) ** 2)
                    delta_nest_mm = 2.0 * r_out - math.sqrt(term)
                rad_pitch_mm = w_step_mm - delta_nest_mm

                w_wire_px = max(1.5, w_step_mm * scale)
                h_wire_px = max(1.5, h_step_mm * scale)
                w_cu_px = max(0.8, w_bare_mm * scale)
                h_cu_px = max(0.8, h_bare_mm * scale)
                r_out_px = max(0.0, r_out * scale)
                r_cu_px = max(0.0, fr * scale)

                for i in range(ceil_layers):
                    is_odd_layer = (i % 2 == 1)
                    cx_mm = (w_step_mm / 2.0) + i * rad_pitch_mm
                    cur_layer_turns = int(turns)
                    if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and is_odd_layer:
                        cur_layer_turns = max(1, int(turns) - 1)
                    if i == ceil_layers - 1 and has_half:
                        cur_layer_turns = max(1, int(round(cur_layer_turns * (layers - full_layers))))

                    for j in range(cur_layer_turns):
                        if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and is_odd_layer:
                            cz_mm = (h_step_mm / 2.0) + (j + 0.5) * h_step_mm
                        else:
                            cz_mm = (h_step_mm / 2.0) + j * h_step_mm

                        px = origin_x + cx_mm * scale
                        py = origin_y - cz_mm * scale

                        # 绘制方线/扁线单侧放大漆膜
                        painter.setPen(pen_ins)
                        painter.setBrush(brush_ins)
                        painter.drawRoundedRect(QRectF(px - w_wire_px / 2.0, py - h_wire_px / 2.0, w_wire_px, h_wire_px), r_out_px, r_out_px)

                        # 绘制方线/扁线单侧放大铜芯
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(brush_cu)
                        painter.drawRoundedRect(QRectF(px - w_cu_px / 2.0, py - h_cu_px / 2.0, w_cu_px, h_cu_px), r_cu_px, r_cu_px)
            else:
                for i in range(ceil_layers):
                    is_odd_layer = (i % 2 == 1)
                    cx_mm = (b_act / 2.0) + i * hcp_dx
                    cur_layer_turns = int(turns)
                    if self.inputs.winding_mode in (WindingMode.VARIABLE, WindingMode.VARIABLE) and is_odd_layer:
                        cur_layer_turns = max(1, int(turns) - 1)
                    if i == ceil_layers - 1 and has_half:
                        cur_layer_turns = max(1, int(round(cur_layer_turns * (layers - full_layers))))

                    for j in range(cur_layer_turns):
                        if is_odd_layer:
                            cz_mm = (b_act / 2.0) + (j + 0.5) * b_act
                        else:
                            cz_mm = (b_act / 2.0) + j * b_act

                        px = origin_x + cx_mm * scale
                        py = origin_y - cz_mm * scale

                        painter.setPen(pen_ins)
                        painter.setBrush(brush_ins)
                        painter.drawEllipse(QPointF(px, py), wire_r_px, wire_r_px)

                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(brush_cu)
                        painter.drawEllipse(QPointF(px, py), cu_r_px, cu_r_px)

            # 3. 单侧标注
            dim_font = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(dim_font)
            painter.setPen(QPen(QColor("#0284C7"), 1, Qt.PenStyle.DashLine))
            x_end = origin_x + phys_w * scale
            painter.drawLine(int(origin_x), int(origin_y + 16), int(x_end), int(origin_y + 16))
            painter.setPen(QColor("#0284C7"))
            painter.drawText(int(origin_x + (phys_w * scale) / 2 - 35), int(origin_y + 30), f"Build E: {self.outputs.e_env:.3f} mm" if is_en else f"X 厚度 E: {self.outputs.e_env:.3f} mm")

            z_line_x = int(x_end + 18)
            z_bottom = int(origin_y)
            z_top = int(origin_y - phys_h * scale)
            painter.setPen(QPen(QColor("#0284C7"), 1.2))
            painter.drawLine(z_line_x, z_bottom, z_line_x, z_top)
            painter.drawLine(z_line_x - 3, z_top + 6, z_line_x, z_top)
            painter.drawLine(z_line_x + 3, z_top + 6, z_line_x, z_top)
            if is_en:
                f_mode_text = "0.5D Offset" if self.inputs.winding_mode == WindingMode.EVEN else "Flush Ends"
            else:
                f_mode_text = "含0.5D偏移" if self.inputs.winding_mode == WindingMode.EVEN else "边界平齐"
            painter.drawText(z_line_x + 6, int((z_bottom + z_top) / 2 - 4), "Height F" if is_en else "Z 高度 F")
            painter.setPen(QColor("#64748B"))
            font_f_sub = QFont("Segoe UI", 7, QFont.Weight.Bold)
            painter.setFont(font_f_sub)
            painter.drawText(z_line_x + 6, int((z_bottom + z_top) / 2 + 10), f"({f_mode_text})")
            painter.setPen(QColor("#0284C7"))
            painter.setFont(dim_font)
            painter.drawText(z_line_x + 6, int((z_bottom + z_top) / 2 + 24), f"{self.outputs.thickness_h:.3f} mm")


class MacroRacetrackCanvas(QWidget):
    """跑道型 2D 俯视外廓矢量画布 (集成 Max_X 与 Max_Y 空间装配包络线)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs = CoilInputs()
        self.outputs = CoilOutputs()
        self.setMinimumSize(280, 190)

    def updateData(self, inputs: CoilInputs, outputs: CoilOutputs):
        self.inputs = inputs
        self.outputs = outputs
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor("#FFFFFF"))

        il = self.inputs.inner_len
        iw = self.inputs.inner_wid
        ol = self.outputs.outer_len if self.outputs.outer_len > 0 else il + 1.0
        ow = self.outputs.outer_wid if self.outputs.outer_wid > 0 else iw + 1.0

        lim_x = self.inputs.max_x_len_limit
        lim_y = self.inputs.max_y_wid_limit

        margin_x = 44
        margin_top = 36
        margin_bottom = 44
        view_w = w - margin_x * 2
        view_h = h - margin_top - margin_bottom

        sqrt2 = math.sqrt(2.0)
        if self.inputs.coil_type == CoilType.OCTAGONAL:
            od1_val = self.outputs.oct_od1 if self.outputs.oct_od1 > 0 else (self.inputs.oct_id1 + 2.0 * max(0.01, self.outputs.e_env))
            od2_val = self.outputs.oct_od2 if self.outputs.oct_od2 > 0 else (self.inputs.oct_id2 + 2.0 * max(0.01, self.outputs.e_env))
            s_mag_req = (od2_val / sqrt2) + 0.25 * sqrt2
            span_oct_x = max(ol, od1_val, s_mag_req * 1.30)
            span_oct_y = max(ow, od1_val, s_mag_req * 1.30)
            span_x = max(lim_x, span_oct_x, 0.1)
            span_y = max(lim_y, span_oct_y, 0.1)
        else:
            span_x = max(ol, lim_x, 0.1)
            span_y = max(ow, lim_y, 0.1)

        scale_x = view_w / span_x
        scale_y = view_h / span_y
        scale = min(scale_x, scale_y)

        cx = w / 2.0
        cy = margin_top + view_h / 2.0

        # 1. 绘制 DFM 装配空间上限虚线框 (Max_X × Max_Y Envelope)
        is_dfm_active = getattr(self.inputs, "dfm_enabled", False)
        x_pass = ol <= lim_x + 1e-4
        y_pass = ow <= lim_y + 1e-4
        all_pass = (x_pass and y_pass) if is_dfm_active else True

        w_lim_px = lim_x * scale
        h_lim_px = lim_y * scale
        rect_lim = QRectF(cx - w_lim_px / 2.0, cy - h_lim_px / 2.0, w_lim_px, h_lim_px)

        if not is_dfm_active:
            pen_lim = QPen(QColor("#CBD5E1"), 1.2, Qt.PenStyle.DashDotLine)
            brush_lim = QBrush(QColor(241, 245, 249, 20))
        elif all_pass:
            pen_lim = QPen(QColor("#10B981"), 1.2, Qt.PenStyle.DashDotLine)
            brush_lim = QBrush(QColor(240, 253, 244, 40))
        else:
            pen_lim = QPen(QColor("#EF4444"), 1.2, Qt.PenStyle.DashDotLine)
            brush_lim = QBrush(QColor(254, 242, 242, 40))

        painter.setPen(pen_lim)
        painter.setBrush(brush_lim)
        painter.drawRect(rect_lim)

        # 空间框角标文字 (固定顶部胶囊状态栏，避免倒置跳入线圈内部)
        font_lim = QFont("Consolas", 7, QFont.Weight.Bold)
        painter.setFont(font_lim)
        delta_x = lim_x - ol
        delta_y = lim_y - ow

        is_en = i18n.is_english()
        if not is_dfm_active:
            status_prefix = "Ref Envelope (DFM Off)" if is_en else "参考结构空间 (DFM未开启)"
            text_lim = f"{status_prefix}: X_Max {lim_x:.2f} mm (ΔX:{delta_x:+.3f}) | Y_Max {lim_y:.2f} mm (ΔY:{delta_y:+.3f})"
            color_txt = QColor("#0284C7")
            border_txt = QColor("#BAE6FD")
            bg_txt = QColor(240, 249, 255, 235)
        elif all_pass:
            status_prefix = "Assembly Envelope Limit" if is_en else "装配空间上限"
            text_lim = f"{status_prefix}: X_Max {lim_x:.2f} mm (ΔX:{delta_x:+.3f}) | Y_Max {lim_y:.2f} mm (ΔY:{delta_y:+.3f})"
            color_txt = QColor("#059669")
            border_txt = QColor("#10B981")
            bg_txt = QColor(255, 255, 255, 235)
        else:
            status_prefix = "⚠️ DFM Limit Exceeded" if is_en else "⚠️ DFM超差警告"
            text_lim = f"{status_prefix}: X_Max {lim_x:.2f} mm (ΔX:{delta_x:+.3f}) | Y_Max {lim_y:.2f} mm (ΔY:{delta_y:+.3f})"
            color_txt = QColor("#DC2626")
            border_txt = QColor("#EF4444")
            bg_txt = QColor(255, 255, 255, 235)

        fm = painter.fontMetrics()
        t_w = fm.horizontalAdvance(text_lim)
        painter.fillRect(10, 8, t_w + 12, 18, bg_txt)
        painter.setPen(QPen(border_txt, 1))
        painter.drawRoundedRect(QRectF(10, 8, t_w + 12, 18), 3, 3)
        painter.setPen(color_txt)
        painter.drawText(16, 21, text_lim)

        # 2. 十字中心线
        painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(int(cx - view_w / 2 - 10), int(cy), int(cx + view_w / 2 + 10), int(cy))
        painter.drawLine(int(cx), int(cy - view_h / 2 - 10), int(cx), int(cy + view_h / 2 + 10))

        # 3. 几何外廓渲染 (支持跑道型、圆形、八角形VCM及任意CAD异形)
        if self.inputs.coil_type == CoilType.CIRCULAR:
            id_val = self.inputs.inner_len
            od_val = self.outputs.outer_len if self.outputs.outer_len > 0 else id_val + 1.0
            r_in = (id_val * scale) / 2.0
            r_out = (od_val * scale) / 2.0

            path_out = QPainterPath()
            path_out.addEllipse(QPointF(cx, cy), r_out, r_out)
            path_in = QPainterPath()
            path_in.addEllipse(QPointF(cx, cy), r_in, r_in)
            coil_path = path_out.subtracted(path_in)

            grad = QLinearGradient(cx - r_out, cy - r_out, cx + r_out, cy + r_out)
            grad.setColorAt(0.0, QColor("#FDBA74"))
            grad.setColorAt(0.5, QColor("#FED7AA"))
            grad.setColorAt(1.0, QColor("#FDBA74"))

            painter.setPen(QPen(QColor("#EA580C"), 1.5))
            painter.setBrush(QBrush(grad))
            painter.drawPath(coil_path)

            # 底部专用无遮挡信息状态栏 (白色半透明底色，双行结构化排版，绝无重叠)
            painter.fillRect(0, h - 34, w, 34, QColor(255, 255, 255, 240))
            painter.setPen(QPen(QColor("#E2E8F0"), 1))
            painter.drawLine(0, h - 34, w, h - 34)

            font_dim = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font_dim)
            painter.setPen(QColor("#0F172A"))
            painter.drawText(12, h - 19, f"[Outer Envelope] Outer Dia OD: Φ {od_val:.3f} mm  |  Mean Dia Dm: Φ {self.outputs.mean_dia_mm:.3f} mm" if is_en else f"【外包络】外径 OD: Φ {od_val:.3f} mm  |  展开中径 Dm: Φ {self.outputs.mean_dia_mm:.3f} mm")

            painter.setPen(QColor("#475569"))
            font_sub = QFont("Consolas", 7, QFont.Weight.Bold)
            painter.setFont(font_sub)
            painter.drawText(12, h - 6, f"[Inner Bore] Inner Dia ID: Φ {id_val:.2f} mm" if is_en else f"【内腔基准】内径 ID: Φ {id_val:.2f} mm")

        elif self.inputs.coil_type == CoilType.OCTAGONAL:
            id1 = max(0.2, self.inputs.oct_id1)
            r1 = max(0.01, self.inputs.oct_r1)
            sqrt2 = math.sqrt(2.0)
            r1_cut = 2.0 * (sqrt2 - 1.0) * r1

            # 严格几何闭合求解与约束，防止 L2 <= 0 倒角坍塌穿透磁钢
            id2_min = (id1 + 0.10 + r1_cut) / sqrt2
            id2_max = sqrt2 * id1 - r1_cut - 0.10
            if id2_max < id2_min:
                id2 = id1 * 1.14
            else:
                raw_id2 = self.inputs.oct_id2 if self.inputs.oct_id2 > 0 else id1 * 1.14
                id2 = max(id2_min, min(raw_id2, id2_max))

            l1 = max(0.10, sqrt2 * id2 - id1 - r1_cut)
            l2 = max(0.10, sqrt2 * id1 - id2 - r1_cut)

            e_val = max(0.01, self.outputs.e_env)
            od1 = self.outputs.oct_od1 if self.outputs.oct_od1 > 0 else id1 + 2.0 * e_val
            od2 = self.outputs.oct_od2 if self.outputs.oct_od2 > 0 else id2 + 2.0 * e_val

            # 1. 绘制 4 颗四角等腰直角三角形永久磁钢 (VCM Corner Magnets, 严格依图3、图4工程装配)
            # 磁钢斜边 (面对线圈) 严格呈 45.0°，与八角形线圈斜边严格平行，单边均匀工作气隙 gap_mag
            # 直角边完全等长，绝不受外部 X/Y 长宽比不对称影响
            gap_mag = 0.25
            s_inner = (od2 / sqrt2) + gap_mag * sqrt2

            # 磁钢斜边长度充分覆盖八角形线圈斜边 L2 并带适度装配包裹裕量
            w_hyp = max(l2 + 0.8, 3.2)
            leg_len = w_hyp / sqrt2
            c_apex = (s_inner + leg_len) / 2.0
            if c_apex < (od1 / 2.0) + 0.4:
                c_apex = (od1 / 2.0) + 0.4

            p_inner = s_inner - c_apex

            mag_corners = [
                # Top-Right (右上角)
                [
                    QPointF(cx + p_inner * scale, cy - c_apex * scale),
                    QPointF(cx + c_apex * scale, cy - c_apex * scale),
                    QPointF(cx + c_apex * scale, cy - p_inner * scale),
                ],
                # Top-Left (左上角)
                [
                    QPointF(cx - p_inner * scale, cy - c_apex * scale),
                    QPointF(cx - c_apex * scale, cy - c_apex * scale),
                    QPointF(cx - c_apex * scale, cy - p_inner * scale),
                ],
                # Bottom-Left (左下角)
                [
                    QPointF(cx - p_inner * scale, cy + c_apex * scale),
                    QPointF(cx - c_apex * scale, cy + c_apex * scale),
                    QPointF(cx - c_apex * scale, cy + p_inner * scale),
                ],
                # Bottom-Right (右下角)
                [
                    QPointF(cx + p_inner * scale, cy + c_apex * scale),
                    QPointF(cx + c_apex * scale, cy + c_apex * scale),
                    QPointF(cx + c_apex * scale, cy + p_inner * scale),
                ],
            ]

            grad_mag = QLinearGradient(cx - (ol * scale) / 2, cy - (ow * scale) / 2, cx + (ol * scale) / 2, cy + (ow * scale) / 2)
            grad_mag.setColorAt(0.0, QColor("#E0F2FE"))
            grad_mag.setColorAt(0.5, QColor("#BAE6FD"))
            grad_mag.setColorAt(1.0, QColor("#7DD3FC"))

            painter.setPen(QPen(QColor("#0284C7"), 1.2))
            painter.setBrush(QBrush(grad_mag))
            for m_poly in mag_corners:
                painter.drawPolygon(QPolygonF(m_poly))

            # 磁钢文字标识：统一标识为“磁钢”（同极性径向充磁，杜绝N/S极性误解，形心居中排版）
            font_mag = QFont("Microsoft YaHei", 6, QFont.Weight.Bold)
            painter.setFont(font_mag)
            painter.setPen(QColor("#0369A1"))
            for m_poly in mag_corners:
                c_x = (m_poly[0].x() + m_poly[1].x() + m_poly[2].x()) / 3.0
                c_y = (m_poly[0].y() + m_poly[1].y() + m_poly[2].y()) / 3.0
                painter.drawText(QRectF(c_x - 24, c_y - 8, 48, 16), Qt.AlignmentFlag.AlignCenter, "Magnet" if is_en else "磁钢")

            # 2. 绘制八角形线圈实体
            in_pts = generate_octagonal_polygon_points(id1, id2, l1, l2, r1, num_arc_pts=10)
            out_pts = generate_octagonal_polygon_points(od1, od2, l1, l2, r1 + e_val, num_arc_pts=10)

            path_out = QPainterPath()
            path_out.addPolygon(QPolygonF([QPointF(cx + p[0][0] * scale, cy - p[0][1] * scale) for p in out_pts]))
            path_out.closeSubpath()

            path_in = QPainterPath()
            path_in.addPolygon(QPolygonF([QPointF(cx + p[0][0] * scale, cy - p[0][1] * scale) for p in in_pts]))
            path_in.closeSubpath()

            coil_path = path_out.subtracted(path_in)

            grad_copper = QLinearGradient(cx - (od1 * scale) / 2, cy - (od1 * scale) / 2, cx + (od1 * scale) / 2, cy + (od1 * scale) / 2)
            grad_copper.setColorAt(0.0, QColor("#FDBA74"))
            grad_copper.setColorAt(0.5, QColor("#FED7AA"))
            grad_copper.setColorAt(1.0, QColor("#EA580C"))

            painter.setPen(QPen(QColor("#C2410C"), 1.5))
            painter.setBrush(QBrush(grad_copper))
            painter.drawPath(coil_path)

            # 底部专用无遮挡信息状态栏 (白色半透明底色，双行结构化排版，绝无重叠)
            painter.fillRect(0, h - 34, w, 34, QColor(255, 255, 255, 240))
            painter.setPen(QPen(QColor("#E2E8F0"), 1))
            painter.drawLine(0, h - 34, w, h - 34)

            font_dim = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font_dim)
            painter.setPen(QColor("#0F172A"))
            painter.drawText(12, h - 19, f"[Outer Envelope] Flat OD1: {od1:.3f} mm  |  Diagonal OD2: {od2:.3f} mm" if is_en else f"【外包络】对边 OD1: {od1:.3f} mm  |  对角 OD2: {od2:.3f} mm")

            painter.setPen(QColor("#475569"))
            font_sub = QFont("Consolas", 7, QFont.Weight.Bold)
            painter.setFont(font_sub)
            painter.drawText(12, h - 6, f"[Inner Bore] ID1: {id1:.2f} | ID2: {id2:.2f} | Flat L1: {l1:.2f} | 45° Bevel L2: {l2:.2f} | R1: {r1:.2f} mm" if is_en else f"【内腔】ID1: {id1:.2f} | ID2: {id2:.2f} | 平直L1: {l1:.2f} | 45°斜边L2: {l2:.2f} | R1: {r1:.2f} mm")

        elif self.inputs.coil_type == CoilType.ARBITRARY_PERIMETER:
            ref_l = max(1.0, self.inputs.arbitrary_outer_len)
            ref_w = max(1.0, self.inputs.arbitrary_outer_wid)
            e_val = max(0.01, self.outputs.e_env)
            c_in = self.outputs.c_inner_mm
            c_out = self.outputs.c_outer_mm
            mlt = self.outputs.mlt

            rx_out = (ref_l + 2.0 * e_val) * scale / 2.0
            ry_out = (ref_w + 2.0 * e_val) * scale / 2.0
            rx_in = ref_l * scale / 2.0
            ry_in = ref_w * scale / 2.0

            path_out = QPainterPath()
            path_out.addRoundedRect(QRectF(cx - rx_out, cy - ry_out, rx_out * 2, ry_out * 2), rx_out * 0.4, ry_out * 0.4)
            path_in = QPainterPath()
            path_in.addRoundedRect(QRectF(cx - rx_in, cy - ry_in, rx_in * 2, ry_in * 2), rx_in * 0.4, ry_in * 0.4)
            coil_path = path_out.subtracted(path_in)

            grad_copper = QLinearGradient(cx - rx_out, cy - ry_out, cx + rx_out, cy + ry_out)
            grad_copper.setColorAt(0.0, QColor("#FDBA74"))
            grad_copper.setColorAt(0.5, QColor("#FED7AA"))
            grad_copper.setColorAt(1.0, QColor("#EA580C"))

            painter.setPen(QPen(QColor("#EA580C"), 1.5))
            painter.setBrush(QBrush(grad_copper))
            painter.drawPath(coil_path)

            # 底部专用无遮挡信息状态栏 (白色半透明底色，双行结构化排版，绝无重叠)
            painter.fillRect(0, h - 34, w, 34, QColor(255, 255, 255, 240))
            painter.setPen(QPen(QColor("#E2E8F0"), 1))
            painter.drawLine(0, h - 34, w, h - 34)

            font_dim = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font_dim)
            painter.setPen(QColor("#0F172A"))
            painter.drawText(12, h - 19, f"[Perimeter] Mean Turn Length MLT: {mlt:.3f} mm  |  Outer C_out: {c_out:.3f} mm" if is_en else f"【周长解析】中线周长 MLT: {mlt:.3f} mm  |  展开外周长 C_out: {c_out:.3f} mm")

            painter.setPen(QColor("#475569"))
            font_sub = QFont("Consolas", 7, QFont.Weight.Bold)
            painter.setFont(font_sub)
            painter.drawText(12, h - 6, f"[CAD Bore] Inner Perimeter C_in: {c_in:.3f} mm  |  Ref Envelope: {self.outputs.outer_len:.2f} × {self.outputs.outer_wid:.2f} mm" if is_en else f"【CAD内腔基准】展开内周长 C_in: {c_in:.3f} mm  |  参考外廓: {self.outputs.outer_len:.2f} × {self.outputs.outer_wid:.2f} mm")

        else:
            def create_racetrack_path(len_mm: float, wid_mm: float) -> QPainterPath:
                path = QPainterPath()
                rad = (wid_mm * scale) / 2.0
                straight_half = max(0.0, (len_mm - wid_mm) * scale / 2.0)

                right_rect = QRectF(cx + straight_half - rad, cy - rad, rad * 2, rad * 2)
                left_rect = QRectF(cx - straight_half - rad, cy - rad, rad * 2, rad * 2)

                path.moveTo(cx - straight_half, cy - rad)
                path.lineTo(cx + straight_half, cy - rad)
                path.arcTo(right_rect, 90, -180)
                path.lineTo(cx - straight_half, cy + rad)
                path.arcTo(left_rect, 270, -180)
                path.closeSubpath()
                return path

            outer_path = create_racetrack_path(ol, ow)
            inner_path = create_racetrack_path(il, iw)
            coil_path = outer_path.subtracted(inner_path)

            grad = QLinearGradient(cx - (ol * scale) / 2, cy, cx + (ol * scale) / 2, cy)
            grad.setColorAt(0.0, QColor("#FDBA74"))
            grad.setColorAt(0.5, QColor("#FED7AA"))
            grad.setColorAt(1.0, QColor("#FDBA74"))

            painter.setPen(QPen(QColor("#EA580C"), 1.5))
            painter.setBrush(QBrush(grad))
            painter.drawPath(coil_path)

            # 4. 绘制 60° 换层交叉线特征标注 (依工程图纸规范: 60.00° 交叉线区域、进出线引脚)
            if self.inputs.has_crossover_wire:
                painter.save()
                r_inner_edge = (iw * scale) / 2.0
                r_outer_edge = (ow * scale) / 2.0
                r_ext = r_outer_edge + 18.0

                # 60° 夹角两条射线 (垂直向下方向 90° ± 30°，即 60° 与 120°)
                rad60 = math.radians(60.0)
                rad120 = math.radians(120.0)

                p_center = QPointF(cx, cy)
                p_ray_left = QPointF(cx + r_ext * math.cos(rad120), cy + r_ext * math.sin(rad120))
                p_ray_right = QPointF(cx + r_ext * math.cos(rad60), cy + r_ext * math.sin(rad60))

                # 1. 交叉线扇形区域半透明警示橙色填充
                hatch_path = QPainterPath()
                hatch_path.moveTo(cx, cy)
                hatch_path.lineTo(p_ray_left)
                hatch_path.lineTo(p_ray_right)
                hatch_path.closeSubpath()
                cross_highlight = hatch_path.intersected(coil_path)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(234, 88, 12, 65)))
                painter.drawPath(cross_highlight)

                # 2. 60° 两侧发散引导虚线
                pen_guide = QPen(QColor("#0284C7"), 1.2, Qt.PenStyle.DashLine)
                painter.setPen(pen_guide)
                painter.drawLine(p_center, p_ray_left)
                painter.drawLine(p_center, p_ray_right)

                # 3. 60.00° CAD 角度标注弧线与双向指示
                r_arc = (r_inner_edge + r_outer_edge) / 2.0
                arc_rect = QRectF(cx - r_arc, cy - r_arc, r_arc * 2, r_arc * 2)
                painter.setPen(QPen(QColor("#0284C7"), 1.0))
                painter.drawArc(arc_rect, int(-60 * 16), int(-60 * 16))

                # 4. 角度文字与局部外扩标注 (置于扇形内部中位，与图纸 CAD 标注风格完全一致，绝不遮挡底部边框)
                font_cross = QFont("Microsoft YaHei", 7, QFont.Weight.Bold)
                painter.setFont(font_cross)
                painter.setPen(QColor("#0369A1"))
                text_cross = (f"60.00° Crossover Zone (+{self.outputs.delta_w_crossover:.3f}mm)" if is_en else f"60.00° 交叉线区域 (+{self.outputs.delta_w_crossover:.3f}mm)")
                fm_c = painter.fontMetrics()
                tw_c = fm_c.horizontalAdvance(text_cross)
                badge_x = cx - tw_c / 2.0
                badge_y = cy + r_arc + 11.0
                painter.fillRect(int(badge_x - 4), int(badge_y - 10), tw_c + 8, 13, QColor(255, 255, 255, 210))
                painter.drawText(int(badge_x), int(badge_y), text_cross)

                # 5. 进线与出线线头示意 (依图纸规范: 进线右下角, 出线右上角)
                pen_lead = QPen(QColor("#D97706"), 1.6)
                painter.setPen(pen_lead)
                # 进线 (底侧偏右斜向引出)
                p_lead_in_start = QPointF(cx + (ol * scale) / 4.0, cy + r_outer_edge)
                p_lead_in_end = QPointF(cx + (ol * scale) / 4.0 + 26, cy + r_outer_edge + 18)
                painter.drawLine(p_lead_in_start, p_lead_in_end)
                painter.drawText(int(p_lead_in_end.x() + 3), int(p_lead_in_end.y() + 4), "Lead In" if is_en else "进线")

                # 出线 (顶侧偏右斜向引出)
                p_lead_out_start = QPointF(cx + (ol * scale) / 4.0, cy - r_outer_edge)
                p_lead_out_end = QPointF(cx + (ol * scale) / 4.0 + 22, cy - r_outer_edge - 18)
                painter.drawLine(p_lead_out_start, p_lead_out_end)
                painter.drawText(int(p_lead_out_end.x() + 3), int(p_lead_out_end.y() - 2), "Lead Out" if is_en else "出线")

                painter.restore()

            # 底部专用无遮挡信息状态栏 (白色半透明底色，双行结构化排版，绝无重叠)
            painter.fillRect(0, h - 34, w, 34, QColor(255, 255, 255, 240))
            painter.setPen(QPen(QColor("#E2E8F0"), 1))
            painter.drawLine(0, h - 34, w, h - 34)

            font_dim = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font_dim)
            painter.setPen(QColor("#0F172A"))
            if self.inputs.has_crossover_wire:
                painter.drawText(12, h - 19, f"[Outer Envelope] Outer Length OL: {ol:.3f} mm  |  Outer Width OW: {ow:.3f} mm (incl. 60° Crossover +{self.outputs.delta_w_crossover:.3f}mm)" if is_en else f"【外包络】外长 OL: {ol:.3f} mm  |  外宽 OW: {ow:.3f} mm (含60°交叉线 +{self.outputs.delta_w_crossover:.3f}mm)")
            else:
                painter.drawText(12, h - 19, f"[Outer Envelope] Outer Length OL: {ol:.3f} mm  |  Outer Width OW: {ow:.3f} mm" if is_en else f"【外包络】外长 OL: {ol:.3f} mm  |  外宽 OW: {ow:.3f} mm")

            painter.setPen(QColor("#475569"))
            font_sub = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font_sub)
            painter.drawText(12, h - 6, f"[Inner Bore] Inner Length IL: {il:.2f} mm  |  Inner Width IW: {iw:.2f} mm" if is_en else f"【内腔基准】内长 IL: {il:.2f} mm  |  内宽 IW: {iw:.2f} mm")


class MagnetSectionCanvas(QWidget):
    """
    线圈 2D 截面与 DFM 空间装配卡控矢量画布 (Pure Coil 2D Cross-Section & DFM Envelope)
    方案 A (极简纯粹主义)：
    1. 彻底剔除非线圈相关的电机外部假设 (磁钢、磁轭、铁芯、工作气隙、振动行程等)
    2. 真实呈现线圈导电截面 (左/右绕组截面、单边壁厚 E、成型厚度/高度 F、内腔孔径 ID/IW/IL、外廓外径 OD/OW/OL)
    3. 叠加 DFM 空间卡控包络框 (Max_X / Max_OD / Max_Y × Max_Z)
    4. 空间余量分析与干涉预警：
       - 当线圈在限高和限宽内时：绿色虚线框提示安全配合余量 (ΔZ, ΔX/ΔY)
       - 当线圈高度超标 (F > Max_Z) 或外廓超宽时：红框报警并以红色半透明高亮干涉超差区域
    5. 支持跑道型线圈在 Z-X 长向截面 与 Z-Y 宽向截面 之间一键切换 (右上角药丸按钮)
    6. 底部双行关键尺寸与配合余量无遮挡清晰呈现
    """

    adaptiveToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs = CoilInputs()
        self.outputs = CoilOutputs()
        self.section_mode = "zy"  # "zx": Z-X长向截面; "zy": Z-Y宽向截面 (跑道型默认宽向剖切，关键配合方向)
        self.setMinimumSize(280, 200)

    def updateData(self, inputs: CoilInputs, outputs: CoilOutputs):
        self.inputs = inputs
        self.outputs = outputs
        self.update()

    def mousePressEvent(self, event):
        if self.inputs.coil_type in (CoilType.RACETRACK, CoilType.OCTAGONAL):
            pos = event.position()
            w = self.width()
            pill_zx = QRectF(w - 225, 8, 100, 22)
            pill_zy = QRectF(w - 115, 8, 100, 22)
            if pill_zx.contains(pos):
                self.section_mode = "zx"
                self.update()
            elif pill_zy.contains(pos):
                self.section_mode = "zy"
                self.update()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        c_type = self.inputs.coil_type
        e_env = max(0.01, self.outputs.e_env)
        f_thk = max(0.01, self.outputs.thickness_h)
        lim_z = self.inputs.max_z_h_limit

        is_en = i18n.is_english()
        if c_type == CoilType.CIRCULAR:
            in_dim = max(0.1, self.inputs.inner_len)
            out_dim = max(in_dim + 2.0 * e_env, self.outputs.outer_len)
            lim_dim = self.inputs.max_x_len_limit
            view_title = "Circular 2D Radial Section & DFM Clearance (OD × F)" if is_en else "圆线圈 2D 径向剖面与 DFM 装配限值 (OD × F)"
            dim_in_name = "ID" if is_en else "内径 ID"
            dim_out_name = "OD" if is_en else "外径 OD"
            dim_lim_name = "Max_OD"
        elif c_type == CoilType.OCTAGONAL:
            if self.section_mode == "zx":
                in_dim = max(0.1, self.inputs.oct_id1)
                out_dim = max(in_dim + 2.0 * e_env, self.outputs.oct_od1)
                lim_dim = self.inputs.max_x_len_limit
                view_title = "Octagonal 2D Section (Flat Span ID1/OD1 & Clearance)" if is_en else "八角形 2D 截面 (对边剖面 ID1/OD1 与限宽公差)"
                dim_in_name = "Flat ID1" if is_en else "对边内跨 ID1"
                dim_out_name = "Flat OD1" if is_en else "对边外跨 OD1"
                dim_lim_name = "Max_X"
            else:
                in_dim = max(0.1, self.inputs.oct_id2)
                out_dim = max(in_dim + 2.0 * e_env, self.outputs.oct_od2)
                lim_dim = self.inputs.max_y_wid_limit
                view_title = "Octagonal 2D Section (45° Diagonal ID2/OD2 & Clearance)" if is_en else "八角形 2D 截面 (45°对角剖面 ID2/OD2 与限宽公差)"
                dim_in_name = "Diag ID2" if is_en else "对角内跨 ID2"
                dim_out_name = "Diag OD2" if is_en else "对角外跨 OD2"
                dim_lim_name = "Max_Y"
        elif c_type == CoilType.ARBITRARY_PERIMETER:
            out_dim = max(1.0, self.outputs.outer_len)
            in_dim = max(0.1, out_dim - 2.0 * e_env)
            lim_dim = self.inputs.max_x_len_limit
            view_title = "Arbitrary Contour 2D Section & DFM Clearance" if is_en else "通用异形 2D 截面与 DFM 装配限高"
            dim_in_name = "Ref Inner" if is_en else "参考内跨"
            dim_out_name = "Ref Outer" if is_en else "参考外跨"
            dim_lim_name = "Max_X"
        else:
            if self.section_mode == "zx":
                in_dim = max(0.1, self.inputs.inner_len)
                out_dim = max(in_dim + 2.0 * e_env, self.outputs.outer_len)
                lim_dim = self.inputs.max_x_len_limit
                view_title = "Racetrack 2D Section (Z-X Long & X-Limit)" if is_en else "跑道型 2D 截面 (Z-X 长向剖面与 X 向限宽)"
                dim_in_name = "IL" if is_en else "内长 IL"
                dim_out_name = "OL" if is_en else "外长 OL"
                dim_lim_name = "Max_X"
            else:
                in_dim = max(0.1, self.inputs.inner_wid)
                out_dim = max(in_dim + 2.0 * e_env, self.outputs.outer_wid)
                lim_dim = self.inputs.max_y_wid_limit
                view_title = "Racetrack 2D Section (Z-Y Width & Y-Limit)" if is_en else "跑道型 2D 截面 (Z-Y 宽向剖面与 Y 向限宽)"
                dim_in_name = "IW" if is_en else "内宽 IW"
                dim_out_name = "OW" if is_en else "外宽 OW"
                dim_lim_name = "Max_Y"

        delta_z = lim_z - f_thk
        delta_dim = lim_dim - out_dim
        z_pass = (f_thk <= lim_z + 1e-4)
        dim_pass = (out_dim <= lim_dim + 1e-4)
        all_pass = z_pass and dim_pass

        # 1. 标题与药丸按钮
        painter.setPen(QColor("#0F172A"))
        painter.setFont(QFont("Microsoft YaHei", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(14, 8, 380, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, view_title)

        if c_type in (CoilType.RACETRACK, CoilType.OCTAGONAL):
            pill_zx = QRectF(w - 225, 8, 100, 22)
            pill_zy = QRectF(w - 115, 8, 100, 22)

            if is_en:
                t1 = ("● Flat Sec" if self.section_mode == "zx" else "○ Flat Sec") if c_type == CoilType.OCTAGONAL else ("● Z-X Long" if self.section_mode == "zx" else "○ Z-X Long")
                t2 = ("● Diag Sec" if self.section_mode == "zy" else "○ Diag Sec") if c_type == CoilType.OCTAGONAL else ("● Z-Y Width" if self.section_mode == "zy" else "○ Z-Y Width")
            else:
                t1 = ("● 对边剖面" if self.section_mode == "zx" else "○ 对边剖面") if c_type == CoilType.OCTAGONAL else ("● Z-X 长向" if self.section_mode == "zx" else "○ Z-X 长向")
                t2 = ("● 对角剖面" if self.section_mode == "zy" else "○ 对角剖面") if c_type == CoilType.OCTAGONAL else ("● Z-Y 宽向" if self.section_mode == "zy" else "○ Z-Y 宽向")

            painter.setPen(QPen(QColor("#0284C7") if self.section_mode == "zx" else QColor("#CBD5E1"), 1.2 if self.section_mode == "zx" else 1))
            painter.setBrush(QBrush(QColor("#E0F2FE") if self.section_mode == "zx" else QColor("#F8FAFC")))
            painter.drawRoundedRect(pill_zx, 11, 11)
            painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Bold))
            painter.setPen(QColor("#0284C7") if self.section_mode == "zx" else QColor("#64748B"))
            painter.drawText(pill_zx, Qt.AlignmentFlag.AlignCenter, t1)

            painter.setPen(QPen(QColor("#0284C7") if self.section_mode == "zy" else QColor("#CBD5E1"), 1.2 if self.section_mode == "zy" else 1))
            painter.setBrush(QBrush(QColor("#E0F2FE") if self.section_mode == "zy" else QColor("#F8FAFC")))
            painter.drawRoundedRect(pill_zy, 11, 11)
            painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Bold))
            painter.setPen(QColor("#0284C7") if self.section_mode == "zy" else QColor("#64748B"))
            painter.drawText(pill_zy, Qt.AlignmentFlag.AlignCenter, t2)
        elif c_type == CoilType.CIRCULAR:
            pill_circ = QRectF(w - 145, 8, 130, 22)
            painter.setPen(QPen(QColor("#0284C7"), 1.2))
            painter.setBrush(QBrush(QColor("#F0F9FF")))
            painter.drawRoundedRect(pill_circ, 11, 11)
            painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Bold))
            painter.setPen(QColor("#0284C7"))
            painter.drawText(pill_circ, Qt.AlignmentFlag.AlignCenter, "● Axisymmetric" if is_en else "● 旋转对称剖面")
        else:
            pill_arb = QRectF(w - 155, 8, 140, 22)
            painter.setPen(QPen(QColor("#0284C7"), 1.2))
            painter.setBrush(QBrush(QColor("#F0F9FF")))
            painter.drawRoundedRect(pill_arb, 11, 11)
            painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Bold))
            painter.setPen(QColor("#0284C7"))
            painter.drawText(pill_arb, Qt.AlignmentFlag.AlignCenter, "● Equiv. Section" if is_en else "● CAD周长等效剖面")

        # 2. 动态自适应几何原点与防重叠底部堆叠布局 (保证任意高度与DPI缩放绝不重叠)
        is_dfm_active = getattr(self.inputs, "dfm_enabled", False)
        if not is_dfm_active:
            z_pass = True
            dim_pass = True
            all_pass = True

        phys_w = max(out_dim, lim_dim) * 1.35 + 0.6
        phys_h = max(f_thk, lim_z) * 1.35 + 0.4
        cx = w / 2.0

        # 底部信息卡固定高度与边距
        bottom_card_h = 32.0
        rect_bottom_card = QRectF(6, h - bottom_card_h - 4, w - 12, bottom_card_h)

        show_floating_badge = (h >= 240)
        if show_floating_badge:
            badge_h = 18.0
            badge_y = rect_bottom_card.top() - badge_h - 6.0
            badge_w = min(w - 40, 420)
            rect_badge = QRectF(cx - badge_w / 2.0, badge_y, badge_w, badge_h)
            y_dim_out = badge_y - 12.0
            y_dim_in = y_dim_out - 20.0
            base_y = y_dim_in - 16.0
        else:
            y_dim_out = rect_bottom_card.top() - 12.0
            y_dim_in = y_dim_out - 20.0
            base_y = y_dim_in - 16.0

        view_w = w - 80
        view_h = max(30.0, base_y - 52.0)
        scale = min(view_w / max(0.1, phys_w), view_h / max(0.1, phys_h))

        # 3. Z=0 基准线 (Datum Baseline) 与 ISO 5459 基准特征符号 [ A ]
        w_base_px = max(out_dim, lim_dim) * scale * 1.35
        x_base_left = cx - w_base_px / 2.0
        x_base_right = cx + w_base_px / 2.0
        painter.setPen(QPen(QColor("#64748B"), 1.2))
        painter.drawLine(int(x_base_left), int(base_y), int(x_base_right), int(base_y))

        # 地线小斜线 (阴影剖面线)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        hatch_step = 16
        for hx in range(int(x_base_left), int(x_base_right), hatch_step):
            painter.drawLine(hx, int(base_y), hx - 5, int(base_y + 5))

        # 4. 对称中心轴 (ISO 128 Dash-Dot Centerline)
        painter.setPen(QPen(QColor("#94A3B8"), 1, Qt.PenStyle.DashDotLine))
        y_top_axis = base_y - max(f_thk, lim_z) * scale - 28
        painter.drawLine(int(cx), int(base_y + 15), int(cx), int(y_top_axis))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#64748B"))
        painter.drawText(int(cx + 4), int(y_top_axis + 10), "℄")

        # 5. DFM 装配空间包络框 (Max Limit Bounding Box)
        w_lim_px = lim_dim * scale
        h_lim_px = lim_z * scale
        x_lim_left = cx - w_lim_px / 2.0
        x_lim_right = cx + w_lim_px / 2.0
        y_lim_top = base_y - h_lim_px
        rect_dfm_box = QRectF(x_lim_left, y_lim_top, w_lim_px, h_lim_px)

        if not is_dfm_active:
            pen_dfm = QPen(QColor("#CBD5E1"), 1.2, Qt.PenStyle.DashLine)
            painter.setPen(pen_dfm)
            painter.setBrush(QBrush(QColor(241, 245, 249, 20)))
        else:
            pen_dfm = QPen(
                QColor("#10B981" if all_pass else "#EF4444"),
                1.4,
                Qt.PenStyle.DashLine
            )
            painter.setPen(pen_dfm)
            painter.setBrush(QBrush(QColor(16, 185, 129, 15) if all_pass else QColor(239, 68, 68, 15)))
        painter.drawRect(rect_dfm_box)

        # Max_Z 限高顶线标注 (置于顶部独立安全带 Y=34，带轻量胶囊底色)
        painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        if not is_dfm_active:
            color_z = QColor("#0284C7")
            bg_z = QColor("#F0F9FF")
            z_tag_text = (f"▲ Ref Z Limit {dim_lim_name}_Z: {lim_z:.2f} mm (Margin ΔZ: {delta_z:+.3f} mm)" if is_en else f"▲ 参考限高 {dim_lim_name}_Z: {lim_z:.2f} mm (余量 ΔZ: {delta_z:+.3f} mm)")
        else:
            color_z = QColor("#059669" if z_pass else "#DC2626")
            bg_z = QColor("#ECFDF5" if z_pass else "#FEF2F2")
            z_tag_text = (f"▲ Max Z Limit {dim_lim_name}_Z: {lim_z:.2f} mm (Margin ΔZ: {delta_z:+.3f} mm)" if is_en else f"▲ 空间限高 {dim_lim_name}_Z: {lim_z:.2f} mm (余量 ΔZ: {delta_z:+.3f} mm)")

        rect_lim_z_tag = QRectF(14, 34, 280, 16)
        painter.setPen(QPen(color_z, 1))
        painter.setBrush(QBrush(bg_z))
        painter.drawRoundedRect(rect_lim_z_tag, 3, 3)
        painter.setPen(color_z)
        painter.drawText(
            rect_lim_z_tag,
            Qt.AlignmentFlag.AlignCenter,
            z_tag_text
        )

        # 在虚线右侧标注短标线
        painter.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        painter.setPen(color_z)
        painter.drawText(int(x_lim_right + 5), int(y_lim_top + 3), f"Max_Z:{lim_z:.2f}")

        # 6. 【核心主角】线圈导电截面 (左/右对称实体)
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

        border_coil = QColor("#DC2626") if (is_dfm_active and not all_pass) else QColor("#C2410C")

        for c_rect, c_dir in [(rect_l_coil, "out"), (rect_r_coil, "in")]:
            painter.setPen(QPen(border_coil, 1.5))
            painter.setBrush(QBrush(grad_coil))
            painter.drawRoundedRect(c_rect, 2, 2)

            # 微观排线层理指示线 (细横线)
            layers_count = min(18, max(2, self.inputs.axial_turns))
            if layers_count > 1 and h_coil_px > 12:
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

        # ISO 5459 基准特征符号 [ A ] (置于左外侧安全区域)
        x_datum = max(x_base_left + 14, x_l_coil - 32)
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
        painter.setPen(QColor("#1E293B"))
        painter.drawText(rect_datum_box, Qt.AlignmentFlag.AlignCenter, "A")

        # 7. 超差干涉红色半透明遮罩与警示 (仅在启用 DFM 卡控时触发)
        if is_dfm_active:
            if not z_pass and y_coil_top < y_lim_top:
                h_over_px = y_lim_top - y_coil_top
                for c_rect in [rect_l_coil, rect_r_coil]:
                    r_over = QRectF(c_rect.left(), y_coil_top, c_rect.width(), h_over_px)
                    painter.fillRect(r_over, QColor(239, 68, 68, 160))
                    painter.setPen(QPen(QColor("#FFFFFF"), 1, Qt.PenStyle.DashLine))
                    painter.drawRect(r_over)

            if not dim_pass:
                if x_l_coil < x_lim_left:
                    w_over = x_lim_left - x_l_coil
                    r_l_over = QRectF(x_l_coil, y_coil_top, w_over, h_coil_px)
                    painter.fillRect(r_l_over, QColor(239, 68, 68, 160))
                if rect_r_coil.right() > rect_dfm_box.right():
                    w_over = rect_r_coil.right() - rect_dfm_box.right()
                    r_r_over = QRectF(rect_dfm_box.right(), y_coil_top, w_over, h_coil_px)
                    painter.fillRect(r_r_over, QColor(239, 68, 68, 160))

        # =========================================================================
        # 8. 【核心】严格遵循 ISO 129 标准工程尺寸标注 (Dimensioning & Tolerancing)
        # =========================================================================
        pen_iso_dim = QPen(QColor("#0369A1"), 1.2)
        pen_iso_ext = QPen(QColor("#64748B"), 1.0)
        brush_iso_arrow = QBrush(QColor("#0369A1"))
        font_dim = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font_dim)

        # 8.1 内孔内径 ID / 内宽 / 内长 (挪至线圈底面基准线下方，垂直延伸界线引下，彻底避免遮挡线圈实体)
        x_in_l = rect_l_coil.right()
        x_in_r = rect_r_coil.left()

        painter.setPen(pen_iso_ext)
        painter.drawLine(int(x_in_l), int(base_y + 1), int(x_in_l), int(y_dim_in + 4))
        painter.drawLine(int(x_in_r), int(base_y + 1), int(x_in_r), int(y_dim_in + 4))

        painter.setPen(pen_iso_dim)
        painter.drawLine(int(x_in_l), int(y_dim_in), int(x_in_r), int(y_dim_in))

        # 闭合实心箭头
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(brush_iso_arrow)
        draw_iso_arrow(painter, x_in_l, y_dim_in, -1.0, 0.0, 6.0, 2.2)
        draw_iso_arrow(painter, x_in_r, y_dim_in, 1.0, 0.0, 6.0, 2.2)

        # 尺寸文字 (置于尺寸线上方，轻量白色底色)
        if c_type == CoilType.CIRCULAR:
            text_in = f"⌀ {in_dim:.2f} mm"
        elif c_type == CoilType.OCTAGONAL:
            text_in = f"{dim_in_name} = {in_dim:.2f} mm"
        else:
            text_in = f"w ({dim_in_name}) = {in_dim:.2f} mm"

        metrics_in = painter.fontMetrics()
        tw_in = metrics_in.horizontalAdvance(text_in)
        th_in = metrics_in.height()
        rect_text_in_bg = QRectF(cx - tw_in / 2.0 - 4, y_dim_in - th_in - 1, tw_in + 8, th_in)
        painter.fillRect(rect_text_in_bg, QColor(255, 255, 255, 230))
        painter.setPen(QColor("#0369A1"))
        painter.drawText(rect_text_in_bg, Qt.AlignmentFlag.AlignCenter, text_in)

        # 8.2 单边壁厚 E 标注 (在左侧线圈顶部上方，垂直延伸界线 + 实心箭头)
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

        text_t = f"t (E)={e_env:.3f}"
        painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        painter.setPen(QColor("#C2410C"))
        tw_t = painter.fontMetrics().horizontalAdvance(text_t)
        painter.drawText(QRectF(rect_l_coil.center().x() - tw_t / 2.0, y_dim_t - 11, tw_t, 11), Qt.AlignmentFlag.AlignCenter, text_t)

        # 8.3 高度 F 标注 (在右侧，从顶面和底面引出水平尺寸界线)
        x_dim_f = rect_r_coil.right() + 24.0
        painter.setPen(pen_iso_ext)
        painter.drawLine(int(rect_r_coil.right() + 2), int(y_coil_top), int(x_dim_f + 5), int(y_coil_top))
        painter.drawLine(int(rect_r_coil.right() + 2), int(base_y), int(x_dim_f + 5), int(base_y))

        painter.setPen(QPen(QColor("#C2410C"), 1.2))
        painter.drawLine(int(x_dim_f), int(y_coil_top), int(x_dim_f), int(base_y))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#C2410C")))
        draw_iso_arrow(painter, x_dim_f, y_coil_top, 0.0, -1.0, 7.0, 2.4)
        draw_iso_arrow(painter, x_dim_f, base_y, 0.0, 1.0, 7.0, 2.4)

        text_f = f"H (F) = {f_thk:.3f} mm"
        painter.setFont(font_dim)
        painter.setPen(QColor("#C2410C"))
        painter.drawText(int(x_dim_f + 6), int((y_coil_top + base_y) / 2.0 + 4), text_f)

        # 8.4 外廓 OD / OW / OL 尺寸线 (ISO 129 标准界线垂直引下 + 闭合实心箭头)
        x_out_l = rect_l_coil.left()
        x_out_r = rect_r_coil.right()

        painter.setPen(pen_iso_ext)
        painter.drawLine(int(x_out_l), int(base_y + 1), int(x_out_l), int(y_dim_out + 5))
        painter.drawLine(int(x_out_r), int(base_y + 1), int(x_out_r), int(y_dim_out + 5))

        painter.setPen(pen_iso_dim)
        painter.drawLine(int(x_out_l), int(y_dim_out), int(x_out_r), int(y_dim_out))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(brush_iso_arrow)
        draw_iso_arrow(painter, x_out_l, y_dim_out, -1.0, 0.0, 7.0, 2.4)
        draw_iso_arrow(painter, x_out_r, y_dim_out, 1.0, 0.0, 7.0, 2.4)

        if c_type == CoilType.CIRCULAR:
            text_out = f"⌀ {out_dim:.3f} mm"
        elif c_type == CoilType.OCTAGONAL:
            text_out = f"{dim_out_name} = {out_dim:.3f} mm"
        else:
            text_out = f"W ({dim_out_name}) = {out_dim:.3f} mm"

        tw_out = metrics_in.horizontalAdvance(text_out)
        rect_text_out_bg = QRectF(cx - tw_out / 2.0 - 4, y_dim_out - th_in - 2, tw_out + 8, th_in)
        painter.fillRect(rect_text_out_bg, QColor(255, 255, 255, 235))
        painter.setPen(QColor("#0F172A"))
        painter.setFont(font_dim)
        painter.drawText(rect_text_out_bg, Qt.AlignmentFlag.AlignCenter, text_out)

        # 9. 状态指示胶囊 (Status Capsule) - 仅在高度充裕时独立悬浮，与上下图元严格保持间距
        if show_floating_badge:
            if not is_dfm_active:
                badge_text = "ℹ DFM Limits Off (Free Parameter Mode: Optimize R20 & Turns)" if is_en else "ℹ DFM 模具卡限已关闭 (自由仿真设计模式: 专注于电阻与匝数寻优)"
                b_color = QColor("#0284C7")
                bg_color = QColor(240, 249, 255, 240)
            elif all_pass:
                badge_text = (f"✓ DFM Clearance Passed (Z-Margin ΔZ: +{delta_z:.3f} mm  |  Lateral Δ: +{delta_dim:.3f} mm)" if is_en else f"✓ DFM 空间合格 (Z 向余量 ΔZ: +{delta_z:.3f} mm  |  侧向余量 Δ: +{delta_dim:.3f} mm)")
                b_color = QColor("#059669")
                bg_color = QColor(240, 253, 244, 240)
            elif not z_pass and not dim_pass:
                badge_text = (f"🚨 Dual-Axis Interference! (Z Over {abs(delta_z):.3f} mm | Lateral Over {abs(delta_dim):.3f} mm)" if is_en else f"🚨 双向严重超差干涉! (Z向超出 {abs(delta_z):.3f} mm | 侧向超出 {abs(delta_dim):.3f} mm)")
                b_color = QColor("#DC2626")
                bg_color = QColor(254, 242, 242, 240)
            elif not z_pass:
                badge_text = (f"🚨 Z-Height Exceeded: H {f_thk:.3f} mm > Max_Z {lim_z:.2f} mm (Over {abs(delta_z):.3f} mm)" if is_en else f"🚨 Z 向超差报警: 线圈高 {f_thk:.3f} mm > Max_Z {lim_z:.2f} mm (超出 {abs(delta_z):.3f} mm)")
                b_color = QColor("#DC2626")
                bg_color = QColor(254, 242, 242, 240)
            else:
                badge_text = (f"🚨 Lateral Exceeded: {dim_out_name} {out_dim:.3f} mm > {dim_lim_name} {lim_dim:.2f} mm (Over {abs(delta_dim):.3f} mm)" if is_en else f"🚨 侧向超差报警: 线圈 {dim_out_name} {out_dim:.3f} mm > {dim_lim_name} {lim_dim:.2f} mm (超出 {abs(delta_dim):.3f} mm)")
                b_color = QColor("#DC2626")
                bg_color = QColor(254, 242, 242, 240)

            painter.setPen(QPen(b_color, 1.2))
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(rect_badge, 3, 3)
            painter.setPen(b_color)
            painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Bold))
            painter.drawText(rect_badge, Qt.AlignmentFlag.AlignCenter, badge_text)

        # 10. 底部专属卡片信息面板 (带高质感浅灰底框，独立封装于底边，100% 杜绝与上方尺寸线重合)
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.setBrush(QBrush(QColor(248, 250, 252, 245)))
        painter.drawRoundedRect(rect_bottom_card, 4, 4)

        painter.setFont(QFont("Microsoft YaHei", 7))
        painter.setPen(QColor("#475569"))
        if is_dfm_active:
            line1 = (f"Coil Height F: {f_thk:.3f} mm  |  Max_Z: {lim_z:.2f} mm (Margin ΔZ: {delta_z:+.3f} mm)  |  Build E: {e_env:.3f} mm" if is_en else f"线圈成型高度 F: {f_thk:.3f} mm  |  空间限高 Max_Z: {lim_z:.2f} mm (余量 ΔZ: {delta_z:+.3f} mm)  |  成型壁厚 E: {e_env:.3f} mm")
            line2 = (f"Inner Bore: {in_dim:.2f} mm  |  Outer Span: {out_dim:.3f} mm  |  Limit {dim_lim_name}: {lim_dim:.2f} mm (Margin Δ: {delta_dim:+.3f} mm)" if is_en else f"线圈内腔基准: {in_dim:.2f} mm  |  实际外廓: {out_dim:.3f} mm  |  空间上限 {dim_lim_name}: {lim_dim:.2f} mm (余量 Δ: {delta_dim:+.3f} mm)")
        else:
            line1 = (f"[Free Mode] Height F: {f_thk:.3f} mm  |  Build E: {e_env:.3f} mm  |  DFM Check Off" if is_en else f"【自由设计】成型高度 F: {f_thk:.3f} mm  |  壁厚 E: {e_env:.3f} mm  |  DFM 限值检查未开启")
            line2 = (f"Inner Bore: {in_dim:.2f} mm  |  Outer Span: {out_dim:.3f} mm  |  Ref {dim_lim_name}: {lim_dim:.2f} mm" if is_en else f"线圈内腔基准: {in_dim:.2f} mm  |  实际外廓: {out_dim:.3f} mm  |  参考限值 {dim_lim_name}: {lim_dim:.2f} mm")

        painter.drawText(QRectF(10, rect_bottom_card.top() + 3, w - 20, 13), Qt.AlignmentFlag.AlignCenter, line1)
        painter.drawText(QRectF(10, rect_bottom_card.top() + 16, w - 20, 13), Qt.AlignmentFlag.AlignCenter, line2)


# 保持向后兼容类名别名
CoilSectionDFMCanvas = MagnetSectionCanvas


class IsometricCoilCanvas(QWidget):
    """
    3D 空间立体斜视矢量画布 (3D Isometric Space Envelope Canvas)
    以 3D 等轴测投影 (Isometric Projection) 呈现：
    1. 脱胎自粘空心线圈 (Self-bonding Air-core Coil) 的 3D 立体跑道/环形实体与微观漆包线质感
    2. 3D 结构装配空间笼 (DFM 3D Bounding Box: Max_X × Max_Y × Max_Z)
    3. 核心聚焦：重点高亮标注 Y 空间配合 (Max_Y 限宽、线圈实际外宽 OW、单双侧装配余量 ΔY)
    4. X/Z 空间限值与三向全干涉安全校验指示看板
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs = CoilInputs()
        self.outputs = CoilOutputs()
        self.setMinimumSize(280, 200)

    def updateData(self, inputs: CoilInputs, outputs: CoilOutputs):
        self.inputs = inputs
        self.outputs = outputs
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        # 尺寸提取
        il = self.inputs.inner_len
        iw = self.inputs.inner_wid if self.inputs.coil_type == CoilType.RACETRACK else il
        ol = self.outputs.outer_len if self.outputs.outer_len > 0 else il + 1.0
        ow = self.outputs.outer_wid if self.outputs.outer_wid > 0 else iw + 1.0
        f_h = self.outputs.thickness_h if self.outputs.thickness_h > 0 else 0.8

        real_lim_x = self.inputs.max_x_len_limit
        real_lim_y = self.inputs.max_y_wid_limit
        real_lim_z = self.inputs.max_z_h_limit

        lim_x = max(ol, real_lim_x)
        lim_y = max(ow, real_lim_y)
        lim_z = max(f_h, real_lim_z)

        is_dfm_active = getattr(self.inputs, "dfm_enabled", False)
        margin_x_pass = (ol <= real_lim_x + 1e-4) if is_dfm_active else True
        margin_y_pass = (ow <= real_lim_y + 1e-4) if is_dfm_active else True
        margin_z_pass = (f_h <= real_lim_z + 1e-4) if is_dfm_active else True
        all_pass = (margin_x_pass and margin_y_pass and margin_z_pass) if is_dfm_active else True

        # 3D 等轴投影变换参数 (30 度等轴测)
        cos30 = math.cos(math.radians(30))
        sin30 = math.sin(math.radians(30))

        u_span = (lim_x + lim_y) * cos30
        v_span = (lim_x + lim_y) * sin30 + lim_z

        scale_u = (w - 200) / max(0.1, u_span)
        scale_v = (h - 105) / max(0.1, v_span)
        scale = min(scale_u, scale_v)

        # 中心投影原点
        cx = w / 2.0 - 20
        cy = h / 2.0 + (lim_z * scale) / 2.0 + 8

        def project(x_mm: float, y_mm: float, z_mm: float):
            """将 3D 空间坐标 (mm) 投影为 2D 像素坐标 (px)"""
            u = cx + (x_mm - y_mm) * cos30 * scale
            v = cy + (x_mm + y_mm) * sin30 * scale - z_mm * scale
            return QPointF(u, v)

        is_en = i18n.is_english()
        # 1. 标题与状态指示药丸
        painter.setPen(QColor("#0284C7"))
        font_title = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.drawText(14, 22, "3D Isometric View (Y-Space Assembly Cage)" if is_en else "3D 空间立体斜视 (Y-Space 空间装配笼)")

        font_badge = QFont("Microsoft YaHei", 8, QFont.Weight.Bold)
        painter.setFont(font_badge)
        badge_w = 175
        badge_h = 22
        badge_rect = QRectF(w - badge_w - 14, 8, badge_w, badge_h)

        if not is_dfm_active:
            painter.setPen(QPen(QColor("#0284C7"), 1))
            painter.setBrush(QBrush(QColor("#F0F9FF")))
            painter.drawRoundedRect(badge_rect, 11, 11)
            painter.setPen(QColor("#0284C7"))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "ℹ Free Design Mode" if is_en else "ℹ 自由仿真设计模式")
        elif all_pass:
            painter.setPen(QPen(QColor("#10B981"), 1))
            painter.setBrush(QBrush(QColor("#ECFDF5")))
            painter.drawRoundedRect(badge_rect, 11, 11)
            painter.setPen(QColor("#047857"))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "✓ 3D Clearance Pass" if is_en else "✓ 3D 装配全部合规")
        else:
            painter.setPen(QPen(QColor("#EF4444"), 1))
            painter.setBrush(QBrush(QColor("#FEF2F2")))
            painter.drawRoundedRect(badge_rect, 11, 11)
            painter.setPen(QColor("#B91C1C"))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "⚠️ 3D Interference" if is_en else "⚠️ 空间干涉超差")

        # 2. 绘制 3D 空间笼的背向虚线 (Back Edges of Bounding Box)
        lx = real_lim_x
        ly = real_lim_y
        lz = real_lim_z

        pb_0 = project(-lx/2, -ly/2, 0)
        pl_0 = project(-lx/2, +ly/2, 0)
        pr_0 = project(+lx/2, -ly/2, 0)
        pf_0 = project(+lx/2, +ly/2, 0)

        pb_z = project(-lx/2, -ly/2, lz)
        pl_z = project(-lx/2, +ly/2, lz)
        pr_z = project(+lx/2, -ly/2, lz)
        pf_z = project(+lx/2, +ly/2, lz)

        pen_cage_back = QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_cage_back)
        painter.drawLine(pb_0, pl_0)
        painter.drawLine(pb_0, pr_0)
        painter.drawLine(pb_0, pb_z)

        # 3. 绘制 3D 脱胎自粘空心线圈实体
        outer_pts = []  # list of ((x, y), (nx, ny))
        inner_pts = []

        if self.inputs.coil_type == CoilType.CIRCULAR:
            r_out = ol / 2.0
            r_in = il / 2.0
            num_pts = 120
            for i in range(num_pts):
                theta = 2.0 * math.pi * i / num_pts
                ct = math.cos(theta)
                st = math.sin(theta)
                outer_pts.append(((r_out * ct, r_out * st), (ct, st)))
                inner_pts.append(((r_in * ct, r_in * st), (ct, st)))
        elif self.inputs.coil_type == CoilType.OCTAGONAL:
            id1 = max(0.2, self.inputs.oct_id1)
            id2 = max(id1 * 1.02, self.inputs.oct_id2 if self.inputs.oct_id2 > 0 else id1 * 1.14)
            r1 = max(0.01, self.inputs.oct_r1)
            sqrt2 = math.sqrt(2.0)
            if self.inputs.oct_l1 > 0 and self.inputs.oct_l2 > 0:
                l1 = self.inputs.oct_l1
                l2 = self.inputs.oct_l2
            else:
                l1 = max(0.05, sqrt2 * id2 - id1 - 2.0 * (sqrt2 - 1.0) * r1)
                l2 = max(0.05, sqrt2 * id1 - id2 - 2.0 * (sqrt2 - 1.0) * r1)
            e_val = max(0.01, self.outputs.e_env)
            od1 = self.outputs.oct_od1 if self.outputs.oct_od1 > 0 else id1 + 2.0 * e_val
            od2 = self.outputs.oct_od2 if self.outputs.oct_od2 > 0 else id2 + 2.0 * e_val
            inner_pts = generate_octagonal_polygon_points(id1, id2, l1, l2, r1, num_arc_pts=6)
            outer_pts = generate_octagonal_polygon_points(od1, od2, l1, l2, r1 + e_val, num_arc_pts=6)
        elif self.inputs.coil_type == CoilType.ARBITRARY_PERIMETER:
            ref_l = max(1.0, self.inputs.arbitrary_outer_len)
            ref_w = max(1.0, self.inputs.arbitrary_outer_wid)
            e_val = max(0.01, self.outputs.e_env)
            str_half = max(0.0, (ref_l - ref_w) / 2.0)
            rad_out = (ref_w + 2.0 * e_val) / 2.0
            rad_in = ref_w / 2.0
            pts_arc = 24
            pts_str = 10
            for i in range(pts_arc):
                th = -math.pi / 2.0 + math.pi * i / pts_arc
                ct = math.cos(th)
                st = math.sin(th)
                outer_pts.append(((str_half + rad_out * ct, rad_out * st), (ct, st)))
                inner_pts.append(((str_half + rad_in * ct, rad_in * st), (ct, st)))
            for i in range(pts_str):
                frac = i / pts_str
                x_out = str_half - frac * (2.0 * str_half)
                outer_pts.append(((x_out, rad_out), (0.0, 1.0)))
                inner_pts.append(((x_out, rad_in), (0.0, 1.0)))
            for i in range(pts_arc):
                th = math.pi / 2.0 + math.pi * i / pts_arc
                ct = math.cos(th)
                st = math.sin(th)
                outer_pts.append(((-str_half + rad_out * ct, rad_out * st), (ct, st)))
                inner_pts.append(((-str_half + rad_in * ct, rad_in * st), (ct, st)))
            for i in range(pts_str):
                frac = i / pts_str
                x_out = -str_half + frac * (2.0 * str_half)
                outer_pts.append(((x_out, -rad_out), (0.0, -1.0)))
                inner_pts.append(((x_out, -rad_in), (0.0, -1.0)))
        else:
            str_half = max(0.0, (ol - ow) / 2.0)
            rad_out = ow / 2.0
            rad_in = iw / 2.0
            str_in_half = max(0.0, (il - iw) / 2.0)

            pts_arc = 36
            pts_str = 16

            # 1. 右半圆
            for i in range(pts_arc):
                th = -math.pi / 2.0 + math.pi * i / pts_arc
                ct = math.cos(th)
                st = math.sin(th)
                outer_pts.append(((str_half + rad_out * ct, rad_out * st), (ct, st)))
                inner_pts.append(((str_in_half + rad_in * ct, rad_in * st), (ct, st)))

            # 2. 上直段
            for i in range(pts_str):
                frac = i / pts_str
                x_out = str_half - frac * (2.0 * str_half)
                x_in = str_in_half - frac * (2.0 * str_in_half)
                outer_pts.append(((x_out, rad_out), (0.0, 1.0)))
                inner_pts.append(((x_in, rad_in), (0.0, 1.0)))

            # 3. 左半圆
            for i in range(pts_arc):
                th = math.pi / 2.0 + math.pi * i / pts_arc
                ct = math.cos(th)
                st = math.sin(th)
                outer_pts.append(((-str_half + rad_out * ct, rad_out * st), (ct, st)))
                inner_pts.append(((-str_in_half + rad_in * ct, rad_in * st), (ct, st)))

            # 4. 下直段
            for i in range(pts_str):
                frac = i / pts_str
                x_out = -str_half + frac * (2.0 * str_half)
                x_in = -str_in_half + frac * (2.0 * str_in_half)
                outer_pts.append(((x_out, -rad_out), (0.0, -1.0)))
                inner_pts.append(((x_in, -rad_in), (0.0, -1.0)))

        outer_curve_top = [project(p[0][0], p[0][1], f_h) for p in outer_pts]
        outer_curve_bot = [project(p[0][0], p[0][1], 0.0) for p in outer_pts]
        inner_curve_top = [project(p[0][0], p[0][1], f_h) for p in inner_pts]
        inner_curve_bot = [project(p[0][0], p[0][1], 0.0) for p in inner_pts]

        # A. 绘制可见的内孔内壁立面 (朝向观察者的内壁背侧: nx + ny < 0)
        grad_inner = QLinearGradient(pl_0.x(), pl_0.y(), pr_0.x(), pr_0.y())
        grad_inner.setColorAt(0.0, QColor("#7C2D12"))
        grad_inner.setColorAt(0.5, QColor("#9A3412"))
        grad_inner.setColorAt(1.0, QColor("#431407"))

        n_pts_total = len(inner_pts)
        for i in range(n_pts_total):
            i_next = (i + 1) % n_pts_total
            nx = (inner_pts[i][1][0] + inner_pts[i_next][1][0]) / 2.0
            ny = (inner_pts[i][1][1] + inner_pts[i_next][1][1]) / 2.0
            if nx + ny < 0.0:
                quad = QPolygonF([
                    inner_curve_top[i],
                    inner_curve_top[i_next],
                    inner_curve_bot[i_next],
                    inner_curve_bot[i]
                ])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(grad_inner))
                painter.drawPolygon(quad)

        # B. 绘制可见的外侧立面 (朝向观察者的外壁: nx + ny > 0)
        grad_outer = QLinearGradient(pl_0.x(), pl_0.y(), pr_0.x(), pr_0.y())
        grad_outer.setColorAt(0.0, QColor("#C2410C"))
        grad_outer.setColorAt(0.5, QColor("#EA580C"))
        grad_outer.setColorAt(1.0, QColor("#9A3412"))

        for i in range(n_pts_total):
            i_next = (i + 1) % n_pts_total
            nx = (outer_pts[i][1][0] + outer_pts[i_next][1][0]) / 2.0
            ny = (outer_pts[i][1][1] + outer_pts[i_next][1][1]) / 2.0
            if nx + ny > 0.0:
                quad = QPolygonF([
                    outer_curve_top[i],
                    outer_curve_top[i_next],
                    outer_curve_bot[i_next],
                    outer_curve_bot[i]
                ])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(grad_outer))
                painter.drawPolygon(quad)

                if i % 3 == 0:
                    painter.setPen(QPen(QColor(254, 215, 170, 50), 0.8))
                    painter.drawLine(outer_curve_top[i], outer_curve_bot[i])
                    painter.setPen(Qt.PenStyle.NoPen)

        # C. 绘制线圈顶面 (Top Face: z = f_h)
        poly_top_outer = QPolygonF(outer_curve_top)
        poly_top_inner = QPolygonF(inner_curve_top)

        path_top = QPainterPath()
        path_top.addPolygon(poly_top_outer)
        path_top.closeSubpath()

        path_in = QPainterPath()
        path_in.addPolygon(poly_top_inner)
        path_in.closeSubpath()

        path_face = path_top.subtracted(path_in)

        grad_top = QLinearGradient(pl_z.x(), pl_z.y(), pr_z.x(), pr_z.y())
        grad_top.setColorAt(0.0, QColor("#FDBA74"))
        grad_top.setColorAt(0.4, QColor("#FED7AA"))
        grad_top.setColorAt(1.0, QColor("#FB923C"))

        painter.setPen(QPen(QColor("#EA580C"), 1.2))
        painter.setBrush(QBrush(grad_top))
        painter.drawPath(path_face)

        # 4. 绘制 3D 空间笼的前向棱边 (Front Edges of DFM Bounding Box)
        if not is_dfm_active:
            pen_cage_front = QPen(QColor("#CBD5E1"), 1.2, Qt.PenStyle.DashDotLine)
        elif all_pass:
            pen_cage_front = QPen(QColor("#10B981"), 1.2, Qt.PenStyle.DashDotLine)
        else:
            pen_cage_front = QPen(QColor("#EF4444"), 1.2, Qt.PenStyle.DashDotLine)

        painter.setPen(pen_cage_front)
        painter.drawLine(pl_0, pf_0)
        painter.drawLine(pr_0, pf_0)
        painter.drawLine(pl_0, pl_z)
        painter.drawLine(pr_0, pr_z)
        painter.drawLine(pf_0, pf_z)
        painter.drawLine(pb_z, pl_z)
        painter.drawLine(pb_z, pr_z)
        painter.drawLine(pl_z, pf_z)
        painter.drawLine(pr_z, pf_z)

        # -------------------------------------------------------------
        # 5. 核心：重点突出标注 Y 空间 (Max_Y, OW, ΔY 装配余量)
        # -------------------------------------------------------------
        dy_edge_x = pf_0.x() - pr_0.x()
        dy_edge_y = pf_0.y() - pr_0.y()
        len_y_edge = math.hypot(dy_edge_x, dy_edge_y)
        if len_y_edge > 1e-4:
            norm_y_x = dy_edge_y / len_y_edge
            norm_y_y = -dy_edge_x / len_y_edge
        else:
            norm_y_x, norm_y_y = 0.5, 0.866

        offset_y = 26.0
        pt_y_dim_start = QPointF(pr_0.x() + offset_y * norm_y_x, pr_0.y() + offset_y * norm_y_y)
        pt_y_dim_end = QPointF(pf_0.x() + offset_y * norm_y_x, pf_0.y() + offset_y * norm_y_y)

        # 辅助引线
        painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(pr_0, pt_y_dim_start)
        painter.drawLine(pf_0, pt_y_dim_end)

        # Max_Y 空间尺寸线
        if not is_dfm_active:
            color_y_line = QColor("#0284C7")
        elif margin_y_pass:
            color_y_line = QColor("#059669")
        else:
            color_y_line = QColor("#DC2626")

        pen_y_limit = QPen(color_y_line, 1.8)
        painter.setPen(pen_y_limit)
        painter.drawLine(pt_y_dim_start, pt_y_dim_end)

        tick_len = 5.0
        painter.drawLine(
            QPointF(pt_y_dim_start.x() - tick_len * norm_y_x, pt_y_dim_start.y() - tick_len * norm_y_y),
            QPointF(pt_y_dim_start.x() + tick_len * norm_y_x, pt_y_dim_start.y() + tick_len * norm_y_y)
        )
        painter.drawLine(
            QPointF(pt_y_dim_end.x() - tick_len * norm_y_x, pt_y_dim_end.y() - tick_len * norm_y_y),
            QPointF(pt_y_dim_end.x() + tick_len * norm_y_x, pt_y_dim_end.y() + tick_len * norm_y_y)
        )

        delta_y = real_lim_y - ow
        if not is_dfm_active:
            delta_y_text = f"{delta_y:+.3f} mm"
        elif delta_y >= 0:
            delta_y_text = f"+{delta_y:.3f} mm"
        else:
            delta_y_text = (f"{delta_y:.3f} mm (Over!)" if is_en else f"{delta_y:.3f} mm (超差!)")

        mid_y_dim = QPointF((pt_y_dim_start.x() + pt_y_dim_end.x()) / 2.0, (pt_y_dim_start.y() + pt_y_dim_end.y()) / 2.0)
        font_y_dim = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font_y_dim)
        color_y_txt = QColor("#0284C7") if not is_dfm_active else (QColor("#047857") if margin_y_pass else QColor("#B91C1C"))
        painter.setPen(color_y_txt)
        painter.drawText(
            int(mid_y_dim.x() + 8), int(mid_y_dim.y() + 2), 
            f"Max_Y: {real_lim_y:.2f} mm"
        )
        painter.setPen(QColor("#1D4ED8"))
        painter.drawText(
            int(mid_y_dim.x() + 8), int(mid_y_dim.y() + 16), 
            f"OW: {ow:.3f} (ΔY: {delta_y_text})"
        )

        # 6. X 限长标注 (沿前左底边 pl_0 -> pf_0)
        dx_edge_x = pf_0.x() - pl_0.x()
        dx_edge_y = pf_0.y() - pl_0.y()
        len_x_edge = math.hypot(dx_edge_x, dx_edge_y)
        if len_x_edge > 1e-4:
            norm_x_x = -dx_edge_y / len_x_edge
            norm_x_y = dx_edge_x / len_x_edge
        else:
            norm_x_x, norm_x_y = -0.5, 0.866

        offset_x = 24.0
        pt_x_dim_start = QPointF(pl_0.x() + offset_x * norm_x_x, pl_0.y() + offset_x * norm_x_y)
        pt_x_dim_end = QPointF(pf_0.x() + offset_x * norm_x_x, pf_0.y() + offset_x * norm_x_y)

        painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(pl_0, pt_x_dim_start)
        painter.drawLine(pf_0, pt_x_dim_end)

        color_x_dim = QColor("#0284C7") if not is_dfm_active else (QColor("#059669") if margin_x_pass else QColor("#DC2626"))
        painter.setPen(QPen(color_x_dim, 1.4))
        painter.drawLine(pt_x_dim_start, pt_x_dim_end)

        delta_x = real_lim_x - ol
        mid_x_dim = QPointF((pt_x_dim_start.x() + pt_x_dim_end.x()) / 2.0, (pt_x_dim_start.y() + pt_x_dim_end.y()) / 2.0)
        font_sub_dim = QFont("Consolas", 7, QFont.Weight.Bold)
        painter.setFont(font_sub_dim)
        painter.setPen(color_x_dim)
        painter.drawText(
            int(mid_x_dim.x() - 110), int(mid_x_dim.y() + 10), 
            (f"Max_X: {real_lim_x:.2f} (OL: {ol:.3f}, ΔX: {delta_x:+.3f})" if is_en else f"X限长: {real_lim_x:.2f} (OL: {ol:.3f}, ΔX: {delta_x:+.3f})")
        )

        # 7. Z 限高标注 (沿右侧立柱 pr_0 -> pr_z)
        delta_z = real_lim_z - f_h
        color_z_dim = QColor("#0284C7") if not is_dfm_active else (QColor("#059669") if margin_z_pass else QColor("#DC2626"))
        painter.setPen(QPen(color_z_dim, 1.2))
        z_label_x = pr_0.x() + 8
        z_label_y = (pr_0.y() + pr_z.y()) / 2.0 + 4
        painter.drawText(
            int(z_label_x), int(z_label_y), 
            (f"Max_Z: {real_lim_z:.2f} (F: {f_h:.3f}, ΔZ: {delta_z:+.3f})" if is_en else f"Z限高: {real_lim_z:.2f} (F: {f_h:.3f}, ΔZ: {delta_z:+.3f})")
        )

        # 8. 左下角专属 Y 空间与三维装配全景看板
        card_w = 260
        card_h = 48
        card_x = 14
        card_y = h - card_h - 12

        if not is_dfm_active:
            card_pen = QPen(QColor("#BAE6FD"), 1.2)
            card_brush = QBrush(QColor("#F0F9FF"))
            card_title_color = QColor("#0284C7")
            card_title = "★ Y-Space Fit Reference (Free Mode)" if is_en else "★ Y 空间配合参考 (自由模式)"
            delta_color = QColor("#0284C7")
        elif margin_y_pass:
            card_pen = QPen(QColor("#059669"), 1.2)
            card_brush = QBrush(QColor("#F0FDF4"))
            card_title_color = QColor("#065F46")
            card_title = "★ Y-Space Clearance Check (Passed)" if is_en else "★ Y 空间装配校验 (宽向配合聚焦)"
            delta_color = QColor("#047857")
        else:
            card_pen = QPen(QColor("#EF4444"), 1.2)
            card_brush = QBrush(QColor("#FEF2F2"))
            card_title_color = QColor("#991B1B")
            card_title = "★ Y-Space Clearance Check (Failed)" if is_en else "★ Y 空间装配校验 (宽向配合聚焦)"
            delta_color = QColor("#B91C1C")

        painter.setPen(card_pen)
        painter.setBrush(card_brush)
        painter.drawRoundedRect(QRectF(card_x, card_y, card_w, card_h), 6, 6)

        painter.setPen(card_title_color)
        font_card = QFont("Microsoft YaHei", 8, QFont.Weight.Bold)
        painter.setFont(font_card)
        painter.drawText(
            card_x + 8, card_y + 16, 
            card_title
        )
        font_card_code = QFont("Consolas", 8)
        painter.setFont(font_card_code)
        painter.setPen(QColor("#1E293B"))
        painter.drawText(
            card_x + 8, card_y + 31, 
            f"Max_Y: {real_lim_y:.2f} mm  |  Coil OW: {ow:.3f} mm" if is_en else f"Max_Y: {real_lim_y:.2f} mm  |  线圈 OW: {ow:.3f} mm"
        )
        painter.setPen(delta_color)
        painter.drawText(
            card_x + 8, card_y + 44, 
            f"Margin ΔY: {delta_y_text} (Per Side {(delta_y/2):.3f} mm)" if is_en else f"装配裕量 ΔY: {delta_y_text} (单边留隙 {(delta_y/2):.3f} mm)"
        )


class CoilDualCanvasWidget(QFrame):
    """双核矢量画布组合容器 (集成微观剖面 + 跑道俯视 + 磁钢装配 + 3D等轴空间斜视)"""

    adaptiveToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CoilDualCanvasWidget")
        self.setStyleSheet("""
            QFrame#CoilDualCanvasWidget {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 左：微观排线截面画布 (支持 Z-X 长向、Z-Y 宽向与单侧放大)
        self.micro_canvas = MicroPackingCanvas(self)
        layout.addWidget(self.micro_canvas, 1)

        # 右：选项卡三重宏观与立体孪生
        self.tab_macro = QTabWidget(self)
        self.racetrack_canvas = MacroRacetrackCanvas(self)
        self.magnet_canvas = MagnetSectionCanvas(self)
        self.isometric_canvas = IsometricCoilCanvas(self)

        self.tab_macro.addTab(self.racetrack_canvas, "2D 轮廓外廓 (X-Y)")
        self.tab_macro.addTab(self.magnet_canvas, "2D 截面与限高 (DFM)")
        self.tab_macro.addTab(self.isometric_canvas, "3D 空间斜视 (Y-Space)")

        layout.addWidget(self.tab_macro, 1)

    def retranslate_ui(self):
        """动态多语言重载选项卡标题与全部矢量画布重绘"""
        from src.core.i18n import t
        is_circ = getattr(self, "_last_is_circ", False)
        if is_circ:
            self.tab_macro.setTabText(0, t("tab_2d_circular", "2D 外径轮廓 (X-Y)"))
        else:
            self.tab_macro.setTabText(0, t("tab_2d_contour", "2D 跑道外廓 (X-Y)"))
        self.tab_macro.setTabText(1, t("tab_2d_section", "2D 截面与限高 (DFM)"))
        self.tab_macro.setTabText(2, t("tab_3d_isometric", "3D 空间斜视 (Y-Space)"))
        self.micro_canvas.update()
        self.racetrack_canvas.update()
        self.magnet_canvas.update()
        self.isometric_canvas.update()

    def updateCoil(self, inputs: CoilInputs, outputs: CoilOutputs):
        # 动态更新 Tab 0 标题
        is_circ = (inputs.coil_type == CoilType.CIRCULAR)
        self._last_is_circ = is_circ
        from src.core.i18n import t
        if is_circ:
            self.tab_macro.setTabText(0, t("tab_2d_circular", "2D 外径轮廓 (X-Y)"))
        else:
            self.tab_macro.setTabText(0, t("tab_2d_contour", "2D 跑道外廓 (X-Y)"))

        self.micro_canvas.updateData(inputs, outputs)
        self.racetrack_canvas.updateData(inputs, outputs)
        self.magnet_canvas.updateData(inputs, outputs)
        self.isometric_canvas.updateData(inputs, outputs)
