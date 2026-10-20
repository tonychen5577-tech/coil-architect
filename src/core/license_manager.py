"""
Coil-Architect Pro - License Manager & Anti-Tamper Security Core
商业软件授权激活、硬件指纹提取、防倒拨时钟与反作弊看门狗
严格依照《商业软件授权激活、反作弊防白嫖与反编译防御全景实战指南》实现
"""

import os
import sys
import json
import hmac
import hashlib
import platform
import subprocess
import base64
from datetime import datetime, date
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

# Coil-Architect Pro 专属高强度私钥
_SECRET_KEY = b"COIL_ARCHITECT_PRO_ANSV_SECRET_AUTH_KEY_2026_@v1#INDUSTRIAL"

_CACHED_IS_VM = None
_CACHED_HW_CODE = None
_CACHED_AUTH_RESULT = None
_LAST_AUTH_CHECK_TS = 0.0


def _atomic_write_bytes(target: Path, data: bytes):
    """原子写入二进制文件，防止写盘中断产生 0 字节损坏"""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f".tmp_{os.getpid()}")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(target)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass


def _atomic_write_text(target: Path, text: str, encoding="utf-8"):
    """原子写入文本文件"""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f".tmp_{os.getpid()}")
    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(target)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass


def _run_cmd_clean(cmd: str) -> str:
    """以安全静默模式执行系统命令"""
    try:
        creationflags = 0x08000000 if sys.platform == "win32" else 0
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=creationflags
        )
        return res.stdout.strip()
    except Exception:
        return ""


def detect_virtual_machine() -> bool:
    """
    嗅探虚拟机与 Ghost 镜像特征 (VMware / VirtualBox / QEMU / Hyper-V 等)
    采用注册表优先 0ms 命中与单例缓存
    """
    global _CACHED_IS_VM
    if _CACHED_IS_VM is not None:
        return _CACHED_IS_VM

    if sys.platform != "win32":
        _CACHED_IS_VM = False
        return False

    vm_signatures = [
        "vmware", "virtualbox", "vbox", "qemu", "kvm", "virtual machine",
        "microsoft corporation", "hyper-v", "parallels", "xen"
    ]

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\BIOS") as k:
            m = str(winreg.QueryValueEx(k, "SystemManufacturer")[0]).lower()
            p = str(winreg.QueryValueEx(k, "SystemProductName")[0]).lower()
            b = str(winreg.QueryValueEx(k, "BIOSVendor")[0]).lower()
            combined = f"{m} {p} {b}"
            if any(sig in combined for sig in vm_signatures):
                _CACHED_IS_VM = True
                return True
            if len(combined.strip()) > 5:
                _CACHED_IS_VM = False
                return False
    except Exception:
        pass

    _CACHED_IS_VM = False
    return False


def get_app_data_dir() -> Path:
    """获取应用程序本地数据安全目录"""
    app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CoilArchitectPro"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data


def get_machine_code() -> str:
    """
    提取 Windows 主板 UUID + CPU ID + MachineGuid
    综合哈希格式化为 16 位机器码: COIL-XXXX-XXXX-XXXX-XXXX
    支持本地持久化 0ms 极速启动缓存
    """
    global _CACHED_HW_CODE
    if _CACHED_HW_CODE:
        return _CACHED_HW_CODE

    guid_str = ""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as k:
                guid_str = str(winreg.QueryValueEx(k, "MachineGuid")[0]).strip().upper()
        except Exception:
            pass

    cache_path = get_app_data_dir() / ".hw_cache.json"
    if cache_path.exists() and guid_str:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("guid") == guid_str and cached.get("code"):
                _CACHED_HW_CODE = cached["code"]
                return _CACHED_HW_CODE
        except Exception:
            pass

    uuid_str = ""
    cpu_str = ""
    if sys.platform == "win32":
        uuid_str = _run_cmd_clean('(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID')
        cpu_str = _run_cmd_clean('(Get-CimInstance -ClassName Win32_Processor).ProcessorId')

    raw = f"{uuid_str.upper()}:{cpu_str.upper()}:{guid_str}:{platform.node()}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    code = f"COIL-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

    try:
        _atomic_write_text(cache_path, json.dumps({"guid": guid_str, "code": code}))
    except Exception:
        pass

    _CACHED_HW_CODE = code
    return code


class TimeGuard:
    """本地单调递增时钟看门狗 (防倒拨系统时间白嫖)"""

    @staticmethod
    def check_and_update() -> Tuple[bool, str]:
        path = get_app_data_dir() / ".time_guard.enc"
        now_ts = datetime.now().timestamp()

        data = {"last_monotonic_ts": now_ts}
        if path.exists():
            try:
                enc = path.read_bytes()
                key = _SECRET_KEY
                dec = bytes([b ^ key[i % len(key)] for i, b in enumerate(enc)])
                data = json.loads(dec.decode("utf-8"))
                last_ts = data.get("last_monotonic_ts", 0.0)

                # 允许 90 秒的网络授时波动容差
                if now_ts < (last_ts - 90.0):
                    return False, f"检测到系统时钟异常倒拨 (历史时间: {datetime.fromtimestamp(last_ts).strftime('%Y-%m-%d %H:%M')})"
            except Exception:
                pass

        # 更新最大单调时间
        data["last_monotonic_ts"] = max(data.get("last_monotonic_ts", 0.0), now_ts)
        try:
            raw = json.dumps(data).encode("utf-8")
            enc = bytes([b ^ _SECRET_KEY[i % len(_SECRET_KEY)] for i, b in enumerate(raw)])
            _atomic_write_bytes(path, enc)
        except Exception:
            pass


        return True, ""


