# -*- coding: utf-8 -*-
"""
自动化全流程集成测试：
1. 华冶纯铜 69 档与 15% 铜包铝 79 档出厂线规数据精度检验
2. 方线、扁线倒角削减与等效圆截面仿真计算校验
3. 双基准线圈称重核算校验 (调用选择的出厂线密度 KM/KG 直接核算)
4. 绝缘耐压 (3000VAC对地 / 1400V匝间冲击) 可靠性评估校验
5. 华冶 5 档电导率预设联动与密度自动同步校验
6. WireCatalogDialog 弹窗与无头 GUI 交互全流程测试
"""

import sys
import os
import math

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.core.models import (
    CoilInputs, CoilOutputs, CoilType, WindingMode,
    WireShape, WireCatalogType, EnamelGrade, WindingDirection
)
from src.core.wire_catalog import (
    WireCatalogItem, get_huaye_copper_wires, get_huaye_ccaw_wires, find_wire_by_diameter
)
from src.core.physics_engine import CoilPhysicsEngine


def test_01_wire_catalog():
    print("\n--- Test 1: Wire Catalog Verification ---")
    cu_wires = get_huaye_copper_wires()
    ccaw_wires = get_huaye_ccaw_wires()

    assert len(cu_wires) == 69, f"Expected 69 copper wires, got {len(cu_wires)}"
    assert len(ccaw_wires) == 79, f"Expected 79 CCAW wires, got {len(ccaw_wires)}"

    # 验证 0.080mm 纯铜规格 (华冶标准: 0.080mm, 外径 0.083mm, 3400.7472 Ω/km)
    cu_008 = find_wire_by_diameter(0.080, 1)
    assert cu_008 is not None
    assert abs(cu_008.diameter - 0.080) < 1e-4
    assert abs(cu_008.max_outer_dia - 0.083) < 1e-4
    assert abs(cu_008.km_resistance_ohm - 3400.7472) < 0.1
    assert cu_008.density == 8.90
    print(f"✔ 纯铜 0.080mm 规格校验通过: {cu_008.display_label}")

    # 验证 0.080mm 定制无氧纯铜规格 (华冶标准: 0.080mm, 外径 0.083mm, 3371.9263 Ω/km)
    ofc_008 = find_wire_by_diameter(0.080, 3)
    assert ofc_008 is not None
    assert abs(ofc_008.diameter - 0.080) < 1e-4
    assert abs(ofc_008.max_outer_dia - 0.083) < 1e-4
    assert abs(ofc_008.resistivity - 0.01694915) < 1e-6
    assert abs(ofc_008.km_resistance_ohm - 3371.9263) < 0.1
    print(f"✔ 无氧纯铜 (OFC) 0.080mm 规格校验通过: {ofc_008.display_label}")

    # 验证 0.080mm 15% 铜包铝规格 (华冶标准: 0.080mm, 5023.3279 Ω/km, 密度 3.63)
    ccaw_008 = find_wire_by_diameter(0.080, 2)
    assert ccaw_008 is not None
    assert abs(ccaw_008.diameter - 0.080) < 1e-4
    assert abs(ccaw_008.km_resistance_ohm - 5023.3279) < 0.1
    assert ccaw_008.density == 3.63
    print(f"✔ 15%铜包铝 0.080mm 规格校验通过: {ccaw_008.display_label}")


