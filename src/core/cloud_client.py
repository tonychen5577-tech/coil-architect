"""
Coil-Architect Pro - Cloudflare Edge Client
用于与 Cloudflare Serverless 边缘服务进行静默心跳通信、防倒拨时钟授时与在线 OTA 版本检测
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from threading import Thread
from typing import Dict, Any, Optional, Tuple

from src.version import APP_VERSION, APP_BUILD
from src.core.license_manager import get_machine_code, get_mac_address, detect_virtual_machine, LicenseManager

# 默认 Cloudflare 边缘服务器 API 基地址 (支持自定义域名与 workers.dev)
DEFAULT_CLOUD_BASE_URL = "https://coil.ansv.net"
FALLBACK_WORKER_URL = "https://coil-architect-cloud.ansv.workers.dev"

_CLIENT_API_KEY = "COIL-SEC-2026#Ansv_TonyTech_c82P"


def _make_post_request(url: str, payload: dict, timeout: float = 3.0) -> Optional[dict]:
    """安全静默执行 HTTP POST 请求"""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"CoilArchitectPro/{APP_VERSION} ({sys.platform})",
                "X-API-Key": _CLIENT_API_KEY
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
    except Exception:
        pass
    return None


def _make_get_request(url: str, timeout: float = 3.0) -> Optional[dict]:
    """安全静默执行 HTTP GET 请求"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"CoilArchitectPro/{APP_VERSION} ({sys.platform})",
                "X-API-Key": _CLIENT_API_KEY
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
    except Exception:
        pass
    return None


class CloudClient:
    """云端边缘协同客户端"""

    @classmethod
    def get_api_urls(cls) -> list:
        # 支持从本地环境覆盖
        custom = os.environ.get("COIL_CLOUD_URL", "").strip()
        urls = []
        if custom:
            urls.append(custom.rstrip("/"))
        urls.extend([DEFAULT_CLOUD_BASE_URL, FALLBACK_WORKER_URL])
        return urls

    @classmethod
    def send_heartbeat_sync(cls) -> Optional[Dict[str, Any]]:
        """同步执行一次心跳上报"""
        try:
            mid = get_machine_code()
            mac = get_mac_address()
            is_vm = detect_virtual_machine()
            import socket, getpass, shutil
            hostname = socket.gethostname()
            system_user = getpass.getuser()

            disk_free_gb = 0.0
            try:
                root_drive = "C:" if sys.platform == "win32" else "/"
                disk_free_gb = round(shutil.disk_usage(root_drive).free / (1024**3), 2)
            except Exception:
                pass

            # 读取当前本地凭证状态
            ok, msg, lic_payload = LicenseManager.is_system_authorized()
            lic_status = "ACTIVE" if ok else "TRIAL"
            lic_exp = lic_payload.get("exp", "-") if ok else "-"
            op_name = lic_payload.get("cust", "-") if ok else "-"

            payload = {
                "machine_id": mid,
                "hostname": hostname,
                "mac_address": mac,
                "app_version": APP_VERSION,
                "app_build": APP_BUILD,
                "wire_db_version": "v1.0",
                "operator_name": op_name,
                "system_user": system_user,
                "disk_free_gb": disk_free_gb,
                "is_virtual_machine": is_vm,
                "license_status": lic_status,
                "license_expire": lic_exp,
                "client_clock_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "client_timestamp": int(datetime.now().timestamp())
            }

            for base_url in cls.get_api_urls():
                api_url = f"{base_url}/api/v1/heartbeat"
                res = _make_post_request(api_url, payload, timeout=2.5)
                if res and res.get("success"):
                    return res
        except Exception:
            pass
        return None

    @classmethod
    def send_heartbeat_async(cls):
        """异步在守护线程中静默执行心跳上报，绝对不阻塞任何 GUI 界面"""
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
