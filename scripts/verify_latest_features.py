# -*- coding: utf-8 -*-
"""
Verification of user's 3 latest requests:
1. Non-self-bonding wire dropdown sorted strictly by 0级, 1级, 2级, 3级.
2. Left mouse double-click inside spinbox lineEdit selects the entire value (not just after decimal point).
3. Huaye wire catalog dialog removes OFC radio button (explained in notes banner),
   and new incoming wire dialog allows directly entering measured Rm and km/kg with physics engine integration.
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QEvent
from PyQt6.QtGui import QMouseEvent

from src.core.models import EnamelGrade, WireCatalogType
from src.gui.main_window import MainWindow
from src.gui.wire_catalog_dialog import WireCatalogDialog
from src.gui.incoming_wire_dialog import IncomingWireDialog, IncomingWireParams


def test_01_dropdown_order(window):
    print("\n--- 1. 验证非自粘线下拉选项排序: 0级 -> 1级 -> 2级 -> 3级 ---")
    items_text = [window.combo_enamel_grade.itemText(i) for i in range(window.combo_enamel_grade.count())]
    items_data = [window.combo_enamel_grade.itemData(i) for i in range(window.combo_enamel_grade.count())]

    print("当前下拉框完整列表:")
    for idx, (t, d) in enumerate(zip(items_text, items_data)):
        print(f"  [{idx}] {t} (Data: {d.name if hasattr(d, 'name') else d})")

    # 提取非自粘等级对应的索引
    idx_g0 = items_data.index(EnamelGrade.GRADE_0)
    idx_g1 = items_data.index(EnamelGrade.GRADE_1)
    idx_g2 = items_data.index(EnamelGrade.GRADE_2)
    idx_g3 = items_data.index(EnamelGrade.GRADE_3)

    assert idx_g0 < idx_g1 < idx_g2 < idx_g3, f"非自粘线顺序错误: 0级({idx_g0}), 1级({idx_g1}), 2级({idx_g2}), 3级({idx_g3})"
    assert "0 级" in items_text[idx_g0]
    assert "1 级" in items_text[idx_g1]
    assert "2 级" in items_text[idx_g2]
    assert "3 级" in items_text[idx_g3]
    print("✔ 非自粘线顺序严格按照: 0级、1级、2级、3级 排序校验通过！")


def test_02_double_click_select_all(window):
    print("\n--- 2. 验证鼠标左键双击输入框全选整个数值 (含小数点与前后整数/小数位) ---")
    test_boxes = [
        ("裸铜线径 (d)", window.sb_bare_dia),
        ("漆包外径 (D)", window.sb_max_od),
        ("线圈内长 (IL)", window.sb_inner_len),
        ("20℃铜电阻率", window.sb_copper_rho),
    ]

    for name, box in test_boxes:
        le = box.spin.lineEdit()
        val_str = le.text()

        # 模拟鼠标左键双击事件 (位于输入框中间)
        event = QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            QPointF(20, 10),
            QPointF(20, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        QApplication.sendEvent(le, event)
        QApplication.processEvents()

        selected = le.selectedText()
        print(f"  • {name}: 当前显示文本='{val_str}', 双击后选中文本='{selected}'")
        assert selected == val_str, f"{name} 双击未全选: '{selected}' != '{val_str}'"

    print("✔ 鼠标左键双击全选全部数值交互校验通过！方便用户直接键入替换数值！")


def test_03_wire_catalog_ofc_in_notes():
    print("\n--- 3. 验证华冶线材库弹窗 (仅纯铜/铜包铝双选项，无氧铜定制在说明中体现) ---")
    dlg = WireCatalogDialog(current_diameter=0.080, is_ccaw=False)
    assert not hasattr(dlg, "rb_ofc") or not dlg.rb_ofc.isVisible(), "无氧纯铜不应作为单独单选按钮出现"
    assert dlg.btn_group.buttons() == [dlg.rb_copper, dlg.rb_ccaw], "弹窗仅保留纯铜与铜包铝两档系列切换"
    
    notice = dlg.lbl_tip_notice.text()
    assert "无氧纯铜" in notice or "OFC" in notice
    assert "0.85%" in notice
    print(f"✔ 华冶线材库说明文本校验通过: {notice[:75]}...")
    dlg.close()


def test_04_incoming_wire_mode(window):
    print("\n--- 4. 验证直接输入线材来料参数 (米阻、一公斤多少米) 闭环仿真 ---")
    # 模拟从 IncomingWireDialog 载入一组进料检验数据
    params = IncomingWireParams(
        meter_resistance_ohm=10.7470,
        km_resistance_ohm=10747.0,
        km_per_kg=70.620,
        bare_dia=0.045,
        max_outer_dia=0.055,
        has_self_bonding=True,
        enamel_grade=EnamelGrade.SB_010,
        material_name="纯铜 (来料)",
        resistivity=0.01709402,
        density=8.90
    )

    window._apply_incoming_wire(params)
    assert abs(window.sb_bare_dia.value() - 0.045) < 1e-4
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4
    assert "【来料实测】" in window.lbl_catalog_selected.text()
    assert "10.747" in window.lbl_catalog_selected.text()
    assert "70.62" in window.lbl_catalog_selected.text()

    out = window.outputs
    # 验证电阻: R20 严格等于 总线长 * 10.7470 Ω/m
    expected_r20 = out.total_wire_len_m * 10.7470
    assert abs(out.r20 - expected_r20) < 1e-5, f"R20 计算不匹配: {out.r20} != {expected_r20}"

    # 验证导体重: W_cu 严格等于 总线长 / 70.620 km/kg
    expected_cu_weight = out.total_wire_len_m / 70.620
    assert abs(out.weight_cu_g - expected_cu_weight) < 1e-5, f"导体重计算不匹配: {out.weight_cu_g} != {expected_cu_weight}"

    print(f"✔ 来料实测闭环校验成功:")
    print(f"   线长: {out.total_wire_len_m:.3f} m")
    print(f"   实测米阻核算 R20: {out.r20:.4f} Ω (完全等于 L × 10.7470)")
    print(f"   实测线密度核算导体重: {out.weight_cu_g:.4f} g (完全等于 L / 70.620)")
    print(f"   漆膜重: {out.weight_ins_g:.4f} g | 公称总重: {out.weight_g:.4f} g")

    # 恢复自定义测试
    window._clear_catalog_wire()
    assert window.sb_bare_dia.isEnabled()
    assert window.sb_max_od.isEnabled()
    assert not window.btn_reset_wire.isVisible()
    print("✔ 点击恢复自定义后成功恢复自由调参！")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()

    test_01_dropdown_order(window)
    test_02_double_click_select_all(window)
    test_03_wire_catalog_ofc_in_notes()
    test_04_incoming_wire_mode(window)

    window.close()
    print("\n========================================================")
    print("🎉 ALL 4 LATEST USER REQUIREMENT TESTS PASSED (100%)!")
    print("========================================================")
