# -*- coding: utf-8 -*-
"""
Coil-Architect Pro - 自定义线材厂商数据库与规格编辑器 (Custom Wire Library & Editor)
允许用户完全自主管理线材供应商规格：
1. 厂商名称、型号/品名、规格名称
2. 几何参数：公称裸线径 d (mm)、出厂最大外径 D (mm)
3. 核心双向推导：铜导率 (% IACS) 与 出厂米阻 (Ω/m 20℃) 二选一输入，实时互推
4. 出厂物理与电气指标：击穿电压 (V)、伸长率 (%)、材料密度 (g/cm³)、出厂重量比 (m/kg 国标单位)
5. 库管理功能：新增、编辑、克隆、删除、导入/导出 JSON、一键调入仿真引擎
"""

import os
import math
import uuid
from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton,
    QButtonGroup, QFrame, QGroupBox, QComboBox, QMessageBox, QFileDialog,
    QAbstractItemView, QSizePolicy
)

from ..core.wire_catalog import (
    CustomWireItem, CustomWireManager, get_custom_wire_manager,
    calculate_rm_from_iacs, calculate_iacs_from_rm, calculate_theoretical_m_per_kg
)
from ..core.i18n import i18n, t
from .widgets.slider_spin_box import ClickableDoubleSpinBox


