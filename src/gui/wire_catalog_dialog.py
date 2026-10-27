# -*- coding: utf-8 -*-
"""
Coil-Architect Pro - 华冶线材出厂标准库弹窗选择器 (Wire Catalog Dialog)
以专业工业级表格弹窗形式展示华冶出厂标准线材：
包含 4 列核心出厂技术指标：
1. 线径 (mm)
2. 最大外径 (mm)
3. KM阻值 (Ω/km)
4. KM/KG (km/kg)
支持纯铜标准系列 (69档) 与 15% 铜包铝系列 (79档) 一键切换及快速关键字过滤搜索。
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

    def __init__(self, current_diameter: float = 0.080, is_ccaw: bool = False, material_type: int = 1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("华冶线材出厂标准数据库 · 规格选型" if not i18n.is_english() else "Huaye Wire Specification Catalog")
        self.resize(920, 580)
        self.setMinimumSize(850, 480)
        
        self.selected_item: Optional[WireCatalogItem] = None
        self._initial_diameter = current_diameter
        self._initial_is_ccaw = is_ccaw
        self._initial_material_type = 2 if is_ccaw else 1

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
        series_box.setSpacing(16)
        
        self.rb_copper = QRadioButton("纯铜标准系列 (69档 · 1/58.5)")
        self.rb_ccaw = QRadioButton("15% 铜包铝轻量化 (79档 · 0.02525)")
        self.rb_copper.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E293B;")
        self.rb_ccaw.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E293B;")

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.rb_copper, 1)
        self.btn_group.addButton(self.rb_ccaw, 2)
        
        if self._initial_is_ccaw or getattr(self, "_initial_material_type", 1) == 2:
            self.rb_ccaw.setChecked(True)
        else:
            self.rb_copper.setChecked(True)
            
        self.btn_group.idToggled.connect(self._on_series_changed)

        series_box.addWidget(self.rb_copper)
        series_box.addWidget(self.rb_ccaw)
        top_bar.addLayout(series_box)

        layout.addLayout(top_bar)

        # 华冶定制说明提示条 (明确说明无氧纯铜定制机制)
        tip_frame = QFrame()
        tip_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFBEB;
                border: 1px solid #FDE68A;
                border-radius: 6px;
            }
        """)
        tip_layout = QHBoxLayout(tip_frame)
        tip_layout.setContentsMargins(10, 8, 10, 8)
        tip_layout.setSpacing(6)
        
        is_en = i18n.is_english()
        notice_text = (
            "💡 材质与定制说明：华冶标准线材出厂采用实测经验纯铜 (ρ=0.017094 Ω·mm²/m，1/58.5)；微特电机若需极低直流阻抗 (DCR)，可向华冶定制高纯退火态无氧纯铜 (OFC，ρ=0.016949 Ω·mm²/m，1/59.0)，模具外径完全通用，线圈阻抗直接下浮约 0.85%（选定出厂规格后可在主界面【导体材质与电导基准】下拉框随时一键切换比对）；其他非库规格支持华冶非标定制。"
            if not is_en else
            "💡 Material & Custom Notice: Huaye standard wires use measured pure copper (rho=0.017094, 1/58.5). For lower DCR, customers can customize high-purity annealed OFC copper (rho=0.016949, 1/59.0) with identical die outer diameters, reducing coil resistance by ~0.85% (can be seamlessly switched via the material dropdown on the main UI). Other non-catalog sizes are available via custom orders."
        )
        self.lbl_tip_notice = QLabel(notice_text)
        self.lbl_tip_notice.setStyleSheet("font-size: 11px; font-weight: 600; color: #B45309;")
        self.lbl_tip_notice.setWordWrap(True)
        tip_layout.addWidget(self.lbl_tip_notice)
        layout.addWidget(tip_frame)

        # 2. 快捷搜索过滤条
        search_box = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 输入线径快速过滤 (例如: 0.080, 0.15, 0.35)...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: #1E293B;
            }
            QLineEdit:focus {
                border-color: #0284C7;
            }
        """)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        search_box.addWidget(self.txt_search)

        self.lbl_count = QLabel("共 69 档规格")
        self.lbl_count.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; padding-left: 8px;")
        search_box.addWidget(self.lbl_count)

        layout.addLayout(search_box)

        # 3. 核心 4 列数据表格 (线径, 最大外径, KM阻值, KM/KG)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "公称裸线径 (mm)",
            "出厂最大外径 (mm · 1UEW)",
            "出厂 KM 阻值 (Ω/km · 20℃)",
            "出厂 KM/KG (km/kg · 裸铜米重)"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                gridline-color: #F1F5F9;
                font-size: 12px;
                color: #1E293B;
            }
            QTableWidget::item {
                padding: 6px 12px;
            }
            QTableWidget::item:selected {
                background-color: #E0F2FE;
                color: #0369A1;
                font-weight: 700;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                border: none;
                border-bottom: 2px solid #E2E8F0;
                color: #475569;
                font-weight: 700;
                padding: 8px 10px;
                font-size: 11px;
            }
        """)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 190)

        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.table)

        # 4. 底部说明与操作栏
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #F8FAFC; border-top: 1px solid #E2E8F0; border-radius: 4px;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(12, 10, 12, 10)
        bottom_layout.setSpacing(12)

        self.lbl_selected_info = QLabel("当前未选定线规 (点击行选择)")
        self.lbl_selected_info.setStyleSheet("font-size: 12px; font-weight: 600; color: #0284C7;")
        bottom_layout.addWidget(self.lbl_selected_info, 1)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("✔ 载入所选华冶规格")
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #0284C7;
                border-radius: 6px;
                padding: 6px 20px;
                font-size: 12px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
                border-color: #CBD5E1;
                color: #94A3B8;
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
        if self.rb_ccaw.isChecked():
            wires: List[WireCatalogItem] = get_huaye_ccaw_wires()
        else:
            wires: List[WireCatalogItem] = get_huaye_copper_wires()

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

            # 匹配初始线径
            if matched_row < 0 and abs(item.diameter - self._initial_diameter) < 1e-4:
                matched_row = row_idx

        # 恢复或触发过滤
        self._apply_filter(self.txt_search.text())

        # 默认高亮行
        if matched_row >= 0:
            self.table.selectRow(matched_row)
            self.table.scrollToItem(self.table.item(matched_row, 0))
        elif len(wires) > 0:
            self.table.selectRow(0)

        series_name = "15% 铜包铝轻量化系列" if self.rb_ccaw.isChecked() else "纯铜标准系列"
        self.lbl_count.setText(f"{series_name}: 共 {len(wires)} 档规格")

    def _on_search_text_changed(self, text: str):
        self._apply_filter(text)

    def _apply_filter(self, query: str):
        q = query.strip()
        visible_count = 0
        for r in range(self.table.rowCount()):
            item_d = self.table.item(r, 0)
            if not item_d:
                continue
            dia_str = item_d.text()
            if not q or q in dia_str:
                self.table.setRowHidden(r, False)
                visible_count += 1
            else:
                self.table.setRowHidden(r, True)

        series_name = "15% 铜包铝系列" if self.rb_ccaw.isChecked() else "纯铜标准系列"
        self.lbl_count.setText(f"{series_name}: 匹配 {visible_count} / {self.table.rowCount()} 档")

    def _on_table_selection_changed(self):
        sel = self.table.selectedItems()
        if not sel:
            self.selected_item = None
            self.lbl_selected_info.setText("当前未选定线规 (点击行选择)")
            self.btn_confirm.setEnabled(False)
            return

        row = sel[0].row()
        item0 = self.table.item(row, 0)
        catalog_item: WireCatalogItem = item0.data(Qt.ItemDataRole.UserRole)
        self.selected_item = catalog_item

        mat_title = "15% 铜包铝" if catalog_item.density < 4.0 else "华冶纯铜"
        info = (
            f"已选定: 【{mat_title}】 线径 {catalog_item.diameter:.3f} mm  |  "
            f"出厂基准外径 {catalog_item.max_outer_dia:.3f} mm  |  "
            f"KM阻值 {catalog_item.km_resistance_ohm:.1f} Ω/km  |  "
            f"裸铜 {catalog_item.km_per_kg:.3f} km/kg"
        )
        self.lbl_selected_info.setText(info)
        self.btn_confirm.setEnabled(True)

    def _on_table_double_clicked(self, item: QTableWidgetItem):
        self._on_table_selection_changed()
        if self.selected_item is not None:
            self._on_confirm_clicked()

    def _on_confirm_clicked(self):
        if self.selected_item is not None:
            self.wire_selected.emit(self.selected_item)
            self.accept()
