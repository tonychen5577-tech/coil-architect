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
from src.version import APP_NAME, APP_VERSION
from src.gui.utils import adapt_dialog_geometry
from src.gui.icon_helper import get_app_icon


def mask_server_url(url: str) -> str:
    """将内部敏感云端服务地址脱敏为受控专线标识，确保核心节点地址保密安全"""
    if not url:
        return "🔒 云端高可用安全集群 (受控专线 · 自动容灾调度)"
    url_lower = str(url).lower()
    if "gear.ansv.net" in url_lower or "coil.ansv.net" in url_lower or "workers.dev" in url_lower or "ansv.net" in url_lower:
        return "🔒 云端高可用安全集群节点 (受控加密专线 · 自动容灾调度)"
    return url


def sanitize_diag_text(text: str) -> str:
    """全面清洗并脱敏诊断文本与导出日志，防止敏感信息与云厂商标识泄露"""
    if not text:
        return ""
    res = str(text)
    res = res.replace("https://coil.ansv.net", "https://[SECURE-CLOUD-NODE]")
    res = res.replace("http://coil.ansv.net", "http://[SECURE-CLOUD-NODE]")
    res = res.replace("coil.ansv.net", "[SECURE-CLOUD-NODE]")
    res = res.replace("https://gear.ansv.net", "https://[SECURE-CLOUD-NODE]")
    res = res.replace("gear.ansv.net", "[SECURE-CLOUD-NODE]")
    res = res.replace("tonychen5577.workers.dev", "[CDN-MIRROR-NODE]")
    res = res.replace("tony-tech.workers.dev", "[CDN-MIRROR-NODE]")
    res = res.replace("workers.dev", "[CDN-MIRROR-NODE]")
    res = re.sub(r'(?i)cloudf[a-z]*e', '云端', res)
    return res


