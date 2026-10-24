"""
Coil-Architect Pro - Scheme Comparison Drawer Widget
底部可折叠方案比对抽屉模块：
1. 纯手动固化方案：点击 [📌 固化当前方案] 保存当前参数与仿真结果快照
2. 实时比对：第一列为当前实时 Live 状态，后续列为各固化方案，直观展示输入与输出差异
3. 基准锚定 (Baseline)：任选基准方案，其他方案自动计算并标出差异量 Δ (+/-)
4. 一键还原：点击任一方案下方的 [⏪ 还原] 瞬间将全界面参数恢复到该方案
5. 报表导出：一键复制 TSV 格式对比表至剪贴板，或导出为 UTF-8 CSV
"""

import copy
import csv
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget,
    QInputDialog, QFileDialog, QApplication, QSizePolicy, QMessageBox,
    QAbstractItemView, QLineEdit, QDialog
)

from ...core.models import CoilInputs, CoilOutputs, CoilType, WindingMode


@dataclass
class SchemeSnapshot:
    """单一方案快照"""
    name: str
    created_at: str
    inputs: CoilInputs
    outputs: CoilOutputs
    is_baseline: bool = False


class ComparisonTable(QTableWidget):
    """支持顺滑滚轮纵向与横向滚动的方案矩阵表格"""

    def wheelEvent(self, event):
        delta_y = event.angleDelta().y()
        delta_x = event.angleDelta().x()

        # 1. 如果用户按住 Shift 键，或者触控板发出横向滚动信号 -> 优先横向滚动
        if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) or (abs(delta_x) > abs(delta_y) and delta_x != 0):
            scroll_val = delta_x if abs(delta_x) > abs(delta_y) else delta_y
            h_bar = self.horizontalScrollBar()
            if h_bar and h_bar.maximum() > 0:
                step = 35 if scroll_val > 0 else -35
                h_bar.setValue(h_bar.value() - step)
                event.accept()
                return

        # 2. 正常竖向滚轮 -> 平滑滚动行
        v_bar = self.verticalScrollBar()
        if v_bar and v_bar.maximum() > 0:
            step = 28 if delta_y > 0 else -28
            v_bar.setValue(v_bar.value() - step)
            event.accept()
            return

        # 3. 竖向已无滚动余量时，自动映射为横向滚动方案列
        h_bar = self.horizontalScrollBar()
        if h_bar and h_bar.maximum() > 0:
            step = 35 if delta_y > 0 else -35
            h_bar.setValue(h_bar.value() - step)
            event.accept()
            return

        super().wheelEvent(event)


class ComparisonPopoutWindow(QDialog):
    """
    方案比对矩阵独立大窗口 (Pop-out Mode)
    - 支持任意拖拽边缘缩放调整窗口大小；
    - 拥有标准的标题栏最大化按钮 (一键铺满全屏) 与还原；
    - 拥有独立的任务栏科技图标与专业窗口标题；
    - 顶部集成完整的方案固化、复制、导出及一键嵌入抽屉按钮；
    - 窗口关闭时自动无损恢复为嵌入底部抽屉模式。
    """
    def __init__(self, drawer, parent=None):
        super().__init__(parent)
        self.drawer = drawer
        self.setWindowTitle("📊 线圈多方案比对与工程评审矩阵 - ANSV Coil-Architect Pro")
        from ..icon_helper import get_app_icon
        self.setWindowIcon(get_app_icon())

        # 设置具备最小化、最大化、关闭按钮，独立浮动
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(1200, 700)
        self.setMinimumSize(820, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. 顶部操作工具条
        self.toolbar_frame = QFrame()
        self.toolbar_frame.setObjectName("popoutToolbarFrame")
        self.toolbar_frame.setStyleSheet("""
            QFrame#popoutToolbarFrame {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        tb_layout = QHBoxLayout(self.toolbar_frame)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        tb_layout.setSpacing(8)

        self.lbl_title = QLabel("📊 多方案横向比对与工程评审矩阵")
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #0284C7;")
        tb_layout.addWidget(self.lbl_title)

        self.lbl_pop_count = QLabel(drawer.lbl_count.text() if hasattr(drawer, "lbl_count") else "(已固化 0 组)")
        self.lbl_pop_count.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        tb_layout.addWidget(self.lbl_pop_count)

        tb_layout.addStretch()

        self.btn_cap = QPushButton("📌 固化当前方案")
        btn_cap = self.btn_cap
        btn_cap.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 700;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        btn_cap.clicked.connect(drawer.capture_current_scheme)
        tb_layout.addWidget(btn_cap)

        self.btn_copy = QPushButton("📋 复制对比表")
        btn_copy = self.btn_copy
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #334155;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #F1F5F9; color: #0284C7; border-color: #0284C7; }
        """)
        btn_copy.clicked.connect(drawer.copy_table_to_clipboard)
        tb_layout.addWidget(btn_copy)

        self.btn_excel = QPushButton("📊 导出 Excel")
        btn_excel = self.btn_excel
        btn_excel.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                color: #059669;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #DCFCE7; }
        """)
        btn_excel.clicked.connect(drawer.export_excel)
        tb_layout.addWidget(btn_excel)

        self.btn_export_schemes = QPushButton("💾 导出方案")
        self.btn_export_schemes.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                color: #059669;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #DCFCE7; }
        """)
        self.btn_export_schemes.clicked.connect(drawer.export_schemes_file)
        tb_layout.addWidget(self.btn_export_schemes)

        self.btn_import_schemes = QPushButton("📂 导入方案")
        self.btn_import_schemes.setStyleSheet("""
            QPushButton {
                background-color: #F0F9FF;
                color: #0284C7;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid #BAE6FD;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #E0F2FE; }
        """)
        self.btn_import_schemes.clicked.connect(drawer.import_schemes_file)
        tb_layout.addWidget(self.btn_import_schemes)

        self.btn_clear = QPushButton("🗑 清空")
        btn_clear = self.btn_clear
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #FFF1F2;
                color: #E11D48;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #FECDD3;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: #FFE4E6; }
        """)
        btn_clear.clicked.connect(drawer.clear_all_schemes)
        tb_layout.addWidget(btn_clear)

        tb_layout.addSpacing(10)

        # 嵌入底部抽屉按钮
        self.btn_dock = QPushButton("⇲ 嵌入底部抽屉")
        btn_dock = self.btn_dock
        btn_dock.setToolTip("将本评审矩阵窗口重新嵌入到主工作台底部抽屉")
        btn_dock.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #0F172A;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0284C7;
                border-color: #0284C7;
            }
        """)
        btn_dock.clicked.connect(self.close)
        tb_layout.addWidget(btn_dock)

        layout.addWidget(self.toolbar_frame)

        # 2. 中间承载表格容器
        self.table_container = QWidget()
        self.table_layout = QVBoxLayout(self.table_container)
        self.table_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table_container, 1)
        self.retranslate_ui()

    def retranslate_ui(self):
        from src.core.i18n import i18n, t
        is_en = i18n.is_english()
        self.setWindowTitle(f"{t('dialog_compare_title', '📊 固化方案独立对比与工程评审矩阵')} - ANSV Coil-Architect Pro")
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(t("dialog_compare_title", "📊 固化方案独立对比与工程评审矩阵"))
        if hasattr(self, "lbl_pop_count") and self.drawer and hasattr(self.drawer, "_format_count_text"):
            self.lbl_pop_count.setText(self.drawer._format_count_text())
        if hasattr(self, "btn_cap"):
            self.btn_cap.setText(t("btn_pin_scheme", "📌 固化当前方案"))
            self.btn_cap.setToolTip("Freeze current live parameters & simulation results as a column for side-by-side comparison" if is_en else "将当前正在微调的参数与仿真结果固化为独立方案列，用于横向比对")
        if hasattr(self, "btn_copy"):
            self.btn_copy.setText(t("btn_copy_table", "📋 复制对比表"))
            self.btn_copy.setToolTip("Copy comparison matrix to clipboard (TSV format for Excel/Word)" if is_en else "复制当前所有方案的比对数据至剪贴板 (制表符格式，可直接粘贴到 Excel 或 Word)")
        if hasattr(self, "btn_excel"):
            self.btn_excel.setText(t("btn_export_excel", "📊 导出 Excel"))
            self.btn_excel.setToolTip("Export multi-scheme comparison matrix as a styled Excel workbook (.xlsx)" if is_en else "导出多方案比对表为格式精美的 Excel 工作簿 (.xlsx)")
        if hasattr(self, "btn_csv"):
            self.btn_csv.setText(t("btn_export_csv", "📄 导出 CSV"))
            self.btn_csv.setToolTip("Export multi-scheme comparison matrix as UTF-8 CSV (.csv)" if is_en else "导出多方案比对表为标准 UTF-8 CSV 报表 (.csv)")
        if hasattr(self, "btn_clear"):
            self.btn_clear.setText(t("btn_clear_schemes", "🗑 清空"))
            self.btn_clear.setToolTip("Clear all frozen scheme snapshots" if is_en else "清空所有已固化的方案快照")
        if hasattr(self, "btn_dock"):
            self.btn_dock.setText(t("btn_embed_window", "⇲ 嵌入底部抽屉"))
            self.btn_dock.setToolTip("Dock this matrix window back into the bottom drawer" if is_en else "将本评审矩阵窗口重新嵌入到主工作台底部抽屉")

    def closeEvent(self, event):
        """窗口关闭时自动安全嵌入回抽屉"""
        if self.drawer and getattr(self.drawer, "_is_popped_out", False):
            self.drawer.dock_back()
        super().closeEvent(event)


