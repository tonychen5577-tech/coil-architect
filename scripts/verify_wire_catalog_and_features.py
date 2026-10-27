# -*- coding: utf-8 -*-
"""
自动化全流程集成测试：
1. 华冶纯铜 69 档与 15% 铜包铝 79 档出厂线规数据精度检验
2. 方线、扁线倒角削减与等效圆截面仿真计算校验
3. 双基准线圈称重核算校验 (纯铜重 + 漆重 vs 车间实测预测重)
4. 绝缘耐压 (3000VAC对地 / 1400V匝间冲击) 可靠性评估校验
5. PyQt6 GUI 无界面模式 (Offscreen) 控件联动与仿真自愈测试
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
    get_huaye_copper_wires, get_huaye_ccaw_wires, find_wire_by_diameter
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
    # 输入宽 0.80mm, 高 0.35mm, 倒角 0.08mm
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


def test_03_dual_baseline_weight():
    print("\n--- Test 3: Dual-Baseline Coil Weight Verification ---")
    # 纯铜圆线
    inp_cu = CoilInputs(
        wire_shape=WireShape.ROUND,
        bare_dia=0.080,
        max_od=0.083,
        wire_density=8.90,
        tension_factor=0.99
    )
    out_cu = CoilPhysicsEngine.calculate(inp_cu)

    assert out_cu.weight_cu_g > 0
    assert out_cu.weight_ins_g > 0
    assert abs(out_cu.weight_theoretical_g - (out_cu.weight_cu_g + out_cu.weight_ins_g)) < 1e-5
    # 车间预测重量由于负公差与拉伸，应略低于理论公称重量
    assert out_cu.weight_actual_expected_g < out_cu.weight_theoretical_g
    print(f"✔ 纯铜线圈 理论总重: {out_cu.weight_theoretical_g:.4f}g (铜: {out_cu.weight_cu_g:.4f}g, 漆: {out_cu.weight_ins_g:.4f}g)")
    print(f"✔ 车间实测预测重: {out_cu.weight_actual_expected_g:.4f}g (符合实际减重规律)")

    # 铜包铝圆线 (同尺寸线圈大幅减重)
    inp_ccaw = CoilInputs(
        wire_shape=WireShape.ROUND,
        wire_catalog_type=WireCatalogType.HUAYE_CCAW,
        bare_dia=0.080,
        max_od=0.083,
        wire_density=3.63,
        copper_resistivity=0.02525
    )
    out_ccaw = CoilPhysicsEngine.calculate(inp_ccaw)
    weight_ratio = out_ccaw.weight_theoretical_g / out_cu.weight_theoretical_g
    assert 0.40 < weight_ratio < 0.48, f"CCAW weight ratio {weight_ratio:.3f} expected ~0.42"
    print(f"✔ 铜包铝线圈 理论总重: {out_ccaw.weight_theoretical_g:.4f}g (仅纯铜的 {weight_ratio*100:.1f}%)")


def test_04_insulation_and_hipot():
    print("\n--- Test 4: Insulation & Hi-Pot Assessment Verification ---")
    # Grade 2 (工业推荐，加厚双涂层，击穿电压 2800V) -> 必须通过 1400V 匝间与 3000VAC 对地
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
    print(f"✔ Grade 2 加厚漆膜耐压评定通过: BDV={out_g2.turn_breakdown_voltage_v}V | 匝间耐压合格: {out_g2.hi_pot_turn_passed} | 评级: {out_g2.insulation_risk_level}")

    # Grade 0 (超薄微细涂层，击穿电压仅 750V) -> 必须触发 1400V 匝间不合格预警
    inp_g0 = CoilInputs(
        enamel_grade=EnamelGrade.GRADE_0,
        withstand_turn_v=1400.0
    )
    out_g0 = CoilPhysicsEngine.calculate(inp_g0)
    assert out_g0.hi_pot_turn_passed is False
    assert out_g0.insulation_risk_level == "WARNING"
    print(f"✔ Grade 0 超薄漆膜耐压预警成功触发: BDV={out_g0.turn_breakdown_voltage_v}V | 匝间预警: {out_g0.insulation_recommendation}")


def test_05_gui_headless():
    print("\n--- Test 5: Headless GUI Integration Verification ---")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    from src.gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    # 1. 测试线材形态切换
    window.combo_wire_shape.setCurrentIndex(2) # 切换至长方形扁线
    assert window.container_flat_wire.isVisible() is True
    assert window.container_round_wire.isVisible() is False

    # 2. 调节扁线尺寸
    window.sb_flat_w.setValue(0.90)
    window.sb_flat_h.setValue(0.40)
    window.sb_flat_r.setValue(0.08)
    assert window.outputs.flat_actual_area > 0.30
    print(f"✔ GUI 扁线参数响应正常，解算截面: {window.outputs.flat_actual_area:.4f} mm²")

    # 3. 测试华冶线规库切换
    window.combo_wire_shape.setCurrentIndex(0) # 切回圆线
    window.combo_wire_catalog.setCurrentIndex(1) # 华冶纯铜 69档
    assert window.combo_huaye_wire.isVisible() is True
    assert window.combo_huaye_wire.count() == 69

    # 选择第 10 档线规
    window.combo_huaye_wire.setCurrentIndex(10)
    item = window.combo_huaye_wire.currentData()
    assert abs(window.sb_bare_dia.value() - item.diameter) < 1e-4
    assert abs(window.sb_max_od.value() - item.max_outer_dia) < 1e-4
    print(f"✔ GUI 华冶纯铜规格联动成功: {item.display_label}")

    # 4. 切换为华冶 15% 铜包铝
    window.combo_wire_catalog.setCurrentIndex(2) # 华冶 CCAW 79档
    assert window.combo_huaye_wire.count() == 79
    window.combo_huaye_wire.setCurrentIndex(5)
    ccaw_item = window.combo_huaye_wire.currentData()
    assert abs(window.sb_copper_rho.value() - 0.02525) < 1e-5
    print(f"✔ GUI 华冶铜包铝规格联动成功: {ccaw_item.display_label}")

    # 5. 验证耐压芯片指示
    assert hasattr(window.dfm_strip, "chip_hipot")
    print(f"✔ DFM 耐压状态芯片存在且运行正常")

    window.close()
    print("✔ GUI 无头集成测试全部通过！")


if __name__ == "__main__":
    test_01_wire_catalog()
    test_02_flat_wire_physics()
    test_03_dual_baseline_weight()
    test_04_insulation_and_hipot()
    test_05_gui_headless()
    print("\n==========================================")
    print("🎉 ALL 5 INTEGRATION TESTS PASSED (100%)!")
    print("==========================================")
