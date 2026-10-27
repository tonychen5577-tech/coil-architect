# -*- coding: utf-8 -*-
"""
Coil-Architect Pro - 华冶线材出厂标准库弹窗选择器 (Wire Catalog Dialog)
以专业工业级表格弹窗形式展示华冶出厂标准线材：
包含 4 列核心出厂技术指标：
1. 线径 (mm)
2. 最大外径 (mm)
3. KM阻值 (Ω/km)
4. KM/KG (km/kg)
支持纯铜系列 (69档) 与 15% 铜包铝系列 (79档) 一键切换及快速关键字过滤搜索。
"""

from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QRadioButton, QButtonGroup, QFrame, QAbstractItemView,
    QSizePolicy
)

from ..core.wire_catalog import (
    WireCatalogItem, get_huaye_copper_wires, get_huaye_ccaw_wires
)
from ..core.i18n import i18n, t


class WireCatalogDialog(QDialog):
    """华冶线材出厂标准数据库选型弹窗"""

    wire_selected = pyqtSignal(object)  # 发射选中的 WireCatalogItem

    def __init__(self, current_diameter: float = 0.080, is_ccaw: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("华冶线材出厂标准数据库 · 规格选型" if not i18n.is_english() else "Huaye Wire Specification Catalog")
        self.resize(920, 580)
        self.setMinimumSize(850, 480)
        
        self.selected_item: Optional[WireCatalogItem] = None
        self._initial_diameter = current_diameter
        self._initial_is_ccaw = is_ccaw

        self._setup_ui()
        self._load_catalog_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. 顶部标题栏
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.lbl_title = QLabel("📖 华冶漆包线出厂技术规格库")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1B365D;")
        self.lbl_sub = QLabel("标准出厂参数直接导入 · 自动绑定线径、外径、千米电阻与线密度 · 其他非材料库尺寸需咨询华冶定制")
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_sub)
        top_bar.addLayout(title_box)
        top_bar.addStretch()

        # 系列切换单选按钮 (纯铜 vs 铜包铝)
        series_box = QHBoxLayout()
        series_box.setSpacing(12)
        
        self.rb_copper = QRadioButton("纯铜标准系列 (69档 · 1/58.5)")
        self.rb_ccaw = QRadioButton("15% 铜包铝轻量化 (79档 · 0.02525)")
        self.rb_copper.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E293B;")
        self.rb_ccaw.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E293B;")

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.rb_copper, 1)
        self.btn_group.addButton(self.rb_ccaw, 2)
        
        if self._initial_is_ccaw:
            self.rb_ccaw.setChecked(True)
        else:
            self.rb_copper.setChecked(True)
            
        self.btn_group.idToggled.connect(self._on_series_changed)

        series_box.addWidget(self.rb_copper)
        series_box.addWidget(self.rb_ccaw)
        top_bar.addLayout(series_box)

        layout.addLayout(top_bar)

        # 华冶定制说明提示条
        tip_frame = QFrame()
        tip_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFBEB;
                border: 1px solid #FDE68A;
                border-radius: 6px;
            }
        """)
        tip_layout = QHBoxLayout(tip_frame)
        tip_layout.setContentsMargins(10, 6, 10, 6)
        tip_layout.setSpacing(6)
        
        is_en = i18n.is_english()
        notice_text = (
            "💡 规格定制说明：本库收录华冶标准出厂规格。其他非材料库尺寸，需咨询华冶定制（支持特殊线径、定制漆膜与耐温等级）。"
            if not is_en else
            "💡 Custom Notice: This catalog contains Huaye standard stock specifications. Other non-catalog sizes require custom fabrication by Huaye."
        )
        self.lbl_tip_notice = QLabel(notice_text)
        self.lbl_tip_notice.setStyleSheet("font-size: 11px; font-weight: 600; color: #B45309;")
        tip_layout.addWidget(self.lbl_tip_notice)
        layout.addWidget(tip_frame)

        # 2. 快捷搜索过滤条
        search_box = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 输入线径快速过滤 (例如: 0.080, 0.15, 0.35)...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: #1E293B;
            }
            QLineEdit:focus {
                border-color: #0284C7;
                background-color: #FFFFFF;
            }
        """)
        self.txt_search.textChanged.connect(self._filter_table)
        search_box.addWidget(self.txt_search)
        
        btn_clear = QPushButton("清空")
        btn_clear.setFixedWidth(54)
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        btn_clear.clicked.connect(lambda: self.txt_search.setText(""))
        search_box.addWidget(btn_clear)

        layout.addLayout(search_box)

        # 3. 核心规格数据表格 (严格 4 列出厂指标)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        headers = ["线径 (mm)", "最大外径 (mm)", "KM阻值 (Ω/km)", "KM/KG (km/kg)"]
        self.table.setHorizontalHeaderLabels(headers)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 滚轮平滑滚动与滚动条常驻
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.verticalScrollBar().setSingleStep(30)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                font-size: 12px;
                color: #1E293B;
            }
            QTableWidget::item {
                padding: 5px 8px;
            }
            QTableWidget::item:selected {
                background-color: #E0F2FE;
                color: #0369A1;
                font-weight: 700;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #1E293B;
                font-size: 11px;
                font-weight: 700;
                border: none;
                border-bottom: 2px solid #CBD5E1;
                padding: 7px 8px;
            }
            QScrollBar:vertical {
                background-color: #F8FAFC;
                width: 12px;
                border-left: 1px solid #E2E8F0;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #CBD5E1;
                min-height: 30px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.table, 1)

        # 4. 底部状态摘要与确认按钮栏
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)

        self.lbl_selected_info = QLabel("请在表格中选择线材规格...")
        self.lbl_selected_info.setStyleSheet("font-size: 12px; font-weight: 600; color: #0284C7;")
        self.lbl_selected_info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bottom_layout.addWidget(self.lbl_selected_info, 1)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("✓ 确认选择并载入仿真")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
                color: #E2E8F0;
            }
        """)
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)
        bottom_layout.addWidget(self.btn_confirm)

        layout.addWidget(bottom_frame)

    def _on_series_changed(self, btn_id: int, checked: bool):
        if checked:
            self._load_catalog_data()

    def _load_catalog_data(self):
        """载入当前选中系列的数据到表格"""
        is_ccaw = self.rb_ccaw.isChecked()
        wires: List[WireCatalogItem] = get_huaye_ccaw_wires() if is_ccaw else get_huaye_copper_wires()

        self.table.setRowCount(len(wires))
        matched_row = -1

        for row_idx, item in enumerate(wires):
            # Col 0: 线径
            c0 = QTableWidgetItem(f"{item.diameter:.3f}")
            c0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c0.setData(Qt.ItemDataRole.UserRole, item)

            # Col 1: 最大外径
            c1 = QTableWidgetItem(f"{item.max_outer_dia:.3f}")
            c1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Col 2: KM 阻值 (Ω/km)
            c2 = QTableWidgetItem(f"{item.km_resistance_ohm:.1f}")
            c2.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Col 3: KM/KG (km/kg)
            c3 = QTableWidgetItem(f"{item.km_per_kg:.3f}")
            c3.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.table.setItem(row_idx, 0, c0)
            self.table.setItem(row_idx, 1, c1)
            self.table.setItem(row_idx, 2, c2)
            self.table.setItem(row_idx, 3, c3)

            # 初始自动高亮匹配线径
            if abs(item.diameter - self._initial_diameter) < 1e-4:
                matched_row = row_idx

        # 选中最匹配行
        if matched_row >= 0:
            self.table.selectRow(matched_row)
            self.table.scrollToItem(self.table.item(matched_row, 0))
        elif len(wires) > 0:
            self.table.selectRow(0)

        self._filter_table()

    def _filter_table(self):
        """按搜索输入即时过滤表格行"""
        query = self.txt_search.text().strip().lower()
        row_count = self.table.rowCount()
        visible_count = 0

        for r in range(row_count):
            if not query:
                self.table.setRowHidden(r, False)
                visible_count += 1
                continue
            item = self.table.item(r, 0)
            dia_str = item.text().lower() if item else ""
            od_str = self.table.item(r, 1).text().lower() if self.table.item(r, 1) else ""
            res_str = self.table.item(r, 2).text().lower() if self.table.item(r, 2) else ""
            
            # 匹配线径、外径或电阻
            matched = (query in dia_str or query in od_str or query in res_str)
            self.table.setRowHidden(r, not matched)
            if matched:
                visible_count += 1

        if query and visible_count == 0:
            is_en = i18n.is_english()
            msg = (
                "💡 未在材料库中检索到该尺寸。其他非材料库尺寸，需咨询华冶定制。"
                if not is_en else
                "💡 Size not found in standard stock catalog. Other non-catalog sizes require custom fabrication by Huaye."
            )
            self.lbl_selected_info.setText(msg)
            self.btn_confirm.setEnabled(False)

    def _on_table_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.btn_confirm.setEnabled(False)
            self.lbl_selected_info.setText("请在表格中选择线材规格...")
            self.selected_item = None
            return

        row = selected_rows[0].row()
        item_obj = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if isinstance(item_obj, WireCatalogItem):
            self.selected_item = item_obj
            self.btn_confirm.setEnabled(True)
            mat = "15% 铜包铝" if "铜包铝" in item_obj.material_name else "纯铜"
            self.lbl_selected_info.setText(
                f"已选: 【{mat}】 线径 {item_obj.diameter:.3f} mm | 最大外径 {item_obj.max_outer_dia:.3f} mm | "
                f"阻值 {item_obj.km_resistance_ohm:.1f} Ω/km | 密度比 {item_obj.km_per_kg:.3f} km/kg"
            )

    def _on_table_double_clicked(self, item):
        self._on_confirm_clicked()

    def _on_confirm_clicked(self):
        if self.selected_item is not None:
            self.wire_selected.emit(self.selected_item)
            self.accept()

    def wheelEvent(self, event):
        """支持在弹窗任意区域滑动鼠标滚轮时均可流畅滚动表格"""
        if hasattr(self, "table") and self.table.verticalScrollBar().isVisible():
            delta = event.angleDelta().y()
            if delta != 0:
                current_val = self.table.verticalScrollBar().value()
                # 滚轮每次滚动约 2~3 行高度 (60px)
                step = 60 if delta < 0 else -60
                self.table.verticalScrollBar().setValue(current_val + step)
                event.accept()
                return
        super().wheelEvent(event)
