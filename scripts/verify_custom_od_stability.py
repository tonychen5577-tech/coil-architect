# -*- coding: utf-8 -*-
"""
Verification script for user-reported operational bug:
Custom mode: bare diameter = 0.045 mm, max outer diameter = 0.055 mm.
Ensure:
1. combo_enamel_grade displays standard +0.010mm and +0.008mm self-bonding options.
2. When bare 0.045 and outer 0.055 are set, toggling self_bonding or changing settings DOES NOT overwrite 0.055 mm!
3. Active selection of +0.008 or +0.010 sets outer diameter accurately.
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication
from src.core.models import EnamelGrade
from src.gui.main_window import MainWindow

def test_custom_od_and_enamel_grade():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    window.show()

    print("\n--- Verifying Custom Mode OD Stability & Standard Increments ---")
    
    # 1. 验证下拉框中包含常规厂商标准选项
    items_text = [window.combo_enamel_grade.itemText(i) for i in range(window.combo_enamel_grade.count())]
    items_data = [window.combo_enamel_grade.itemData(i) for i in range(window.combo_enamel_grade.count())]
    print("下拉框选项:")
    for t, d in zip(items_text, items_data):
        print(f"  - {t} (Data: {d})")

    assert EnamelGrade.SB_010 in items_data, "Must contain standard +0.010mm option"
    assert EnamelGrade.SB_008 in items_data, "Must contain thin +0.008mm option"
    assert EnamelGrade.CUSTOM in items_data, "Must contain custom option"

    # 2. 用户设定裸线径 0.045，漆包外径 0.055
    print("\n步骤 1: 设定裸线径 0.045 mm, 漆包外径 0.055 mm")
    window.sb_bare_dia.setValue(0.045)
    window.sb_max_od.setValue(0.055)

    assert abs(window.sb_bare_dia.value() - 0.045) < 1e-4
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4

    # 验证自动对齐到常规标准自粘 (+0.010mm)
    assert window.combo_enamel_grade.currentData() == EnamelGrade.SB_010
    assert window.chk_self_bonding.isChecked() is True
    print(f"✔ 自动匹配预设成功: 当前下拉项为 [{window.combo_enamel_grade.currentText()}], 自粘勾选={window.chk_self_bonding.isChecked()}")

    # 3. 测试点击取消勾选复合热风自粘
    print("\n步骤 2: 取消勾选复合自粘胶层")
    window.chk_self_bonding.setChecked(False)
    # 核心验证: 外径 0.055 绝对不能发生变化！
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4, f"外径被意外篡改！当前为 {window.sb_max_od.value()}"
    print(f"✔ 取消自粘勾选后，外径完好保持: {window.sb_max_od.value():.3f} mm")

    # 4. 再次勾选复合自粘胶层
    print("\n步骤 3: 重新勾选复合自粘胶层")
    window.chk_self_bonding.setChecked(True)
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4, f"外径被意外篡改！当前为 {window.sb_max_od.value()}"
    print(f"✔ 重新勾选自粘后，外径完好保持: {window.sb_max_od.value():.3f} mm")

    # 5. 选择自定义外径
    print("\n步骤 4: 选择【自定义外径 (保持手动输入设定)】")
    for i in range(window.combo_enamel_grade.count()):
        if window.combo_enamel_grade.itemData(i) == EnamelGrade.CUSTOM:
            window.combo_enamel_grade.setCurrentIndex(i)
            break
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4, f"外径被意外篡改！当前为 {window.sb_max_od.value()}"
    print(f"✔ 选择自定义档位后，外径完好保持: {window.sb_max_od.value():.3f} mm")

    # 6. 用户主动从下拉框选择【薄胶复合自粘 (+0.008mm)】
    print("\n步骤 5: 用户主动选择【薄胶复合自粘 (漆膜+胶厚 +0.008mm)】")
    for i in range(window.combo_enamel_grade.count()):
        if window.combo_enamel_grade.itemData(i) == EnamelGrade.SB_008:
            window.combo_enamel_grade.setCurrentIndex(i)
            break
    expected_thin_od = round(0.045 + 0.008, 4)
    assert abs(window.sb_max_od.value() - expected_thin_od) < 1e-4, f"薄胶外径计算错误: {window.sb_max_od.value()} != {expected_thin_od}"
    print(f"✔ 薄胶复合自粘外径准确更新为: {window.sb_max_od.value():.3f} mm (0.045 + 0.008)")

    # 7. 用户主动从下拉框选择【常规标准自粘 (+0.010mm · +0.01 标配)】
    print("\n步骤 6: 用户主动选择【常规标准自粘 (漆膜+胶厚 +0.010mm · +0.01 标配)】")
    for i in range(window.combo_enamel_grade.count()):
        if window.combo_enamel_grade.itemData(i) == EnamelGrade.SB_010:
            window.combo_enamel_grade.setCurrentIndex(i)
            break
    expected_std_od = round(0.045 + 0.010, 4)
    assert abs(window.sb_max_od.value() - expected_std_od) < 1e-4, f"标准自粘外径计算错误: {window.sb_max_od.value()} != {expected_std_od}"
    print(f"✔ 常规标准自粘外径准确更新为: {window.sb_max_od.value():.3f} mm (0.045 + 0.010)")

    # 8. 验证再次切换勾选，外径依旧固若金汤
    print("\n步骤 7: 在标准自粘档位下切换自粘勾选")
    window.chk_self_bonding.setChecked(False)
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4
    window.chk_self_bonding.setChecked(True)
    assert abs(window.sb_max_od.value() - 0.055) < 1e-4
    print("✔ 任何自粘状态切换均绝不篡改外径！")

    window.close()
    print("\n🎉 ALL CUSTOM MODE OD STABILITY TESTS PASSED 100%!")

if __name__ == "__main__":
    test_custom_od_and_enamel_grade()
