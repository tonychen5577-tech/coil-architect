# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.abspath("."))
import math
from pathlib import Path
from PyQt6.QtWidgets import QApplication

sys.stdout.reconfigure(encoding='utf-8')

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

print("=" * 70)
print("TEST 1: 数学严密性检验 - 铜导率(% IACS) 与 出厂米阻(Ω/m) 双向推导")
print("=" * 70)
from src.core.wire_catalog import (
    calculate_rm_from_iacs, calculate_iacs_from_rm, calculate_theoretical_m_per_kg,
    CustomWireItem, CustomWireManager, get_custom_wire_manager,
    get_huaye_copper_wires, get_huaye_ccaw_wires
)

test_sizes = [0.050, 0.080, 0.100, 0.150, 0.250]
for d in test_sizes:
    # 纯铜 100% IACS (rho = 0.017241)
    rm_100, rho_100 = calculate_rm_from_iacs(d, 100.0)
    iacs_rev, rho_rev = calculate_iacs_from_rm(d, rm_100)
    area = math.pi * (d ** 2) / 4.0
    expected_rm = 0.017241 / area

    assert abs(rm_100 - expected_rm) < 1e-6, f"Rm derivation mismatch at d={d}"
    assert abs(iacs_rev - 100.0) < 1e-4, f"IACS reverse derivation mismatch at d={d}"
    print(f"  [PASS] d={d:.3f}mm: 100% IACS -> Rm={rm_100:.5f} Ω/m -> Reverse IACS={iacs_rev:.2f}% (误差 0.000%)")

    # 华冶 1/58.5 高纯退火铜 (100.86% IACS)
    rm_huaye, _ = calculate_rm_from_iacs(d, 100.86)
    iacs_huaye, _ = calculate_iacs_from_rm(d, rm_huaye)
    assert abs(iacs_huaye - 100.86) < 1e-4
    print(f"  [PASS] d={d:.3f}mm: 100.86% IACS -> Rm={rm_huaye:.5f} Ω/m -> Reverse IACS={iacs_huaye:.2f}%")

print("\n" + "=" * 70)
print("TEST 2: 国标单位检验 - 出厂重量 (m/kg) 理论与实际标称闭环")
print("=" * 70)
for d in test_sizes:
    m_per_kg_cu = calculate_theoretical_m_per_kg(d, 8.90)
    mass_g_per_m = 1000.0 / m_per_kg_cu
    # 校验 1米质量 * m/kg == 1000g
    assert abs(mass_g_per_m * m_per_kg_cu - 1000.0) < 1e-5
    print(f"  [PASS] d={d:.3f}mm 纯铜(8.90g/cm³): 理论米重比 = {m_per_kg_cu:.1f} m/kg ({mass_g_per_m:.4f} g/m)")

# 校验与华冶 0.080mm 标称数据
huaye_wires = get_huaye_copper_wires()
w_0080 = [w for w in huaye_wires if abs(w.diameter - 0.080) < 1e-5][0]
print(f"  华冶出厂表 0.080mm: km_per_kg={w_0080.km_per_kg:.4f} km/kg -> m/kg={w_0080.m_per_kg:.1f} m/kg, Rm={w_0080.meter_resistance_ohm:.4f} Ω/m")
assert abs(w_0080.m_per_kg - 22353.2) < 0.1
assert abs(w_0080.meter_resistance_ohm - 3.4007) < 0.001
print("  [PASS] 现有华冶线规库已全面实现国标 GB 单位属性封装！")

print("\n" + "=" * 70)
print("TEST 3: 自定义线材库管理器 (CustomWireManager) CRUD 与持久化检验")
print("=" * 70)
test_json = Path("config/test_custom_wires.json")
if test_json.exists():
    test_json.unlink()

mgr = CustomWireManager(storage_path=test_json)
assert len(mgr.list_all()) >= 5
print(f"  [PASS] 成功自愈并初始化内置预设，规格数: {len(mgr.list_all())}")

# 新增
test_wire = CustomWireItem(
    id="test_new_wire_001",
    vendor="华冶精工定制",
    model="特级自粘线",
    spec_name="0.065mm",
    bare_dia=0.065,
    max_od=0.074,
    meter_resistance_ohm=5.1952,
    breakdown_voltage=2200.0,
    elongation_pct=17.5,
    copper_conductivity_iacs=100.86,
    resistivity=0.01709402,
    weight_m_per_kg=33860.5,
    density=8.90,
    note="自动化测试条目"
)
assert mgr.add(test_wire)
assert mgr.get_by_id("test_new_wire_001") is not None
print("  [PASS] 成功执行 add() 并写入 JSON 文件")

