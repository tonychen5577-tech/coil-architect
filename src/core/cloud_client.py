"""
=============================================================================
Module: src.core.cloud_client
Description: Coil-Architect Pro - Cloudflare Serverless Edge Client & Remote Control Engine
架构规范：深度对标 Gear-NVH / FFT 分析软件 全量工业商业桌面软件企业内网网络与数据库连接标准
功能：
1. 智能 DNS 韧性解析与 Anycast 兜底 (内置 SmartDNS，100% 免疫内网 DNS 阻断)；
2. 兼容企业自签证书与安全网关 SSL 检查 (_get_safe_ssl_context)；
3. 多模式网络代理策略 (自动检测系统代理 / 纯内网直连 / 手动指定内网代理)；
4. cloud_config.json 本地持久化与多候选容灾节点平滑调度；
5. 实时双向心跳与工位机状态遥测 (每30分钟静默同步，离线/超时绝对零卡顿)；
6. 毫秒级网络与数据库连通性诊断 (test_connection / diagnose_full)；
7. 云端远程遥控指令双向通道 (LOCK_APP / REVOKE_LICENSE / UPDATE_LICENSE)；
8. 在线版本检测与最小流量增量补丁升级分发。
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
from pathlib import Path
from threading import Thread, Event
from typing import Dict, Any, Optional, Tuple, Callable, List

# 导入智能 DNS 韧性解析器 (企业内网防 11001 域名解析阻断)
import src.core.smart_dns
from src.version import APP_VERSION, APP_BUILD
from src.core.license_manager import (
    get_machine_code, get_mac_address, detect_virtual_machine, 
    LicenseManager
)
from src.utils.logger import get_logger

logger = get_logger("CloudClient")

# 默认 Cloudflare 边缘服务器 API 基地址 (主域名 + 备用 workers.dev)
DEFAULT_CLOUD_BASE_URL = "https://coil.ansv.net"
FALLBACK_SERVER_URLS = [
    "https://coil.ansv.net",
    "https://coil-architect-cloud.tonychen5577.workers.dev",
    "https://gear.ansv.net"
]

_CLIENT_API_KEY = "COIL-SEC-2026#Ansv_TonyTech_c82P"
_DEFAULT_TIMEOUT_SEC = 15.0
_DEFAULT_UA = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 CoilArchitectPro/{APP_VERSION}"

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CoilArchitectPro"
CONFIG_FILE = CONFIG_DIR / "cloud_config.json"

_CACHED_CLIENT_IP = None


def get_client_ip() -> str:
    """尝试获取本机内网 IP 地址 (内存缓存，对标 Gear 标准)"""
    global _CACHED_CLIENT_IP
    if _CACHED_CLIENT_IP is not None:
        return _CACHED_CLIENT_IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        _CACHED_CLIENT_IP = ip
        return ip
    except Exception:
        _CACHED_CLIENT_IP = "127.0.0.1"
        return "127.0.0.1"


def _get_safe_ssl_context() -> ssl.SSLContext:
    """获取安全的 SSL 上下文 (在企业内网自签证书/杀毒软件劫持时保持通信顺畅)"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return ssl._create_unverified_context()


def load_cloud_config() -> Dict[str, Any]:
    """优先从运行目录读取配置，其次读取 AppData，默认用官方云端"""
    target_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(".")
    candidates = [
        target_dir / "cloud_config.json",
        CONFIG_FILE,
    ]

    for p in candidates:
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if not data.get("server_url"):
                            data["server_url"] = DEFAULT_CLOUD_BASE_URL
                        if not data.get("fallback_urls"):
                            data["fallback_urls"] = list(FALLBACK_SERVER_URLS)
                        if not data.get("proxy_setting"):
                            data["proxy_setting"] = "auto"
                        return data
        except Exception:
            pass

    return {
        "server_url": DEFAULT_CLOUD_BASE_URL,
        "fallback_urls": list(FALLBACK_SERVER_URLS),
        "proxy_setting": "auto",
        "custom_proxy": "",
        "customer_name": "内部研发机构",
        "line_station": "专业研发工作站 (Pro Station)"
    }


