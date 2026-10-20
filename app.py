"""
=============================================================================
Coil-Architect Pro - Main Application Entry (app.py)
Windows 10/11 原生精密电磁线圈多物理场仿真工作站
(完全对齐 Gear-NVH / FFT 分析软件 工业商业软件架构与美学规范)
=============================================================================
"""

import sys
import os
import traceback
from pathlib import Path

# 确保当前目录与 src 在 sys.path 中
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from src.version import APP_NAME, APP_TITLE, APP_VERSION
from src.utils.logger import setup_logging, install_crash_hook, get_logger
from src.core.single_instance import SingleInstanceChecker
from src.gui.styles import apply_light_theme
from src.gui.icon_helper import get_app_icon, set_windows_app_user_model_id, apply_window_icon_to_hwnd
from src.gui.splash_screen import SplashScreen
from src.gui.utils import GlobalNoWheelChangeFilter


def main():
    # 0. 启动企业内网智能 DNS 韧性解析器 (对标 Gear 规范，防内网 DNS 阻断)
    import src.core.smart_dns

    # 1. 初始化全局安全滚动日志与未捕获异常崩溃看门狗 (规范 05.一)
    setup_logging()
    install_crash_hook()
    logger = get_logger("MainApp")
    logger.info(f"{APP_TITLE} 正在启动...")

    # 2. 启用专属 Windows AppUserModelID (规范 04.三: 确保 Windows 任务栏独立高清应用图标)
    set_windows_app_user_model_id("ansv.net.coilarchitect.station.1.1")

    # 3. 针对 Windows 高分屏 (4K/2K) DPI 缩放优化
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(get_app_icon())

    # 4. 强制设置纯白工业测控浅色主题 (Fusion 调色板，免疫系统深色模式污染)
    apply_light_theme(app)

    # 5. 全局安装防滚轮误触过滤器 (规范 04.一)
    app.installEventFilter(GlobalNoWheelChangeFilter(app))

    # 6. 单实例进程间通信 (IPC) 无缝路由：
    # 若已有主工作台在运行，静默将外部双击打开的算例文件或前台唤醒指令投递给主工作台，彻底消灭双开冲突警告
    from src.core.ipc_manager import send_args_to_running_instance, SingleInstanceIPCServer
    target_arg_file = sys.argv[1] if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]) else ""
    if send_args_to_running_instance(target_arg_file):
        # 成功投递给已在运行的主窗口，二次进程安全静默退出
        logger.info("已将外部调用指令无缝投递给当前运行中的主实例，当前辅助进程安全退出。")
        sys.exit(0)

    # 首次启动或异常崩溃恢复检测
    instance_checker = SingleInstanceChecker()
    if instance_checker.check():
        logger.warning("检测到互斥体残留，执行前台唤醒或异常残留恢复判定。")
        if not instance_checker.handle_already_running():
            sys.exit(0)
    app._instance_checker = instance_checker  # 保持全局句柄常驻内存防回收

    try:
        # 7. 立即弹出科技感工业启动闪屏 (0.1 秒极速呈现，消除操作员等待焦虑)
        splash = SplashScreen()
        splash.show()
        splash.update_progress(15, "正在校验一机一码硬件指纹与数字凭证...")

        # 8. 校验商业授权状态 (未激活状态正常启动进入工作台预览，操作时再提示激活)
        from src.core.license_manager import LicenseManager

        auth_ok, auth_msg, lic_data = LicenseManager.is_system_authorized()
        if not auth_ok:
            logger.info(f"系统处于未激活状态 ({auth_msg})，进入评估预览模式。")
            splash.update_progress(35, "检测到未激活评估模式，正在准备工作台预览...")
        else:
            is_trial = lic_data.get("is_trial", False) if lic_data else False
            if is_trial:
                days_left = lic_data.get("days_left", 7)
                logger.info(f"系统处于 7 天全功能免激活试用期 (剩余 {days_left} 天)")
                splash.update_progress(35, f"7天全功能试用有效 (剩 {days_left} 天)，正在装载物理引擎...")
            else:
                splash.update_progress(35, "正式商业授权凭证验证通过，正在装载物理引擎...")

        # 9. 步进式加载系统核心物理引擎
        splash.update_progress(45, "正在装载电磁线圈双核高精度求解器 (Cython加速内核)...")
        from src.core.physics_engine import CoilPhysicsEngine

        # 10. 动态构建主工作区核心组件
        splash.update_progress(70, "正在构建 2D 矢量数字孪生图纸与 DFM 装配卡控条...")
        from src.gui.main_window import MainWindow

        # 11. 实例化主工作台窗口
        splash.update_progress(90, "正在初始化高对比度测控工作台与基准预设库...")
        window = MainWindow()

        # 检查命令行入参，支持 Windows 双击 .ansvcoil 算例直接唤起并自动载入
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            target_file = sys.argv[1]
            if target_file.lower().endswith((".ansvcoil", ".ansv", ".json")):
                logger.info(f"检测到外部文件打开请求，自动载入算例: {target_file}")
                window.load_project_file(target_file)

        # 12. Win32 原生图标强注入 (规范 04.三: 直接注入 HWND)
        apply_window_icon_to_hwnd(window)

        # 13. 无缝过渡进入主工作台
        splash.finish_and_show(window)
        logger.info(f"{APP_TITLE} 启动就绪，进入主交互事件循环。")

        # 14. 异步云端静默心跳与时钟授时 (守护线程，离线/超时绝不阻塞界面)
        try:
            from src.core.cloud_client import CloudClient
            CloudClient.send_heartbeat_async()
        except Exception:
            pass

        # 15. 自动维护 Windows .ansvcoil 专属文件类型与图标关联 (静默免打扰)
        try:
            from src.utils.file_association import register_ansvcoil_association
            register_ansvcoil_association()
        except Exception:
            pass

        # 16. 启动单实例 IPC 监听服务，处理后续外部双击文件或激活调用
        ipc_server = SingleInstanceIPCServer(window)
        app._ipc_server = ipc_server

        def on_external_file_import(filepath: str):
            """响应外部进程投递的算例文件打开请求"""
            # 1. 窗口前台激活置顶
            window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            window.show()
            window.raise_()
            window.activateWindow()
            try:
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(int(window.winId()))
            except Exception:
                pass

            # 2. 弹出高对比度覆盖确认弹窗
            filename = os.path.basename(filepath)
            reply = QMessageBox.question(
                window,
                "导入外部线圈算例确认",
                f"检测到外部请求打开线圈工程算例：\n\n"
                f"📄 算例文件: {filename}\n"
                f"📁 算例路径: {filepath}\n\n"
                f"是否确认将此算例导入到当前工作台？\n\n"
                f"⚠️ 警告: 导入新算例将覆盖当前工作台中尚未保存的参数与仿真结果！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                window.load_project_file(filepath)
                window.status_bar.showMessage(f"已成功导入外部算例: {filename}", 5000)
            else:
                window.status_bar.showMessage("已取消导入外部算例，当前工作台参数保持不变。", 3500)

        def on_external_activate():
            """响应外部重复启动请求：纯粹前台唤醒置顶，绝不弹窗打扰"""
            window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            window.show()
            window.raise_()
            window.activateWindow()
            try:
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(int(window.winId()))
            except Exception:
                pass
            window.status_bar.showMessage("工作台已在前台激活就绪", 3000)

        ipc_server.file_import_requested.connect(on_external_file_import)
        ipc_server.activate_requested.connect(on_external_activate)

        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"系统启动主循环捕获严重异常: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(
            None,
            "启动异常",
            f"Coil-Architect Pro 启动遭遇不可恢复的异常：\n\n{str(e)}\n\n"
            f"详情请查阅 logs/coil_architect.log。"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
