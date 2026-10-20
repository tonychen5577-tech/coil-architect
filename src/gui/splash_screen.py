"""
=============================================================================
Module: src.gui.splash_screen
Description: Coil-Architect Pro 现代工业级 SolidWorks 风格启动闪屏 (16:9 纯净测控美学)
融入 ANSV 微型执行器与精密传动电磁线圈多物理场仿真工作站品牌标识、官方超链接与拟态电磁线圈视窗
=============================================================================
"""

import sys
import math
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl, QPointF, QRectF
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QLinearGradient,
    QPen, QBrush, QPixmap, QDesktopServices, QPolygonF
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGraphicsDropShadowEffect, QApplication, QPushButton
)

from src.version import (
    APP_NAME, APP_TITLE, APP_VERSION, APP_BUILD, APP_AUTHOR, OFFICIAL_URL,
    PLATFORM_NAME, PLATFORM_NAME_EN, PLATFORM_FULL_TITLE, WECHAT_OFFICIAL_ACCOUNT
)
from src.gui.icon_helper import get_app_icon_pixmap


class CoilViewportWidget(QWidget):
    """
    电磁线圈与磁通多物理场拟态工程视窗
    采用 3D 等轴测 (Isometric) 金属质感电磁音圈与磁通多物理场高保真工程渲染
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(170)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

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

        # 中心 CAD 坐标准星基准
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

        # 跑道闭合轮廓生成
        def get_full_racetrack(r_val, n_arc=36, n_str=24):
            pts = []
            for i in range(n_str):
                t = i / float(n_str)
                pts.append((-L_straight + 2.0 * L_straight * t, r_val))
            for i in range(n_arc):
                ang = math.pi / 2.0 - math.pi * (i / float(n_arc))
                pts.append((L_straight + r_val * math.cos(ang), r_val * math.sin(ang)))
            for i in range(n_str):
                t = i / float(n_str)
                pts.append((L_straight - 2.0 * L_straight * t, -r_val))
            for i in range(n_arc + 1):
                ang = -math.pi / 2.0 - math.pi * (i / float(n_arc))
                pts.append((-L_straight + r_val * math.cos(ang), r_val * math.sin(ang)))
            return pts

        def get_front_racetrack_wall(r_val, n_arc=32, n_str=32):
            pts = []
            ang_left_start = -math.pi - math.radians(20)
            ang_left_end = -math.pi / 2.0
            for i in range(n_arc):
                ang = ang_left_start + (ang_left_end - ang_left_start) * (i / float(n_arc))
                pts.append((-L_straight + r_val * math.cos(ang), -r_val * math.sin(ang)))
            for i in range(n_str):
                t = i / float(n_str)
                pts.append((-L_straight + 2.0 * L_straight * t, r_val))
            ang_right_start = math.pi / 2.0
            ang_right_end = math.radians(10)
            for i in range(n_arc + 1):
                ang = ang_right_start + (ang_right_end - ang_right_start) * (i / float(n_arc))
                pts.append((L_straight + r_val * math.cos(ang), r_val * math.sin(ang)))
            return pts

        pts_outer_full = get_full_racetrack(R_out, 36, 24)
        pts_inner_full = get_full_racetrack(R_in, 36, 24)
        pts_front_wall = get_front_racetrack_wall(R_out, 32, 32)

        # 3. 底部接触投影阴影
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

        # 5. 立体内孔内壁 (深色景深)
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

        # 侧壁各层漆包线同数密排线纹
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
        grad_top.setColorAt(0.55, QColor("#FEF08A"))
        grad_top.setColorAt(0.75, QColor("#D97706"))
        grad_top.setColorAt(1.0, QColor("#78350F"))

        painter.setPen(QPen(QColor("#78350F"), 1.2))
        painter.setBrush(QBrush(grad_top))
        painter.drawPath(coil_top_ring)

        # 顶部同心密排线纹
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 140), 0.8))
        for r_layer in range(1, 6):
            r_curr = R_in + (R_out - R_in) * (r_layer / 6.0)
            pts_layer_all = get_full_racetrack(r_curr, 28, 20)
            p_ring = QPolygonF([project_3d(x, y_top_coil, z) for x, z in pts_layer_all])
            painter.drawPolyline(p_ring)

        # 8. 引出引脚端子 (Lead Terminal Pins)
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

            painter.setPen(QPen(QColor(56, 189, 248, 50), 3.0))
            painter.drawPath(path_flux_front)
            painter.setPen(QPen(QColor("#0284C7"), 1.2))
            painter.drawPath(path_flux_front)

            p_dot = path_flux_front.pointAtPercent(0.55)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#38BDF8")))
            painter.drawEllipse(p_dot, 2.0, 2.0)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # 10. 专业工业 HUD 视标与工程元数据
        font_hud = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font_hud)

        painter.setPen(QColor("#0369A1"))
        painter.drawText(14, 20, "MODEL: 3D Axonometric Precision Voice Coil (HCP Winding)")
        painter.setPen(QColor("#64748B"))
        painter.drawText(14, 34, "PHYSICS: Coupled Electromagnetic B-Field & Joule Heating")

        painter.setPen(QColor("#059669"))
        painter.drawText(w - 180, 20, "✔ ISO 129 COMPLIANT")
        painter.setPen(QColor("#64748B"))
        painter.drawText(w - 180, 34, "MESH: 48,200 HEXA ELEMENTS")

        painter.setPen(QColor("#94A3B8"))
        painter.drawText(14, h - 12, "Z=0 DATUM [A]  |  ANSV DUAL-CORE SOLVER ENGINE  |  SCALE 1:1")

        pill_rect = QRectF(w - 145, h - 26, 132, 18)
        painter.setPen(QPen(QColor("#BAE6FD"), 1))
        painter.setBrush(QBrush(QColor("#F0F9FF")))
        painter.drawRoundedRect(pill_rect, 9, 9)
        painter.setPen(QColor("#0284C7"))
        font_pill = QFont("Consolas", 7, QFont.Weight.Bold)
        painter.setFont(font_pill)
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, "● SIMULATION READY")


class SplashScreen(QWidget):
    """
    16:9 SolidWorks 工业测控风格启动闪屏：
    - 0.1 秒秒级弹出，与主界面纯白高精工业调性 100% 呼应；
    - 16:9 黄金宽屏比例 (672x378)；
    - 官方网址提供标准超链接 (点击打开 ansv.net)；
    - 底部包含标准工业版权信息与步进式进度条。
    """

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(672, 378)

        # 居中屏幕
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

        self._current_progress = 0
        self._current_message = "正在初始化系统核心..."
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 主卡片画板 (纯白底色 + 浅蓝灰精细边框)
        self.card_widget = QWidget(self)
        self.card_widget.setObjectName("swSplashCard")
        self.card_widget.setStyleSheet("""
            #swSplashCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        # 优雅工业柔和阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(15, 23, 42, 50))
        shadow.setOffset(0, 6)
        self.card_widget.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card_widget)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        # 1. 顶部 Header (左侧高清图标+大标题，右侧官方可点击网址方框)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel()
        icon_pix = get_app_icon_pixmap(44)
        if not icon_pix.isNull():
            icon_label.setPixmap(icon_pix)
        header_layout.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        lbl_app_name = QLabel(f"<span style='color: #0284C7; font-weight: 800;'>ANSV</span> 微型执行器与精密传动仿真验证平台 <span style='font-size: 11px; color: #0284C7; font-weight: 600;'>{APP_VERSION}</span>")
        lbl_app_name.setTextFormat(Qt.TextFormat.RichText)
        lbl_app_name.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A; letter-spacing: 0.2px;")
        title_box.addWidget(lbl_app_name)

        lbl_sub = QLabel("Actuator Numerical Simulation & Validation | 电磁线圈多物理场工作站 (Coil-Architect Pro)")
        lbl_sub.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        title_box.addWidget(lbl_sub)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # 官方网址跳转按钮 (带悬停微动与外链手势)
        self.url_btn = QPushButton("ansv.net ↗")
        self.url_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.url_btn.setToolTip("访问官方技术门户: ansv.net")
        self.url_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                color: #0284C7;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border: 1px solid #0284C7;
                color: #0369A1;
            }
            QPushButton:pressed {
                background-color: #BAE6FD;
            }
        """)
        self.url_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_URL)))
        header_layout.addWidget(self.url_btn, 0, Qt.AlignmentFlag.AlignTop)

        card_layout.addLayout(header_layout)

        # 2. 中间拟态电磁线圈多物理场工程视窗
        self.viewport = CoilViewportWidget(self)
        card_layout.addWidget(self.viewport)

        # 3. 底部进度条与状态文字
        bottom_box = QVBoxLayout()
        bottom_box.setSpacing(4)

        status_line = QHBoxLayout()
        self.msg_label = QLabel(self._current_message)
        self.msg_label.setStyleSheet("font-size: 11px; color: #334155; font-weight: 600;")
        status_line.addWidget(self.msg_label)

        status_line.addStretch()

        self.percent_label = QLabel(f"{self._current_progress}%")
        self.percent_label.setStyleSheet("font-size: 11px; color: #0284C7; font-weight: 700; font-family: Consolas;")
        status_line.addWidget(self.percent_label)

        bottom_box.addLayout(status_line)

        # 科技天蓝高对比进度条
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(self._current_progress)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setFixedHeight(5)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0284C7;
                border-radius: 2px;
            }
        """)
        bottom_box.addWidget(self.prog_bar)

        # 底部版权留痕行
        copy_line = QHBoxLayout()
        lbl_copy_left = QLabel(f"Core Engine: Yaming.Chen | Build: {APP_BUILD}")
        lbl_copy_left.setStyleSheet("font-size: 10px; color: #94A3B8;")
        copy_line.addWidget(lbl_copy_left)

        copy_line.addStretch()

        lbl_copy_right = QLabel(APP_AUTHOR)
        lbl_copy_right.setStyleSheet("font-size: 10px; color: #94A3B8;")
        copy_line.addWidget(lbl_copy_right)

        bottom_box.addLayout(copy_line)
        card_layout.addLayout(bottom_box)

        main_layout.addWidget(self.card_widget)

    def update_progress(self, percent: int, message: str):
        """步进式更新进度条与状态文字，并强制刷新界面响应"""
        self._current_progress = max(0, min(100, int(percent)))
        self._current_message = message
        self.prog_bar.setValue(self._current_progress)
        self.msg_label.setText(self._current_message)
        self.percent_label.setText(f"{self._current_progress}%")
        QApplication.processEvents()

    def finish_and_show(self, window):
        """平滑收起闪屏并展开主窗口"""
        self.update_progress(100, "就绪，正在开启多物理场仿真工作台...")
        window.show()
        self.close()
