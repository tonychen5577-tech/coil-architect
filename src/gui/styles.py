"""
Coil-Architect Pro - Clean White Industrial UI Design System
高对比度精密测控工业风格 (严格对齐 FFT 分析软件 / Gear-NVH 工业设计规范)
"""

import os
import sys
from pathlib import Path

COLOR_PALETTE = {
    "bg_base": "#F8FAFC",          # 柔和科技白灰背景
    "bg_card": "#FFFFFF",          # 纯白卡片容器
    "bg_header": "#F1F5F9",        # 标题/表头淡灰背景
    "bg_input": "#FFFFFF",         # 输入框白底
    "border_subtle": "#E2E8F0",    # 浅灰精细边框
    "border_medium": "#CBD5E1",    # 中度边框
    "border_focus": "#0284C7",     # 聚焦天蓝色
    "text_main": "#0F172A",        # 主文字炭黑
    "text_muted": "#64748B",       # 说明文字铅灰
    "primary": "#0284C7",          # 科技天蓝
    "primary_hover": "#0369A1",
    "primary_light": "#E0F2FE",    # 浅天蓝背景
    "success": "#059669",          # 翡翠绿 (正常/合格)
    "success_light": "#ECFDF5",
    "warning": "#D97706",          # 琥珀黄 (预警/重点指标)
    "warning_light": "#FFFBEB",
    "danger": "#DC2626",           # 珊瑚红 (超标/干涉报警)
    "danger_light": "#FEF2F2",
    "purple": "#7C3AED",          # 稳态结温特征紫
    "purple_light": "#F5F3FF",
}

_RES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "resources")).replace("\\", "/")
os.makedirs(_RES_DIR, exist_ok=True)

_ICONS = {
    "spin_up.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="5,0 10,6 0,6" fill="#475569"/></svg>',
    "spin_up_hover.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="5,0 10,6 0,6" fill="#0284C7"/></svg>',
    "spin_down.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="0,0 10,0 5,6" fill="#475569"/></svg>',
    "spin_down_hover.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="0,0 10,0 5,6" fill="#0284C7"/></svg>',
}
for name, svg_content in _ICONS.items():
    icon_path = os.path.join(_RES_DIR, name)
    if not os.path.exists(icon_path):
        with open(icon_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

_SPIN_UP_SVG = f"{_RES_DIR}/spin_up.svg"
_SPIN_UP_HOVER_SVG = f"{_RES_DIR}/spin_up_hover.svg"
_SPIN_DOWN_SVG = f"{_RES_DIR}/spin_down.svg"
_SPIN_DOWN_HOVER_SVG = f"{_RES_DIR}/spin_down_hover.svg"


def get_arrow_icon_path() -> str:
    """获取下拉框箭头图标绝对路径"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    arrow = root_dir / "resources" / "down_arrow.png"
    if arrow.exists():
        return arrow.as_posix()
    return ""


LIGHT_INDUSTRIAL_QSS = """
/* 全局基础字体与默认文字颜色 - 纯白/浅灰白底色，彻底杜绝黑色透明透底 */
* {
    font-family: "Segoe UI", "Microsoft YaHei", -apple-system, sans-serif;
    color: #0F172A;
    outline: none;
}

/* 全局 QToolTip 悬停工程释义卡片规范 (统一纯白科技微框风格，彻底消除 Windows 原生黄色与黑底不一致) */
QToolTip {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #0284C7;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 11px;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}

QMainWindow {
    background-color: #F8FAFC;
}

QDialog {
    background-color: #FFFFFF;
    color: #0F172A;
}

#centralWidget {
    background-color: #F8FAFC;
}

/* QMessageBox 消息提示框专用规范 (防止系统深色模式下变黑导致文字不可见) */
QMessageBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
}

QMessageBox QLabel {
    background-color: transparent;
    color: #0F172A;
    font-size: 13px;
    font-weight: 500;
}

QMessageBox QPushButton {
    background-color: #0284C7;
    border: 1px solid #0284C7;
    border-radius: 4px;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: bold;
    min-width: 80px;
    min-height: 28px;
    padding: 4px 16px;
}

QMessageBox QPushButton:hover {
    background-color: #0369A1;
}

QMessageBox QPushButton:pressed {
    background-color: #0284C7;
}

/* 全局基础标签规范 (彻底杜绝继承 QFrame 的边框与内边距) */
QLabel {
    background-color: transparent;
    border: none;
    padding: 0px;
    color: #0F172A;
}

/* 顶部状态与工具栏 */
QStatusBar {
    background-color: #FFFFFF;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
    font-size: 12px;
}