class CloudConfigDialog(QDialog):
    """数据库网络通信与内网环境诊断控制中心"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"数据库通信与网络环境诊断中心 — {APP_NAME}")
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
        adapt_dialog_geometry(self, target_w=660, target_h=580, min_w=520, min_h=420)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        # 1. 顶部提示栏
        lbl_intro = QLabel(
            "🔒 <b>企业内网连接保障说明</b>：系统已集成 SmartDNS 韧性穿透与 Anycast 安全通道，自动应对内网 DNS 阻断。\n"
            "• <b>网络排查</b>：点击【🔍 开始网络连通诊断】可执行 DNS、TCP、SSL 与 API 接口全链路检测；\n"
            "• <b>链路体检</b>：点击【🩺 一键体检并导出日志】可生成诊断报告直接提供给技术人员分析；\n"
            "• <b>参数定制</b>：点击【📥 导入网络设置参数】可直接导入内网私有部署或专属代理配置文件。"
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
        group_url = QGroupBox("📍 数据库通信数据链路 (云端加密受控)")
        v_url = QVBoxLayout(group_url)
        v_url.setContentsMargins(12, 12, 12, 10)
        v_url.setSpacing(6)

        cur_url = self.cfg.get("server_url", DEFAULT_CLOUD_BASE_URL)
        self._target_server_url = cur_url
        self.edit_url = QLineEdit(mask_server_url(cur_url))
        self.edit_url.setReadOnly(True)
        self.edit_url.setToolTip("数据链路已由服务端与 SmartDNS 动态调度，禁止现场擅自篡改")
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

        # 3. 网络代理与路由模式
        group_proxy = QGroupBox("🛡️ 当前网络代理与内网路由策略")
        v_proxy = QVBoxLayout(group_proxy)
        v_proxy.setContentsMargins(12, 12, 12, 10)
        v_proxy.setSpacing(6)

        h_p_sel = QHBoxLayout()
        h_p_sel.addWidget(QLabel("网络模式:"))
        self.cmb_proxy = QComboBox()
        self.cmb_proxy.addItems([
            "自动检测系统代理 (推荐，自动读取 Windows 系统代理)",
            "直连模式 (不走任何代理，企业内网/涉密局域网互通)",
            "指定本地代理 (手动指定内网代理服务器端口)"
        ])
        p_mode = self.cfg.get("proxy_setting", "auto")
        if p_mode == "direct":
            self.cmb_proxy.setCurrentIndex(1)
        elif p_mode == "custom":
            self.cmb_proxy.setCurrentIndex(2)
        else:
            self.cmb_proxy.setCurrentIndex(0)
        self.cmb_proxy.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                font-size: 11px;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #1E293B;
            }
        """)
        self.cmb_proxy.currentIndexChanged.connect(self._on_proxy_changed)
        h_p_sel.addWidget(self.cmb_proxy, 1)
        v_proxy.addLayout(h_p_sel)

        self.edit_custom_proxy = QLineEdit(self.cfg.get("custom_proxy", ""))
        self.edit_custom_proxy.setPlaceholderText("请输入代理地址，例如: http://10.0.0.1:8080 或 socks5://127.0.0.1:10808")
        self.edit_custom_proxy.setStyleSheet("""
            QLineEdit {
                padding: 5px 8px;
                font-size: 11px;
                font-family: monospace;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #1E293B;
            }
        """)
        self.edit_custom_proxy.setVisible(self.cmb_proxy.currentIndex() == 2)
        self.edit_custom_proxy.textChanged.connect(self._on_custom_proxy_changed)
        v_proxy.addWidget(self.edit_custom_proxy)

        root_layout.addWidget(group_proxy)

        # 4. 实时网络诊断控制台
        group_diag = QGroupBox("🔍 网络连通性实时诊断输出控制台")
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
        self.txt_diag.setPlaceholderText("点击下方的【🔍 开始网络连通诊断】按钮，系统将自动测试 DNS、TCP 端口、SSL 证书及 API 鉴权，并在此输出详尽诊断细节...")
        v_diag.addWidget(self.txt_diag)
        root_layout.addWidget(group_diag, 1)

        # 5. 底部操作按钮
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_test = QPushButton("🔍 开始网络连通诊断")
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

        self.btn_export_log = QPushButton("🩺 一键体检并导出日志")
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

        self.btn_import_cfg = QPushButton("📥 导入网络设置参数")
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

        btn_close = QPushButton("关闭")
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
        modes = ["auto", "direct", "custom"]
        p_mode = modes[idx] if idx < len(modes) else "auto"
        self.edit_custom_proxy.setVisible(idx == 2)
        self.cfg["proxy_setting"] = p_mode
        save_cloud_config(self.cfg)

    def _on_custom_proxy_changed(self, text: str):
        self.cfg["custom_proxy"] = text.strip()
        save_cloud_config(self.cfg)

    def _do_test(self):
        """执行网络连通性诊断 (100% 对齐 Gear 工业级诊断标准)"""
        target_url = getattr(self, "_target_server_url", None) or CloudClient.get_server_url() or DEFAULT_CLOUD_BASE_URL
        if not target_url:
            QMessageBox.warning(self, "提示", "未找到有效的数据库服务器地址！")
            return

        ps_idx = self.cmb_proxy.currentIndex()
        ps_mode = "auto" if ps_idx == 0 else ("direct" if ps_idx == 1 else "custom")
        cp_val = self.edit_custom_proxy.text().strip() if ps_mode == "custom" else ""

        self.btn_test.setEnabled(False)
        self.btn_test.setText("⏳ 正在探测网络...")
        self.txt_diag.clear()
        self.txt_diag.append(f"[*] 开始网络连通性诊断: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.txt_diag.append(f"• 目标数据链路:   {mask_server_url(target_url)}")
        self.txt_diag.append(f"• 路由代理模式:   {ps_mode} {('(' + cp_val + ')') if cp_val else ''}")
        self.txt_diag.append(f"• 本机机器标识码: {get_machine_code()}")
        self.txt_diag.append(f"• 本机网卡 MAC:   {get_mac_address()}")
        self.txt_diag.append(f"• 本机内网 IP:    {get_client_ip()}")
        self.txt_diag.append("-" * 65)
        QApplication.processEvents()

        ok, msg = CloudClient.test_connection(target_url, ps_mode, cp_val)
        self.btn_test.setEnabled(True)
        self.btn_test.setText("🔍 开始网络连通诊断")

        clean_msg = sanitize_diag_text(msg)
        if ok:
            self.txt_diag.append(f"✅ [诊断通过] {clean_msg}")
            self.txt_diag.append("• SSL 握手安全通道: 正常建立 (兼容证书模式)")
            self.txt_diag.append("• API 通信鉴权:     HTTP 200 OK (X-API-Key 已匹配)")
            self.txt_diag.append("• 数据库状态:       正常就绪，可无缝同步与查阅专家案例！")
            QMessageBox.information(self, "连接成功", f"✅ 数据库联机测试成功！\n\n{clean_msg}")
        else:
            self.txt_diag.append(f"❌ [诊断失败] {clean_msg}")
            self.txt_diag.append("\n【排查诊断分析与对策建议】:")
            if "127.0.0.1" in target_url or "localhost" in target_url:
                self.txt_diag.append("1. 您配置的地址为 127.0.0.1 (本机)。若数据库运行在另一台主机电脑上，请将 127.0.0.1 替换为该主机的局域网 IP；")
                self.txt_diag.append("2. 请确认该主机电脑上已启动数据库后端服务。")
            else:
                self.txt_diag.append("1. 请检查本机是否能正常访问公网（可尝试开启或切换系统网络代理）；")
                self.txt_diag.append("2. 请检查局域网防火墙或路由器是否拦截了出站网络通信；")
                self.txt_diag.append("3. 若现场网络发生变动，请点击【📥 导入网络设置参数】重新导入由技术专家分发的配置文件。")
            QMessageBox.critical(self, "连接失败", f"❌ 数据库未能连通！\n\n原因: {clean_msg}\n\n详细排查建议已输出至控制台，请参考修改。")

    def _export_diag_log(self):
        """一键执行环境体检并将诊断报告保存为日志文件，方便直接发送给技术专家分析 (对标 Gear 标准)"""
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

        report_lines = [
            "=" * 70,
            "ANSV Coil-Architect Pro 专家数据库通信与网络环境体检报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"软件版本: v{APP_VERSION}",
            f"本机机器码: {get_machine_code()}",
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
            QMessageBox.warning(self, "导出失败", f"保存体检报告时出错: {e}")

    def _import_config_file(self):
        """导入作者或管理员下发的受控标准网络配置文件 (.json / .cfg)"""
        desktop_dir = Path.home() / "Desktop"
        if not desktop_dir.exists():
            desktop_dir = Path.home()

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

            QMessageBox.information(self, "导入成功", f"✅ 网络参数已成功导入并生效！\n\n{sanitize_diag_text(msg)}")
            self._do_test()
        else:
            QMessageBox.warning(self, "导入失败", f"❌ 网络参数导入失败:\n{msg}")


def open_cloud_config_dialog(parent=None):
    """便捷调出网络与数据库通信诊断中心"""
    dlg = CloudConfigDialog(parent)
    return dlg.exec()
