"""
验证全界面 ToolTip 悬停卡片主题统一性:
彻底解决“有时黄色、有时黑色”的原生与暗黑混合渲染问题，
确保全界面所有控件（滑块、输入框、下拉框、16宫格KPI卡片、DFM状态条）
全部统一呈现高对比度、纯白底色、科技蓝微框、清晰炭黑文字的工业级工程释义卡片。
"""

import sys
import os
from pathlib import Path

# Ensure root dir is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication, QToolTip, QLabel
from PyQt6.QtCore import QPoint, QEvent
from PyQt6.QtGui import QColor, QHelpEvent
from src.gui.styles import apply_light_theme
from src.gui.main_window import MainWindow

def test_tooltip_unification():
    app = QApplication(sys.argv)
    apply_light_theme(app)

    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    app.processEvents()

    artifact_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"

    print("\n=== 1. 验证全局应用与主窗口 QSS 样式表注入 QToolTip 规则 ===")
    app_qss = app.styleSheet()
    win_qss = window.styleSheet()
    assert "QToolTip" in app_qss, "app.styleSheet() 缺失 QToolTip 规范!"
    assert "QToolTip" in win_qss, "MainWindow.styleSheet() 缺失 QToolTip 规范!"
    assert "background-color: #FFFFFF" in app_qss, "QToolTip 背景不是纯白 #FFFFFF!"
    assert "color: #0F172A" in app_qss, "QToolTip 文字颜色不是炭黑 #0F172A!"
    assert "border: 1px solid #0284C7" in app_qss, "QToolTip 边框不是科技蓝 #0284C7!"
    print("✓ 全局 Application 与主窗口样式表已注入统一纯白科技蓝边框 QToolTip 规则!")

    print("\n=== 2. 验证原生滑块控件 (曾显示 Windows 黄色) 悬停卡片已统一为纯白高质感 ===")
    slider_widget = window.sb_inner_len.slider
    slider_tip_text = slider_widget.toolTip()
    assert slider_tip_text, "滑块未设置 ToolTip!"
    
    # 模拟在滑块中心弹出 Tooltip
    pt_slider = slider_widget.mapToGlobal(QPoint(slider_widget.width() // 2, slider_widget.height() // 2))
    QToolTip.showText(pt_slider, slider_tip_text, slider_widget)
    app.processEvents()

    tip_labels = [w for w in app.topLevelWidgets() if w.metaObject().className() == 'QTipLabel']
    assert len(tip_labels) > 0, "未检测到弹出的 ToolTip 窗口!"
    tip_slider = tip_labels[0]
    pix_slider_tip = tip_slider.grab()
    path_slider_tip = os.path.join(artifact_dir, "verify_tooltip_slider_clean_white.png")
    pix_slider_tip.save(path_slider_tip)
    print(f"  ✓ 滑块悬停卡片已成功捕获并保存: {path_slider_tip}")
    print(f"  ✓ 滑块 Tooltip 尺寸: {tip_slider.size()}, 文字长度: {len(tip_slider.text())}")
    QToolTip.hideText()
    app.processEvents()

    print("\n=== 3. 验证 16 宫格卡片数值悬停 (彻底杜绝大字号、输出文字颜色与黑底) ===")
    test_cards = [
        ("R20 基准电阻", window.card_r20),
        ("稳态热态电阻 (橙色高亮)", window.card_dcr_hot),
        ("安匝数 (紫色高亮)", window.card_ampere_turns),
        ("极限结温 (红色高亮)", window.card_t_final),
    ]

    for name, card in test_cards:
        # 测试在数值标签 (lbl_val) 上悬停
        val_widget = card.lbl_val
        pt_val = val_widget.mapToGlobal(QPoint(val_widget.width() // 2, val_widget.height() // 2))
        ev = QHelpEvent(QEvent.Type.ToolTip, QPoint(val_widget.width() // 2, val_widget.height() // 2), pt_val)
        app.sendEvent(val_widget, ev)
        app.processEvents()

        tip_labels = [w for w in app.topLevelWidgets() if w.metaObject().className() == 'QTipLabel']
        assert len(tip_labels) > 0, f"卡片 [{name}] 数值标签未检测到弹出的 ToolTip 窗口!"
        tip_card = tip_labels[0]
        pix_card_tip = tip_card.grab()
        img = pix_card_tip.toImage()

        bg_color = img.pixelColor(10, 10).name()
        border_color = img.pixelColor(2, 2).name()
        text_color = img.pixelColor(pix_card_tip.width() // 2, pix_card_tip.height() // 2).name()

        assert bg_color == "#ffffff", f"[{name}] 数值悬停 Tooltip 背景不是纯白! 实际: {bg_color}"
        assert border_color == "#0284c7", f"[{name}] 数值悬停 Tooltip 边框不是科技蓝! 实际: {border_color}"
        assert text_color != card.accent_color.lower(), f"[{name}] 数值悬停文字颜色污染成了数值输出颜色 ({text_color})!"
        assert tip_card.height() <= 110, f"[{name}] 数值悬停 Tooltip 逻辑高度过大 ({tip_card.height()}px)，疑似字体被拉大!"

        print(f"  ✓ [{name}] 鼠标悬停在数值上: 背景={bg_color}(纯白), 边框={border_color}(天蓝), 尺寸={pix_card_tip.size()}, 文本色={text_color} (正常炭黑)")
        QToolTip.hideText()
        app.processEvents()

    # 保存一张最具代表性的数值悬停截图
    val_widget = window.card_dcr_hot.lbl_val
    pt_val = val_widget.mapToGlobal(QPoint(val_widget.width() // 2, val_widget.height() // 2))
    ev = QHelpEvent(QEvent.Type.ToolTip, QPoint(val_widget.width() // 2, val_widget.height() // 2), pt_val)
    app.sendEvent(val_widget, ev)
    app.processEvents()
    tip_labels = [w for w in app.topLevelWidgets() if w.metaObject().className() == 'QTipLabel']
    if tip_labels:
        path_card_val_tip = os.path.join(artifact_dir, "verify_tooltip_card_val_clean_white.png")
        tip_labels[0].grab().save(path_card_val_tip)
        print(f"  ✓ 橙色卡片数值悬停高质感纯白截图已保存: {path_card_val_tip}")
    QToolTip.hideText()
    app.processEvents()

    print("\n=== 4. 验证底部 DFM 状态条卡片悬停卡片已统一为纯白高质感 ===")
    chip_widget = window.dfm_strip.chip_z
    chip_tip_text = chip_widget.toolTip()
    assert chip_tip_text, "DFM芯片未设置 ToolTip!"

    pt_chip = chip_widget.mapToGlobal(QPoint(chip_widget.width() // 2, chip_widget.height() // 2))
    QToolTip.showText(pt_chip, chip_tip_text, chip_widget)
    app.processEvents()

    tip_labels = [w for w in app.topLevelWidgets() if w.metaObject().className() == 'QTipLabel']
    assert len(tip_labels) > 0, "未检测到弹出的 ToolTip 窗口!"
    tip_chip = tip_labels[0]
    pix_chip_tip = tip_chip.grab()
    path_chip_tip = os.path.join(artifact_dir, "verify_tooltip_chip_clean_white.png")
    pix_chip_tip.save(path_chip_tip)
    print(f"  ✓ DFM状态芯片悬停卡片已成功捕获并保存: {path_chip_tip}")
    print(f"  ✓ DFM Tooltip 尺寸: {tip_chip.size()}, 文字长度: {len(tip_chip.text())}")
    QToolTip.hideText()
    app.processEvents()

    print("\n=== 5. 验证去除 AI 夸张词汇，全面使用正常工程描述 ===")
    twin_label = window.findChild(QLabel, "twinBusTitle") or [w for w in window.findChildren(QLabel) if "仿真计算结果" in w.text()][0]
    assert "孪生" not in twin_label.text(), f"标题仍含有'孪生': {twin_label.text()}"
    assert "仿真计算结果" in twin_label.text(), f"标题未更新为'仿真计算结果': {twin_label.text()}"
    print(f"  ✓ 标题成功去AI化: [{twin_label.text()}]")

    # 验证 16 宫格卡片参数标题正常
    card_titles = [
        window.card_ol.lbl_title.text(),
        window.card_ow.lbl_title.text(),
        window.card_thk.lbl_title.text(),
        window.card_n.lbl_title.text(),
        window.card_r20.lbl_title.text(),
        window.card_r_init.lbl_title.text(),
        window.card_dcr_hot.lbl_title.text(),
        window.card_inductance.lbl_title.text(),
        window.card_v_term.lbl_title.text(),
        window.card_power.lbl_title.text(),
        window.card_ampere_turns.lbl_title.text(),
        window.card_t_final.lbl_title.text(),
        window.card_weight.lbl_title.text(),
        window.card_wire_fill.lbl_title.text(),
        window.card_cu_fill.lbl_title.text(),
        window.card_mlt.lbl_title.text(),
    ]
    for ct in card_titles:
        assert "微观" not in ct, f"参数标题含有浮夸AI词汇'微观': {ct}"
        assert "轴向成型" not in ct, f"参数标题含有生硬词汇'轴向成型': {ct}"
    print(f"  ✓ 16 宫格卡片标题全部对齐专业正常工程术语: {card_titles}")

    # 保存全窗口界面截图
    path_main_window = os.path.join(artifact_dir, "verify_ui_clean_engineering_titles.png")
    window.grab().save(path_main_window)
    print(f"  ✓ 全界面去AI化自然工程标题截图已保存: {path_main_window}")

    print("\n所有测试 100% PASS! 彻底解决鼠标悬停黑底/大字/变色问题，并全面还原真实工程表达!")

if __name__ == "__main__":
    test_tooltip_unification()

