"""
Coil-Architect Pro - GUI & Reliability Utilities
工业级可靠性工具集：
1. 全局滚轮防误触过滤器 (GlobalNoWheelChangeFilter)
2. 突发断电防损：原子持久化写 (atomic_write_json / atomic_write_text)
3. Windows 任务栏 AppUserModelID 与 HWND 图标 Win32 原生注入
4. 高低分辨率与 DPI 小屏防爆自适应 (adapt_dialog_geometry)
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QComboBox, QAbstractSlider, QScrollArea, QApplication, QDialog, QWidget
)


class GlobalNoWheelChangeFilter(QObject):
    """
    全局滚轮事件防误触过滤器 (依据规范 04.一 实现)：
    拦截 QAbstractSpinBox (含 QSpinBox, QDoubleSpinBox), QComboBox 以及 QAbstractSlider (滑块)
    的滚轮调值事件，顺着组件树找到 QScrollArea 并安全平滑滚动页面，
    彻底消除递归调用 parent.wheelEvent() 引发的 C++ 栈溢出与静默闪退。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_handling = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            if self._is_handling:
                return False
            if isinstance(obj, (QAbstractSpinBox, QComboBox, QAbstractSlider)):
                # 寻找祖先中的 QScrollArea 并直接控制其滚动条，杜绝事件重入
                parent = obj.parentWidget()
                while parent:
                    if isinstance(parent, QScrollArea):
                        self._is_handling = True
                        try:
                            delta = event.angleDelta().y()
                            bar = parent.verticalScrollBar()
                            if bar and delta != 0:
                                bar.setValue(bar.value() - delta // 2)
                        finally:
                            self._is_handling = False
                        return True
                    parent = parent.parentWidget()
                # 若外部无滚动区域，直接丢弃该滚轮事件，防止误调参数
                event.ignore()
                return True
        return super().eventFilter(obj, event)


def atomic_write_json(target_path: Path, data: dict, indent: int = 2) -> bool:
    """
    工业级原子 JSON 持久化写入 (依据规范 05.三 实现)：
    1. 写入同目录下的 PID 隔离临时文件 (.tmp_{pid})；
    2. flush + os.fsync 强制物理扇区落盘；
    3. 操作系统底层原子重命名覆盖 (replace)；
    保证突发断电时“要么是旧文件完整，要么是新文件完整”，100% 杜绝 0 字节空洞。
    """
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target.with_suffix(f".tmp_{os.getpid()}")

    try:
        raw_text = json.dumps(data, ensure_ascii=False, indent=indent)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(raw_text)
            f.flush()
            os.fsync(f.fileno())  # 强制刷入物理存储介质
        
        # Windows 原生原子重命名
        temp_file.replace(target)
        return True
    except Exception as e:
        if temp_file.exists():
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass
        raise e


def atomic_write_text(target_path: Path, text: str, encoding: str = "utf-8") -> bool:
    """
    工业级原子文本/CSV持久化写入：
    保证写盘过程断电绝不产生损坏空洞。
    """
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target.with_suffix(f".tmp_{os.getpid()}")

    try:
        with open(temp_file, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        
        temp_file.replace(target)
        return True
    except Exception as e:
        if temp_file.exists():
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass
        raise e


def set_windows_app_user_model_id(app_id: str = "ansv.net.coilarchitect.1.0"):
    """
    Windows 任务栏应用组声明 (依据规范 04.三 实现)：
    防止 Windows 将 Python 桌面程序归组至默认小黑窗或白板。
    """
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


def apply_window_icon_to_hwnd(window: QWidget, icon_path: Path):
    """
    Win32 原生图标强注入：
    向主窗口句柄 HWND 发送 WM_SETICON 消息，确保任务栏和大图标 Alt+Tab 100% 显式生效。
    """
    if sys.platform == "win32" and hasattr(window, "winId") and icon_path.exists():
        try:
            hwnd = int(window.winId())
            user32 = ctypes.windll.user32
            # 0x0010 = LR_LOADFROMFILE, 1 = IMAGE_ICON
            # 32x32 大图标 (任务栏 / Alt+Tab)
            h_big = user32.LoadImageW(None, str(icon_path), 1, 32, 32, 0x0010)
            if h_big:
                user32.SendMessageW(hwnd, 0x0080, 1, h_big)  # WM_SETICON, ICON_BIG
            # 16x16 小图标 (窗口标题栏)
            h_small = user32.LoadImageW(None, str(icon_path), 1, 16, 16, 0x0010)
            if h_small:
                user32.SendMessageW(hwnd, 0x0080, 0, h_small)  # WM_SETICON, ICON_SMALL
        except Exception:
            pass


def adapt_dialog_geometry(
    dialog: QDialog, 
    target_w: int = 640, 
    target_h: int = 420, 
    min_w: int = 460, 
    min_h: int = 320
):
    """
    高低分辨率与 DPI 自适应弹窗居中函数 (依据规范 04.四 实现)：
    提取剔除 Windows 任务栏后的可用工作区 (availableGeometry)，
    严格保证弹窗最大高度 <= 工作区的 88%，杜绝工控小屏/高缩放下底部确认按钮被遮挡。
    """
    screen = QApplication.primaryScreen()
    avail = screen.availableGeometry() if screen else None
    screen_w = avail.width() if avail else 1280
    screen_h = avail.height() if avail else 720

    safe_max_w = int(screen_w * 0.95)
    safe_max_h = int(screen_h * 0.88)

    effective_min_w = min(min_w, safe_max_w)
    effective_min_h = min(min_h, safe_max_h)
    dialog.setMinimumSize(effective_min_w, effective_min_h)

    final_w = min(max(target_w, effective_min_w), safe_max_w)
    final_h = min(max(target_h, effective_min_h), safe_max_h)
    dialog.resize(final_w, final_h)

    if avail:
        x = avail.x() + (avail.width() - final_w) // 2
        y = avail.y() + (avail.height() - final_h) // 2
        dialog.move(x, y)
