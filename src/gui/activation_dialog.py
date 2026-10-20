"""
Coil-Architect Pro - Activation Dialog
商业授权激活弹窗 (工业浅色高对比度设计)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFileDialog, QApplication
)
from ..core.license_manager import get_machine_code, LicenseManager
from .utils import adapt_dialog_geometry


class ActivationDialog(QDialog):
    """商业软件激活对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("商业授权激活 - Coil-Architect Pro")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; color: #0F172A; }")

        self._init_ui()
        adapt_dialog_geometry(self, target_w=540, target_h=360, min_w=460, min_h=300)


    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 标题与说明
        title = QLabel("🛡 Coil-Architect Pro 商业软件授权激活")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0284C7;")
        layout.addWidget(title)

        desc = QLabel("本软件已启用硬件绑定防御体系。首次使用请将下方机器码发送给软件发布方以获取正式商业许可证。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; color: #64748B; line-height: 1.4;")
        layout.addWidget(desc)

        # 机器码卡片
        mid_box = QVBoxLayout()
        mid_box.setSpacing(4)
        lbl_mid_title = QLabel("本机硬件特征码 (Machine Code):")
        lbl_mid_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #334155;")
        mid_box.addWidget(lbl_mid_title)

        mid_h = QHBoxLayout()
        self.machine_code = get_machine_code()
        self.txt_mid = QLineEdit(self.machine_code)
        self.txt_mid.setReadOnly(True)
        self.txt_mid.setStyleSheet("""
            background-color: #F8FAFC;
            font-family: 'Consolas', monospace;
            font-weight: bold;
            font-size: 13px;
            color: #0284C7;
            padding: 6px;
        """)
        mid_h.addWidget(self.txt_mid)

        btn_copy = QPushButton("📋 复制")
        btn_copy.setFixedWidth(75)
        btn_copy.clicked.connect(self._copy_machine_code)
        mid_h.addWidget(btn_copy)
        mid_box.addLayout(mid_h)

        layout.addLayout(mid_box)

        # 激活码输入
        act_box = QVBoxLayout()
        act_box.setSpacing(4)
        lbl_act = QLabel("输入激活码 (License Token):")
        lbl_act.setStyleSheet("font-size: 11px; font-weight: 700; color: #334155;")
        act_box.addWidget(lbl_act)

        self.txt_token = QLineEdit()
        self.txt_token.setPlaceholderText("粘贴 COIL-SEC-XXXX 格式激活码...")
        self.txt_token.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px; padding: 6px;")
        act_box.addWidget(self.txt_token)

        layout.addLayout(act_box)

        # 按钮条
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_import_lic = QPushButton("📂 导入 license.lic 文件")
        btn_import_lic.clicked.connect(self._import_lic_file)
        btn_layout.addWidget(btn_import_lic)

        btn_layout.addStretch()

        btn_cancel = QPushButton("暂不激活 (稍后处理)")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_activate = QPushButton("立即激活")
        btn_activate.setProperty("class", "PrimaryBtn")
        btn_activate.clicked.connect(self._on_activate)
        btn_layout.addWidget(btn_activate)

        layout.addLayout(btn_layout)

    def _copy_machine_code(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.machine_code)
        QMessageBox.information(self, "复制成功", "机器码已复制到剪贴板，请发送给管理员！")

    def _import_lic_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择授权文件", "", "授权许可 (*.lic);;所有文件 (*.*)")
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
            QMessageBox.information(self, "激活成功", "Coil-Architect Pro 商业授权激活成功！")
            self.accept()
        else:
            QMessageBox.critical(self, "激活失败", f"授权验证未通过:\n{msg}")
