"""
=============================================================================
Module: src.gui.about_dialog
Description: ANSV 微型执行器与精密传动仿真验证平台 (Coil-Architect Pro)
16:9 SolidWorks 纯白工业测控风格“关于系统 (About)”标准对话框
功能特性：
1. 完整展示 ANSV 平台全称与 Coil-Architect Pro 工作站定义；
2. 官方微信公众号真实二维码、专属名称【ANSV微型执行器】与精炼版 5 大工程师权益；
3. 右侧系统软硬件全景信息（机器码、本机 MAC、授权工位、Git 源码指纹，严格剔除良率）；
4. 底栏操作按钮：桌面快捷方式生成、一键导出全景诊断日志包、在线检查更新（导入 Git 版本记录）。
=============================================================================
"""

import sys
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import (
    QColor, QFont, QPixmap, QDesktopServices
)
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QLineEdit,
    QMessageBox, QApplication, QGraphicsDropShadowEffect
)

from src.version import (
    APP_NAME, APP_TITLE, APP_VERSION, APP_BUILD, BUILD_TIME, OFFICIAL_URL, OFFICIAL_EMAIL, COPYRIGHT_TEXT,
    PLATFORM_NAME, PLATFORM_NAME_EN, PLATFORM_FULL_TITLE, WECHAT_OFFICIAL_ACCOUNT,
    WECHAT_CONTACT_ID, WHATSAPP_CONTACT_ID, CORE_ENGINE_AUTHOR, get_git_commit
)
from src.core.license_manager import get_machine_code, get_mac_address, get_station_info
from src.gui.icon_helper import get_app_icon, get_app_icon_pixmap, get_ansv_logo_pixmap
from src.gui.utils import adapt_dialog_geometry


