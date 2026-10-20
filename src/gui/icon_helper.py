"""
=============================================================================
Module: src.gui.icon_helper
Description: Coil-Architect Pro 全局图标与品牌图像资源管理
(自动适配源码执行、动态打包与 PyInstaller _MEIPASS 单文件/单目录环境)
=============================================================================
"""

import sys
import os
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt


def get_icon_path() -> Path:
    """寻找应用图标文件的绝对路径 (多级智能探测与容错)"""
    candidates = []

    # 1. PyInstaller 打包环境
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates.extend([
            meipass / "resources" / "app_icon.ico",
            meipass / "resources" / "app_icon.png",
            meipass / "app_icon.ico",
            meipass / "app_icon.png"
        ])

    # 2. 源码环境 (以当前文件为基准推导根目录)
    root_dir = Path(__file__).resolve().parent.parent.parent
    candidates.extend([
        root_dir / "resources" / "app_icon.ico",
        root_dir / "resources" / "app_icon.png",
        root_dir / "app_icon.ico",
        root_dir / "app_icon.png"
    ])

    # 3. 当前工作目录
    cwd = Path.cwd()
    candidates.extend([
        cwd / "resources" / "app_icon.ico",
        cwd / "resources" / "app_icon.png",
        cwd / "app_icon.ico",
        cwd / "app_icon.png"
    ])

    for p in candidates:
        if p.exists():
            return p

    return candidates[0] if candidates else Path("resources/app_icon.ico")


def get_app_icon() -> QIcon:
    """获取应用主图标 QIcon (加载多分辨率金字塔，确保 Windows 任务栏与标题栏极致锐利)"""
    path = get_icon_path()
    icon = QIcon()
    if path.exists():
        icon.addFile(str(path))
        png_path = path.parent / "app_icon.png"
        if png_path.exists() and png_path != path:
            icon.addFile(str(png_path))
        return icon

    # 若资源文件缺失，动态生成优雅的内存备用矢量图标 (杜绝异常闪退)
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0F172A"))
    painter.setPen(QPen(QColor("#0284C7"), 3))
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(QPen(QColor("#D97706"), 3))
    painter.drawEllipse(14, 14, 36, 36)
    painter.end()
    icon.addPixmap(pix)
    return icon


def get_app_icon_pixmap(size: int = 48) -> QPixmap:
    """获取指定尺寸的高清应用图标 QPixmap (高质量平滑缩放)"""
    path = get_icon_path()
    png_path = path.parent / "app_icon.png"
    target_path = png_path if png_path.exists() else path

    if target_path.exists():
        pix = QPixmap(str(target_path))
        if not pix.isNull():
            return pix.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

    # 动态内存回退
    icon = get_app_icon()
    return icon.pixmap(size, size)


def set_windows_app_user_model_id(app_id: str = "ansv.net.coilarchitect.station.1.1"):
    """
    配置 Windows 任务栏应用专属 AppUserModelID
    确保在 Windows 任务栏、Alt+Tab 切换窗口中正确常驻独立应用图标，而非显示默认的 Python 终端图标
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


def apply_window_icon_to_hwnd(window, icon_path: Path = None):
    """
    通过 Windows 底层 Win32 API 直接向窗口 HWND 注入 32x32(任务栏/Alt+Tab) 与 16x16(标题栏) 图标
    彻底解决部分 Windows 10/11 版本下 Qt setWindowIcon 无法触发任务栏图标更新的系统级缓存顽疾
    """
    if sys.platform == "win32" and hasattr(window, "winId"):
        try:
            import ctypes
            hwnd = int(window.winId())
            if not icon_path or not icon_path.exists():
                icon_path = get_icon_path()
            if icon_path.exists():
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x0010
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1

                user32 = ctypes.windll.user32
                # 32x32 对应任务栏、Alt+Tab 任务切换大图标
                hicon_big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                if hicon_big:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)

                # 16x16 对应窗口标题栏与任务栏小图标
                hicon_small = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if hicon_small:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
        except Exception:
            pass
