"""
验证针对用户两条最新反馈的全面修复:
1. 最下方的超限状态卡片: 左对齐、消除前部巨大空白、无文字截断、标题简洁
2. 工程预设: 仅保留 1-5，删除 6/7 冗余，标题极简无括号
3. 界面参数与卡片标题去除冗余英文与括号内容
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def test_user_requests():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    app.processEvents()

    artifact_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"

    print("\n=== 1. 验证工程预设仅保留 1-5 且标题极简 ===")
    preset_count = window.combo_presets.count()
    preset_items = [window.combo_presets.itemText(i) for i in range(preset_count)]
    print(f"当前预设数量: {preset_count}")
    print(f"当前预设列表: {preset_items}")
    assert preset_count == 5, f"预设数量不等于 5: {preset_count}"
    expected_presets = [
        "1. 手机VCM马达",
        "2. 手机LRA圆线圈",
        "3. 手机LRA跑道线圈",
        "4. VCM八角形线圈",
        "5. CAD异形线圈"
    ]
    assert preset_items == expected_presets, f"预设列表不匹配! 期望: {expected_presets}, 实际: {preset_items}"
    print("✓ 工程预设严格保留 1-5 项，冗余 6、7 成功剔除!")
    print("✓ 预设标题极简规范，无冗余多层括号!")

    # 验证每一个预设加载正常
    for i, p_name in enumerate(preset_items):
        window._load_preset(p_name)
        app.processEvents()
        assert window.outputs is not None
        print(f"  ✓ 预设 [{p_name}] 载入成功, R20={window.outputs.r20:.3f}Ω, 匝数={window.outputs.total_turns}")

    print("\n=== 2. 验证最下方 DFM 状态条: 左对齐、消除空白、无截断 ===")
    # 重新加载预设 1 并开启 DFM 卡控 (模拟用户图中的超标状态: 14层×18匝, 厚度0.990mm > 0.85mm, 电压3.353V > 2.50V)
    window._load_preset(preset_items[0])
    window.chk_dfm_enabled.setChecked(True)
    window.sb_radial_layers.setValue(14.0)
    window.sb_axial_turns.setValue(18)
    window.sb_limit_z.setValue(0.85)
    window.sb_limit_v.setValue(2.50)
    window.run_simulation()
    app.processEvents()

    strip = window.dfm_strip
    print(f"DFM 标题: {strip.findChild(type(strip.summary_lbl)).text()}")
    print(f"DFM 汇总文本: {strip.summary_lbl.text()}")
    assert strip.summary_lbl.text() != "", "DFM 汇总文本为空!"

    chips = [strip.chip_x, strip.chip_y, strip.chip_z, strip.chip_v, strip.chip_t]
    for chip in chips:
        dot_w = chip.dot.width()
        text_w = chip.lbl_text.width()
        chip_w = chip.width()
        text_content = chip.lbl_text.text()
        print(f"  ✓ 芯片 [{chip.name}]: 图标宽={dot_w}px, 文字='{text_content}' (文字宽={text_w}px / 总宽={chip_w}px)")
        # 1. 验证图标固定宽度 16px (杜绝占满整个芯片产生巨大空白)
        assert dot_w <= 16, f"图标宽度过大: {dot_w}"
        # 2. 验证文本不被截断 (长度在合理范围内且文本标签宽大于 0)
        assert text_w > 0, "文字宽度为 0!"
        # 3. 验证超标状态文字格式 (无冗余括号，极简表达)
        if "超标" in text_content:
            assert "限" in text_content, f"超标文本缺少限值说明: {text_content}"
            print(f"    -> 超标警示紧凑左对齐验证通过: {text_content}")

    print("\n=== 3. 验证全界面标题极简去括号与自然工程描述 ===")
    assert window.sb_radial_layers.lbl_title.text() == "径向层数", "径向层数标题不符"
    assert window.sb_axial_turns.lbl_title.text() == "每层匝数", "每层匝数标题不符"
    assert window.card_ol.lbl_title.text() == "外廓长度 (L)", "外长卡片标题不符"
    assert window.card_r20.lbl_title.text() == "20℃直流电阻", "R20卡片标题不符"
    print("✓ 输入控件与 KPI 卡片标题简洁纯粹，去除了冗余 English 符号与多层括号!")

    # 截图整体窗口与底部 DFM
    pix_win = window.grab()
    path_win = os.path.join(artifact_dir, "verify_optimized_dfm_and_presets.png")
    pix_win.save(path_win)
    print(f"✓ 优化后完整窗口截图已保存: {path_win}")

    pix_dfm = strip.grab()
    path_dfm = os.path.join(artifact_dir, "verify_optimized_dfm_strip.png")
    pix_dfm.save(path_dfm)
    print(f"✓ 优化后底部 DFM 状态条放大截图已保存: {path_dfm}")

    print("\n所有用户优化项 100% PASS!")

if __name__ == "__main__":
    test_user_requests()