def test_02_flat_wire_physics():
    print("\n--- Test 2: Flat Wire Physics & Fillet Area Verification ---")
    w = 0.80
    h = 0.35
    r = 0.08
    expected_area = w * h - (4.0 - math.pi) * (r ** 2)
    expected_deq = 2.0 * math.sqrt(expected_area / math.pi)

    inp = CoilInputs(
        wire_shape=WireShape.RECTANGULAR,
        flat_w=w,
        flat_h=h,
        flat_r=r,
        flat_r_auto=False,
        enamel_grade=EnamelGrade.GRADE_2,
        flat_winding_dir=WindingDirection.FLATWISE,
        tension_factor=1.00
    )
    out = CoilPhysicsEngine.calculate(inp)

    assert abs(out.flat_actual_area - expected_area) < 1e-5
    assert abs(out.flat_eq_round_dia - expected_deq) < 1e-4
    assert out.flat_actual_area < w * h, "Fillet area must be strictly smaller than straight rectangular area"
    assert out.b_actual > out.d_actual, f"b_actual ({out.b_actual}) must be greater than d_actual ({out.d_actual})"
    print(f"✔ 扁线倒角削减面积: {out.flat_actual_area:.5f} mm² (理论: {expected_area:.5f} mm²)")
    print(f"✔ 等效圆线径: {out.flat_eq_round_dia:.4f} mm | 带漆外径: {out.b_actual:.4f} mm (b > d 校验通过)")

    # 验证方线 0.20x0.20 mm 严密消除倒挂缺陷
    inp_sq = CoilInputs(
        wire_shape=WireShape.SQUARE,
        flat_w=0.20,
        flat_h=0.20,
        flat_r=0.025,
        flat_r_auto=False,
        enamel_grade=EnamelGrade.GRADE_1,
        tension_factor=1.00
    )
    out_sq = CoilPhysicsEngine.calculate(inp_sq)
    assert out_sq.b_actual > out_sq.d_actual, "Square wire b_actual must be strictly greater than d_actual"
    print(f"✔ 0.20x0.20方线消除倒挂: d_actual={out_sq.d_actual:.4f} mm < b_actual={out_sq.b_actual:.4f} mm")

    # 验证三维工艺标准轴向刚性极限 (平绕宽面沿轴向4.0mm vs 立绕窄面沿轴向1.0mm)
    inp_fw = CoilInputs(wire_shape=WireShape.RECTANGULAR, flat_w=0.40, flat_h=0.10, axial_turns=10, flat_winding_dir=WindingDirection.FLATWISE, tension_factor=1.00)
    out_fw = CoilPhysicsEngine.calculate(inp_fw)
    assert abs(out_fw.h_solid_limit - 4.00) < 1e-4, f"Flatwise h_solid should be 4.00mm, got {out_fw.h_solid_limit}"
    assert out_fw.h_solid_limit < out_fw.free_thickness_h, "h_solid must be less than free thickness"

    inp_ew = CoilInputs(wire_shape=WireShape.RECTANGULAR, flat_w=0.40, flat_h=0.10, axial_turns=10, flat_winding_dir=WindingDirection.EDGEWISE, tension_factor=1.00)
    out_ew = CoilPhysicsEngine.calculate(inp_ew)
    assert abs(out_ew.h_solid_limit - 1.00) < 1e-4, f"Edgewise h_solid should be 1.00mm, got {out_ew.h_solid_limit}"
    assert out_ew.h_solid_limit < out_ew.free_thickness_h, "h_solid must be less than free thickness"
    print("✔ 扁线三维绕向轴向刚性极限校验通过: 平绕(4.0mm) / 立绕(1.0mm)")

    # 验证方线/扁线平直接触面恒为正交矩阵同数排布 (N = i * j = 4 * 10 = 40匝)
    inp_matrix = CoilInputs(wire_shape=WireShape.RECTANGULAR, radial_layers=4, axial_turns=10, winding_mode=WindingMode.VARIABLE)
    out_matrix = CoilPhysicsEngine.calculate(inp_matrix)
    assert out_matrix.total_turns == 40, f"Flat wire matrix must strictly be 40 turns, got {out_matrix.total_turns}"
    print("✔ 扁线正交矩阵整齐排布校验通过: 4层 x 10匝 = 40匝 (无异数空隙减匝)")


