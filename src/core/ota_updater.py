"""
=============================================================================
Module: src.core.ota_updater
Description: Coil-Architect Pro 软件本体 OTA 静默自动升级引擎 (OtaUpdater & OtaChecker)
深度对标 Gear-NVH / FFT 分析软件 全量工业商业桌面软件企业内网与断点续传影子替换架构
-----------------------------------------------------------------------------
功能特性：
1. 双轨智能升级决策：工位机已处于安装运行态，优先拉取 ~8.7 MB 累积增量热补丁包；
2. 分块断点续传与自愈：支持 256KB 分块、HTTP 206 断点续传，国内镜像多源轮换；
3. 全静默后台热升级：打开软件后台静默检测与限速下载 (throttle=True)，绝不打扰工位仿真；
4. 影子替换架构 (Shadow Replacement)：更新就绪后不中断当前工作，软件退出时后台静默覆盖，
   下次启动自动生效；支持 UpdateDialog 显式立即重启。
=============================================================================
"""

import os
import sys
import json
import time
import hashlib
import platform
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.version import APP_VERSION, APP_BUILD, compare_versions, compare_builds
from src.core.cloud_client import (
    load_cloud_config, get_opener, _CLIENT_API_KEY, 
    _get_safe_ssl_context, DEFAULT_CLOUD_BASE_URL, FALLBACK_SERVER_URLS
)
import src.core.smart_dns
from src.utils.logger import get_logger

logger = get_logger("OtaUpdater")

# 升级包专用隐藏暂存目录
UPDATE_CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / ".coil_update"
MANIFEST_FILE = UPDATE_CACHE_DIR / "update_ready.json"
MAX_DOWNLOAD_SPEED_BYTES = 1024 * 1024  # 静默限速 ≤ 1 MB/s
CHUNK_SIZE = 256 * 1024  # 256 KB 分块

# 标准兼容浏览器 User-Agent，规避 Cloudflare WAF 误拦截
STANDARD_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    f"(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 CoilArchitectPro-OTA/{APP_VERSION}"
)


def get_ota_opener():
    """获取继承企业数据库网络与代理配置、兼容 SSL 证书的安全 urllib Opener"""
    try:
        cfg = load_cloud_config()
        return get_opener(cfg.get("proxy_setting", "auto"), cfg.get("custom_proxy", ""))
    except Exception:
        return urllib.request.build_opener(urllib.request.HTTPSHandler(context=_get_safe_ssl_context()))


def get_candidate_server_urls() -> list:
    """获取用于版本检测与更新的多级高可用服务端节点列表"""
    urls = []
    try:
        cfg = load_cloud_config()
        if cfg.get("server_url"):
            urls.append(cfg["server_url"].rstrip("/"))
        for u in cfg.get("fallback_urls", []):
            if u and u not in urls:
                urls.append(u.rstrip("/"))
    except Exception:
        pass
    for u in [DEFAULT_CLOUD_BASE_URL, "https://coil.ansv.net"]:
        if u not in urls:
            urls.append(u.rstrip("/"))
    return urls


