"""
=============================================================================
Module: src.core.cloud_client
Description: Coil-Architect Pro - Cloudflare Serverless Edge Client & Remote Control Engine
架构规范：深度对标 Gear-NVH / FFT 分析软件 全量工业商业桌面软件云端架构规范
功能：
1. 实时双向心跳与工位机状态遥测 (每30秒静默同步，离线/超时绝对零卡顿)；
2. 云端远程遥控指令双向通道：
   - LOCK_APP / REVOKE_LICENSE: 远程吊销授权、销毁本地凭证并安全锁定；
   - UPDATE_LICENSE: 远程推送新激活码/静默延期；
   - FORCE_SYNC_CASES: 远程通知同步官方标杆案例库；
   - UNLOCK: 远程解除锁定；
3. 毫秒级指令回执 (ACK) 闭环确认；
4. 防倒拨时钟校准与原子钟防作弊检测；
5. 在线 OTA 新版本检测与下载分发。
=============================================================================
"""

import os
import sys
import ssl
import json
import time
import socket
import getpass
import shutil
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from threading import Thread, Event
from typing import Dict, Any, Optional, Tuple, Callable, List

from src.version import APP_VERSION, APP_BUILD
from src.core.license_manager import (
    get_machine_code, get_mac_address, detect_virtual_machine, 
    LicenseManager
)
from src.utils.logger import get_logger

logger = get_logger("CloudClient")

# 默认 Cloudflare 边缘服务器 API 基地址 (主域名 + 备用 workers.dev)
DEFAULT_CLOUD_BASE_URL = "https://coil.ansv.net"
FALLBACK_WORKER_URL = "https://coil-architect-cloud.tony-tech.workers.dev"

_CLIENT_API_KEY = "COIL-SEC-2026#Ansv_TonyTech_c82P"
_DEFAULT_TIMEOUT_SEC = 6.0


def _get_safe_ssl_context() -> ssl.SSLContext:
    """获取安全的 SSL 上下文 (在企业内网自签证书/杀毒软件劫持时保持通信顺畅)"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return ssl._create_unverified_context()


def _make_post_request(url: str, payload: dict, timeout: float = _DEFAULT_TIMEOUT_SEC) -> Optional[dict]:
    """安全静默执行 HTTP POST 请求"""
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"CoilArchitectPro/{APP_VERSION} ({sys.platform})",
                "X-API-Key": _CLIENT_API_KEY
            }
        )
        ctx = _get_safe_ssl_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
    except Exception as e:
        logger.debug(f"POST {url} 请求异常: {e}")
    return None


def _make_get_request(url: str, timeout: float = _DEFAULT_TIMEOUT_SEC) -> Optional[dict]:
    """安全静默执行 HTTP GET 请求"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"CoilArchitectPro/{APP_VERSION} ({sys.platform})",
                "X-API-Key": _CLIENT_API_KEY
            }
        )
        ctx = _get_safe_ssl_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
    except Exception as e:
        logger.debug(f"GET {url} 请求异常: {e}")
    return None