class AboutDialog(QDialog):
    """
    16:9 SolidWorks 纯白工业测控风格系统关于对话框
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        from src.core.i18n import i18n
        self.is_en = i18n.is_english()
        self.setWindowTitle(
            f"About System — {PLATFORM_NAME_EN}" if self.is_en else f"关于系统 — {PLATFORM_NAME}"
        )
        self.setWindowIcon(get_app_icon())
        self.setModal(True)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #F1F5F9;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
        """)

        self._init_ui()
        adapt_dialog_geometry(self, target_w=980, target_h=600, min_w=860, min_h=540)

    def _init_ui(self):
        is_en = self.is_en
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 纯白中心卡片 (SolidWorks 经典工业卡片底色 + 浅柔投影)
        card = QWidget(self)
        card.setObjectName("aboutCard")
        card.setStyleSheet("""
            #aboutCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(15, 23, 42, 35))
        shadow.setOffset(0, 3)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 14)
        card_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. 顶部 Header (平台名称、版本号与官方网址直达)
        # -------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel()
        icon_pm = get_ansv_logo_pixmap(52)
        if not icon_pm.isNull():
            icon_label.setPixmap(icon_pm)
        header_layout.addWidget(icon_label)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)

        row_t1 = QHBoxLayout()
        row_t1.setSpacing(8)
        lbl_brand = QLabel(PLATFORM_NAME_EN if is_en else PLATFORM_NAME)
        lbl_brand.setStyleSheet("color: #0F172A; font-size: 15px; font-weight: 800; letter-spacing: 0.5px;")
        
        lbl_ver_badge = QLabel(f"{APP_VERSION}")
        lbl_ver_badge.setStyleSheet("""
            color: #0284C7;
            background-color: #E0F2FE;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border: 1px solid #BAE6FD;
            border-radius: 4px;
        """)
        row_t1.addWidget(lbl_brand)
        row_t1.addWidget(lbl_ver_badge)
        row_t1.addStretch()
        title_vbox.addLayout(row_t1)

        lbl_desc = QLabel(
            f"Micro-Coil Design & Electro-Thermal Simulation Workstation ({APP_NAME})"
            if is_en else
            f"{PLATFORM_NAME_EN} | 微型线圈设计与电热仿真工作站 ({APP_NAME})"
        )
        lbl_desc.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")
        title_vbox.addWidget(lbl_desc)

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        btn_url = QPushButton(
            f"🌐 Website: {OFFICIAL_URL.replace('https://', '')}"
            if is_en else
            f"🌐 官方网址: {OFFICIAL_URL.replace('https://', '')}"
        )
        btn_url.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_url.setToolTip(
            f"Official Portal: {OFFICIAL_URL}\nTechnical Support & Business Email: {OFFICIAL_EMAIL}"
            if is_en else
            f"官方主页: {OFFICIAL_URL}\n技术支持与商务合作邮箱: {OFFICIAL_EMAIL}"
        )
        btn_url.setStyleSheet("""
            QPushButton {
                color: #0284C7;
                font-size: 11px;
                font-weight: 600;
                padding: 5px 12px;
                background-color: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0284C7;
            }
            QPushButton:pressed {
                background-color: #BAE6FD;
            }
        """)
        btn_url.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_URL)))
        header_layout.addWidget(btn_url)

        card_layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # 2. 中间左右分栏 (左侧公众号与权益，右侧系统规格与特色)
        # -------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # === 左侧: 官方公众号、微信咨询与 WhatsApp 国际支持 (约 48% 宽度) ===
        left_box = QWidget()
        left_box.setObjectName("leftBox")
        left_box.setStyleSheet("""
            #leftBox {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
            QLabel {
                background: transparent;
            }
        """)
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(12, 10, 12, 10)
        left_layout.setSpacing(6)

        # 1. 顶部分页切换按钮组 (官方公众号 | 工程师微信 | WhatsApp)
        tab_h = QHBoxLayout()
        tab_h.setSpacing(4)

        btn_tab_official = QPushButton("📢 Official Account" if is_en else "📢 官方公众号")
        btn_tab_wechat = QPushButton("💬 WeChat Support" if is_en else "💬 微信技术咨询")
        btn_tab_whatsapp = QPushButton("🌐 WhatsApp")

        for b in [btn_tab_official, btn_tab_wechat, btn_tab_whatsapp]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    color: #475569;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 3px 6px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    color: #0F172A;
                }
            """)

        tab_h.addWidget(btn_tab_official)
        tab_h.addWidget(btn_tab_wechat)
        tab_h.addWidget(btn_tab_whatsapp)
        left_layout.addLayout(tab_h)

        # 头部卡片标题与动态复制按钮
        wc_header = QHBoxLayout()
        wc_header.setSpacing(6)
        lbl_wc_icon = QLabel("🟢 Official WeChat Account" if is_en else "🟢 官方微信公众号")
        lbl_wc_icon.setStyleSheet("font-size: 11px; font-weight: 800; color: #166534;")
        wc_header.addWidget(lbl_wc_icon)
        wc_header.addStretch()

        btn_copy_wc = QPushButton("📋 Copy ID" if is_en else "📋 复制公众号")
        btn_copy_wc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_wc.setStyleSheet("""
            QPushButton {
                color: #15803D;
                font-size: 9.5px;
                font-weight: 600;
                padding: 2px 7px;
                border: 1px solid #86EFAC;
                border-radius: 3px;
                background: #F0FDF4;
            }
            QPushButton:hover {
                background: #DCFCE7;
                color: #14532D;
            }
        """)
        wc_header.addWidget(btn_copy_wc)
        left_layout.addLayout(wc_header)

        # 二维码与信息卡片
        qr_container = QFrame()
        qr_container.setObjectName("qrContainer")
        qr_container.setStyleSheet("""
            QFrame#qrContainer {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        qr_row = QHBoxLayout(qr_container)
        qr_row.setContentsMargins(8, 6, 8, 6)
        qr_row.setSpacing(10)

        # 二维码图片
        lbl_qr_img = QLabel()
        lbl_qr_img.setFixedSize(98, 98)
        lbl_qr_img.setStyleSheet("border: 1px solid #E2E8F0; border-radius: 4px; background: #FFFFFF;")
        lbl_qr_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_row.addWidget(lbl_qr_img)

        # 二维码右侧文字说明
        qr_info_v = QVBoxLayout()
        qr_info_v.setSpacing(3)
        lbl_wc_name = QLabel(f"公众号: <b style='color:#15803D;'>{WECHAT_OFFICIAL_ACCOUNT}</b>")
        lbl_wc_name.setStyleSheet("font-size: 10.5px; color: #1E293B;")
        lbl_wc_tip = QLabel("手机微信「扫一扫」关注官方公众号")
        lbl_wc_tip.setWordWrap(True)
        lbl_wc_tip.setStyleSheet("font-size: 8.5px; color: #64748B;")
        lbl_wc_val = QLabel("关注「ANSV」官方公众号，您可以获取：")
        lbl_wc_val.setWordWrap(True)
        lbl_wc_val.setStyleSheet("font-size: 8.5px; font-weight: 700; color: #0284C7; margin-top: 1px;")

        qr_info_v.addWidget(lbl_wc_name)
        qr_info_v.addWidget(lbl_wc_tip)
        qr_info_v.addWidget(lbl_wc_val)
        qr_info_v.addStretch()
        qr_row.addLayout(qr_info_v)
        left_layout.addWidget(qr_container)

        # 定义多渠道配置
        res_dir = Path(__file__).resolve().parent.parent.parent / "resources"
        channels = {
            "official": {
                "title": "🟢 Official WeChat Account" if is_en else "🟢 官方微信公众号",
                "title_color": "#166534",
                "name_html": (
                    f"Account: <b style='color:#15803D;'>{WECHAT_OFFICIAL_ACCOUNT}</b>"
                    if is_en else
                    f"公众号: <b style='color:#15803D;'>{WECHAT_OFFICIAL_ACCOUNT}</b>"
                ),
                "copy_text": WECHAT_OFFICIAL_ACCOUNT,
                "btn_text": "📋 Copy Account" if is_en else "📋 复制公众号",
                "tip": "Scan via WeChat to follow our official engineering channel" if is_en else "手机微信「扫一扫」关注官方公众号",
                "val_title": "Follow ANSV Official Channel to unlock:" if is_en else "关注「ANSV」官方公众号，您可以获取：",
                "qr_paths": [
                    Path(r"C:\Workspace\07_AI_Work\ansv-web\static\images\official-account-qr.jpg"),
                    res_dir / "official-account-qr.jpg"
                ]
            },
            "wechat": {
                "title": "💬 Engineer WeChat Support" if is_en else "💬 工程师专属微信咨询",
                "title_color": "#0369A1",
                "name_html": (
                    f"WeChat ID: <b style='color:#0284C7;'>{WECHAT_CONTACT_ID}</b>"
                    if is_en else
                    f"微信号: <b style='color:#0284C7;'>{WECHAT_CONTACT_ID}</b>"
                ),
                "copy_text": WECHAT_CONTACT_ID,
                "btn_text": "📋 Copy WeChat ID" if is_en else "📋 复制微信号",
                "tip": "Scan via WeChat to connect with Senior Engineer (Yaming.Chen)" if is_en else "微信扫码添加工程师微信 (陈亚明 · 微型执行器)",
                "val_title": "1-on-1 engineering support, custom solver & consulting:" if is_en else "一对一技术支持、算例定制与工程咨询：",
                "qr_paths": [
                    res_dir / "wechat_personal_qr.png"
                ]
            },
            "whatsapp": {
                "title": "🌐 WhatsApp International Support",
                "title_color": "#15803D",
                "name_html": f"WhatsApp: <b style='color:#16A34A;'>{WHATSAPP_CONTACT_ID}</b>",
                "copy_text": WHATSAPP_CONTACT_ID,
                "btn_text": "📋 Copy WhatsApp" if is_en else "📋 复制 WhatsApp",
                "tip": "Scan via WhatsApp Camera (Yaming.Chen - ANSV)",
                "val_title": "Global technical support & instant consultation:",
                "qr_paths": [
                    res_dir / "whatsapp_qr.png"
                ]
            }
        }

        self._current_channel_copy = WECHAT_OFFICIAL_ACCOUNT

        def switch_channel(key: str):
            cfg = channels[key]
            lbl_wc_icon.setText(cfg["title"])
            lbl_wc_icon.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {cfg['title_color']};")
            lbl_wc_name.setText(cfg["name_html"])
            lbl_wc_tip.setText(cfg["tip"])
            lbl_wc_val.setText(cfg["val_title"])
            btn_copy_wc.setText(cfg["btn_text"])
            self._current_channel_copy = cfg["copy_text"]

            # 加载二维码
            loaded = False
            for p in cfg["qr_paths"]:
                if p.exists():
                    pix = QPixmap(str(p))
                    if not pix.isNull():
                        scaled = pix.scaled(94, 94, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        lbl_qr_img.setPixmap(scaled)
                        loaded = True
                        break
            if not loaded:
                lbl_qr_img.setText("Loading QR..." if is_en else "二维码加载中")

            # 激活状态高亮
            for b, k in [(btn_tab_official, "official"), (btn_tab_wechat, "wechat"), (btn_tab_whatsapp, "whatsapp")]:
                if k == key:
                    b.setStyleSheet("""
                        background-color: #0284C7;
                        border: 1px solid #0284C7;
                        border-radius: 4px;
                        color: #FFFFFF;
                        font-size: 10px;
                        font-weight: 700;
                        padding: 3px 6px;
                    """)
                else:
                    b.setStyleSheet("""
                        background-color: #F1F5F9;
                        border: 1px solid #CBD5E1;
                        border-radius: 4px;
                        color: #475569;
                        font-size: 10px;
                        font-weight: 600;
                        padding: 3px 6px;
                    """)

        btn_tab_official.clicked.connect(lambda: switch_channel("official"))
        btn_tab_wechat.clicked.connect(lambda: switch_channel("wechat"))
        btn_tab_whatsapp.clicked.connect(lambda: switch_channel("whatsapp"))
        btn_copy_wc.clicked.connect(lambda: self._copy_to_clipboard(self._current_channel_copy, btn_copy_wc, "Copied" if is_en else "已复制"))

        # 默认初始化：英文环境下优先展示 WhatsApp 国际通道，中文环境下展示官方公众号
        switch_channel("whatsapp" if is_en else "official")

        # 5 大权益说明 (精简版 · 条理清晰)
        benefits_v = QVBoxLayout()
        benefits_v.setSpacing(4)

        if is_en:
            benefits = [
                ("🔬", "In-Depth Multiphysics Insights", "LRA / VCM / Precision Drive coupled simulation (EM-Thermal-Mech)"),
                ("🛠️", "Exclusive Engineering Solvers", "Coil-Architect Pro & Motor-Insight dynamic verification suites"),
                ("⚠️", "Mass-Production DFM & RCA", "Spring fracture, cold solder & wire break root-cause diagnosis"),
                ("📑", "Flagship Teardowns & Patents", "Global flagship actuator structural teardowns & patent reviews"),
                ("💬", "Direct Engineer Consultation", "1-on-1 technical support via WhatsApp / WeChat & peer community")
            ]
        else:
            benefits = [
                ("🔬", "硬核技术深度拆解", "LRA / VCM / 传动多物理场仿真（电-磁-热-力）与一线复盘"),
                ("🛠️", "独家工程工具与算例", "Coil-Architect 线圈解算器、Motor-Insight 动力学工具"),
                ("⚠️", "量产避坑与失效诊断", "断簧/虚焊/脆断等根因诊断（RCA）与 DFM 工艺红线"),
                ("📑", "前沿专利与拆解报告", "国内外旗舰硬件执行器结构 Teardown 与专利深度透视"),
                ("💬", "工程师技术答疑通道", "一对一技术咨询通道、行业交流群与专家同行技术研讨")
            ]

        for icon, title, desc in benefits:
            row = QHBoxLayout()
            row.setSpacing(5)
            row.setAlignment(Qt.AlignmentFlag.AlignTop)

            ico_lbl = QLabel(icon)
            ico_lbl.setFixedWidth(16)
            ico_lbl.setStyleSheet("font-size: 10.5px;")
            row.addWidget(ico_lbl)

            text_lbl = QLabel(f"<b style='color:#0F172A;'>{title}</b>: <span style='color:#475569;'>{desc}</span>")
            text_lbl.setWordWrap(True)
            text_lbl.setStyleSheet("font-size: 9.5px; line-height: 1.3;")
            row.addWidget(text_lbl, 1)

            benefits_v.addLayout(row)

        left_layout.addLayout(benefits_v)
        left_layout.addStretch()

        body_layout.addWidget(left_box, 48)

        # === 右侧: 系统规格参数与特色功能卡片 (约 52% 宽度) ===
        right_box = QWidget()
        right_box.setObjectName("rightBox")
        right_box.setStyleSheet("""
            #rightBox {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
            QLabel {
                font-size: 10.5px;
                color: #334155;
                background: transparent;
            }
        """)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(14, 10, 14, 10)
        right_layout.setSpacing(5)

        def make_row(key_text: str, val_widget_or_text, is_bold=False):
            row = QHBoxLayout()
            row.setSpacing(6)
            k_lbl = QLabel(key_text)
            k_lbl.setFixedWidth(82 if is_en else 68)
            k_lbl.setStyleSheet("color: #64748B; font-weight: 600; font-size: 10.5px;")
            row.addWidget(k_lbl)

            if isinstance(val_widget_or_text, str):
                v_lbl = QLabel(val_widget_or_text)
                v_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                if is_bold:
                    v_lbl.setStyleSheet("color: #0F172A; font-weight: 700; font-size: 10.5px;")
                else:
                    v_lbl.setStyleSheet("color: #1E293B; font-size: 10.5px;")
                row.addWidget(v_lbl)
            else:
                row.addWidget(val_widget_or_text)
            row.addStretch()
            return row

        key_w = 82 if is_en else 68

        # 1. 软件系统全称
        right_layout.addLayout(make_row(
            "Platform:" if is_en else "软件系统:",
            PLATFORM_NAME_EN if is_en else PLATFORM_NAME,
            is_bold=True
        ))

        # 2. 软件模块
        right_layout.addLayout(make_row(
            "Workstation:" if is_en else "工作站模块:",
            f"{APP_NAME} | Micro-Coil Design & Electro-Thermal Solver" if is_en else f"{APP_NAME} | 微型线圈设计与电热仿真"
        ))

        # 3. 软件版本 (含 Git Hash)
        git_hash = get_git_commit()
        row_ver = QHBoxLayout()
        row_ver.setSpacing(6)
        k_ver = QLabel("Version:" if is_en else "软件版本:")
        k_ver.setFixedWidth(key_w)
        k_ver.setStyleSheet("color: #64748B; font-weight: 600; font-size: 10.5px;")
        row_ver.addWidget(k_ver)
        v_ver = QLabel(f"{APP_VERSION}")
        v_ver.setStyleSheet("color: #0284C7; font-weight: 800; font-size: 11px;")
        v_build = QLabel(f"(Build {APP_BUILD} · git-{git_hash})")
        v_build.setStyleSheet("color: #64748B; font-size: 10px;")
        row_ver.addWidget(v_ver)
        row_ver.addWidget(v_build)
        row_ver.addStretch()
        right_layout.addLayout(row_ver)

        # 4. 构建时间
        right_layout.addLayout(make_row("Build Time:" if is_en else "构建时间:", BUILD_TIME))

        # 5. 核心架构
        row_arch = QHBoxLayout()
        row_arch.setSpacing(6)
        k_arch = QLabel("Architecture:" if is_en else "核心架构:")
        k_arch.setFixedWidth(key_w)
        k_arch.setStyleSheet("color: #64748B; font-weight: 600; font-size: 10.5px;")
        row_arch.addWidget(k_arch)
        v_arch = QLabel(CORE_ENGINE_AUTHOR)
        v_arch.setStyleSheet("color: #0F172A; font-weight: 600; font-size: 10.5px;")
        v_site_tag = QLabel("(ansv.net)")
        v_site_tag.setStyleSheet("color: #0284C7; font-weight: 600; font-size: 10.5px;")
        row_arch.addWidget(v_arch)
        row_arch.addWidget(v_site_tag)
        row_arch.addStretch()
        right_layout.addLayout(row_arch)

        # 6. 机器码 (COIL-XXXX-XXXX-XXXX-XXXX + 一键复制)
        mid = get_machine_code()
        row_mid = QHBoxLayout()
        row_mid.setSpacing(6)
        k_mid = QLabel("Machine ID:" if is_en else "机器码:")
        k_mid.setFixedWidth(key_w)
        k_mid.setStyleSheet("color: #64748B; font-weight: 600; font-size: 10.5px;")
        row_mid.addWidget(k_mid)
        v_mid = QLabel(mid)
        v_mid.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v_mid.setStyleSheet("""
            color: #0369A1; font-family: 'Consolas', monospace; font-size: 10.5px;
            font-weight: 700; background-color: #E0F2FE; border-radius: 3px;
            padding: 1px 6px; border: 1px solid #BAE6FD;
        """)
        btn_copy_mid = QPushButton("Copy ID" if is_en else "复制机器码")
        btn_copy_mid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_mid.setStyleSheet("""
            QPushButton {
                color: #0369A1; font-size: 9.5px; font-weight: 600; padding: 1px 6px;
                border: 1px solid #BAE6FD; border-radius: 3px; background: #FFFFFF;
            }
            QPushButton:hover { background: #E0F2FE; color: #0284C7; }
        """)
        btn_copy_mid.clicked.connect(lambda: self._copy_to_clipboard(mid, btn_copy_mid, "Copied" if is_en else "已复制机器码"))
        row_mid.addWidget(v_mid)
        row_mid.addWidget(btn_copy_mid)
        row_mid.addStretch()
        right_layout.addLayout(row_mid)

        # 7. 本机 MAC (真实网卡 MAC + 一键复制)
        mac_addr = get_mac_address()
        row_mac = QHBoxLayout()
        row_mac.setSpacing(6)
        k_mac = QLabel("Local MAC:" if is_en else "本机MAC:")
        k_mac.setFixedWidth(key_w)
        k_mac.setStyleSheet("color: #64748B; font-weight: 600; font-size: 10.5px;")
        row_mac.addWidget(k_mac)
        v_mac = QLabel(mac_addr)
        v_mac.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v_mac.setStyleSheet("""
            color: #475569; font-family: 'Consolas', monospace; font-size: 10.5px;
            font-weight: 600; background-color: #F1F5F9; border-radius: 3px;
            padding: 1px 6px; border: 1px solid #CBD5E1;
        """)
        btn_copy_mac = QPushButton("Copy MAC" if is_en else "复制MAC")
        btn_copy_mac.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_mac.setStyleSheet("""
            QPushButton {
                color: #475569; font-size: 9.5px; font-weight: 600; padding: 1px 6px;
                border: 1px solid #CBD5E1; border-radius: 3px; background: #FFFFFF;
            }
            QPushButton:hover { background: #F1F5F9; color: #0F172A; }
        """)
        btn_copy_mac.clicked.connect(lambda: self._copy_to_clipboard(mac_addr, btn_copy_mac, "Copied" if is_en else "已复制MAC"))
        row_mac.addWidget(v_mac)
        row_mac.addWidget(btn_copy_mac)
        row_mac.addStretch()
        right_layout.addLayout(row_mac)

        # 8. 授权工位与授权状态
        st_info = get_station_info()
        cust_name = st_info.get("customer", "Authorized R&D Center" if is_en else "内部核准机构")
        line_stat = st_info.get("station", "Pro R&D Workstation" if is_en else "专业研发工作站 (Pro Station)")
        status_txt = st_info.get("status_text", "🛡️ Active Commercial License" if is_en else "🛡️ 正式商业授权")
        if is_en:
            if cust_name in ("内部核准机构", "全功能试用评估用户"):
                cust_name = "Full-Feature Evaluation User" if st_info.get("is_trial") else "Authorized R&D Center"
            if "7天全功能评估工位" in line_stat:
                d_left = st_info.get("days_left", 7)
                e_date = st_info.get("exp_date", "")
                line_stat = f"7-Day Evaluation Station ({d_left}d left · Exp {e_date})"
            elif "专业研发工作站" in line_stat:
                line_stat = "Pro R&D Workstation"
            if "7天全功能试用中" in status_txt:
                d_left = st_info.get("days_left", 7)
                status_txt = f"⏱️ 7-Day Trial Active ({d_left}d left)"
            elif "未激活" in status_txt or "评估" in status_txt:
                status_txt = "🔓 Evaluation Mode (Unactivated)"
            elif "正式商业授权" in status_txt:
                status_txt = "🛡️ Active Commercial License"
        right_layout.addLayout(make_row("Workstation ID:" if is_en else "授权工位:", f"{cust_name} · {line_stat}"))
        right_layout.addLayout(make_row("License Status:" if is_en else "授权状态:", status_txt))

        # 分割线
        div_line = QFrame()
        div_line.setFrameShape(QFrame.Shape.HLine)
        div_line.setStyleSheet("color: #E2E8F0; margin-top: 2px; margin-bottom: 2px;")
        right_layout.addWidget(div_line)

        # 9. 软件核心特色 (通俗易懂 · 紧凑展示)
        feat_card = QFrame()
        feat_card.setObjectName("featCard")
        feat_card.setStyleSheet("""
            QFrame#featCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 5px;
                padding: 4px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        fc_box = QVBoxLayout(feat_card)
        fc_box.setContentsMargins(6, 4, 6, 4)
        fc_box.setSpacing(3)

        lbl_fc_t = QLabel(
            "💡 Key Platform Capabilities (Production-Proven)"
            if is_en else
            "💡 平台特色功能 (通俗易懂 · 工程实战)"
        )
        lbl_fc_t.setStyleSheet("font-size: 10px; font-weight: 700; color: #0284C7;")
        fc_box.addWidget(lbl_fc_t)

        if is_en:
            mini_feats = [
                ("📱 Multi-Topology Packing", "Racetrack, Circular, Octagonal & Arbitrary CAD perimeter solver"),
                ("🧬 Wire Necking Compensation", "Micron-level enamel & tension thinning model for exact DCR"),
                ("🛡️ Magnet Clearance DFM", "Real-time air-gap & housing collision check with ISO 129 section"),
                ("📊 Scheme Comparison Matrix", "One-click freeze, side-by-side delta analysis & Excel export")
            ]
        else:
            mini_feats = [
                ("📱 八角/跑道物理拓扑", "精确倒推多层多列漆包线排布与内外边距"),
                ("🧬 铜线拉伸减径补偿", "微米级真实漆膜与拉细预测，电阻仿真极准"),
                ("🛡️ 磁钢干涉 DFM 预警", "气隙红线主动诊断，一键 ISO 129 截面标注"),
                ("📊 多方案微调折叠抽屉", "固化对比无缝切换，Excel 报表列宽自适应")
            ]
        for f_title, f_sub in mini_feats:
            f_row = QHBoxLayout()
            f_row.setSpacing(4)
            lbl_k = QLabel(f"• <b>{f_title}</b>:")
            lbl_k.setStyleSheet("font-size: 9px; color: #1E293B;")
            lbl_v = QLabel(f_sub)
            lbl_v.setStyleSheet("font-size: 9px; color: #64748B;")
            f_row.addWidget(lbl_k)
            f_row.addWidget(lbl_v)
            f_row.addStretch()
            fc_box.addLayout(f_row)

        right_layout.addWidget(feat_card)
        right_layout.addStretch()

        body_layout.addWidget(right_box, 52)
        card_layout.addLayout(body_layout)

        # -------------------------------------------------------------
        # 3. 底部版权声明与功能按钮栏 (完全对齐用户截图要求)
        # -------------------------------------------------------------
        # 底部操作栏 (分层设计：上层工程辅助工具 + 版权，下层主控操作与说明书，彻底避免挤压重叠)
        footer_container = QVBoxLayout()
        footer_container.setContentsMargins(0, 6, 0, 0)
        footer_container.setSpacing(7)

        # 分割线
        footer_div = QFrame()
        footer_div.setFrameShape(QFrame.Shape.HLine)
        footer_div.setStyleSheet("color: #E2E8F0; margin-top: 2px; margin-bottom: 2px;")
        footer_container.addWidget(footer_div)

        # 第一行: 系统工程辅助工具条 + 左侧版权说明
        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(8)

        lbl_copyright = QLabel("Copyright © 2026 ansv.net & Yaming.Chen. All rights reserved.")
        lbl_copyright.setStyleSheet("color: #94A3B8; font-size: 10px;")
        row1_layout.addWidget(lbl_copyright)
        row1_layout.addStretch()

        # 辅助按钮 1: 🖥️ 桌面快捷方式
        btn_shortcut = QPushButton("🖥️ Desktop Shortcut" if is_en else "🖥️ 桌面快捷方式")
        btn_shortcut.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_shortcut.setToolTip(
            "Create a high-DPI desktop shortcut for Coil-Architect Pro"
            if is_en else
            "在当前电脑桌面上创建本系统专属高清快捷方式"
        )
        btn_shortcut.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
                white-space: nowrap;
            }
            QPushButton:hover {
                background-color: #F0F9FF;
                border-color: #0284C7;
                color: #0284C7;
            }
        """)
        btn_shortcut.clicked.connect(self._on_create_shortcut_clicked)
        row1_layout.addWidget(btn_shortcut)

        # 辅助按钮 2: 🔗 关联 .ansvcoil 算例
        btn_assoc = QPushButton("🔗 Associate .ansvcoil" if is_en else "🔗 关联 .ansvcoil 算例")
        btn_assoc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_assoc.setToolTip(
            "Register .ansvcoil project extension in Windows so double-clicking opens Coil-Architect Pro"
            if is_en else
            "在 Windows 系统中注册 .ansvcoil 专属算例格式与科技感图标，支持双击算例直接唤起工作站"
        )
        btn_assoc.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #0284C7;
                border: 1px solid #BAE6FD;
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
                white-space: nowrap;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0284C7;
            }
        """)
        btn_assoc.clicked.connect(self._on_register_association_clicked)
        row1_layout.addWidget(btn_assoc)

        # 辅助按钮 3: 📄 导出诊断日志
        btn_export_logs = QPushButton("📄 Export Logs" if is_en else "📄 导出诊断日志")
        btn_export_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_logs.setToolTip(
            "Package full runtime logs & environment diagnostics (.zip) for technical support"
            if is_en else
            "一键打包全景运行日志与系统体检指纹 (.zip) 供研发快速定位排查"
        )
        btn_export_logs.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #059669;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
                white-space: nowrap;
            }
            QPushButton:hover {
                background-color: #ECFDF5;
                border-color: #059669;
            }
        """)
        btn_export_logs.clicked.connect(self._on_export_logs_clicked)
        row1_layout.addWidget(btn_export_logs)

        # 辅助按钮 4: 🌐 网络数据库诊断
        btn_cloud_diag = QPushButton("🌐 Network Diagnostics" if is_en else "🌐 网络数据库诊断")
        btn_cloud_diag.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cloud_diag.setToolTip(
            "Open Enterprise Network & License Server Diagnostics Center (Shortcut: Ctrl+D)"
            if is_en else
            "打开企业内网数据库与通信环境诊断中心 (快捷键: Ctrl+D)"
        )
        btn_cloud_diag.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #0369A1;
                border: 1px solid #BAE6FD;
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
                white-space: nowrap;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0284C7;
            }
        """)
        btn_cloud_diag.clicked.connect(self._on_cloud_diag_clicked)
        row1_layout.addWidget(btn_cloud_diag)
        footer_container.addLayout(row1_layout)

        # 第二行: 核心主控操作栏 (说明书高亮直达、检查更新与确定关闭)
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(10)

        lbl_f1_tip = QLabel(
            "💡 Tip: Press F1 anywhere to open the offline HTML User Manual & Engineering Guide"
            if is_en else
            "💡 提示：在任意界面按 F1 键可随时一键唤起离线 HTML 用户说明书与工程实战指南"
        )
        lbl_f1_tip.setStyleSheet("color: #64748B; font-size: 10.5px;")
        row2_layout.addWidget(lbl_f1_tip)
        row2_layout.addStretch()

        # 主控按钮 1: 📖 使用说明书 (高亮主推，宽度充裕)
        from src.core.i18n import t
        btn_manual = QPushButton(t("about_btn_manual", "📖 使用说明书"))
        btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_manual.setToolTip(
            "Open the offline HTML User Manual & Engineering Guide in your default browser (Shortcut: F1)"
            if is_en else
            "在默认浏览器中打开本软件专属离线 HTML 用户手册与工程指南 (快捷键: F1)"
        )
        btn_manual.setStyleSheet("""
            QPushButton {
                background-color: #F0F9FF;
                color: #0284C7;
                border: 1.5px solid #38BDF8;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11.5px;
                font-weight: 700;
                min-width: 105px;
                white-space: nowrap;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0284C7;
                color: #0369A1;
            }
        """)
        btn_manual.clicked.connect(self._on_open_manual_clicked)
        row2_layout.addWidget(btn_manual)

        # 主控按钮 2: 🚀 检查更新
        btn_chk_update = QPushButton("🚀 Check Updates" if is_en else "🚀 检查更新")
        btn_chk_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_chk_update.setToolTip(
            "Check for OTA updates and view Git release changelog"
            if is_en else
            "检查软件更新并查看 Git 提交历史记录 (Changelog)"
        )
        btn_chk_update.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #0284C7;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11.5px;
                font-weight: 600;
                min-width: 90px;
                white-space: nowrap;
            }
            QPushButton:hover {
                background-color: #F0F9FF;
                border-color: #0284C7;
            }
        """)
        btn_chk_update.clicked.connect(self._on_check_update_clicked)
        row2_layout.addWidget(btn_chk_update)

        # 主控按钮 3: 确定
        btn_ok = QPushButton("OK" if is_en else "确定")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: 1px solid #0284C7;
                border-radius: 4px;
                padding: 5px 22px;
                font-size: 11.5px;
                font-weight: 700;
                min-width: 75px;
                white-space: nowrap;
            }
            QPushButton:hover {
                background-color: #0369A1;
                border-color: #0369A1;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        row2_layout.addWidget(btn_ok)

        footer_container.addLayout(row2_layout)
        card_layout.addLayout(footer_container)
        main_layout.addWidget(card)

    def _copy_to_clipboard(self, text: str, btn: QPushButton, success_msg: str = "已复制"):
        """复制文本到系统剪贴板并给按钮微动反馈"""
        cb = QApplication.clipboard()
        if cb:
            cb.setText(text)
            orig_text = btn.text()
            btn.setText(f"✓ {success_msg}")
            btn.setEnabled(False)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: (btn.setText(orig_text), btn.setEnabled(True)))

    def _on_create_shortcut_clicked(self):
        """用户主动创建专属桌面快捷方式"""
        from src.core.shortcut_helper import create_desktop_shortcut
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        ok, msg = create_desktop_shortcut()
        if ok:
            if is_en:
                QMessageBox.information(
                    self,
                    "Desktop Shortcut",
                    "✅ Desktop shortcut created with the high-DPI vector icon!\nYou can now launch Coil-Architect Pro directly from your desktop.",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.information(
                    self,
                    "桌面快捷方式",
                    "✅ 桌面快捷方式已成功创建并绑定专属高清图标！\n您可随时从桌面双击直接启动。",
                    QMessageBox.StandardButton.Ok
                )
        else:
            if is_en:
                QMessageBox.warning(
                    self,
                    "Desktop Shortcut",
                    f"Could not create desktop shortcut:\n{msg}",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.warning(
                    self,
                    "桌面快捷方式",
                    f"快捷方式创建未完成：\n{msg}",
                    QMessageBox.StandardButton.Ok
                )

    def _on_register_association_clicked(self):
        """用户点击注册 .ansvcoil 文件关联响应"""
        from src.utils.file_association import register_ansvcoil_association
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        ok, msg = register_ansvcoil_association()
        if ok:
            if is_en:
                QMessageBox.information(
                    self,
                    "File Association Registered",
                    "🎉 Successfully registered the .ansvcoil project file type in Windows!\n\n"
                    "• Custom Icon: Bound to the high-DPI vector coil icon\n"
                    "• One-Click Launch: Double-click any .ansvcoil file to open it directly\n"
                    "• Backward Compatible: Legacy .ansv files remain supported",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.information(
                    self,
                    "文件关联注册成功",
                    "🎉 已在 Windows 系统中成功注册 .ansvcoil 专属算例文件类型！\n\n"
                    "• 专属图标: 已绑定高科技矢量线圈图标\n"
                    "• 便捷启动: 任何地方双击 .ansvcoil 文件均可秒级调用本系统打开\n"
                    "• 兼容支持: 历史 .ansv 算例依然可随时导入",
                    QMessageBox.StandardButton.Ok
                )
        else:
            if is_en:
                QMessageBox.warning(
                    self,
                    "File Association Failed",
                    f"Failed to register file association:\n{msg}",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.warning(
                    self,
                    "文件关联注册失败",
                    f"未能成功注册文件关联：\n{msg}",
                    QMessageBox.StandardButton.Ok
                )

    def _on_export_logs_clicked(self):
        """用户一键导出全景诊断日志包"""
        from src.utils.logger import export_diagnostic_bundle, open_log_directory
        from src.core.i18n import i18n
        is_en = i18n.is_english()
        try:
            zip_path = export_diagnostic_bundle()
            try:
                QApplication.clipboard().setText(str(zip_path))
            except Exception:
                pass
            msg = QMessageBox(self)
            if is_en:
                msg.setWindowTitle("Diagnostic Log Bundle Exported")
                msg.setText(
                    f"✅ Full diagnostic log bundle generated:\n{zip_path}\n\n"
                    f"💡 The file path has been copied to your clipboard.\n"
                    f"You can send this ZIP archive directly to our R&D support team."
                )
                btn_open_folder = msg.addButton("📂 Open Log Folder", QMessageBox.ButtonRole.ActionRole)
                msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            else:
                msg.setWindowTitle("诊断日志包导出成功")
                msg.setText(
                    f"✅ 全景诊断日志包已成功生成：\n{zip_path}\n\n"
                    f"💡 文件路径已自动复制到剪贴板。\n"
                    f"您可以直接将该 ZIP 压缩包发送给研发人员排查。"
                )
                btn_open_folder = msg.addButton("📂 打开日志所在目录", QMessageBox.ButtonRole.ActionRole)
                msg.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
            msg.exec()
            if msg.clickedButton() == btn_open_folder:
                open_log_directory()
        except Exception as e:
            if is_en:
                QMessageBox.critical(self, "Export Failed", f"Failed to generate diagnostic log bundle: {e}")
            else:
                QMessageBox.critical(self, "导出失败", f"生成诊断日志包失败: {e}")

    def _on_cloud_diag_clicked(self):
        """唤起企业内网数据库与通信环境诊断中心 (对标 Gear 规范)"""
        from src.gui.cloud_config_dialog import open_cloud_config_dialog
        open_cloud_config_dialog(self)

    def _on_open_manual_clicked(self):
        """一键在默认浏览器打开对应语言的本地 HTML 用户说明书"""
        import sys
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        from src.core.i18n import i18n
        app_dir = Path(__file__).resolve().parent.parent.parent
        is_en = i18n.is_english()
        if is_en:
            candidates = [
                app_dir / "Coil-Architect-Pro_User_Manual.html",
                app_dir / "README_EN.html",
                app_dir / "docs" / "Coil-Architect-Pro_User_Manual.html",
                Path(sys.executable).parent / "Coil-Architect-Pro_User_Manual.html",
                Path(sys.executable).parent / "README_EN.html",
                Path(sys.executable).parent / "docs" / "Coil-Architect-Pro_User_Manual.html",
                app_dir / "Coil-Architect-Pro_使用说明书.html",
                Path(sys.executable).parent / "Coil-Architect-Pro_使用说明书.html",
            ]
            fallback_url = "https://github.com/tonychen5577-tech/coil-architect"
        else:
            candidates = [
                app_dir / "Coil-Architect-Pro_使用说明书.html",
                app_dir / "README.html",
                app_dir / "docs" / "Coil-Architect-Pro_使用说明书.html",
                Path(sys.executable).parent / "Coil-Architect-Pro_使用说明书.html",
                Path(sys.executable).parent / "README.html",
                Path(sys.executable).parent / "docs" / "Coil-Architect-Pro_使用说明书.html",
            ]
            fallback_url = "https://github.com/tonychen5577-tech/coil-architect/blob/main/README_CN.md"

        for p in candidates:
            if p.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.resolve())))
                return
        QDesktopServices.openUrl(QUrl(fallback_url))

    def _on_check_update_clicked(self):
        """唤起检查更新与 Git 版本提交记录窗口"""
        from src.gui.update_dialog import UpdateDialog
        dlg = UpdateDialog(self)
        dlg.exec()
