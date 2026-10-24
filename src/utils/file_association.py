"""
=============================================================================
Module: src.utils.file_association
Description: Windows 操作系统 .ansvcoil 与 .ansvschemes 专属文件扩展名与科技图标注册
支持一机一键建立专属文件关联：
1. .ansvcoil (单工程算例): 折角图纸 + 黄金线圈 + 蓝色 COIL 徽标
2. .ansvschemes (多方案对比集): 折角图纸 + 多个错落对比线圈 + 翡翠绿 SCHEMES 徽标
双击任一文件直接唤起 Coil-Architect Pro 工作站并自动还原装载数据。
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

ASSOCIATIONS = [
    {
        "ext": ".ansvcoil",
        "prog_id": "ANSV.CoilArchitect.Project.1",
        "friendly_name": "ANSV 线圈工程算例 (ANSV Coil Project)",
        "mime_type": "application/x-ansv-coil",
        "icon_file": "coil_project_icon.ico",
        "desc": "ANSV 线圈工程物理仿真算例"
    },
    {
        "ext": ".ansvschemes",
        "prog_id": "ANSV.CoilArchitect.Schemes.1",
        "friendly_name": "ANSV 多方案对比集 (ANSV Coil Comparison Schemes)",
        "mime_type": "application/x-ansv-schemes",
        "icon_file": "coil_schemes_icon.ico",
        "desc": "ANSV 微型线圈多方案参数与矩阵比对集"
    }
]


def get_icon_path(icon_filename: str) -> Path:
    """寻找指定专属文件图标路径"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        root_dir / "resources" / icon_filename,
        root_dir / "resources" / "coil_project_icon.ico",
        root_dir / "resources" / "app_icon.ico",
        Path(f"resources/{icon_filename}"),
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates.insert(0, meipass / "resources" / icon_filename)
        candidates.insert(1, meipass / "resources" / "coil_project_icon.ico")

    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def get_target_command_for_file() -> str:
    """推导当前运行环境下的启动命令"""
    if getattr(sys, "frozen", False):
        # 打包环境: 直接调用 Coil-Architect-Pro.exe
        exe_path = sys.executable
        return f'"{exe_path}" "%1"'
    else:
        # 源码环境: 使用 pythonw.exe 或 python.exe 执行 app.py
        app_py = Path(__file__).resolve().parent.parent.parent / "app.py"
        python_exe = sys.executable
        return f'"{python_exe}" "{app_py}" "%1"'


def register_all_file_associations() -> tuple[bool, str]:
    """
    在 Windows 当前用户注册表 (HKCU\\Software\\Classes) 建立 .ansvcoil 与 .ansvschemes 双重关联
    无需 UAC 管理员提权，即时生效
    """
    if sys.platform != "win32":
        return False, "非 Windows 平台，无需注册文件关联。"

    try:
        command_str = get_target_command_for_file()
        registered_exts = []

        for item in ASSOCIATIONS:
            ext = item["ext"]
            prog_id = item["prog_id"]
            friendly_name = item["friendly_name"]
            mime = item["mime_type"]
            icon_p = get_icon_path(item["icon_file"]).resolve()
            icon_str = str(icon_p)

            # 1. 注册扩展名键 HKCU\Software\Classes\<ext>
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}") as key_ext:
                winreg.SetValue(key_ext, "", winreg.REG_SZ, prog_id)
                winreg.SetValueEx(key_ext, "Content Type", 0, winreg.REG_SZ, mime)

            # 2. 注册 ProgID 键 HKCU\Software\Classes\<prog_id>
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}") as key_prog:
                winreg.SetValue(key_prog, "", winreg.REG_SZ, friendly_name)
                winreg.SetValueEx(key_prog, "FriendlyTypeName", 0, winreg.REG_SZ, friendly_name)

            # 3. 注册默认图标 DefaultIcon
            if icon_str and os.path.exists(icon_str):
                icon_entry = f'"{icon_str}",0'
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}\DefaultIcon") as key_icon:
                    winreg.SetValue(key_icon, "", winreg.REG_SZ, icon_entry)

            # 4. 注册双击打开命令 shell\open\command
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}\shell\open\command") as key_cmd:
                winreg.SetValue(key_cmd, "", winreg.REG_SZ, command_str)

            registered_exts.append(ext)
            logger.info(f"成功注册 {ext} 文件关联: {prog_id} (图标: {icon_p.name})")

        # 5. 通知 Windows Shell 刷新图标缓存与文件关联
        try:
            SHCNE_ASSOCCHANGED = 0x08000000
            SHCNF_IDLIST = 0x0000
            ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        except Exception as e:
            logger.debug(f"广播 SHChangeNotify 失败: {e}")

        ext_str = " & ".join(registered_exts)
        return True, (
            f"已成功建立 {ext_str} 专属工程文件关联与科技感图标！\n"
            f"• .ansvcoil: 单线圈工程算例 (蓝色 COIL 徽标)\n"
            f"• .ansvschemes: 多方案对比集 (翡翠绿 SCHEMES 徽标)\n\n"
            f"双击任意文件即可直接唤起 Coil-Architect Pro 查看与还原。"
        )

    except Exception as e:
        logger.error(f"注册文件关联失败: {e}")
        return False, f"注册文件关联时发生错误:\n{str(e)}"


def register_ansvcoil_association() -> tuple[bool, str]:
    """向后兼容别名函数，同时注册全量文件关联"""
    return register_all_file_associations()