def calculate_sha256(file_path: Path) -> str:
    """计算文件的 SHA256 哈希值 (十六进制全小写)"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest().lower()


class OtaUpdater(QObject):
    """
    OTA 升级管理器：负责版本检查、断点下载、SHA256 校验与影子替换部署
    """
    update_available = pyqtSignal(dict)                     # (version_info)
    update_download_progress = pyqtSignal(int, int, float)  # (current_bytes, total_bytes, speed_mbps)
    update_download_ready = pyqtSignal(str, str)            # (latest_version, zip_path)
    update_download_failed = pyqtSignal(str)                # (error_msg)

    _instance = None

    @classmethod
    def get_instance(cls) -> "OtaUpdater":
        if cls._instance is None:
            cls._instance = OtaUpdater()
        return cls._instance

    def __init__(self):
        super().__init__()
        UPDATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.current_version = APP_VERSION
        self.current_build = APP_BUILD
        self._is_downloading = False
        self._cancel_download = False
        self.last_check_error: str = ""
        self.last_download_error: str = ""

    def check_version(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        向云端节点发起版本检测，支持企业代理与多级高可用容灾
        """
        from src.core.license_manager import LicenseManager
        is_auth, auth_msg, lic_data = LicenseManager.is_system_authorized()
        machine_id = lic_data.get("machine_id", "-") if lic_data else "-"
        lic_status = "AUTHORIZED" if is_auth else "TRIAL"

        headers = {
            "X-API-Key": _CLIENT_API_KEY,
            "User-Agent": STANDARD_USER_AGENT,
            "X-Machine-ID": urllib.parse.quote(str(machine_id)),
            "X-Hostname": urllib.parse.quote(str(platform.node())),
            "X-App-Version": str(self.current_version),
            "X-App-Build": str(self.current_build),
            "X-License-Status": lic_status
        }

        candidate_urls = get_candidate_server_urls()
        opener = get_ota_opener()
        errors = []

        for base_url in candidate_urls:
            # 兼容两个标准路由: /api/v1/check_update 与 /api/v1/app/version-check
            for path in ["/api/v1/check_update", "/api/v1/app/version-check"]:
                url = f"{base_url}{path}"
                try:
                    req = urllib.request.Request(url, headers=headers, method="GET")
                    with opener.open(req, timeout=12) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            self.last_check_error = ""

                            # 统一标准化元信息
                            raw_ver = data.get("version") or data.get("latest_version") or "0.0.0"
                            raw_build = str(data.get("build") or "").strip()
                            raw_notes = data.get("changelog") or data.get("release_notes") or ""
                            dl_url = data.get("download_url") or ""
                            gh_url = data.get("github_download_url") or (dl_url if "github.com" in dl_url else "")
                            patch_url = data.get("patch_url") or data.get("patch_download_url") or ""
                            sha = (data.get("sha256") or "").strip().lower()
                            patch_sha = (data.get("patch_sha256") or "").strip().lower()

                            # 计算字节大小
                            file_size = int(data.get("file_size_bytes") or (float(data.get("file_size_mb", 0)) * 1024 * 1024))
                            patch_size = int(data.get("patch_size_bytes") or (float(data.get("patch_size_mb", 0)) * 1024 * 1024))

                            norm = {
                                "latest_version": raw_ver,
                                "version": raw_ver,
                                "build": raw_build,
                                "release_notes": raw_notes,
                                "changelog": raw_notes,
                                "download_url": dl_url,
                                "github_download_url": gh_url,
                                "patch_download_url": patch_url,
                                "patch_url": patch_url,
                                "sha256": sha,
                                "patch_sha256": patch_sha,
                                "file_size_bytes": file_size,
                                "patch_size_bytes": patch_size,
                                "is_patch": bool(patch_url),
                                "is_mandatory": bool(data.get("is_mandatory", False)),
                                "server_base_url": base_url
                            }

                            v_cmp = compare_versions(raw_ver, self.current_version)
                            if v_cmp > 0:
                                return True, norm
                            elif v_cmp == 0:
                                # 版本号相同，比对构建号
                                if raw_build and compare_builds(raw_build, str(self.current_build)) > 0:
                                    return True, norm

                                # 比对本地已安装 SHA256 (同版本热补丁)
                                local_sha_file = UPDATE_CACHE_DIR / "current_installed_sha256.txt"
                                if local_sha_file.exists() and (sha or patch_sha):
                                    try:
                                        local_sha = local_sha_file.read_text(encoding="utf-8").strip().lower()
                                        if local_sha and (local_sha != sha and local_sha != patch_sha):
                                            return True, norm
                                    except Exception:
                                        pass
                            return False, norm
                        else:
                            errors.append(f"{url} (HTTP {resp.status})")
                except urllib.error.HTTPError as he:
                    errors.append(f"{url} (HTTP {he.code})")
                except Exception as e:
                    errors.append(f"{url} ({e})")

        self.last_check_error = "; ".join(errors) if errors else "网络连接超时或无法解析云端服务节点"
        return False, None

    def is_update_ready(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        检测本地是否已有一份通过校验且就绪的更新包
        """
        if not MANIFEST_FILE.exists():
            return False, None
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
            zip_path = Path(meta.get("zip_path", ""))
            staged_dir = Path(meta.get("staged_dir", ""))
            version = meta.get("version", "")
            ready_build = str(meta.get("build") or "").strip()
            expected_sha = meta.get("sha256", "").lower()

            has_source = zip_path.exists() or staged_dir.exists()
            v_cmp = compare_versions(version, self.current_version)
            if v_cmp == 0 and meta.get("is_patch", False) and ready_build:
                if compare_builds(ready_build, self.current_build) <= 0:
                    try:
                        MANIFEST_FILE.unlink(missing_ok=True)
                        if zip_path.exists():
                            zip_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return False, None

            if has_source and (v_cmp > 0 or (v_cmp == 0 and (not ready_build or compare_builds(ready_build, self.current_build) > 0))):
                if zip_path.exists() and zip_path.stat().st_size < 100 * 1024:
                    try:
                        MANIFEST_FILE.unlink(missing_ok=True)
                        zip_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return False, None

                if expected_sha and zip_path.exists():
                    if calculate_sha256(zip_path) != expected_sha:
                        return False, None
                return True, meta
        except Exception:
            pass
        return False, None

    def download_update_package(
        self,
        version_info: Dict[str, Any],
        progress_callback=None,
        throttle: bool = False
    ) -> bool:
        """
        分块断点续传下载升级包，支持实时进度与速率反馈，具备国内高可用镜像、多节点自动容灾与自愈续传
        """
        import zipfile
        import shutil

        if self._is_downloading:
            return False
        self._is_downloading = True
        self._cancel_download = False

        latest_ver = version_info.get("latest_version") or version_info.get("version")
        expected_sha = (version_info.get("sha256") or "").lower()
        dl_rel_url = version_info.get("download_url") or ""
        gh_url = version_info.get("github_download_url") or ""

        # 智能双轨优先决策：工位机已处于安装运行态，优先拉取 ~8.7 MB 累积热补丁包
        patch_url = version_info.get("patch_download_url") or version_info.get("patch_url") or ""
        clean_tag = latest_ver if str(latest_ver).startswith("v") else f"v{latest_ver}"
        if not patch_url or "ansv.net/download" in patch_url:
            patch_url = f"https://github.com/tonychen5577-tech/coil-architect/releases/download/{clean_tag}/ANSV_Coil_Architect_Pro_{clean_tag}_Incremental_Patch.zip"

        if not dl_rel_url or "ansv.net/download" in dl_rel_url:
            dl_rel_url = f"https://github.com/tonychen5577-tech/coil-architect/releases/download/{clean_tag}/ANSV_Coil_Architect_Pro_{clean_tag}_Full.zip"

        patch_sha = (version_info.get("patch_sha256") or "").lower()

        use_patch = False
        if patch_url and "http" in patch_url:
            use_patch = True
            if patch_sha:
                expected_sha = patch_sha
            elif expected_sha:
                expected_sha = ""  # 避免用全量包 SHA 误判补丁包

        # 整理候选下载源 (优先国内高速镜像 -> Cloudflare 边缘代理 -> GitHub Releases 直链)
        candidate_urls = []
        if use_patch and patch_url:
            candidate_urls.append(patch_url)
            if "github.com" in patch_url:
                candidate_urls.insert(0, f"https://ghfast.top/{patch_url}")
                candidate_urls.insert(1, f"https://ghproxy.net/{patch_url}")

        if gh_url:
            candidate_urls.append(f"https://ghfast.top/{gh_url}")
            candidate_urls.append(f"https://ghproxy.net/{gh_url}")
            candidate_urls.append(gh_url)

        if dl_rel_url and dl_rel_url not in candidate_urls:
            candidate_urls.append(dl_rel_url)

        if not candidate_urls:
            self._is_downloading = False
            self.last_download_error = "更新包下载地址为空"
            return False

        zip_prefix = "Coil_Architect_Patch_v" if use_patch else "Coil_Architect_v"
        target_zip = UPDATE_CACHE_DIR / f"{zip_prefix}{latest_ver}.zip"
        part_zip = UPDATE_CACHE_DIR / f"{zip_prefix}{latest_ver}.part"
        opener = get_ota_opener()
        expected_size = int((version_info.get("patch_size_bytes") if use_patch else version_info.get("file_size_bytes")) or 0)

        # 预检查 1: 若正式 zip 已存在且 SHA256 校验完全一致，免重复下载直接复用
        if target_zip.exists():
            if not expected_sha or calculate_sha256(target_zip) == expected_sha:
                logger.info(f"[OTA] 本地正式包已就绪且校验一致，直接复用: {target_zip}")
                self._is_downloading = False
                self.update_download_ready.emit(latest_ver, str(target_zip))
                return True

        # 预检查 2: 若 .part 文件已完整并校验一致，直接重命名复用
        if part_zip.exists():
            actual_size = part_zip.stat().st_size
            if (expected_size == 0 or actual_size >= expected_size) and expected_sha and calculate_sha256(part_zip) == expected_sha:
                logger.info(f"[OTA] 本地断点文件已完整且校验一致，直接装载: {part_zip}")
                if target_zip.exists():
                    target_zip.unlink()
                part_zip.replace(target_zip)
                self._is_downloading = False
                self.update_download_ready.emit(latest_ver, str(target_zip))
                return True

        # 多轮自愈重试机制 (最多尝试 8 次，轮换可用镜像源与边缘代理)
        max_attempts = max(8, len(candidate_urls) * 2)
        download_success = False

        for attempt in range(1, max_attempts + 1):
            if self._cancel_download:
                self._is_downloading = False
                return False

            download_url = candidate_urls[(attempt - 1) % len(candidate_urls)]
            logger.info(f"[OTA] 正在尝试从源 ({attempt}/{max_attempts}) 下载: {download_url[:65]}...")

            try:
                existing_size = part_zip.stat().st_size if part_zip.exists() else 0
                if expected_size > 0 and existing_size > expected_size:
                    part_zip.unlink(missing_ok=True)
                    existing_size = 0

                headers = {
                    "X-API-Key": _CLIENT_API_KEY,
                    "User-Agent": STANDARD_USER_AGENT
                }
                if existing_size > 0:
                    headers["Range"] = f"bytes={existing_size}-"

                req = urllib.request.Request(download_url, headers=headers)
                try:
                    resp = opener.open(req, timeout=35)
                except urllib.error.HTTPError as he:
                    if he.code == 416:  # Range Not Satisfiable
                        if existing_size > 0 and expected_sha and calculate_sha256(part_zip) == expected_sha:
                            download_success = True
                            break
                        existing_size = 0
                        part_zip.unlink(missing_ok=True)
                        headers.pop("Range", None)
                        req = urllib.request.Request(download_url, headers=headers)
                        resp = opener.open(req, timeout=35)
                    else:
                        raise he

                if resp.status not in (200, 206):
                    raise RuntimeError(f"HTTP 响应状态码异常: {resp.status}")

                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type.lower():
                    raise RuntimeError(f"节点返回 HTML 页面而非 ZIP 数据流: {content_type}")

                total_bytes = 0
                content_range = resp.headers.get("Content-Range", "")
                if content_range and "/" in content_range:
                    try:
                        total_bytes = int(content_range.split("/")[-1].strip())
                    except Exception:
                        pass

                if total_bytes <= 0:
                    total_content_length = resp.headers.get("Content-Length")
                    if total_content_length:
                        if resp.status == 206:
                            total_bytes = existing_size + int(total_content_length)
                        else:
                            total_bytes = int(total_content_length)
                    else:
                        total_bytes = expected_size

                mode = "ab" if existing_size > 0 and resp.status == 206 else "wb"
                if mode == "wb":
                    existing_size = 0

                downloaded_bytes = existing_size
                last_calc_time = time.perf_counter()
                last_calc_bytes = downloaded_bytes
                current_speed = 0.0

                with open(part_zip, mode) as out_f:
                    while True:
                        if self._cancel_download:
                            resp.close()
                            self._is_downloading = False
                            return False

                        t_start = time.perf_counter()
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded_bytes += len(chunk)

                        now = time.perf_counter()
                        dt = now - last_calc_time
                        if dt >= 0.25:
                            bytes_diff = downloaded_bytes - last_calc_bytes
                            current_speed = (bytes_diff / (1024 * 1024)) / dt if dt > 0 else 0.0
                            last_calc_time = now
                            last_calc_bytes = downloaded_bytes

                        if progress_callback:
                            progress_callback(downloaded_bytes, total_bytes, current_speed)
                        self.update_download_progress.emit(downloaded_bytes, total_bytes, current_speed)

                        if throttle:
                            t_elapsed = time.perf_counter() - t_start
                            t_min = len(chunk) / MAX_DOWNLOAD_SPEED_BYTES
                            if t_elapsed < t_min:
                                time.sleep(t_min - t_elapsed)

                actual_size = part_zip.stat().st_size if part_zip.exists() else 0
                if total_bytes > 0 and actual_size < total_bytes:
                    cur_mb = actual_size / (1024 * 1024)
                    tot_mb = total_bytes / (1024 * 1024)
                    self.last_download_error = f"网络传输中断 ({cur_mb:.1f}/{tot_mb:.1f} MB)，断点已保存，正在自动换源续传..."
                    logger.warning(f"[OTA] {self.last_download_error}")
                    time.sleep(0.5)
                    continue

                if expected_sha:
                    computed_sha = calculate_sha256(part_zip)
                    if computed_sha != expected_sha:
                        part_zip.unlink(missing_ok=True)
                        self.last_download_error = f"校验失败: 期望 {expected_sha[:10]}... 实际 {computed_sha[:10]}..."
                        logger.warning(f"[OTA] {self.last_download_error}")
                        time.sleep(0.5)
                        continue

                download_success = True
                break

            except Exception as e:
                actual_size = part_zip.stat().st_size if part_zip.exists() else 0
                cur_mb = actual_size / (1024 * 1024)
                self.last_download_error = f"连接异常 ({e})，断点已保存 ({cur_mb:.1f} MB)，正在自动续传..."
                logger.warning(f"[OTA] {self.last_download_error}")
                time.sleep(0.5)
                continue

        if not download_success:
            self._is_downloading = False
            self.update_download_failed.emit(self.last_download_error or "所有候选更新源下载均失败，请检查网络设置。")
            return False

        # 重命名为正式文件
        if target_zip.exists():
            target_zip.unlink()
        part_zip.replace(target_zip)

        # 提前在 Python 端将更新包解压至 staged 暂存目录 (规避批处理解压异常与依赖)
        staged_dir = UPDATE_CACHE_DIR / "staged"
        if staged_dir.exists():
            try:
                shutil.rmtree(staged_dir, ignore_errors=True)
            except Exception:
                pass
        staged_dir.mkdir(parents=True, exist_ok=True)

        copy_source = staged_dir
        try:
            with zipfile.ZipFile(target_zip, "r") as zf:
                zf.extractall(staged_dir)
            # 若解压后包含单层根目录，平铺定位
            for sub in staged_dir.iterdir():
                if sub.is_dir() and "Coil" in sub.name:
                    copy_source = sub
                    break
        except Exception as e:
            logger.warning(f"[OTA] 预解压升级包出现异常: {e}")

        # 记录就绪清单
        manifest = {
            "ready": True,
            "version": latest_ver,
            "build": version_info.get("build", ""),
            "is_patch": use_patch,
            "zip_path": str(target_zip.resolve()),
            "staged_dir": str(copy_source.resolve()),
            "sha256": expected_sha,
            "release_notes": version_info.get("release_notes", ""),
            "downloaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        self._is_downloading = False
        self.update_download_ready.emit(latest_ver, str(target_zip))
        return True

    def cancel_download(self):
        """取消当前正在进行的后台下载"""
        self._cancel_download = True

    def get_app_install_dir(self) -> Path:
        """获取当前 EXE 运行目录或脚本工作目录"""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent.parent.parent

    def is_install_dir_writable(self) -> bool:
        """检查当前安装目录是否有写入/覆盖权限"""
        install_dir = self.get_app_install_dir()
        test_file = install_dir / f".perm_test_{os.getpid()}"
        try:
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return True
        except (PermissionError, OSError):
            return False

    _shadow_replacement_active: bool = False

    def generate_updater_ps1(self) -> Path:
        """生成基于 PowerShell 的完全静默、高可靠影子替换脚本 updater.ps1"""
        UPDATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ps_path = UPDATE_CACHE_DIR / "updater.ps1"
        ps_content = r"""param(
    [int]$TargetPid = 0,
    [string]$ZipFile = "",
    [string]$InstallDir = "",
    [string]$ExeName = "",
    [string]$NewVer = "",
    [string]$StagedDir = "",
    [switch]$RestartAfterUpdate
)

if ($InstallDir) { $InstallDir = $InstallDir.Trim('\"''').TrimEnd('\', '/') }
if ($StagedDir) { $StagedDir = $StagedDir.Trim('\"''').TrimEnd('\', '/') }
if ($ZipFile) { $ZipFile = $ZipFile.Trim('\"''') }
if ($ExeName) { $ExeName = $ExeName.Trim('\"''') }

$logDir = Join-Path $env:LOCALAPPDATA ".coil_update"
if (-not (Test-Path -Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null
}
$logFile = Join-Path $logDir "ota_update.log"

function Log-Msg($msg) {
    $timeStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$timeStr] [Coil-Architect OTA] $msg" -Encoding UTF8 -ErrorAction SilentlyContinue
}

Log-Msg "=================================================="
Log-Msg "开始执行静默影子替换升级流程 (目标 PID: $TargetPid, 新版本: $NewVer)"
Log-Msg "安装目录: $InstallDir"
Log-Msg "可执行文件: $ExeName"

# 1. 监控并等待主进程安全退出 (最多等待 8 秒)
if ($TargetPid -gt 0) {
    Log-Msg "正在等待主进程 PID $TargetPid 退出..."
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt 8000) {
        $proc = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
        if (-not $proc -or $proc.HasExited) { break }
        Start-Sleep -Milliseconds 250
    }
    $proc = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
    if ($proc -and -not $proc.HasExited) {
        Log-Msg "主进程未能及时退出，强行终止 PID $TargetPid 释放文件锁..."
        Stop-Process -Id $TargetPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    } else {
        Log-Msg "主进程已安全退出。"
    }
}

# 清理可能残留的同名进程
$baseName = [System.IO.Path]::GetFileNameWithoutExtension($ExeName)
if ($baseName) {
    Get-Process -Name $baseName -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $PID } | Stop-Process -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 400

# 2. 确认替换源目录
$copySrc = ""
if (-not [string]::IsNullOrWhiteSpace($StagedDir) -and (Test-Path -LiteralPath $StagedDir)) {
    $copySrc = $StagedDir
    foreach ($sub in Get-ChildItem -LiteralPath $StagedDir -Directory -ErrorAction SilentlyContinue) {
        if ($sub.Name -like "*Coil*") {
            $copySrc = $sub.FullName
            break
        }
    }
} elseif (-not [string]::IsNullOrWhiteSpace($ZipFile) -and (Test-Path -LiteralPath $ZipFile)) {
    Log-Msg "暂存目录不存在，准备从 Zip 解压: $ZipFile"
    $tempExtract = Join-Path $env:TEMP ("coil_update_extract_" + (Get-Random))
    if (Test-Path -LiteralPath $tempExtract) { Remove-Item -LiteralPath $tempExtract -Recurse -Force -ErrorAction SilentlyContinue }
    New-Item -Path $tempExtract -ItemType Directory -Force | Out-Null
    Expand-Archive -LiteralPath $ZipFile -DestinationPath $tempExtract -Force
    $copySrc = $tempExtract
} else {
    Log-Msg "【严重错误】更新包与解压源均不存在，升级终止！"
    exit 1
}
$copySrc = $copySrc.TrimEnd('\', '/')
Log-Msg "源文件目录: $copySrc"

# 3. 执行核心文件覆盖 (带 5 次重试机制应对杀软扫描占用)
$maxRetries = 5
$success = $false
for ($i = 1; $i -le $maxRetries; $i++) {
    Log-Msg "正在执行文件覆盖 (第 $i / $maxRetries 次尝试)..."
    try {
        $rc = Start-Process -FilePath "robocopy.exe" -ArgumentList "`"$copySrc`"", "`"$InstallDir`"", "/E", "/NP", "/R:2", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS" -NoNewWindow -Wait -PassThru
        if ($rc.ExitCode -lt 8) {
            $success = $true
            Log-Msg "核心文件覆盖成功 (Robocopy 返回码: $($rc.ExitCode))"
            break
        }
    } catch {
        Log-Msg "Robocopy 启动异常: $_"
    }

    try {
        Get-ChildItem -LiteralPath $copySrc -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $InstallDir -Recurse -Force -ErrorAction Stop
        }
        $success = $true
        Log-Msg "通过 Copy-Item 覆盖成功"
        break
    } catch {
        Log-Msg "Copy-Item 尝试失败: $_"
    }
    Start-Sleep -Milliseconds 1000
}

if (-not $success) {
    Log-Msg "【严重错误】核心文件覆盖失败，升级终止！"
    exit 1
}

# 4. 写入新版升级成功标志
$flagFile = Join-Path $InstallDir ".updated_flag"
Set-Content -Path $flagFile -Value $NewVer -Encoding UTF8
Log-Msg "已写入升级成功标志文件: $flagFile (版本: $NewVer)"

# 5. 清理本地就绪清单 (防止重复提示)
$manifestPath = Join-Path $env:LOCALAPPDATA ".coil_update\update_ready.json"
if (Test-Path -Path $manifestPath) {
    Remove-Item -Path $manifestPath -Force -ErrorAction SilentlyContinue
    Log-Msg "已清理就绪清单: $manifestPath"
}

# 6. 重新拉起新版进程 (微信式体验：仅在显式请求重启时拉起；正常退出时静默完成，不自启)
if ($RestartAfterUpdate) {
    $targetExe = Join-Path $InstallDir $ExeName
    Log-Msg "用户选择立即重启，正在启动新版程序: $targetExe"
    if (Test-Path -LiteralPath $targetExe) {
        Start-Process -FilePath $targetExe -WorkingDirectory $InstallDir -WindowStyle Normal
        Log-Msg "新版本启动成功！OTA 升级圆满完成。"
    } else {
        Log-Msg "【警告】未找到目标可执行文件: $targetExe"
    }
} else {
    Log-Msg "遵循微信式静默升级体验：遵从用户关闭退出意图，不自动重新弹起程序。"
}

Log-Msg "升级脚本执行完毕，退出。"
exit 0
"""
        with open(ps_path, "w", encoding="utf-8-sig") as f:
            f.write(ps_content)
        return ps_path

    def generate_updater_bat(self) -> Path:
        """生成兼容性批处理包装脚本 updater.bat"""
        UPDATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        bat_path = UPDATE_CACHE_DIR / "updater.bat"
        bat_content = r"""@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "TARGET_PID=%~1"
set "ZIP_FILE=%~2"
set "INSTALL_DIR=%~3"
set "EXE_NAME=%~4"
set "NEW_VER=%~5"
set "STAGED_DIR=%~6"
set "RESTART_AFTER=%~7"

set "LOG_DIR=%LOCALAPPDATA%\.coil_update"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\ota_update.log"

echo [%date% %time%] [OTA-BAT] 开始执行批处理备用升级流程... >> "%LOG_FILE%"

:: 1. 终止进程释放文件锁
if not "%TARGET_PID%"=="" (
    taskkill /PID %TARGET_PID% /F >nul 2>&1
)
if not "%EXE_NAME%"=="" (
    taskkill /IM "%EXE_NAME%" /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: 2. 文件覆盖
set "COPY_SRC=%STAGED_DIR%"
if not exist "%COPY_SRC%" (
    if exist "%ZIP_FILE%" (
        powershell.exe -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP_FILE%' -DestinationPath '%TEMP%\coil_bat_ext' -Force" >nul 2>&1
        set "COPY_SRC=%TEMP%\coil_bat_ext"
    )
)

if exist "%COPY_SRC%" (
    robocopy "%COPY_SRC%" "%INSTALL_DIR%" /E /NP /R:2 /W:1 /NFL /NDL /NJH /NJS >nul
    if errorlevel 8 (
        xcopy "%COPY_SRC%\*" "%INSTALL_DIR%\" /E /Y /Q >nul 2>&1
    )
)

:: 3. 写入升级成功标志
echo %NEW_VER%> "%INSTALL_DIR%\.updated_flag"

:: 4. 清理就绪清单
if exist "%LOG_DIR%\update_ready.json" del /f /q "%LOG_DIR%\update_ready.json" >nul 2>&1

:: 5. 重新拉起程序 (微信式体验：仅在 RESTART_AFTER=1 时拉起，否则安静退出)
if "%RESTART_AFTER%"=="1" (
    if exist "%INSTALL_DIR%\%EXE_NAME%" (
        start "" /D "%INSTALL_DIR%" "%INSTALL_DIR%\%EXE_NAME%"
        echo [%date% %time%] [OTA-BAT] 新版程序拉起成功 >> "%LOG_FILE%"
    )
)

exit 0
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        return bat_path

    def launch_shadow_replacement(self, restart_after: bool = False) -> bool:
        """
        呼出影子替换脚本，防重锁定并完全静默独立运行
        :param restart_after: True 时覆盖后立即重启程序；False 时仅静默覆盖并安静退出 (微信式体验)
        """
        if self._shadow_replacement_active:
            logger.info("影子替换升级脚本已在运行中，跳过重复拉起。")
            return True

        ready, meta = self.is_update_ready()
        if not ready or not meta:
            return False

        self._shadow_replacement_active = True

        zip_path = str(Path(meta.get("zip_path", "")).resolve()).rstrip(r"\/")
        staged_dir = str(Path(meta.get("staged_dir", "")).resolve()).rstrip(r"\/")
        new_version = str(meta.get("version", "新版本")).strip()
        install_dir = str(self.get_app_install_dir().resolve()).rstrip(r"\/")
        exe_name = Path(sys.executable).name if getattr(sys, "frozen", False) else "Coil-Architect-Pro.exe"
        cur_pid = str(os.getpid())

        ps_path = self.generate_updater_ps1()
        bat_path = self.generate_updater_bat()

        ps_exe = "powershell.exe"
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        candidate = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if candidate.exists():
            ps_exe = str(candidate)

        flags = 0
        if platform.system() == "Windows":
            flags = subprocess.CREATE_NO_WINDOW | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

        # 1. 尝试以 PowerShell 纯静默拉起
        try:
            cmd_ps = [
                ps_exe,
                "-WindowStyle", "Hidden",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", str(ps_path),
                "-TargetPid", cur_pid,
                "-ZipFile", zip_path,
                "-InstallDir", install_dir,
                "-ExeName", exe_name,
                "-NewVer", new_version,
                "-StagedDir", staged_dir
            ]
            if restart_after:
                cmd_ps.append("-RestartAfterUpdate")

            subprocess.Popen(
                cmd_ps,
                creationflags=flags,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            logger.warning(f"拉起 PowerShell 影子升级脚本失败，尝试批处理后备: {e}")

        # 2. PowerShell 失败时，无缝回退到 updater.bat 保底
        try:
            restart_arg = "1" if restart_after else "0"
            cmd_bat = [
                "cmd.exe", "/c", str(bat_path),
                cur_pid, zip_path, install_dir, exe_name, new_version, staged_dir, restart_arg
            ]
            subprocess.Popen(
                cmd_bat,
                creationflags=flags,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e2:
            self._shadow_replacement_active = False
            logger.error(f"拉起批处理后备脚本亦失败: {e2}")
            return False

    def check_and_clear_updated_flag(self, return_version_only: bool = False) -> Optional[str]:
        """
        检查本次启动是否刚由 OTA 自动完成升级，若存在标志则返回升级提示语并清除标志
        """
        flag_file = self.get_app_install_dir() / ".updated_flag"
        if not flag_file.exists():
            return None
        try:
            with open(flag_file, "r", encoding="utf-8") as f:
                ver = f.read().strip()
            flag_file.unlink(missing_ok=True)
            if return_version_only:
                return ver or self.current_version
            now_date = datetime.now().strftime("%Y-%m-%d")
            return f"✅ 仿真引擎已优化至 v{ver or self.current_version}（{now_date}）"
        except Exception:
            return None


class OtaChecker(QThread):
    """
    后台静默 OTA 检查线程 (支持启动自检与定时巡检)
    """
    def __init__(self, updater: OtaUpdater, interval_sec: int = 3600, parent=None):
        super().__init__(parent)
        self.updater = updater
        self.interval_sec = max(interval_sec, 60)
        self._running = True

    def run(self):
        # 启动后先休眠 5 秒，避开主界面初次加载的资源争用
        for _ in range(5):
            if not self._running:
                return
            time.sleep(1)

        while self._running:
            try:
                # 1. 检查本地是否已有就绪更新包
                is_ready, meta = self.updater.is_update_ready()
                if is_ready and meta:
                    self.updater.update_download_ready.emit(meta.get("version", ""), meta.get("zip_path", ""))
                else:
                    # 2. 检查云端最新版本
                    has_new, info = self.updater.check_version()
                    if has_new and info:
                        self.updater.update_available.emit(info)
                        # 3. 静默在后台开始断点下载 (限速，不打扰当前仿真工作)
                        self.updater.download_update_package(info, throttle=True)
            except Exception as e:
                logger.debug(f"[OtaChecker] 异常已拦截: {e}")

            for _ in range(int(self.interval_sec)):
                if not self._running:
                    break
                time.sleep(1)

    def stop(self):
        self._running = False
        self.updater.cancel_download()
        self.wait(800)
        if self.isRunning():
            self.terminate()


def apply_staged_update_if_pending() -> Optional[str]:
    """
    软件启动前安全自检：若存在未完成覆盖的 staged 就绪包，执行就地拷贝覆盖并清除清单
    """
    try:
        if not MANIFEST_FILE.exists():
            return None
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        staged_dir = Path(meta.get("staged_dir", ""))
        ver = meta.get("version", "")
        if not staged_dir.exists():
            return None

        install_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        import shutil
        for item in staged_dir.iterdir():
            dest = install_dir / item.name
            try:
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            except Exception:
                pass

        try:
            (install_dir / ".updated_flag").write_text(ver, encoding="utf-8")
            MANIFEST_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return ver
    except Exception as e:
        logger.debug(f"启动前增量更新自愈拦截: {e}")
        return None

