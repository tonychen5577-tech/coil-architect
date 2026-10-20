"""
Coil-Architect Pro - Exclusive Keygen & License Signer (Admin Only)
开发者专属离线激活码签发工具 (支持 CLI 与 GUI 双模式)
"""

import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.license_manager import LicenseManager


def main_cli():
    print("=" * 60)
    print("Coil-Architect Pro - 商业授权私钥签发工具 (管理员专属)")
    print("=" * 60)

    mid = input("请输入客户机器码 (如 COIL-A1B2-C3D4-E5F6-7890，输入 * 代表通用): ").strip()
    if not mid:
        mid = "*"

    days_str = input("请输入授权有效天数 (默认 365 天，输入 0 代表永久): ").strip()
    if not days_str or days_str == "365":
        exp_date = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
    elif days_str == "0":
        exp_date = "PERMANENT"
    else:
        exp_date = (date.today() + timedelta(days=int(days_str))).strftime("%Y-%m-%d")

    cust = input("请输入客户企业/机构名称 (默认 ANSV Client): ").strip() or "ANSV Client"
    stat = input("请输入工位/设备编号 (默认 WORKSTATION-01): ").strip() or "WORKSTATION-01"

    token = LicenseManager.generate_token(mid, exp_date, cust, stat)

    print("\n" + "-" * 60)
    print(f"客户名称: {cust}")
    print(f"绑定机器: {mid}")
    print(f"到期时间: {exp_date}")
    print(f"工位编号: {stat}")
    print("-" * 60)
    print("【 签发激活码 (Token) 】:")
    print(token)
    print("-" * 60)

    # 导出文件
    save_file = f"license_{cust}_{exp_date}.lic".replace(" ", "_")
    with open(save_file, "w", encoding="utf-8") as f:
        f.write(token)
    print(f"已同时将许可证保存至当前目录: {save_file}\n")


if __name__ == "__main__":
    main_cli()