class ComparisonDrawer(QFrame):
    """底部可折叠方案比对与调参记录抽屉"""

    # 信号通知主窗口还原参数
    restore_requested = pyqtSignal(object)  # 传递 SchemeSnapshot
    status_message = pyqtSignal(str)        # 状态栏提示消息

    ROW_DEFINITIONS = [
        # (行标题, 分组, 字段取值器函数)
        ("绕线拓扑", "input", "_get_topology_str"),
        ("内腔内径/长宽 (mm)", "input", "_get_inner_dims"),
        ("铜线裸径 d (mm)", "input", "_get_bare_dia"),
        ("漆包外径 D (mm)", "input", "_get_max_od"),
        ("径向层数 I (层)", "input", "_get_layers"),
        ("每层匝数 J (匝)", "input", "_get_turns"),
        ("绕线模式", "input", "_get_mode_str"),
        ("张力系数 η", "input", "_get_tension"),
        ("成型总匝数 N (匝)", "output", "_get_total_n"),
        ("外廓长宽/对边 (mm)", "output", "_get_outer_size"),
        ("单边壁厚 E (mm)", "output", "_get_wall_thickness"),
        ("轴向成型厚度 H (mm)", "output", "_get_height"),
        ("20℃直流电阻 R20 (Ω)", "output", "_get_r20"),
        ("等效电感 L (μH)", "output", "_get_inductance"),
        ("纯铜填充率 (%)", "output", "_get_cu_fill"),
        ("DFM 制造公差", "output", "_get_dfm_status"),
        ("方案操作", "action", None),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ComparisonDrawer")
        self.snapshots: List[SchemeSnapshot] = []
        self._curr_inputs: Optional[CoilInputs] = None
        self._curr_outputs: Optional[CoilOutputs] = None
        self._is_expanded = False
        self._is_popped_out = False
        self.popout_window: Optional[ComparisonPopoutWindow] = None

        self.setStyleSheet("""
            #ComparisonDrawer {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
            }
        """)

        main_layout = QVBoxLayout(self)
        self.main_layout = main_layout
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(4)

        # -------------------------------------------------------------
        # 1. 顶部折叠条 / 快捷操作栏 (始终常驻)
        # -------------------------------------------------------------
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 4px;
            }
        """)
        h_layout = QHBoxLayout(self.header_frame)
        h_layout.setContentsMargins(8, 3, 8, 3)
        h_layout.setSpacing(8)

        # 展开/收起切换主按钮
        self.btn_toggle = QPushButton("▶ 📊 方案比对抽屉")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                font-weight: 700;
                color: #0F172A;
                background: transparent;
                border: none;
                text-align: left;
                padding: 2px 4px;
            }
            QPushButton:hover {
                color: #0284C7;
            }
        """)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_expanded)
        h_layout.addWidget(self.btn_toggle)

        # 已固化方案数量标签
        self.lbl_count = QLabel("(已固化 0 组)")
        self.lbl_count.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748B; background: transparent; border: none;")
        h_layout.addWidget(self.lbl_count)

        h_layout.addStretch()

        # 核心固化按钮 (显眼天蓝色，主行动按钮)
        self.btn_capture = QPushButton("📌 固化当前方案")
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 700;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        self.btn_capture.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_capture.setToolTip("将当前正在微调的参数与仿真结果固化为独立方案列，用于横向比对")
        self.btn_capture.clicked.connect(self.capture_current_scheme)
        h_layout.addWidget(self.btn_capture)

        # 复制对比表按钮
        self.btn_copy = QPushButton("📋 复制对比表")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #334155;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0284C7;
                border-color: #0284C7;
            }
        """)
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setToolTip("复制当前所有方案的比对数据至剪贴板 (制表符格式，可直接粘贴到 Excel 或 Word)")
        self.btn_copy.clicked.connect(self.copy_table_to_clipboard)
        h_layout.addWidget(self.btn_copy)

        # 导出 Excel 按钮
        self.btn_export = QPushButton("📊 导出 Excel")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #059669;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #ECFDF5;
                color: #047857;
                border-color: #059669;
            }
        """)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setToolTip("导出多方案比对表为格式精美的 Excel 工作簿 (.xlsx)")
        self.btn_export.clicked.connect(self.export_excel)
        h_layout.addWidget(self.btn_export)

        # 导出方案按钮
        self.btn_export_schemes = QPushButton("💾 导出方案")
        self.btn_export_schemes.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #059669;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #ECFDF5;
                color: #047857;
                border-color: #059669;
            }
        """)
        self.btn_export_schemes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_schemes.setToolTip("将所有已固化的多组对比方案导出为 .ansvschemes 方案归档文件")
        self.btn_export_schemes.clicked.connect(self.export_schemes_file)
        h_layout.addWidget(self.btn_export_schemes)

        # 导入方案按钮
        self.btn_import_schemes = QPushButton("📂 导入方案")
        self.btn_import_schemes.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #0284C7;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid #BAE6FD;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #F0F9FF;
                color: #0369A1;
                border-color: #0284C7;
            }
        """)
        self.btn_import_schemes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_schemes.setToolTip("导入 .ansvschemes 方案归档文件，还原并横向对比历史方案")
        self.btn_import_schemes.clicked.connect(self.import_schemes_file)
        h_layout.addWidget(self.btn_import_schemes)

        # 清空按钮
        self.btn_clear = QPushButton("🗑 清空")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #64748B;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid #E2E8F0;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                color: #DC2626;
                border-color: #FCA5A5;
            }
        """)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setToolTip("清空所有已固化的方案快照")
        self.btn_clear.clicked.connect(self.clear_all_schemes)
        h_layout.addWidget(self.btn_clear)

        # 弹出独立大窗按钮
        self.btn_popout = QPushButton("⛶ 弹出大窗")
        self.btn_popout.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #1D4ED8;
                font-size: 10px;
                font-weight: 700;
                border: 1px solid #BFDBFE;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #DBEAFE;
                border-color: #3B82F6;
            }
        """)
        self.btn_popout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_popout.setToolTip("将方案比对矩阵弹出为独立可缩放窗口，支持全屏最大化与宽屏多方案横向评审")
        self.btn_popout.clicked.connect(self._on_popout_button_clicked)
        h_layout.addWidget(self.btn_popout)

        # 折叠图标按钮
        self.btn_fold = QPushButton("▲ 展开")
        self.btn_fold.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #0284C7;
                font-size: 10px;
                font-weight: 600;
                padding: 2px 4px;
            }
        """)
        self.btn_fold.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fold.clicked.connect(self.toggle_expanded)
        h_layout.addWidget(self.btn_fold)

        main_layout.addWidget(self.header_frame)

        # -------------------------------------------------------------
        # 2. 展开后的横向比对矩阵表格 (默认收起)
        # -------------------------------------------------------------
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 2, 0, 0)
        content_layout.setSpacing(2)

        self.table = ComparisonTable()
        self.table.setRowCount(len(self.ROW_DEFINITIONS))
        self.table.setColumnCount(2)  # 列0: 指标名, 列1: 实时 Live
        self.table.setHorizontalHeaderLabels(["参数 / 指标项目", "实时微调 (Live) ⚡"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setMinimumSectionSize(148)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                gridline-color: #E2E8F0;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                font-size: 11px;
                color: #0F172A;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #334155;
                font-weight: 700;
                font-size: 11px;
                padding: 4px 6px;
                border: 1px solid #E2E8F0;
            }
            QTableWidget::item {
                padding: 3px 6px;
            }
        """)
        self.table.horizontalHeader().sectionDoubleClicked.connect(self._on_header_double_clicked)
        self.table.setMinimumHeight(170)
        self.table.setMaximumHeight(260)

        # 初始化行名称
        self._init_row_headers()

        content_layout.addWidget(self.table)
        main_layout.addWidget(self.content_container)

        # 默认收起
        self.content_container.setVisible(False)

    ROW_I18N = {
        "绕线拓扑": "row_topology",
        "内腔内径/长宽 (mm)": "row_inner_dims",
        "单边壁厚 E (mm)": "row_wall_thickness",
        "铜线裸径 d (mm)": "row_bare_dia",
        "漆包外径 D (mm)": "row_outer_dia",
        "径向层数 I (层)": "row_layers",
        "每层匝数 J (匝)": "row_turns_per_layer",
        "绕线模式": "row_winding_mode",
        "张力系数 η": "row_tension",
        "成型总匝数 N (匝)": "row_total_turns",
        "外廓长宽/对边 (mm)": "row_outer_dims",
        "轴向成型厚度 H (mm)": "row_coil_height",
        "20℃直流电阻 R20 (Ω)": "row_r20",
        "等效电感 L (μH)": "row_inductance",
        "纯铜填充率 (%)": "row_copper_fill",
        "DFM 制造公差": "row_dfm_status",
        "方案操作": "row_action",
    }

    def _format_count_text(self) -> str:
        from src.core.i18n import i18n
        n = len(self.snapshots)
        return f"({n} Frozen)" if i18n.is_english() else f"(已固化 {n} 组)"

    def retranslate_ui(self):
        """动态多语言重载"""
        from src.core.i18n import i18n, t
        is_en = i18n.is_english()
        if getattr(self, "_is_popped_out", False):
            self.btn_toggle.setText("📊 Scheme Matrix Detached [Click to Dock]" if is_en else "📊 方案比对已在独立大窗展开 [点击恢复嵌入]")
            self.btn_popout.setText("⇲ Dock Back" if is_en else "⇲ 恢复嵌入")
        else:
            arrow = "▼ 📊 " if self._is_expanded else "▶ 📊 "
            self.btn_toggle.setText(f"{arrow}{t('drawer_title', '方案比对抽屉')}")
            self.btn_popout.setText(t("btn_popout_window", "⛶ 弹出大窗"))
        self.lbl_count.setText(self._format_count_text())
        self.btn_capture.setText(t("btn_pin_scheme", "📌 固化当前方案"))
        self.btn_capture.setToolTip("Freeze current live parameters & simulation results as a column for side-by-side comparison" if is_en else "将当前正在微调的参数与仿真结果固化为独立方案列，用于横向比对")
        self.btn_copy.setText(t("btn_copy_table", "📋 复制对比表"))
        self.btn_copy.setToolTip("Copy comparison matrix to clipboard (TSV format for Excel/Word)" if is_en else "复制当前所有方案的比对数据至剪贴板 (制表符格式，可直接粘贴到 Excel 或 Word)")
        self.btn_export.setText(t("btn_export_excel", "📊 导出 Excel"))
        self.btn_export.setToolTip("Export multi-scheme comparison matrix as a styled Excel workbook (.xlsx)" if is_en else "导出多方案比对表为格式精美的 Excel 工作簿 (.xlsx)")
        if hasattr(self, "btn_export_schemes"):
            self.btn_export_schemes.setText(t("btn_export_schemes", "💾 导出方案"))
            self.btn_export_schemes.setToolTip("Export all frozen comparison schemes as file (.ansvschemes)" if is_en else "将当前所有已固化方案导出为文件 (.ansvschemes)")
        if hasattr(self, "btn_import_schemes"):
            self.btn_import_schemes.setText(t("btn_import_schemes", "📂 导入方案"))
            self.btn_import_schemes.setToolTip("Import and restore schemes from file (.ansvschemes)" if is_en else "从文件导入并还原多组对比方案 (.ansvschemes)")
        self.btn_clear.setText(t("btn_clear_schemes", "🗑 清空"))
        self.btn_clear.setToolTip("Clear all frozen scheme snapshots" if is_en else "清空所有已固化的方案快照")
        self.btn_popout.setToolTip("Detach scheme comparison matrix into a resizable floating window" if is_en else "将方案比对矩阵弹出为独立可缩放窗口，支持全屏最大化与宽屏多方案横向评审")
        if hasattr(self, "btn_fold"):
            self.btn_fold.setText(t("btn_fold_drawer", "收起 ▼") if self._is_expanded else t("btn_unfold_drawer", "展开 ▲"))
        if self.popout_window:
            self.popout_window.retranslate_ui()
        self._init_row_headers()
        self._rebuild_table_columns()

    def _init_row_headers(self):
        """填充行标签"""
        from src.core.i18n import t
        for row_idx, (title, group, _) in enumerate(self.ROW_DEFINITIONS):
            key = self.ROW_I18N.get(title)
            disp_title = t(key, title) if key else title
            item = QTableWidgetItem(disp_title)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if group == "input":
                item.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
                item.setForeground(QColor("#0369A1"))
            elif group == "output":
                item.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
                item.setForeground(QColor("#0F172A"))
            else:
                item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                item.setForeground(QColor("#475569"))
            self.table.setItem(row_idx, 0, item)

    def _on_popout_button_clicked(self):
        """响应弹出/嵌入按钮点击"""
        if getattr(self, "_is_popped_out", False):
            self.dock_back()
        else:
            self.pop_out()

    def pop_out(self):
        """弹出独立大窗口模式 (支持拉伸缩放、最大化全屏与宽屏多方案评审)"""
        if getattr(self, "_is_popped_out", False):
            if hasattr(self, "popout_window") and self.popout_window:
                self.popout_window.show()
                self.popout_window.raise_()
                self.popout_window.activateWindow()
            return

        self._is_popped_out = True

        # 1. 实例化独立弹窗
        self.popout_window = ComparisonPopoutWindow(self, parent=self.window())

        # 2. 将 table 从 content_container 动态移入 popout_window
        self.table.setParent(self.popout_window.table_container)
        self.popout_window.table_layout.addWidget(self.table)
        self.table.setMinimumHeight(350)
        self.table.setMaximumHeight(16777215)  # 解除 260px 抽屉限高，充满整个弹窗

        # 3. 隐藏抽屉内部内容区，更新抽屉按钮状态
        self.content_container.setVisible(False)
        from src.core.i18n import i18n
        self.btn_popout.setText("⇲ Dock Back" if i18n.is_english() else "⇲ 恢复嵌入")
        self.btn_popout.setStyleSheet("""
            QPushButton {
                background-color: #FEF3C7;
                color: #B45309;
                font-size: 10px;
                font-weight: 700;
                border: 1px solid #FCD34D;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #FDE68A;
            }
        """)
        self.btn_toggle.setText("📊 Scheme Matrix Detached [Click to Dock]" if i18n.is_english() else "📊 方案比对已在独立大窗展开 [点击恢复嵌入]")

        # 4. 显示并激活弹窗
        self.popout_window.show()
        self.popout_window.raise_()
        self.popout_window.activateWindow()
        self.status_message.emit(
            "⛶ Scheme Comparison Matrix detached into a floating window!"
            if i18n.is_english() else
            "⛶ 方案比对矩阵已弹出为独立窗口，可自由调整尺寸或点击右上角最大化全屏评审！"
        )

    def dock_back(self):
        """收回嵌入底部抽屉模式"""
        if not getattr(self, "_is_popped_out", False):
            return

        self._is_popped_out = False

        # 1. 将 table 移回 content_container
        content_layout = self.content_container.layout()
        self.table.setParent(self.content_container)
        content_layout.addWidget(self.table)
        self.table.setMinimumHeight(170)
        self.table.setMaximumHeight(260)  # 恢复抽屉限高

        # 2. 恢复抽屉按钮文本与样式
        from src.core.i18n import t
        self.btn_popout.setText(t("btn_popout_window", "⛶ 弹出大窗"))
        self.btn_popout.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #1D4ED8;
                font-size: 10px;
                font-weight: 700;
                border: 1px solid #BFDBFE;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #DBEAFE;
                border-color: #3B82F6;
            }
        """)

        # 3. 展开抽屉
        self._is_expanded = True
        self.content_container.setVisible(True)
        self.btn_toggle.setText(f"▼ 📊 {t('drawer_title', '方案比对抽屉')}")
        self.btn_fold.setText(t("btn_fold_drawer", "收起 ▼"))

        # 4. 关闭并释放弹窗
        if hasattr(self, "popout_window") and self.popout_window:
            p = self.popout_window
            self.popout_window = None
            p.close()

        from src.core.i18n import i18n
        self.status_message.emit(
            "⇲ Scheme Comparison Matrix docked back into the bottom drawer."
            if i18n.is_english() else
            "⇲ 方案比对矩阵已重新嵌入工作台底部抽屉。"
        )

    def toggle_expanded(self):
        """展开或收起比对抽屉"""
        if getattr(self, "_is_popped_out", False):
            # 若当前正处于独立窗口模式，点击标题恢复嵌入
            self.dock_back()
            return

        self._is_expanded = not self._is_expanded
        self.content_container.setVisible(self._is_expanded)
        from src.core.i18n import t
        arrow = "▼ 📊 " if self._is_expanded else "▶ 📊 "
        self.btn_toggle.setText(f"{arrow}{t('drawer_title', '方案比对抽屉')}")
        self.btn_fold.setText(t("btn_fold_drawer", "▼ 收起") if self._is_expanded else t("btn_unfold_drawer", "▲ 展开"))

    def set_expanded(self, expanded: bool):
        """显式设置展开状态"""
        if self._is_expanded != expanded:
            self.toggle_expanded()

    def update_live(self, inputs: CoilInputs, outputs: CoilOutputs):
        """当主窗口计算产生新结果时，实时刷新第一列 Live 状态"""
        self._curr_inputs = copy.deepcopy(inputs)
        self._curr_outputs = copy.deepcopy(outputs)

        baseline = self._get_baseline_snapshot()
        self._render_column(1, "实时微调 (Live) ⚡", inputs, outputs, baseline, is_live=True)

    def _check_auth(self, action_name: str = "方案比对操作") -> bool:
        """检查授权；未激活时调出激活窗口"""
        win = self.window()
        if win and hasattr(win, "check_authorization_or_prompt"):
            return win.check_authorization_or_prompt(action_name)
        parent = self.parent()
        while parent:
            if hasattr(parent, "check_authorization_or_prompt"):
                return parent.check_authorization_or_prompt(action_name)
            parent = parent.parent()
        return True

    def capture_current_scheme(self):
        """核心行动：固化当前方案快照"""
        if not self._check_auth("固化记录方案快照"):
            return
        from src.core.i18n import i18n
        if self._curr_inputs is None or self._curr_outputs is None:
            self.status_message.emit(
                "⚠ No simulation result available to freeze."
                if i18n.is_english() else
                "⚠ 当前尚无计算结果，无法固化方案"
            )
            return

        scheme_num = len(self.snapshots) + 1
        from src.core.i18n import t
        prefix = t("scheme_prefix", "方案")
        name = f"{prefix} {scheme_num}"
        created_at = datetime.now().strftime("%H:%M:%S")

        # 若是第一组，默认自动设为基线
        is_baseline = (len(self.snapshots) == 0)

        snapshot = SchemeSnapshot(
            name=name,
            created_at=created_at,
            inputs=copy.deepcopy(self._curr_inputs),
            outputs=copy.deepcopy(self._curr_outputs),
            is_baseline=is_baseline
        )
        self.snapshots.append(snapshot)

        # 刷新表格列与表头
        self._rebuild_table_columns()

        # 自动展开抽屉让工程师看到固化结果
        if not self._is_expanded:
            self.set_expanded(True)

        from src.core.i18n import t, i18n
        self.lbl_count.setText(self._format_count_text())
        if getattr(self, "_is_popped_out", False) and hasattr(self, "popout_window") and self.popout_window:
            self.popout_window.lbl_pop_count.setText(self.lbl_count.text())
        self.status_message.emit(
            f"✓ Frozen [{name}]! Click [⏪ Restore] or [★ Set Base] below at any time."
            if i18n.is_english() else
            f"✓ 成功固化 [{name}]！可随时点击下方 [⏪ 还原] 或指定基准方案"
        )

    def _get_baseline_snapshot(self) -> Optional[SchemeSnapshot]:
        for s in self.snapshots:
            if s.is_baseline:
                return s
        return self.snapshots[0] if self.snapshots else None

    def _rebuild_table_columns(self):
        """重新排列表格所有方案列"""
        total_cols = 2 + len(self.snapshots)
        self.table.setColumnCount(total_cols)

        # 设置列标题
        from src.core.i18n import t
        headers = [t("col_metric", "参数 / 指标项目"), t("col_live_tuning", "实时微调 (Live) ⚡")]
        for idx, s in enumerate(self.snapshots):
            disp_name = s.name
            if disp_name.startswith("方案 "):
                disp_name = disp_name.replace("方案 ", f"{t('scheme_prefix', '方案')} ")
            elif disp_name.startswith("Scheme "):
                disp_name = disp_name.replace("Scheme ", f"{t('scheme_prefix', '方案')} ")
            base_badge = f" [{t('col_baseline', '基准 📌').strip('[]')}]" if s.is_baseline else ""
            headers.append(f"{disp_name}{base_badge}\n({s.created_at})")
        self.table.setHorizontalHeaderLabels(headers)

        # 宽度自适应与防截断最小宽度保护 (每列至少176px以完美容纳中英文全部操作按钮)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(1, total_cols):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            hint_w = self.table.sizeHintForColumn(c)
            self.table.setColumnWidth(c, max(176, hint_w))

        baseline = self._get_baseline_snapshot()

        # 重新渲染 Live 列
        if self._curr_inputs and self._curr_outputs:
            self._render_column(1, "实时微调 (Live) ⚡", self._curr_inputs, self._curr_outputs, baseline, is_live=True)

        # 渲染各个已固化方案列
        for idx, s in enumerate(self.snapshots):
            col_idx = 2 + idx
            self._render_column(col_idx, s.name, s.inputs, s.outputs, baseline, is_live=False, snapshot_idx=idx)

        self.lbl_count.setText(self._format_count_text())
        if getattr(self, "_is_popped_out", False) and hasattr(self, "popout_window") and self.popout_window:
            self.popout_window.lbl_pop_count.setText(self._format_count_text())

    def _render_column(self, col_idx: int, col_name: str, inp: CoilInputs, out: CoilOutputs,
                       baseline: Optional[SchemeSnapshot], is_live: bool, snapshot_idx: int = -1):
        """渲染单列中的所有行单元格"""
        base_inp = baseline.inputs if (baseline and not (not is_live and self.snapshots[snapshot_idx].is_baseline)) else None
        base_out = baseline.outputs if (baseline and not (not is_live and self.snapshots[snapshot_idx].is_baseline)) else None

        for row_idx, (title, group, getter_name) in enumerate(self.ROW_DEFINITIONS):
            if getter_name is None:
                # 最后一行为操作按钮 (先清理旧组件防止在(0,0)残留)
                old_w = self.table.cellWidget(row_idx, col_idx)
                if old_w is not None:
                    self.table.removeCellWidget(row_idx, col_idx)
                    old_w.hide()
                    old_w.deleteLater()
                action_widget = self._create_action_widget(is_live, snapshot_idx)
                self.table.setCellWidget(row_idx, col_idx, action_widget)
                continue

            getter_func = getattr(self, getter_name)
            val_str, diff_str, is_improved, is_warn = getter_func(inp, out, base_inp, base_out)

            full_text = val_str
            if diff_str:
                full_text += f" ({diff_str})"

            item = QTableWidgetItem(full_text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 差异视觉着色
            if is_warn:
                item.setBackground(QColor("#FEE2E2"))  # 浅红报警
                item.setForeground(QColor("#DC2626"))
            elif is_improved:
                item.setBackground(QColor("#ECFDF5"))  # 浅绿优化
                item.setForeground(QColor("#059669"))
            elif diff_str and group == "input":
                item.setBackground(QColor("#EFF6FF"))  # 浅蓝表示输入参数有差异
                item.setForeground(QColor("#0284C7"))
            else:
                if is_live:
                    item.setForeground(QColor("#0284C7") if group == "input" else QColor("#0F172A"))
                else:
                    item.setForeground(QColor("#334155"))

            self.table.setItem(row_idx, col_idx, item)

    def _create_action_widget(self, is_live: bool, snapshot_idx: int) -> QWidget:
        """创建单元格底部的操作控制微组件 (按钮固定宽度防截断)"""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(1, 1, 1, 1)
        h.setSpacing(3)
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if is_live:
            from src.core.i18n import t
            btn_save = QPushButton(t("btn_pin_scheme", "📌 固化此方案"))
            btn_save.setMinimumWidth(112)
            btn_save.setStyleSheet("""
                QPushButton {
                    background-color: #E0F2FE;
                    color: #0284C7;
                    font-size: 10px;
                    font-weight: 700;
                    border: 1px solid #BAE6FD;
                    border-radius: 3px;
                    padding: 2px 4px;
                }
                QPushButton:hover {
                    background-color: #0284C7;
                    color: #FFFFFF;
                }
            """)
            btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_save.clicked.connect(self.capture_current_scheme)
            h.addWidget(btn_save)
        else:
            s = self.snapshots[snapshot_idx]

            # 设为基准按钮
            if not s.is_baseline:
                from src.core.i18n import t
                btn_set_base = QPushButton(t("btn_set_baseline", "★ 设为基线"))
                btn_set_base.setMinimumWidth(86)
                btn_set_base.setStyleSheet("""
                    QPushButton {
                        background-color: #F8FAFC;
                        color: #475569;
                        font-size: 10px;
                        font-weight: 600;
                        border: 1px solid #CBD5E1;
                        border-radius: 3px;
                        padding: 1px 2px;
                    }
                    QPushButton:hover {
                        background-color: #F1F5F9;
                        color: #0284C7;
                        border-color: #0284C7;
                    }
                """)
                from src.core.i18n import i18n
                is_en = i18n.is_english()
                btn_set_base.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_set_base.setToolTip("Set this scheme as the comparison baseline" if is_en else "设为此方案为对比基准")
                btn_set_base.clicked.connect(lambda _, idx=snapshot_idx: self._set_as_baseline(idx))
                h.addWidget(btn_set_base)
            else:
                from src.core.i18n import t
                lbl_is_base = QLabel(t("col_baseline", "📌 基准方案"))
                lbl_is_base.setMinimumWidth(78)
                lbl_is_base.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_is_base.setStyleSheet("font-size: 10px; font-weight: 700; color: #059669; padding: 1px;")
                h.addWidget(lbl_is_base)

            # 还原此方案按钮
            from src.core.i18n import t, i18n
            is_en = i18n.is_english()
            btn_restore = QPushButton(t("btn_restore_scheme", "⏪ 还原"))
            btn_restore.setMinimumWidth(62)
            btn_restore.setStyleSheet("""
                QPushButton {
                    background-color: #F0FDF4;
                    color: #16A34A;
                    font-size: 10px;
                    font-weight: 700;
                    border: 1px solid #BBF7D0;
                    border-radius: 3px;
                    padding: 1px 2px;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                    color: #FFFFFF;
                }
            """)
            btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_restore.setToolTip("Restore all input parameters from this scheme" if is_en else "点击一键将左侧所有参数还原为此方案的所有设置")
            btn_restore.clicked.connect(lambda _, snap=s: self._on_restore_clicked(snap))
            h.addWidget(btn_restore)

            # 删除按钮
            btn_del = QPushButton("✕")
            btn_del.setFixedWidth(18)
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94A3B8;
                    font-size: 11px;
                    font-weight: 700;
                    border: none;
                    padding: 1px;
                }
                QPushButton:hover {
                    color: #DC2626;
                }
            """)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setToolTip("Remove this scheme column" if is_en else "移除此方案列")
            btn_del.clicked.connect(lambda _, idx=snapshot_idx: self._delete_scheme(idx))
            h.addWidget(btn_del)

        return w

    def _on_restore_clicked(self, snap: SchemeSnapshot):
        """响应还原方案点击（未激活时拦截弹窗）"""
        if not self._check_auth("Restore Scheme Parameters" if i18n.is_english() else "还原历史方案参数"):
            return
        self.restore_requested.emit(snap)

    def _set_as_baseline(self, target_idx: int):
        """将指定序号的方案设为对比基准"""
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        if not self._check_auth("Set Baseline Scheme" if is_en else "设置基准方案"):
            return
        for i, s in enumerate(self.snapshots):
            s.is_baseline = (i == target_idx)
        self._rebuild_table_columns()
        self.status_message.emit(
            f"📌 Set [{self.snapshots[target_idx].name}] as comparison baseline."
            if is_en else
            f"📌 已将 [{self.snapshots[target_idx].name}] 设为对比基准方案，其他方案将以此计算差异量"
        )

    def _delete_scheme(self, target_idx: int):
        """移除指定方案"""
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        if not self._check_auth("Delete Scheme Snapshot" if is_en else "删除方案快照"):
            return
        deleted = self.snapshots.pop(target_idx)
        # 若删除了基线且还有方案，把第一个设为基线
        if deleted.is_baseline and self.snapshots:
            self.snapshots[0].is_baseline = True
        self._rebuild_table_columns()
        if getattr(self, "_is_popped_out", False) and hasattr(self, "popout_window") and self.popout_window:
            self.popout_window.lbl_pop_count.setText(self._format_count_text())
        self.status_message.emit(
            f"Removed scheme [{deleted.name}]"
            if is_en else
            f"已移除方案 [{deleted.name}]"
        )

    def clear_all_schemes(self):
        """清空所有方案快照"""
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        if not self._check_auth("Clear Comparison Matrix" if is_en else "清空方案对比"):
            return
        if not self.snapshots:
            return
        res = QMessageBox.question(
            self,
            "Confirm Clear" if is_en else "确认清空",
            f"Are you sure you want to clear all {len(self.snapshots)} frozen comparison schemes?"
            if is_en else
            f"确定清空全部 {len(self.snapshots)} 组方案比对数据吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.snapshots.clear()
            self._rebuild_table_columns()
            self.lbl_count.setText(self._format_count_text())
            if getattr(self, "_is_popped_out", False) and hasattr(self, "popout_window") and self.popout_window:
                self.popout_window.lbl_pop_count.setText(self._format_count_text())
            self.status_message.emit("Scheme comparison matrix cleared." if is_en else "方案比对表已清空")

    def _on_header_double_clicked(self, section: int):
        """双击表头重命名方案"""
        if section < 2:
            return  # 无法重命名第0列和Live列
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        snap_idx = section - 2
        curr_name = self.snapshots[snap_idx].name
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Scheme" if is_en else "重命名方案",
            "Enter new scheme name:" if is_en else "请输入方案名称:",
            text=curr_name
        )
        if ok and new_name.strip():
            self.snapshots[snap_idx].name = new_name.strip()
            self._rebuild_table_columns()
            self.status_message.emit(
                f"Scheme renamed to [{new_name.strip()}]"
                if is_en else
                f"方案已重命名为 [{new_name.strip()}]"
            )

    # -------------------------------------------------------------
    # 字段取值与差异量计算辅助方法
    # -------------------------------------------------------------
    def _get_inner_dims(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        if inp.coil_type == CoilType.CIRCULAR:
            val = f"⌀ {inp.inner_len:.2f}"
            diff = ""
            if base_i:
                d = inp.inner_len - base_i.inner_len
                if abs(d) >= 0.005:
                    diff = f"{d:+.2f}"
        elif inp.coil_type == CoilType.OCTAGONAL:
            val = f"{inp.oct_id1:.2f} × {inp.oct_id2:.2f}"
            diff = ""
        else:
            val = f"{inp.inner_len:.2f} × {inp.inner_wid:.2f}"
            diff = ""
            if base_i:
                dl = inp.inner_len - base_i.inner_len
                dw = inp.inner_wid - base_i.inner_wid
                if abs(dl) >= 0.005 or abs(dw) >= 0.005:
                    diff = f"ΔL{dl:+.2f} ΔW{dw:+.2f}"
        return val, diff, False, False

    def _get_wall_thickness(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{out.e_env:.3f}"
        diff = ""
        if base_o:
            d = out.e_env - base_o.e_env
            if abs(d) >= 0.002:
                diff = f"{d:+.3f}"
        return val, diff, False, False

    def _get_topology_str(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        map_zh = {
            CoilType.RACETRACK: "跑道型",
            CoilType.CIRCULAR: "圆形",
            CoilType.OCTAGONAL: "八角形",
            CoilType.ARBITRARY_PERIMETER: "异形"
        }
        map_en = {
            CoilType.RACETRACK: "Racetrack",
            CoilType.CIRCULAR: "Circular",
            CoilType.OCTAGONAL: "Octagonal",
            CoilType.ARBITRARY_PERIMETER: "Arbitrary"
        }
        t_map = map_en if is_en else map_zh
        t_name = t_map.get(inp.coil_type, "Coil" if is_en else "线圈")
        m_name = "HCP" if inp.winding_mode == WindingMode.VARIABLE else "EVEN"
        val = f"{t_name} · {m_name}"
        diff = ""
        if base_i:
            base_t = t_map.get(base_i.coil_type, "Coil" if is_en else "线圈")
            base_m = "HCP" if base_i.winding_mode == WindingMode.VARIABLE else "EVEN"
            if t_name != base_t or m_name != base_m:
                diff = f"vs {base_t}·{base_m}"
        return val, diff, False, False

    def _get_bare_dia(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{inp.bare_dia:.3f}"
        diff = ""
        if base_i:
            d = inp.bare_dia - base_i.bare_dia
            if abs(d) >= 0.0005:
                diff = f"{d:+.3f}"
        return val, diff, False, False

    def _get_max_od(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{inp.max_od:.3f}"
        diff = ""
        if base_i:
            d = inp.max_od - base_i.max_od
            if abs(d) >= 0.0005:
                diff = f"{d:+.3f}"
        return val, diff, False, False

    def _get_layers(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{inp.radial_layers:.1f}"
        diff = ""
        if base_i:
            d = inp.radial_layers - base_i.radial_layers
            if abs(d) >= 0.1:
                diff = f"{d:+.1f}"
        return val, diff, False, False

    def _get_turns(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{inp.axial_turns}"
        diff = ""
        if base_i:
            d = inp.axial_turns - base_i.axial_turns
            if d != 0:
                diff = f"{d:+d}"
        return val, diff, False, False

    def _get_mode_str(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        from src.core.i18n import i18n
        if i18n.is_english():
            val = "HCP (Var)" if inp.winding_mode == WindingMode.VARIABLE else "Ortho (Even)"
            diff = "Changed" if (base_i and inp.winding_mode != base_i.winding_mode) else ""
        else:
            val = "异数 (HCP)" if inp.winding_mode == WindingMode.VARIABLE else "同数 (EVEN)"
            diff = "排法变更" if (base_i and inp.winding_mode != base_i.winding_mode) else ""
        return val, diff, False, False

    def _get_tension(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{inp.tension_factor:.3f}"
        diff = ""
        if base_i:
            d = inp.tension_factor - base_i.tension_factor
            if abs(d) >= 0.002:
                diff = f"{d:+.3f}"
        return val, diff, False, False

    def _get_total_n(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{out.total_turns}"
        diff = ""
        if base_o:
            d = out.total_turns - base_o.total_turns
            if d != 0:
                diff = f"{d:+d}"
        return val, diff, False, False

    def _get_outer_size(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        if inp.coil_type == CoilType.OCTAGONAL:
            val = f"{out.oct_od1:.3f} × {out.oct_od2:.3f}"
        else:
            val = f"{out.outer_len:.3f} × {out.outer_wid:.3f}"
        diff = ""
        if base_o:
            if inp.coil_type == CoilType.OCTAGONAL:
                d1 = out.oct_od1 - base_o.oct_od1
                d2 = out.oct_od2 - base_o.oct_od2
                if abs(d1) >= 0.002 or abs(d2) >= 0.002:
                    diff = f"{d1:+.3f}/{d2:+.3f}"
            else:
                dl = out.outer_len - base_o.outer_len
                dw = out.outer_wid - base_o.outer_wid
                if abs(dl) >= 0.002 or abs(dw) >= 0.002:
                    diff = f"{dl:+.3f}/{dw:+.3f}"
        return val, diff, False, False

    def _get_height(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{out.thickness_h:.3f}"
        diff = ""
        improved = False
        warn = False
        if out.dfm and not out.dfm.z_passed:
            warn = True
        if base_o:
            d = out.thickness_h - base_o.thickness_h
            if abs(d) >= 0.001:
                diff = f"{d:+.3f}"
        return val, diff, improved, warn

    def _get_r20(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{out.r20:.2f}"
        diff = ""
        if base_o:
            d = out.r20 - base_o.r20
            if abs(d) >= 0.02:
                diff = f"{d:+.2f}"
        return val, diff, False, False

    def _get_inductance(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{out.inductance_uh:.1f}"
        diff = ""
        if base_o:
            d = out.inductance_uh - base_o.inductance_uh
            if abs(d) >= 0.5:
                diff = f"{d:+.1f}"
        return val, diff, False, False

    def _get_cu_fill(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        val = f"{out.copper_fill_factor:.1f}%"
        diff = ""
        if base_o:
            d = out.copper_fill_factor - base_o.copper_fill_factor
            if abs(d) >= 0.2:
                diff = f"{d:+.1f}%"
        return val, diff, False, False

    def _get_dfm_status(self, inp: CoilInputs, out: CoilOutputs, base_i: Optional[CoilInputs], base_o: Optional[CoilOutputs]):
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        if not out.dfm or not out.dfm.enabled:
            return ("Limits Off" if is_en else "限值未开启"), "", False, False
        if out.dfm.all_passed:
            return ("✔ All Passed" if is_en else "✔ 全部合格"), "", True, False
        errs = []
        if not out.dfm.x_passed: errs.append("X")
        if not out.dfm.y_passed: errs.append("Y")
        if not out.dfm.z_passed: errs.append("Z")
        if not out.dfm.voltage_passed: errs.append("V" if is_en else "压")
        if not out.dfm.temp_passed: errs.append("T" if is_en else "温")
        return (f"⚠ {','.join(errs)} Over" if is_en else f"⚠ {','.join(errs)}超差"), "", False, True

    # -------------------------------------------------------------
    # 导出与复制
    # -------------------------------------------------------------
    def copy_table_to_clipboard(self):
        """将表格内容组织为 TSV 复制到剪贴板"""
        if not self._check_auth("复制方案对比表"):
            return
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        lines = []

        # 标题行
        header_vals = []
        for c in range(cols):
            header_item = self.table.horizontalHeaderItem(c)
            header_vals.append(header_item.text().replace("\n", " ") if header_item else "")
        lines.append("\t".join(header_vals))

        # 数据行 (不包含最后一行的操作按钮)
        for r in range(rows - 1):
            row_vals = []
            for c in range(cols):
                item = self.table.item(r, c)
                row_vals.append(item.text() if item else "")
            lines.append("\t".join(row_vals))

        from src.core.i18n import i18n
        is_en = i18n.is_english()
        tsv_data = "\n".join(lines)
        clipboard = QApplication.clipboard()
        clipboard.setText(tsv_data)
        self.status_message.emit(
            "✓ Scheme comparison matrix copied to clipboard (TSV format for Excel)!"
            if is_en else
            "✓ 方案对比表已成功复制至剪贴板，可直接在 Excel 中粘贴！"
        )

    def get_project_name(self) -> str:
        """获取所属主窗口的工程项目名称 (默认 Coli-Architect)"""
        win = self.window()
        if win and hasattr(win, "get_project_name"):
            return win.get_project_name()
        parent = self.parent()
        while parent:
            if hasattr(parent, "get_project_name"):
                return parent.get_project_name()
            parent = parent.parent()
        return "Coli-Architect"

    def export_excel(self):
        """导出为格式精美的 Excel 工作簿 (.xlsx)"""
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        if not self._check_auth("Export Scheme Comparison Excel" if is_en else "导出方案比对 Excel 报表"):
            return
        current_name = self.get_project_name()
        proj_name, ok = QInputDialog.getText(
            self, 
            "Export Comparison Matrix - Confirm Project Name" if is_en else "导出方案比对表 - 确认项目名称", 
            "Enter project code/name (injected into filename & matrix header):" if is_en else "请输入工程项目名称 (将注入文件名与方案对比表):", 
            QLineEdit.EchoMode.Normal, 
            current_name
        )
        if not ok:
            return
        proj_name = proj_name.strip() if proj_name else "Coli-Architect"
        if not proj_name:
            proj_name = "Coli-Architect"

        win = self.window()
        if win and hasattr(win, "txt_project_name"):
            win.txt_project_name.setText(proj_name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = (
            f"{proj_name}_Coil_Comparison_Matrix_{timestamp}.xlsx"
            if is_en else
            f"{proj_name}_线圈多方案对比表_{timestamp}.xlsx"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Comparison Matrix to Excel" if is_en else "导出方案比对表为 Excel",
            default_filename,
            "Excel Workbook (*.xlsx)" if is_en else "Excel 工作簿 (*.xlsx)"
        )
        if not path:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Scheme Comparison Matrix" if is_en else "方案对比矩阵"
            ws.views.sheetView[0].showGridLines = True

            font_title = Font(name="Segoe UI" if is_en else "Microsoft YaHei", size=13, bold=True, color="FFFFFF")
            font_subtitle = Font(name="Segoe UI" if is_en else "Microsoft YaHei", size=9, italic=True, color="64748B")
            font_header = Font(name="Segoe UI" if is_en else "Microsoft YaHei", size=10, bold=True, color="1E293B")
            font_body = Font(name="Segoe UI" if is_en else "Microsoft YaHei", size=10, color="0F172A")

            fill_title = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
            fill_header = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            fill_live = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
            fill_baseline = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
            fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

            border_thin = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            cols = self.table.columnCount()
            rows = self.table.rowCount()

            # 1. 顶部标题栏
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=cols)
            cell_title = ws.cell(
                row=1,
                column=1,
                value=(
                    "Coil-Architect Pro - Multi-Scheme Parameter & Simulation Comparison Matrix"
                    if is_en else
                    "Coil-Architect Pro - 线圈多方案参数与仿真结果对比矩阵"
                )
            )
            cell_title.font = font_title
            cell_title.fill = fill_title
            cell_title.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 36

            # 2. 副标题、项目名称与导出时间
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=cols)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cell_sub = ws.cell(
                row=2,
                column=1,
                value=(
                    f"Project Name: {proj_name}  |  Export Time: {now_str}  |  Official Platform: ansv.net  |  Coil-Architect Pro"
                    if is_en else
                    f"工程项目名称: {proj_name}  |  导出时间: {now_str}  |  官方支持: ansv.net  |  线圈架构师 Pro"
                )
            )
            cell_sub.font = font_subtitle
            cell_sub.alignment = Alignment(horizontal="right", vertical="center")
            ws.row_dimensions[2].height = 20

            # 3. 表头行 (第 4 行)
            header_row = 4
            ws.row_dimensions[header_row].height = 30
            for c in range(cols):
                header_item = self.table.horizontalHeaderItem(c)
                header_text = header_item.text().replace("\n", " ") if header_item else ""
                cell = ws.cell(row=header_row, column=c + 1, value=header_text)
                cell.font = font_header
                cell.border = border_thin
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
                if c == 0:
                    cell.fill = fill_header
                elif c == 1:
                    cell.fill = fill_live
                elif c - 2 >= 0 and c - 2 < len(self.snapshots) and self.snapshots[c - 2].is_baseline:
                    cell.fill = fill_baseline
                else:
                    cell.fill = fill_header

            # 4. 数据行 (第 5 行开始，忽略最后一行的操作按钮)
            for r in range(rows - 1):
                excel_row = header_row + 1 + r
                ws.row_dimensions[excel_row].height = 24
                for c in range(cols):
                    item = self.table.item(r, c)
                    val = item.text() if item else ""
                    cell = ws.cell(row=excel_row, column=c + 1, value=val)
                    cell.font = font_body
                    cell.border = border_thin
                    align_h = "left" if c == 0 else "center"
                    cell.alignment = Alignment(horizontal=align_h, vertical="center", wrap_text=False)
                    if r % 2 == 1:
                        cell.fill = fill_zebra

            # 5. 列宽自适应 (中文字符 2.3 权重 + 8 字符边距冗余，第一列参数名保底 38 宽，方案列保底 22 宽，绝不截断)
            for col in ws.columns:
                col_idx = col[0].column
                col_letter = get_column_letter(col_idx)
                max_len = 0.0
                for cell in col:
                    if cell.row >= 4 and cell.value is not None:
                        val_str = str(cell.value)
                        w = sum(2.3 if ord(ch) > 127 else 1.15 for ch in val_str)
                        if w > max_len:
                            max_len = w
                if col_idx == 1:
                    ws.column_dimensions[col_letter].width = max(max_len + 8.0, 38.0)
                else:
                    ws.column_dimensions[col_letter].width = max(max_len + 6.0, 22.0)

            wb.save(path)
            if is_en:
                self.status_message.emit(f"✓ Scheme comparison matrix exported to Excel: {path}")
                QMessageBox.information(self, "Export Successful", f"Scheme comparison matrix exported to Excel workbook:\n{path}")
            else:
                self.status_message.emit(f"✓ 方案对比表已成功导出为 Excel 工作簿: {path}")
                QMessageBox.information(self, "导出成功", f"方案对比表已成功导出为 Excel 工作簿:\n{path}")
        except Exception as e:
            if is_en:
                QMessageBox.critical(self, "Excel Export Failed", f"Failed to write Excel workbook:\n{str(e)}")
            else:
                QMessageBox.critical(self, "导出 Excel 失败", f"无法写入 Excel 文件:\n{str(e)}")

    def export_csv(self):
        """导出为标准 UTF-8 CSV 报表 (.csv)"""
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        if not self._check_auth("Export Scheme Comparison CSV" if is_en else "导出方案比对 CSV 报表"):
            return
        current_name = self.get_project_name()
        proj_name, ok = QInputDialog.getText(
            self,
            "Export Comparison Matrix - Confirm Project Name" if is_en else "导出方案比对表 - 确认项目名称",
            "Enter project code/name (injected into filename & CSV header):" if is_en else "请输入工程项目名称 (将注入文件名与 CSV 报表):",
            QLineEdit.EchoMode.Normal,
            current_name
        )
        if not ok:
            return
        proj_name = proj_name.strip() if proj_name else "Coli-Architect"
        if not proj_name:
            proj_name = "Coli-Architect"

        win = self.window()
        if win and hasattr(win, "txt_project_name"):
            win.txt_project_name.setText(proj_name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = (
            f"{proj_name}_Coil_Comparison_Matrix_{timestamp}.csv"
            if is_en else
            f"{proj_name}_线圈多方案对比表_{timestamp}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Comparison Matrix to CSV" if is_en else "导出方案比对表为 CSV",
            default_filename,
            "CSV Report (*.csv)" if is_en else "CSV 报表文件 (*.csv)"
        )
        if not path:
            return

        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows = self.table.rowCount()
            cols = self.table.columnCount()

            if is_en:
                lines = [
                    "Coil-Architect Pro - Multi-Scheme Parameter & Simulation Comparison Matrix",
                    f"Project Name,{proj_name}",
                    f"Export Timestamp,{now_str}",
                    "Official Platform,ansv.net (ANSV Micro-Actuator & Precision Drive Platform)",
                    ""
                ]
            else:
                lines = [
                    "Coil-Architect Pro - 线圈多方案参数与仿真结果对比矩阵",
                    f"工程项目名称,{proj_name}",
                    f"导出时间,{now_str}",
                    "官方支持平台,ansv.net (ANSV 微型执行器与精密传动平台)",
                    ""
                ]

            # 表头
            header_vals = []
            for c in range(cols):
                header_item = self.table.horizontalHeaderItem(c)
                val = header_item.text().replace("\n", " ") if header_item else ""
                header_vals.append(f'"{val}"' if ',' in val else val)
            lines.append(",".join(header_vals))

            # 数据行 (不包含最后一行的操作按钮)
            for r in range(rows - 1):
                row_vals = []
                for c in range(cols):
                    item = self.table.item(r, c)
                    val = item.text() if item else ""
                    row_vals.append(f'"{val}"' if (',' in val or '\n' in val) else val)
                lines.append(",".join(row_vals))

            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write("\n".join(lines))

            if is_en:
                self.status_message.emit(f"✓ Scheme comparison matrix exported to CSV: {path}")
                QMessageBox.information(self, "Export Successful", f"Scheme comparison matrix exported to CSV report:\n{path}")
            else:
                self.status_message.emit(f"✓ 方案对比表已成功导出为 CSV 报表: {path}")
                QMessageBox.information(self, "导出成功", f"方案对比表已成功导出为 CSV 报表:\n{path}")
        except Exception as e:
            if is_en:
                QMessageBox.critical(self, "CSV Export Failed", f"Failed to write CSV report:\n{str(e)}")
            else:
                QMessageBox.critical(self, "导出 CSV 失败", f"无法写入 CSV 文件:\n{str(e)}")


    def export_schemes_file(self):
        """将当前抽屉中所有固化的对比方案导出为可导入还原的 .ansvschemes 文件"""
        from src.core.i18n import i18n
        import json
        is_en = i18n.is_english()
        if not self.snapshots:
            msg = "No frozen schemes to export! Please click [📌 Freeze Current Scheme] first." if is_en else "当前暂无已固化方案可导出！请先点击【📌 固化当前方案】保存至少一组方案。"
            QMessageBox.information(self, "Notice" if is_en else "提示", msg)
            return

        proj_name = self.get_project_name()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        def_name = f"{proj_name}_Coil_Schemes_{timestamp}.ansvschemes" if is_en else f"{proj_name}_线圈对比方案_{timestamp}.ansvschemes"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Comparison Schemes" if is_en else "导出方案比对归档文件",
            def_name,
            "ANSV Coil Schemes (*.ansvschemes);;JSON Schemes (*.json)" if is_en else "ANSV 线圈方案归档 (*.ansvschemes);;JSON 方案文件 (*.json)"
        )
        if not path:
            return

        try:
            from dataclasses import asdict
            data = {
                "file_type": "ANSV_COIL_SCHEMES_BUNDLE",
                "version": "1.1.0",
                "project_name": proj_name,
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "schemes_count": len(self.snapshots),
                "snapshots": []
            }
            for s in self.snapshots:
                inp_dict = asdict(s.inputs)
                inp_dict["coil_type"] = int(s.inputs.coil_type)
                inp_dict["winding_mode"] = int(s.inputs.winding_mode)
                out_dict = asdict(s.outputs)
                out_dict["dfm_status"] = int(s.outputs.dfm_status)
                data["snapshots"].append({
                    "name": s.name,
                    "created_at": s.created_at,
                    "is_baseline": s.is_baseline,
                    "inputs": inp_dict,
                    "outputs": out_dict
                })

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            ok_msg = (f"✓ {len(self.snapshots)} comparison schemes exported to:\n{path}" if is_en else f"✓ 已成功导出 {len(self.snapshots)} 组比对方案至:\n{path}")
            self.status_message.emit(ok_msg)
            QMessageBox.information(self, "Export Successful" if is_en else "导出成功", ok_msg)
        except Exception as e:
            err_msg = f"Failed to export schemes: {e}" if is_en else f"导出方案文件失败: {e}"
            QMessageBox.critical(self, "Error" if is_en else "错误", err_msg)

    def import_schemes_file(self):
        """导入 .ansvschemes 文件，将历史多组方案重新载入抽屉进行横向对比与验证还原"""
        from src.core.i18n import i18n
        import json
        is_en = i18n.is_english()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Comparison Schemes" if is_en else "导入方案比对归档文件",
            "",
            "ANSV Coil Schemes (*.ansvschemes *.json);;All Files (*.*)" if is_en else "ANSV 线圈方案归档 (*.ansvschemes *.json);;所有文件 (*.*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_snaps = data.get("snapshots", [])
            if not raw_snaps:
                raise ValueError("未在文件中找到方案快照数据 (snapshots 为空)")

            # 如果当前已有快照，询问是否追加或替换
            if self.snapshots:
                btn_replace = "Replace All" if is_en else "覆盖替换"
                btn_append = "Append" if is_en else "追加合并"
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setWindowTitle("Import Mode" if is_en else "导入方式确认")
                msg_box.setText(
                    (f"Current drawer has {len(self.snapshots)} frozen scheme(s).\nImporting file contains {len(raw_snaps)} scheme(s).\nChoose how to import:")
                    if is_en else
                    (f"当前比对抽屉已存在 {len(self.snapshots)} 组方案，导入文件包含 {len(raw_snaps)} 组方案。\n请选择导入方式：")
                )
                b_rep = msg_box.addButton(btn_replace, QMessageBox.ButtonRole.DestructiveRole)
                b_app = msg_box.addButton(btn_append, QMessageBox.ButtonRole.ActionRole)
                b_can = msg_box.addButton("Cancel" if is_en else "取消", QMessageBox.ButtonRole.RejectRole)
                msg_box.exec()
                if msg_box.clickedButton() == b_can:
                    return
                elif msg_box.clickedButton() == b_rep:
                    self.snapshots.clear()

            from src.core.physics_engine import CoilPhysicsEngine
            from src.core.models import DFMCheckResult
            for s_data in raw_snaps:
                inp_dict = s_data.get("inputs", {})
                if "coil_type" in inp_dict:
                    inp_dict["coil_type"] = CoilType(inp_dict["coil_type"])
                if "winding_mode" in inp_dict:
                    inp_dict["winding_mode"] = WindingMode(inp_dict["winding_mode"])
                inp_obj = CoilInputs(**inp_dict)
                # 使用物理引擎重新解算确保真实有效
                out_obj = CoilPhysicsEngine.calculate(inp_obj)
                snap = SchemeSnapshot(
                    name=s_data.get("name", f"方案 {len(self.snapshots)+1}"),
                    created_at=s_data.get("created_at", datetime.now().strftime("%H:%M:%S")),
                    inputs=inp_obj,
                    outputs=out_obj,
                    is_baseline=s_data.get("is_baseline", len(self.snapshots) == 0)
                )
                self.snapshots.append(snap)

            # 确保至少有一个 baseline
            has_base = any(s.is_baseline for s in self.snapshots)
            if not has_base and self.snapshots:
                self.snapshots[0].is_baseline = True

            self._rebuild_table_columns()
            ok_msg = (f"✓ Successfully loaded {len(raw_snaps)} comparison schemes from:\n{os.path.basename(path)}" if is_en else f"✓ 已成功载入 {len(raw_snaps)} 组对比方案至比对抽屉！\n随时可点击方案列底部的【↺ 还原】按钮一键装载验证。")
            self.status_message.emit(ok_msg)
            QMessageBox.information(self, "Import Successful" if is_en else "导入成功", ok_msg)
        except Exception as e:
            err_msg = f"Failed to import schemes: {e}" if is_en else f"导入方案文件失败: {e}"
            QMessageBox.critical(self, "Error" if is_en else "错误", err_msg)