class CustomWireEditorDialog(QDialog):
    """自定义线材单项规格添加/编辑对话框"""

    def __init__(self, wire_item: Optional[CustomWireItem] = None, parent=None):
        super().__init__(parent)
        self.is_edit_mode = (wire_item is not None)
        self.wire_item = wire_item

        is_en = i18n.is_english()
        title = ("编辑线材规格" if self.is_edit_mode else "新增线材规格") if not is_en else (
            "Edit Custom Wire" if self.is_edit_mode else "Add Custom Wire"
        )
        self.setWindowTitle(f"⚡ {title}")
        self.resize(700, 750)
        self.setMinimumSize(680, 720)

        self._is_updating = False
        self._active_derivation_mode = 1  # 1: IACS -> Rm, 2: Rm -> IACS

        self._setup_ui()
        self._populate_initial_data()

    def _setup_ui(self):
        is_en = i18n.is_english()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. 顶部标题
        header_box = QHBoxLayout()
        header_box.setSpacing(8)
        lbl_head = QLabel("⚡ 自定义线材规格参数设定" if not is_en else "⚡ Custom Wire Specification Editor")
        lbl_head.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E3A8A;")
        header_box.addWidget(lbl_head)
        header_box.addStretch()
        layout.addLayout(header_box)

        # 2. 基本信息卡片 (厂商, 型号, 规格名称)
        grp_basic = QGroupBox("线材品名与厂商归属" if not is_en else "Vendor & Model Information")
        grp_basic.setStyleSheet(self._group_box_qss())
        grid_basic = QGridLayout(grp_basic)
        grid_basic.setContentsMargins(14, 22, 14, 12)
        grid_basic.setHorizontalSpacing(12)
        grid_basic.setVerticalSpacing(8)

        lbl_vendor = QLabel("线材厂商:" if not is_en else "Manufacturer:")
        self.combo_vendor = QComboBox()
        self.combo_vendor.setEditable(True)
        self.combo_vendor.addItems(["华冶精工", "益达微电", "胜牌电气", "宏天特种", "金杯电工", "精达股份", "宝胜科技", "自定义厂商"])
        self.combo_vendor.setStyleSheet(self._input_field_qss())

        lbl_model = QLabel("型号/品名:" if not is_en else "Model / Type:")
        self.txt_model = QLineEdit()
        self.txt_model.setPlaceholderText("例如: 1UEW-SB 复合自粘线, 2PEW, 0UEW...")
        self.txt_model.setStyleSheet(self._input_field_qss())

        lbl_spec = QLabel("规格名称:" if not is_en else "Spec Name:")
        self.txt_spec = QLineEdit()
        self.txt_spec.setPlaceholderText("例如: 0.080mm (留空自动生成)")
        self.txt_spec.setStyleSheet(self._input_field_qss())

        grid_basic.addWidget(lbl_vendor, 0, 0)
        grid_basic.addWidget(self.combo_vendor, 0, 1)
        grid_basic.addWidget(lbl_model, 0, 2)
        grid_basic.addWidget(self.txt_model, 0, 3)
        grid_basic.addWidget(lbl_spec, 1, 0)
        grid_basic.addWidget(self.txt_spec, 1, 1, 1, 3)

        layout.addWidget(grp_basic)

        # 3. 几何尺寸卡片 (公称裸线径 d, 出厂最大外径 D)
        grp_geom = QGroupBox("公称几何尺寸 (国标 mm)" if not is_en else "Nominal Dimensions (mm)")
        grp_geom.setStyleSheet(self._group_box_qss())
        grid_geom = QGridLayout(grp_geom)
        grid_geom.setContentsMargins(14, 22, 14, 12)
        grid_geom.setHorizontalSpacing(12)
        grid_geom.setVerticalSpacing(8)

        lbl_bare_dia = QLabel("公称裸线径 d (mm):" if not is_en else "Nominal Bare Dia (mm):")
        self.sb_bare_dia = ClickableDoubleSpinBox()
        self.sb_bare_dia.setRange(0.010, 5.000)
        self.sb_bare_dia.setDecimals(4)
        self.sb_bare_dia.setSingleStep(0.0005)
        self.sb_bare_dia.setValue(0.080)
        self.sb_bare_dia.setStyleSheet(self._input_field_qss())
        self.sb_bare_dia.valueChanged.connect(self._on_bare_dia_changed)

        lbl_max_od = QLabel("出厂最大外径 D (mm):" if not is_en else "Max Outer Dia D (mm):")
        self.sb_max_od = ClickableDoubleSpinBox()
        self.sb_max_od.setRange(0.012, 6.000)
        self.sb_max_od.setDecimals(4)
        self.sb_max_od.setSingleStep(0.0005)
        self.sb_max_od.setValue(0.089)
        self.sb_max_od.setStyleSheet(self._input_field_qss())

        grid_geom.addWidget(lbl_bare_dia, 0, 0)
        grid_geom.addWidget(self.sb_bare_dia, 0, 1)
        grid_geom.addWidget(lbl_max_od, 0, 2)
        grid_geom.addWidget(self.sb_max_od, 0, 3)

        layout.addWidget(grp_geom)

        # 4. 核心双向推导卡片 (铜导率 % IACS 与 出厂米阻 Ω/m 互推)
        grp_derivation = QGroupBox("⚡ 铜导率与出厂米阻联动推导 (二选一输入 · 双向闭环)" if not is_en else "⚡ Conductivity & Resistance Mutual Derivation")
        grp_derivation.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: 700;
                color: #0369A1;
                border: 1px solid #7DD3FC;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 6px;
                background-color: #F0F9FF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        vbox_deriv = QVBoxLayout(grp_derivation)
        vbox_deriv.setContentsMargins(14, 24, 14, 12)
        vbox_deriv.setSpacing(8)

        # 模式切换单选按钮
        mode_box = QHBoxLayout()
        mode_box.setSpacing(16)
        self.rb_mode_iacs = QRadioButton("① 设定铜导率 (% IACS) ➔ 自动反推米阻" if not is_en else "① Set % IACS ➔ Auto derive Rm")
        self.rb_mode_rm = QRadioButton("② 设定出厂米阻 (Ω/m) ➔ 自动反推铜导率" if not is_en else "② Set Rm (Ω/m) ➔ Auto derive % IACS")
        self.rb_mode_iacs.setChecked(True)
        self.rb_mode_iacs.setStyleSheet("font-size: 11px; font-weight: 600; color: #0C4A6E;")
        self.rb_mode_rm.setStyleSheet("font-size: 11px; font-weight: 600; color: #0C4A6E;")

        self.btn_grp_mode = QButtonGroup(self)
        self.btn_grp_mode.addButton(self.rb_mode_iacs, 1)
        self.btn_grp_mode.addButton(self.rb_mode_rm, 2)
        self.btn_grp_mode.idToggled.connect(self._on_derivation_mode_changed)

        mode_box.addWidget(self.rb_mode_iacs)
        mode_box.addWidget(self.rb_mode_rm)
        mode_box.addStretch()
        vbox_deriv.addLayout(mode_box)

        # 核心输入行 (采用清晰自适应横向布局，杜绝高度冲突重叠)
        row_deriv_inputs = QHBoxLayout()
        row_deriv_inputs.setSpacing(10)

        lbl_iacs = QLabel("铜导率 (% IACS):" if not is_en else "Conductivity (% IACS):")
        lbl_iacs.setStyleSheet("font-size: 11px; font-weight: 600; color: #1E293B;")
        self.sb_iacs = ClickableDoubleSpinBox()
        self.sb_iacs.setRange(10.0, 125.0)
        self.sb_iacs.setDecimals(2)
        self.sb_iacs.setSingleStep(0.5)
        self.sb_iacs.setValue(100.86)
        self.sb_iacs.setStyleSheet(self._input_field_qss())
        self.sb_iacs.valueChanged.connect(self._on_iacs_spin_changed)

        lbl_rm = QLabel("20℃ 出厂米阻 (Ω/m):" if not is_en else "20℃ Res (Ω/m):")
        lbl_rm.setStyleSheet("font-size: 11px; font-weight: 600; color: #1E293B;")
        self.sb_rm = ClickableDoubleSpinBox()
        self.sb_rm.setRange(0.00001, 20000.0)
        self.sb_rm.setDecimals(5)
        self.sb_rm.setSingleStep(0.0001)
        self.sb_rm.setValue(3.4007)
        self.sb_rm.setStyleSheet(self._input_field_qss())
        self.sb_rm.valueChanged.connect(self._on_rm_spin_changed)

        row_deriv_inputs.addWidget(lbl_iacs)
        row_deriv_inputs.addWidget(self.sb_iacs)
        row_deriv_inputs.addSpacing(10)
        row_deriv_inputs.addWidget(lbl_rm)
        row_deriv_inputs.addWidget(self.sb_rm)
        vbox_deriv.addLayout(row_deriv_inputs)

        # 派生结果提示行 (独立成行，宽敞美观)
        self.lbl_deriv_summary = QLabel()
        self.lbl_deriv_summary.setStyleSheet("""
            font-size: 11px;
            color: #0369A1;
            font-weight: 600;
            padding: 5px 8px;
            background-color: #E0F2FE;
            border: 1px solid #BAE6FD;
            border-radius: 4px;
        """)
        vbox_deriv.addWidget(self.lbl_deriv_summary)
        grp_derivation.setMinimumHeight(135)
        layout.addWidget(grp_derivation)

        # 5. 出厂重量与物理/机械性能 (出厂重量 m/kg, 击穿电压 BDV, 伸长率 %, 材料密度)
        grp_phys = QGroupBox("出厂重量与电气/机械指标 (国标 GB/T 6109)" if not is_en else "Factory Weight & Electrical/Mechanical Specs")
        grp_phys.setStyleSheet(self._group_box_qss())
        grid_phys = QGridLayout(grp_phys)
        grid_phys.setContentsMargins(14, 22, 14, 12)
        grid_phys.setHorizontalSpacing(12)
        grid_phys.setVerticalSpacing(8)

        lbl_m_kg = QLabel("出厂重量比 (m/kg):" if not is_en else "Yield Ratio (m/kg):")
        self.sb_m_kg = ClickableDoubleSpinBox()
        self.sb_m_kg.setRange(0.1, 5000000.0)
        self.sb_m_kg.setDecimals(1)
        self.sb_m_kg.setSingleStep(100.0)
        self.sb_m_kg.setValue(22353.2)
        self.sb_m_kg.setStyleSheet(self._input_field_qss())

        self.btn_calc_weight = QPushButton("⚡ 计算理论推荐值" if not is_en else "⚡ Calc Theoretical")
        self.btn_calc_weight.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calc_weight.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #0F172A;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }
        """)
        self.btn_calc_weight.clicked.connect(self._apply_theoretical_weight)

        lbl_density = QLabel("导体密度 (g/cm³):" if not is_en else "Density (g/cm³):")
        self.sb_density = ClickableDoubleSpinBox()
        self.sb_density.setRange(1.00, 20.00)
        self.sb_density.setDecimals(2)
        self.sb_density.setSingleStep(0.05)
        self.sb_density.setValue(8.90)
        self.sb_density.setStyleSheet(self._input_field_qss())
        self.sb_density.valueChanged.connect(self._on_density_changed)

        lbl_bdv = QLabel("击穿电压 BDV (V):" if not is_en else "Breakdown Voltage (V):")
        self.sb_bdv = ClickableDoubleSpinBox()
        self.sb_bdv.setRange(0.0, 30000.0)
        self.sb_bdv.setDecimals(0)
        self.sb_bdv.setSingleStep(100.0)
        self.sb_bdv.setValue(1800.0)
        self.sb_bdv.setStyleSheet(self._input_field_qss())

        lbl_elong = QLabel("出厂伸长率 (%):" if not is_en else "Elongation (%):")
        self.sb_elong = ClickableDoubleSpinBox()
        self.sb_elong.setRange(0.0, 100.0)
        self.sb_elong.setDecimals(1)
        self.sb_elong.setSingleStep(1.0)
        self.sb_elong.setValue(16.0)
        self.sb_elong.setStyleSheet(self._input_field_qss())

        # 布局
        weight_box = QHBoxLayout()
        weight_box.addWidget(self.sb_m_kg)
        weight_box.addWidget(self.btn_calc_weight)

        grid_phys.addWidget(lbl_m_kg, 0, 0)
        grid_phys.addLayout(weight_box, 0, 1)
        grid_phys.addWidget(lbl_density, 0, 2)
        grid_phys.addWidget(self.sb_density, 0, 3)

        grid_phys.addWidget(lbl_bdv, 1, 0)
        grid_phys.addWidget(self.sb_bdv, 1, 1)
        grid_phys.addWidget(lbl_elong, 1, 2)
        grid_phys.addWidget(self.sb_elong, 1, 3)

        layout.addWidget(grp_phys)

        # 6. 备注说明
        grp_note = QGroupBox("备注与出厂说明" if not is_en else "Notes")
        grp_note.setStyleSheet(self._group_box_qss())
        hbox_note = QHBoxLayout(grp_note)
        hbox_note.setContentsMargins(14, 20, 14, 12)
        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("可记录供应商批号、耐热等级或定制要求...")
        self.txt_note.setStyleSheet(self._input_field_qss())
        hbox_note.addWidget(self.txt_note)
        layout.addWidget(grp_note)

        # 7. 底部按钮
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("取消" if not is_en else "Cancel")
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
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("✔ 保存规格" if not is_en else "✔ Save Specification")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #0284C7;
                border-radius: 6px;
                padding: 6px 22px;
                font-size: 12px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

    def _group_box_qss(self) -> str:
        return """
            QGroupBox {
                font-size: 12px;
                font-weight: 700;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 6px;
                background-color: #F8FAFC;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """

    def _input_field_qss(self) -> str:
        return """
            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 3px 6px;
                min-height: 24px;
                font-size: 12px;
                color: #1E293B;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border-color: #0284C7;
            }
        """

    def _populate_initial_data(self):
        """装载初始数据"""
        if self.wire_item is not None:
            it = self.wire_item
            idx = self.combo_vendor.findText(it.vendor)
            if idx >= 0:
                self.combo_vendor.setCurrentIndex(idx)
            else:
                self.combo_vendor.setEditText(it.vendor)
            self.txt_model.setText(it.model)
            self.txt_spec.setText(it.spec_name)
            self.sb_bare_dia.setValue(it.bare_dia)
            self.sb_max_od.setValue(it.max_od)
            self.sb_iacs.setValue(it.copper_conductivity_iacs)
            self.sb_rm.setValue(it.meter_resistance_ohm)
            self.sb_m_kg.setValue(it.weight_m_per_kg)
            self.sb_density.setValue(it.density)
            self.sb_bdv.setValue(it.breakdown_voltage)
            self.sb_elong.setValue(it.elongation_pct)
            self.txt_note.setText(it.note)
        else:
            self._update_derivation(source="iacs")
            self._apply_theoretical_weight()

        self._refresh_summary_label()

    def _on_derivation_mode_changed(self, mode_id: int, checked: bool):
        if not checked:
            return
        self._active_derivation_mode = mode_id
        if mode_id == 1:
            self.sb_iacs.setEnabled(True)
            self.sb_rm.setEnabled(False)
            self._update_derivation(source="iacs")
        else:
            self.sb_iacs.setEnabled(False)
            self.sb_rm.setEnabled(True)
            self._update_derivation(source="rm")

    def _on_bare_dia_changed(self, val: float):
        if self._is_updating:
            return
        # 自动推荐外径 (如果之前是默认增量)
        if self.sb_max_od.value() < val:
            self.sb_max_od.setValue(round(val + 0.009, 4))
        # 根据当前模式重新推导
        if self._active_derivation_mode == 1:
            self._update_derivation(source="iacs")
        else:
            self._update_derivation(source="rm")
        self._apply_theoretical_weight()

    def _on_density_changed(self, val: float):
        self._apply_theoretical_weight()

    def _on_iacs_spin_changed(self, val: float):
        if self._is_updating or self._active_derivation_mode != 1:
            return
        self._update_derivation(source="iacs")

    def _on_rm_spin_changed(self, val: float):
        if self._is_updating or self._active_derivation_mode != 2:
            return
        self._update_derivation(source="rm")

    def _update_derivation(self, source: str = "iacs"):
        if self._is_updating:
            return
        self._is_updating = True
        try:
            d = self.sb_bare_dia.value()
            if source == "iacs":
                iacs = self.sb_iacs.value()
                rm, rho = calculate_rm_from_iacs(d, iacs)
                self.sb_rm.setValue(rm)
            else:
                rm = self.sb_rm.value()
                iacs, rho = calculate_iacs_from_rm(d, rm)
                self.sb_iacs.setValue(iacs)
            self._refresh_summary_label()
        finally:
            self._is_updating = False

    def _refresh_summary_label(self):
        d = self.sb_bare_dia.value()
        rm = self.sb_rm.value()
        iacs = self.sb_iacs.value()
        area = math.pi * (d ** 2) / 4.0
        rho = rm * area if area > 0 else 0.017241
        km_res = rm * 1000.0
        self.lbl_deriv_summary.setText(
            f"⚡ 闭环物理核算: 裸铜截面 {area:.6f} mm² | 电阻率 ρ={rho:.8f} Ω·mm²/m | 等效千米阻值 {km_res:.1f} Ω/km"
        )

    def _apply_theoretical_weight(self):
        d = self.sb_bare_dia.value()
        dens = self.sb_density.value()
        m_kg = calculate_theoretical_m_per_kg(d, dens)
        self.sb_m_kg.setValue(m_kg)

    def _on_save_clicked(self):
        vendor = self.combo_vendor.currentText().strip()
        model = self.txt_model.text().strip()
        if not vendor:
            QMessageBox.warning(self, "提示", "请输入线材厂商名称！")
            self.combo_vendor.setFocus()
            return
        if not model:
            QMessageBox.warning(self, "提示", "请输入线材型号/品名！")
            self.txt_model.setFocus()
            return

        d = self.sb_bare_dia.value()
        od = self.sb_max_od.value()
        if od < d:
            QMessageBox.warning(self, "数据异常", f"出厂最大外径 ({od:.4f}mm) 不能小于裸导体线径 ({d:.4f}mm)！")
            self.sb_max_od.setFocus()
            return

        spec = self.txt_spec.text().strip()
        if not spec:
            spec = f"{d:.3f}mm"

        rm = self.sb_rm.value()
        iacs = self.sb_iacs.value()
        area = math.pi * (d ** 2) / 4.0
        rho = rm * area

        wire_id = self.wire_item.id if (self.wire_item and self.wire_item.id) else str(uuid.uuid4())
        created_at = self.wire_item.created_at if self.wire_item else ""

        self.wire_item = CustomWireItem(
            id=wire_id,
            vendor=vendor,
            model=model,
            spec_name=spec,
            bare_dia=d,
            max_od=od,
            meter_resistance_ohm=rm,
            breakdown_voltage=self.sb_bdv.value(),
            elongation_pct=self.sb_elong.value(),
            copper_conductivity_iacs=iacs,
            resistivity=rho,
            weight_m_per_kg=self.sb_m_kg.value(),
            density=self.sb_density.value(),
            note=self.txt_note.text().strip(),
            created_at=created_at
        )

        self.accept()


class CustomWireLibraryDialog(QDialog):
    """自定义线材厂商数据库 · 规格全生命周期管理弹窗"""

    wire_applied = pyqtSignal(object)  # 发射选中的 CustomWireItem

    def __init__(self, current_diameter: float = 0.080, parent=None):
        super().__init__(parent)
        is_en = i18n.is_english()
        self.setWindowTitle("自定义线材厂商数据库 · 规格管理" if not is_en else "Custom Wire Vendor Catalog & Manager")
        self.resize(1020, 620)
        self.setMinimumSize(920, 500)

        self.manager: CustomWireManager = get_custom_wire_manager()
        self.selected_item: Optional[CustomWireItem] = None
        self._initial_diameter = current_diameter

        self._setup_ui()
        self._reload_table_data()

    def _setup_ui(self):
        is_en = i18n.is_english()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. 顶部标题栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_title = QLabel("📚 自定义线材厂商数据库 · 规格选型与管理")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E3A8A;")
        self.lbl_sub = QLabel("支持自定义厂商、型号、国标米阻、击穿电压、伸长率与铜导率推导 · 自由调入仿真计算")
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_sub)
        top_bar.addLayout(title_box)
        top_bar.addStretch()

        # 操作快捷按钮组
        self.btn_add = QPushButton("➕ 新增规格" if not is_en else "➕ Add Wire")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setStyleSheet(self._action_btn_qss(bg="#0284C7", fg="#FFFFFF", hover="#0369A1"))
        self.btn_add.clicked.connect(self._on_add_clicked)

        self.btn_edit = QPushButton("✏️ 编辑" if not is_en else "✏️ Edit")
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setStyleSheet(self._action_btn_qss(bg="#F1F5F9", fg="#334155", hover="#E2E8F0"))
        self.btn_edit.clicked.connect(self._on_edit_clicked)

        self.btn_clone = QPushButton("📋 克隆" if not is_en else "📋 Clone")
        self.btn_clone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clone.setStyleSheet(self._action_btn_qss(bg="#F1F5F9", fg="#334155", hover="#E2E8F0"))
        self.btn_clone.clicked.connect(self._on_clone_clicked)

        self.btn_delete = QPushButton("🗑️ 删除" if not is_en else "🗑️ Delete")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet(self._action_btn_qss(bg="#FEF2F2", fg="#DC2626", hover="#FEE2E2"))
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        self.btn_import = QPushButton("📥 导入" if not is_en else "📥 Import")
        self.btn_import.setStyleSheet(self._action_btn_qss(bg="#F8FAFC", fg="#475569", hover="#F1F5F9"))
        self.btn_import.clicked.connect(self._on_import_clicked)

        self.btn_export = QPushButton("📤 导出" if not is_en else "📤 Export")
        self.btn_export.setStyleSheet(self._action_btn_qss(bg="#F8FAFC", fg="#475569", hover="#F1F5F9"))
        self.btn_export.clicked.connect(self._on_export_clicked)

        top_bar.addWidget(self.btn_add)
        top_bar.addWidget(self.btn_edit)
        top_bar.addWidget(self.btn_clone)
        top_bar.addWidget(self.btn_delete)
        top_bar.addWidget(self.btn_import)
        top_bar.addWidget(self.btn_export)

        layout.addLayout(top_bar)

        # 2. 快捷搜索与厂商过滤
        search_box = QHBoxLayout()
        search_box.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 快速搜索厂商、型号、规格或线径 (例如: 华冶, 1UEW, 0.080)...")
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
        self.txt_search.textChanged.connect(self._apply_filter)
        search_box.addWidget(self.txt_search, 2)

        self.combo_vendor_filter = QComboBox()
        self.combo_vendor_filter.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1E293B;
            }
        """)
        self.combo_vendor_filter.currentIndexChanged.connect(self._apply_filter)
        search_box.addWidget(self.combo_vendor_filter, 1)

        self.lbl_count = QLabel("共 0 档规格")
        self.lbl_count.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; padding-left: 6px;")
        search_box.addWidget(self.lbl_count)

        layout.addLayout(search_box)

        # 3. 核心表格 (9 列国标展示)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "厂商 (Vendor)",
            "型号/品名",
            "公称裸径 (mm)",
            "出厂最大外径 (mm)",
            "20℃出厂阻值 (Ω/m)",
            "出厂重量比 (m/kg)",
            "击穿电压 (V)",
            "伸长率 (%)",
            "铜导率 (% IACS)"
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
                padding: 6px 10px;
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
                padding: 8px 8px;
                font-size: 11px;
            }
        """)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 135)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 95)

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

        self.btn_cancel = QPushButton("取消" if not is_en else "Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet(self._action_btn_qss(bg="#F1F5F9", fg="#475569", hover="#E2E8F0"))
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("✔ 调入所选线材到当前仿真" if not is_en else "✔ Apply Selected Wire")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("""
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
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        bottom_layout.addWidget(self.btn_apply)

        layout.addWidget(bottom_frame)

    def _action_btn_qss(self, bg: str, fg: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                color: {fg};
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """

    def _reload_table_data(self):
        items = self.manager.list_all()

        # 刷新厂商筛选下拉框
        curr_vendor = self.combo_vendor_filter.currentText()
        self.combo_vendor_filter.blockSignals(True)
        self.combo_vendor_filter.clear()
        self.combo_vendor_filter.addItem("全部厂商 (All Vendors)")
        vendors = sorted(list(set(it.vendor for it in items if it.vendor)))
        for v in vendors:
            self.combo_vendor_filter.addItem(v)
        idx = self.combo_vendor_filter.findText(curr_vendor)
        if idx >= 0:
            self.combo_vendor_filter.setCurrentIndex(idx)
        self.combo_vendor_filter.blockSignals(False)

        self.table.setRowCount(len(items))
        matched_row = -1

        for r, it in enumerate(items):
            c0 = QTableWidgetItem(it.vendor)
            c0.setData(Qt.ItemDataRole.UserRole, it)

            c1 = QTableWidgetItem(f"{it.model} ({it.spec_name})")
            c2 = QTableWidgetItem(f"{it.bare_dia:.4f}")
            c2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            c3 = QTableWidgetItem(f"{it.max_od:.4f}")
            c3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            c4 = QTableWidgetItem(f"{it.meter_resistance_ohm:.5f}")
            c4.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c4.setToolTip(f"国标米阻: {it.meter_resistance_ohm:.6f} Ω/m\n千米阻值: {it.km_resistance_ohm:.1f} Ω/km")

            c5 = QTableWidgetItem(f"{it.weight_m_per_kg:.1f}")
            c5.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c5.setToolTip(f"出厂米重比: {it.weight_m_per_kg:.1f} m/kg\n千米/公斤: {it.km_per_kg:.3f} km/kg")

            c6 = QTableWidgetItem(f"{it.breakdown_voltage:.0f}")
            c6.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            c7 = QTableWidgetItem(f"{it.elongation_pct:.1f}%")
            c7.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            c8 = QTableWidgetItem(f"{it.copper_conductivity_iacs:.1f}%")
            c8.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c8.setToolTip(f"电阻率 ρ: {it.resistivity:.8f} Ω·mm²/m")

            self.table.setItem(r, 0, c0)
            self.table.setItem(r, 1, c1)
            self.table.setItem(r, 2, c2)
            self.table.setItem(r, 3, c3)
            self.table.setItem(r, 4, c4)
            self.table.setItem(r, 5, c5)
            self.table.setItem(r, 6, c6)
            self.table.setItem(r, 7, c7)
            self.table.setItem(r, 8, c8)

            if matched_row < 0 and abs(it.bare_dia - self._initial_diameter) < 1e-4:
                matched_row = r

        self._apply_filter()

        if matched_row >= 0:
            self.table.selectRow(matched_row)
            self.table.scrollToItem(self.table.item(matched_row, 0))
        elif len(items) > 0:
            self.table.selectRow(0)

    def _apply_filter(self):
        q = self.txt_search.text().strip().lower()
        selected_vendor = self.combo_vendor_filter.currentText()
        is_all_vendor = ("全部厂商" in selected_vendor)

        visible_count = 0
        for r in range(self.table.rowCount()):
            c0 = self.table.item(r, 0)
            if not c0:
                continue
            it: CustomWireItem = c0.data(Qt.ItemDataRole.UserRole)
            if not it:
                continue

            vendor_match = is_all_vendor or (it.vendor == selected_vendor)
            query_match = True
            if q:
                search_targets = [
                    it.vendor.lower(),
                    it.model.lower(),
                    it.spec_name.lower(),
                    f"{it.bare_dia:.3f}",
                    f"{it.max_od:.3f}",
                    it.note.lower()
                ]
                query_match = any(q in target for target in search_targets)

            show = vendor_match and query_match
            self.table.setRowHidden(r, not show)
            if show:
                visible_count += 1

        self.lbl_count.setText(f"匹配 {visible_count} / {self.table.rowCount()} 档规格")

    def _on_table_selection_changed(self):
        sel = self.table.selectedItems()
        if not sel:
            self.selected_item = None
            self.lbl_selected_info.setText("当前未选定线规 (点击行选择)")
            self.btn_apply.setEnabled(False)
            return

        row = sel[0].row()
        item0 = self.table.item(row, 0)
        wire_item: CustomWireItem = item0.data(Qt.ItemDataRole.UserRole)
        self.selected_item = wire_item

        info = (
            f"已选定: 【{wire_item.vendor}】{wire_item.model} {wire_item.spec_name}  |  "
            f"裸径 {wire_item.bare_dia:.3f} mm  |  外径 {wire_item.max_od:.3f} mm  |  "
            f"阻值 {wire_item.meter_resistance_ohm:.4f} Ω/m  |  "
            f"米重比 {wire_item.weight_m_per_kg:.1f} m/kg  |  "
            f"耐压 {wire_item.breakdown_voltage:.0f} V"
        )
        self.lbl_selected_info.setText(info)
        self.btn_apply.setEnabled(True)

    def _on_table_double_clicked(self, item: QTableWidgetItem):
        self._on_table_selection_changed()
        if self.selected_item is not None:
            self._on_apply_clicked()

    def _on_add_clicked(self):
        dlg = CustomWireEditorDialog(wire_item=None, parent=self)
        if dlg.exec():
            if dlg.wire_item:
                self.manager.add(dlg.wire_item)
                self._reload_table_data()

    def _on_edit_clicked(self):
        if self.selected_item is None:
            QMessageBox.information(self, "提示", "请先在列表中选中要编辑的线材规格！")
            return
        dlg = CustomWireEditorDialog(wire_item=self.selected_item, parent=self)
        if dlg.exec():
            if dlg.wire_item:
                self.manager.update(dlg.wire_item)
                self._reload_table_data()

    def _on_clone_clicked(self):
        if self.selected_item is None:
            QMessageBox.information(self, "提示", "请先在列表中选中要克隆的线材规格！")
            return
        it = self.selected_item
        cloned = CustomWireItem(
            id=str(uuid.uuid4()),
            vendor=it.vendor,
            model=f"{it.model} (副本)",
            spec_name=it.spec_name,
            bare_dia=it.bare_dia,
            max_od=it.max_od,
            meter_resistance_ohm=it.meter_resistance_ohm,
            breakdown_voltage=it.breakdown_voltage,
            elongation_pct=it.elongation_pct,
            copper_conductivity_iacs=it.copper_conductivity_iacs,
            resistivity=it.resistivity,
            weight_m_per_kg=it.weight_m_per_kg,
            density=it.density,
            note=it.note
        )
        self.manager.add(cloned)
        self._reload_table_data()

    def _on_delete_clicked(self):
        if self.selected_item is None:
            QMessageBox.information(self, "提示", "请先在列表中选中要删除的线材规格！")
            return
        it = self.selected_item
        confirm = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除线材规格【{it.vendor} · {it.model} ({it.spec_name})】吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.manager.delete(it.id)
            self._reload_table_data()

    def _on_import_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入自定义线材库", "", "JSON Files (*.json);;All Files (*.*)"
        )
        if path:
            try:
                count = self.manager.import_from_json(path)
                QMessageBox.information(self, "导入成功", f"已成功导入 {count} 项线材规格！")
                self._reload_table_data()
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入文件失败: {e}")

    def _on_export_clicked(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出自定义线材库", "custom_wires_export.json", "JSON Files (*.json);;All Files (*.*)"
        )
        if path:
            try:
                self.manager.export_to_json(path)
                QMessageBox.information(self, "导出成功", f"线材库已成功导出至: {path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出失败: {e}")

    def _on_apply_clicked(self):
        if self.selected_item is not None:
            self.wire_applied.emit(self.selected_item)
            self.accept()