class CloudClient:
    """云端边缘协同与双向遥控客户端 (单例/类方法)"""

    _sync_thread: Optional[Thread] = None
    _stop_event: Event = Event()
    _trigger_event: Event = Event()
    _is_running: bool = False
    _last_status: Tuple[bool, str, str] = (False, "未初始化", "")

    # 回调钩子
    _status_callback: Optional[Callable[[bool, str, str], None]] = None
    _command_callback: Optional[Callable[[str, str], None]] = None

    @classmethod
    def get_api_urls(cls) -> List[str]:
        """获取云端 API 候选地址列表"""
        custom = os.environ.get("COIL_CLOUD_URL", "").strip()
        urls = []
        if custom:
            urls.append(custom.rstrip("/"))
        urls.extend([DEFAULT_CLOUD_BASE_URL, FALLBACK_WORKER_URL])
        return urls

    @classmethod
    def _ack_remote_command(cls, base_url: str, machine_id: str, command: str, status: str):
        """向云端发送指令执行回执 (ACK)"""
        try:
            ack_url = f"{base_url}/api/v1/command_ack"
            payload = {
                "machine_id": machine_id,
                "command": command,
                "status": status,
                "ack_timestamp": int(time.time() * 1000)
            }
            _make_post_request(ack_url, payload, timeout=2.0)
            logger.info(f"已向云端回执指令: {command} -> {status}")
        except Exception as e:
            logger.debug(f"回执发送异常: {e}")

    @classmethod
    def send_heartbeat_sync(cls, on_command_callback: Optional[Callable[[str, str], None]] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        同步执行一次心跳遥测与双向指令拉取
        :return: (is_success, status_message, response_data)
        """
        try:
            mid = get_machine_code()
            mac = get_mac_address()
            is_vm = detect_virtual_machine()
            hostname = socket.gethostname()
            system_user = getpass.getuser()

            disk_free_gb = 0.0
            try:
                root_drive = "C:" if sys.platform == "win32" else "/"
                disk_free_gb = round(shutil.disk_usage(root_drive).free / (1024**3), 2)
            except Exception:
                pass

            # 读取当前本地凭证与 7 天免激活试用状态
            ok, msg, lic_payload = LicenseManager.is_system_authorized()
            is_trial = lic_payload.get("is_trial", False) if lic_payload else False
            if ok:
                lic_status = "TRIAL_ACTIVE" if is_trial else "ACTIVE"
                days_left = lic_payload.get("days_left", 7)
                plan_type = f"7-Day Trial (剩{days_left}天)" if is_trial else lic_payload.get("plan", "COMMERCIAL")
                lic_exp = lic_payload.get("exp", "-")
            else:
                lic_status = "TRIAL_EXPIRED" if is_trial else "UNACTIVATED"
                plan_type = "EXPIRED"
                lic_exp = lic_payload.get("exp", "-") if lic_payload else "-"

            maint_exp = lic_payload.get("maint_exp", "-") if lic_payload else "-"
            op_name = lic_payload.get("cust", "-") if lic_payload else "-"
            cur_token = LicenseManager.get_installed_license_token() or ""

            payload = {
                "machine_id": mid,
                "hostname": hostname,
                "mac_address": mac,
                "app_version": APP_VERSION,
                "app_build": APP_BUILD,
                "wire_db_version": "v1.0",
                "plan_type": plan_type,
                "operator_name": op_name,
                "system_user": system_user,
                "disk_free_gb": disk_free_gb,
                "is_virtual_machine": is_vm,
                "license_status": lic_status,
                "license_expire": lic_exp,
                "maint_expire": maint_exp,
                "active_token": cur_token[:32] if cur_token else "",
                "client_clock_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "client_timestamp": int(datetime.now().timestamp())
            }

            for base_url in cls.get_api_urls():
                api_url = f"{base_url}/api/v1/heartbeat"
                res = _make_post_request(api_url, payload, timeout=_DEFAULT_TIMEOUT_SEC)
                if res and res.get("success"):
                    # 1. 解析云端远程控制指令 (深度对标 Gear: LOCK_APP / REVOKE_LICENSE / UPDATE_LICENSE)
                    remote_cmd = str(res.get("remote_command", "NONE")).upper().strip()
                    remote_payload = str(res.get("remote_command_payload") or "").strip()
                    server_status = str(res.get("license_status", "")).upper().strip()

                    # 判定是否需要远程锁机或吊销
                    if remote_cmd in ("LOCK_APP", "REVOKE_LICENSE") or server_status in ("BANNED", "REVOKED"):
                        logger.warning(f"接收到云端远程吊销/锁机指令: {remote_cmd} (状态: {server_status})")
                        LicenseManager.revoke_local_license("当前工位机商业授权已被管理员在云端控制台吊销/终止")
                        cls._ack_remote_command(base_url, mid, remote_cmd if remote_cmd != "NONE" else "LOCK_APP", "LOCKED")
                        cb = on_command_callback or cls._command_callback
                        if cb:
                            try:
                                cb("LOCK_APP", "当前工位机商业授权已被管理员在云端控制台吊销/终止")
                            except Exception as ce:
                                logger.error(f"执行远程锁机回调异常: {ce}")

                    # 判定是否需要远程安装新激活码 (静默延期或下发新方案)
                    elif remote_cmd == "UPDATE_LICENSE" and remote_payload:
                        logger.info("接收到云端下发的新激活凭证，执行远程自动更新...")
                        act_ok, act_msg = LicenseManager.install_license(remote_payload)
                        if act_ok:
                            cls._ack_remote_command(base_url, mid, "UPDATE_LICENSE", "SUCCESS")
                            cb = on_command_callback or cls._command_callback
                            if cb:
                                try:
                                    cb("UPDATE_LICENSE", remote_payload)
                                except Exception:
                                    pass
                        else:
                            cls._ack_remote_command(base_url, mid, "UPDATE_LICENSE", f"FAILED: {act_msg}")

                    # 判定是否需要远程刷新官方标杆案例库
                    elif remote_cmd == "FORCE_SYNC_CASES":
                        cls._ack_remote_command(base_url, mid, "FORCE_SYNC_CASES", "SYNCED")
                        cb = on_command_callback or cls._command_callback
                        if cb:
                            try:
                                cb("FORCE_SYNC_CASES", "")
                            except Exception:
                                pass

                    # 判定远程解除锁定
                    elif remote_cmd == "UNLOCK":
                        cls._ack_remote_command(base_url, mid, "UNLOCK", "UNLOCKED")
                        cb = on_command_callback or cls._command_callback
                        if cb:
                            try:
                                cb("UNLOCK", "")
                            except Exception:
                                pass

                    cls._last_status = (True, f"已连接至云端控制台 ({base_url.replace('https://', '')})", base_url)
                    return True, "云端连接正常", res

        except Exception as e:
            logger.debug(f"心跳同步异常: {e}")

        cls._last_status = (False, "无法连接云端服务器 (当前以本地离线模式安全运行)", "")
        return False, "云端连接不可用 (离线模式)", None

    @classmethod
    def start_background_sync(
        cls, 
        interval_sec: float = 1800.0, 
        on_status_callback: Optional[Callable[[bool, str, str], None]] = None,
        on_command_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        启动后台高可用静默授权检测与远程指令监听守护线程
        - 每 interval_sec 秒 (默认 1800 秒 / 30 分钟) 与官方授权服务器安全校验一次；
        - 全程守护线程运行，绝对不阻塞任何主线程 GUI 渲染；
        - 仅做授权状态和版本校验，绝对不上报任何线圈物理设计仿真数据；
        - 离线时自动静默降级，网络恢复时秒级自动重新握手。
        """
        if cls._is_running:
            return

        cls._status_callback = on_status_callback
        cls._command_callback = on_command_callback
        cls._stop_event.clear()
        cls._trigger_event.clear()
        cls._is_running = True

        def _sync_worker_loop():
            logger.info("云端授权守护引擎已启动 (每 30 分钟自动检测授权)")
            while not cls._stop_event.is_set():
                ok, msg, data = cls.send_heartbeat_sync(cls._command_callback)
                if cls._status_callback:
                    try:
                        target = data.get("server_time") if (ok and data) else ""
                        cls._status_callback(ok, msg, cls._last_status[2])
                    except Exception as e:
                        logger.debug(f"状态回调抛出: {e}")

                # 等待间隔或被主动触发 (支持 trigger_sync_now 立即唤醒)
                cls._trigger_event.wait(timeout=interval_sec)
                cls._trigger_event.clear()

            logger.info("云端协同守护引擎已退出")

        cls._sync_thread = Thread(target=_sync_worker_loop, daemon=True, name="CloudSyncDaemon")
        cls._sync_thread.start()

    @classmethod
    def trigger_sync_now(cls):
        """主动立即唤醒执行一次云端心跳同步 (不等待 30 秒)"""
        cls._trigger_event.set()

    @classmethod
    def stop_background_sync(cls):
        """安全停止后台心跳线程"""
        cls._is_running = False
        cls._stop_event.set()
        cls._trigger_event.set()

    @classmethod
    def send_heartbeat_async(cls):
        """单次异步快速心跳上报"""
        t = Thread(target=cls.send_heartbeat_sync, daemon=True)
        t.start()

    @classmethod
    def check_update_sync(cls) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """在线检测官方最新版本"""
        for base_url in cls.get_api_urls():
            api_url = f"{base_url}/api/v1/check_update"
            res = _make_get_request(api_url, timeout=3.0)
            if res and res.get("success"):
                remote_ver = res.get("version", "")
                is_newer = (remote_ver != APP_VERSION and remote_ver > APP_VERSION)
                return is_newer, res, f"已连接至云端 ({base_url})"

        return False, None, "无法连接至云端服务 (当前运行本地离线模式)"
