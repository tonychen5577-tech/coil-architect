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
        flat_winding_dir=WindingDirection.FLATWISE
    )
    out = CoilPhysicsEngine.calculate(inp)

    assert abs(out.flat_actual_area - expected_area) < 1e-5
    assert abs(out.flat_eq_round_dia - expected_deq) < 1e-4
    assert out.flat_actual_area < w * h, "Fillet area must be strictly smaller than straight rectangular area"
    print(f"✔ 扁线倒角削减面积: {out.flat_actual_area:.5f} mm² (理论: {expected_area:.5f} mm²)")
    print(f"✔ 等效圆线径: {out.flat_eq_round_dia:.4f} mm")


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
    assert abs(window.sb_max_od.value() - 0.083) < 1e-4
    assert abs(getattr(window, "_catalog_km_kg", 0.0) - 22.3532) < 1e-3
    assert "22.35" in window.lbl_catalog_selected.text()

    # 4. 严格校验锁定机制：选定出厂线规后，必须锁定电导率等级及全部冲突几何/材质选项
    assert not window.combo_copper_grade.isEnabled(), "combo_copper_grade 必须锁定禁用"
    assert not window.sb_copper_rho.isEnabled(), "sb_copper_rho 必须锁定禁用"
    assert not window.sb_bare_dia.isEnabled(), "sb_bare_dia 必须锁定禁用"
    assert not window.sb_max_od.isEnabled(), "sb_max_od 必须锁定禁用"
    assert not window.combo_enamel_grade.isEnabled(), "combo_enamel_grade 必须锁定禁用"
    assert not window.chk_self_bonding.isEnabled(), "chk_self_bonding 必须锁定禁用"
    assert not window.combo_wire_shape.isEnabled(), "combo_wire_shape 必须锁定禁用"
    assert window.btn_reset_wire.isVisible(), "恢复自定义按钮必须显现"
    print("✔ 华冶线规防冲突锁定校验通过: 电导率等级、电阻率滑块、线径、外径、漆膜等级、自粘层、导线形状全部严格锁定！")

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

    window.close()
    print("✔ GUI 弹窗集成、电导率锁定与排查防冲突测试全部通过！")


if __name__ == "__main__":
    test_01_wire_catalog()
    test_02_flat_wire_physics()
    test_03_dual_baseline_and_catalog_weight()
    test_04_insulation_and_hipot()
    test_05_gui_dialog_and_material_presets()
    print("\n==========================================")
    print("🎉 ALL 5 INTEGRATION TESTS PASSED (100%)!")
    print("==========================================")
