"""
验证底部可折叠方案比对抽屉模块：
1. 启动验证：比对抽屉正常加载，默认收起
2. 固化验证：点击 [📌 固化当前方案] 保存方案 1 为基准
3. 实时对比验证：修改参数后，Live 列实时显示相对于方案 1 的差异 Δ
4. 多方案固化：保存方案 2，比对矩阵同时展现多套方案与差值高亮
5. 一键还原验证：点击方案 1 的 [⏪ 还原]，界面参数完美回退
6. 复制对比表验证：剪贴板 TSV 格式数据正常
"""

import sys
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.gui.main_window import MainWindow

def test_comparison_drawer():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1366, 820)
    window.show()
    app.processEvents()

    drawer = window.comparison_drawer
    assert drawer is not None, "方案比对抽屉未正确加载!"
    print("\n=== 1. 验证方案比对抽屉默认收起状态 ===")
    assert not drawer._is_expanded, "比对抽屉默认应为收起状态!"
    print("✓ 比对抽屉默认折叠收起，占用高度极小，零打扰画布。")

    # 1. 加载八角形预设 4 (方案 1: 0.045/0.053, 13匝HCP)
    print("\n=== 2. 固化方案 1 (基准 Baseline) ===")
    window._load_preset("4. VCM八角形线圈")
    app.processEvents()

    # 点击固化
    drawer.capture_current_scheme()
    app.processEvents()

    assert len(drawer.snapshots) == 1, "方案 1 固化失败!"
    snap1 = drawer.snapshots[0]
    assert snap1.is_baseline, "首个方案应自动设为基准 Baseline!"
    print(f"✓ 成功固化方案 1: 匝数={snap1.outputs.total_turns}, H={snap1.outputs.thickness_h:.3f}mm, R20={snap1.outputs.r20:.2f}Ω, 设为基准={snap1.is_baseline}")
    assert drawer._is_expanded, "固化方案后应自动平滑展开抽屉以便工程师比对!"

    # 2. 微调参数：修改为 12 匝同数排布 (EVEN)
    print("\n=== 3. 参数微调并验证实时 Live 列差异计算 ===")
    window.combo_mode.setCurrentIndex(1)  # 同数 EVEN
    window.sb_axial_turns.setValue(12)    # 12 匝
    window.run_simulation()
    app.processEvents()

    # 检查 Live 列 (第 1 列) 的总匝数和差值
    live_turns_item = drawer.table.item(7, 1)  # 行7: 成型总匝数
    live_h_item = drawer.table.item(9, 1)      # 行9: 轴向成型厚度
    live_r20_item = drawer.table.item(10, 1)   # 行10: 20℃电阻

    print(f"  Live 列成型总匝数文本: '{live_turns_item.text()}'")
    print(f"  Live 列厚度文本: '{live_h_item.text()}'")
    print(f"  Live 列电阻文本: '{live_r20_item.text()}'")

    assert "-3" in live_turns_item.text(), f"匝数差值未正确标出 (-3): {live_turns_item.text()}"
    assert "72" in live_turns_item.text(), f"实时匝数不为 72: {live_turns_item.text()}"
    print("✓ Live 实时微调列能够动态计算并显示相对于基线方案 1 的差值 Δ！")

    # 3. 固化方案 2 (72匝同数版)
    print("\n=== 4. 固化方案 2 (同数12匝版) 并验证多方案并排对比 ===")
    drawer.capture_current_scheme()
    app.processEvents()

    assert len(drawer.snapshots) == 2, "方案 2 固化失败!"
    snap2 = drawer.snapshots[1]
    snap2.name = "同数12匝方案"
    drawer._rebuild_table_columns()
    app.processEvents()

    print(f"✓ 成功固化方案 2: 方案名='{snap2.name}', 匝数={snap2.outputs.total_turns}, H={snap2.outputs.thickness_h:.3f}mm, R20={snap2.outputs.r20:.2f}Ω")

    # 验证表格列数: 列0 (参数名), 列1 (Live), 列2 (方案1), 列3 (方案2)
    assert drawer.table.columnCount() == 4, f"表格列数不等于 4: {drawer.table.columnCount()}"
    print("✓ 表格成功展示 4 列：参数名 | 实时调参 (Live) | 方案 1 (基准) | 同数12匝方案")

    # 4. 验证一键还原功能：从方案 2 状态一键还原到方案 1 (13匝HCP)
    print("\n=== 5. 验证一键还原方案 1 ===")
    drawer.restore_requested.emit(snap1)
    app.processEvents()

    assert window.sb_axial_turns.value() == 13, f"匝数未还原回 13: {window.sb_axial_turns.value()}"
    assert window.combo_mode.currentIndex() == 0, f"排法未还原回 HCP: {window.combo_mode.currentIndex()}"
    assert window.outputs.total_turns == 75, f"总匝数未恢复 75: {window.outputs.total_turns}"
    print(f"✓ 点击一键还原后，左侧输入面板与物理引擎瞬间恢复至方案 1 (13匝HCP, 75匝, R20={window.outputs.r20:.2f}Ω)！")

    # 5. 验证剪贴板复制功能
    print("\n=== 6. 验证复制对比表至剪贴板 ===")
    drawer.copy_table_to_clipboard()
    tsv_text = QApplication.clipboard().text()
    assert "实时微调" in tsv_text, "剪贴板未包含实时列!"
    assert "方案 1" in tsv_text, "剪贴板未包含方案 1!"
    assert "同数12匝方案" in tsv_text, "剪贴板未包含方案 2!"
    print("✓ 成功生成 TSV 制表符格式对比表并写入剪贴板，可无缝粘贴至 Excel/Word！")
    print("剪贴板内容预览 (前 5 行):")
    for line in tsv_text.split("\n")[:5]:
        print("  ", line)

    # 截图保存为 artifact
    artifact_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    pix = window.grab()
    save_path = os.path.join(artifact_dir, "verify_comparison_drawer_full.png")
    pix.save(save_path)
    print(f"\n✓ 方案比对抽屉完整界面截图已保存: {save_path}")

    pix_drawer = drawer.grab()
    save_drawer_path = os.path.join(artifact_dir, "verify_comparison_drawer_widget.png")
    pix_drawer.save(save_drawer_path)
    print(f"✓ 方案比对抽屉局部高精截图已保存: {save_drawer_path}")

    print("\n全套功能 100% PASS！")

if __name__ == "__main__":
    try:
        test_comparison_drawer()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