def test_03_dual_baseline_and_catalog_weight():
    print("\n--- Test 3: Dual-Baseline & Catalog KM/KG Weight Verification ---")
    # 纯铜圆线直接调用华冶出厂 KM/KG
    km_per_kg_cu = 22.3532  # 0.080mm 纯铜出厂线密度 (严格对应出厂标称裸导体米重)
    inp_catalog = CoilInputs(
        wire_shape=WireShape.ROUND,
        bare_dia=0.080,
        max_od=0.083,
        catalog_km_kg=km_per_kg_cu,
        wire_density=8.90,
        tension_factor=0.99
    )
    out_catalog = CoilPhysicsEngine.calculate(inp_catalog)

    # 验证导体净重严格等于 total_wire_len_m / km_per_kg
    expected_cu_weight = out_catalog.total_wire_len_m / km_per_kg_cu
    assert abs(out_catalog.weight_cu_g - expected_cu_weight) < 1e-5
    # 验证公称总重 = 导体净重 + 漆膜净重 (基于华冶 UEW 1.27 固化密度)
    assert abs(out_catalog.weight_theoretical_g - (out_catalog.weight_cu_g + out_catalog.weight_ins_g)) < 1e-5
    assert abs(out_catalog.weight_g - out_catalog.weight_theoretical_g) < 1e-5
    print(f"✔ 直接调用华冶出厂线密度 ({km_per_kg_cu} km/kg) 核算导体与漆膜重量:")
    print(f"   线长: {out_catalog.total_wire_len_m:.3f}m | 导体净重: {out_catalog.weight_cu_g:.4f}g | 漆膜重: {out_catalog.weight_ins_g:.4f}g")
    print(f"   公称总重: {out_catalog.weight_g:.4f}g | 车间实测预测重: {out_catalog.weight_actual_expected_g:.4f}g (计入张力拉伸修正)")


def test_04_insulation_and_hipot():
    print("\n--- Test 4: Insulation & Hi-Pot Assessment Verification ---")
    inp_g2 = CoilInputs(
        enamel_grade=EnamelGrade.GRADE_2,
        withstand_ground_vac=3000.0,
        withstand_turn_v=1400.0
    )
    out_g2 = CoilPhysicsEngine.calculate(inp_g2)
    assert out_g2.hi_pot_turn_passed is True
    assert out_g2.hi_pot_ground_passed is True
    assert out_g2.turn_breakdown_voltage_v >= 2800.0
    assert out_g2.insulation_risk_level in ("SAFE", "NORMAL")
    print(f"✔ Grade 2 加厚漆膜耐压评定通过: BDV={out_g2.turn_breakdown_voltage_v}V | 匝间耐压合格: True | 评级: {out_g2.insulation_risk_level}")