def save_cloud_config(cfg: Dict[str, Any]):
    """持久化网络与数据库通信配置"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存网络配置文件失败: {e}")


def get_opener(proxy_setting: Optional[str] = None, custom_proxy: Optional[str] = None):
    """构建带安全兼容 SSL 及网络代理支持的 urllib Opener"""
    cfg = load_cloud_config()
    ps = proxy_setting if proxy_setting is not None else cfg.get("proxy_setting", "auto")
    cp = custom_proxy if custom_proxy is not None else cfg.get("custom_proxy", "")

    handlers = []
    if ps == "direct":
        # 强制直连，忽略系统代理 (内网/局域网互通)
        handlers.append(urllib.request.ProxyHandler({}))
    elif ps == "custom" and cp:
        # 指定企业内网代理
        handlers.append(urllib.request.ProxyHandler({"http": cp, "https": cp}))
    else:
        # 自动读取系统系统代理
        handlers.append(urllib.request.ProxyHandler())

    ssl_ctx = _get_safe_ssl_context()
    handlers.append(urllib.request.HTTPSHandler(context=ssl_ctx))
    return urllib.request.build_opener(*handlers)


def _make_post_request(url: str, payload: dict, timeout: float = _DEFAULT_TIMEOUT_SEC) -> Optional[dict]:
    """安全静默执行 HTTP POST 请求 (全兼容代理与 SSL)"""
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": _DEFAULT_UA,
                "X-API-Key": _CLIENT_API_KEY
            }
        )
        opener = get_opener()
        with opener.open(req, timeout=timeout) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
    except Exception as e:
        logger.debug(f"POST {url} 请求异常: {e}")
    return None


def _make_get_request(url: str, timeout: float = _DEFAULT_TIMEOUT_SEC) -> Optional[dict]:
    """安全静默执行 HTTP GET 请求 (全兼容代理与 SSL)"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _DEFAULT_UA,
                "X-API-Key": _CLIENT_API_KEY
            }
        )
        opener = get_opener()
        with opener.open(req, timeout=timeout) as resp:
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
    def get_server_url(cls) -> str:
        """获取当前配置的主数据库服务地址"""
        cfg = load_cloud_config()
        return (cfg.get("server_url") or DEFAULT_CLOUD_BASE_URL).rstrip("/")

    @classmethod
    def get_api_urls(cls) -> List[str]:
        """获取云端 API 候选地址列表 (主节点 + 容灾镜像)"""
        cfg = load_cloud_config()
        urls = []
        custom = os.environ.get("COIL_CLOUD_URL", "").strip()
        if custom:
            urls.append(custom.rstrip("/"))
        main_url = cfg.get("server_url", DEFAULT_CLOUD_BASE_URL).rstrip("/")
        if main_url not in urls:
            urls.append(main_url)
        fallbacks = cfg.get("fallback_urls") or list(FALLBACK_SERVER_URLS)
        for fb in fallbacks:
            fb_clean = fb.rstrip("/")
            if fb_clean not in urls:
                urls.append(fb_clean)
        return urls

    @classmethod
    def test_connection(
        cls,
        test_url: Optional[str] = None,
        proxy_setting: Optional[str] = None,
        custom_proxy: Optional[str] = None,
        retry: int = 1
    ) -> Tuple[bool, str]:
        """测试与数据库服务节点的连通性 (内置超时自动重试与平滑容灾调度，对标 Gear 标准)"""
        target_base = (test_url or cls.get_server_url()).rstrip("/")
        # 探针列表：包含 D1 专家案例库、版本更新与健康探针，确保企业内网 100% 连通响应
        probe_endpoints = [
            "/api/v1/cases/benchmarks",
            "/api/v1/check_update",
            "/api/v1/health"
        ]

        try:
            opener = get_opener(proxy_setting, custom_proxy)
            last_err = None
            for p in probe_endpoints:
                url = f"{target_base}{p}"
                try:
                    req = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": _DEFAULT_UA,
                            "X-API-Key": _CLIENT_API_KEY
                        }
                    )
                    with opener.open(req, timeout=_DEFAULT_TIMEOUT_SEC) as resp:
                        if resp.status == 200:
                            raw = resp.read().decode("utf-8", errors="replace")
                            try:
                                data = json.loads(raw)
                                raw_msg = str(data.get("message", "专家数据库运行正常"))
                            except Exception:
                                raw_msg = "专家数据库运行正常"
                            clean_msg = (
                                raw_msg.replace("Cloudflare 边缘专家库与审计服务正常运行中", "专家知识库与协同审计服务正常运行中")
                                       .replace("Cloudflare", "云端")
                                       .replace("cloudflare", "云端")
                                       .replace("cloudfare", "云端")
                                       .replace("企业", "")
                            )
                            if "正常" in clean_msg or "成功" in clean_msg or "cases" in raw or "version" in raw:
                                clean_msg = "专家知识库与协同审计服务正常运行中"
                            return True, f"数据库在线: {clean_msg}"
                        return False, f"HTTP 状态码: {resp.status}"
                except urllib.error.HTTPError as e:
                    if e.code == 401:
                        return False, "401 鉴权拒绝 (API-Key 不匹配或未授权)"
                    if e.code == 404:
                        last_err = e
                        continue
                    last_err = e
                except (urllib.error.URLError, TimeoutError, OSError) as e:
                    last_err = e
                    if ("timed out" in str(e).lower() or "超时" in str(e)) and retry > 0:
                        time.sleep(0.3)
                        return cls.test_connection(test_url=test_url, proxy_setting=proxy_setting, custom_proxy=custom_proxy, retry=retry - 1)
                    continue
                except Exception as e:
                    last_err = e
                    continue

            # 若主节点未通且无指定 test_url，平滑尝试备用容灾节点调度策略
            if not test_url:
                for alt_url in cls.get_api_urls():
                    if alt_url.rstrip("/") != target_base:
                        try:
                            ok_alt, msg_alt = cls.test_connection(test_url=alt_url, proxy_setting=proxy_setting, custom_proxy=custom_proxy, retry=0)
                            if ok_alt:
                                logger.info(f"主节点不可达，已自动切换备用容灾节点: {alt_url}")
                                cfg = load_cloud_config()
                                cfg["server_url"] = alt_url
                                save_cloud_config(cfg)
                                return True, "主节点不可达，已自动切换备用高可用安全镜像节点"
                        except Exception:
                            pass

            if last_err:
                raise last_err
            return False, "未能获取到数据库有效响应"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "401 鉴权拒绝 (API-Key 不匹配或未授权)"
            return False, f"云端服务拒绝 (HTTP {e.code}): {e.reason}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason_str = str(getattr(e, "reason", e))
            if ("timed out" in reason_str.lower() or "超时" in reason_str) and retry > 0:
                time.sleep(0.3)
                return cls.test_connection(test_url=test_url, proxy_setting=proxy_setting, custom_proxy=custom_proxy, retry=retry - 1)

            if "10061" in reason_str or "actively refused" in reason_str or "积极拒绝" in reason_str:
                return False, f"连接被拒绝: 目标端口未开放或后端未启动 ({reason_str})"
            if "10060" in reason_str or "timed out" in reason_str.lower() or "超时" in reason_str:
                return False, f"连接超时: 网络延迟波动或防火墙阻断 ({reason_str})"
            return False, f"网络连接失败 ({reason_str})"
        except Exception as e:
            err_str = str(e)
            if ("timed out" in err_str.lower() or "超时" in err_str) and retry > 0:
                time.sleep(0.3)
                return cls.test_connection(test_url=test_url, proxy_setting=proxy_setting, custom_proxy=custom_proxy, retry=retry - 1)
            return False, f"连接异常: {e}"

    @classmethod
    def auto_detect_best_network_mode(
        cls,
        test_url: Optional[str] = None
    ) -> Tuple[str, bool, str, List[Dict[str, Any]]]:
        """
        自动顺序验证网络连接模式，智能测速并获取最佳连接方式 (对标 Gear 工业级规范，不允许个人擅自修改)
        顺序验证队列：
          1. 自动检测系统代理 (auto) - 优先读取 Windows 操作系统网络与 PAC 设置
          2. 企业内网原生直连 (direct) - 绕过本地所有代理，直连企业专线或云端
          3. 专用本地代理 (custom) - 若配置文件中指定了代理地址，则测试该代理
        
        返回:
          (best_mode, is_connected, summary_message, probe_details)
        """
        cfg = load_cloud_config()
        target_base = (test_url or cls.get_server_url() or DEFAULT_CLOUD_BASE_URL).rstrip("/")
        custom_proxy = cfg.get("custom_proxy", "").strip()

        candidates = [
            ("auto", "自动检测系统代理 (auto)"),
            ("direct", "企业原生直连 (direct)")
        ]
        if custom_proxy:
            candidates.append(("custom", f"专用本地代理 ({custom_proxy})"))

        probe_details = []
        successful_modes = []

        for mode_key, mode_name in candidates:
            t0 = time.time()
            try:
                ok, msg = cls.test_connection(
                    test_url=target_base,
                    proxy_setting=mode_key,
                    custom_proxy=custom_proxy if mode_key == "custom" else "",
                    retry=0
                )
                latency_ms = max(1, int((time.time() - t0) * 1000))
                item = {
                    "mode": mode_key,
                    "name": mode_name,
                    "ok": ok,
                    "latency": latency_ms,
                    "msg": msg
                }
                probe_details.append(item)
                if ok:
                    successful_modes.append(item)
            except Exception as e:
                latency_ms = max(1, int((time.time() - t0) * 1000))
                probe_details.append({
                    "mode": mode_key,
                    "name": mode_name,
                    "ok": False,
                    "latency": latency_ms,
                    "msg": str(e)
                })

        if successful_modes:
            # 排序优选：优先可用，测速延迟最低者胜出；若延迟差距在 40ms 以内，优先保持当前配置模式稳定性
            current_mode = cfg.get("proxy_setting", "auto")
            current_match = [m for m in successful_modes if m["mode"] == current_mode]
            min_latency_item = min(successful_modes, key=lambda x: x["latency"])

            if current_match and (current_match[0]["latency"] <= min_latency_item["latency"] + 40):
                best_item = current_match[0]
            else:
                best_item = min_latency_item

            best_mode = best_item["mode"]
            best_name = best_item["name"]
            best_latency = best_item["latency"]

            # 静默持久化生效
            if cfg.get("proxy_setting") != best_mode:
                cfg["proxy_setting"] = best_mode
                save_cloud_config(cfg)
                logger.info(f"[NetworkMode] 自动顺序验证完成，已锁定最佳连接模式: {best_mode} (延迟: {best_latency}ms)")

            return best_mode, True, f"已锁定最佳连接模式 [{best_name}] (响应延迟: {best_latency}ms)", probe_details
        else:
            current_mode = cfg.get("proxy_setting", "auto")
            return current_mode, False, "所有网络模式顺序验证均未连通，请检查物理网线或联系技术管理员", probe_details

    @classmethod
    def diagnose_full(
        cls,
        test_url: Optional[str] = None,
        proxy_setting: Optional[str] = None,
        custom_proxy: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """执行全方位内网穿透与数据库通信诊断 (对标 Gear 诊断标准)"""
        cfg = load_cloud_config()
        target_base = (test_url or cfg.get("server_url") or DEFAULT_CLOUD_BASE_URL).rstrip("/")
        ps = proxy_setting if proxy_setting is not None else cfg.get("proxy_setting", "auto")
        cp = custom_proxy if custom_proxy is not None else cfg.get("custom_proxy", "")

        logs = []
        logs.append(f"[*] 开始网络连通性与内网穿透体检: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logs.append(f"• 目标数据链路:   {target_base}")
        logs.append(f"• 路由代理策略:   {ps} {('(' + cp + ')') if cp else ''}")
        logs.append(f"• 本机工位机器码: {get_machine_code()}")
        logs.append(f"• 本机网卡 MAC:   {get_mac_address()}")
        logs.append(f"• 本机内网 IP:    {get_client_ip()}")
        logs.append("-" * 65)

        # 1. 域名解析
        parsed = urllib.parse.urlparse(target_base)
        host = parsed.hostname or "coil.ansv.net"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        logs.append(f"[步骤 1/4] DNS 域名解析测试: {host}")
        ip_list = []
        try:
            addrs = socket.getaddrinfo(host, port)
            ip_list = list(set([a[-1][0] for a in addrs if a[-1]]))
            logs.append(f"  ✓ 域名解析成功 (SmartDNS 韧性穿透): {', '.join(ip_list)}")
        except Exception as e:
            logs.append(f"  ❌ 域名解析失败: {e}")
            return False, logs

        # 2. TCP 端口探测
        logs.append(f"[步骤 2/4] TCP 端口连通性探测: {host}:{port}")
        try:
            target_ip = ip_list[0]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.5)
            s.connect((target_ip, port))
            s.close()
            logs.append(f"  ✓ TCP 握手成功 (已连通 {target_ip}:{port})")
        except Exception as e:
            logs.append(f"  ❌ TCP 端口连接被拒绝或超时: {e}")
            return False, logs

        # 3. SSL 握手与证书通道
        if parsed.scheme == "https":
            logs.append(f"[步骤 3/4] SSL/TLS 安全通道握手测试")
            try:
                ctx = _get_safe_ssl_context()
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3.5)
                wrapped = ctx.wrap_socket(s, server_hostname=host)
                wrapped.connect((target_ip, port))
                wrapped.close()
                logs.append("  ✓ SSL 安全传输加密通道建立成功 (企业内网安全证书兼容模式生效)")
            except Exception as e:
                logs.append(f"  ❌ SSL 握手异常: {e}")
                return False, logs
        else:
            logs.append("[步骤 3/4] 局域网 HTTP 协议 (跳过 SSL 检查)")

        # 4. API 业务接口与鉴权检查
        logs.append(f"[步骤 4/4] 数据库健康状态与 API-Key 校验")
        ok, test_msg = cls.test_connection(test_url=target_base, proxy_setting=ps, custom_proxy=cp)
        if ok:
            logs.append(f"  ✓ 数据库接口响应正常: {test_msg}")
            logs.append("-" * 65)
            logs.append("🎉 [结论: 数据库连通正常] 该工位机可正常进行数据同步、授权通信与标杆案例下载！")
            return True, logs
        else:
            logs.append(f"  ❌ 数据库连接异常: {test_msg}")
            logs.append("-" * 65)
            logs.append("⚠️ [结论: 数据库未连通] 建议切换网络代理为『直连模式』或联系网络管理员导入专属配置文件。")
            return False, logs

    @classmethod
    def import_config_from_file(cls, file_path: str) -> Tuple[bool, str]:
        """导入作者或管理员分发的标准网络配置文件 (.json / .cfg / .txt)"""
        try:
            p = Path(file_path)
            if not p.exists():
                return False, f"未找到文件: {file_path}"
            raw = p.read_text(encoding="utf-8").strip()
            data = json.loads(raw)
            if not isinstance(data, dict):
                return False, "配置文件格式不正确 (必须为 JSON)"

            cfg = load_cloud_config()
            if "server_url" in data and data["server_url"]:
                cfg["server_url"] = str(data["server_url"]).strip().rstrip("/")
            if "fallback_urls" in data and isinstance(data["fallback_urls"], list):
                cfg["fallback_urls"] = [str(u).strip().rstrip("/") for u in data["fallback_urls"] if u]
            if "proxy_setting" in data:
                cfg["proxy_setting"] = str(data["proxy_setting"]).strip()
            if "custom_proxy" in data:
                cfg["custom_proxy"] = str(data["custom_proxy"]).strip()

            save_cloud_config(cfg)
            return True, f"网络参数已导入并生效！目标链路: {cfg.get('server_url')}"
        except Exception as e:
            return False, f"导入配置发生异常: {e}"

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
                    remote_cmd = str(res.get("remote_command", "NONE")).upper().strip()
                    remote_payload = str(res.get("remote_command_payload") or "").strip()
                    server_status = str(res.get("license_status", "")).upper().strip()

                    # 处理远程遥控指令
                    if remote_cmd in ["LOCK_APP", "REVOKE_LICENSE"]:
                        logger.warning(f"接收到云端强制吊销与锁机指令: {remote_cmd}")
                        LicenseManager.revoke_local_license(reason="当前工位机授权已被管理员在云端吊销或锁定")
                        cls._ack_remote_command(base_url, mid, remote_cmd, "EXECUTED")
                        if on_command_callback:
                            on_command_callback(remote_cmd, remote_payload)
                    elif remote_cmd == "UPDATE_LICENSE" and remote_payload:
                        logger.info("接收到云端推送的新授权凭证，自动安装...")
                        ok_inst, _ = LicenseManager.install_license(remote_payload)
                        cls._ack_remote_command(base_url, mid, remote_cmd, "SUCCESS" if ok_inst else "FAILED")
                        if ok_inst and on_command_callback:
                            try:
                                on_command_callback(remote_cmd, remote_payload)
                            except Exception as cb_err:
                                logger.error(f"回调 on_command_callback 异常: {cb_err}")


                    status_text = "授权服务器已连接"
                    cls._last_status = (True, status_text, base_url)
                    if cls._status_callback:
                        cls._status_callback(True, status_text, base_url)
                    return True, status_text, res

            err_msg = "数据库未连通 (运行本地离线模式)"
            cls._last_status = (False, err_msg, "")
            if cls._status_callback:
                cls._status_callback(False, err_msg, "")
            return False, err_msg, None

        except Exception as e:
            err_msg = f"心跳异常: {e}"
            cls._last_status = (False, err_msg, "")
            if cls._status_callback:
                cls._status_callback(False, err_msg, "")
            return False, err_msg, None

    @classmethod
    def start_heartbeat_daemon(
        cls, 
        interval_seconds: int = 1800,  # 30分钟一次
        status_callback: Optional[Callable[[bool, str, str], None]] = None,
        command_callback: Optional[Callable[[str, str], None]] = None
    ):
        """启动后台静默心跳守护线程 (对齐 Gear 规范)"""
        if cls._is_running:
            return

        cls._status_callback = status_callback
        cls._command_callback = command_callback
        cls._stop_event.clear()
        cls._trigger_event.clear()
        cls._is_running = True

        def _worker_loop():
            logger.info("云端授权与数据库协同守护引擎已启动 (智能自适应心跳检测)")
            # 启动时立即执行一次探测
            cls.send_heartbeat_sync(on_command_callback=cls._command_callback)

            while not cls._stop_event.is_set():
                # 智能动态自适应心跳轮询：
                # 1. 若当前未激活商业授权（试用或未授权），将心跳缩短至 15 秒，确保管理员在云端控制台点击【一键下发】后瞬时触达；
                # 2. 一旦检测到正式商业授权有效激活，自动拉长至常规周期 (默认1800秒/30分钟)，极度节约网络流量
                try:
                    auth_ok, _, lic_info = LicenseManager.is_system_authorized()
                    is_trial = lic_info.get("is_trial", False) if lic_info else True
                    is_commercial = auth_ok and not is_trial
                except Exception:
                    is_commercial = False

                current_timeout = interval_seconds if is_commercial else 15

                # 等待定时到期或主动触发信号
                triggered = cls._trigger_event.wait(timeout=current_timeout)
                if cls._stop_event.is_set():
                    break
                if triggered:
                    cls._trigger_event.clear()
                cls.send_heartbeat_sync(on_command_callback=cls._command_callback)

            logger.info("云端授权守护引擎已安全退出。")
            cls._is_running = False

        cls._sync_thread = Thread(target=_worker_loop, daemon=True, name="CloudClientHeartbeatDaemon")
        cls._sync_thread.start()

    @classmethod
    def stop_heartbeat_daemon(cls):
        """安全停止守护线程"""
        cls._stop_event.set()
        cls._trigger_event.set()
        cls._is_running = False

    @classmethod
    def request_online_activation(
        cls, 
        customer_name: str = "", 
        contact: str = ""
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        向云端发起在线一键激活请求 (免去繁琐的手动输入激活码流程)
        1. 收集本机硬件指纹；
        2. 向云端 /api/v1/online_activate 发送请求；
        3. 若云端已下发授权，自动安装凭证并触发状态刷新；
        4. 若尚未下发，登记工位机信息便于管理员后台一键授权。
        """
        mid = LicenseManager.get_machine_code()
        payload = {
            "machine_id": mid,
            "hostname": socket.gethostname(),
            "mac_address": get_mac_address(),
            "app_version": APP_VERSION,
            "app_build": APP_BUILD,
            "customer_name": customer_name or "-",
            "contact": contact or "-",
            "is_virtual_machine": detect_virtual_machine(),
            "timestamp": int(time.time()),
        }

        for base_url in cls.get_api_urls():
            api_url = f"{base_url}/api/v1/online_activate"
            res = _make_post_request(api_url, payload, timeout=_DEFAULT_TIMEOUT_SEC)
            if res:
                if res.get("success") and res.get("status") == "ACTIVATED":
                    token = res.get("token")
                    if token:
                        ok, msg = LicenseManager.install_license(token)
                        if ok:
                            cls.trigger_heartbeat_now()
                            return True, "🎉 在线授权激活成功！商业特权已全面解锁。", res
                        else:
                            return False, f"凭证安装失败: {msg}", res
                else:
                    msg = res.get("message") or "在线激活申请已提交，等待管理员审核授权。"
                    return False, msg, res

        return False, "未能连通云端授权服务器，请检查网络连接或防火墙设置。", {}

    @classmethod
    def trigger_heartbeat_now(cls):
        """立即唤醒守护线程执行一次同步"""
        cls._trigger_event.set()

    # 兼容历史与 Gear 命名规范别名
    @classmethod
    def start_background_sync(cls, interval_sec: float = 1800.0, on_status_callback=None, on_command_callback=None):
        return cls.start_heartbeat_daemon(interval_seconds=int(interval_sec), status_callback=on_status_callback, command_callback=on_command_callback)

    @classmethod
    def stop_background_sync(cls):
        return cls.stop_heartbeat_daemon()

    @classmethod
    def trigger_sync_now(cls):
        return cls.trigger_heartbeat_now()

    @classmethod
    def send_heartbeat_async(cls):
        """单次异步快速心跳上报"""
        t = Thread(target=cls.send_heartbeat_sync, daemon=True)
        t.start()

    @classmethod
    def check_update_sync(cls) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """在线检测官方最新版本 (全兼容代理与 SmartDNS)"""
        for base_url in cls.get_api_urls():
            api_url = f"{base_url}/api/v1/check_update"
            res = _make_get_request(api_url, timeout=3.5)
            if res and res.get("success"):
                remote_ver = res.get("version", "")
                is_newer = (remote_ver != APP_VERSION and remote_ver > APP_VERSION)
                return is_newer, res, f"已连接至云端 ({base_url})"

        return False, None, "无法连接至云端服务 (当前运行本地离线模式)"
