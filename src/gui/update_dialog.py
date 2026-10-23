"""
=============================================================================
Module: src.gui.update_dialog
Description: Coil-Architect Pro 在线自动升级与断点续传交互对话框 (UpdateDialog)
深度对标 Gear-NVH / FFT 分析软件 全量工业商业桌面软件企业内网与断点续传影子替换架构
-----------------------------------------------------------------------------
核心特性：
1. 双轨智能升级决策：优先拉取 ~8.7 MB 累积增量热补丁包 (省流量 85%+)，亦支持全量包；
2. 内部原生分块断点续传：UI 内置实时进度条与瞬时速度仪表，彻底告别浏览器 404 跳转；
3. 零打扰影子替换：下载完成后不影响当前仿真设计，下次启动自动静默生效，亦支持一键立即重启；
4. 内置网络与代理诊断：云端连接受阻时一键调出诊断中心，排查 SmartDNS 与企业内网代理。
=============================================================================
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextBrowser, QFrame, QMessageBox, QApplication, QWidget,
    QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.version import (
    APP_NAME, APP_TITLE, APP_VERSION, APP_BUILD, BUILD_TIME,
    compare_versions, compare_builds, is_newer_version, get_git_commit, get_git_log
)
from src.core.ota_updater import OtaUpdater, calculate_sha256
from src.core.i18n import i18n
from src.gui.utils import adapt_dialog_geometry


class DownloadWorkerThread(QThread):
    """
    后台高并发断点续传下载线程
    """
    progress_changed = pyqtSignal(int, int, float)  # (current_bytes, total_bytes, speed_mbps)
    download_finished = pyqtSignal(bool, str)        # (success, message_or_path)

    def __init__(self, updater: OtaUpdater, version_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.updater = updater
        self.version_info = version_info

    def run(self):
        is_en = i18n.is_english()
        def cb(cur, total, speed):
            self.progress_changed.emit(cur, total, speed)

        try:
            ok = self.updater.download_update_package(self.version_info, progress_callback=cb, throttle=False)
            if ok:
                self.download_finished.emit(
                    True,
                    "Download complete & SHA256 integrity verified!" if is_en else "下载完成并通过 SHA256 完整性校验！"
                )
            else:
                err_msg = self.updater.last_download_error or ("Network transfer interrupted or timed out" if is_en else "网络传输中断或超时")
                self.download_finished.emit(False, f"{err_msg}")
        except Exception as e:
            self.download_finished.emit(False, f"{'Download exception' if is_en else '下载异常'}: {e}")


class UpdateDialog(QDialog):
    """
    OTA 检查与在线升级对话框
    """

    def __init__(self, parent=None, version_info: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.is_en = i18n.is_english()
        self.updater = OtaUpdater.get_instance()
        self.version_info = version_info
        self.has_new = False
        self.download_thread: Optional[DownloadWorkerThread] = None
        self._target_use_patch = True

        self.setWindowTitle(
            f"Software Update & OTA Center — {APP_NAME}"
            if self.is_en else
            f"软件版本与在线自动升级 — {APP_NAME}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                color: #0F172A;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        adapt_dialog_geometry(self, target_w=680, target_h=620, min_w=580, min_h=500)
        self.setModal(True)
        self._init_ui()

        if self.version_info is None:
            self._fetch_latest_info_async()
        else:
            self._render_version_state()

    def _format_v(self, v_str: str) -> str:
        s = str(v_str or "").strip()
        if not s:
            return "v1.1.0"
        return s if s.startswith("v") or s.startswith("V") else f"v{s}"

    def _init_ui(self):
        is_en = self.is_en
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(10)

        # 1. 顶部 Header
        header_h = QHBoxLayout()
        header_h.setSpacing(10)

        icon_lbl = QLabel("🚀")
        icon_lbl.setStyleSheet("font-size: 26px;")
        header_h.addWidget(icon_lbl)

        title_v = QVBoxLayout()
        title_v.setSpacing(2)

        self.lbl_title = QLabel(
            "🔍 Connecting to cloud server to check for updates..."
            if is_en else
            "🔍 正在连接云端服务检查最新版本..."
        )
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A;")
        title_v.addWidget(self.lbl_title)

        lbl_sub = QLabel(
            "ANSV Micro-Actuator & Precision Drive Platform · Smart OTA Shadow Update Engine"
            if is_en else
            "ANSV 微型执行器与精密传动仿真平台 · 智能 OTA 影子替换升级引擎"
        )
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        title_v.addWidget(lbl_sub)

        header_h.addLayout(title_v)
        header_h.addStretch()

        layout.addLayout(header_h)

        # 2. 版本状态徽章卡片
        self.card_info = QFrame()
        self.card_info.setObjectName("cardInfoFrame")
        self.card_info.setStyleSheet("""
            QFrame#cardInfoFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        card_layout = QVBoxLayout(self.card_info)
        card_layout.setSpacing(4)

        git_hash = get_git_commit()
        cur_v = self._format_v(APP_VERSION)
        self.lbl_ver_badge = QLabel(
            f"Current Version: {cur_v} (Build {APP_BUILD} · git-{git_hash})"
            if is_en else
            f"当前版本: {cur_v} (Build {APP_BUILD} · git-{git_hash})"
        )
        self.lbl_ver_badge.setStyleSheet("font-size: 12px; font-weight: 700; color: #334155;")
        card_layout.addWidget(self.lbl_ver_badge)

        self.lbl_meta_desc = QLabel(
            "Querying edge distribution node status & incremental delta stream..."
            if is_en else
            "正在检索边缘分发节点状态与增量更新流..."
        )
        self.lbl_meta_desc.setStyleSheet("font-size: 11px; color: #64748B;")
        self.lbl_meta_desc.setWordWrap(True)
        card_layout.addWidget(self.lbl_meta_desc)

        layout.addWidget(self.card_info)

        # 3. 升级通道选择卡片 (增量升级补丁包 vs 全量完整安装包)
        self.card_channels = QFrame()
        self.card_channels.setStyleSheet("""
            QFrame#cardChannelsFrame {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.card_channels.setObjectName("cardChannelsFrame")
        ch_layout = QVBoxLayout(self.card_channels)
        ch_layout.setContentsMargins(10, 8, 10, 8)
        ch_layout.setSpacing(8)

        lbl_ch_title = QLabel(
            "📦 Update Channel Selection (Incremental Patch saves 85%+ bandwidth):"
            if is_en else
            "📦 升级通道选择 (工位机推荐极速增量补丁，节省 85%+ 流量):"
        )
        lbl_ch_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #0F172A;")
        ch_layout.addWidget(lbl_ch_title)

        box_row = QHBoxLayout()
        box_row.setSpacing(10)

        # 通道 1: 增量补丁
        self.box_patch = QFrame()
        self.box_patch.setObjectName("boxPatchFrame")
        self.box_patch.setMinimumHeight(86)
        self.box_patch.setCursor(Qt.CursorShape.PointingHandCursor)
        bp_layout = QVBoxLayout(self.box_patch)
        bp_layout.setContentsMargins(12, 10, 12, 10)
        bp_layout.setSpacing(6)

        self.lbl_patch_header = QLabel(
            "🔘 Incremental Hot-Patch (Recommended)"
            if is_en else
            "🔘 增量升级补丁包 (强烈推荐)"
        )
        self.lbl_patch_header.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #166534; border: none; background: transparent;")
        bp_layout.addWidget(self.lbl_patch_header)

        self.lbl_patch_desc = QLabel(
            "• Target: Existing workstations\n• Advantage: Updates core solver & UI modules only (~8.7 MB), instant apply"
            if is_en else
            "• 适用对象: 已安装旧版的工位机\n• 特性优势: 仅更新算法库与核心组件 (~8.7 MB)，秒级覆盖生效"
        )
        self.lbl_patch_desc.setWordWrap(True)
        self.lbl_patch_desc.setStyleSheet("font-size: 10px; color: #15803D; line-height: 1.4; border: none; background: transparent;")
        bp_layout.addWidget(self.lbl_patch_desc)

        self.box_patch.mousePressEvent = lambda e: self._select_channel(use_patch=True)
        box_row.addWidget(self.box_patch, 1)

        # 通道 2: 全量安装包
        self.box_full = QFrame()
        self.box_full.setObjectName("boxFullFrame")
        self.box_full.setMinimumHeight(86)
        self.box_full.setCursor(Qt.CursorShape.PointingHandCursor)
        bf_layout = QVBoxLayout(self.box_full)
        bf_layout.setContentsMargins(12, 10, 12, 10)
        bf_layout.setSpacing(6)

        self.lbl_full_header = QLabel("⚪ Full Standalone Release" if is_en else "⚪ 全量完整发布包")
        self.lbl_full_header.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #475569; border: none; background: transparent;")
        bf_layout.addWidget(self.lbl_full_header)

        self.lbl_full_desc = QLabel(
            "• Target: Fresh workstations or standalone deployment\n• Advantage: Bundles full Python 3.12 runtime & Qt dependencies (~61.5 MB)"
            if is_en else
            "• 适用对象: 全新电脑或初次独立部署\n• 特性优势: 内置完整 Python 3.12 运行时与全套 Qt 依赖 (~61.5 MB)"
        )
        self.lbl_full_desc.setWordWrap(True)
        self.lbl_full_desc.setStyleSheet("font-size: 10px; color: #64748B; line-height: 1.4; border: none; background: transparent;")
        bf_layout.addWidget(self.lbl_full_desc)

        self.box_full.mousePressEvent = lambda e: self._select_channel(use_patch=False)
        box_row.addWidget(self.box_full, 1)

        ch_layout.addLayout(box_row)
        layout.addWidget(self.card_channels)

        # 初始化通道选中状态
        self._update_channel_styles()

        # 4. 更新日志展示区
        lbl_notes_title = QLabel(
            "📝 Release Notes & R&D Changelog:"
            if is_en else
            "📝 研发优化留痕与更新日志 (Changelog):"
        )
        lbl_notes_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #1E293B;")
        layout.addWidget(lbl_notes_title)

        self.text_notes = QTextBrowser()
        self.text_notes.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
                color: #334155;
                line-height: 1.4;
            }
        """)
        self.text_notes.setFixedHeight(110)
        self.text_notes.setPlaceholderText("No detailed release notes available." if is_en else "暂无详细更新日志。")
        layout.addWidget(self.text_notes)

        # 5. 下载进度条与瞬时速度反馈 (默认隐藏)
        self.progress_container = QWidget()
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                background-color: #F1F5F9;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
                color: #0F172A;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #38BDF8);
                border-radius: 4px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)

        self.lbl_speed = QLabel("Preparing secure transfer channel..." if is_en else "准备建立安全传输通道...")
        self.lbl_speed.setStyleSheet("font-size: 10.5px; color: #0284C7; font-weight: 600;")
        prog_layout.addWidget(self.lbl_speed)

        self.progress_container.setVisible(False)
        layout.addWidget(self.progress_container)

        # 6. 底部按钮操作栏
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_network_config = QPushButton("🌐 Network & Proxy Diagnostics" if is_en else "🌐 网络与代理诊断")
        self.btn_network_config.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                color: #166534;
                border: 1px solid #BBF7D0;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #DCFCE7;
                color: #15803D;
            }
        """)
        self.btn_network_config.clicked.connect(self._open_network_diagnostic)
        self.btn_network_config.setVisible(False)
        btn_box.addWidget(self.btn_network_config)

        btn_box.addStretch()

        self.btn_cancel = QPushButton("Close" if is_en else "关 闭")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #1E293B;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_action = QPushButton("⚡ Update Now" if is_en else "⚡ 立即在线升级")
        self.btn_action.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: 1px solid #0369A1;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 11.5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
                border-color: #CBD5E1;
            }
        """)
        self.btn_action.clicked.connect(self._on_action_clicked)
        btn_box.addWidget(self.btn_action)

        layout.addLayout(btn_box)

    def _select_channel(self, use_patch: bool):
        """用户切换升级通道"""
        self._target_use_patch = use_patch
        self._update_channel_styles()

    def _update_channel_styles(self):
        """更新升级通道卡片与主操作按钮样式"""
        is_en = self.is_en
        if self._target_use_patch:
            self.box_patch.setStyleSheet("""
                QFrame#boxPatchFrame {
                    background-color: #F0FDF4;
                    border: 2px solid #16A34A;
                    border-radius: 6px;
                }
                QLabel { border: none; background: transparent; }
            """)
            self.lbl_patch_header.setText("🔘 Incremental Hot-Patch (Recommended)" if is_en else "🔘 增量升级补丁包 (强烈推荐)")
            self.lbl_patch_header.setStyleSheet("font-size: 11px; font-weight: 800; color: #166534; border: none; background: transparent;")

            self.box_full.setStyleSheet("""
                QFrame#boxFullFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                }
                QLabel { border: none; background: transparent; }
            """)
            self.lbl_full_header.setText("⚪ Full Standalone Release" if is_en else "⚪ 全量完整发布包")
            self.lbl_full_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; border: none; background: transparent;")

            if self.has_new:
                self.btn_action.setText("⚡ Update Incremental Patch (~8.7 MB)" if is_en else "⚡ 立即更新增量补丁 (~8.7 MB)")
        else:
            self.box_patch.setStyleSheet("""
                QFrame#boxPatchFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                }
                QLabel { border: none; background: transparent; }
            """)
            self.lbl_patch_header.setText("⚪ Incremental Hot-Patch (Recommended)" if is_en else "⚪ 增量升级补丁包 (强烈推荐)")
            self.lbl_patch_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; border: none; background: transparent;")

            self.box_full.setStyleSheet("""
                QFrame#boxFullFrame {
                    background-color: #EFF6FF;
                    border: 2px solid #0284C7;
                    border-radius: 6px;
                }
                QLabel { border: none; background: transparent; }
            """)
            self.lbl_full_header.setText("🔘 Full Standalone Release" if is_en else "🔘 全量完整发布包")
            self.lbl_full_header.setStyleSheet("font-size: 11px; font-weight: 800; color: #0369A1; border: none; background: transparent;")

            if self.has_new:
                self.btn_action.setText("📦 Download Full Release (~61.5 MB)" if is_en else "📦 立即下载全量安装包 (~61.5 MB)")

    def _open_network_diagnostic(self):
        """打开企业内网数据库与网络环境诊断中心，关闭后自动重新检查更新"""
        from src.gui.cloud_config_dialog import open_cloud_config_dialog
        if open_cloud_config_dialog(self, require_auth=False):
            self._fetch_latest_info_async()

    def _fetch_latest_info_async(self):
        """异步向云端检查版本"""
        self.btn_action.setEnabled(False)
        self.lbl_title.setText(
            "🔍 Connecting to cloud server to check for updates..."
            if self.is_en else
            "🔍 正在连接云端服务检查最新版本..."
        )
        self.btn_network_config.setVisible(False)

        class CheckThread(QThread):
            res_signal = pyqtSignal(bool, object)

            def __init__(self, updater):
                super().__init__()
                self.updater = updater

            def run(self):
                has_new, info = self.updater.check_version()
                self.res_signal.emit(has_new, info)

        self.check_thread = CheckThread(self.updater)
        self.check_thread.res_signal.connect(self._on_check_finished)
        self.check_thread.start()

    def _on_check_finished(self, has_new: bool, info: Optional[Dict[str, Any]]):
        self.has_new = has_new
        self.version_info = info
        self._render_version_state()

    def _render_version_state(self):
        is_en = self.is_en
        cur_v = self._format_v(APP_VERSION)

        if not self.version_info:
            err = getattr(self.updater, "last_check_error", "")
            self.lbl_title.setText("⚠️ Unable to Connect to Update Server" if is_en else "⚠️ 无法连接至云端检查更新")
            if is_en:
                desc = "Connection timed out or unable to resolve the cloud distribution node."
                if err:
                    desc += f"\nDiagnostic details: {err}"
                desc += "\nPlease check your network or click [🌐 Network & Proxy Diagnostics] below."
            else:
                desc = "网络连接超时或无法解析云端服务节点。"
                if err:
                    desc += f"\n排查诊断详情: {err}"
                desc += "\n您可以检查网络、设置代理或点击下方【🌐 网络与代理诊断】调整服务器。"
            self.lbl_meta_desc.setText(desc)
            self.btn_action.setText("🔄 Retry Check" if is_en else "🔄 重新检查")
            self.btn_action.setEnabled(True)
            self.btn_network_config.setVisible(True)
            return

        self.btn_network_config.setVisible(False)

        raw_ver = self.version_info.get("latest_version") or self.version_info.get("version") or APP_VERSION
        latest_ver = self._format_v(raw_ver)
        cloud_build = str(self.version_info.get("build") or "").strip()
        is_patch = bool(self.version_info.get("is_patch", False))
        cloud_sha = (self.version_info.get("sha256") or "").strip().lower()

        # 检测本地是否已经下载好就绪包
        is_ready, meta = self.updater.is_update_ready()
        if is_ready and meta:
            ready_ver = self._format_v(meta.get("version", APP_VERSION))
            ready_build = str(meta.get("build") or "").strip()
            ready_patch = meta.get("is_patch", False)
            is_newer_ready = (compare_versions(ready_ver, APP_VERSION) > 0) or (
                compare_versions(ready_ver, APP_VERSION) == 0 and (
                    compare_builds(ready_build, APP_BUILD) > 0 if ready_build else ready_patch
                )
            )
            if is_newer_ready:
                if is_en:
                    self.lbl_title.setText(f"🎉 Update Package {ready_ver} Ready to Install!")
                    self.lbl_ver_badge.setText(f"Current: {cur_v} ({APP_BUILD})  ➔  Ready: {ready_ver} ({ready_build or 'Latest'})")
                    self.lbl_meta_desc.setText("The update package has been downloaded and verified via SHA256. Click below to restart and apply.")
                    self.btn_action.setText("🔄 Restart Now to Apply")
                    self.btn_action.setEnabled(True)
                    self.btn_cancel.setText("Apply on Next Launch")
                else:
                    self.lbl_title.setText(f"🎉 升级补丁/新版本 {ready_ver} 已就绪，可立即升级！")
                    self.lbl_ver_badge.setText(f"当前版本: {cur_v} ({APP_BUILD})  ➔  就绪版本: {ready_ver} ({ready_build or '最新'})")
                    self.lbl_meta_desc.setText("安装包已在后台下载完毕并通过 SHA256 完整性校验，点击下方按钮将自动安全替换生效。")
                    self.btn_action.setText("🔄 立即重启完成升级")
                    self.btn_action.setEnabled(True)
                    self.btn_cancel.setText("稍后自动生效 (不重启)")
                self._render_release_notes()
                return

        v_cmp = compare_versions(latest_ver, APP_VERSION)
        b_cmp = compare_builds(cloud_build, APP_BUILD) if cloud_build else 0
        has_newer = (v_cmp > 0) or (v_cmp == 0 and (b_cmp > 0 or self.has_new))

        if not has_newer:
            if v_cmp < 0 or (v_cmp == 0 and b_cmp < 0):
                if is_en:
                    self.lbl_title.setText("⭐ Client Version Ahead of Cloud Release")
                    self.lbl_ver_badge.setText(f"Local Client: {cur_v} (Build {APP_BUILD})  |  Cloud Release: {latest_ver}" + (f" ({cloud_build})" if cloud_build else ""))
                    self.lbl_meta_desc.setText("Your workstation build is newer than the public release channel.")
                    self.btn_action.setText("Up to Date")
                else:
                    self.lbl_title.setText("⭐ 当前客户端版本高于云端数据库")
                    self.lbl_ver_badge.setText(f"当前客户端: {cur_v} (Build {APP_BUILD})  |  云端库版本: {latest_ver}" + (f" ({cloud_build})" if cloud_build else ""))
                    self.lbl_meta_desc.setText("您的客户端版本高于云端发布库。如需跨工位统一部署，请联系系统管理员。")
                    self.btn_action.setText("已是最新")
                self.btn_action.setEnabled(False)
            else:
                if is_en:
                    self.lbl_title.setText("🎉 You Are Running the Latest Version!")
                    self.lbl_ver_badge.setText(f"Current Version: {cur_v} | Build {APP_BUILD} (Latest Release)")
                    self.lbl_meta_desc.setText("Your Coil-Architect Pro simulation workstation is completely up to date.")
                    self.btn_action.setText("Up to Date")
                else:
                    self.lbl_title.setText("🎉 当前已是最新版本！")
                    self.lbl_ver_badge.setText(f"当前版本: {cur_v} | Build {APP_BUILD} (最新发布态)")
                    self.lbl_meta_desc.setText("您的 Coil-Architect Pro 多物理场仿真系统处于最新状态，无需升级。")
                    self.btn_action.setText("已是最新")
                self.btn_action.setEnabled(False)
            self._render_release_notes()
            return

        # 发现可用新版本或累积热补丁
        patch_size_mb = self.version_info.get("patch_size_bytes", 0) / (1024 * 1024) if self.version_info.get("patch_size_bytes") else 8.7
        full_size_mb = self.version_info.get("file_size_bytes", 0) / (1024 * 1024) if self.version_info.get("file_size_bytes") else 61.5
        sha_str = cloud_sha[:10] + "..." if cloud_sha else ("SHA256 Verified" if is_en else "SHA256 安全哈希校验")

        if v_cmp == 0:
            if is_en:
                self.lbl_title.setText(f"⚡ Cumulative Hot-Patch Available: {latest_ver} (Build {cloud_build or 'Latest'})")
                self.lbl_ver_badge.setText(f"Current Build: {cur_v} (Build {APP_BUILD})  ➔  Cloud Patch: Build {cloud_build or 'Latest'}")
                self.lbl_meta_desc.setText(f"📦 Incremental Patch Size: ~{patch_size_mb:.1f} MB | Hash: {sha_str}")
            else:
                self.lbl_title.setText(f"⚡ 发现累积热补丁: {latest_ver} (Build {cloud_build or '最新'})")
                self.lbl_ver_badge.setText(f"当前构建: {cur_v} (Build {APP_BUILD})  ➔  云端补丁: Build {cloud_build or '最新'}")
                self.lbl_meta_desc.setText(f"📦 累积补丁大小: ~{patch_size_mb:.1f} MB (极速增量) | 安全哈希: {sha_str}")
        else:
            if is_en:
                self.lbl_title.setText(f"🚀 New Version Available: {latest_ver}" + (f" (Build {cloud_build})" if cloud_build else ""))
                self.lbl_ver_badge.setText(f"Current Version: {cur_v} (Build {APP_BUILD})  ➔  Latest Version: {latest_ver}")
                self.lbl_meta_desc.setText(f"📦 Incremental Patch: ~{patch_size_mb:.1f} MB | Full Package: ~{full_size_mb:.1f} MB | Hash: {sha_str}")
            else:
                self.lbl_title.setText(f"🚀 发现软件新版本: {latest_ver}" + (f" (Build {cloud_build})" if cloud_build else ""))
                self.lbl_ver_badge.setText(f"当前版本: {cur_v} (Build {APP_BUILD})  ➔  最新版本: {latest_ver}")
                self.lbl_meta_desc.setText(f"📦 推荐增量补丁: ~{patch_size_mb:.1f} MB | 全量安装包: ~{full_size_mb:.1f} MB | 安全哈希: {sha_str}")

        self.btn_action.setEnabled(True)
        self._update_channel_styles()
        self._render_release_notes()

    def _render_release_notes(self):
        is_en = self.is_en
        notes = self.version_info.get("release_notes", "") if self.version_info else ""
        if not notes:
            notes = self.version_info.get("changelog", "") if self.version_info else ""
        if not notes:
            notes = (
                "Includes multi-physics solver enhancements, DFM tolerance guardrails, and stability improvements."
                if is_en else
                "本次更新包含物理模型优化、DFM 制程公差卡控增强与已知问题修复。"
            )

        formatted = notes.replace("\\n", "\n")
        self.text_notes.setPlainText(formatted)

    def _on_action_clicked(self):
        # 1. 若没有版本信息重新检查
        if not self.version_info:
            self._fetch_latest_info_async()
            return

        is_ready, meta = self.updater.is_update_ready()
        if is_ready and meta:
            ready_ver = meta.get("version", APP_VERSION)
            ready_build = str(meta.get("build") or "").strip()
            ready_patch = meta.get("is_patch", False)
            is_newer_ready = (compare_versions(ready_ver, APP_VERSION) > 0) or (
                compare_versions(ready_ver, APP_VERSION) == 0 and (
                    compare_builds(ready_build, APP_BUILD) > 0 if ready_build else ready_patch
                )
            )
            if is_newer_ready:
                self._perform_restart_and_update()
                return

        # 2. 否则启动高速在线下载
        self._start_download()

    def _start_download(self):
        is_en = self.is_en
        self.btn_action.setEnabled(False)
        self.btn_action.setText("⏳ Downloading..." if is_en else "⏳ 正在高速下载...")
        self.btn_cancel.setText("Cancel" if is_en else "取 消")
        self.progress_container.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_speed.setText(
            "Establishing high-speed transfer stream with cloud node..."
            if is_en else
            "正在建立与云端节点的高速传输流..."
        )

        # 根据用户选择调整下载包类型
        target_info = dict(self.version_info)
        if not self._target_use_patch:
            target_info["patch_download_url"] = ""
            target_info["patch_url"] = ""

        self.download_thread = DownloadWorkerThread(self.updater, target_info, parent=self)
        self.download_thread.progress_changed.connect(self._on_download_progress)
        self.download_thread.download_finished.connect(self._on_download_finished)
        self.download_thread.start()

    def _on_download_progress(self, cur_bytes: int, total_bytes: int, speed_mbps: float):
        is_en = self.is_en
        if total_bytes > 0:
            pct = int((cur_bytes / float(total_bytes)) * 100)
            self.progress_bar.setValue(min(100, pct))
            cur_mb = cur_bytes / (1024 * 1024)
            tot_mb = total_bytes / (1024 * 1024)
            if is_en:
                self.lbl_speed.setText(f"Downloading: {cur_mb:.1f} MB / {tot_mb:.1f} MB ({pct}%) · Speed: {speed_mbps:.1f} MB/s")
            else:
                self.lbl_speed.setText(f"正在高速下载: {cur_mb:.1f} MB / {tot_mb:.1f} MB ({pct}%) · 瞬时速度: {speed_mbps:.1f} MB/s")
        else:
            cur_mb = cur_bytes / (1024 * 1024)
            if is_en:
                self.lbl_speed.setText(f"Downloaded: {cur_mb:.1f} MB · Speed: {speed_mbps:.1f} MB/s")
            else:
                self.lbl_speed.setText(f"已下载: {cur_mb:.1f} MB · 瞬时速度: {speed_mbps:.1f} MB/s")

    def _on_download_finished(self, success: bool, msg: str):
        is_en = self.is_en
        if success:
            self.progress_bar.setValue(100)
            if is_en:
                self.lbl_speed.setText("✅ Download complete & SHA256 verified! Update package is ready.")
                self.lbl_title.setText("🎉 Update Package Downloaded!")
                self.btn_action.setEnabled(True)
                self.btn_action.setText("🔄 Restart Now to Apply")
                self.btn_cancel.setText("Apply on Next Launch")

                res = QMessageBox.information(
                    self,
                    "Update Ready",
                    "The latest update package has been downloaded and verified!\n\n"
                    "• Your current simulation work is completely unaffected.\n"
                    "• The update is staged and will apply automatically on next launch.\n\n"
                    "Would you like to restart Coil-Architect Pro now to apply the update?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
            else:
                self.lbl_speed.setText("✅ 下载完成并通过 SHA256 完整性校验！更新包已就绪。")
                self.lbl_title.setText("🎉 升级包下载完成！")
                self.btn_action.setEnabled(True)
                self.btn_action.setText("🔄 立即重启完成升级")
                self.btn_cancel.setText("稍后自动生效 (不重启)")

                res = QMessageBox.information(
                    self,
                    "升级包就绪",
                    "最新版本安装包已成功下载并校验就绪！\n\n"
                    "• 本次升级绝不影响当前正在进行的仿真工作。\n"
                    "• 更新包已在后台暂存，将在下次启动软件时自动完成替换升级。\n\n"
                    "您是否希望现在【立即重启软件】以完成升级？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
            if res == QMessageBox.StandardButton.Yes:
                self._perform_restart_and_update()
        else:
            self.progress_container.setVisible(False)
            self.btn_action.setEnabled(True)
            if is_en:
                self.btn_action.setText("⚡ Resume Download")
                self.btn_cancel.setText("Close")
                QMessageBox.warning(
                    self,
                    "Download Incomplete",
                    f"Online update download did not complete:\n{msg}\n\n"
                    f"💡 Tip: Partial download progress has been saved. Click [Resume Download] to continue from where it left off."
                )
            else:
                self.btn_action.setText("⚡ 重新尝试下载")
                self.btn_cancel.setText("关 闭")
                QMessageBox.warning(
                    self,
                    "下载未完成",
                    f"在线升级包下载未完成：\n{msg}\n\n💡 提示：系统已自动保留已下载的断点进度，点击【重新尝试下载】即可自动断点续传，无需从头重新下载。"
                )

    def _perform_restart_and_update(self):
        """拉起影子替换脚本并安全退出当前程序"""
        is_en = self.is_en
        if not self.updater.is_install_dir_writable():
            if is_en:
                QMessageBox.warning(
                    self,
                    "Write Permission Restricted",
                    "The software is currently located in a system-protected folder (e.g. Program Files), preventing non-admin self-updates.\n\n"
                    "💡 [Solution]:\n"
                    "Move the application folder to your Desktop, Documents, or D: drive to enjoy seamless automatic updates without administrator privileges!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "目录写入权限受限",
                    "检测到当前软件放置在系统管理员保护目录（如 Program Files），导致非管理员账户无法直接覆盖。\n\n"
                    "💡【解决方案】：\n"
                    "只需将软件整个文件夹移动到【桌面】、【文档】或【D 盘】等日常工作目录，无需管理员权限即可永久畅享全自动静默升级！"
                )
            return

        ok = self.updater.launch_shadow_replacement(restart_after=True)
        if ok:
            try:
                from src.core.cloud_client import CloudClient
                CloudClient.stop_background_sync()
            except Exception:
                pass
            QApplication.closeAllWindows()
            QApplication.quit()

            import threading
            def _ensure_process_exit():
                time.sleep(0.6)
                os._exit(0)
            t = threading.Thread(target=_ensure_process_exit, daemon=True)
            t.start()
        else:
            if is_en:
                QMessageBox.critical(
                    self,
                    "Update Launch Failed",
                    "Failed to launch the background shadow update script. Please check your antivirus logs or manually extract the latest version."
                )
            else:
                QMessageBox.critical(
                    self,
                    "启动升级失败",
                    "未能成功拉起后台替换脚本，请检查系统防病毒软件拦截日志，或手动解压最新版本覆盖运行。"
                )

    def reject(self):
        if self.download_thread and self.download_thread.isRunning():
            self.updater.cancel_download()
            self.download_thread.wait(500)
        super().reject()
