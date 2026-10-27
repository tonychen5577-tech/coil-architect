# -*- coding: utf-8 -*-
import sys

def patch_ranges():
    # 1. Patch slider_spin_box.py widths
    with open("src/gui/widgets/slider_spin_box.py", "r", encoding="utf-8") as f:
        ssb_code = f.read()

    ssb_target_1 = "self.spin.setFixedWidth(118 if decimals >= 5 else 98)"
    ssb_replace_1 = "self.spin.setFixedWidth(120 if decimals >= 5 else 105)"
    if ssb_target_1 in ssb_code:
        ssb_code = ssb_code.replace(ssb_target_1, ssb_replace_1, 1)
        print("Patched FloatSliderBox spin width")

    ssb_target_2 = "self.spin.setFixedWidth(85)"
    ssb_replace_2 = "self.spin.setFixedWidth(98)"
    if ssb_target_2 in ssb_code:
        ssb_code = ssb_code.replace(ssb_target_2, ssb_replace_2, 1)
        print("Patched IntSliderBox spin width")

    with open("src/gui/widgets/slider_spin_box.py", "w", encoding="utf-8") as f:
        f.write(ssb_code)
    print("Saved slider_spin_box.py")

    # 2. Patch main_window.py
    with open("src/gui/main_window.py", "r", encoding="utf-8") as f:
        mw_code = f.read()

    replacements = [
        # 几何尺寸
        ('self.sb_inner_len = FloatSliderBox("线圈内长 (IL)", "mm", 0.5, 40.0, 4.86, 0.01)',
         'self.sb_inner_len = FloatSliderBox("线圈内长 (IL)", "mm", 0.2, 500.0, 4.86, 0.01)'),
        ('self.sb_inner_wid = FloatSliderBox("线圈内宽 (IW)", "mm", 0.2, 20.0, 1.50, 0.01)',
         'self.sb_inner_wid = FloatSliderBox("线圈内宽 (IW)", "mm", 0.1, 300.0, 1.50, 0.01)'),
        ('self.sb_oct_id1 = FloatSliderBox("对边内径 ID1", "mm", 1.0, 25.0, 7.10, 0.01)',
         'self.sb_oct_id1 = FloatSliderBox("对边内径 ID1", "mm", 0.5, 200.0, 7.10, 0.01)'),
        ('self.sb_oct_id2 = FloatSliderBox("对角内径 ID2", "mm", 1.0, 30.0, 7.05, 0.01)',
         'self.sb_oct_id2 = FloatSliderBox("对角内径 ID2", "mm", 0.5, 250.0, 7.05, 0.01)'),
        ('self.sb_oct_r1 = FloatSliderBox("拐角内圆角 R1", "mm", 0.05, 1.50, 0.30, 0.01)',
         'self.sb_oct_r1 = FloatSliderBox("拐角内圆角 R1", "mm", 0.01, 30.0, 0.30, 0.01)'),
        ('self.sb_perim_in = FloatSliderBox("展开内周长 C_in", "mm", 1.0, 200.0, 20.0, 0.05)',
         'self.sb_perim_in = FloatSliderBox("展开内周长 C_in", "mm", 1.0, 2000.0, 20.0, 0.05)'),
        ('self.sb_perim_outer_len = FloatSliderBox("参考外廓长 Max_X", "mm", 1.0, 50.0, 7.0, 0.05)',
         'self.sb_perim_outer_len = FloatSliderBox("参考外廓长 Max_X", "mm", 1.0, 800.0, 7.0, 0.05)'),
        ('self.sb_perim_outer_wid = FloatSliderBox("参考外廓宽 Max_Y", "mm", 1.0, 50.0, 5.0, 0.05)',
         'self.sb_perim_outer_wid = FloatSliderBox("参考外廓宽 Max_Y", "mm", 1.0, 800.0, 5.0, 0.05)'),
        
        # 层数与匝数 (重点优化: 匝数扩充至 3000 匝，层数扩充至 300 层)
        ('self.sb_radial_layers = FloatSliderBox("径向层数", "层", 0.5, 50.0, 14.0, 0.5, decimals=1)',
         'self.sb_radial_layers = FloatSliderBox("径向层数", "层", 0.5, 300.0, 14.0, 0.5, decimals=1)'),
        ('self.sb_axial_turns = IntSliderBox("每层匝数", "匝", 1, 80, 12)',
         'self.sb_axial_turns = IntSliderBox("每层匝数", "匝", 1, 3000, 12)'),
        ('self.sb_mold_height = FloatSliderBox("模具压实厚度", "mm", 0.10, 5.00, 0.55, 0.01, decimals=2)',
         'self.sb_mold_height = FloatSliderBox("模具压实厚度", "mm", 0.05, 100.00, 0.55, 0.01, decimals=2)'),

        # 线径与截面
        ('self.sb_bare_dia = FloatSliderBox("铜线裸径 (d)", "mm", 0.010, 0.800, 0.075, 0.001)',
         'self.sb_bare_dia = FloatSliderBox("铜线裸径 (d)", "mm", 0.010, 3.500, 0.075, 0.001)'),
        ('self.sb_max_od = FloatSliderBox("漆包外径 (D)", "mm", 0.012, 1.000, 0.085, 0.001)',
         'self.sb_max_od = FloatSliderBox("漆包外径 (D)", "mm", 0.012, 4.000, 0.085, 0.001)'),
        ('self.sb_flat_w = FloatSliderBox("宽边宽度 (W)", "mm", 0.020, 3.000, 0.800, 0.005)',
         'self.sb_flat_w = FloatSliderBox("宽边宽度 (W)", "mm", 0.020, 15.000, 0.800, 0.005)'),
        ('self.sb_flat_h = FloatSliderBox("高边厚度 (H)", "mm", 0.020, 2.000, 0.350, 0.005)',
         'self.sb_flat_h = FloatSliderBox("高边厚度 (H)", "mm", 0.020, 10.000, 0.350, 0.005)'),
        ('self.sb_flat_r = FloatSliderBox("倒圆角半径 (r)", "mm", 0.000, 0.500, 0.080, 0.005)',
         'self.sb_flat_r = FloatSliderBox("倒圆角半径 (r)", "mm", 0.000, 5.000, 0.080, 0.005)'),
        ('self.sb_tension = FloatSliderBox("张力拉伸系数", "系数", 0.85, 1.00, 0.99, 0.005)',
         'self.sb_tension = FloatSliderBox("张力拉伸系数", "系数", 0.70, 1.00, 0.99, 0.005)'),
        ('self.sb_copper_rho = FloatSliderBox("20℃材料电阻率", "Ω·mm²/m", 0.0150, 0.0300, 0.017094, 0.00001, decimals=6)',
         'self.sb_copper_rho = FloatSliderBox("20℃材料电阻率", "Ω·mm²/m", 0.0100, 0.0500, 0.017094, 0.00001, decimals=6)'),

        # 热工工况与电流
        ('self.sb_ambient_temp = FloatSliderBox("环境温度", "℃", -20.0, 85.0, 20.0, 0.5)',
         'self.sb_ambient_temp = FloatSliderBox("环境温度", "℃", -50.0, 180.0, 20.0, 0.5)'),
        ('self.sb_drive_current = FloatSliderBox("测试电流", "mA", 0.0, 500.0, 10.0, 1.0)',
         'self.sb_drive_current = FloatSliderBox("测试电流", "mA", 0.0, 20000.0, 10.0, 1.0)'),
        ('self.sb_convection_h = FloatSliderBox("散热对流系数", "W/(m²·K)", 5.0, 100.0, 25.0, 1.0)',
         'self.sb_convection_h = FloatSliderBox("散热对流系数", "W/(m²·K)", 1.0, 500.0, 25.0, 1.0)'),

        # DFM 约束与耐压
        ('self.sb_limit_x = FloatSliderBox("X向装配限值 (Max L)", "mm", 1.0, 30.0, 7.20, 0.05)',
         'self.sb_limit_x = FloatSliderBox("X向装配限值 (Max L)", "mm", 1.0, 600.0, 7.20, 0.05)'),
        ('self.sb_limit_y = FloatSliderBox("Y向装配限值 (Max W)", "mm", 1.0, 20.0, 3.82, 0.05)',
         'self.sb_limit_y = FloatSliderBox("Y向装配限值 (Max W)", "mm", 1.0, 400.0, 3.82, 0.05)'),
        ('self.sb_limit_z = FloatSliderBox("Z向装配限高 (Max H)", "mm", 0.2, 10.0, 1.05, 0.02)',
         'self.sb_limit_z = FloatSliderBox("Z向装配限高 (Max H)", "mm", 0.1, 150.0, 1.05, 0.02)'),
        ('self.sb_limit_v = FloatSliderBox("驱动电压上限 (Max V)", "V", 0.5, 12.0, 2.80, 0.05)',
         'self.sb_limit_v = FloatSliderBox("驱动电压上限 (Max V)", "V", 0.1, 120.0, 2.80, 0.05)'),
        ('self.sb_limit_t = FloatSliderBox("耐温安全上限", "℃", 60.0, 220.0, 155.0, 5.0)',
         'self.sb_limit_t = FloatSliderBox("耐温安全上限", "℃", 40.0, 350.0, 155.0, 5.0)'),
        ('self.sb_withstand_ground = FloatSliderBox("对地/轭铁耐压要求", "VAC", 500, 5000, 3000, 100)',
         'self.sb_withstand_ground = FloatSliderBox("对地/轭铁耐压要求", "VAC", 100, 20000, 3000, 100)'),
        ('self.sb_withstand_turn = FloatSliderBox("匝间冲击耐压要求", "V", 200, 3000, 1400, 50)',
         'self.sb_withstand_turn = FloatSliderBox("匝间冲击耐压要求", "V", 50, 10000, 1400, 50)'),
    ]

    count = 0
    for old_s, new_s in replacements:
        if old_s in mw_code:
            mw_code = mw_code.replace(old_s, new_s, 1)
            count += 1
        else:
            print(f"Warning: target not found: {old_s[:40]}...")

    print(f"Applied {count}/{len(replacements)} range replacements in main_window.py")

    with open("src/gui/main_window.py", "w", encoding="utf-8") as f:
        f.write(mw_code)
    print("Saved main_window.py")

if __name__ == "__main__":
    patch_ranges()
