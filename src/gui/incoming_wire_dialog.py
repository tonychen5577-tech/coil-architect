# -*- coding: utf-8 -*-
"""
Coil-Architect Pro - 线材来料检验参数直接输入弹窗 (Incoming Wire Dialog)
允许用户直接输入线材供应商出厂/来料检验核心指标：
1. 实测常温米阻 (Ω/m 或 Ω/km 双向即时换算)
2. 实测一公斤多少米 (km/kg 或 m/kg 线密度)
3. 实测漆包外径 D (mm)
4. 公称裸导体线径 d (mm，支持根据米阻与铜材电导率一键智能反推)
5. 导体材质与漆膜自粘层配置
直接绑定物理求解器，以实测数据 100% 真实还原线圈直流阻抗与线材质量。
"""

import math
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QComboBox, QCheckBox, QSizePolicy
)

from ..core.models import EnamelGrade
from ..core.i18n import i18n, t
from .widgets.slider_spin_box import ClickableDoubleSpinBox


@dataclass
class IncomingWireParams:
    """来料实测线材参数"""
    meter_resistance_ohm: float     # 实测米阻 (Ω/m)
    km_resistance_ohm: float        # 实测千米阻值 (Ω/km)
    km_per_kg: float                # 一公斤多少千米 (km/kg)
    bare_dia: float                 # 公称裸导体直径 (mm)
    max_outer_dia: float            # 实测漆包外径 (mm)
    has_self_bonding: bool          # 是否含自粘胶层
    enamel_grade: EnamelGrade       # 漆膜绝缘等级
    material_name: str              # 导体材质名称
    resistivity: float              # 材料基准电阻率 (Ω·mm²/m)
    density: float                  # 材料密度 (g/cm³)


