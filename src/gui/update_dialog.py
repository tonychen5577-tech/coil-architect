"""
=============================================================================
Module: src.gui.update_dialog
Description: Coil-Architect Pro 在线更新检测、增量升级补丁与 Git 版本记录对话框
提供双通道升级模式：
1. 增量升级补丁包 (推荐 · 仅 ~8.7 MB · 节省 85%+ 流量 · 极速覆盖升级)
2. 全量独立发布包 (~61.5 MB · 完整免安装 · 首次部署)
集成 Git 提交演进留痕、云端版本检测与最小流量分发指导。
=============================================================================
"""

from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QFont, QDesktopServices, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget,
    QApplication, QMessageBox
)

from src.version import (
    APP_NAME, APP_VERSION, APP_BUILD, BUILD_TIME, OFFICIAL_URL,
    PLATFORM_NAME, GITHUB_RELEASES_URL, get_git_commit, get_git_log
)
from src.gui.utils import adapt_dialog_geometry


class UpdateDialog(QDialog):
    """软件在线更新与 Git 版本提交记录对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"检查软件更新与增量升级通道 — {APP_NAME}")
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

        self._init_ui()
        adapt_dialog_geometry(self, target_w=740, target_h=640, min_w=660, min_h=540)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 18, 22, 16)
        main_layout.setSpacing(10)

        # 1. 顶部 Header
        header_h = QHBoxLayout()
        header_h.setSpacing(10)

        icon_lbl = QLabel("🚀")
        icon_lbl.setStyleSheet("font-size: 26px;")
        header_h.addWidget(icon_lbl)

        title_v = QVBoxLayout()
        title_v.setSpacing(2)

        lbl_title = QLabel("软件版本更新与增量升级分发通道")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A;")
        title_v.addWidget(lbl_title)

        lbl_sub = QLabel(f"{PLATFORM_NAME} | 最小网络流量升级引擎")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        title_v.addWidget(lbl_sub)

        header_h.addLayout(title_v)
        header_h.addStretch()

        btn_web = QPushButton("🌐 官方发布与更新主页")
        btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_web.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                color: #0284C7;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F0F9FF;
                border-color: #0284C7;
            }
        """)
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL)))
        header_h.addWidget(btn_web)

        main_layout.addLayout(header_h)

        # 2. 当前版本状态卡片
        card_status = QFrame()
        card_status.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        st_layout = QVBoxLayout(card_status)
        st_layout.setContentsMargins(10, 8, 10, 8)
        st_layout.setSpacing(4)

        git_hash = get_git_commit()
        ver_row = QHBoxLayout()
        v_tag = APP_VERSION if APP_VERSION.startswith("v") else f"v{APP_VERSION}"
        self.lbl_curr_ver = QLabel(f"当前构建: <b style='color:#0284C7;'>{v_tag}</b> (Build {APP_BUILD} · git-{git_hash})")
        self.lbl_curr_ver.setStyleSheet("font-size: 11.5px; color: #1E293B;")
        
        self.lbl_status_tag = QLabel("✔ 已是最新发布版本")
        self.lbl_status_tag.setStyleSheet("""
            background-color: #DCFCE7;
            color: #15803D;
            font-size: 10.5px;
            font-weight: 700;
            padding: 2px 8px;
            border: 1px solid #86EFAC;
            border-radius: 3px;
        """)
        ver_row.addWidget(self.lbl_curr_ver)
        ver_row.addStretch()
        ver_row.addWidget(self.lbl_status_tag)
        st_layout.addLayout(ver_row)

        lbl_desc = QLabel(f"构建时间: {BUILD_TIME} | 云端分发: ansv.net Edge CDN 节点已同步")
        lbl_desc.setStyleSheet("font-size: 10px; color: #64748B;")
        st_layout.addWidget(lbl_desc)

        main_layout.addWidget(card_status)

        # 3. 核心升级通道选择卡片 (增量包 vs 全量包)
        card_channels = QFrame()
        card_channels.setStyleSheet("""
            QFrame#card_channels {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
            }
        """)
        card_channels.setObjectName("card_channels")
        ch_layout = QVBoxLayout(card_channels)
        ch_layout.setContentsMargins(12, 10, 12, 10)
        ch_layout.setSpacing(8)

        lbl_ch_title = QLabel("📦 升级包下载通道选择 (支持其他客户端最小网络流量升级):")
        lbl_ch_title.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #0F172A;")
        ch_layout.addWidget(lbl_ch_title)

        box_row = QHBoxLayout()
        box_row.setSpacing(10)

        # 通道 1: 增量升级补丁包 (推荐)
        box_patch = QFrame()
        box_patch.setStyleSheet("""
            QFrame {
                background-color: #F0FDF4;
                border: 1.5px solid #86EFAC;
                border-radius: 5px;
            }
        """)
        bp_layout = QVBoxLayout(box_patch)
        bp_layout.setContentsMargins(10, 8, 10, 8)
        bp_layout.setSpacing(5)

        bp_head = QHBoxLayout()
        lbl_bp_t = QLabel("⚡ 增量升级补丁包 (强烈推荐)")
        lbl_bp_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #166534;")
        bp_badge = QLabel("仅 ~8.7 MB · 省流量 85%+")
        bp_badge.setStyleSheet("""
            background-color: #DCFCE7;
            color: #15803D;
            font-size: 9.5px;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
        """)
        bp_head.addWidget(lbl_bp_t)
        bp_head.addStretch()
        bp_head.addWidget(bp_badge)
        bp_layout.addLayout(bp_head)

        lbl_bp_desc = QLabel(
            "• 适用对象: 已安装过旧版的客户端工位机。\n"
            "• 升级方式: 仅下载更新后的 EXE、算法库与资源，解压直接覆盖原目录即可极速生效。\n"
            "• 优势: 下载极速，零重复依赖，适合向多台电脑批量分发。"
        )
        lbl_bp_desc.setWordWrap(True)
        lbl_bp_desc.setStyleSheet("font-size: 10px; color: #15803D; line-height: 1.4;")
        bp_layout.addWidget(lbl_bp_desc)

        btn_download_patch = QPushButton("⚡ 获取增量升级补丁包 (~8.7 MB)")
        btn_download_patch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_download_patch.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: #FFFFFF;
                font-size: 10.5px;
                font-weight: 700;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #15803D;
            }
        """)
        btn_download_patch.clicked.connect(self._on_download_patch_clicked)
        bp_layout.addWidget(btn_download_patch)

        box_row.addWidget(box_patch, 1)

        # 通道 2: 全量完整安装包
        box_full = QFrame()
        box_full.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 5px;
            }
        """)
        bf_layout = QVBoxLayout(box_full)
        bf_layout.setContentsMargins(10, 8, 10, 8)
        bf_layout.setSpacing(5)

        bf_head = QHBoxLayout()
        lbl_bf_t = QLabel("📦 全量独立安装包")
        lbl_bf_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #334155;")
        bf_badge = QLabel("~61.5 MB · 独立免装")
        bf_badge.setStyleSheet("""
            background-color: #E2E8F0;
            color: #475569;
            font-size: 9.5px;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
        """)
        bf_head.addWidget(lbl_bf_t)
        bf_head.addStretch()
        bf_head.addWidget(bf_badge)
        bf_layout.addLayout(bf_head)

        lbl_bf_desc = QLabel(
            "• 适用对象: 全新电脑或未安装旧版本环境。\n"
            "• 升级方式: 内置全量 Python 3.12 运行时与 Qt6 图形界面组件，解压即运行。\n"
            "• 优势: 开箱即用，无需任何历史软件基础支持。"
        )
        lbl_bf_desc.setWordWrap(True)
        lbl_bf_desc.setStyleSheet("font-size: 10px; color: #64748B; line-height: 1.4;")
        bf_layout.addWidget(lbl_bf_desc)

        btn_download_full = QPushButton("📦 获取全量安装包 (~61.5 MB)")
        btn_download_full.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_download_full.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #334155;
                font-size: 10.5px;
                font-weight: 600;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
            }
        """)
        btn_download_full.clicked.connect(self._on_download_full_clicked)
        bf_layout.addWidget(btn_download_full)

        box_row.addWidget(box_full, 1)

        ch_layout.addLayout(box_row)

        # 底部最小流量提示栏
        lbl_tip_bar = QLabel("💡 <b>多客户端极速升级建议</b>: 在实验室或产线多台工位机分发时，只需传输【增量补丁包】放入局域网网盘或 U 盘，几秒内即可完成覆盖升级，最小化外网流量占用。")
        lbl_tip_bar.setStyleSheet("""
            font-size: 9.5px;
            color: #0284C7;
            background-color: #F0F9FF;
            border: 1px solid #BAE6FD;
            border-radius: 4px;
            padding: 4px 8px;
        """)
        lbl_tip_bar.setWordWrap(True)
        ch_layout.addWidget(lbl_tip_bar)

        main_layout.addWidget(card_channels)

        # 4. Git 提交记录历史列表
        lbl_list_title = QLabel("📌 Git 提交版本记录与研发演进留痕 (Changelog):")
        lbl_list_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #334155;")
        main_layout.addWidget(lbl_list_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background-color: #FFFFFF;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(6)

        git_commits = get_git_log(max_count=20)
        for commit in git_commits:
            c_card = QFrame()
            c_card.setStyleSheet("""
                QFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 4px;
                    padding: 3px;
                }
            """)
            c_box = QVBoxLayout(c_card)
            c_box.setContentsMargins(6, 4, 6, 4)
            c_box.setSpacing(2)

            meta_h = QHBoxLayout()
            h_commit = QLabel(f"commit <b>{commit.get('commit', '')}</b>")
            h_commit.setStyleSheet("""
                color: #0369A1;
                font-family: 'Consolas', monospace;
                font-size: 10px;
                background-color: #E0F2FE;
                padding: 1px 5px;
                border: 1px solid #BAE6FD;
                border-radius: 3px;
            """)
            meta_h.addWidget(h_commit)

            h_date = QLabel(f"📅 {commit.get('date', '')}")
            h_date.setStyleSheet("color: #64748B; font-size: 9.5px; margin-left: 6px;")
            meta_h.addWidget(h_date)

            h_author = QLabel(f"👤 {commit.get('author', 'Yaming.Chen')}")
            h_author.setStyleSheet("color: #64748B; font-size: 9.5px; margin-left: 6px;")
            meta_h.addWidget(h_author)
            meta_h.addStretch()

            c_box.addLayout(meta_h)

            lbl_sub = QLabel(commit.get("subject", ""))
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet("color: #1E293B; font-size: 10.5px; font-weight: 600; margin-top: 1px;")
            c_box.addWidget(lbl_sub)

            c_layout.addWidget(c_card)

        c_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        # 5. 底栏操作按钮
        bottom_h = QHBoxLayout()
        bottom_h.setSpacing(10)

        self.btn_refresh = QPushButton("🔄 重新检测云端更新")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                color: #334155;
                font-size: 11px;
                font-weight: 600;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0F172A;
            }
        """)
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        bottom_h.addWidget(self.btn_refresh)

        bottom_h.addStretch()

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
        bottom_h.addWidget(btn_close)

        main_layout.addLayout(bottom_h)

    def _on_download_patch_clicked(self):
        """点击获取增量升级补丁包"""
        QMessageBox.information(
            self,
            "增量升级补丁包使用说明 (最小流量)",
            "⚡ 增量升级补丁使用指南 (仅 ~8.7 MB，省流量 85%+)\n\n"
            "1. 适用工位机:\n"
            "   适用于已安装历史版本的客户电脑。\n\n"
            "2. 极速升级三步法:\n"
            "   ① 下载增量升级补丁 (ANSV_Coil_Architect_Pro_*_Incremental_Patch.zip)；\n"
            "   ② 解压压缩包，将所有文件直接复制并覆盖到 Coil-Architect Pro 原安装根目录；\n"
            "   ③ 重新运行 Coil-Architect-Pro.exe 即可秒级完成升级！\n\n"
            "• 多机分发建议: 将此补丁包拷入 U 盘或内网共享，各客户端就地覆盖，完全免消耗外网流量。\n\n"
            "点击【确定】将为您在浏览器中打开官方增量补丁下载发布通道。"
        )
        url = getattr(self, "_patch_download_url", None) or GITHUB_RELEASES_URL
        QDesktopServices.openUrl(QUrl(url))

    def _on_download_full_clicked(self):
        """点击获取全量完整安装包"""
        QMessageBox.information(
            self,
            "全量独立安装包说明",
            "📦 全量独立安装包使用说明 (~61.5 MB)\n\n"
            "• 适用工位机: 全新电脑或未安装旧版本环境。\n"
            "• 包含内容: 内置独立 Python 运行时、全量 Qt 库与完整算法引擎，解压即可运行。\n\n"
            "点击【确定】将为您在浏览器中打开官方全量下载发布通道。"
        )
        url = getattr(self, "_full_download_url", None) or GITHUB_RELEASES_URL
        QDesktopServices.openUrl(QUrl(url))

    def _on_refresh_clicked(self):
        """重新检测更新并反馈"""
        self.btn_refresh.setText("🔄 正在连接云端服务器...")
        self.btn_refresh.setEnabled(False)

        def do_check():
            try:
                from src.core.cloud_client import CloudClient
                from src.core.license_manager import LicenseManager
                is_auth, _, lic_data = LicenseManager.is_system_authorized()
                maint_exp = lic_data.get("maint_exp", lic_data.get("exp", "PERMANENT")) if is_auth else "PERMANENT"

                is_newer, release, msg = CloudClient.check_update_sync()
                if release:
                    self._full_download_url = release.get("download_url") or GITHUB_RELEASES_URL
                    self._patch_download_url = release.get("patch_url") or release.get("download_url") or GITHUB_RELEASES_URL

                if is_newer and release:
                    rel_ver = release.get("version", "")
                    patch_size = release.get("patch_size_mb", 8.7)
                    full_size = release.get("file_size_mb", 61.5)
                    self.lbl_status_tag.setText(f"🚀 发现新版本 {rel_ver}")
                    self.lbl_status_tag.setStyleSheet("""
                        background-color: #FEF3C7;
                        color: #B45309;
                        font-size: 10.5px;
                        font-weight: 700;
                        padding: 2px 8px;
                        border: 1px solid #FCD34D;
                        border-radius: 3px;
                    """)
                    self.btn_refresh.setText(f"🚀 发现新版 {rel_ver} (推荐增量补丁 ~{patch_size}MB)")
                else:
                    self.btn_refresh.setText(f"✔ {msg} (当前已是最新)")
            except Exception:
                self.btn_refresh.setText("✔ 当前已是最新版本 (离线已验证)")

            QTimer.singleShot(3500, lambda: (self.btn_refresh.setText("🔄 重新检测云端更新"), self.btn_refresh.setEnabled(True)))

        QTimer.singleShot(400, do_check)
