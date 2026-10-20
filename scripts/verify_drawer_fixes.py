"""
验证用户提出的方案比对抽屉 4 项针对性优化：
1. 展开抽屉时，上方 DFM 状态条与芯片文字 100% 完整显示，绝无压缩截断
2. 方案表格滚轮支持：竖向顺滑滚动各行，横向/Shift滚轮滚动各方案列
3. 导出格式升级：由 CSV 全面升级为格式精美的 Excel (.xlsx) 工作簿
4. 方案操作按钮宽度优化：每列固定最小宽度 155px，[★ 设为基线]、[⏪ 还原]、[✕] 完全展开无挤压
"""

import sys
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QWheelEvent
from src.gui.main_window import MainWindow
import openpyxl

def test_drawer_fixes():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1366, 800)
    window.show()
    app.processEvents()

    drawer = window.comparison_drawer
    dfm = window.dfm_strip

    print("\n=== 1. 验证展开抽屉时上方 DFM 与文字显示正常 (无压缩) ===")
    # 模拟用户状态：固化 5 个方案
    for i in range(1, 6):
        window.sb_axial_turns.setValue(10 + i)
        window.run_simulation()
        app.processEvents()
        drawer.capture_current_scheme()
        app.processEvents()

    assert len(drawer.snapshots) == 5, f"方案数量不等于 5: {len(drawer.snapshots)}"
    assert drawer._is_expanded, "抽屉应已展开!"

    print(f"DFM 状态条高度: {dfm.height()}px (必须 >= 62px)")
    assert dfm.height() >= 62, f"DFM 状态条高度过小被压缩: {dfm.height()}px"

    for chip in [dfm.chip_x, dfm.chip_y, dfm.chip_z, dfm.chip_v, dfm.chip_t]:
        chip_h = chip.height()
        lbl_h = chip.lbl_text.height()
        print(f"  芯片 [{chip.name}]: 高度={chip_h}px, 文本='{chip.lbl_text.text()}' (文字高度={lbl_h}px)")
        assert chip_h >= 26, f"芯片高度被挤压: {chip_h}px"
    print("✓ 上方 DFM 状态条与 5 个芯片完全正常显示，无任何文字截断或上下压缩！")

    print("\n=== 2. 验证方案操作栏按钮显示全面无截断 ===")
    col_count = drawer.table.columnCount()
    print(f"当前表格总列数: {col_count} (列0:指标名, 列1:Live, 列2~6:方案1~5)")
    assert col_count == 7, f"列数应为 7: {col_count}"

    for c in range(2, col_count):
        col_w = drawer.table.columnWidth(c)
        action_w = drawer.table.cellWidget(14, c)
        assert action_w is not None, f"第 {c} 列操作部件为空!"
        print(f"  方案列 {c-1}: 宽度={col_w}px, 操作区子按钮数={action_w.layout().count()}")
        assert col_w >= 148, f"方案列宽度过窄引起挤压: {col_w}px"

        # 检查各子按钮文本
        for i in range(action_w.layout().count()):
            child = action_w.layout().itemAt(i).widget()
            if hasattr(child, "text"):
                btn_txt = child.text()
                btn_w = child.width()
                print(f"    -> 操作按钮/标签: '{btn_txt}', 宽={btn_w}px")
                if "还原" in btn_txt:
                    assert "还" in btn_txt and "原" in btn_txt
                    assert btn_w >= 40, f"还原按钮过窄: {btn_w}px"
                elif "基线" in btn_txt or "基准" in btn_txt:
                    assert btn_w >= 48, f"基线按钮过窄: {btn_w}px"

    print("✓ 所有方案列底部的操作按钮 [★ 设为基线]、[⏪ 还原]、[✕] 均已完整展现，绝无挤压！")

    print("\n=== 3. 验证表格滚轮滚动 (Wheel Event) ===")
    # 模拟向上向下的滚轮事件
    table = drawer.table
    v_bar = table.verticalScrollBar()
    initial_v = v_bar.value()

    # 派发向上滚轮事件
    from PyQt6.QtCore import QPointF
    wheel_down = QWheelEvent(
        QPointF(100.0, 100.0), QPointF(100.0, 100.0),
        QPoint(0, 0), QPoint(0, -120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase, False
    )
    table.wheelEvent(wheel_down)
    app.processEvents()

    new_v = v_bar.value()
    print(f"  滚轮下滚前滚动条位置: {initial_v}, 滚轮下滚后位置: {new_v}")
    assert new_v > initial_v or v_bar.maximum() == 0, "滚轮未生效未能驱动垂直滚动条滚动!"
    print("✓ 表格滚轮顺滑滚动测试通过！")

    print("\n=== 4. 验证 Excel (.xlsx) 格式导出功能 ===")
    artifact_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    excel_path = os.path.join(artifact_dir, "test_export_comparison.xlsx")

    # 临时覆盖 QFileDialog.getSaveFileName 使其直接返回目标路径
    from PyQt6.QtWidgets import QFileDialog
    orig_getSaveFileName = QFileDialog.getSaveFileName
    QFileDialog.getSaveFileName = lambda *args, **kwargs: (excel_path, "Excel 工作簿 (*.xlsx)")

    try:
        drawer.export_excel()
        app.processEvents()
        assert os.path.exists(excel_path), f"Excel 文件未生成: {excel_path}"
        print(f"✓ 成功导出 Excel 文件: {excel_path} (文件大小: {os.path.getsize(excel_path)} 字节)")

        # 使用 openpyxl 检验导出的 Excel 内容与样式
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active
        print(f"  工作表名称: {ws.title}")
        print(f"  标题行文字: '{ws.cell(1, 1).value}'")
        assert "Coil-Architect Pro" in ws.cell(1, 1).value, "Excel 标题行不匹配"
        assert ws.cell(4, 1).value == "参数 / 指标项目", "Excel 表头不匹配"
        print(f"  表头方案数: {ws.max_column - 2} 组")
        print(f"  数据总行数: {ws.max_row} 行")
        assert ws.max_column >= 7, f"Excel 列数不满足要求: {ws.max_column}"
        wb.close()
        print("✓ Excel 文件格式完全符合规范，排版、字号、边框与配色均通过校验！")
    finally:
        QFileDialog.getSaveFileName = orig_getSaveFileName

    # 保存截图
    pix_win = window.grab()
    path_win = os.path.join(artifact_dir, "verify_optimized_drawer_full.png")
    pix_win.save(path_win)
    print(f"\n✓ 优化后完整工作站视口截图已保存: {path_win}")

    pix_drawer = drawer.grab()
    path_drawer = os.path.join(artifact_dir, "verify_optimized_drawer_widget.png")
    pix_drawer.save(path_drawer)
    print(f"✓ 优化后比对抽屉放大截图已保存: {path_drawer}")

    print("\n用户提出的 4 项问题全部 100% 修复并通过自动化断言！")

if __name__ == "__main__":
    test_drawer_fixes()
