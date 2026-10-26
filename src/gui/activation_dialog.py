"""
=============================================================================
Module: src.gui.activation_dialog
Description: ANSV Coil-Architect Pro 商业软件授权激活与国际订购引导向导
采用工业级双栏高对比度设计：
- 左栏: 双币定价阶梯 (RMB / USD)、专属代工冲抵特权、微信与 WhatsApp 国际直通通道
- 右栏: 本机特征码、一键复制订购草稿 (双语适配)、激活码输入与 .lic 导入
=============================================================================
"""

import sys
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QPixmap, QDesktopServices, QColor
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFileDialog, QFrame,
    QStackedWidget, QWidget, QSizePolicy
)

from ..core.license_manager import get_machine_code, LicenseManager
from .icon_helper import get_app_icon, get_ansv_logo_pixmap
from src.version import (
    APP_NAME, APP_VERSION, APP_BUILD, OFFICIAL_URL, OFFICIAL_EMAIL,
    WECHAT_CONTACT_ID, WHATSAPP_CONTACT_ID
)
from .utils import adapt_dialog_geometry


class ActivationDialog(QDialog):
    """全新国际化双栏商业授权激活与订购引导工作台"""

    def __init__(self, parent=None):
        super().__init__(parent)
        from src.core.i18n import i18n
        self.is_en = i18n.is_english()
        self.setWindowTitle(
            f"Commercial License & Purchase Guide — {APP_NAME}"
            if self.is_en else
            f"商业授权激活与订购向导 — {APP_NAME} (License & Purchase Guide)"
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

        self.machine_code = get_machine_code()
        self._init_ui()
        adapt_dialog_geometry(self, target_w=890, target_h=620, min_w=820, min_h=560)

        # 告知云端守护线程当前向导已打开，启动 3 秒高敏探测对账
        try:
            from src.core.cloud_client import CloudClient
            CloudClient.set_activation_dialog_open(True)
        except Exception:
            pass

        # 1. 开窗即刻握手：弹窗打开后 150 毫秒立即向云端上报一次握手与状态核验
        QTimer.singleShot(150, self._fast_handshake_on_open)

        # 2. 弹窗在前台时的轮询：poll_timer 以 3 秒 / 次的高敏频率自动对账云端
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(3000)
        self.poll_timer.timeout.connect(self._poll_cloud_reconciliation)
        self.poll_timer.start()

    def _init_ui(self):
        is_en = self.is_en
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. 顶部 Header (Logo + 双语标题 + 官方门户)
        # -------------------------------------------------------------
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_card.setStyleSheet("""
            QFrame#headerCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(12)

        lbl_logo = QLabel()
        lbl_logo.setPixmap(get_ansv_logo_pixmap(44))
        lbl_logo.setFixedSize(44, 44)
        h_layout.addWidget(lbl_logo)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        lbl_title = QLabel(
            "ANSV Coil-Architect Pro · Commercial License & Purchase Guide"
            if is_en else
            "ANSV Coil-Architect Pro · 商业授权激活与订购向导 (License & Purchase)"
        )
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0284C7; letter-spacing: 0.3px;")
        lbl_sub = QLabel(
            "Micro-Coil Design & Electro-Thermal Workstation | Hardware-Locked Node-Locked License"
            if is_en else
            "微型线圈设计与电热仿真工作站 | 官方正版授权认证 · 全球一机一码硬件加密防御体系"
        )
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        h_layout.addLayout(title_vbox)

        h_layout.addStretch()

        btn_site = QPushButton("🌐 Portal: ansv.net ↗" if is_en else "🌐 官方门户: ansv.net ↗")
        btn_site.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_site.setStyleSheet("""
            QPushButton {
                background-color: #F0F9FF;
                border: 1px solid #BAE6FD;
                color: #0284C7;
                font-size: 11px;
                font-weight: 600;
                padding: 5px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0284C7;
            }
        """)
        btn_site.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_URL)))
        h_layout.addWidget(btn_site)

        root_layout.addWidget(header_card)

        # -------------------------------------------------------------
        # 2. 中间左右双栏卡片
        # -------------------------------------------------------------
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(10)

        # =============================================================
        # 左栏：双币资费阶梯 (RMB / USD) 与 微信/WhatsApp 国际通道
        # =============================================================
        left_card = QFrame()
        left_card.setStyleSheet("""
            QFrame#leftCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
        """)
        left_card.setObjectName("leftCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(8)

        lbl_tier_title = QLabel(
            "🛒 Commercial License Tiers & Pricing (USD / RMB):"
            if is_en else
            "🛒 商业授权方案与双币资费 (Tier & Pricing):"
        )
        lbl_tier_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        left_layout.addWidget(lbl_tier_title)

        # 方案条目 (带美金标价)
        tiers_box = QVBoxLayout()
        tiers_box.setSpacing(5)

        def make_tier_item(badge_txt, badge_bg, badge_fg, name, orig_price, promo_price, desc):
            row = QFrame()
            row.setObjectName("tierRowFrame")
            row.setStyleSheet("""
                QFrame#tierRowFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 5px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(8, 5, 8, 5)
            r_layout.setSpacing(8)

            badge = QLabel(badge_txt)
            badge.setStyleSheet(f"""
                background-color: {badge_bg};
                color: {badge_fg};
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 3px;
            """)
            r_layout.addWidget(badge)

            v_info = QVBoxLayout()
            v_info.setSpacing(1)
            t_line = QLabel(
                f"<b>{name}</b>  "
                f"<span style='color: #0284C7; font-weight: 800;'>{promo_price}</span> "
                f"<span style='color: #94A3B8; text-decoration: line-through; font-size: 10px;'>{orig_price}</span>"
            )
            t_line.setStyleSheet("font-size: 11px; color: #1E293B;")
            d_line = QLabel(desc)
            d_line.setStyleSheet("font-size: 10px; color: #64748B;")
            v_info.addWidget(t_line)
            v_info.addWidget(d_line)
            r_layout.addLayout(v_info)

            r_layout.addStretch()
            return row

        if is_en:
            tiers_box.addWidget(make_tier_item(
                "⚡ 90-Day", "#E0F2FE", "#0369A1", "Quarterly (90d)", "$349 / ¥2,180", "🔥20% OFF: $279 (¥1,744)", "Short-term R&D sprint / EVT-DVT validation"
            ))
            tiers_box.addWidget(make_tier_item(
                "🌟 Best Value", "#FEF3C7", "#92400E", "Annual Pro (365d)", "$899 / ¥5,800", "🔥20% OFF: $719 (¥4,680)", "Full solver suite · Priority 1-on-1 support · Free OTA"
            ))
            tiers_box.addWidget(make_tier_item(
                "🛡️ Perpetual", "#DCFCE7", "#166534", "Perpetual", "$2,699 / ¥16,800", "🔥20% OFF: $2,159 (¥13,440)", "Lifetime license · 100% Air-gapped intranet · 1-Yr Maint."
            ))
        else:
            tiers_box.addWidget(make_tier_item(
                "⚡ 季度", "#E0F2FE", "#0369A1", "项目季度版 (90天)", "¥2,180 ($349)", "🔥8折: ¥ 1,744 ($279)", "短期项目攻关 / EVT-DVT 单案验算"
            ))
            tiers_box.addWidget(make_tier_item(
                "🌟 主推", "#FEF3C7", "#92400E", "年度商业版 (365天)", "¥5,800 ($899)", "🔥8折: ¥ 4,680 ($719)", "全套物理模型 · 优先一对一支持 · 免费升级"
            ))
            tiers_box.addWidget(make_tier_item(
                "🛡️ 买断", "#DCFCE7", "#166534", "企业单机买断 (永久)", "¥16,800 ($2,699)", "🔥8折: ¥ 13,440 ($2,159)", "终身授权 · 涉密工位内网脱网运行 · 首年维护"
            ))
        left_layout.addLayout(tiers_box)

        # 限期 8 折首发特惠提示卡 (红金高亮)
        promo_bar = QFrame()
        promo_bar.setObjectName("promoBarFrame")
        promo_bar.setStyleSheet("""
            QFrame#promoBarFrame {
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 5px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        p_layout = QHBoxLayout(promo_bar)
        p_layout.setContentsMargins(8, 6, 8, 6)
        p_layout.setSpacing(6)
        lbl_promo = QLabel(
            "🔥 <b>Limited-Time 20% OFF Launch Offer</b>:<br>"
            "Contact our engineer directly to enjoy <b>20% OFF across all editions</b> (Annual Edition only <b>$719 / ¥4,680</b>)! "
            "Plus, 100% of your initial software license fee can be credited toward custom FEA consulting or prototyping!"
            if is_en else
            "🔥 <b>限期 8 折首发特惠 (Limited-Time 20% OFF)</b>：<br>"
            "联系工程师开通即享全版本 <b>限时 8 折直降</b>（年度版立省 ¥1,120，仅需 <b>¥4,680 / $719</b>）！"
            "后续委托 ANSV 进行工程代工仿真或打样，首期软件费仍可冲抵技术服务费！"
        )
        lbl_promo.setWordWrap(True)
        lbl_promo.setStyleSheet("color: #991B1B; font-size: 10.5px; line-height: 1.35;")
        p_layout.addWidget(lbl_promo)
        left_layout.addWidget(promo_bar)

        # 联系通道 Tab 切换 (微信咨询 vs WhatsApp International)
        tab_box = QFrame()
        tab_box.setStyleSheet("""
            QFrame#tabFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
        """)
        tab_box.setObjectName("tabFrame")
        tab_vbox = QVBoxLayout(tab_box)
        tab_vbox.setContentsMargins(8, 8, 8, 8)
        tab_vbox.setSpacing(6)

        tab_btn_bar = QHBoxLayout()
        tab_btn_bar.setSpacing(6)

        self.btn_subtab_wx = QPushButton("💬 WeChat Support" if is_en else "💬 工程师微信 (WeChat)")
        self.btn_subtab_wa = QPushButton("🌐 WhatsApp (International)")

        for b in [self.btn_subtab_wx, self.btn_subtab_wa]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(26)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    font-size: 10.5px;
                    font-weight: 600;
                    color: #475569;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    color: #0F172A;
                }
            """)
        tab_btn_bar.addWidget(self.btn_subtab_wx)
        tab_btn_bar.addWidget(self.btn_subtab_wa)
        tab_vbox.addLayout(tab_btn_bar)

        # 堆叠视窗 (微信 vs WhatsApp)
        self.contact_stack = QStackedWidget()

        # 1. 微信卡片
        wx_widget = QWidget()
        wx_h = QHBoxLayout(wx_widget)
        wx_h.setContentsMargins(0, 4, 0, 0)
        wx_h.setSpacing(10)

        lbl_wx_qr = QLabel()
        candidates_wx = [
            Path("resources/wechat_personal_qr.png"),
            Path(__file__).resolve().parent.parent.parent / "resources" / "wechat_personal_qr.png",
            Path("docs/images/qr_wechat_personal.png")
        ]
        p_wx = next((p for p in candidates_wx if p.exists()), None)
        if p_wx:
            lbl_wx_qr.setPixmap(QPixmap(str(p_wx)).scaled(76, 76, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        lbl_wx_qr.setFixedSize(76, 76)
        lbl_wx_qr.setStyleSheet("border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 4px;")
        wx_h.addWidget(lbl_wx_qr)

        wx_info = QVBoxLayout()
        wx_info.setSpacing(3)
        wx_info.addWidget(QLabel(
            f"WeChat ID: <code style='color:#0284C7; font-weight:bold;'>{WECHAT_CONTACT_ID}</code>"
            if is_en else
            f"微信号: <code style='color:#0284C7; font-weight:bold;'>{WECHAT_CONTACT_ID}</code>"
        ))
        wx_info.addWidget(QLabel(
            "<span style='font-size:10px; color:#64748B;'>Scan via WeChat or copy ID for instant activation</span>"
            if is_en else
            "<span style='font-size:10px; color:#64748B;'>手机微信扫码或复制微信号咨询开通</span>"
        ))
        btn_copy_wx = QPushButton(f"📋 Copy WeChat ({WECHAT_CONTACT_ID})" if is_en else "📋 复制微信号 (ansv-net)")
        btn_copy_wx.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_wx.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #0284C7; color: #0284C7;
                border-radius: 4px; font-size: 10.5px; font-weight: 700; padding: 3px 8px;
            }
            QPushButton:hover { background-color: #E0F2FE; }
        """)
        btn_copy_wx.clicked.connect(self._copy_wechat_id)
        wx_info.addWidget(btn_copy_wx)
        wx_h.addLayout(wx_info)
        self.contact_stack.addWidget(wx_widget)

        # 2. WhatsApp 卡片
        wa_widget = QWidget()
        wa_h = QHBoxLayout(wa_widget)
        wa_h.setContentsMargins(0, 4, 0, 0)
        wa_h.setSpacing(10)

        lbl_wa_qr = QLabel()
        candidates_wa = [
            Path("resources/whatsapp_qr.png"),
            Path(__file__).resolve().parent.parent.parent / "resources" / "whatsapp_qr.png",
            Path("docs/images/qr_whatsapp.png")
        ]
        p_wa = next((p for p in candidates_wa if p.exists()), None)
        if p_wa:
            lbl_wa_qr.setPixmap(QPixmap(str(p_wa)).scaled(76, 76, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        lbl_wa_qr.setFixedSize(76, 76)
        lbl_wa_qr.setStyleSheet("border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 4px;")
        wa_h.addWidget(lbl_wa_qr)

        wa_info = QVBoxLayout()
        wa_info.setSpacing(3)
        wa_info.addWidget(QLabel(f"WhatsApp: <code style='color:#16A34A; font-weight:bold;'>{WHATSAPP_CONTACT_ID}</code>"))
        wa_info.addWidget(QLabel("<span style='font-size:10px; color:#64748B;'>Global direct technical support & license</span>"))
        btn_copy_wa = QPushButton(f"📋 Copy WhatsApp ({WHATSAPP_CONTACT_ID})" if is_en else "📋 复制 WhatsApp (ansv_net)")
        btn_copy_wa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_wa.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #16A34A; color: #16A34A;
                border-radius: 4px; font-size: 10.5px; font-weight: 700; padding: 3px 8px;
            }
            QPushButton:hover { background-color: #DCFCE7; }
        """)
        btn_copy_wa.clicked.connect(self._copy_whatsapp_id)
        wa_info.addWidget(btn_copy_wa)
        wa_h.addLayout(wa_info)
        self.contact_stack.addWidget(wa_widget)

        tab_vbox.addWidget(self.contact_stack)
        left_layout.addWidget(tab_box)

        # 切换逻辑
        def switch_tab(idx):
            self.contact_stack.setCurrentIndex(idx)
            if idx == 0:
                self.btn_subtab_wx.setStyleSheet("background-color: #E0F2FE; border: 1px solid #0284C7; color: #0284C7; font-weight: 700; border-radius: 4px; font-size: 10.5px;")
                self.btn_subtab_wa.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; color: #475569; font-weight: 600; border-radius: 4px; font-size: 10.5px;")
            else:
                self.btn_subtab_wa.setStyleSheet("background-color: #DCFCE7; border: 1px solid #16A34A; color: #16A34A; font-weight: 700; border-radius: 4px; font-size: 10.5px;")
                self.btn_subtab_wx.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; color: #475569; font-weight: 600; border-radius: 4px; font-size: 10.5px;")

        self.btn_subtab_wx.clicked.connect(lambda: switch_tab(0))
        self.btn_subtab_wa.clicked.connect(lambda: switch_tab(1))
        default_tab = 1 if is_en else 0
        switch_tab(default_tab)

        # 底部支持支付方式声明
        lbl_pay_tips = QLabel(
            "💳 Payment Methods: PayPal (International USD) · WeChat Pay · Alipay"
            if is_en else
            "💳 支付通道: 微信支付 · 支付宝 · PayPal (International USD)"
        )
        lbl_pay_tips.setStyleSheet("color: #64748B; font-size: 9.5px; text-align: center;")
        lbl_pay_tips.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(lbl_pay_tips)

        columns_layout.addWidget(left_card, 1)

        # =============================================================
        # 右栏：一机一码特征码与激活输入核销区
        # =============================================================
        right_card = QFrame()
        right_card.setStyleSheet("""
            QFrame#rightCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
        """)
        right_card.setObjectName("rightCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(10)

        lbl_hw_title = QLabel(
            "💻 Local Hardware Fingerprint (Machine Code):"
            if is_en else
            "💻 本机硬件特征码 (Machine Code):"
        )
        lbl_hw_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        right_layout.addWidget(lbl_hw_title)

        hw_row = QHBoxLayout()
        hw_row.setSpacing(6)
        self.txt_mid = QLineEdit(self.machine_code)
        self.txt_mid.setReadOnly(True)
        self.txt_mid.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                font-family: 'Consolas', monospace;
                font-weight: bold;
                font-size: 13px;
                color: #0284C7;
                padding: 6px 8px;
            }
        """)
        hw_row.addWidget(self.txt_mid)

        btn_copy_mid = QPushButton("📋 Copy Code" if is_en else "📋 复制机器码")
        btn_copy_mid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_mid.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 10px;
                color: #1E293B;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        btn_copy_mid.clicked.connect(self._copy_machine_code)
        hw_row.addWidget(btn_copy_mid)
        right_layout.addLayout(hw_row)

        # 核心促单加速神器: 一键复制订购消息草稿 (双语模板)
        btn_copy_order_msg = QPushButton(
            "💬 Copy Order Message Template (Send via WhatsApp / WeChat)"
            if is_en else
            "💬 一键复制订购消息草稿 (微信 / WhatsApp 直发)"
        )
        btn_copy_order_msg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_order_msg.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                border: 1px solid #86EFAC;
                border-radius: 5px;
                color: #15803D;
                font-size: 11px;
                font-weight: 700;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: #DCFCE7;
                border-color: #22C55E;
            }
        """)
        btn_copy_order_msg.clicked.connect(self._copy_order_template)
        right_layout.addWidget(btn_copy_order_msg)

        right_layout.addSpacing(4)

        # -------------------------------------------------------------
        # ⚡ 联网一键在线极速激活面板 (无需手动输码 · 优先首选)
        # -------------------------------------------------------------
        online_panel = QFrame()
        online_panel.setObjectName("onlinePanel")
        online_panel.setStyleSheet("""
            QFrame#onlinePanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EFF6FF, stop:1 #F0FDF4);
                border: 1px solid #93C5FD;
                border-radius: 6px;
            }
        """)
        online_vbox = QVBoxLayout(online_panel)
        online_vbox.setContentsMargins(10, 8, 10, 8)
        online_vbox.setSpacing(5)

        lbl_online_header = QLabel(
            "⚡ Instant Online Activation (No Code Required)"
            if is_en else
            "⚡ 联网一键极速激活 (无需手动输入激活码 · 官方推荐)"
        )
        lbl_online_header.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #1D4ED8;")
        online_vbox.addWidget(lbl_online_header)

        lbl_online_desc = QLabel(
            "Contact our support to authorize this workstation. Once approved, click below to activate immediately (or keep this window open for auto-activation within 15s)."
            if is_en else
            "联系客服或管理员开通后，点击下方按钮即可秒级在线核验激活；或保持软件运行，云端下发后系统亦会在15秒内自动激活！"
        )
        lbl_online_desc.setWordWrap(True)
        lbl_online_desc.setStyleSheet("font-size: 10px; color: #475569; line-height: 1.3;")
        online_vbox.addWidget(lbl_online_desc)

        self.btn_online_activate = QPushButton(
            "⚡ Connect && Activate Online Now"
            if is_en else
            "⚡ 立即连接云端在线激活"
        )
        self.btn_online_activate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_online_activate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
                border: 1px solid #1E40AF;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 11.5px;
                font-weight: 700;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB);
            }
            QPushButton:pressed {
                background: #1E40AF;
            }
            QPushButton:disabled {
                background: #94A3B8;
                border-color: #CBD5E1;
            }
        """)
        self.btn_online_activate.clicked.connect(self._on_online_activate_clicked)
        online_vbox.addWidget(self.btn_online_activate)

        right_layout.addWidget(online_panel)

        # 分割线
        sep_row = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #E2E8F0;")
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #E2E8F0;")
        lbl_or = QLabel("Or Offline Manual Verification (Air-Gapped Workstation)" if is_en else "或离线手动输入激活码 (脱网涉密工位)")
        lbl_or.setStyleSheet("font-size: 10px; color: #94A3B8; font-weight: 600;")
        sep_row.addWidget(line1)
        sep_row.addWidget(lbl_or)
        sep_row.addWidget(line2)
        right_layout.addLayout(sep_row)

        # 激活码输入区域
        lbl_act_title = QLabel(
            "🔑 Enter or Paste Commercial License Token:"
            if is_en else
            "🔑 输入或粘贴商业许可证激活码 (License Token):"
        )
        lbl_act_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        right_layout.addWidget(lbl_act_title)

        self.txt_token = QLineEdit()
        self.txt_token.setPlaceholderText(
            "Paste COIL-SEC-XXXX license token here..."
            if is_en else
            "粘贴 COIL-SEC-XXXX 格式激活码..."
        )
        self.txt_token.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 7px 8px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #0284C7;
                background-color: #F8FAFC;
            }
        """)
        right_layout.addWidget(self.txt_token)

        btn_import_lic = QPushButton(
            "📂 Import license.lic File..."
            if is_en else
            "📂 导入 license.lic 授权文件..."
        )
        btn_import_lic.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import_lic.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px dashed #94A3B8;
                border-radius: 5px;
                font-size: 11px;
                color: #475569;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #0284C7;
                color: #0284C7;
            }
        """)
        btn_import_lic.clicked.connect(self._import_lic_file)
        right_layout.addWidget(btn_import_lic)

        right_layout.addStretch()

        # 右栏底栏操作按钮
        right_btn_row = QHBoxLayout()
        right_btn_row.setSpacing(10)

        btn_cancel = QPushButton("Later (Evaluate)" if is_en else "暂不激活 (稍后处理)")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                color: #475569;
                font-size: 11px;
                font-weight: 600;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0F172A;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        right_btn_row.addWidget(btn_cancel)

        btn_activate = QPushButton("Verify && Activate Now" if is_en else "立即验证并激活")
        btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_activate.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #0369A1;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 11.5px;
                font-weight: 700;
                padding: 7px 20px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        btn_activate.clicked.connect(self._on_activate)
        right_btn_row.addWidget(btn_activate)

        right_layout.addLayout(right_btn_row)

        columns_layout.addWidget(right_card, 1)

        root_layout.addLayout(columns_layout)

    def _copy_wechat_id(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(WECHAT_CONTACT_ID)
        if self.is_en:
            QMessageBox.information(
                self,
                "WeChat ID Copied",
                f"✅ WeChat Support ID Copied: {WECHAT_CONTACT_ID}\n\nPaste and search in WeChat to add our engineer for instant commercial license activation!"
            )
        else:
            QMessageBox.information(
                self,
                "微信号已复制",
                f"✅ 工程师微信号已复制: {WECHAT_CONTACT_ID}\n\n请在微信中粘贴搜索添加好友，即可极速开通正式商业授权！"
            )

    def _copy_whatsapp_id(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(WHATSAPP_CONTACT_ID)
        if self.is_en:
            QMessageBox.information(
                self,
                "WhatsApp ID Copied",
                f"✅ WhatsApp Contact Copied: {WHATSAPP_CONTACT_ID}\n\nAdd us on WhatsApp for international license procurement & technical support!"
            )
        else:
            QMessageBox.information(
                self,
                "WhatsApp 已复制",
                f"✅ WhatsApp 联系方式已复制: {WHATSAPP_CONTACT_ID}\n\n欢迎在 WhatsApp 中添加工程师，快速办理国际商业授权与技术支持！"
            )

    def _copy_machine_code(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.machine_code)
        if self.is_en:
            QMessageBox.information(
                self,
                "Machine Code Copied",
                f"✅ Hardware Machine Code copied to clipboard!\n\nMachine Code: {self.machine_code}\nPlease send this code to our support engineer to issue your dedicated license."
            )
        else:
            QMessageBox.information(
                self,
                "机器码已复制",
                f"✅ 本机机器码已成功复制到剪贴板！\n\n机器码: {self.machine_code}\n请直接发送给工程师开通专属许可证。"
            )

    def _copy_order_template(self):
        if self.is_en:
            template = (
                f"[ANSV Coil-Architect Pro Commercial License Order (20% OFF)]\n"
                f"• License Tier: Annual Commercial Workstation (Limited-Time 20% OFF: $719 USD / ¥4,680 CNY)\n"
                f"• Hardware Machine Code: {self.machine_code}\n"
                f"• Client / Organization: [Your Name or Company]\n"
                f"• Official Support: WhatsApp: {WHATSAPP_CONTACT_ID} | WeChat: {WECHAT_CONTACT_ID} | {OFFICIAL_URL}"
            )
            clipboard = QApplication.clipboard()
            clipboard.setText(template)
            QMessageBox.information(
                self,
                "Order Message Copied",
                f"🎉 Order message template copied to clipboard!\n\nIt includes your Hardware Machine Code ({self.machine_code}).\nSimply paste and send it to our engineer via WhatsApp or WeChat for instant activation!"
            )
        else:
            template = (
                f"【ANSV Coil-Architect Pro 商业授权 8 折特惠申请】\n"
                f"• 申请方案 (Tier): 年度商业版 / Annual Commercial (限时8折: ¥4,680 / $719)\n"
                f"• 本机特征码 (Machine Code): {self.machine_code}\n"
                f"• 申请人或单位 (Client / Organization): [请填写 / Your Name or Company]\n"
                f"• 官方技术支持 (Support): WeChat: {WECHAT_CONTACT_ID} | WhatsApp: {WHATSAPP_CONTACT_ID} | {OFFICIAL_URL}"
            )
            clipboard = QApplication.clipboard()
            clipboard.setText(template)
            QMessageBox.information(
                self,
                "订购消息草稿已就绪",
                f"🎉 订购消息草稿已成功复制到剪贴板！\n\n内容已包含您的本机机器码 ({self.machine_code}) 与双语格式。\n请直接打开微信或 WhatsApp 发送给工程师即可秒级开通！"
            )

    def _import_lic_file(self):
        if self.is_en:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select License File", "", "License Files (*.lic);;All Files (*.*)"
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "选择授权许可证文件", "", "许可证文件 (*.lic);;所有文件 (*.*)"
            )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                token = f.read().strip()
            self.txt_token.setText(token)
            self._on_activate()
        except Exception as e:
            if self.is_en:
                QMessageBox.critical(self, "Read Failed", f"Failed to read license file:\n{str(e)}")
            else:
                QMessageBox.critical(self, "读取失败", f"无法读取许可证文件: {str(e)}")

    def _fast_handshake_on_open(self):
        """开窗 150ms 极速云端握手：静默探测是否有最新已批准的授权凭证"""
        try:
            from src.core.cloud_client import CloudClient
            # 静默核验一次
            ok, msg, res = CloudClient.request_online_activation(customer_name="向导开窗对账")
            if ok:
                self.poll_timer.stop()
                self.accept()
                show_license_activated_dialog(self.parent(), res)
        except Exception:
            pass

    def _poll_cloud_reconciliation(self):
        """弹窗在前台时，每 3 秒自动静默轮询云端核查授权下发状态"""
        # 若已激活则自动关闭向导
        auth_ok, _, lic_data = LicenseManager.is_system_authorized()
        if auth_ok and lic_data and not lic_data.get("is_trial", False):
            # 已经是正式商业版
            self.poll_timer.stop()
            self.accept()
            return

        try:
            from src.core.cloud_client import CloudClient
            ok, msg, res = CloudClient.request_online_activation(customer_name="向导3秒对账")
            if ok:
                self.poll_timer.stop()
                self.accept()
                show_license_activated_dialog(self.parent(), res)
        except Exception:
            pass

    def closeEvent(self, event):
        """窗口关闭时恢复常规心跳，注销高敏模式"""
        try:
            if hasattr(self, "poll_timer") and self.poll_timer:
                self.poll_timer.stop()
            from src.core.cloud_client import CloudClient
            CloudClient.set_activation_dialog_open(False)
        except Exception:
            pass
        super().closeEvent(event)

    def reject(self):
        """用户点击关闭/Esc/取消时恢复常规心跳"""
        try:
            if hasattr(self, "poll_timer") and self.poll_timer:
                self.poll_timer.stop()
            from src.core.cloud_client import CloudClient
            CloudClient.set_activation_dialog_open(False)
        except Exception:
            pass
        super().reject()

    def _on_online_activate_clicked(self):
        is_en = self.is_en
        self.btn_online_activate.setEnabled(False)
        self.btn_online_activate.setText(
            "⏳ Connecting to cloud..." if is_en else "⏳ 正在连接云端核发授权..."
        )
        QApplication.processEvents()

        try:
            from src.core.cloud_client import CloudClient
            ok, msg, res = CloudClient.request_online_activation()
            if ok:
                self.btn_online_activate.setText(
                    "✅ Activated!" if is_en else "✅ 在线激活成功！"
                )
                self.accept()
                show_license_activated_dialog(self.parent(), res)
            else:
                self.btn_online_activate.setEnabled(True)
                self.btn_online_activate.setText(
                    "🔄 Refresh Online Status" if is_en else "🔄 刷新激活状态"
                )
                if res and res.get("status") == "PENDING_APPROVAL":
                    info_text = (
                        f"Workstation Machine Code: {self.machine_code}\n\n"
                        "An online activation request has been submitted to the cloud console.\n"
                        "Please notify the administrator or customer support to click 'Authorize'.\n"
                        "Once approved, this software will activate automatically within seconds!"
                        if is_en else
                        f"本机机器码：{self.machine_code}\n\n"
                        "已向云端控制台提交在线激活申请。\n"
                        "请联系管理员或技术客服在后台点击【⚡ 一键下发授权】。\n"
                        "授权后本软件将在 15 秒内自动完成激活并弹出凭证，您也可以随时再次点击【刷新激活状态】！"
                    )
                    QMessageBox.information(
                        self,
                        "Pending Cloud Authorization" if is_en else "在线申请已提交，等待授权",
                        info_text
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Online Activation Notice" if is_en else "在线激活提示",
                        msg
                    )
        except Exception as e:
            self.btn_online_activate.setEnabled(True)
            self.btn_online_activate.setText(
                "⚡ Connect & Activate Online Now" if is_en else "⚡ 立即连接云端在线激活"
            )
            QMessageBox.warning(
                self,
                "Connection Error" if is_en else "连接异常",
                f"未能连通云端服务器: {e}"
            )

    def _on_activate(self):
        token = self.txt_token.text().strip()
        if not token:
            if self.is_en:
                QMessageBox.warning(self, "Notice", "Please paste a license token or import a .lic file first!")
            else:
                QMessageBox.warning(self, "提示", "请输入或导入激活码！")
            return

        ok, msg = LicenseManager.install_license(token)
        if ok:
            self.accept()
            show_license_activated_dialog(self.parent())
        else:
            if self.is_en:
                QMessageBox.critical(
                    self,
                    "Activation Failed",
                    f"License verification failed. Please check your activation token:\n\n{msg}\n\n"
                    f"For assistance, contact WhatsApp: {WHATSAPP_CONTACT_ID} or WeChat: {WECHAT_CONTACT_ID}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "激活失败",
                    f"授权验证未通过，请检查激活码是否正确:\n\n{msg}\n\n如有疑问，可随时联系微信技术支持: {WECHAT_CONTACT_ID} 或 WhatsApp: {WHATSAPP_CONTACT_ID}"
                )


class LicenseActivatedDialog(QDialog):
    """
    商业授权激活成功详细凭证卡片弹窗 (对标顶级工业商业软件体验)
    直观展示：授权客户名称、绑定工位机器码、授权类型方案、有效期截止日、全功能解锁列表
    """

    def __init__(self, parent=None, payload=None):
        super().__init__(parent)
        from src.core.i18n import i18n
        self.is_en = i18n.is_english()
        is_en = self.is_en

        self.setWindowTitle(
            "Commercial License Activated — ANSV Coil-Architect Pro"
            if is_en else
            "商业授权激活成功 — ANSV Coil-Architect Pro"
        )
        self.setWindowIcon(get_app_icon())
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
        """)

        # 获取当前或传入凭证数据
        if not payload:
            auth_ok, _, lic_info = LicenseManager.is_system_authorized()
            payload = lic_info if (auth_ok and lic_info) else {}

        self.payload = payload
        self._init_ui()
        adapt_dialog_geometry(self, target_w=640, target_h=490, min_w=580, min_h=450)

    def _init_ui(self):
        is_en = self.is_en
        p = self.payload or {}
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # 1. 顶部 Header (高亮金色/绿色微章 + 渐变成功横幅)
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ECFDF5, stop:1 #EFF6FF);
                border: 1px solid #A7F3D0;
                border-radius: 8px;
            }
        """)
        b_h = QHBoxLayout(banner)
        b_h.setContentsMargins(14, 12, 14, 12)
        b_h.setSpacing(12)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_ansv_logo_pixmap(46))
        lbl_icon.setFixedSize(46, 46)
        b_h.addWidget(lbl_icon)

        v_title = QVBoxLayout()
        v_title.setSpacing(3)
        lbl_t = QLabel(
            "🎉 Commercial License Activated Successfully!"
            if is_en else
            "🎉 恭喜！ANSV 正式商业授权已成功激活"
        )
        lbl_t.setStyleSheet("font-size: 15px; font-weight: 800; color: #047857;")
        lbl_st = QLabel(
            "Hardware bound · All physical solvers & unlimited exports unlocked"
            if is_en else
            "硬件一机一码已绑定 · 全套电磁热力学求解器与无损导出特权已全部开放"
        )
        lbl_st.setStyleSheet("font-size: 11px; color: #475569;")
        v_title.addWidget(lbl_t)
        v_title.addWidget(lbl_st)
        b_h.addLayout(v_title)
        b_h.addStretch()
        root.addWidget(banner)

        # 2. 授权详细凭证卡片 (白色卡片 + 结构化参数网格)
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        c_v = QVBoxLayout(card)
        c_v.setContentsMargins(14, 12, 14, 12)
        c_v.setSpacing(8)

        lbl_card_t = QLabel("📜 Commercial License Credentials:" if is_en else "📜 商业授权凭证详情 (License Credentials):")
        lbl_card_t.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #0F172A;")
        c_v.addWidget(lbl_card_t)

        cust_name = p.get("cust") or p.get("customer_name") or "ANSV VIP 商业客户"
        mid = p.get("mid") or get_machine_code()
        exp_date = p.get("exp") or p.get("expire_date") or "PERMANENT"
        maint_exp = p.get("maint_exp") or exp_date
        plan_code = p.get("plan") or p.get("plan_type") or "SUB_ANNUAL_365"

        plan_map = {
            "SUB_QUARTER_90": ("Quarterly Sprint (90d)", "短期季度冲刺版 (90天)"),
            "SUB_ANNUAL_365": ("Annual Commercial Pro (365d)", "👑 年度商业标准版 (365天)"),
            "PERPETUAL_1Y_UPDATE": ("Perpetual Enterprise (Lifetime)", "👑 企业永久买断版 (终身有效)"),
            "PERMANENT": ("Perpetual Enterprise (Lifetime)", "👑 企业永久买断版 (终身有效)"),
        }
        plan_label = plan_map.get(plan_code, (plan_code, plan_code))[1 if not is_en else 0]

        if exp_date == "PERMANENT":
            exp_display = "Lifetime / Perpetual" if is_en else "永久有效 (终身买断)"
        else:
            exp_display = exp_date

        def make_row(title_en, title_zh, val, is_code=False, highlight=False):
            r = QHBoxLayout()
            r.setSpacing(8)
            lbl_k = QLabel((title_en if is_en else title_zh) + ":")
            lbl_k.setFixedWidth(120 if is_en else 110)
            lbl_k.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
            
            lbl_v = QLabel(str(val))
            if highlight:
                lbl_v.setStyleSheet("font-size: 11.5px; color: #0284C7; font-weight: 800;")
            elif is_code:
                lbl_v.setStyleSheet("font-size: 11px; font-family: 'Consolas', monospace; color: #1E293B; font-weight: 700;")
            else:
                lbl_v.setStyleSheet("font-size: 11px; color: #1E293B; font-weight: 600;")
            
            r.addWidget(lbl_k)
            r.addWidget(lbl_v)
            r.addStretch()
            return r

        c_v.addLayout(make_row("Licensed Entity", "授权所属客户", cust_name, highlight=True))
        c_v.addLayout(make_row("Workstation ID", "绑定机器特征码", mid, is_code=True))
        c_v.addLayout(make_row("License Tier", "授权类别方案", plan_label))
        c_v.addLayout(make_row("Validity Period", "授权有效期限至", exp_display, highlight=True))
        c_v.addLayout(make_row("Maintenance Exp", "软件维护服务至", maint_exp))
        c_v.addLayout(make_row("Delivery Mode", "授权分发途径", "⚡ Instant Cloud Push" if is_en else "⚡ 云端在线实时核发 / 边缘微协同"))

        root.addWidget(card)

        # 3. 已解锁高级特权概览 (绿色勾选卡片)
        feats_card = QFrame()
        feats_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px dashed #CBD5E1;
                border-radius: 6px;
            }
        """)
        f_v = QVBoxLayout(feats_card)
        f_v.setContentsMargins(12, 8, 12, 8)
        f_v.setSpacing(4)

        lbl_f_t = QLabel("🚀 Unlocked Industrial Capabilities (All Constraints Lifted):" if is_en else "🚀 商业专属特权已全面就绪 (解除全部仿真与操作限制):")
        lbl_f_t.setStyleSheet("font-size: 10.5px; font-weight: 700; color: #047857;")
        f_v.addWidget(lbl_f_t)

        feats = [
            ("✔ 6 Topologies Full-DOF Parametric Modeling", "✔ 全 6 类线圈拓扑 (方形/赛道/圆角/骨架) 全自由度设计建模"),
            ("✔ 3D FEM Electro-Thermal Multi-Physics Coupled Solver", "✔ 3D FEM 电磁-热流-瞬态场强耦合有限元求解器"),
            ("✔ Dynamic Stiffness, Modal Harmonics & NVH Vibration", "✔ 动刚度、模态振型与高阶谐响应 NVH 振动噪声计算"),
            ("✔ Lossless CAD/DXF/STEP/JSON & Multi-case Comparison Matrix", "✔ 无损 CAD / DXF / STEP 工程出图与多方案比对导出"),
            ("✔ Cloudflare Anycast OTA Silent Upgrade & SmartDNS Self-Healing", "✔ 全球分布式 Anycast OTA 升级保障与数据库静默自愈")
        ]
        for f_en, f_zh in feats:
            l = QLabel(f_en if is_en else f_zh)
            l.setStyleSheet("font-size: 10px; color: #334155;")
            f_v.addWidget(l)

        root.addWidget(feats_card)

        # 4. 底部确认按钮
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_start = QPushButton("🚀 Start Designing Now" if is_en else "🚀 立即进入微型线圈工作站")
        btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                border: 1px solid #0369A1;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 700;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        btn_start.clicked.connect(self.accept)
        btn_box.addWidget(btn_start)
        root.addLayout(btn_box)


def show_license_activated_dialog(parent=None, payload=None):
    """全局弹出商业授权激活成功详细凭证卡片对话框"""
    dlg = LicenseActivatedDialog(parent, payload=payload)
    return dlg.exec()
