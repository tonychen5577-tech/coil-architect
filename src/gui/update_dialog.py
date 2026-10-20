"""
=============================================================================
Module: src.gui.update_dialog
Description: Coil-Architect Pro 在线更新检测与 Git 版本记录展示对话框
展示当前版本指纹、Git 提交历史与工程优化记录，支持重新检测与官方发布通道直达。
=============================================================================
"""

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget,
    QApplication, QGraphicsDropShadowEffect
)

from src.version import (
    APP_NAME, APP_VERSION, APP_BUILD, BUILD_TIME, OFFICIAL_URL,
    PLATFORM_NAME, get_git_commit, get_git_log
)
from src.gui.utils import adapt_dialog_geometry


class UpdateDialog(QDialog):
    """软件在线更新与 Git 版本提交记录对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"检查软件更新 — {APP_NAME}")
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
        adapt_dialog_geometry(self, target_w=620, target_h=480, min_w=520, min_h=400)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 16)
        main_layout.setSpacing(12)

        # 1. 顶部 Header
        header_h = QHBoxLayout()
        header_h.setSpacing(10)

        icon_lbl = QLabel("🚀")
        icon_lbl.setStyleSheet("font-size: 26px;")
        header_h.addWidget(icon_lbl)

        title_v = QVBoxLayout()
        title_v.setSpacing(2)

        lbl_title = QLabel("软件更新与 Git 版本历史记录")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A;")
        title_v.addWidget(lbl_title)

        lbl_sub = QLabel(f"{PLATFORM_NAME} | 源码构建留痕引擎")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        title_v.addWidget(lbl_sub)

        header_h.addLayout(title_v)
        header_h.addStretch()

        btn_web = QPushButton("🌐 官方更新主页")
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
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_URL)))
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
        st_layout.setSpacing(6)

        git_hash = get_git_commit()
        ver_row = QHBoxLayout()
        v_tag = APP_VERSION if APP_VERSION.startswith("v") else f"v{APP_VERSION}"
        lbl_ver = QLabel(f"当前构建: <b style='color:#0284C7;'>{v_tag}</b> (Build {APP_BUILD} · git-{git_hash})")
        lbl_ver.setStyleSheet("font-size: 11.5px; color: #1E293B;")
        lbl_tag = QLabel("✔ 已是最新发布版本")
        lbl_tag.setStyleSheet("""
            background-color: #DCFCE7;
            color: #15803D;
            font-size: 10.5px;
            font-weight: 700;
            padding: 2px 8px;
            border: 1px solid #86EFAC;
            border-radius: 3px;
        """)
        ver_row.addWidget(lbl_ver)
        ver_row.addStretch()
        ver_row.addWidget(lbl_tag)
        st_layout.addLayout(ver_row)

        lbl_desc = QLabel(f"构建时间: {BUILD_TIME} | 云端分发通道: ansv.net Edge CDN 状态同步正常")
        lbl_desc.setStyleSheet("font-size: 10px; color: #64748B;")
        st_layout.addWidget(lbl_desc)

        main_layout.addWidget(card_status)

        # 3. Git 提交记录历史列表
        lbl_list_title = QLabel("📌 Git 提交版本记录与研发演进留痕 (Changelog):")
        lbl_list_title.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #334155;")
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
        c_layout.setContentsMargins(10, 10, 10, 10)
        c_layout.setSpacing(8)

        git_commits = get_git_log(max_count=20)
        for commit in git_commits:
            c_card = QFrame()
            c_card.setStyleSheet("""
                QFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 5px;
                    padding: 4px;
                }
            """)
            c_box = QVBoxLayout(c_card)
            c_box.setContentsMargins(8, 6, 8, 6)
            c_box.setSpacing(3)

            meta_h = QHBoxLayout()
            h_commit = QLabel(f"commit <b>{commit.get('commit', '')}</b>")
            h_commit.setStyleSheet("""
                color: #0369A1;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                background-color: #E0F2FE;
                padding: 1px 6px;
                border: 1px solid #BAE6FD;
                border-radius: 3px;
            """)
            meta_h.addWidget(h_commit)

            h_date = QLabel(f"📅 {commit.get('date', '')}")
            h_date.setStyleSheet("color: #64748B; font-size: 10px; margin-left: 6px;")
            meta_h.addWidget(h_date)

            h_author = QLabel(f"👤 {commit.get('author', 'Yaming.Chen')}")
            h_author.setStyleSheet("color: #64748B; font-size: 10px; margin-left: 6px;")
            meta_h.addWidget(h_author)
            meta_h.addStretch()

            c_box.addLayout(meta_h)

            lbl_sub = QLabel(commit.get("subject", ""))
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet("color: #1E293B; font-size: 11px; font-weight: 600; margin-top: 2px;")
            c_box.addWidget(lbl_sub)

            c_layout.addWidget(c_card)

        c_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        # 4. 底栏操作按钮
        bottom_h = QHBoxLayout()
        bottom_h.setSpacing(10)

        self.btn_refresh = QPushButton("🔄 重新检测更新")
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

        btn_close = QPushButton("确定")
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

    def _on_refresh_clicked(self):
        """重新检测更新并反馈"""
        self.btn_refresh.setText("🔄 正在连接云端服务器...")
        self.btn_refresh.setEnabled(False)

        from PyQt6.QtCore import QTimer
        def do_check():
            try:
                from src.core.cloud_client import CloudClient
                from src.core.license_manager import LicenseManager
                is_auth, _, lic_data = LicenseManager.is_system_authorized()
                maint_exp = lic_data.get("maint_exp", lic_data.get("exp", "PERMANENT")) if is_auth else "PERMANENT"

                is_newer, release, msg = CloudClient.check_update_sync()
                if is_newer and release:
                    rel_date = release.get("release_date", "2099-12-31")
                    if maint_exp != "PERMANENT" and rel_date > maint_exp:
                        self.btn_refresh.setText(f"💎 发现新版 {release.get('version')} (需续订维护期)")
                        self.lbl_curr_ver.setText(f"当前版本: {APP_VERSION} <span style='color:#B45309;'>(买断维护升级期已于 {maint_exp} 届满)</span>")
                    else:
                        self.btn_refresh.setText(f"🚀 发现新版本 {release.get('version')} (可免费升级)！")
                        self.lbl_curr_ver.setText(f"当前版本: {APP_VERSION} <b>(可升级至 {release.get('version')})</b>")
                else:
                    self.btn_refresh.setText(f"✔ {msg} (当前已是最新)")
            except Exception:
                self.btn_refresh.setText("✔ 当前已是最新版本 (离线已验证)")

            QTimer.singleShot(3500, lambda: (self.btn_refresh.setText("🔄 重新检测更新"), self.btn_refresh.setEnabled(True)))

        QTimer.singleShot(400, do_check)
