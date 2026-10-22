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
from PyQt6.QtCore import Qt, QUrl
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
        self.setWindowTitle(f"商业授权激活与订购向导 — {APP_NAME} (License & Purchase Guide)")
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
        adapt_dialog_geometry(self, target_w=870, target_h=560, min_w=800, min_h=500)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. 顶部 Header (Logo + 双语标题 + 官方门户)
        # -------------------------------------------------------------
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
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
        lbl_title = QLabel("ANSV Coil-Architect Pro · 商业授权激活与订购向导 (License & Purchase)")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0284C7; letter-spacing: 0.3px;")
        lbl_sub = QLabel("微型线圈设计与电热仿真工作站 | 官方正版授权认证 · 全球一机一码硬件加密防御体系")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        h_layout.addLayout(title_vbox)

        h_layout.addStretch()

        btn_site = QPushButton(f"🌐 官方门户: ansv.net ↗")
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

        lbl_tier_title = QLabel("🛒 商业授权方案与双币资费 (Tier & Pricing):")
        lbl_tier_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        left_layout.addWidget(lbl_tier_title)

        # 方案条目 (带美金标价)
        tiers_box = QVBoxLayout()
        tiers_box.setSpacing(5)

        def make_tier_item(badge_txt, badge_bg, badge_fg, name, rmb_price, usd_price, desc):
            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 5px;
                }
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(8, 6, 8, 6)
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
                f"<span style='color: #0284C7; font-weight: 800;'>{rmb_price}</span> "
                f"<span style='color: #64748B; font-size: 10.5px;'>({usd_price})</span>"
            )
            t_line.setStyleSheet("font-size: 11px; color: #1E293B;")
            d_line = QLabel(desc)
            d_line.setStyleSheet("font-size: 10px; color: #64748B;")
            v_info.addWidget(t_line)
            v_info.addWidget(d_line)
            r_layout.addLayout(v_info)

            r_layout.addStretch()
            return row

        tiers_box.addWidget(make_tier_item(
            "⚡ 季度", "#E0F2FE", "#0369A1", "项目季度版 (90天)", "¥ 2,180", "$349", "短期项目攻关 / EVT-DVT 单案打样"
        ))
        tiers_box.addWidget(make_tier_item(
            "🌟 主推", "#FEF3C7", "#92400E", "年度商业版 (365天)", "¥ 5,800", "$899", "全物理模型 · 优先一对一支持 · 免费升级"
        ))
        tiers_box.addWidget(make_tier_item(
            "🛡️ 买断", "#DCFCE7", "#166534", "企业单机买断 (永久)", "¥ 16,800", "$2,699", "终身授权 · 涉密工位内网脱网运行 · 首年维护"
        ))
        left_layout.addLayout(tiers_box)

        # 冲抵特权提示卡
        offset_bar = QFrame()
        offset_bar.setStyleSheet("""
            QFrame {
                background-color: #FFFBEB;
                border: 1px solid #FDE68A;
                border-radius: 5px;
            }
        """)
        o_layout = QHBoxLayout(offset_bar)
        o_layout.setContentsMargins(8, 6, 8, 6)
        o_layout.setSpacing(6)
        lbl_offset = QLabel(
            "🎁 <b>专属冲抵权益</b>：订购年度或企业版的客户，后续委托 ANSV 进行专项仿真代工或样品打样时，<b>首期软件费用可全额冲抵技术服务费！</b>"
        )
        lbl_offset.setWordWrap(True)
        lbl_offset.setStyleSheet("color: #92400E; font-size: 10.5px; line-height: 1.3;")
        o_layout.addWidget(lbl_offset)
        left_layout.addWidget(offset_bar)

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

        self.btn_subtab_wx = QPushButton("💬 工程师微信 (WeChat)")
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
        wx_info.addWidget(QLabel(f"微信号: <code style='color:#0284C7; font-weight:bold;'>{WECHAT_CONTACT_ID}</code>"))
        wx_info.addWidget(QLabel("<span style='font-size:10px; color:#64748B;'>手机微信扫码或复制微信号咨询开通</span>"))
        btn_copy_wx = QPushButton("📋 复制微信号 (ansv-net)")
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
        btn_copy_wa = QPushButton("📋 复制 WhatsApp (ansv_net)")
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
        switch_tab(0)

        # 底部支持支付方式声明
        lbl_pay_tips = QLabel("💳 支付通道: 微信支付 · 支付宝 · PayPal (International USD)")
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

        lbl_hw_title = QLabel("💻 本机硬件特征码 (Machine Code):")
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

        btn_copy_mid = QPushButton("📋 复制机器码")
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
        btn_copy_order_msg = QPushButton("💬 一键复制订购消息草稿 (微信 / WhatsApp 直发)")
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

        # 激活码输入区域
        lbl_act_title = QLabel("🔑 输入或粘贴商业许可证激活码 (License Token):")
        lbl_act_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        right_layout.addWidget(lbl_act_title)

        self.txt_token = QLineEdit()
        self.txt_token.setPlaceholderText("粘贴 COIL-SEC-XXXX 格式激活码...")
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

        btn_import_lic = QPushButton("📂 导入 license.lic 授权文件...")
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

        btn_cancel = QPushButton("暂不激活 (稍后处理)")
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

        btn_activate = QPushButton("立即验证并激活")
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
        QMessageBox.information(
            self,
            "微信号已复制",
            f"✅ 工程师微信号已复制: {WECHAT_CONTACT_ID}\n\n请在微信中粘贴搜索添加好友，即可极速开通正式商业授权！"
        )

    def _copy_whatsapp_id(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(WHATSAPP_CONTACT_ID)
        QMessageBox.information(
            self,
            "WhatsApp ID Copied",
            f"✅ WhatsApp Contact Copied: {WHATSAPP_CONTACT_ID}\n\nAdd us on WhatsApp for international license procurement & technical support!"
        )

    def _copy_machine_code(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.machine_code)
        QMessageBox.information(
            self,
            "机器码已复制",
            f"✅ 本机机器码已成功复制到剪贴板！\n\n机器码: {self.machine_code}\n请直接发送给工程师开通专属许可证。"
        )

    def _copy_order_template(self):
        template = (
            f"【ANSV Coil-Architect Pro 商业授权订购申请】\n"
            f"• 意向方案 (Tier): 年度商业版 / Annual Commercial ($899 / ¥5,800)\n"
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
        path, _ = QFileDialog.getOpenFileName(self, "选择授权许可证文件", "", "许可证文件 (*.lic);;所有文件 (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                token = f.read().strip()
            self.txt_token.setText(token)
            self._on_activate()
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法读取许可证文件: {str(e)}")

    def _on_activate(self):
        token = self.txt_token.text().strip()
        if not token:
            QMessageBox.warning(self, "提示", "请输入或导入激活码！")
            return

        ok, msg = LicenseManager.install_license(token)
        if ok:
            QMessageBox.information(
                self,
                "🎉 激活成功",
                "恭喜！ANSV Coil-Architect Pro 正式商业授权已成功激活！\n\n"
                "• 核心双核物理引擎已全部解锁\n"
                "• 2D/3D 高保真出图与 DXF 导出已就绪\n"
                "• 方案比对矩阵与 Excel 评审报表全功能已开放\n\n"
                "感谢您对 ANSV 工业仿真平台的信任与支持！"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "激活失败",
                f"授权验证未通过，请检查激活码是否正确:\n\n{msg}\n\n如有疑问，可随时联系微信技术支持: {WECHAT_CONTACT_ID} 或 WhatsApp: {WHATSAPP_CONTACT_ID}"
            )
