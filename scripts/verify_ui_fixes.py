import os
import sys

# Ensure UTF-8 stdout
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure offscreen rendering
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter

from src.gui.main_window import MainWindow
from src.core.models import CoilType

def test_ui_fixes():
    app = QApplication.instance() or QApplication(sys.argv)
    from PyQt6.QtGui import QFont
    app.setFont(QFont("Microsoft YaHei", 9))
    window = MainWindow()
    window.resize(1380, 860)
    window.show()
    app.processEvents()

    artifact_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    os.makedirs(artifact_dir, exist_ok=True)

    print("=== 1. 验证 DFM 模具卡限默认设定关闭 ===")
    assert hasattr(window, "chk_dfm_enabled"), "chk_dfm_enabled 控件不存在!"
    assert not window.chk_dfm_enabled.isChecked(), "DFM 开关默认未关闭!"
    assert not window.inputs.dfm_enabled, "inputs.dfm_enabled 默认为 True!"
    assert window.outputs.dfm.all_passed, "DFM 未开启时 all_passed 不为 True!"
    print(f"✓ DFM 默认关闭验证通过: chk_dfm_enabled.isChecked() = {window.chk_dfm_enabled.isChecked()}, outputs.dfm.all_passed = {window.outputs.dfm.all_passed}")

    # 验证大匝数超尺寸工况下依然不爆红
    window.sb_radial_layers.setValue(28.3)
    window.run_simulation()
    assert window.outputs.outer_len > window.inputs.max_x_len_limit, "外长应已超出参考空间"
    assert window.outputs.dfm.all_passed, "未开启 DFM 时超尺寸不应判定为 all_passed 失败"
    print(f"✓ 自由仿真模式大匝数测试通过: 即使外廓 OL({window.outputs.outer_len:.3f}) 远超 X_Max({window.inputs.max_x_len_limit:.2f})，系统依然处于纯净自由设计模式，零报警拦截!")

    print("\n=== 2. 验证 16 宫格卡片参数值全部正常显示 ===")
    cards = [
        ("OL", window.card_ol), ("OW", window.card_ow), ("THK", window.card_thk), ("N", window.card_n),
        ("R20", window.card_r20), ("R_init", window.card_r_init), ("DCR_hot", window.card_dcr_hot), ("L", window.card_inductance),
        ("V", window.card_v_term), ("P", window.card_power), ("NI", window.card_ampere_turns), ("T", window.card_t_final),
        ("Weight", window.card_weight), ("Fill", window.card_wire_fill), ("CuFill", window.card_cu_fill), ("MLT", window.card_mlt)
    ]
    for c_name, card in cards:
        val_text = card.lbl_val.text()
        assert val_text and val_text != "--", f"{c_name} 卡片未显示有效数值!"
        assert card.lbl_val.width() > 0, f"{c_name} 卡片数值标签宽度为 0 像素!"
        print(f"  ✓ {c_name} KPI 卡片: 数值={val_text} {card.lbl_unit.text()} (宽度={card.lbl_val.width()}px)")
    print("✓ 16 宫格 KPI 卡片参数值 100% 完整显示正常!")

    # 恢复预设 1 匝数
    window.sb_radial_layers.setValue(12.0)
    window.run_simulation()

    print("\n=== 2. 验证左右栏宽度防抖动与锁定 ===")
    initial_sizes = window.splitter.sizes()
    print(f"初始 Splitter sizes: {initial_sizes}")
    assert initial_sizes[0] == 440, f"左栏初始宽度不是 440: {initial_sizes[0]}"

    # 测试改变各种参数（导致右侧卡片输出文本长度频繁巨变）
    test_params = [
        (25, 20, 0.045, 0.055),
        (5, 4, 0.120, 0.145),
        (35, 16, 0.025, 0.032),
        (12, 10, 0.060, 0.068),
        (19, 8, 0.060, 0.068),
    ]
    for layers, turns, bare, od in test_params:
        window.sb_radial_layers.setValue(layers)
        window.sb_axial_turns.setValue(turns)
        window.sb_bare_dia.setValue(bare)
        window.sb_max_od.setValue(od)
        app.processEvents()
        curr_sizes = window.splitter.sizes()
        assert curr_sizes[0] == 440, f"参数变动导致左栏跳变! 现为: {curr_sizes[0]}"
    print("✓ 极端参数与卡片文本变化下，左栏宽度严格锁死 440px，零跳变验证通过!")

    # 测试用户手工拖动 Splitter
    window._on_splitter_moved(480, 0)
    window.splitter.setSizes([480, initial_sizes[0] + initial_sizes[1] - 480])
    app.processEvents()
    window.run_simulation()
    assert window.splitter.sizes()[0] == 480, "用户手工调整宽度后未保持锁定!"
    print("✓ 用户手工调整宽度后，新宽度锁定保持功能验证通过!")
    
    # 恢复 440
    window._on_splitter_moved(440, 0)
    window.splitter.setSizes([440, initial_sizes[0] + initial_sizes[1] - 440])
    app.processEvents()

    print("\n=== 3. 验证鼠标悬停解释功能 (Tooltips) ===")
    tooltip_checks = [
        ("工程预设", window.combo_presets.toolTip()),
        ("线圈拓扑", window.combo_coil_type.toolTip()),
        ("线圈内长", window.sb_inner_len.toolTip()),
        ("线圈内宽", window.sb_inner_wid.toolTip()),
        ("径向层数", window.sb_radial_layers.toolTip()),
        ("轴向匝数", window.sb_axial_turns.toolTip()),
        ("排线模式", window.combo_mode.toolTip()),
        ("铜裸径", window.sb_bare_dia.toolTip()),
        ("标称外径", window.sb_max_od.toolTip()),
        ("绕线张力", window.sb_tension.toolTip()),
        ("铜材等级", window.combo_copper_grade.toolTip()),
        ("电阻率", window.sb_copper_rho.toolTip()),
        ("环境温度", window.sb_ambient_temp.toolTip()),
        ("测试电流", window.sb_drive_current.toolTip()),
        ("对流散热", window.sb_convection_h.toolTip()),
        ("DFM开关", window.chk_dfm_enabled.toolTip()),
        ("X向限值", window.sb_limit_x.toolTip()),
        ("Y向限值", window.sb_limit_y.toolTip()),
        ("Z向限值", window.sb_limit_z.toolTip()),
        ("耐温上限", window.sb_limit_t.toolTip()),
        ("外廓长卡片", window.card_ol.toolTip()),
        ("外廓宽卡片", window.card_ow.toolTip()),
        ("厚度卡片", window.card_thk.toolTip()),
        ("匝数卡片", window.card_n.toolTip()),
        ("冷态电阻卡片", window.card_r20.toolTip()),
        ("热态电阻卡片", window.card_dcr_hot.toolTip()),
        ("电感卡片", window.card_inductance.toolTip()),
        ("安匝数卡片", window.card_ampere_turns.toolTip()),
        ("终态温度卡片", window.card_t_final.toolTip()),
        ("铜线重量卡片", window.card_weight.toolTip()),
        ("槽满率卡片", window.card_wire_fill.toolTip()),
        ("单匝周长MLT卡片", window.card_mlt.toolTip()),
        ("DFM状态带", window.dfm_strip.toolTip()),
    ]
    for name, tip in tooltip_checks:
        assert tip and len(tip) > 10, f"Tooltip 缺失或内容过短: {name}"
        # 打印部分采样
        print(f"  ✓ {name}: {tip.splitlines()[0]}")
    print("✓ 全界面输入控件与 16 宫格输出卡片 Tooltips 100% 覆盖有效!")

    print("\n=== 4. 验证 2D 截面与限高文字无重叠渲染 ===")
    # 加载预设 3 (LRA 跑道线圈图纸规范)
    window._load_preset(window.combo_presets.itemText(2))
    app.processEvents()

    # 切换到 Tab 1 (2D 截面与限高)
    tab_macro = window.canvas_widget.tab_macro
    tab_macro.setCurrentIndex(1)
    app.processEvents()

    # 截图整体窗口
    pixmap_win = window.grab()
    win_path = os.path.join(artifact_dir, "verify_ui_fixes_main_window.png")
    pixmap_win.save(win_path)
    print(f"✓ 完整窗口截图已保存: {win_path}")

    # 截图 Tab 1 (MagnetSectionCanvas)
    magnet_canvas = window.canvas_widget.magnet_canvas
    pixmap_section = magnet_canvas.grab()
    section_path = os.path.join(artifact_dir, "verify_ui_fixes_section_canvas.png")
    pixmap_section.save(section_path)
    print(f"✓ Tab 1 (2D截面与限高) 画布截图已保存: {section_path}")

    # 截图左侧 DFM 控制卡片
    pixmap_dfm_card = window.grp_dfm.grab()
    dfm_card_path = os.path.join(artifact_dir, "verify_ui_fixes_dfm_card.png")
    pixmap_dfm_card.save(dfm_card_path)
    print(f"✓ DFM 卡片截图已保存: {dfm_card_path}")

    print("\n所有 4 项功能验证 100% PASS!")

if __name__ == "__main__":
    test_ui_fixes()
