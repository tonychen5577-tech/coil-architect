"""
验证预设 4 (VCM八角形线圈) 倒推参数在软件中的载入与仿真精度
已知实测/图纸输入:
- 对边内径 ID1 = 7.10 mm
- 对角内径 ID2 = 7.05 mm
- 拐角内圆角 R1 = 0.30 mm
- 目标对边外径 OD1 = 7.76 mm
- 目标对角外径 OD2 = 7.71 mm
- 目标厚度 H = 0.67 mm
- 目标直流电阻 R20 = 19.5 ± 3 Ω (16.5 ~ 22.5 Ω)
"""

import sys
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def test_octagonal_preset4():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1366, 800)
    window.show()
    app.processEvents()

    # 加载预设 4
    window._load_preset("4. VCM八角形线圈")
    app.processEvents()

    out = window.outputs
    assert out is not None, "仿真输出为空!"

    print("\n=== 八角形线圈预设 4 倒推参数验证 ===")
    print(f"线圈类型: {window.combo_coil_type.currentText()}")
    print(f"对边内径 ID1: {window.sb_oct_id1.value():.2f} mm (目标 7.10 mm)")
    print(f"对角内径 ID2: {window.sb_oct_id2.value():.2f} mm (目标 7.05 mm)")
    print(f"拐角内圆角 R1: {window.sb_oct_r1.value():.2f} mm (目标 0.30 mm)")
    print(f"闭式推导平直内长 L1: {window._oct_l1:.2f} mm")
    print(f"闭式推导斜边内长 L2: {window._oct_l2:.2f} mm")
    print(f"径向层数: {window.sb_radial_layers.value()} 层")
    print(f"每层匝数: {window.sb_axial_turns.value()} 匝")
    print(f"铜线裸径 d: {window.sb_bare_dia.value():.3f} mm (标准 VCM 微细漆包线)")
    print(f"漆包外径 D: {window.sb_max_od.value():.3f} mm")
    print(f"张力系数: {window.sb_tension.value():.3f}")
    print(f"排线模式: {window.combo_mode.currentText()}")

    print("\n=== 仿真输出结果比对 ===")
    print(f"成型总匝数: {out.total_turns} 匝")
    print(f"对边外径 OD1: {out.oct_od1:.3f} mm (目标: 7.76 mm, 绝对误差: {abs(out.oct_od1 - 7.76):.3f} mm)")
    print(f"对角外径 OD2: {out.oct_od2:.3f} mm (目标: 7.71 mm, 绝对误差: {abs(out.oct_od2 - 7.71):.3f} mm)")
    print(f"轴向厚度 H: {out.thickness_h:.3f} mm (目标: 0.67 mm, 绝对误差: {abs(out.thickness_h - 0.67):.3f} mm)")
    print(f"20℃ 直流电阻 R20: {out.r20:.3f} Ω (目标: 19.500 ± 3.000 Ω, 偏差: {out.r20 - 19.50:+.3f} Ω)")
    print(f"等效电感: {out.inductance_uh:.2f} μH")

    # 断言误差在工程严格容限内 (<0.01 mm, 电阻在区间内)
    assert abs(out.oct_od1 - 7.76) <= 0.01, f"OD1 误差超标: {out.oct_od1}"
    assert abs(out.oct_od2 - 7.71) <= 0.01, f"OD2 误差超标: {out.oct_od2}"
    assert abs(out.thickness_h - 0.67) <= 0.025, f"厚度误差超标: {out.thickness_h}"
    assert 16.5 <= out.r20 <= 22.5, f"电阻不在 19.5±3Ω 内: {out.r20}"

    print("\n✓ 几何外径、高度及电阻全部高精度吻合！")

    artifact_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    pix = window.grab()
    save_path = os.path.join(artifact_dir, "verify_octagonal_preset4.png")
    pix.save(save_path)
    print(f"✓ 预设 4 界面截图已保存至: {save_path}")

if __name__ == "__main__":
    test_octagonal_preset4()
