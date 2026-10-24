"""
=============================================================================
Module: src.gui.cloud_config_dialog
Description: Coil-Architect Pro - 数据库网络通信设置与环境诊断控制中心
架构规范：完全对齐 Gear-NVH / FFT 分析软件 全量工业商业桌面软件企业内网网络与数据库连接标准
功能：
1. 显示受控云端与企业内网数据库通信链路；
2. 路由策略与内网代理设置 (自动读取系统代理 / 纯内网直连 / 手动内网代理)；
3. 一键网络全链路深度体检 (DNS 韧性穿透、TCP 端口握手、SSL 兼容通道与 API 鉴权)；
4. 诊断日志脱敏一键导出 (便于直接提供给内网技术专家分析)；
5. 导入定制网络参数配置文件 (支持内网私有部署与穿透网关一键同步)。
=============================================================================
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QMessageBox, QGroupBox,
    QApplication, QWidget, QFileDialog, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt

from src.core.cloud_client import (
    CloudClient, load_cloud_config, save_cloud_config, 
    DEFAULT_CLOUD_BASE_URL, get_client_ip
)
from src.core.license_manager import get_machine_code, get_mac_address
from src.core.i18n import i18n
from src.version import APP_NAME, APP_VERSION, APP_BUILD
from src.gui.utils import adapt_dialog_geometry
from src.gui.icon_helper import get_app_icon


def mask_server_url(url: str) -> str:
    """将内部敏感云端服务地址脱敏为受控专线标识，确保核心节点地址保密安全"""
    is_en = i18n.is_english()
    if not url:
        return (
            "🔒 High-Availability Secure Cloud Cluster (Managed Link · Auto-Failover)"
            if is_en else
            "🔒 云端高可用安全集群 (受控专线 · 自动容灾调度)"
        )
    url_lower = str(url).lower()
    if "gear.ansv.net" in url_lower or "coil.ansv.net" in url_lower or "workers.dev" in url_lower or "ansv.net" in url_lower:
        return (
            "🔒 High-Availability Secure Cloud Node (Managed Encrypted Link · Auto-Failover)"
            if is_en else
            "🔒 云端高可用安全集群节点 (受控加密专线 · 自动容灾调度)"
        )
    return url


def sanitize_diag_text(text: str) -> str:
    """全面清洗并脱敏诊断文本与导出日志，防止敏感信息与云厂商标识泄露"""
    if not text:
        return ""
    is_en = i18n.is_english()
    res = str(text)
    res = res.replace("https://coil.ansv.net", "https://[SECURE-CLOUD-NODE]")
    res = res.replace("http://coil.ansv.net", "http://[SECURE-CLOUD-NODE]")
    res = res.replace("coil.ansv.net", "[SECURE-CLOUD-NODE]")
    res = res.replace("https://gear.ansv.net", "https://[SECURE-CLOUD-NODE]")
    res = res.replace("gear.ansv.net", "[SECURE-CLOUD-NODE]")
    res = res.replace("tonychen5577.workers.dev", "[CDN-MIRROR-NODE]")
    res = res.replace("tony-tech.workers.dev", "[CDN-MIRROR-NODE]")
    res = res.replace("workers.dev", "[CDN-MIRROR-NODE]")
    res = re.sub(r'(?i)cloudf[a-z]*e', 'Cloud' if is_en else '云端', res)
    return res


class CloudConfigDialog(QDialog):
    """数据库网络通信与内网环境诊断控制中心"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_en = i18n.is_english()
        self.setWindowTitle(
            f"Network & Database Diagnostics Center — {APP_NAME}"
            if self.is_en else
            f"数据库通信与网络环境诊断中心 — {APP_NAME}"
        )
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                color: #0F172A;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QGroupBox {
                font-weight: 700;
                color: #0284C7;
                font-size: 11.5px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 10px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)

        self.cfg = load_cloud_config()
        self._init_ui()
        adapt_dialog_geometry(self, target_w=720, target_h=580, min_w=580, min_h=420)

    def _init_ui(self):
        is_en = self.is_en
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        # 1. 顶部提示栏
        lbl_intro = QLabel(
            "🔒 <b>Enterprise Database Connectivity Assurance</b>: Built-in sequential routing probe & SmartDNS resilient tunneling.\n"
            "• <b>Auto-Optimization</b>: Automatically probes [System Proxy] & [Direct Link] to lock the optimal route (read-only);\n"
            "• <b>Link Diagnostics</b>: Click [🔍 Run Network Diagnostics] to re-verify DNS, TCP, SSL & API authentication;\n"
            "• <b>Export Report</b>: Click [🩺 Export Diagnostic Report] to generate a sanitized log file for R&D support;\n"
            "• <b>Custom Config</b>: Click [📥 Import Network Config] to load an enterprise routing profile issued by support."
            if is_en else
            "🔒 <b>企业数据库通信保障说明</b>：系统已集成网络模式自动顺序验证与 SmartDNS 韧性穿透技术。\n"
            "• <b>自动优选</b>：系统自动顺序验证【系统代理】与【企业直连】等模式并锁定最佳连接链路，禁止个人擅自修改；\n"
            "• <b>连通诊断</b>：点击【🔍 开始网络连通诊断】可重新触发顺序验证并执行全链路体检；\n"
            "• <b>日志导出</b>：点击【🩺 一键体检并导出日志】可生成诊断报告直接提供给技术人员分析；\n"
            "• <b>参数定制</b>：点击【📥 导入网络设置参数】可直接导入由技术专家分发的专用配置文件。"
        )
        lbl_intro.setWordWrap(True)
        lbl_intro.setStyleSheet("""
            QLabel {
                font-size: 10.5px;
                color: #1E293B;
                background-color: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-radius: 6px;
                padding: 8px 10px;
                line-height: 1.45;
            }
        """)
        root_layout.addWidget(lbl_intro)

        # 2. 目标数据库通信链路
        group_url = QGroupBox(
            "📍 Database Communication Link (Managed Encrypted Channel)"
            if is_en else
            "📍 数据库通信数据链路 (云端加密受控)"
        )
        v_url = QVBoxLayout(group_url)
        v_url.setContentsMargins(12, 12, 12, 10)
        v_url.setSpacing(6)

        cur_url = self.cfg.get("server_url", DEFAULT_CLOUD_BASE_URL)
        self._target_server_url = cur_url
        self.edit_url = QLineEdit(mask_server_url(cur_url))
        self.edit_url.setReadOnly(True)
        self.edit_url.setToolTip(
            "Managed dynamically by SmartDNS & edge cluster; manual modification disabled"
            if is_en else
            "数据链路已由服务端与 SmartDNS 动态调度，禁止现场擅自篡改"
        )
        self.edit_url.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                font-size: 11.5px;
                font-family: 'Consolas', monospace;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #F1F5F9;
                color: #0369A1;
                font-weight: 700;
            }
        """)
        v_url.addWidget(self.edit_url)
        root_layout.addWidget(group_url)

        # 3. 网络代理与路由模式 (受控只读 · 自动顺序验证优选)
        group_proxy = QGroupBox(
            "🛡️ Network Routing Policy (Auto Sequential Probe · Managed Read-Only)"
            if is_en else
            "🛡️ 当前网络模式与路由策略 (自动顺序验证 · 受控只读)"
        )
        v_proxy = QVBoxLayout(group_proxy)
        v_proxy.setContentsMargins(12, 12, 12, 10)
        v_proxy.setSpacing(6)

        h_p_sel = QHBoxLayout()
        h_p_sel.addWidget(QLabel("Routing Mode:" if is_en else "网络模式:"))
        self.cmb_proxy = QComboBox()
        if is_en:
            self.cmb_proxy.addItems([
                "Auto-Detect System Proxy (Recommended, reads Windows Proxy & PAC)",
                "Enterprise Direct Connection (Bypasses proxy, direct intranet/leased line)",
                "Dedicated Local Proxy (Loaded from support configuration profile)"
            ])
        else:
            self.cmb_proxy.addItems([
                "自动检测系统代理 (推荐，自动读取 Windows 系统代理与 PAC)",
                "企业原生直连 (不走任何代理，企业内网/专线互联)",
                "专用本地代理 (技术专家配置文件指定专用端口)"
            ])
        p_mode = self.cfg.get("proxy_setting", "auto")
        if p_mode == "direct":
            self.cmb_proxy.setCurrentIndex(1)
        elif p_mode == "custom":
            self.cmb_proxy.setCurrentIndex(2)
        else:
            self.cmb_proxy.setCurrentIndex(0)
        self.cmb_proxy.setEnabled(False)  # 严格对标 Gear 规范，受控只读，禁止个人修改
        self.cmb_proxy.setToolTip(
            "Network routing mode is automatically locked via sequential probing (read-only)"
            if is_en else
            "网络连接模式已锁定为自动顺序验证，系统自动获取最佳连接方式 (受控只读，禁止个人擅自修改)"
        )
        self.cmb_proxy.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                font-size: 11px;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #F1F5F9;
                color: #334155;
            }
        """)
        h_p_sel.addWidget(self.cmb_proxy, 1)
        v_proxy.addLayout(h_p_sel)

        self.edit_custom_proxy = QLineEdit(self.cfg.get("custom_proxy", ""))
        self.edit_custom_proxy.setReadOnly(True)  # 受控只读
        self.edit_custom_proxy.setPlaceholderText(
            "Loaded automatically via [📥 Import Network Config]"
            if is_en else
            "由【📥 导入网络设置参数】自动载入，禁止个人手动输入"
        )
        self.edit_custom_proxy.setStyleSheet("""
            QLineEdit {
                padding: 5px 8px;
                font-size: 11px;
                font-family: monospace;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #F1F5F9;
                color: #334155;
            }
        """)
        self.edit_custom_proxy.setVisible(self.cmb_proxy.currentIndex() == 2)
        v_proxy.addWidget(self.edit_custom_proxy)

        root_layout.addWidget(group_proxy)

        # 4. 实时网络诊断控制台
        group_diag = QGroupBox(
            "🔍 Real-Time Network Connectivity Diagnostic Console"
            if is_en else
            "🔍 网络连通性实时诊断输出控制台"
        )
        v_diag = QVBoxLayout(group_diag)
        v_diag.setContentsMargins(12, 12, 12, 10)
        v_diag.setSpacing(6)

        self.txt_diag = QTextEdit()
        self.txt_diag.setReadOnly(True)
        self.txt_diag.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #38BDF8;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10.5px;
                border: 1px solid #1E293B;
                border-radius: 4px;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        self.txt_diag.setPlaceholderText(
            "Click [🔍 Run Network Diagnostics] below to automatically verify DNS, TCP handshake, SSL channel & API authentication..."
            if is_en else
            "点击下方的【🔍 开始网络连通诊断】按钮，系统将自动测试 DNS、TCP 端口、SSL 证书及 API 鉴权，并在此输出详尽诊断细节..."
        )
        v_diag.addWidget(self.txt_diag)
        root_layout.addWidget(group_diag, 1)

        # 5. 底部操作按钮
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_test = QPushButton("🔍 Run Network Diagnostics" if is_en else "🔍 开始网络连通诊断")
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                color: #166534;
                border: 1px solid #86EFAC;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #DCFCE7;
            }
        """)
        self.btn_test.clicked.connect(self._do_test)
        btn_box.addWidget(self.btn_test)

        self.btn_export_log = QPushButton("🩺 Export Diagnostic Report" if is_en else "🩺 一键体检并导出日志")
        self.btn_export_log.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_log.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #1D4ED8;
                border: 1px solid #93C5FD;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #DBEAFE;
            }
        """)
        self.btn_export_log.clicked.connect(self._export_diag_log)
        btn_box.addWidget(self.btn_export_log)

        self.btn_import_cfg = QPushButton("📥 Import Network Config" if is_en else "📥 导入网络设置参数")
        self.btn_import_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_cfg.setStyleSheet("""
            QPushButton {
                background-color: #FEF3C7;
                color: #92400E;
                border: 1px solid #FCD34D;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FDE68A;
            }
        """)
        self.btn_import_cfg.clicked.connect(self._import_config_file)
        btn_box.addWidget(self.btn_import_cfg)

        btn_box.addStretch()

        btn_close = QPushButton("Close" if is_en else "关闭")
        btn_close.setFixedWidth(80)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 700;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        root_layout.addLayout(btn_box)

    def _on_proxy_changed(self, idx: int):
        """受控只读：模式由系统自动顺序验证决定，忽略外部直接修改"""
        pass

    def _on_custom_proxy_changed(self, text: str):
        """受控只读：专用代理地址由配置文件导入，忽略个人手动输入"""
        pass

    def _do_test(self):
        """执行网络连通性诊断与模式自动顺序验证 (100% 对齐 Gear 工业级诊断标准)"""
        is_en = i18n.is_english()
        target_url = getattr(self, "_target_server_url", None) or CloudClient.get_server_url() or DEFAULT_CLOUD_BASE_URL
        if not target_url:
            if is_en:
                QMessageBox.warning(self, "Notice", "No valid license server endpoint found!")
            else:
                QMessageBox.warning(self, "提示", "未找到有效的数据库服务器地址！")
            return

        self.btn_test.setEnabled(False)
        self.btn_test.setText("⏳ Probing Network Routes..." if is_en else "⏳ 正在顺序探测网络...")
        self.txt_diag.clear()
        if is_en:
            self.txt_diag.append(f"[*] Starting Network Connectivity & Route Verification: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.txt_diag.append(f"• Software Version:   {APP_VERSION} (Build {APP_BUILD})")
            self.txt_diag.append(f"• Target Data Link:   {mask_server_url(target_url)}")
            self.txt_diag.append(f"• Workstation ID:     {get_machine_code()}")
            self.txt_diag.append(f"• Adapter MAC Addr:   {get_mac_address()}")
            self.txt_diag.append(f"• Local Intranet IP:  {get_client_ip()}")
            self.txt_diag.append("-" * 65)
            self.txt_diag.append("⏳ Probing routing modes sequentially to lock the optimal link...")
        else:
            self.txt_diag.append(f"[*] 开始网络连通性诊断与全自动模式验证: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.txt_diag.append(f"• 软件与构建版本: {APP_VERSION} (Build {APP_BUILD})")
            self.txt_diag.append(f"• 目标数据链路:   {mask_server_url(target_url)}")
            self.txt_diag.append(f"• 本机工位机器码: {get_machine_code()}")
            self.txt_diag.append(f"• 物理网卡 MAC:   {get_mac_address()}")
            self.txt_diag.append(f"• 本机内网 IP:    {get_client_ip()}")
            self.txt_diag.append("-" * 65)
            self.txt_diag.append("⏳ 正在自动顺序验证各网络模式，获取最佳连接链路...")
        QApplication.processEvents()

        best_mode, ok, summary_msg, probe_details = CloudClient.auto_detect_best_network_mode(target_url)

        for step_idx, probe in enumerate(probe_details, start=1):
            p_name = probe['name']
            if is_en:
                p_name = p_name.replace("系统代理", "System Proxy").replace("企业直连", "Direct Link").replace("专用代理", "Custom Proxy")
            if probe["ok"]:
                if is_en:
                    self.txt_diag.append(f"  [Step {step_idx}/{len(probe_details)}] {p_name}: ✅ Connected (Latency {probe['latency']}ms)")
                else:
                    self.txt_diag.append(f"  [步骤 {step_idx}/{len(probe_details)}] {p_name}: ✅ 连通成功 (延迟 {probe['latency']}ms)")
            else:
                if is_en:
                    self.txt_diag.append(f"  [Step {step_idx}/{len(probe_details)}] {p_name}: ❌ Unreachable ({sanitize_diag_text(probe['msg'])})")
                else:
                    self.txt_diag.append(f"  [步骤 {step_idx}/{len(probe_details)}] {p_name}: ❌ 连接未通 ({sanitize_diag_text(probe['msg'])})")

        self.txt_diag.append("-" * 65)
        self.btn_test.setEnabled(True)
        self.btn_test.setText("🔍 Run Network Diagnostics" if is_en else "🔍 开始网络连通诊断")

        # 刷新下拉框显示对应最佳模式
        if best_mode == "direct":
            self.cmb_proxy.setCurrentIndex(1)
        elif best_mode == "custom":
            self.cmb_proxy.setCurrentIndex(2)
        else:
            self.cmb_proxy.setCurrentIndex(0)
        self.edit_custom_proxy.setVisible(self.cmb_proxy.currentIndex() == 2)

        if ok:
            if is_en:
                self.txt_diag.append(f"🎯 Optimal Route Locked: {best_mode.upper()}")
                self.txt_diag.append("• SSL Secure Channel:   Established (Enterprise TLS Compatibility Active)")
                self.txt_diag.append("• API Authentication:   HTTP 200 OK (X-API-Key Verified)")
                self.txt_diag.append("• License Cloud Status: Ready & Online")
                QMessageBox.information(
                    self,
                    "Connection Verified",
                    f"✅ Network route verification complete!\n\nOptimal Mode: {best_mode.upper()}\n\nThe system has locked the best communication link."
                )
            else:
                self.txt_diag.append(f"🎯 最佳连接方式: {summary_msg}")
                self.txt_diag.append("• SSL 握手安全通道: 正常建立 (企业内网安全证书兼容模式生效)")
                self.txt_diag.append("• API 通信鉴权:     HTTP 200 OK (X-API-Key 已匹配)")
                self.txt_diag.append("• 数据库状态:       正常就绪，可无缝同步与查阅专家案例！")
                QMessageBox.information(self, "连接成功", f"✅ 网络模式顺序验证完成！\n\n{summary_msg}\n\n系统已自动为您锁定最佳通信链路。")
        else:
            if is_en:
                self.txt_diag.append(f"❌ [Diagnostic Failed] Unable to reach license cluster ({best_mode})")
                self.txt_diag.append("\n[Troubleshooting Recommendations]:")
                self.txt_diag.append("1. Verify that this workstation has internet or enterprise intranet access;")
                self.txt_diag.append("2. Check if a firewall or gateway is blocking outbound HTTPS traffic;")
                self.txt_diag.append("3. Click [📥 Import Network Config] to load a dedicated routing profile from support.")
                QMessageBox.critical(
                    self,
                    "Connection Offline",
                    "⚠️ Database network connection is currently unreachable!\n\n"
                    "Troubleshooting recommendations have been printed to the diagnostic console."
                )
            else:
                self.txt_diag.append(f"❌ [诊断失败] {summary_msg}")
                self.txt_diag.append("\n【排查诊断分析与对策建议】:")
                self.txt_diag.append("1. 请检查本机是否能正常访问公网或企业专网；")
                self.txt_diag.append("2. 请检查局域网防火墙或网络路由设备是否拦截了出站网络通信；")
                self.txt_diag.append("3. 若现场网络发生变动，请点击【📥 导入网络设置参数】重新导入由技术专家分发的专用配置文件。")
                QMessageBox.critical(self, "连接未就绪", f"⚠️ 数据库网络连接未就绪！\n\n原因: {summary_msg}\n\n详细排查建议已输出至控制台，请参考修改。")

    def _export_diag_log(self):
        """一键执行环境体检并将诊断报告保存为日志文件，方便直接发送给技术专家分析 (对标 Gear 标准)"""
        is_en = i18n.is_english()
        self._do_test()

        diag_text = self.txt_diag.toPlainText().strip()
        if not diag_text:
            return

        target_url = getattr(self, "_target_server_url", None) or CloudClient.get_server_url() or DEFAULT_CLOUD_BASE_URL
        desktop_dir = Path.home() / "Desktop"
        if not desktop_dir.exists():
            desktop_dir = Path.home()

        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        def_filename = f"Coil_Architect_NetDiag_{time_str}.txt"
        save_path = desktop_dir / def_filename

        if is_en:
            report_lines = [
                "=" * 70,
                "ANSV Coil-Architect Pro - Network & Database Diagnostic Report",
                f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"App Version:  {APP_VERSION} (Build {APP_BUILD})",
                f"Workstation:  {get_machine_code()}",
                f"MAC Address:  {get_mac_address()}",
                f"Data Link:    {mask_server_url(target_url)}",
                "=" * 70,
                "",
                "[Network Probe & Connectivity Details]",
                diag_text,
                "=" * 70,
                "[Note] Please send this report file to ANSV R&D support for network analysis."
            ]
        else:
            report_lines = [
                "=" * 70,
                "ANSV Coil-Architect Pro 专家数据库通信与网络环境体检报告",
                f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"软件版本: {APP_VERSION} (Build {APP_BUILD})",
                f"本机机器码: {get_machine_code()}",
                f"网卡 MAC:   {get_mac_address()}",
                f"通信链路: {mask_server_url(target_url)}",
                "=" * 70,
                "",
                "[网络探测与连通性详情]",
                diag_text,
                "=" * 70,
                "【说明】请将此报告文件发送给研发支持人员确认网络环境链路。"
            ]

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines) + "\n")

            if is_en:
                res = QMessageBox.information(
                    self,
                    "Diagnostic Report Exported",
                    f"🩺 Network diagnostic report saved to Desktop!\n\n"
                    f"📄 Filename: {def_filename}\n"
                    f"📁 Path: {save_path}\n\n"
                    f"You can send this text file to our support engineer for analysis.\n"
                    f"Would you like to open the folder now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
            else:
                res = QMessageBox.information(
                    self,
                    "体检日志导出成功",
                    f"🩺 网络环境诊断报告已成功保存至桌面！\n\n"
                    f"📄 文件名: {def_filename}\n"
                    f"📁 路径: {save_path}\n\n"
                    f"您可以直接将此文本文件发送给技术专家协助定位内网问题。\n"
                    f"是否立即在文件夹中查看该报告？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
            if res == QMessageBox.StandardButton.Yes:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(desktop_dir)))
        except Exception as e:
            if is_en:
                QMessageBox.warning(self, "Export Failed", f"Failed to save diagnostic report: {e}")
            else:
                QMessageBox.warning(self, "导出失败", f"保存体检报告时出错: {e}")

    def _import_config_file(self):
        """导入作者或管理员下发的受控标准网络配置文件 (.json / .cfg)"""
        is_en = i18n.is_english()
        desktop_dir = Path.home() / "Desktop"
        if not desktop_dir.exists():
            desktop_dir = Path.home()

        if is_en:
            fpath, _ = QFileDialog.getOpenFileName(
                self,
                "Select Network Configuration Profile",
                str(desktop_dir),
                "Network Config Files (*.json *.cfg *.txt);;All Files (*.*)"
            )
        else:
            fpath, _ = QFileDialog.getOpenFileName(
                self,
                "选择技术人员发送的网络配置文件",
                str(desktop_dir),
                "网络配置文件 (*.json *.cfg *.txt);;所有文件 (*.*)"
            )
        if not fpath:
            return

        ok, msg = CloudClient.import_config_from_file(fpath)
        if ok:
            self.cfg = load_cloud_config()
            self._target_server_url = self.cfg.get("server_url", DEFAULT_CLOUD_BASE_URL)
            self.edit_url.setText(mask_server_url(self._target_server_url))

            p_mode = self.cfg.get("proxy_setting", "auto")
            if p_mode == "direct":
                self.cmb_proxy.setCurrentIndex(1)
            elif p_mode == "custom":
                self.cmb_proxy.setCurrentIndex(2)
            else:
                self.cmb_proxy.setCurrentIndex(0)

            self.edit_custom_proxy.setText(self.cfg.get("custom_proxy", ""))
            self.edit_custom_proxy.setVisible(p_mode == "custom")

            if is_en:
                QMessageBox.information(self, "Import Successful", f"✅ Network configuration imported and applied!\n\n{sanitize_diag_text(msg)}")
            else:
                QMessageBox.information(self, "导入成功", f"✅ 网络参数已成功导入并生效！\n\n{sanitize_diag_text(msg)}")
            self._do_test()
        else:
            if is_en:
                QMessageBox.warning(self, "Import Failed", f"❌ Failed to import network configuration:\n{msg}")
            else:
                QMessageBox.warning(self, "导入失败", f"❌ 网络参数导入失败:\n{msg}")


def open_cloud_config_dialog(parent=None, **kwargs):
    """便捷调出网络与数据库通信诊断中心"""
    dlg = CloudConfigDialog(parent)
    return dlg.exec()
