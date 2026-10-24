"""
=============================================================================
Tool: tools/publish_release_to_cloud.py
Description: Coil-Architect Pro 官方云端 OTA 发版元数据自动化发布与同步工具
自动化将本地最新编译打包的 Full 完整包与 Patch 增量包元信息注册至 Cloudflare D1 边缘节点，
确保全国/全球各工位机在「检查更新」或启动时 100% 毫秒级探测到最新构建版本。
=============================================================================
"""

import os
import sys
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Windows 控制台编码安全保护
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 注入项目根路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.version import APP_VERSION, APP_BUILD, APP_DATE

CLOUD_URL = "https://coil.ansv.net"
ADMIN_PASSWORD = os.environ.get("COIL_ADMIN_PASSWORD", "Ansv@Coil#2026")
DEFAULT_SESSION_COOKIE = "coil_admin_session=COIL_AUTH_VALID_ANSV_2026_SESSION"


def get_file_info(file_path: Path):
    if not file_path.exists():
        return 0.0, ""
    size_mb = file_path.stat().st_size / (1024 * 1024)
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(256 * 1024):
            h.update(chunk)
    return round(size_mb, 2), h.hexdigest().lower()


def publish_release(
    version: str = None,
    build: str = None,
    server_base: str = CLOUD_URL,
    is_mandatory: bool = False
) -> bool:
    ver = version or APP_VERSION
    bld = build or APP_BUILD
    today_str = datetime.now().strftime("%Y-%m-%d")

    dist_dir = ROOT_DIR / "dist"
    full_zip = dist_dir / f"ANSV_Coil_Architect_Pro_{ver}_Full.zip"
    patch_zip = dist_dir / f"ANSV_Coil_Architect_Pro_{ver}_Incremental_Patch.zip"

    full_size, full_sha = get_file_info(full_zip)
    patch_size, patch_sha = get_file_info(patch_zip)

    # 规范化 release version 标识 (以 1.1.0-BUILD 命名，保证递增与唯一索引)
    clean_ver = ver.lstrip("vV")
    release_version_key = f"{clean_ver}-{bld}"

    download_url = f"https://github.com/tonychen5577-tech/coil-architect/releases/download/{ver}/ANSV_Coil_Architect_Pro_{ver}_Full.zip"
    patch_url = f"https://github.com/tonychen5577-tech/coil-architect/releases/download/{ver}/ANSV_Coil_Architect_Pro_{ver}_Incremental_Patch.zip"

    changelog = f"""### ANSV Coil-Architect Pro {ver} (Build {bld})
- 🌟 核心算法与拓扑：优化微观多层密排绕线算法与实际截面拓扑（支持不在同一层出现的绕线计算）；
- 📊 报表与方案比对：强化 Excel 仿真报告自适应导出，方案比对抽屉补齐内长内宽等几何指标并支持方案导入导出与现场还原；
- 🛡️ 工业授权与网络：统一授权悬停与点击有效期，在线数据库面板展示版本号、构建号与真实物理 MAC；
- 📖 双语手册全量内置：中英双语离线说明书与非同层截面图全量打包，F1 一键本地离线查看。"""

    payload = {
        "version": release_version_key,
        "build": bld,
        "release_date": today_str,
        "download_url": download_url,
        "backup_url": patch_url,
        "sha256": full_sha,
        "file_size_mb": full_size,
        "changelog": changelog,
        "is_mandatory": 1 if is_mandatory else 0
    }

    print(f"[Cloud-OTA] 正在向边缘发布节点同步版本元数据: {server_base}/admin/api/releases ...")
    print(f"  - 发布版本键: {release_version_key}")
    print(f"  - 构建指纹号: {bld}")
    print(f"  - 全量包体积: {full_size} MB | SHA256: {full_sha[:12]}...")
    print(f"  - 补丁包体积: {patch_size} MB | SHA256: {patch_sha[:12]}...")

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cookie": DEFAULT_SESSION_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CoilArchitectPro-Publisher/1.1.0"
    }

    req = urllib.request.Request(
        f"{server_base}/admin/api/releases",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                print("[Cloud-OTA] [OK] 云端 D1 数据库发布元数据更新成功！")
            else:
                print(f"[Cloud-OTA] [FAIL] 发布失败: {data}")
                return False
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        if "UNIQUE constraint failed" in err_body or "SQLITE_CONSTRAINT" in err_body:
            print(f"[Cloud-OTA] [INFO] 云端数据库已存在该构建版本记录 ({release_version_key})。")
        else:
            print(f"[Cloud-OTA] [FAIL] HTTP Error {e.code}: {err_body}")
            return False
    except Exception as e:
        print(f"[Cloud-OTA] [FAIL] 通信异常: {e}")
        return False

    # 验证更新接口
    print("[Cloud-OTA] 正在校验公开检查更新接口 /api/v1/check_update ...")
    check_req = urllib.request.Request(
        f"{server_base}/api/v1/check_update",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(check_req, timeout=10) as resp:
            check_data = json.loads(resp.read().decode("utf-8"))
            server_build = check_data.get("build")
            server_ver = check_data.get("version")
            if server_build == bld:
                print(f"[Cloud-OTA] [SUCCESS] 验证通过！云端最新版本已刷新为: {server_ver} (Build {server_build})")
                return True
            else:
                print(f"[Cloud-OTA] [WARN] 校验异常: 云端返回 build={server_build}, 期望={bld}")
                return False
    except Exception as e:
        print(f"[Cloud-OTA] [WARN] 校验请求失败: {e}")
        return False


if __name__ == "__main__":
    publish_release()
