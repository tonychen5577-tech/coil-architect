"""
=============================================================================
Module: src.core.single_instance
Description: Coil-Architect Pro 单实例运行守卫 (基于 Windows Named Mutex)
内核级互斥体：即使进程异常终止或被强杀，操作系统也会自动释放互斥体句柄，杜绝残留。
若检测到已有实例在运行，则自动将已有主窗口激活置顶，并弹出提示安全退出二次启动的进程。
=============================================================================
"""

import sys
import ctypes
from typing import Optional

ERROR_ALREADY_EXISTS = 183


class SingleInstanceChecker:
    """
    单实例运行守卫 (基于 Windows Named Mutex)
    """

    def __init__(self, mutex_name: str = "Local\\CoilArchitect_App_SingleInstance_Mutex_2026"):
        self.mutex_name = mutex_name
        self.mutex_handle = None
        self._already_running = False

    def check(self) -> bool:
        """
        检查是否已有程序实例在运行。
        :return: True 表示已存在运行中实例；False 表示当前为首个实例。
        """
        if sys.platform != "win32":
            return False

        try:
            kernel32 = ctypes.windll.kernel32
            # CreateMutexW(lpMutexAttributes, bInitialOwner, lpName)
            self.mutex_handle = kernel32.CreateMutexW(None, False, self.mutex_name)
            last_error = kernel32.GetLastError()
            if last_error == ERROR_ALREADY_EXISTS:
                self._already_running = True
                return True
            return False
        except Exception:
            return False

    def is_already_running(self) -> bool:
        return self._already_running

    def activate_existing_window(self) -> bool:
        """寻找已打开的 Coil-Architect 主窗口并唤醒置顶"""
        if sys.platform != "win32":
            return False

        try:
            user32 = ctypes.windll.user32
            found_hwnd = []

            def enum_windows_callback(hwnd, extra):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value
                        if "Coil-Architect" in title or "电磁线圈多物理场仿真工作站" in title:
                            found_hwnd.append(hwnd)
                            return False  # 停止枚举
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
            cb = WNDENUMPROC(enum_windows_callback)
            user32.EnumWindows(cb, 0)

            if found_hwnd:
                hwnd = found_hwnd[0]
                SW_RESTORE = 9
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
                return True
        except Exception:
            pass
        return False

    def handle_already_running(self) -> bool:
        """
        处理已有实例检测逻辑：
        1. 若找到可见主窗口，则前台唤醒并提示用户已切换，返回 False (当前进程退出)
        2. 若未找到可见主窗口 (后台僵尸进程或无界面进程残留)，则提示用户是否强制清理并启动，
           若用户确认，则强制清理残留并重新夺取互斥体，返回 True (允许当前进程继续启动)；若取消则返回 False。
        """
        found = self.activate_existing_window()
        from PyQt6.QtWidgets import QMessageBox

        if found:
            QMessageBox.information(
                None,
                "程序已在运行",
                "Coil-Architect Pro 已有一个实例正在运行中。\n\n"
                "系统已为您自动切换并置顶该工作窗口，无需重复启动。"
            )
            return False

        # 未找到可视窗口，说明是后台无界面残留进程或异常互斥体
        reply = QMessageBox.question(
            None,
            "检测到后台残留进程",
            "检测到系统后台存在未退出的 Coil-Architect 进程或互斥体，但桌面上未找到已打开的窗口。\n\n"
            "是否强制结束后台残留进程并正常启动？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            return self.force_cleanup_and_acquire()
        return False

    def force_cleanup_and_acquire(self) -> bool:
        """强制清理其他残留的 app.py 进程并重新获取互斥体"""
        import os
        import subprocess
        import time

        my_pid = os.getpid()
        try:
            if self.mutex_handle:
                ctypes.windll.kernel32.CloseHandle(self.mutex_handle)
                self.mutex_handle = None

            ps_cmd = (
                f"Get-CimInstance Win32_Process | "
                f"Where-Object {{ $_.ProcessId -ne {my_pid} -and $_.CommandLine -match 'app\\.py' }} | "
                f"Stop-Process -Force"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                timeout=5,
                capture_output=True
            )
            time.sleep(0.3)

            kernel32 = ctypes.windll.kernel32
            self.mutex_handle = kernel32.CreateMutexW(None, False, self.mutex_name)
            last_error = kernel32.GetLastError()
            if last_error != ERROR_ALREADY_EXISTS:
                self._already_running = False
                return True
        except Exception:
            pass
        return True

    def show_alert_and_exit(self):
        """兼容旧接口：唤醒旧窗口并处理退出/恢复"""
        if not self.handle_already_running():
            sys.exit(0)
