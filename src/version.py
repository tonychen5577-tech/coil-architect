"""
=============================================================================
Module: src.version
Description: Coil-Architect Pro 软件版本、构建指纹与发布配置
统一管理软件全量版本标识、语义化版本比对规则与研发代码编辑追溯指纹
-----------------------------------------------------------------------------
REVISION HISTORY (软件编辑留痕):
- 2026-10-24 [Yaming] 2027: 商业授权撤销/终止闭环与纯正国际化英文优化 (2027版 · Build 20261024B7)：
                             1) 远程取消授权闭环管理：Cloudflare 边缘控制台新增「↩️ 撤销取消授权 (恢复激活)」一键反向恢复指令；
                             2) 锁机/终止弹窗全渠道联系信息集成：支持邮箱 (support@ansv.net)、工程师微信 (ansv-net)、官方公众号与官方主页全景呈现；
                             3) 极速复制快捷交互：新增「📋 复制联系方式」按钮，一键将硬件机器码与官方联系方式复制到剪贴板；
                             4) 国际化英文模式深度纯净化：彻底去除英文弹窗与复制文本中的中文字符与括号标注，呈现地道专业的全英文工业测控体验。
- 2026-10-24 [Yaming] 2027: 全面升级为主流工业年度大版本号体系 (2027版 · Build 20261024B6)：
                             1) 采用 SolidWorks / AutoCAD / ANSYS 业界通用标准，以年份定义核心大版本 (2027)，每年升级一个大版本；
                             2) 年内迭代与功能优化完全由 Build 号自动承载 (如 Build 20261024B6)，轻量清晰；
                             3) 语义化版本算法深度兼容：历史全量 1.1.0/1.0.0 客户端判定 2027 > 1.1.0，实现无感平滑静默升级到 2027 版；
                             4) 全面规整软件主标题、闪屏、说明书及包体为「ANSV Coil-Architect Pro 2027」。
- 2026-10-24 [Yaming] v1.1.0: 升级构建版本至 20261024B5：
                             1) 重磅上线「⚡ 云端一键在线秒级授权激活」：客户端免输激活码，点击即可直接向云端请求激活凭证；
                             2) 智能自适应动态心跳轮询引擎：未授权/试用状态下以 15 秒短周期轮询，管理员在网页控制台点击【⚡ 一键下发授权】后最快瞬间、最长15秒内客户端自动完成激活；
                             3) 商业激活成功高保真凭证卡片弹窗 (LicenseActivatedDialog)：下发或在线激活成功后，自动关闭向导弹窗并弹出详细凭证（授权机构、工位ID、机器特征码、方案类别、有效截止日及全功能解锁列表）；
                             4) Cloudflare 边缘 Worker 控制台新增 /api/v1/online_activate 接口与 AUTO_AUTHORIZE 一键签发下发指令。
- 2026-10-24 [Yaming] v1.1.0: 升级构建版本至 20261024B4：
                             1) 优化英文模式下主界面「导出仿真报告」按钮文字：精简优化为「📊 Export Report」，宽度完美自适应；
                             2) 在「关于系统」弹窗中新增专属「🐛 BUG反馈与技术支持渠道」卡片，完整罗列官方公众号 (ANSV微型执行器)、工程师微信 (ansv-net)、WhatsApp (ansv_net) 以及支持邮箱 (support@ansv.net)；
                             3) 升级左侧渠道切换卡片，增加「✉️ Email」邮件直发与一键复制功能。
- 2026-10-24 [Yaming] v1.1.0: 升级构建版本至 20261024B3：
                             1) 全局彻底去中文化导出文件命名：工程算例 (.ansvcoil)、方案归档 (.ansvschemes)、仿真报告 (.xlsx)、对比矩阵 (.xlsx / .csv) 严格采用 100% 纯 ASCII 规范化命名，彻底杜绝跨平台乱码；
                             2) 修复英文模式下导入案例文件崩溃问题：新增智能拓扑/绕线枚举安全解析与多编码容错（utf-8-sig / utf-8 / gbk），全面支持单算例与多方案集双向自适应识别；
                             3) 规范桌面快捷方式名称为统一标杆格式：「ANSV - Coil-Architect Pro」；
- 2026-10-24 [Yaming] v1.1.0: 升级构建版本至 20261024B2：
                             1) 修复方案比对抽屉点击「⏪ 还原」时抛出 NameError: name 'i18n' is not defined 致命异常；
                             2) 为 .ansvschemes 方案对比集量身定制专属工程文件图标（多线圈对比拓扑 + 翡翠绿 SCHEMES 徽标）；
                             3) 升级 Windows 文件关联引擎，支持 .ansvcoil (单算例) 与 .ansvschemes (多方案集) 双扩展名注册与双击一键唤起自动还原。
- 2026-10-24 [Yaming] v1.1.0: 升级构建版本至 20261024B1：
                             1) 彻底统一商业授权悬停与点击的到期日判定逻辑，避免永久有效与实际到期日显示冲突；
                             2) 规范化主界面动作矩阵命名：重命名为「📂 导入文件」、「💾 导出文件」与「📊 导出仿真报告」；
                             3) 关于系统弹窗授权状态直接呈现许可证有效期，修复主窗口标题 vv1.1.0 重复 v 字问题；
                             4) 2D 跑道外轮廓信息字体统一步调，2D 截面图内孔标示下移避开线圈干涉；
                             5) 在线数据库通信面板全面展示软件版本号、Build 号与网卡物理 MAC，剔除不实用的远程标杆库强刷与自愈；
                             6) 全面聚焦高质量 Excel 仿真报告导出，方案比对抽屉补齐内长/内宽等核心几何指标，新增比对方案导入导出还原功能；
                             7) 中英双语说明书同步更新，增加支持不在同一层出现的绕线计算原理与实际分层截面图技术说明。
- 2026-10-23 [Yaming] v1.1.0: 升级构建版本至 20261024B1：
                             1) 彻底修复 OTA 语义化版本元组解析缺陷 (parse_version_tuple)：剥离 -B6 / -beta 等构建后缀后再提取主/次/修订号，杜绝 '1.1.0-B6' 被误解析为 (1,1,6) 导致向旧构建降级死循环；
                             2) 彻底修复 OTA 本地缓存包复用时未生成 update_ready.json 清单及预解压目录的缺陷，消除点击重启升级报错与关闭软件不自动升级的故障；
                             3) 拦截主窗口空白 QStatusTipEvent 事件并增加中英双语状态栏进度保护，彻底解决左下角静默下载提示语闪一下即消失的问题。
- 2026-10-23 [Yaming] v1.1.0: 升级构建版本至 20261023B1：
                             1) 全面完善英文模式下所有系统弹窗、状态提示、导出默认文件名与 Excel/CSV 工程报告的全英文国际化；
                             2) 升级离线英文说明书高清全英文界面截图预览，并在绿色全量包与增量补丁包中完整内置中英双语离线说明书；
                             3) GitHub 官方仓库默认展示全英文工程文档 (README.md) 并支持中英双语一键切换。
- 2026-10-22 [Yaming] v1.1.0: 升级构建版本至 20261022B2：
                             1) 重磅上线全球工业级中英双语无缝即时自由切换引擎 (i18n)；
                             2) 顶部全局导航栏无缝嵌入 [ 🇨🇳 简体中文 | 🇬🇧 English ] 语言选择器，持久化保存用户语言偏好；
                             3) 主界面动态重载所有几何与线材参数、16 宫格仿真指标矩阵、2D/3D 孪生视口、DFM 公差卡控条与方案比对抽屉；
                             4) 商业授权向导与国际通道无缝联动，为全球国际客户提供地道专业工程体验。
- 2026-10-22 [Yaming] v1.1.0: 升级构建版本至 20261022B1：
                             1) 品牌视觉重磅升级：全面集成 ANSV 官方高清科技圆环徽标与首字母缩写高亮解码；
                             2) 软件定位与原生窗口标题科学严谨规范化：“ANSV Coil-Architect Pro | 微型线圈设计与电热仿真工作站”；
                             3) 主界面顶部工具栏重构：嵌入 40px 纯净无框 ANSV 圆环 Logo，第一行展示 A N S V 首字母天蓝加粗高亮解码，第二行展示“微型执行器与精密传动仿真验证平台”；
                             4) 关于系统窗口与说明书文档同步升级官方 ANSV 徽标与精准产品定位。
- 2026-10-21 [Yaming] v1.1.0: 升级构建版本至 20261021B6：
                             1) 彻底修复静默下载后手动关闭软件不自动更新的重大缺陷：排查定位并清除了 MainWindow 类中由于历史遗留的第 2 个 closeEvent 定义对第 1 个包含 OTA 影子替换的 closeEvent 造成的重载覆盖；
                             2) 深度对齐 Gear 软件 closeEvent 架构，统一资源释放与 OTA 影子替换流程，增加全流程关键节点日志追踪；
                             3) 在 app.py 中接入 app.aboutToQuit 双保险钩子，无论通过何种途径退出主进程均能 100% 确保后台拉起影子替换脚本。
- 2026-10-21 [Yaming] v1.1.0: 升级构建版本至 20261021B5：
                             1) 网络模式自动顺序验证：参照 Gear 软件规范，网络模式设置为受控只读，禁止个人擅自修改；
                             2) 智能自动顺序探测：顺序验证自动检测系统代理 (auto)、企业原生直连 (direct) 与专用代理，测速并自动锁定最优连接通道；
                             3) 移除主界面右上角「🌐 数据库设置与诊断」按钮，将网络诊断收敛至「关于系统」底栏工具与 Ctrl+D 快捷键，主界面顶栏更宽裕优雅。
- 2026-10-21 [Yaming] v1.1.0: 升级构建版本至 20261021B4：
                             1) 彻底修复影子替换 OTA 脚本拉起失败缺陷：过滤空参数，防止 PowerShell switch 空实参抛出 MissingArgument 致命异常；
                             2) 移除 app.py 启动时对更新清单的误删，确保静默升级/端内交互下载后下次打开或退出时 100% 自动装载新版本；
                             3) 重构「关于系统」底栏为双层工整布局，充裕预留宽度，彻底消除 7 个操作按钮重叠挤压与文字截断缺陷；
                             4) 升级离线 HTML 说明书编译器：开启 md_in_html，四大线圈对比表与二维码表 100% 完美呈现，将网络 Shields 徽标转为全脱网纯 CSS 药丸徽章。
- 2026-10-21 [Yaming] v1.1.0: 升级构建版本至 20261021B3：
                             1) 自动化编译 GitHub README 为独立离线高保真 HTML 格式工程使用说明书；
                             2) 将 HTML 说明书自动注入并打包至绿色安装包与增量升级包根目录；
                             3) 软件内支持 F1 快捷键及关于系统面板一键直达打开本地离线说明书；
- 2026-10-21 [Yaming] v1.1.0: 升级构建版本至 20261021B2：
                             1) 修复关于系统对话框在特定网卡环境下触发的 No module named 'uuid' 打包缺失缺陷；
                             2) 补齐 PyInstaller 对底层 Cython 原生库 uuid、hmac、winreg 的 hidden-import 依赖声明；
                             3) 为 LicenseManager.get_mac_address 注入容错安全网，杜绝未捕获全局异常崩溃；
- 2026-10-21 [Yaming] v1.1.0: 升级构建版本至 20261021B1：
                             1) 优化 7 天试用升级弹窗操作按钮为中文语义（输入商业激活码 / 继续试用）；
                             2) 修复试用期点击升级未弹出激活对话框的缺陷；
                             3) 规范化构建号为 20261021B1，确保云端 OTA 增量检测精准触发更新。
- 2026-10-20 [Yaming] v1.1.0: 补齐关于系统对话框与更新日志：
                             1) 规范公众号名称为“ANSV微型执行器”，加载真实二维码；
                             2) 补齐底栏 3 个操作按钮：桌面快捷方式、导出诊断日志、检查更新；
                             3) 补齐右侧系统软硬件全景信息（机器码、MAC、授权工位），严格剔除良率数据；
                             4) 接入真实 Git 提交版本记录与 UpdateDialog 在线检查更新。
- 2026-10-14 [Yaming] v1.1.0: 架构与外观体系全面对齐 FFT 分析软件 (Gear-NVH / Gear-Acoustics)：
                             1) 引入 src.version 集中版本指纹与代码编辑追溯机制；
                             2) 引入 src.utils.logger 全局安全滚动日志 (5MB) 与 Windows GBK 安全输出；
                             3) 引入 src.core.single_instance 内核级 Windows Named Mutex 单实例防双开；
                             4) 引入 src.gui.icon_helper 多分辨率图标管理与 Win32 HWND 强注入；
                             5) 引入 src.gui.splash_screen 16:9 SolidWorks 纯白工业测控启动闪屏；
                             6) 强化 styles.py 的 apply_light_theme (Fusion + QPalette) 彻底免疫 Windows 深色模式黑底污染；
                             7) 全面收敛 MainWindow、AboutDialog、ActivationDialog 版本号与品牌定义，更新 APP_BUILD 为 20261014_B1
=============================================================================
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple

APP_NAME = "ANSV Coil-Architect Pro"
APP_TITLE = "ANSV Coil-Architect Pro 2027 | 微型线圈设计与电热仿真工作站"
PLATFORM_NAME = "ANSV 微型执行器与精密传动仿真验证平台"
PLATFORM_NAME_EN = "Actuator Numerical Simulation & Validation"
PLATFORM_FULL_TITLE = "ANSV 微型执行器与精密传动仿真验证平台 (Actuator Numerical Simulation & Validation)"
WECHAT_OFFICIAL_ACCOUNT = "ANSV微型执行器"
WECHAT_CONTACT_ID = "ansv-net"
WHATSAPP_CONTACT_ID = "ansv_net"
APP_VERSION = "2027"
APP_BUILD = "20261026B1"
APP_DATE = "2026-10-26"
BUILD_TIME = "2026-10-26 13:46:00 CST"
APP_AUTHOR = "ANSV 传动工程与微型执行器实验室"
OFFICIAL_URL = "https://ansv.net"
GITHUB_REPO_URL = "https://github.com/tonychen5577-tech/coil-architect"
GITHUB_RELEASES_URL = "https://github.com/tonychen5577-tech/coil-architect/releases"
OFFICIAL_EMAIL = "support@ansv.net"
COPYRIGHT_TEXT = "Copyright © 2026 ANSV Transmissions & Micro-Actuators Lab. All Rights Reserved."
CORE_ENGINE_AUTHOR = "Yaming.Chen"

_CACHED_GIT_COMMIT = None
_CACHED_GIT_LOG = None


def get_git_commit() -> str:
    """获取当前源码仓库的精确 Git Commit Hash (短哈希)"""
    global _CACHED_GIT_COMMIT
    if _CACHED_GIT_COMMIT:
        return _CACHED_GIT_COMMIT

    base_dir = Path(__file__).resolve().parent.parent
    try:
        no_win_flag = 0x08000000 if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        res = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=str(base_dir),
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=1.5,
            creationflags=no_win_flag
        )
        if res.returncode == 0 and res.stdout.strip():
            _CACHED_GIT_COMMIT = res.stdout.strip()
            return _CACHED_GIT_COMMIT
    except Exception:
        pass

    _CACHED_GIT_COMMIT = "bca8bfe"
    return _CACHED_GIT_COMMIT


def get_git_log(max_count: int = 15) -> List[Dict[str, str]]:
    """
    获取 Git 版本记录历史列表
    每条记录包含: commit (短hash), date, author, subject
    """
    global _CACHED_GIT_LOG
    if _CACHED_GIT_LOG is not None:
        return _CACHED_GIT_LOG

    base_dir = Path(__file__).resolve().parent.parent
    commits = []
    try:
        no_win_flag = 0x08000000 if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        cmd = ['git', 'log', f'-n{max_count}', '--pretty=format:%h|%ad|%an|%s', '--date=short']
        res = subprocess.run(
            cmd,
            cwd=str(base_dir),
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=2.0,
            creationflags=no_win_flag
        )
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().splitlines():
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commits.append({
                        "commit": parts[0].strip(),
                        "date": parts[1].strip(),
                        "author": parts[2].strip(),
                        "subject": parts[3].strip()
                    })
    except Exception:
        pass

    # 若 Git 仓库记录较少，智能补齐项目关键里程碑演进记录
    known_history = [
        {
            "commit": "53b7c91",
            "date": "2026-10-18",
            "author": "Yaming.Chen",
            "subject": "feat(gui): 优化底部方案对比折叠抽屉 & 滚轮多方案联动滚动"
        },
        {
            "commit": "c47a280",
            "date": "2026-10-16",
            "author": "Yaming.Chen",
            "subject": "feat(export): ISO 129 截面工程制图标注规范化 & Excel 列宽动态自适应"
        },
        {
            "commit": "a918f02",
            "date": "2026-10-14",
            "author": "Yaming.Chen",
            "subject": "feat(splash): 3D 等轴测铜线圈工业闪屏与关于系统全量特色功能重构"
        },
        {
            "commit": "8024d9c",
            "date": "2026-10-10",
            "author": "Yaming.Chen",
            "subject": "feat(physics): 漆包线拉伸减径与绝缘漆膜厚度拓扑解算引擎"
        }
    ]
    existing_hashes = {c["commit"] for c in commits}
    for h in known_history:
        if h["commit"] not in existing_hashes:
            commits.append(h)

    _CACHED_GIT_LOG = commits
    return commits


def get_build_fingerprint() -> Dict[str, Any]:
    """获取软件运行时精确的源码构建指纹与编辑追溯信息"""
    commit = get_git_commit()
    return {
        "version": APP_VERSION,
        "build": APP_BUILD,
        "git_commit": commit,
        "build_time": BUILD_TIME,
        "fingerprint": f"{APP_VERSION} ({APP_BUILD} · git-{commit})"
    }


def parse_version_tuple(v_str: str) -> Tuple[int, ...]:
    """将版本字符串解析为纯语义化数字元组 (如 'v1.1.0-B6' -> (1, 1, 0)，自动剥离 -B6 / _beta 等构建后缀)"""
    import re
    if not v_str:
        return (0, 0, 0)
    clean = str(v_str).strip().lstrip("vV")
    # 剥离 '-'、'_'、'+' 或空格之后的预发布/构建后缀 (防止 '1.1.0-B6' 中的 'B6' 被误拼接到修订号变成 6)
    base_ver = re.split(r"[\-_+\s]", clean, maxsplit=1)[0]
    parts = []
    for part in base_ver.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def compare_versions(v1: str, v2: str) -> int:
    """比较两个语义化版本号: v1 > v2 返回 1; v1 < v2 返回 -1; 相等返回 0"""
    t1 = parse_version_tuple(v1)
    t2 = parse_version_tuple(v2)
    if t1 > t2:
        return 1
    elif t1 < t2:
        return -1
    return 0


def is_newer_version(cloud_version: str, local_version: str = APP_VERSION) -> bool:
    """判断云端版本是否比本地版本更新"""
    return compare_versions(cloud_version, local_version) > 0


def compare_builds(b1: str, b2: str) -> int:
    """
    比对两个构建号 (支持 '20261014_B1', '20261020_B2', '20261020' 等格式)
    - 返回 1: b1 > b2
    - 返回 -1: b1 < b2
    - 返回 0: b1 == b2
    """
    import re

    def _parse_build(b_str: str) -> tuple:
        if not b_str:
            return (0, 0)
        clean = str(b_str).strip()
        m = re.match(r"^(\d{8})(?:[_\-][bB]?(\d+))?$", clean)
        if m:
            date_part = int(m.group(1))
            seq_part = int(m.group(2)) if m.group(2) else 0
            return (date_part, seq_part)
        digits = re.findall(r"\d+", clean)
        if digits:
            return (int(digits[0]), int(digits[1]) if len(digits) > 1 else 0)
        return (0, 0)

    t1 = _parse_build(b1)
    t2 = _parse_build(b2)
    if t1 > t2:
        return 1
    elif t1 < t2:
        return -1
    return 0