/* 卡片容器 */
QFrame.CardFrame {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

QFrame.CardFrame:hover {
    border: 1px solid #CBD5E1;
}

/* 区域小标题 */
QLabel.SectionTitle {
    font-size: 13px;
    font-weight: 700;
    color: #0284C7;
    letter-spacing: 0.3px;
    padding-bottom: 4px;
    border-bottom: 1px solid #F1F5F9;
}

QLabel.SubText {
    font-size: 11px;
    color: #64748B;
}

/* 按钮设计 */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    color: #334155;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #F8FAFC;
    border: 1px solid #0284C7;
    color: #0284C7;
}

QPushButton:pressed {
    background-color: #F1F5F9;
}

QPushButton.PrimaryBtn {
    background-color: #0284C7;
    border: 1px solid #0284C7;
    color: #FFFFFF;
    font-weight: 700;
}

QPushButton.PrimaryBtn:hover {
    background-color: #0369A1;
    border: 1px solid #0369A1;
    color: #FFFFFF;
}

QPushButton.SuccessBtn {
    background-color: #059669;
    border: 1px solid #059669;
    color: #FFFFFF;
    font-weight: 700;
}

QPushButton.SuccessBtn:hover {
    background-color: #047857;
}

QPushButton.SecondaryBtn {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    color: #334155;
    font-weight: 600;
}

QPushButton.SecondaryBtn:hover {
    background-color: #F1F5F9;
    border: 1px solid #94A3B8;
    color: #0F172A;
}

/* 输入框与下拉框 */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    color: #0F172A;
    padding: 3px 6px;
    font-size: 12px;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
}

QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    color: #0F172A;
    padding: 2px 24px 2px 6px;
    min-height: 24px;
    font-size: 12px;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    height: 13px;
    border-left: 1px solid #CBD5E1;
    border-bottom: 1px solid #E2E8F0;
    border-top-right-radius: 3px;
    background-color: #F8FAFC;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background-color: #E0F2FE;
    border-left-color: #0284C7;
}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {
    background-color: #BAE6FD;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    height: 13px;
    border-left: 1px solid #CBD5E1;
    border-bottom-right-radius: 3px;
    background-color: #F8FAFC;
}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #E0F2FE;
    border-left-color: #0284C7;
}

QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
    background-color: #BAE6FD;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url("__SPIN_UP_SVG__");
    width: 9px;
    height: 6px;
}

QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {
    image: url("__SPIN_UP_HOVER_SVG__");
    width: 9px;
    height: 6px;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url("__SPIN_DOWN_SVG__");
    width: 9px;
    height: 6px;
}

QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {
    image: url("__SPIN_DOWN_HOVER_SVG__");
    width: 9px;
    height: 6px;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    color: #0F172A;
    padding: 4px 24px 4px 10px;
    font-size: 12px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #CBD5E1;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: #F8FAFC;
}

QComboBox::drop-down:hover {
    background-color: #E2E8F0;
}

QComboBox::down-arrow {
    image: url("__ARROW_ICON_PATH__");
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    selection-background-color: #E0F2FE;
    selection-color: #0284C7;
    color: #0F172A;
    padding: 4px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #0284C7;
    background-color: #FFFFFF;
}

/* 进度条与滑块 */
QSlider::groove:horizontal {
    height: 4px;
    background: #E2E8F0;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #0284C7;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #0284C7;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #0284C7;
}

/* 滚动区域 */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #F1F5F9;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_INDUSTRIAL_QSS = (
    LIGHT_INDUSTRIAL_QSS
    .replace("__SPIN_UP_SVG__", _SPIN_UP_SVG)
    .replace("__SPIN_UP_HOVER_SVG__", _SPIN_UP_HOVER_SVG)
    .replace("__SPIN_DOWN_SVG__", _SPIN_DOWN_SVG)
    .replace("__SPIN_DOWN_HOVER_SVG__", _SPIN_DOWN_HOVER_SVG)
    .replace("__ARROW_ICON_PATH__", get_arrow_icon_path())
)


def apply_light_theme(app):
    """
    强制设置纯白工业测控浅色主题 (Fusion 浅色调色板 + LIGHT_INDUSTRIAL_QSS)
    免疫任何 Windows 10/11 操作系统深色模式黑底/黑框污染，确保弹窗、菜单与提示框 100% 纯白可读。
    """
    from PyQt6.QtGui import QPalette, QColor, QFont
    from PyQt6.QtWidgets import QToolTip
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F1F5F9"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#0F172A"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0F172A"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#DC2626"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0284C7"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    app.setStyleSheet(LIGHT_INDUSTRIAL_QSS)
    QToolTip.setFont(QFont("Segoe UI", 9))
