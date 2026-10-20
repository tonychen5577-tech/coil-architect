import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')
import platform
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices, QColor
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit
)

from src.core.license_manager import get_machine_code, LicenseManager
from src.version import (
    APP_NAME, APP_VERSION, APP_BUILD, OFFICIAL_URL, COPYRIGHT_TEXT,
    PLATFORM_NAME, PLATFORM_NAME_EN, PLATFORM_FULL_TITLE, WECHAT_OFFICIAL_ACCOUNT
)

class TestAboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 ANSV 平台与系统")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFixedSize(760, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 18, 22, 16)
        main_layout.setSpacing(12)

        # 1. 顶行：标题与官网直达
        top_h = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        lbl_app = QLabel(f"<span style='color:#0284C7; font-weight:800;'>ANSV</span> 微型执行器与精密传动仿真验证平台 <span style='font-size: 11px; color: #0284C7; font-weight: 700; background:#E0F2FE; padding:2px 6px; border-radius:3px;'>{APP_VERSION}</span>")
        lbl_app.setTextFormat(Qt.TextFormat.RichText)
        lbl_app.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A;")

        lbl_sub = QLabel("Actuator Numerical Simulation & Validation | 电磁线圈多物理场仿真工作站 (Coil-Architect Pro)")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        top_h.addLayout(title_box)

        top_h.addStretch()

        btn_web = QPushButton(f"🌐 官方网站: {OFFICIAL_URL.replace('https://', '')}")
        btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_web.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                color: #0284C7;
                font-size: 11px;
                font-weight: 700;
                padding: 5px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0284C7;
                color: #0369A1;
            }
        """)
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_URL)))
        top_h.addWidget(btn_web, 0, Qt.AlignmentFlag.AlignTop)

        main_layout.addLayout(top_h)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E2E8F0; margin: 0px;")
        main_layout.addWidget(line)

        # 2. 中间双区布局
        content_h = QHBoxLayout()
        content_h.setSpacing(16)

        # 左侧：核心特色功能卡片 (通俗易懂 · 实战导向)
        card_left = QFrame()
        card_left.setObjectName("cardLeft")
        card_left.setStyleSheet("""
            #cardLeft {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        left_layout = QVBoxLayout(card_left)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(8)

        lbl_feat_title = QLabel("💡 软件核心特色功能 (通俗易懂 · 工程实战)")
        lbl_feat_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #0284C7;")
        left_layout.addWidget(lbl_feat_title)

        features = [
            ("📱 八角/跑道/圆形微型线圈全支持", "专为手机镜头马达与音圈电机打造！特别是业界公认难算的“八角形异形线圈”，输入空间和目标阻值，软件秒级自动反推圈数与排线层数，告别盲目试凑。"),
            ("🎯 真实张力拉伸与微米级排线精算", "打破传统简单估算！真实模拟绕线受拉变细（0.99拉伸系数）与自粘漆膜厚度，计算出的成型高度、外径尺寸与冷/热态电阻，与工厂打样实测高度吻合。"),
            ("📌 底部方案抽屉（边调边比一键还原）", "微调参数不用来回切换，点击【固化为方案】即可将当前数据存入抽屉横向并排对比；自动计算与基线方案的差值，不满意还可一键原样还原。"),
            ("🔥 电-热-磁多物理场实时防烧", "拖动参数滑块时，软件实时联动评估通电发热温升、绝缘耐温极限、驱动端压与电感，在线圈开模打样前就把过热与驱动不足隐患排查干净。"),
            ("📐 ISO 129 国际标准制图规范", "2D 截面图严格遵循机械制图 ISO 129 标准尺寸界线、闭合实心箭头与基准面代号，图样规范直观，与模具厂、结构工程师无缝对接。"),
            ("📊 一键导出防重名自适应 Excel 报表", "自动按年月日时间戳命名（绝不覆盖历史文件）；导出的 Excel 列宽宽裕排版考究，文字完整显示，彻底告别手动拉伸调宽。")
        ]

        for title, desc in features:
            item_box = QVBoxLayout()
            item_box.setSpacing(1)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #0F172A;")
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("font-size: 10px; color: #475569; line-height: 1.3;")
            d_lbl.setWordWrap(True)
            item_box.addWidget(t_lbl)
            item_box.addWidget(d_lbl)
            left_layout.addLayout(item_box)

        left_layout.addStretch()
        content_h.addWidget(card_left, stretch=6)

        # 右侧：系统信息与微信公众号联系卡片
        right_box = QVBoxLayout()
        right_box.setSpacing(10)

        # 右上：系统参数与机器特征码
        card_sys = QFrame()
        card_sys.setObjectName("cardSys")
        card_sys.setStyleSheet("""
            #cardSys {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        sys_layout = QVBoxLayout(card_sys)
        sys_layout.setContentsMargins(12, 10, 12, 10)
        sys_layout.setSpacing(5)

        lbl_ver = QLabel(f"系统版本: {APP_VERSION} (Build {APP_BUILD})")
        lbl_ver.setStyleSheet("font-size: 11px; font-weight: 700; color: #0F172A;")
        sys_layout.addWidget(lbl_ver)

        lbl_plat = QLabel(f"归属平台: {PLATFORM_NAME}")
        lbl_plat.setStyleSheet("font-size: 10px; color: #64748B;")
        lbl_plat.setWordWrap(True)
        sys_layout.addWidget(lbl_plat)

        auth_ok, auth_msg, _ = LicenseManager.is_system_authorized()
        status_color = "#059669" if auth_ok else "#DC2626"
        status_text = "✔ 正式商业授权 (永久有效)" if auth_ok else f"⚠ {auth_msg}"
        lbl_status = QLabel(f"授权状态: <span style='color:{status_color}; font-weight:700;'>{status_text}</span>")
        lbl_status.setTextFormat(Qt.TextFormat.RichText)
        lbl_status.setStyleSheet("font-size: 11px;")
        sys_layout.addWidget(lbl_status)

        # 硬件指纹机器码
        lbl_mid = QLabel("本机硬件特征码 (Machine Code):")
        lbl_mid.setStyleSheet("font-size: 10px; font-weight: 700; color: #334155; margin-top: 2px;")
        sys_layout.addWidget(lbl_mid)

        mid_h = QHBoxLayout()
        mid_h.setSpacing(4)
        self.code = get_machine_code()
        txt_code = QLineEdit(self.code)
        txt_code.setReadOnly(True)
        txt_code.setStyleSheet("""
            background-color: #F8FAFC;
            font-family: 'Consolas', monospace;
            font-weight: bold;
            font-size: 11px;
            color: #0284C7;
            padding: 3px 5px;
            border: 1px solid #CBD5E1;
            border-radius: 4px;
        """)
        mid_h.addWidget(txt_code)

        btn_copy_mid = QPushButton("复制")
        btn_copy_mid.setFixedWidth(50)
        btn_copy_mid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_mid.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                color: #0F172A;
                font-size: 10px;
                font-weight: 600;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0284C7;
            }
        """)
        btn_copy_mid.clicked.connect(lambda: self._copy_text(self.code, btn_copy_mid, "复制"))
        mid_h.addWidget(btn_copy_mid)
        sys_layout.addLayout(mid_h)

        right_box.addWidget(card_sys)

        # 右下：微信公众号技术支持联系卡片
        card_wechat = QFrame()
        card_wechat.setObjectName("cardWechat")
        card_wechat.setStyleSheet("""
            #cardWechat {
                background-color: #F0FDF4;
                border: 1px solid #86EFAC;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        wc_layout = QVBoxLayout(card_wechat)
        wc_layout.setContentsMargins(12, 10, 12, 10)
        wc_layout.setSpacing(6)

        wc_top_h = QHBoxLayout()
        lbl_wc_icon = QLabel("🟢 官方微信公众号")
        lbl_wc_icon.setStyleSheet("font-size: 11px; font-weight: 800; color: #166534;")
        wc_top_h.addWidget(lbl_wc_icon)
        wc_top_h.addStretch()
        wc_layout.addLayout(wc_top_h)

        # 公众号名称与复制按钮
        wc_name_h = QHBoxLayout()
        wc_name_h.setSpacing(6)
        txt_wc = QLineEdit(WECHAT_OFFICIAL_ACCOUNT)
        txt_wc.setReadOnly(True)
        txt_wc.setStyleSheet("""
            background-color: #FFFFFF;
            font-size: 11px;
            font-weight: 700;
            color: #15803D;
            padding: 3px 6px;
            border: 1px solid #86EFAC;
            border-radius: 4px;
        """)
        wc_name_h.addWidget(txt_wc)

        btn_copy_wc = QPushButton("📋 复制")
        btn_copy_wc.setFixedWidth(56)
        btn_copy_wc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_wc.setStyleSheet("""
            QPushButton {
                background-color: #DCFCE7;
                border: 1px solid #4ADE80;
                border-radius: 4px;
                color: #14532D;
                font-size: 10px;
                font-weight: 700;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #BBF7D0;
                border-color: #22C55E;
                color: #166534;
            }
        """)
        btn_copy_wc.clicked.connect(lambda: self._copy_text(WECHAT_OFFICIAL_ACCOUNT, btn_copy_wc, "📋 复制"))
        wc_name_h.addWidget(btn_copy_wc)
        wc_layout.addLayout(wc_name_h)

        lbl_wc_desc = QLabel(
            "微信搜索关注公众号，获取：\n"
            "• 微型马达与电磁线圈仿真设计实战专栏\n"
            "• 工业级真实工程算例库与微调指南\n"
            "• 软件最新版本发布与工程师一对一答疑"
        )
        lbl_wc_desc.setStyleSheet("font-size: 10px; color: #166534; line-height: 1.4;")
        wc_layout.addWidget(lbl_wc_desc)

        right_box.addWidget(card_wechat)
        right_box.addStretch()

        content_h.addLayout(right_box, stretch=4)
        main_layout.addLayout(content_h)

        # 3. 底栏：版权声明与关闭按钮
        bottom_h = QHBoxLayout()
        lbl_copy = QLabel(COPYRIGHT_TEXT)
        lbl_copy.setStyleSheet("font-size: 10px; color: #94A3B8;")
        bottom_h.addWidget(lbl_copy)

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

    def _copy_text(self, text: str, btn: QPushButton, original_text: str):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            btn.setText("✔ 已复制")

if __name__ == "__main__":
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    out_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    out_file = os.path.join(out_dir, "test_about_redesign_preview.png")
    dlg = TestAboutDialog()
    dlg.show()
    app.processEvents()
    dlg.grab().save(out_file)
    print(f"Rendered about redesign preview to: {out_file}")
