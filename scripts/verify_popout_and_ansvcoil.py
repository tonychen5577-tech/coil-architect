"""
端到端验证 .ansvcoil 专属算例格式与对比抽屉弹窗模式
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.gui.main_window import MainWindow
from src.utils.file_association import register_ansvcoil_association

print("=== 1. 测试 Windows .ansvcoil 文件关联注册 ===")
ok, msg = register_ansvcoil_association()
print("注册状态:", ok)
assert ok is True, f"注册应当成功: {msg}"

print("\n=== 2. 测试 MainWindow 实例与 .ansvcoil 导出载入 ===")
win = MainWindow()
win.show()

# 导出 .ansvcoil 测试算例
test_file = Path("test_sample.ansvcoil").resolve()
data = {
    "version": "1.1.0",
    "file_type": "ANSV_COIL_PROJECT",
    "project_name": "Test-VCM-Coil",
    "inputs": {
        "coil_type": 2, # 八角形
        "inner_len": 6.8,
        "inner_wid": 6.8,
        "radial_layers": 10,
        "axial_turns": 8,
        "bare_dia": 0.050,
        "max_od": 0.060,
        "tension_factor": 0.99
    }
}
import json
with open(test_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

# 测试 load_project_file
load_ok = win.load_project_file(str(test_file))
print("加载 .ansvcoil 文件成功:", load_ok)
assert load_ok is True, "应当成功载入 .ansvcoil 算例"
print("载入后项目名称:", win.get_project_name())
assert win.get_project_name() == "Test-VCM-Coil", "项目名称应当成功更新为 Test-VCM-Coil"

# 清理测试文件
if test_file.exists():
    test_file.unlink()

print("\n=== 3. 测试方案比对抽屉的【弹窗模式 (Pop-out Mode)】 ===")
drawer = win.drawer
print("初始抽屉状态: is_expanded =", drawer._is_expanded, "is_popped_out =", drawer._is_popped_out)

# 固化一个方案
drawer.capture_current_scheme()
print("固化方案后数量:", len(drawer.snapshots))
assert len(drawer.snapshots) >= 1, "抽屉中应有至少1组固化方案"

# 触发弹出大窗
print("正在触发弹出独立大窗...")
drawer.pop_out()
print("弹出后状态: is_popped_out =", drawer._is_popped_out)
assert drawer._is_popped_out is True, "状态应变为已弹出"
assert drawer.popout_window is not None, "popout_window 实例应存在"
assert drawer.popout_window.isVisible(), "独立大窗应当可见"
print("独立窗口初始尺寸:", drawer.popout_window.width(), "x", drawer.popout_window.height())
assert drawer.popout_window.width() >= 1000, "弹窗宽度应当大于 1000 以支持宽屏大矩阵查看"

# 截图保存弹窗模式
drawer.popout_window.grab().save("verify_drawer_popout_window.png")
print("独立弹窗截图已保存: verify_drawer_popout_window.png")

# 在弹窗模式下再固化一个方案，测试实时联动
drawer.capture_current_scheme()
print("弹窗模式下二次固化后总数:", len(drawer.snapshots))
assert len(drawer.snapshots) >= 2, "应有2组方案"
print("弹窗顶部计数标签文本:", drawer.popout_window.lbl_pop_count.text())

# 测试收回嵌入底部抽屉
print("\n正在测试收回嵌入底部抽屉...")
drawer.dock_back()
print("恢复嵌入后状态: is_popped_out =", drawer._is_popped_out)
assert drawer._is_popped_out is False, "状态应恢复为 False"
assert drawer.content_container.isVisible(), "抽屉内容区应恢复可见"
print("抽屉内部表格当前高度限制:", drawer.table.maximumHeight())
assert drawer.table.maximumHeight() <= 300, "抽屉表格应恢复限高以保持主工作台协调"

# 截图保存恢复嵌入后的工作台
win.grab().save("verify_docked_drawer_ui.png")
print("主工作台截图已保存: verify_docked_drawer_ui.png")

win.close()
print("\n🎉 所有端到端测试 100% 全部通过！")