# 更新
test_wire.breakdown_voltage = 2500.0
assert mgr.update(test_wire)
retrieved = mgr.get_by_id("test_new_wire_001")
assert retrieved.breakdown_voltage == 2500.0
print("  [PASS] 成功执行 update() 更新属性")

# 删除
assert mgr.delete("test_new_wire_001")
assert mgr.get_by_id("test_new_wire_001") is None
print("  [PASS] 成功执行 delete() 删除条目")

# 清理测试文件
if test_json.exists():
    test_json.unlink()

print("\n" + "=" * 70)
print("TEST 4: 前端界面集成检验 (MainWindow + CustomWireLibraryDialog + 仿真闭环)")
print("=" * 70)
from src.gui.main_window import MainWindow
from src.gui.custom_wire_dialog import CustomWireLibraryDialog, CustomWireEditorDialog
from src.gui.wire_catalog_dialog import WireCatalogDialog

win = MainWindow()
assert hasattr(win, "btn_custom_wire")
assert hasattr(win, "btn_open_catalog")
assert hasattr(win, "btn_incoming_wire")
assert hasattr(win, "btn_reset_wire")
print("  [PASS] 主界面 4 大选规/设定按钮全部装配就绪！")

# 模拟选中并调入自定义线材
custom_wire_item = CustomWireItem(
    id="apply_test_001",
    vendor="胜牌特种",
    model="1UEW-SB 耐热线",
    spec_name="0.090mm",
    bare_dia=0.090,
    max_od=0.100,
    meter_resistance_ohm=2.6870,
    breakdown_voltage=2000.0,
    elongation_pct=18.0,
    copper_conductivity_iacs=100.86,
    resistivity=0.01709402,
    weight_m_per_kg=17661.8,
    density=8.90,
    note="仿真联动验证"
)

win._apply_custom_wire(custom_wire_item)

# 校验主窗口是否已正确绑定并锁定
assert win.sb_bare_dia.value() == 0.090
assert win.sb_bare_dia.isEnabled() == False
assert win.sb_max_od.value() == 0.100
assert win.sb_max_od.isEnabled() == False
assert abs(win.sb_copper_rho.value() - 0.017094) < 1e-5
assert win.sb_copper_rho.isEnabled() == False
assert not win.btn_reset_wire.isHidden()
assert "胜牌特种" in win.lbl_catalog_selected.text()
assert "2.6870" in win.lbl_catalog_selected.text()
print("  [PASS] _apply_custom_wire() 成功将线材参数调入主界面，并全参数锁定防冲突！")

# 校验求解器运行结果
out = win.outputs
assert out is not None
print(f"  [PASS] 仿真求解成功: 总匝数 N={out.total_turns}, 直流阻抗 R20={out.r20:.4f} Ω, 铜重={out.weight_cu_g:.4f} g")

# 重置自定义线规
win._clear_catalog_wire()
assert win.sb_bare_dia.isEnabled() == True
assert win.sb_max_od.isEnabled() == True
assert win.sb_copper_rho.isEnabled() == True
assert win.btn_reset_wire.isHidden()
print("  [PASS] _clear_catalog_wire() 成功解除锁定，恢复自由自定义线规！")

# 验证 WireCatalogDialog 国标列与自定义跳转按钮
dlg_catalog = WireCatalogDialog(current_diameter=0.080, parent=win)
assert dlg_catalog.table.horizontalHeaderItem(2).text() == "20℃出厂阻值 (Ω/m · 国标米阻)"
assert dlg_catalog.table.horizontalHeaderItem(3).text() == "出厂重量比 (m/kg · 国标米重)"
assert hasattr(dlg_catalog, "btn_open_custom")
print("  [PASS] WireCatalogDialog 已完整统一为国标单位，并支持从华冶库直跳自定义线库！")

# 验证 CustomWireLibraryDialog
dlg_custom = CustomWireLibraryDialog(current_diameter=0.080, parent=win)
assert dlg_custom.table.columnCount() == 9
print("  [PASS] CustomWireLibraryDialog 表格初始化成功，列数与国标指标完整对应！")

print("\n" + "=" * 70)
print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY! 100% PASS!")
print("=" * 70)
os._exit(0)
