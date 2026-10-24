"""
=============================================================================
Module: src.core.shortcut_helper
Description: Coil-Architect Pro Windows 桌面快捷方式生成管理器
负责一键生成指向 ANSV 仿真验证平台 / Coil-Architect Pro 的专属桌面快捷方式 (.lnk)，
智能自适应 PyInstaller 打包固化环境与源码运行环境，并支持专属高清图标绑定。
=============================================================================
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple

SHORTCUT_FILENAME = "ANSV 微型执行器 - Coil-Architect Pro.lnk"
SHORTCUT_DESCRIPTION = "ANSV 微型执行器与精密传动仿真验证平台 (Coil-Architect Pro)"


def get_desktop_dir() -> Path:
    """
    通过 Windows 原生 SHGetFolderPathW API 获取真实桌面路径
    完美兼容桌面重定向至 OneDrive、D盘或其他路径
    """
    try:
        import ctypes
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        # CSIDL_DESKTOPDIRECTORY = 0x0010
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0:
            desktop_path = Path(buf.value)
            if desktop_path.is_dir():
                return desktop_path
    except Exception:
        pass

    user_profile = os.environ.get("USERPROFILE")
    if user_profile and os.path.isdir(os.path.join(user_profile, "Desktop")):
        return Path(user_profile) / "Desktop"
    return Path.home() / "Desktop"


def get_desktop_shortcut_path() -> Path:
    """获取标准桌面快捷方式的目标路径"""
    return get_desktop_dir() / SHORTCUT_FILENAME


def is_desktop_shortcut_exists() -> bool:
    """检测用户桌面上是否已存在快捷方式"""
    desktop = get_desktop_dir()
    if (desktop / SHORTCUT_FILENAME).exists():
        return True
    for alt in [
        "Coil-Architect Pro.lnk",
        "CoilArchitect.lnk",
        "ANSV 微型执行器.lnk"
    ]:
        if (desktop / alt).exists():
            return True
    return False


def resolve_app_target() -> Tuple[Path, str, Path, Path]:
    """
    解析当前软件的目标可执行程序、运行参数、工作目录与专属图标路径
    返回: (target_path, arguments, working_dir, icon_path)
    """
    if getattr(sys, "frozen", False):
        target_path = Path(sys.executable).resolve()
        arguments = ""
        working_dir = target_path.parent
        icon_path = target_path
        for ico_cand in [
            working_dir / "resources" / "app_icon.ico",
            working_dir / "_internal" / "resources" / "app_icon.ico",
        ]:
            if ico_cand.exists():
                icon_path = ico_cand
                break
        return target_path, arguments, working_dir, icon_path

    base_dir = Path(__file__).resolve().parent.parent.parent

    # 若本地已编译生成正式 EXE (dist/Coil-Architect-Pro/Coil-Architect-Pro.exe)，优先绑定正式 EXE，杜绝指向 pythonw.exe
    dist_exe = base_dir / "dist" / "Coil-Architect-Pro" / "Coil-Architect-Pro.exe"
    if dist_exe.exists():
        target_path = dist_exe.resolve()
        working_dir = target_path.parent
        icon_path = base_dir / "resources" / "app_icon.ico"
        if not icon_path.exists():
            icon_path = target_path
        return target_path, "", working_dir, icon_path

    # 纯源码环境 (尚未编译 EXE 时后备)
    py_exe = Path(sys.executable).resolve()
    pyw = py_exe.parent / "pythonw.exe"
    target_exe = pyw if pyw.exists() else py_exe

    main_script = base_dir / "main.py"
    if not main_script.exists():
        main_script = base_dir / "app.py"

    arguments = f'"{main_script}"'
    working_dir = base_dir
    icon_path = base_dir / "resources" / "app_icon.ico"
    return target_exe, arguments, working_dir, icon_path


def create_desktop_shortcut() -> Tuple[bool, str]:
    """
    在 Windows 桌面上创建专属程序快捷方式 (.lnk)
    优先使用 Windows Script Host (cscript) 极速生成 (0.1s 无黑框)，并以 PowerShell 作为高可用兜底。
    """
    try:
        target_exe, args, working_dir, icon_path = resolve_app_target()
        shortcut_path = get_desktop_shortcut_path()

        target_str = str(target_exe).replace("/", "\\")
        working_str = str(working_dir).replace("/", "\\")
        shortcut_str = str(shortcut_path).replace("/", "\\")
        icon_str = str(icon_path).replace("/", "\\") if icon_path and icon_path.exists() else ""

        # 方案 A: Windows Script Host (VBScript via cscript) - 毫秒级极速响应，零控制台黑框
        escaped_args = args.replace('"', '""') if args else ""
        vbs_lines = [
            'Set oWS = CreateObject("WScript.Shell")',
            f'Set oLink = oWS.CreateShortcut("{shortcut_str}")',
            f'oLink.TargetPath = "{target_str}"',
            f'oLink.WorkingDirectory = "{working_str}"',
            f'oLink.Arguments = "{escaped_args}"',
        ]
        if icon_str:
            vbs_lines.append(f'oLink.IconLocation = "{icon_str}, 0"')
        vbs_lines.append(f'oLink.Description = "{SHORTCUT_DESCRIPTION}"')
        vbs_lines.append('oLink.Save')

        vbs_content = "\r\n".join(vbs_lines)

        with tempfile.NamedTemporaryFile(suffix='.vbs', delete=False, mode='w', encoding='utf-16') as tf:
            tf.write(vbs_content)
            vbs_file = tf.name

        no_win_flag = 0x08000000 if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        res = subprocess.run(['cscript', '//nologo', vbs_file], capture_output=True, text=True, creationflags=no_win_flag)
        if os.path.exists(vbs_file):
            try:
                os.unlink(vbs_file)
            except Exception:
                pass

        if res.returncode == 0 and shortcut_path.exists():
            return True, "桌面快捷方式已成功创建！"

        # 方案 B: PowerShell 备用兜底
        ps_lines = [
            '$WshShell = New-Object -ComObject WScript.Shell',
            f'$Shortcut = $WshShell.CreateShortcut("{shortcut_str}")',
            f'$Shortcut.TargetPath = "{target_str}"',
            f'$Shortcut.WorkingDirectory = "{working_str}"',
            f'$Shortcut.Arguments = \'{args}\'' if args else '$Shortcut.Arguments = ""',
        ]
        if icon_str:
            ps_lines.append(f'$Shortcut.IconLocation = "{icon_str}, 0"')
        ps_lines.append(f'$Shortcut.Description = "{SHORTCUT_DESCRIPTION}"')
        ps_lines.append('$Shortcut.Save()')

        ps_script = "\r\n".join(ps_lines)
        res_ps = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, creationflags=no_win_flag
        )
        if res_ps.returncode == 0 and shortcut_path.exists():
            return True, "桌面快捷方式已成功创建！"

        err_msg = res.stderr.strip() or res_ps.stderr.strip() or "未知权限受限"
        return False, f"创建桌面快捷方式失败: {err_msg}"
    except Exception as e:
        return False, f"创建桌面快捷方式遇到异常: {e}"
