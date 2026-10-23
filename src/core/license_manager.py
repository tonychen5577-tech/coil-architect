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
import uuid
from datetime import datetime, date, timedelta
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


class TrialGuard:
    """
    7天全功能免激活试用看门狗 (首次运行自动享受，一机一码双重锚点防篡改)
    双重持久化防删除重置:
    1. 本地安全凭证: %LOCALAPPDATA%/CoilArchitectPro/.trial_anchor.enc (HMAC+XOR)
    2. Windows 注册表: HKCU\\Software\\ANSV\\CoilArchitect\\Security\\TrialAnchor
    若任一方被清理，会自动根据另一方自愈还原；若同时检测到时钟倒拨或历史时钟超期，则判定试用届满。
    """

    TRIAL_DAYS = 7
    REG_SUBKEY = r"Software\ANSV\CoilArchitect\Security"
    REG_VALUE_NAME = "TrialAnchor"

    @classmethod
    def _get_file_path(cls) -> Path:
        return get_app_data_dir() / ".trial_anchor.enc"

    @classmethod
    def _create_token(cls, mid: str, start_date_str: str, exp_date_str: str) -> str:
        """根据工位机硬件指纹与起止时间签发加密试用 Token"""
        data = {
            "mid": mid,
            "start": start_date_str,
            "exp": exp_date_str,
            "days": cls.TRIAL_DAYS,
            "created_ts": datetime.now().timestamp()
        }
        raw_json = json.dumps(data, separators=(',', ':')).encode("utf-8")
        key = _SECRET_KEY
        xored = bytes([b ^ key[i % len(key)] for i, b in enumerate(raw_json)])
        b64 = base64.urlsafe_b64encode(xored).decode("utf-8").rstrip("=")
        sig = hmac.new(key, f"{mid}|{start_date_str}|{exp_date_str}|{cls.TRIAL_DAYS}".encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()
        return f"{b64}.{sig}"

    @classmethod
    def _verify_token(cls, token_str: str, mid: str) -> Optional[Dict[str, Any]]:
        """解密并校验试用 Token 完整性"""
        if not token_str or "." not in token_str:
            return None
        parts = token_str.split(".", 1)
        if len(parts) != 2:
            return None
        b64, sig = parts
        try:
            padding = 4 - (len(b64) % 4)
            if padding != 4:
                b64 += "=" * padding
            xored = base64.urlsafe_b64decode(b64)
            key = _SECRET_KEY
            raw_json = bytes([b ^ key[i % len(key)] for i, b in enumerate(xored)])
            data = json.loads(raw_json.decode("utf-8"))
            if data.get("mid") != mid:
                return None
            expected_sig = hmac.new(key, f"{mid}|{data.get('start')}|{data.get('exp')}|{cls.TRIAL_DAYS}".encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()
            if not hmac.compare_digest(sig.upper(), expected_sig):
                return None
            return data
        except Exception:
            return None

    @classmethod
    def get_or_create_trial(cls) -> Tuple[bool, str, Dict[str, Any]]:
        """
        获取或首次自动生成 7 天全功能免激活试用凭证
        :return: (is_authorized, msg, payload)
        """
        mid = get_machine_code()
        token_from_file = ""
        token_from_reg = ""

        # 1. 读取本地加密文件
        fpath = cls._get_file_path()
        if fpath.exists():
            try:
                token_from_file = fpath.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        # 2. 读取 Windows 注册表
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_SUBKEY) as k:
                    val, _ = winreg.QueryValueEx(k, cls.REG_VALUE_NAME)
                    token_from_reg = str(val).strip()
            except Exception:
                pass

        data = None
        if token_from_file:
            data = cls._verify_token(token_from_file, mid)
        if not data and token_from_reg:
            data = cls._verify_token(token_from_reg, mid)

        # 3. 首次在当前机器运行：自动享受 7 天全功能免激活试用！
        if not data:
            start_d = date.today()
            exp_d = start_d + timedelta(days=cls.TRIAL_DAYS)
            start_str = start_d.strftime("%Y-%m-%d")
            exp_str = exp_d.strftime("%Y-%m-%d")

            new_token = cls._create_token(mid, start_str, exp_str)
            try:
                _atomic_write_text(fpath, new_token)
            except Exception:
                pass

            if sys.platform == "win32":
                try:
                    import winreg
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.REG_SUBKEY) as k:
                        winreg.SetValueEx(k, cls.REG_VALUE_NAME, 0, winreg.REG_SZ, new_token)
                except Exception:
                    pass

            data = {
                "mid": mid,
                "start": start_str,
                "exp": exp_str,
                "days": cls.TRIAL_DAYS
            }
        else:
            # 双向自愈同步
            valid_token = token_from_file if (token_from_file and cls._verify_token(token_from_file, mid)) else token_from_reg
            if valid_token:
                if not token_from_file or not cls._verify_token(token_from_file, mid):
                    try:
                        _atomic_write_text(fpath, valid_token)
                    except Exception:
                        pass
                if sys.platform == "win32" and (not token_from_reg or not cls._verify_token(token_from_reg, mid)):
                    try:
                        import winreg
                        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.REG_SUBKEY) as k:
                            winreg.SetValueEx(k, cls.REG_VALUE_NAME, 0, winreg.REG_SZ, valid_token)
                    except Exception:
                        pass

        # 4. 计算剩余天数与试用有效期
        exp_str = data.get("exp", "")
        start_str = data.get("start", "")
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            today = date.today()
            delta_days = (exp_date - today).days

            trial_payload = {
                "mid": mid,
                "cust": "全功能试用评估用户",
                "customer": "全功能试用评估用户",
                "owner": "全功能试用评估用户",
                "stat": f"7天全功能试用工位 (剩余 {max(0, delta_days)} 天)",
                "station": f"7天全功能试用工位 (剩余 {max(0, delta_days)} 天)",
                "type": f"7天全功能免激活试用 (剩 {max(0, delta_days)} 天)",
                "exp": exp_str,
                "exp_date": exp_str,
                "is_trial": True,
                "days_left": max(0, delta_days),
                "start_date": start_str,
                "total_days": cls.TRIAL_DAYS
            }

            if delta_days >= 0:
                return True, f"7天全功能免激活试用中 (剩余 {delta_days} 天，有效期至 {exp_str})", trial_payload
            else:
                return False, f"7天全功能免费试用已于 {exp_str} 到期，请激活正式商业授权", trial_payload
        except Exception as e:
            return False, f"试用周期解析异常: {e}", {}


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
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        token = token.strip()
        if not token.startswith("COIL-SEC-") or "." not in token:
            return False, ("Invalid activation token format" if is_en else "激活码格式不正确"), {}

        body = token[9:]
        parts = body.split(".", 1)
        if len(parts) != 2:
            return False, ("Corrupted activation token structure" if is_en else "激活码结构损坏"), {}

        b64_payload, sig = parts
        expected_sig = hmac.new(_SECRET_KEY, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()
        if not hmac.compare_digest(sig.upper(), expected_sig):
            return False, ("Invalid digital signature or tampered license token" if is_en else "数字签名无效或激活码已被篡改"), {}

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
            return False, ("License payload decryption failed" if is_en else "凭证解密失败"), {}

        # 校验机器码
        cur_mid = get_machine_code()
        target_mid = payload.get("mid", "")
        if target_mid != "*" and cur_mid != target_mid:
            return False, (f"Machine Code mismatch (bound to: {target_mid})" if is_en else f"机器码不匹配 (该激活码绑定于: {target_mid})"), payload

        # 校验到期日
        exp_str = payload.get("exp", "2099-12-31")
        if exp_str != "PERMANENT":
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                if date.today() > exp_date:
                    return False, (f"License expired on {exp_str}. Please contact support for renewal." if is_en else f"授权已于 {exp_str} 到期，请联系管理员续期"), payload
            except Exception:
                return False, ("Invalid expiration date format in license" if is_en else "到期时间格式解析错误"), payload

        return True, ("License Valid" if is_en else "授权有效"), payload

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

        # 2. 检查本地正式商业凭证文件 (若存在有效正式授权则优先享用)
        lic_path = cls.get_license_path()
        if lic_path.exists():
            try:
                token = lic_path.read_text(encoding="utf-8").strip()
                res = cls.verify_token(token)
                if res[0]:
                    payload = dict(res[2])
                    payload["is_trial"] = False
                    _CACHED_AUTH_RESULT = (True, res[1], payload)
                    _LAST_AUTH_CHECK_TS = now_ts
                    return _CACHED_AUTH_RESULT
            except Exception:
                pass

        # 3. 首次运行或未激活状态：自动享受 7 天全功能免激活试用！
        trial_ok, trial_msg, trial_payload = TrialGuard.get_or_create_trial()
        _CACHED_AUTH_RESULT = (trial_ok, trial_msg, trial_payload)
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

    @classmethod
    def revoke_local_license(cls, reason: str = "当前工位机授权已被管理员在云端吊销") -> Tuple[bool, str]:
        """
        远程或本地吊销授权凭证，安全移除本地许可文件并刷新状态
        (对标 Gear-NVH 远程锁机与吊销规范)
        """
        lic_path = cls.get_license_path()
        revoked_path = lic_path.with_suffix(".key.revoked")
        try:
            if lic_path.exists():
                try:
                    if revoked_path.exists():
                        revoked_path.unlink(missing_ok=True)
                    lic_path.replace(revoked_path)
                except Exception:
                    lic_path.unlink(missing_ok=True)

            global _CACHED_AUTH_RESULT, _LAST_AUTH_CHECK_TS
            _CACHED_AUTH_RESULT = (False, reason, {})
            _LAST_AUTH_CHECK_TS = datetime.now().timestamp()
            return True, "已安全吊销本地授权凭证"
        except Exception as e:
            return False, f"吊销异常: {str(e)}"

    @classmethod
    def get_installed_license_token(cls) -> Optional[str]:
        """获取当前安装的原始 Token 字符串"""
        lic_path = cls.get_license_path()
        if lic_path.exists():
            try:
                return lic_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return None


# 便捷别名与物理 MAC 地址提取
get_machine_id = get_machine_code
_CACHED_MAC_ADDRESS = None


def get_mac_address() -> str:
    """
    获取工位机真实的物理网卡 MAC 地址 (格式: XX:XX:XX:XX:XX:XX)
    单例内存缓存与多重静默获取，毫秒级快速返回，杜绝多进程阻塞与卡顿
    """
    global _CACHED_MAC_ADDRESS
    if _CACHED_MAC_ADDRESS is not None:
        return _CACHED_MAC_ADDRESS

    mac_found = None
    try:
        import subprocess, re
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        out_bytes = subprocess.check_output(
            "getmac /fo csv /nh",
            shell=True,
            timeout=1.5,
            startupinfo=startupinfo,
            stderr=subprocess.DEVNULL
        )
        out = out_bytes.decode("utf-8", errors="ignore")
        macs = [m.replace("-", ":").upper() for m in re.findall(r"([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})", out)]
        for m in macs:
            if not m.startswith("00:00:00") and not m.startswith("FF:FF:FF"):
                mac_found = m
                break
    except Exception:
        pass

    if not mac_found:
        try:
            import uuid
            node = uuid.getnode()
            mac_hex = f"{node:012X}"
            mac_found = ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
        except Exception:
            mac_found = "02:00:00:00:00:01" 

    _CACHED_MAC_ADDRESS = mac_found
    return _CACHED_MAC_ADDRESS


def get_station_info() -> Dict[str, Any]:
    """获取当前授权工位信息"""
    from src.core.i18n import i18n
    is_en = i18n.is_english()
    try:
        ok, _, payload = LicenseManager.is_system_authorized()
        if ok and payload:
            is_trial = payload.get("is_trial", False)
            if is_trial:
                days_left = payload.get("days_left", 7)
                exp = payload.get("exp_date", "")
                if is_en:
                    cust = payload.get("customer", "Full-Feature Evaluation User")
                    if cust == "全功能试用评估用户":
                        cust = "Full-Feature Evaluation User"
                    return {
                        "customer": cust,
                        "station": f"7-Day Evaluation Station ({days_left}d left · Exp {exp})",
                        "status_text": f"⏱️ 7-Day Trial Active ({days_left}d left)",
                        "is_trial": True,
                        "days_left": days_left,
                        "exp_date": exp
                    }
                return {
                    "customer": payload.get("customer", "全功能试用评估用户"),
                    "station": f"7天全功能评估工位 (剩余 {days_left} 天 · 截止 {exp})",
                    "status_text": f"7天全功能试用中 (剩 {days_left} 天)",
                    "is_trial": True,
                    "days_left": days_left,
                    "exp_date": exp
                }
            if is_en:
                cust = payload.get("customer", payload.get("cust", "Authorized R&D Center"))
                if cust == "内部核准机构":
                    cust = "Authorized R&D Center"
                stat = payload.get("station", payload.get("stat", "Pro R&D Workstation"))
                if "专业研发工作站" in stat:
                    stat = "Pro R&D Workstation"
                exp_v = payload.get("exp", "Permanent")
                if exp_v in ("永久有效", "PERMANENT"):
                    exp_v = "Permanent"
                return {
                    "customer": cust,
                    "station": stat,
                    "status_text": "🛡️ Active Commercial License",
                    "is_trial": False,
                    "days_left": -1,
                    "exp_date": exp_v
                }
            return {
                "customer": payload.get("customer", payload.get("cust", "内部核准机构")),
                "station": payload.get("station", payload.get("stat", "专业研发工作站 (Pro Station)")),
                "status_text": "🛡️ 正式商业授权",
                "is_trial": False,
                "days_left": -1,
                "exp_date": payload.get("exp", "永久有效")
            }
    except Exception:
        pass
    if is_en:
        return {
            "customer": "Full-Feature Evaluation User",
            "station": "Pro R&D Workstation",
            "status_text": "🔓 Evaluation Mode (Unactivated)",
            "is_trial": False,
            "days_left": 0,
            "exp_date": "-"
        }
    return {
        "customer": "全功能试用评估用户",
        "station": "专业研发工作站 (Pro Station)",
        "status_text": "未激活",
        "is_trial": False,
        "days_left": 0,
        "exp_date": "-"
    }

