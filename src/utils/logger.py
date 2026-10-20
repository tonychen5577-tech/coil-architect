"""
=============================================================================
Module: src.utils.logger
Description: Coil-Architect Pro 全局统一日志、异常追踪与崩溃看门狗引擎
1. 自动滚动限额落盘 (单文件 5MB, 最多 3 个备份, 杜绝占满磁盘)
2. 全局崩溃与未捕获异常 Traceback 自动落盘 (消除静默闪退盲盒)
3. Windows GBK 控制台安全编码输出 (SafeStreamHandler 防止 Unicode 报错)
=============================================================================
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# 默认日志存储目录 (程序所在目录/logs)
DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILENAME = "coil_architect.log"
CRASH_FILENAME = "last_crash.log"
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3                  # 最多保留 3 个滚动备份

_LOGGER_INITIALIZED = False
_LOG_FILE_PATH: Optional[Path] = None


class SafeStreamHandler(logging.StreamHandler):
    """防止在 Windows GBK 控制台下因特殊字符抛出 UnicodeEncodeError"""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                enc = getattr(stream, "encoding", "gbk") or "gbk"
                safe_msg = msg.encode(enc, errors="replace").decode(enc)
                stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def get_log_dir() -> Path:
    """获取并确保日志目录存在"""
    global DEFAULT_LOG_DIR
    target = DEFAULT_LOG_DIR
    try:
        target.mkdir(parents=True, exist_ok=True)
        return target
    except Exception:
        fallback = Path(os.environ.get("APPDATA", str(Path.home()))) / "CoilArchitect" / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def setup_logging(log_level: int = logging.INFO) -> Path:
    """
    初始化全局日志系统：配置根日志器、滚动文件处理器与控制台输出。
    返回日志文件绝对路径。
    """
    global _LOGGER_INITIALIZED, _LOG_FILE_PATH
    if _LOGGER_INITIALIZED and _LOG_FILE_PATH:
        return _LOG_FILE_PATH

    log_dir = get_log_dir()
    log_file = log_dir / LOG_FILENAME
    _LOG_FILE_PATH = log_file

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除旧的重复处理器
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # 1. 统一格式器 (含毫秒级时间戳)
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d [%(levelname)-5s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 2. 滚动文件处理器 (安全 UTF-8, 5MB 轮转)
    try:
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
            delay=True
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"[LoggerSetupError] 无法创建日志文件处理器: {e}", file=sys.stderr)

    # 3. 控制台处理器
    if sys.stdout and hasattr(sys.stdout, "write"):
        try:
            console_handler = SafeStreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        except Exception:
            pass

    _LOGGER_INITIALIZED = True
    root_logger.info(f"=== Coil-Architect Pro 日志引擎已启动 | 日志文件: {log_file} ===")
    return log_file


def get_logger(name: str = "CoilArchitect") -> logging.Logger:
    """获取指定模块命名的子日志器"""
    if not _LOGGER_INITIALIZED:
        setup_logging()
    return logging.getLogger(name)


logger = get_logger("CoilArchitect")


def install_crash_hook():
    """
    安装全局未捕获异常处理器 (sys.excepthook)
    确保任何 Python 崩溃闪退、未捕获异常均 100% 写入日志磁盘并弹窗自救
    """
    orig_hook = sys.excepthook
    crash_logger = get_logger("CrashReporter")

    def global_excepthook(exc_type, exc_value, exc_traceback):
        # 1. 记录完整堆栈到日志文件
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = "".join(tb_lines)
        crash_logger.critical(
            f"!!! 检测到全局未捕获异常 (CRASH / UNCAUGHT EXCEPTION) !!!\n"
            f"异常类型: {exc_type.__name__}\n"
            f"异常信息: {exc_value}\n"
            f"异常堆栈:\n{tb_text}"
        )

        # 2. 写入简要崩溃记录到 last_crash.log
        try:
            from datetime import datetime
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean_code = f"{exc_type.__name__}: {str(exc_value)[:120]}"
            crash_file = get_log_dir() / CRASH_FILENAME
            crash_file.write_text(f"{time_str}|{clean_code}\n", encoding="utf-8")
        except Exception:
            pass

        # 3. 若有活跃的 Qt 界面，弹出友好提示杜绝静默闪退
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app_inst = QApplication.instance()
            if app_inst:
                QMessageBox.critical(
                    None,
                    "系统异常提示",
                    f"Coil-Architect Pro 捕获到未处理的底层异常：\n\n"
                    f"{exc_type.__name__}: {str(exc_value)[:100]}\n\n"
                    f"故障详细堆栈已记录至运行日志：\n{_LOG_FILE_PATH}\n"
                    f"请联系系统运维人员排查。"
                )
        except Exception:
            pass

        # 4. 调用原生 hook
        if orig_hook:
            orig_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = global_excepthook
    crash_logger.info("全局异常与崩溃捕获钩子 (CrashHook) 已安装")


def collect_system_fingerprint() -> dict:
    """收集系统诊断指纹信息"""
    import json
    import platform
    from datetime import datetime
    try:
        from src.version import APP_VERSION, APP_BUILD, BUILD_TIME, get_git_commit
        git_commit = get_git_commit()
    except Exception:
        APP_VERSION = "v1.1.0"
        APP_BUILD = "20261014_B1"
        BUILD_TIME = "2026-10-20"
        git_commit = "bca8bfe"

    machine_id = "UNKNOWN"
    mac_addr = "UNKNOWN"
    try:
        from src.core.license_manager import get_machine_code, get_mac_address
        machine_id = get_machine_code()
        mac_addr = get_mac_address()
    except Exception:
        pass

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "app_name": "Coil-Architect Pro",
        "app_version": APP_VERSION,
        "app_build": APP_BUILD,
        "git_commit": git_commit,
        "build_time": BUILD_TIME,
        "machine_id": machine_id,
        "mac_address": mac_addr,
        "os_platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "system_encoding": sys.getdefaultencoding(),
    }


def export_diagnostic_bundle(target_dir: Optional[Path] = None) -> Path:
    """
    一键打包全量诊断包为 ZIP 归档文件
    包含：
    1. coil_architect.log 全量日志与滚动历史日志
    2. system_diagnostic_summary.json 系统软硬件与网络指纹
    3. diagnostic_readme.txt 诊断指引与研发说明
    """
    import json
    import zipfile
    from datetime import datetime

    diag_logger = get_logger("DiagnosticBundle")
    log_dir = get_log_dir()

    if target_dir is None:
        desktop = Path.home() / "Desktop"
        target_dir = desktop if desktop.exists() else log_dir

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    machine_id_short = "UNKNOWN"
    try:
        from src.core.license_manager import get_machine_code
        machine_id_short = get_machine_code().replace("COIL-", "")[:8]
    except Exception:
        pass

    zip_filename = f"CoilArchitect_Diagnostic_{machine_id_short}_{timestamp_str}.zip"
    zip_path = target_dir / zip_filename

    fingerprint = collect_system_fingerprint()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. 写入环境摘要 JSON
        summary_str = json.dumps(fingerprint, ensure_ascii=False, indent=2)
        zf.writestr("system_diagnostic_summary.json", summary_str.encode("utf-8"))

        # 2. 写入研发快速排查说明
        readme_lines = [
            "=" * 72,
            f"ANSV Coil-Architect Pro 诊断体检报告包 (生成时间: {fingerprint.get('timestamp')})",
            "=" * 72,
            f"平台全称: ANSV 微型执行器与精密传动仿真验证平台",
            f"软件模块: Coil-Architect Pro 电磁线圈多物理场仿真工作站",
            f"软件版本: v{fingerprint.get('app_version', '-')} (Build {fingerprint.get('app_build', '-')})",
            f"Git指纹:  {fingerprint.get('git_commit', '-')} (构建于: {fingerprint.get('build_time', '-')})",
            f"机器代码: {fingerprint.get('machine_id', '-')}",
            f"物理MAC:  {fingerprint.get('mac_address', '-')}",
            f"运行环境: {fingerprint.get('os_platform', '-')} | Python {fingerprint.get('python_version', '-')}",
            "=" * 72,
            "【使用说明】:",
            "请将本压缩包直接发送给 ANSV 平台研发工程师，工程师可精准溯源日志与异常堆栈。",
            "=" * 72,
        ]
        zf.writestr("diagnostic_readme.txt", "\n".join(readme_lines).encode("utf-8"))

        # 3. 收集并写入全部相关 log 文件
        for log_f in log_dir.glob(f"{LOG_FILENAME}*"):
            if log_f.is_file():
                try:
                    zf.write(log_f, arcname=f"logs/{log_f.name}")
                except Exception as e:
                    diag_logger.warning(f"打包日志文件 {log_f.name} 失败: {e}")

        # 如果有崩溃记录也一并写入
        crash_log = log_dir / CRASH_FILENAME
        if crash_log.exists():
            try:
                zf.write(crash_log, arcname=f"logs/{crash_log.name}")
            except Exception:
                pass

    diag_logger.info(f"✅ 全景诊断包已成功生成: {zip_path}")
    return zip_path


def open_log_directory():
    """在操作系统资源管理器中打开日志目录"""
    log_dir = get_log_dir()
    if sys.platform == "win32":
        os.startfile(str(log_dir))
    else:
        import subprocess
        subprocess.run(["xdg-open", str(log_dir)])

