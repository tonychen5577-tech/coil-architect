"""
验证 Coil-Architect Pro 未激活与已激活状态下的交互与拦截守卫
"""
import sys
import os
from pathlib import Path

# 加入项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QPointF, QEvent
from PyQt6.QtGui import QMouseEvent

# 设置控制台 utf-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.gui.main_window import MainWindow
from src.core.license_manager import LicenseManager

# 1. 测试已激活状态
print("=== 1. 测试已激活状态下的 MainWindow ===")
win_active = MainWindow()
win_active.show()
print("已激活按钮文字:", win_active.btn_license.text())
print("已激活状态标志:", win_active.is_authorized)
win_active.grab().save("verify_active_ui.png")
win_active.close()

# 2. 模拟未激活状态
print("\n=== 2. 测试未激活评估状态下的 MainWindow ===")
# 临时 mock LicenseManager.is_system_authorized 返回 False
orig_check = LicenseManager.is_system_authorized
LicenseManager.is_system_authorized = classmethod(lambda cls: (False, "试用期已截止或未导入许可证", {}))

try:
    win_unactive = MainWindow()
    win_unactive.show()
    print("未激活按钮文字:", win_unactive.btn_license.text())
    print("未激活状态标志:", win_unactive.is_authorized)
    win_unactive.grab().save("verify_unactivated_ui.png")

    # 测试未激活时触发操作拦截
    print("\n--- 测试操作拦截触发 ---")
    # mock ActivationDialog.exec 让它直接返回 0 (用户取消激活)
    from src.gui.activation_dialog import ActivationDialog
    orig_exec = ActivationDialog.exec
    ActivationDialog.exec = lambda self: 0

    try:
        # A. 测试保存算例拦截
        res = win_unactive.check_authorization_or_prompt("测试操作")
        print("未激活时调用 check_authorization_or_prompt 返回值 (应为 False):", res)
        assert res is False, "未激活时应当返回 False 阻断操作"
        print("状态栏提示文本:", win_unactive.status_bar.currentMessage())

        # B. 测试事件过滤器对左侧参数面板点击的拦截
        target_widget = win_unactive.sb_bare_dia.spin
        evt = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5.0, 5.0), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        filtered = win_unactive._param_interaction_filter.eventFilter(target_widget, evt)
        print("左侧参数面板点击被过滤器拦截:", filtered)
        assert filtered is True, "左侧参数面板点击应当被过滤器拦截 (返回 True)"

        # C. 测试滚动条放行
        scrollbar = win_unactive.scroll_left.verticalScrollBar()
        evt_scroll = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(2.0, 2.0), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        scroll_filtered = win_unactive._param_interaction_filter.eventFilter(scrollbar, evt_scroll)
        print("滚动条点击被过滤器放行:", not scroll_filtered)
        assert scroll_filtered is False, "滚动条应当被完全放行供用户滚动浏览"

        # D. 测试右侧画布放行
        canvas = win_unactive.canvas_widget
        evt_canvas = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(50.0, 50.0), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        canvas_filtered = win_unactive._param_interaction_filter.eventFilter(canvas, evt_canvas)
        print("画布点击被过滤器放行:", not canvas_filtered)
        assert canvas_filtered is False, "右侧画布视口应当被放行供用户缩放平移"

        print("\n✅ 所有拦截与放行逻辑测试全部 PASS！")
    finally:
        ActivationDialog.exec = orig_exec
        win_unactive.close()
finally:
    LicenseManager.is_system_authorized = orig_check

print("\n🎉 自动化端到端测试圆满完成！")