def test_05_gui_dialog_and_material_presets():
    print("\n--- Test 5: WireCatalogDialog & 5 Material Presets Verification ---")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)

    from src.gui.wire_catalog_dialog import WireCatalogDialog
    from src.gui.main_window import MainWindow

    # 1. 测试 WireCatalogDialog 弹窗本身的数据加载、尺寸与过滤
    dlg = WireCatalogDialog(current_diameter=0.080, is_ccaw=False)
    assert dlg.width() >= 900, "Dialog width should be widened to >= 900px"
    assert dlg.table.rowCount() == 69, "Copper table must have 69 rows"
    assert dlg.table.columnCount() == 4, "Table must have 4 columns (线径, 外径, KM阻值, KM/KG)"

    # 切换至铜包铝
    dlg.rb_ccaw.setChecked(True)
    assert dlg.table.rowCount() == 79, "CCAW table must have 79 rows"

    # 测试即时搜索过滤
    dlg.txt_search.setText("0.15")
    visible_rows = [r for r in range(dlg.table.rowCount()) if not dlg.table.isRowHidden(r)]
    assert len(visible_rows) > 0, "Filter should match 0.15mm"
    print(f"✔ WireCatalogDialog 弹窗尺寸({dlg.width()}x{dlg.height()})、4 列指标与即时过滤校验通过！")
    dlg.close()

    # 2. 测试 MainWindow 集成与华冶 5 档电导率预设
    window = MainWindow()
    window.show()

    # 按钮名称简化为：华冶线材库
    assert "华冶线材库" in window.btn_open_catalog.text()
    print("✔ 主界面按钮名称简化校验通过: [华冶线材库]")

    # 检查电导率下拉框的 5 档华冶参数
    presets = [
        (0, "纯铜 (华冶实测经验值)", 0.01709402, 8.90),
        (1, "纯铜 (国标 100% IACS)", 0.01724138, 8.90),
        (2, "无氧纯铜 (高纯退火态)", 0.01694915, 8.90),
        (3, "15% 铜包铝 (CCAW 经验值)", 0.02525000, 3.63),
        (4, "电工纯铝 (EC-1350)", 0.02826000, 2.70),
    ]

    for idx, name, exp_rho, exp_density in presets:
        window.combo_copper_grade.setCurrentIndex(idx)
        assert abs(window.sb_copper_rho.value() - exp_rho) < 1e-5
        assert abs(getattr(window, "_current_wire_density", 8.90) - exp_density) < 1e-4
        print(f"✔ 华冶电导率预设 [{name}]: 电阻率={exp_rho:.6f} | 密度={exp_density:.2f} 同步正确")

    # 3. 测试通过弹窗选中 0.080mm 纯铜并载入仿真
    cu_item = find_wire_by_diameter(0.080, 1)
    window._apply_catalog_wire(cu_item)
    assert abs(window.sb_bare_dia.value() - 0.080) < 1e-4
    # 默认勾选自粘线：外径自动适配 1UEW-SB (0.083 + 0.006 = 0.089mm)
    assert abs(window.sb_max_od.value() - 0.089) < 1e-4
    assert abs(getattr(window, "_catalog_km_kg", 0.0) - 22.3532) < 1e-3
    assert "22.35" in window.lbl_catalog_selected.text()
    assert "1UEW-SB" in window.lbl_catalog_selected.text()

    # 测试取消自粘层：外径自动回退为标准 1UEW (0.083mm)
    window.chk_self_bonding.setChecked(False)
    assert abs(window.sb_max_od.value() - 0.083) < 1e-4
    assert "1UEW" in window.lbl_catalog_selected.text()

    # 4. 校验材质联动机制：选定出厂铜线后，铜材质选择器保持可用（支持标准纯铜与无氧纯铜一秒无缝比对切换）
    assert window.combo_copper_grade.isEnabled(), "combo_copper_grade 必须保持可用以支持标准纯铜与定制无氧铜比对"
    assert not window.sb_copper_rho.isEnabled(), "sb_copper_rho 必须锁定禁用"
    assert not window.sb_bare_dia.isEnabled(), "sb_bare_dia 必须锁定禁用"
    assert not window.sb_max_od.isEnabled(), "sb_max_od 必须锁定禁用"
    assert not window.combo_enamel_grade.isEnabled(), "combo_enamel_grade 必须锁定禁用"
    assert window.chk_self_bonding.isEnabled(), "chk_self_bonding 允许自由切换 1UEW 与 1UEW-SB"
    assert not window.combo_wire_shape.isEnabled(), "combo_wire_shape 必须锁定禁用"
    assert window.btn_reset_wire.isVisible(), "恢复自定义按钮必须显现"

    # 测试主界面一键切换为【无氧纯铜 (高纯退火态)】
    r_before = window.outputs.r20
    window.combo_copper_grade.setCurrentIndex(2) # 切换至无氧铜
    assert abs(window.sb_copper_rho.value() - 0.016949) < 1e-5
    assert "无氧纯铜" in window.lbl_catalog_selected.text()
    assert window.outputs.r20 < r_before, "无氧纯铜电阻必须严格低于普通纯铜"
    reduction_pct = (r_before - window.outputs.r20) / r_before * 100.0
    assert abs(reduction_pct - 0.848) < 0.05, f"降阻比例应约为 0.85%，实际 {reduction_pct:.3f}%"
    print(f"✔ 华冶铜线材质一键比对校验通过: 切换无氧纯铜(OFC)后电阻成功下降 {reduction_pct:.3f}% (R20: {r_before:.4f}Ω -> {window.outputs.r20:.4f}Ω)")

    # 测试尝试切换为铝线：智能防冲突拦截并重置
    window.combo_copper_grade.setCurrentIndex(4) # 纯铝
    assert window.combo_copper_grade.currentIndex() in (0, 2), "铜线模具不可直接混切为铝线"
    print("✔ 铜铝模具防冲突保护校验通过: 智能拦截非法铜铝混切！")

    # 验证仿真计算直接调用出厂 KM/KG 计算导体净重，并基于华冶漆膜密度计算绝缘重
    assert abs(window.outputs.weight_cu_g - (window.outputs.total_wire_len_m / 22.3532)) < 1e-4
    assert window.outputs.weight_ins_g > 0.0
    assert abs(window.outputs.weight_g - (window.outputs.weight_cu_g + window.outputs.weight_ins_g)) < 1e-5
    print(f"✔ 仿真计算成功调用华冶出厂重量参数: 导体净重={window.outputs.weight_cu_g:.4f}g | 漆膜重={window.outputs.weight_ins_g:.4f}g | 总重={window.outputs.weight_g:.4f}g")

    # 5. 测试点击【恢复自定义】一键解除锁定
    window._clear_catalog_wire()
    assert window.combo_copper_grade.isEnabled(), "combo_copper_grade 必须恢复可用"
    assert window.sb_copper_rho.isEnabled(), "sb_copper_rho 必须恢复可用"
    assert window.sb_bare_dia.isEnabled(), "sb_bare_dia 必须恢复可用"
    assert window.sb_max_od.isEnabled(), "sb_max_od 必须恢复可用"
    assert window.combo_enamel_grade.isEnabled(), "combo_enamel_grade 必须恢复可用"
    assert window.chk_self_bonding.isEnabled(), "chk_self_bonding 必须恢复可用"
    assert window.combo_wire_shape.isEnabled(), "combo_wire_shape 必须恢复可用"
    assert not window.btn_reset_wire.isVisible(), "恢复自定义按钮必须隐藏"
    assert window._current_catalog_item is None, "_current_catalog_item 必须置空"
    assert window._catalog_km_kg == 0.0, "_catalog_km_kg 必须清零"
    print("✔ 一键【恢复自定义】校验通过: 所有被锁定的冲突参数 100% 恢复自由调参！")

    # 6. 自定义模式下防外径被篡改与厂商标准 +0.010mm / +0.008mm 联动验证
    items_data = [window.combo_enamel_grade.itemData(i) for i in range(window.combo_enamel_grade.count())]
    assert EnamelGrade.SB_010 in items_data
    assert EnamelGrade.SB_008 in items_data
    assert EnamelGrade.CUSTOM in items_data

    # 设定裸径 0.045, 外径 0.055
    window.sb_bare_dia.setValue(0.045)
    window.sb_max_od.setValue(0.055)
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4
    assert window.combo_enamel_grade.currentData() == EnamelGrade.SB_010
    assert window.chk_self_bonding.isChecked() is True

    # 切换自粘勾选，绝不篡改 0.055 外径
    window.chk_self_bonding.setChecked(False)
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4
    window.chk_self_bonding.setChecked(True)
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4

    # 选择自定义档位，绝不篡改 0.055 外径
    for i in range(window.combo_enamel_grade.count()):
        if window.combo_enamel_grade.itemData(i) == EnamelGrade.CUSTOM:
            window.combo_enamel_grade.setCurrentIndex(i)
            break
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4

    # 主动选择薄胶自粘 (+0.008mm)
    for i in range(window.combo_enamel_grade.count()):
        if window.combo_enamel_grade.itemData(i) == EnamelGrade.SB_008:
            window.combo_enamel_grade.setCurrentIndex(i)
            break
    assert abs(window.sb_max_od.value() - 0.053) < 1e-4

    # 主动选择常规标准自粘 (+0.010mm)
    for i in range(window.combo_enamel_grade.count()):
        if window.combo_enamel_grade.itemData(i) == EnamelGrade.SB_010:
            window.combo_enamel_grade.setCurrentIndex(i)
            break
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4

    print("✔ 自定义模式外径防篡改与常规厂商 +0.010mm/+0.008mm 标准联动测试全部通过！")

    # 5. 方线/扁线专属双输入与圆线切方线自动调用同步测试
    window.sb_bare_dia.setValue(0.045)
    window.sb_max_od.setValue(0.055)

    # 切换至方线 (SQUARE)
    for i in range(window.combo_wire_shape.count()):
        if window.combo_wire_shape.itemData(i) == WireShape.SQUARE:
            window.combo_wire_shape.setCurrentIndex(i)
            break

    assert not window.container_flat_wire.isHidden()
    assert window.container_round_wire.isHidden()
    assert abs(window.sb_flat_w.value() - 0.045) < 1e-4
    assert abs(window.sb_flat_max_w.value() - 0.055) < 1e-4
    assert window.sb_flat_h.isHidden()
    assert window.sb_flat_max_h.isHidden()
    assert "正方边长" in window.sb_flat_w.lbl_title.text()
    assert "漆包外径" in window.sb_flat_max_w.lbl_title.text()
    assert abs(window.sb_flat_r.value() - 0.020) < 1e-4
    print("✔ 圆线切方线裸径与漆包外径自动同步通过: a=0.045mm, D=0.055mm, r=0.020mm")

    # 切换至长方形扁线 (RECTANGULAR)
    for i in range(window.combo_wire_shape.count()):
        if window.combo_wire_shape.itemData(i) == WireShape.RECTANGULAR:
            window.combo_wire_shape.setCurrentIndex(i)
            break

    assert not window.sb_flat_h.isHidden()
    assert not window.sb_flat_max_h.isHidden()
    assert "宽边宽度" in window.sb_flat_w.lbl_title.text()
    assert "高边厚度" in window.sb_flat_h.lbl_title.text()
    assert "带漆外宽" in window.sb_flat_max_w.lbl_title.text()
    assert "带漆外厚" in window.sb_flat_max_h.lbl_title.text()
    print("✔ 矩形扁线四项双输入控件展示正确")

    # 手动输入带漆外径与微小 R 角并验证工程文件保存/读取
    window.sb_flat_w.setValue(0.300)
    window.sb_flat_h.setValue(0.080)
    window.sb_flat_max_w.setValue(0.320)
    window.sb_flat_max_h.setValue(0.100)
    window.sb_flat_r.setValue(0.015)

    test_proj = os.path.abspath("test_temp_flat_wire.ansvcoil")
    import json
    try:
        inp_export = window._collect_inputs()
        data = {
            "version": "1.1.0",
            "file_type": "ANSV_COIL_PROJECT",
            "project_name": "Flat_Wire_Test",
            "inputs": {
                "coil_type": int(inp_export.coil_type),
                "inner_len": inp_export.inner_len,
                "inner_wid": inp_export.inner_wid,
                "radial_layers": inp_export.radial_layers,
                "axial_turns": inp_export.axial_turns,
                "winding_mode": int(inp_export.winding_mode),
                "wire_shape": int(inp_export.wire_shape),
                "flat_w": inp_export.flat_w,
                "flat_h": inp_export.flat_h,
                "flat_max_w": inp_export.flat_max_w,
                "flat_max_h": inp_export.flat_max_h,
                "flat_r": inp_export.flat_r,
                "flat_winding_dir": int(inp_export.flat_winding_dir),
            }
        }
        with open(test_proj, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        load_ok = window.load_project_file(test_proj)
        assert load_ok is True
        assert window.combo_wire_shape.currentData() == WireShape.RECTANGULAR
        assert abs(window.sb_flat_w.value() - 0.300) < 1e-4
        assert abs(window.sb_flat_h.value() - 0.080) < 1e-4
        assert abs(window.sb_flat_max_w.value() - 0.320) < 1e-4
        assert abs(window.sb_flat_max_h.value() - 0.100) < 1e-4
        assert abs(window.sb_flat_r.value() - 0.015) < 1e-4
        print("✔ 工程文件保存与载入 100% 恢复方线与扁线双输入参数！")
    finally:
        if os.path.exists(test_proj):
            os.remove(test_proj)

    window.close()
    print("✔ GUI 弹窗集成、电导率锁定与排查防冲突测试全部通过！")



def test_06_huaye_r_angle_and_dual_od():
    print("\n--- Test 6: Huaye Shaped Wire R-Angle & Dual Input Verification ---")
    
    # 1. 大宽厚比超薄扁线 (0.06 x 0.25, 宽厚比 4.167 >= 2.5) -> 全圆边 flat_r = r_max = 0.030mm
    inp_thin = CoilInputs(
        wire_shape=WireShape.RECTANGULAR,
        flat_w=0.25,
        flat_h=0.06,
        flat_r_auto=True,
    )
    out_thin = CoilPhysicsEngine.calculate(inp_thin)
    assert abs(out_thin.flat_r - 0.030) < 1e-4, f"Expected 0.030mm, got {out_thin.flat_r}"
    assert not out_thin.is_sharp_corner_risk, "Full round narrow side must not trigger sharp corner risk"
    print(f"✔ 超薄扁线 (0.06x0.25) 全圆边自动 R 角校验通过: r={out_thin.flat_r:.3f}mm")

    # 2. 方线 0.07 x 0.07 -> 自动取华冶涂漆安全最小基准 0.020mm
    inp_sq_small = CoilInputs(
        wire_shape=WireShape.SQUARE,
        flat_w=0.07,
        flat_h=0.07,
        flat_r_auto=True,
    )
    out_sq_small = CoilPhysicsEngine.calculate(inp_sq_small)
    assert abs(out_sq_small.flat_r - 0.020) < 1e-4, f"Expected 0.020mm, got {out_sq_small.flat_r}"
    assert not out_sq_small.is_sharp_corner_risk
    print(f"✔ 微型方线 (0.07x0.07) 华冶安全涂漆基准 R 角校验通过: r={out_sq_small.flat_r:.3f}mm")

    # 3. 较大方线 0.45 x 0.45 -> round(0.45 * 0.09, 3) = 0.040mm (上限 0.040mm)
    inp_sq_large = CoilInputs(
        wire_shape=WireShape.SQUARE,
        flat_w=0.45,
        flat_h=0.45,
        flat_r_auto=True,
    )
    out_sq_large = CoilPhysicsEngine.calculate(inp_sq_large)
    assert abs(out_sq_large.flat_r - 0.040) < 1e-4, f"Expected 0.040mm, got {out_sq_large.flat_r}"
    print(f"✔ 常规方线 (0.45x0.45) 推荐标准 R 角校验通过: r={out_sq_large.flat_r:.3f}mm")

    # 4. 手动微小 R 角 (0.010mm < 0.020mm) 触发尖角缩漆风险与耐压折减联动
    inp_sharp = CoilInputs(
        wire_shape=WireShape.RECTANGULAR,
        flat_w=0.25,
        flat_h=0.08,
        flat_r=0.010,
        flat_r_auto=False,
        enamel_grade=EnamelGrade.GRADE_2,
        has_self_bonding=False,
    )
    out_sharp = CoilPhysicsEngine.calculate(inp_sharp)
    assert abs(out_sharp.flat_r - 0.010) < 1e-4
    assert out_sharp.is_sharp_corner_risk is True, "R=0.010mm must trigger sharp corner risk"
    assert "【尖角缩漆预警】" in out_sharp.insulation_recommendation
    # 验证击穿电压折减: 正常 Grade 2 为 2800V, 折减后应为 2800 * (0.010/0.020)^0.6 ≈ 1847V
    assert out_sharp.turn_breakdown_voltage_v < 2000
    print(f"✔ 尖角缩漆预警 (<0.020mm) 与耐压折减联动校验通过: BDV={out_sharp.turn_breakdown_voltage_v:.0f}V | 风险警报已追加")

    # 5. 扁线/方线带漆外径双输入支持
    inp_dual = CoilInputs(
        wire_shape=WireShape.RECTANGULAR,
        flat_w=0.80,
        flat_h=0.35,
        flat_max_w=0.820,
        flat_max_h=0.370,
        flat_r=0.040,
        flat_r_auto=False,
    )
    out_dual = CoilPhysicsEngine.calculate(inp_dual)
    assert out_dual.b_actual > out_dual.d_actual
    print(f"✔ 扁线带漆外径双输入 (0.82x0.37) 优先解算校验通过: b_actual={out_dual.b_actual:.4f}mm")

    # 6. Wheeler 电感公制单位制系数 (0.007874) 校验
    inp_circ = CoilInputs(
        coil_type=CoilType.CIRCULAR,
        inner_len=2.30,
        radial_layers=8,
        axial_turns=26,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.042,
        max_od=0.052,
    )
    out_circ = CoilPhysicsEngine.calculate(inp_circ)
    assert 80 < out_circ.inductance_uh < 110, f"Expected ~95uH, got {out_circ.inductance_uh}uH"
    print(f"✔ Wheeler 公制标准电感校验通过: L={out_circ.inductance_uh:.2f}μH ({out_circ.inductance_mh:.4f}mH)")

if __name__ == "__main__":
    test_01_wire_catalog()
    test_02_flat_wire_physics()
    test_03_dual_baseline_and_catalog_weight()
    test_04_insulation_and_hipot()
    test_05_gui_dialog_and_material_presets()
    test_06_huaye_r_angle_and_dual_od()
    print("\n==========================================")
    print("🎉 ALL 6 INTEGRATION TESTS PASSED (100%)!")
    print("==========================================")