class LicenseManager:
    """商业授权管理器"""

    LICENSE_FILE = "license.lic"

    @classmethod
    def get_license_path(cls) -> Path:
        # 优先读取应用程序同级目录，其次读取 AppData
        local_lic = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / ".." / cls.LICENSE_FILE
        if local_lic.exists():
            return local_lic
        return get_app_data_dir() / cls.LICENSE_FILE

    @classmethod
    def generate_token(
        cls, 
        machine_code: str, 
        expire_date_str: str, 
        customer_name: str = "ANSV VIP Client",
        station_id: str = "WORKSTATION-01"
    ) -> str:
        """
        签发授权激活 Token (供作者专属注册机调用)
        Token 格式: COIL-SEC-<Base64XorPayload>.<HMAC16>
        """
        payload = {
            "mid": machine_code.strip().upper(),
            "exp": expire_date_str.strip(),
            "cust": customer_name.strip(),
            "stat": station_id.strip(),
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        raw_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        
        # 异或混淆
        key = _SECRET_KEY
        xored = bytes([b ^ key[i % len(key)] for i, b in enumerate(raw_json)])
        b64_payload = base64.urlsafe_b64encode(xored).decode("utf-8").rstrip("=")

        sig = hmac.new(_SECRET_KEY, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()
        return f"COIL-SEC-{b64_payload}.{sig}"

    @classmethod
    def verify_token(cls, token: str) -> Tuple[bool, str, Dict[str, Any]]:
        """验签 Token 完整性与机器码匹配"""
        token = token.strip()
        if not token.startswith("COIL-SEC-") or "." not in token:
            return False, "激活码格式不正确", {}

        body = token[9:]
        parts = body.split(".", 1)
        if len(parts) != 2:
            return False, "激活码结构损坏", {}

        b64_payload, sig = parts
        expected_sig = hmac.new(_SECRET_KEY, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()
        if not hmac.compare_digest(sig.upper(), expected_sig):
            return False, "数字签名无效或激活码已被篡改", {}

        try:
            # 补齐 Base64 padding
            padding = 4 - (len(b64_payload) % 4)
            if padding != 4:
                b64_payload += "=" * padding
            xored = base64.urlsafe_b64decode(b64_payload)
            key = _SECRET_KEY
            raw_json = bytes([b ^ key[i % len(key)] for i, b in enumerate(xored)])
            payload = json.loads(raw_json.decode("utf-8"))
        except Exception:
            return False, "凭证解密失败", {}

        # 校验机器码
        cur_mid = get_machine_code()
        target_mid = payload.get("mid", "")
        if target_mid != "*" and cur_mid != target_mid:
            return False, f"机器码不匹配 (该激活码绑定于: {target_mid})", payload

        # 校验到期日
        exp_str = payload.get("exp", "2099-12-31")
        if exp_str != "PERMANENT":
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                if date.today() > exp_date:
                    return False, f"授权已于 {exp_str} 到期，请联系管理员续期", payload
            except Exception:
                return False, "到期时间格式解析错误", payload

        return True, "授权有效", payload

    @classmethod
    def is_system_authorized(cls) -> Tuple[bool, str, Dict[str, Any]]:
        """
        核心业务暗桩：毫秒级静默验签
        具备 5 秒内存缓存，避免频繁读盘损耗计算性能
        """
        global _CACHED_AUTH_RESULT, _LAST_AUTH_CHECK_TS
        now_ts = datetime.now().timestamp()
        if _CACHED_AUTH_RESULT is not None and (now_ts - _LAST_AUTH_CHECK_TS) < 5.0:
            return _CACHED_AUTH_RESULT

        # 1. 单调递增时钟看门狗校验
        clock_ok, clock_err = TimeGuard.check_and_update()
        if not clock_ok:
            _CACHED_AUTH_RESULT = (False, clock_err, {})
            _LAST_AUTH_CHECK_TS = now_ts
            return _CACHED_AUTH_RESULT

        # 2. 检查本地凭证文件
        lic_path = cls.get_license_path()
        if not lic_path.exists():
            _CACHED_AUTH_RESULT = (False, "未检测到授权文件，请先激活软件", {})
            _LAST_AUTH_CHECK_TS = now_ts
            return _CACHED_AUTH_RESULT

        try:
            token = lic_path.read_text(encoding="utf-8").strip()
            res = cls.verify_token(token)
            _CACHED_AUTH_RESULT = res
            _LAST_AUTH_CHECK_TS = now_ts
            return res
        except Exception as e:
            _CACHED_AUTH_RESULT = (False, f"授权文件读取异常: {str(e)}", {})
            _LAST_AUTH_CHECK_TS = now_ts
            return _CACHED_AUTH_RESULT

    @classmethod
    def install_license(cls, token: str) -> Tuple[bool, str]:
        """安装并持久化新凭证"""
        ok, msg, _ = cls.verify_token(token)
        if not ok:
            return False, msg
        try:
            p = get_app_data_dir() / cls.LICENSE_FILE
            _atomic_write_text(p, token.strip())
            # 刷新内存缓存
            global _CACHED_AUTH_RESULT
            _CACHED_AUTH_RESULT = None
            return True, "授权成功激活！"

        except Exception as e:
            return False, f"写入凭证失败: {str(e)}"