class IncomingWireDialog(QDialog):
    """线材来料参数直接输入弹窗"""

    params_applied = pyqtSignal(object)  # 发射 IncomingWireParams

    def __init__(
        self,
        current_bare_dia: float = 0.045,
        current_max_od: float = 0.055,
        current_rm: float = 10.747,
        current_km_kg: float = 70.620,
        has_self_bonding: bool = True,
        enamel_grade: EnamelGrade = EnamelGrade.SB_010,
        parent=None
    ):
        super().__init__(parent)
        is_en = i18n.is_english()
        self.setWindowTitle("线材来料检验实测参数直入" if not is_en else "Direct Incoming Wire Parameters Input")
        self.resize(680, 520)
        self.setMinimumSize(620, 480)

        self._init_bare_dia = current_bare_dia
        self._init_max_od = current_max_od
        self._init_rm = current_rm
        self._init_km_kg = current_km_kg
        self._init_has_sb = has_self_bonding
        self._init_enamel_grade = enamel_grade

        self._is_updating = False
        self._setup_ui()
        self._update_calculation_preview()

    def _setup_ui(self):
        is_en = i18n.is_english()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. 顶部标题与说明
        top_box = QVBoxLayout()
        top_box.setSpacing(3)
        self.lbl_title = QLabel("⚡ 线材来料实测参数设定 (供应商进料指标直接导入)")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E3A8A;")
        self.lbl_sub = QLabel(
            "直接输入供应商出厂检验单或实验室实测的【米阻】与【一公斤多少米】，求解器将直接调用该物理参数核算阻抗与重量。"
            if not is_en else
            "Enter incoming test report parameters (Ohm/m and km/kg). Physics engine calculates resistance and weight directly."
        )
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        top_box.addWidget(self.lbl_title)
        top_box.addWidget(self.lbl_sub)
        layout.addLayout(top_box)

        # 2. 核心输入卡片
        grp_inputs = QGroupBox("来料实测核心参数输入" if not is_en else "Incoming Test Measurements")
        grp_inputs.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: 700;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                background-color: #F8FAFC;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """)
        grid = QGridLayout(grp_inputs)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # 2.1 常温实测米阻 (Ω/m) 与 千米阻值 (Ω/km)
        lbl_rm = QLabel("实测常温米阻 (Ω/m):" if not is_en else "Measured Res (Ω/m):")
        lbl_rm.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.sb_rm = ClickableDoubleSpinBox()
        self.sb_rm.setRange(0.0001, 50000.0)
        self.sb_rm.setDecimals(4)
        self.sb_rm.setSingleStep(0.1)
        self.sb_rm.setValue(self._init_rm if self._init_rm > 0 else 10.7470)
        self.sb_rm.valueChanged.connect(self._on_rm_changed)

        lbl_km_res = QLabel("等效千米阻值 (Ω/km):" if not is_en else "Equiv Res (Ω/km):")
        lbl_km_res.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        self.sb_km_res = ClickableDoubleSpinBox()
        self.sb_km_res.setRange(0.1, 50000000.0)
        self.sb_km_res.setDecimals(1)
        self.sb_km_res.setSingleStep(100.0)
        self.sb_km_res.setValue(self.sb_rm.value() * 1000.0)
        self.sb_km_res.valueChanged.connect(self._on_km_res_changed)

        grid.addWidget(lbl_rm, 0, 0)
        grid.addWidget(self.sb_rm, 0, 1)
        grid.addWidget(lbl_km_res, 0, 2)
        grid.addWidget(self.sb_km_res, 0, 3)

        # 2.2 一公斤多少米 (km/kg) 与 米重 (g/m)
        lbl_km_kg = QLabel("一公斤多少米 (km/kg):" if not is_en else "Wire Yield (km/kg):")
        lbl_km_kg.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.sb_km_kg = ClickableDoubleSpinBox()
        self.sb_km_kg.setRange(0.01, 20000.0)
        self.sb_km_kg.setDecimals(3)
        self.sb_km_kg.setSingleStep(1.0)
        self.sb_km_kg.setValue(self._init_km_kg if self._init_km_kg > 0 else 70.620)
        self.sb_km_kg.valueChanged.connect(self._on_km_kg_changed)

        self.lbl_g_per_m = QLabel("裸导体米重: -- g/m" if not is_en else "Linear mass: -- g/m")
        self.lbl_g_per_m.setStyleSheet("font-size: 11px; color: #0284C7; font-weight: 600;")

        grid.addWidget(lbl_km_kg, 1, 0)
        grid.addWidget(self.sb_km_kg, 1, 1)
        grid.addWidget(self.lbl_g_per_m, 1, 2, 1, 2)

        # 2.3 实测漆包外径 D 与 裸线径 d
        lbl_od = QLabel("实测漆包外径 D (mm):" if not is_en else "Outer Diameter D (mm):")
        lbl_od.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.sb_od = ClickableDoubleSpinBox()
        self.sb_od.setRange(0.012, 5.000)
        self.sb_od.setDecimals(3)
        self.sb_od.setSingleStep(0.001)
        self.sb_od.setValue(self._init_max_od)
        self.sb_od.valueChanged.connect(self._on_geometry_changed)

        lbl_bare = QLabel("公称导体裸径 d (mm):" if not is_en else "Bare Diameter d (mm):")
        lbl_bare.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.sb_bare = ClickableDoubleSpinBox()
        self.sb_bare.setRange(0.010, 4.000)
        self.sb_bare.setDecimals(3)
        self.sb_bare.setSingleStep(0.001)
        self.sb_bare.setValue(self._init_bare_dia)
        self.sb_bare.valueChanged.connect(self._on_geometry_changed)

        grid.addWidget(lbl_od, 2, 0)
        grid.addWidget(self.sb_od, 2, 1)
        grid.addWidget(lbl_bare, 2, 2)
        grid.addWidget(self.sb_bare, 2, 3)

        # 智能反算辅助按钮
        btn_calc_d = QPushButton("📐 依米阻自动推算裸径" if not is_en else "📐 Infer bare d from Res")
        btn_calc_d.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_calc_d.setStyleSheet("""
            QPushButton {
                background-color: #E0F2FE;
                border: 1px solid #7DD3FC;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #0369A1;
            }
            QPushButton:hover {
                background-color: #BAE6FD;
            }
        """)
        btn_calc_d.clicked.connect(self._auto_infer_bare_dia)
        grid.addWidget(btn_calc_d, 3, 2, 1, 2)

        layout.addWidget(grp_inputs)

        # 3. 导体材质与自粘绝缘属性卡片
        grp_mat = QGroupBox("材质类型与绝缘自粘配置" if not is_en else "Material & Insulation Setup")
        grp_mat.setStyleSheet(grp_inputs.styleSheet())
        mat_layout = QGridLayout(grp_mat)
        mat_layout.setContentsMargins(14, 14, 14, 14)
        mat_layout.setHorizontalSpacing(14)
        mat_layout.setVerticalSpacing(8)

        lbl_mat = QLabel("导体材质基准:" if not is_en else "Conductor Material:")
        lbl_mat.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.combo_material = QComboBox()
        self.combo_material.addItem("纯铜 (华冶实测 1/58.5 · ρ=0.017094)", (0.01709402, 8.90, "纯铜"))
        self.combo_material.addItem("无氧纯铜 (高纯退火态 1/59.0 · ρ=0.016949)", (0.01694915, 8.90, "无氧纯铜"))
        self.combo_material.addItem("15% 铜包铝 (CCAW 经验值 · ρ=0.025250)", (0.02525000, 3.63, "15%铜包铝"))
        self.combo_material.addItem("纯铜 (国标 100% IACS · ρ=0.017241)", (0.01724138, 8.90, "国标纯铜"))
        self.combo_material.currentIndexChanged.connect(self._on_material_changed)

        mat_layout.addWidget(lbl_mat, 0, 0)
        mat_layout.addWidget(self.combo_material, 0, 1, 1, 2)

        lbl_grade = QLabel("漆膜绝缘等级:" if not is_en else "Enamel Grade:")
        lbl_grade.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.combo_enamel = QComboBox()
        self.combo_enamel.addItem("常规标准自粘 (漆膜+胶厚 +0.010mm · +0.01 标配)", EnamelGrade.SB_010)
        self.combo_enamel.addItem("薄胶复合自粘 (漆膜+胶厚 +0.008mm)", EnamelGrade.SB_008)
        self.combo_enamel.addItem("加厚复合自粘 (漆膜+胶厚 +0.014mm · 2UEW-SB)", EnamelGrade.SB_014)
        self.combo_enamel.addItem("0 级超薄漆膜 (非自粘 1UEW, 外径+0.003mm)", EnamelGrade.GRADE_0)
        self.combo_enamel.addItem("1 级单涂层 (非自粘 1UEW, 外径+0.008mm)", EnamelGrade.GRADE_1)
        self.combo_enamel.addItem("2 级加厚双涂层 (非自粘 2UEW, 外径+0.014mm)", EnamelGrade.GRADE_2)
        self.combo_enamel.addItem("3 级特厚涂层 (非自粘 3UEW, 外径+0.022mm)", EnamelGrade.GRADE_3)
        self.combo_enamel.addItem("自定义外径 (保持手动设定)", EnamelGrade.CUSTOM)
        self.combo_enamel.currentIndexChanged.connect(self._update_calculation_preview)

        # 选中当前初始等级
        for idx in range(self.combo_enamel.count()):
            if self.combo_enamel.itemData(idx) == self._init_enamel_grade:
                self.combo_enamel.setCurrentIndex(idx)
                break

        self.chk_sb = QCheckBox("复合热风/酒精自粘胶层 (Self-Bonding)" if not is_en else "Composite Self-Bonding Coat")
        self.chk_sb.setChecked(self._init_has_sb)
        self.chk_sb.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.chk_sb.toggled.connect(self._update_calculation_preview)

        mat_layout.addWidget(lbl_grade, 1, 0)
        mat_layout.addWidget(self.combo_enamel, 1, 1)
        mat_layout.addWidget(self.chk_sb, 1, 2)

        layout.addWidget(grp_mat)

        # 4. 实时对账与推算看板
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 8px;
            }
        """)
        prev_layout = QVBoxLayout(self.preview_frame)
        prev_layout.setContentsMargins(12, 10, 12, 10)
        prev_layout.setSpacing(4)

        self.lbl_preview_title = QLabel("📊 来料实测参数对账核算分析:" if not is_en else "📊 Measurement Reconciliation Analysis:")
        self.lbl_preview_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #166534;")
        self.lbl_preview_detail = QLabel()
        self.lbl_preview_detail.setStyleSheet("font-size: 11px; color: #15803D;")
        self.lbl_preview_detail.setWordWrap(True)

        prev_layout.addWidget(self.lbl_preview_title)
        prev_layout.addWidget(self.lbl_preview_detail)
        layout.addWidget(self.preview_frame)

        layout.addStretch()

        # 5. 底部按钮栏
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_cancel = QPushButton("取消" if not is_en else "Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 18px;
                font-size: 12px;
                font-weight: 600;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_apply = QPushButton("✔ 确认并载入仿真" if not is_en else "✔ Apply to Simulation")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #0284C7;
                border-radius: 6px;
                padding: 7px 22px;
                font-size: 12px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_apply.clicked.connect(self._on_apply_clicked)

        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_cancel)
        btn_bar.addWidget(self.btn_apply)
        layout.addLayout(btn_bar)

    def _on_rm_changed(self, rm: float):
        if self._is_updating:
            return
        self._is_updating = True
        self.sb_km_res.setValue(round(rm * 1000.0, 1))
        self._is_updating = False
        self._update_calculation_preview()

    def _on_km_res_changed(self, km_res: float):
        if self._is_updating:
            return
        self._is_updating = True
        self.sb_rm.setValue(round(km_res / 1000.0, 4))
        self._is_updating = False
        self._update_calculation_preview()

    def _on_km_kg_changed(self, km_kg: float):
        self._update_calculation_preview()

    def _on_geometry_changed(self):
        self._update_calculation_preview()

    def _on_material_changed(self):
        self._update_calculation_preview()

    def _auto_infer_bare_dia(self):
        """根据当前实测米阻与材料电阻率推导公称裸径"""
        rm = self.sb_rm.value()
        rho, density, mat_name = self.combo_material.currentData()
        if rm > 1e-6 and rho > 1e-6:
            area = rho / rm
            d_calc = round(2.0 * math.sqrt(area / math.pi), 3)
            self.sb_bare.setValue(d_calc)

    def _update_calculation_preview(self):
        rm = self.sb_rm.value()
        km_res = self.sb_km_res.value()
        km_kg = self.sb_km_kg.value()
        od = self.sb_od.value()
        bare = self.sb_bare.value()
        rho, density, mat_name = self.combo_material.currentData()

        # 计算米重
        g_per_m = (1000.0 / km_kg) if km_kg > 0 else 0.0
        self.lbl_g_per_m.setText(f"裸导体米重: {g_per_m:.5f} g/m ({km_kg * 1000:.0f} m/kg)")

        # 理论推导截面积与裸径
        a_theo = (rho / rm) if rm > 1e-6 else 0.0
        d_theo = (2.0 * math.sqrt(a_theo / math.pi)) if a_theo > 0 else 0.0
        delta_thick = round(od - bare, 4)

        is_en = i18n.is_english()
        if not is_en:
            text = (
                f"• 实测米阻: {rm:.4f} Ω/m  |  千米阻值: {km_res:.1f} Ω/km\n"
                f"• 出厂线密度: {km_kg:.3f} km/kg (每千克可绕 {km_kg * 1000:.0f} 米导体)\n"
                f"• 依据电阻率(ρ={rho:.6f})推算等效裸径: {d_theo:.4f} mm (当前设定: {bare:.3f} mm)\n"
                f"• 漆膜与胶层总外径增量: +{delta_thick:.3f} mm (成品外径: {od:.3f} mm)\n"
                f"• 仿真求解保障: 阻抗直接采用 L × {rm:.4f}Ω/m，导体重量直接采用 L / {km_kg:.3f}km/kg 100% 实测直接闭环！"
            )
        else:
            text = (
                f"• Measured Rm: {rm:.4f} Ω/m  |  Km resistance: {km_res:.1f} Ω/km\n"
                f"• Wire yield: {km_kg:.3f} km/kg ({km_kg * 1000:.0f} m/kg bare conductor)\n"
                f"• Inferred bare dia: {d_theo:.4f} mm (Current setup: {bare:.3f} mm)\n"
                f"• Total coating buildup: +{delta_thick:.3f} mm (Finished OD: {od:.3f} mm)\n"
                f"• Solver guarantee: Resistance L * {rm:.4f}Ω/m, conductor mass L / {km_kg:.3f}km/kg."
            )
        self.lbl_preview_detail.setText(text)

    def _on_apply_clicked(self):
        rho, density, mat_name = self.combo_material.currentData()
        params = IncomingWireParams(
            meter_resistance_ohm=round(self.sb_rm.value(), 6),
            km_resistance_ohm=round(self.sb_km_res.value(), 2),
            km_per_kg=round(self.sb_km_kg.value(), 4),
            bare_dia=round(self.sb_bare.value(), 4),
            max_outer_dia=round(self.sb_od.value(), 4),
            has_self_bonding=self.chk_sb.isChecked(),
            enamel_grade=self.combo_enamel.currentData(),
            material_name=mat_name,
            resistivity=rho,
            density=density
        )
        self.params_applied.emit(params)
        self.accept()
