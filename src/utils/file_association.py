"""
=============================================================================
Module: src.utils.file_association
Description: Windows 操作系统 .ansvcoil 专属文件扩展名与科技感图标注册
支持一机一键建立文件关联：双击 .ansvcoil 算例直接唤起 Coil-Architect Pro 并呈现高清图标
=============================================================================
"""

import sys
import os
import winreg
import ctypes
from pathlib import Path
from src.version import APP_NAME, APP_TITLE
from src.utils.logger import get_logger

logger = get_logger("FileAssociation")

PROG_ID = "ANSV.CoilArchitect.Project.1"
FILE_EXT = ".ansvcoil"
FRIENDLY_TYPE_NAME = "ANSV 线圈工程算例 (ANSV Coil Project)"


def get_target_executable_and_icon() -> tuple[str, str]:
    """
    推导当前运行环境下的启动命令与图标路径
    兼容 PyInstaller 打包环境与 Python 源码运行环境
    """
    # 1. 图标绝对路径
    from src.gui.icon_helper import get_icon_path
    icon_p = get_icon_path().resolve()
    icon_str = str(icon_p)

    # 2. 启动执行体路径
    if getattr(sys, "frozen", False):
        # 打包环境: 直接调用 Coil-Architect-Pro.exe
        exe_path = sys.executable
        command_str = f'"{exe_path}" "%1"'
    else:
        # 源码环境: 使用 pythonw.exe 或 python.exe 执行 app.py
        app_py = Path(__file__).resolve().parent.parent.parent / "app.py"
        python_exe = sys.executable
        command_str = f'"{python_exe}" "{app_py}" "%1"'

    return command_str, icon_str


def register_ansvcoil_association() -> tuple[bool, str]:
    """
    在 Windows 当前用户注册表 (HKCU\\Software\\Classes) 建立 .ansvcoil 关联
    无需 UAC 管理员提权，即时生效
    """
    if sys.platform != "win32":
        return False, "非 Windows 平台，无需注册文件关联。"

    try:
        command_str, icon_str = get_target_executable_and_icon()

        # 1. 注册扩展名键 HKCU\Software\Classes\.ansvcoil
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{FILE_EXT}") as key_ext:
            winreg.SetValue(key_ext, "", winreg.REG_SZ, PROG_ID)
            winreg.SetValueEx(key_ext, "Content Type", 0, winreg.REG_SZ, "application/x-ansv-coil")

        # 2. 注册 ProgID 键 HKCU\Software\Classes\ANSV.CoilArchitect.Project.1
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}") as key_prog:
            winreg.SetValue(key_prog, "", winreg.REG_SZ, FRIENDLY_TYPE_NAME)
            winreg.SetValueEx(key_prog, "FriendlyTypeName", 0, winreg.REG_SZ, FRIENDLY_TYPE_NAME)

        # 3. 注册默认图标 DefaultIcon
        if icon_str and os.path.exists(icon_str):
            icon_entry = f'"{icon_str}",0'
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}\DefaultIcon") as key_icon:
                winreg.SetValue(key_icon, "", winreg.REG_SZ, icon_entry)

        # 4. 注册双击打开命令 shell\open\command
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}\shell\open\command") as key_cmd:
            winreg.SetValue(key_cmd, "", winreg.REG_SZ, command_str)

        # 5. 通知 Windows Shell 刷新图标缓存与文件关联
        try:
            SHCNE_ASSOCCHANGED = 0x08000000
            SHCNF_IDLIST = 0x0000
            ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        except Exception as e:
            logger.debug(f"广播 SHChangeNotify 失败: {e}")

        logger.info(f"成功注册 {FILE_EXT} 文件关联: {PROG_ID}")
        return True, f"已成功建立 {FILE_EXT} 专属文件关联与科技感图标！\n双击即可直接调用 Coil-Architect Pro 打开算例。"

    except Exception as e:
        logger.error(f"注册文件关联失败: {e}")
        return False, f"注册文件关联时发生错误:\n{str(e)}"
