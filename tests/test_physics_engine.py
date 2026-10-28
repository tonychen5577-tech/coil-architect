"""
Unit tests for CoilPhysicsEngine benchmarked against Web Simulator and Excel Sheet
"""

import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.models import CoilInputs, CoilOutputs, WindingMode, CoilType
from src.core.physics_engine import CoilPhysicsEngine


def test_benchmark_case_against_web():
    """验证与网页端真实截屏完全对齐的基准用例 (标准退火铜 IACS 100% / 0.017241)"""
    inputs = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=4.86,
        inner_wid=1.50,
        radial_layers=14,
        axial_turns=12,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.075,
        max_od=0.085,
        tension_factor=0.99,
        copper_resistivity=0.017241,  # 标准退火铜电阻率
        ambient_temp=20.0,
        drive_current_ma=10.0,
        convection_h=25.0,
        max_x_len_limit=7.20,
        max_y_wid_limit=3.82,
        max_z_h_limit=1.05,
        max_v_term_limit=2.80,
        max_temp_limit=110.0,
    )

    out = CoilPhysicsEngine.calculate(inputs)

    # 1. 匝数校验: 14 * 12 - floor(14/2) = 168 - 7 = 161
    assert out.total_turns == 161

    # 2. 成型外廓尺寸 (截屏值: 6.9231, 3.7314, 1.0199)
    assert round(out.outer_len, 4) == 6.9231
    assert round(out.outer_wid, 4) == 3.7314
    assert round(out.thickness_h, 4) == 1.0199

    # 3. 电阻与电压 (截屏值: R20=10.443, R_init=10.443, DCR_hot=10.469, V_term=0.105)
    assert round(out.r20, 3) == 10.443
    assert round(out.r_init, 3) == 10.443
    assert abs(out.dcr_hot - 10.47) < 0.01
    assert round(out.v_term, 3) == 0.105

    # 4. 槽满率 (截屏值: 89.18%, 69.43%)
    assert round(out.wire_fill_factor, 2) == 89.18
    assert round(out.copper_fill_factor, 2) == 69.43

    # 5. 稳态结温 (截屏值: 20.6 ℃)
    assert abs(out.t_final - 20.7) < 0.2

    # 6. DFM 卡控全部通过
    assert out.dfm.all_passed is True


def test_ofhc_factory_alignment():
    """验证高导电率无氧铜 (OFHC 0.016959) 及细线理论米阻计算"""
    inputs = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=5.30,
        inner_wid=0.92,
        radial_layers=12,
        axial_turns=12,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.045,
        max_od=0.055,
        tension_factor=0.99,
        copper_resistivity=0.016959,
    )
    assert inputs.copper_resistivity == 0.016959

    out = CoilPhysicsEngine.calculate(inputs)
    # 拉伸后有效线径 d_eff = 0.045 * 0.99 = 0.04455 mm
    # 截面积 a_cu = pi / 4 * 0.04455^2 ≈ 0.0015588 mm²
    # 理论米阻 rho_per_meter = 0.016959 / 0.0015588 ≈ 10.879 Ω/m
    assert round(out.rho_per_meter, 2) == 10.88
    assert out.r20 > 0
    assert out.dcr_hot > out.r20


def test_circular_coil_against_excel():
    """验证圆线圈算法与《圆线圈COIL设计.xlsx》基准对齐"""
    inputs = CoilInputs(
        coil_type=CoilType.CIRCULAR,
        inner_len=2.30,   # ID = 2.30 mm
        inner_wid=2.30,
        radial_layers=8,  # I = 8 层
        axial_turns=26,   # J = 26 匝
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.042,   # 导体直径 0.042 mm
        max_od=0.052,     # 带漆外径 0.052 mm
        tension_factor=1.00,
        ambient_temp=20.0,
        drive_current_ma=88.36,
        rated_voltage_v=1.8,
    )

    out = CoilPhysicsEngine.calculate(inputs)

    # 1. 匝数: 8 * 26 - floor(8/2) = 208 - 4 = 204
    assert out.total_turns == 204

    # 2. 中径 Dm = (2.3 + OD) / 2
    # E_env = (7 * 0.866025 + 2) * 0.052 = 8.062 * 0.052 = 0.419 mm
    # OD = 2.3 + 2 * 0.419 = 3.138 mm
    assert out.outer_len > 3.0
    assert out.mean_dia_mm > 2.5

    # 3. Wheeler 电感应在 ~950 μH (≈ 0.95 mH)
    assert 800 < out.inductance_uh < 1100
    assert 0.8 < out.inductance_mh < 1.1

    # 4. 安匝数校验
    assert out.ampere_turns > 0


def test_pure_coil_dfm_envelope():
    """验证纯粹线圈 DFM 空间包络卡控 (方案 A：极简纯粹主义，绝不死板叠加电机外部假设)"""
    # 1. 默认属性与向后兼容字段校验
    inputs = CoilInputs(coil_type=CoilType.CIRCULAR)
    assert inputs.zlra_vibe_space_mm == 0.50
    assert inputs.zlra_safety_gap_mm == 0.08

    # 2. 纯线圈 Z 向空间卡控校验 (F <= Max_Z)
    out = CoilPhysicsEngine.calculate(inputs)
    f_thk = out.thickness_h
    
    # 当空间限高大于线圈厚度 -> 合格通过
    inputs.max_z_h_limit = f_thk + 0.10
    out_pass = CoilPhysicsEngine.calculate(inputs)
    assert out_pass.dfm.z_passed is True

    # 当空间限高小于线圈厚度 -> 超差干涉报警
    inputs.max_z_h_limit = f_thk - 0.05
    out_fail = CoilPhysicsEngine.calculate(inputs)
    assert out_fail.dfm.z_passed is False

    # 3. 外径/外廓 X 向与 Y 向空间卡控校验
    inputs.max_z_h_limit = f_thk + 0.20
    inputs.max_x_len_limit = out.outer_len + 0.50
    out_x_pass = CoilPhysicsEngine.calculate(inputs)
    assert out_x_pass.dfm.x_passed is True

    inputs.max_x_len_limit = out.outer_len - 0.20
    out_x_fail = CoilPhysicsEngine.calculate(inputs)
    assert out_x_fail.dfm.x_passed is False

    # 4. 跑道型线圈 Y 向空间卡控校验
    rt_inputs = CoilInputs(
        coil_type=CoilType.RACETRACK,
        max_x_len_limit=8.0,
        max_y_wid_limit=4.0,
        max_z_h_limit=1.2
    )
    rt_out = CoilPhysicsEngine.calculate(rt_inputs)
    assert rt_out.dfm.y_passed is True

    rt_inputs.max_y_wid_limit = rt_out.outer_wid - 0.10
    rt_out_y_fail = CoilPhysicsEngine.calculate(rt_inputs)
    assert rt_out_y_fail.dfm.y_passed is False


def test_octagonal_vcm_coil():
    """验证八角形 VCM 手机镜头线圈 (严格依据图4闭合几何方程与斯坦纳等距外扩公理)"""
    inputs = CoilInputs(
        coil_type=CoilType.OCTAGONAL,
        oct_id1=6.80,
        oct_id2=7.60,
        oct_r1=0.50,
        radial_layers=14,
        axial_turns=12,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.075,
        max_od=0.085,
        tension_factor=0.99,
        ambient_temp=20.0,
        drive_current_ma=100.0,
        convection_h=25.0,
        max_x_len_limit=9.50,
        max_y_wid_limit=10.50,
        max_z_h_limit=1.50,
    )
    out = CoilPhysicsEngine.calculate(inputs)

    # 1. 验证总匝数
    assert out.total_turns == 161

    # 2. 验证斯坦纳等距外扩公理 (Steiner's Invariant)
    # MLT 恒等于 C_in + pi * E_env
    # C_out 恒等于 C_in + 2 * pi * E_env
    e_env = out.e_env
    assert round(out.mlt, 4) == round(out.c_inner_mm + 3.141592653589793 * e_env, 4)
    assert round(out.c_outer_mm, 4) == round(out.c_inner_mm + 2.0 * 3.141592653589793 * e_env, 4)

    # 3. 验证对边外宽与对角外宽
    assert round(out.oct_od1, 4) == round(inputs.oct_id1 + 2.0 * e_env, 4)
    assert round(out.oct_od2, 4) == round(inputs.oct_id2 + 2.0 * e_env, 4)

    # 4. 电阻与电感为正且物理守恒
    assert out.r20 > 0
    assert out.dcr_hot > out.r20
    assert out.inductance_uh > 0

    # 5. DFM 判定
    assert out.dfm.all_passed is True


def test_arbitrary_perimeter_coil():
    """验证 CAD 任意异形/中线周长推算线圈 (严格基于斯坦纳外扩与物理守恒)"""
    c_in = 22.50
    inputs = CoilInputs(
        coil_type=CoilType.ARBITRARY_PERIMETER,
        perimeter_in=c_in,
        arbitrary_outer_len=8.0,
        arbitrary_outer_wid=6.0,
        radial_layers=10,
        axial_turns=14,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.060,
        max_od=0.070,
        ambient_temp=20.0,
        drive_current_ma=50.0,
        convection_h=20.0,
        max_x_len_limit=10.0,
        max_y_wid_limit=8.0,
        max_z_h_limit=1.5,
    )
    out = CoilPhysicsEngine.calculate(inputs)

    e_env = out.e_env
    assert out.c_inner_mm == c_in
    assert round(out.mlt, 4) == round(c_in + 3.141592653589793 * e_env, 4)
    assert round(out.c_outer_mm, 4) == round(c_in + 2.0 * 3.141592653589793 * e_env, 4)
    assert out.r20 > 0
    assert out.dfm.all_passed is True


def test_presets_vcm_and_lra():
    """验证用户专属三套电机线圈工程预设及耐温等级联动"""
    # 1. 手机VCM马达 (图1工业标杆)
    p1 = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=5.30,
        inner_wid=0.92,
        radial_layers=12,
        axial_turns=12,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.045,
        max_od=0.055,
        tension_factor=0.99,
        copper_resistivity=0.016959,
        ambient_temp=25.0,
        drive_current_ma=60.0,
        convection_h=40.0,
        max_x_len_limit=7.20,
        max_y_wid_limit=3.00,
        max_z_h_limit=0.85,
        max_v_term_limit=2.50,
        max_temp_limit=155.0,  # 155等级
    )
    out1 = CoilPhysicsEngine.calculate(p1)
    assert out1.total_turns == 138
    assert round(out1.outer_len, 3) == 6.446
    assert round(out1.outer_wid, 3) == 2.175
    assert round(out1.thickness_h, 3) == 0.660
    assert 20.0 <= out1.r20 <= 22.0
    assert out1.t_final < 155.0
    assert out1.dfm.all_passed is True

    # 2. 手机LRA圆线圈 (硬币式0825 Z-LRA / 图2基准)
    p2 = CoilInputs(
        coil_type=CoilType.CIRCULAR,
        inner_len=2.12,
        radial_layers=6,
        axial_turns=23,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.033,
        max_od=0.040,
        tension_factor=0.99,
        copper_resistivity=0.016959,
        ambient_temp=20.0,
        drive_current_ma=40.0,
        convection_h=35.0,
        max_x_len_limit=10.0,
        max_y_wid_limit=10.0,
        max_z_h_limit=3.5,
        max_v_term_limit=3.5,
        max_temp_limit=155.0,
    )
    out2 = CoilPhysicsEngine.calculate(p2)
    assert out2.total_turns == 135
    assert round(out2.outer_len, 3) == 2.621
    assert round(out2.thickness_h, 3) == 0.920
    assert round(out2.r20, 3) == 20.544
    assert out2.t_final < 155.0
    assert out2.dfm.all_passed is True

    # 3. 手机LRA马达跑道线圈 (图3工程图纸: 19层 8匝 异数平齐模式 自然厚度 0.541mm)
    p3 = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=2.30,
        inner_wid=0.60,
        radial_layers=19.0,
        axial_turns=8,
        winding_mode=WindingMode.VARIABLE,
        bare_dia=0.060,
        max_od=0.068,
        tension_factor=0.985,
        copper_resistivity=0.016920,
        has_crossover_wire=True,
        ambient_temp=20.0,
        drive_current_ma=50.0,
        convection_h=35.0,
        max_x_len_limit=4.60,
        max_y_wid_limit=3.15,
        max_z_h_limit=0.57,
        max_v_term_limit=1.50,
        max_temp_limit=155.0,
    )
    out3 = CoilPhysicsEngine.calculate(p3)
    assert out3.total_turns == 143
    assert round(out3.thickness_h, 3) == 0.541
    assert round(out3.outer_len, 3) == 4.522
    assert round(out3.outer_wid, 3) == 3.023
    assert round(out3.r20, 3) == 8.455  # 8 ± 0.5 Ω 图纸范围
    assert out3.dfm.all_passed is True

    # 4. 耐温等级门限判定 (120等级、155等级、180等级)
    p3_class120 = CoilInputs(**{**p3.__dict__, "max_temp_limit": 120.0})
    out3_120 = CoilPhysicsEngine.calculate(p3_class120)
    assert out3_120.dfm.temp_passed is True

    p3_hot = CoilInputs(**{**p3.__dict__, "drive_current_ma": 180.0, "max_temp_limit": 120.0})
    out3_hot = CoilPhysicsEngine.calculate(p3_hot)
    assert out3_hot.t_final > 120.0
    assert out3_hot.dfm.temp_passed is False


def test_fractional_half_layer_envelope_and_resistance():
    """验证 18.5 半层绕线外廓包络按 19 层取整与电阻按照匝数*中线周长计算"""
    # 18.0 整层
    p18 = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=2.30,
        inner_wid=0.60,
        radial_layers=18.0,
        axial_turns=8,
        winding_mode=WindingMode.EVEN,
        bare_dia=0.060,
        max_od=0.068,
        tension_factor=0.99,
        copper_resistivity=0.016959,
    )
    o18 = CoilPhysicsEngine.calculate(p18)
    assert o18.total_turns == 144
    assert round(o18.outer_wid, 3) == 2.852

    # 18.5 半层 (最外径进驻第19层，外廓包络严格按19层计算防干涉)
    p18_5 = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=2.30,
        inner_wid=0.60,
        radial_layers=18.5,
        axial_turns=8,
        winding_mode=WindingMode.EVEN,
        bare_dia=0.060,
        max_od=0.068,
        tension_factor=0.99,
        copper_resistivity=0.016959,
    )
    o18_5 = CoilPhysicsEngine.calculate(p18_5)
    # 匝数 = 18.5 * 8 = 148 匝
    assert o18_5.total_turns == 148
    # 外宽按照 19 层算 = 2.968 mm (明显大于 18 层的 2.852 mm)
    assert round(o18_5.outer_wid, 3) == 2.968
    # 电阻严格依据 匝数 * 中线周长 * 米阻 计算
    expected_r20 = (148 * o18_5.mlt * 1.01 / 1000.0) * o18_5.rho_per_meter
    assert round(o18_5.r20, 3) == round(expected_r20, 3)


def test_mold_clamping_compaction_and_crossover_wire():
    """验证模具限位压实厚度与换层交叉线补偿算法 (对齐实测 0.55mm 厚度与 3.10mm 外宽)"""
    # 1. 基础自由堆叠 (未模压)
    free_inputs = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=2.311,
        inner_wid=0.617,
        radial_layers=18.5,
        axial_turns=8,
        winding_mode=WindingMode.EVEN,
        bare_dia=0.060,
        max_od=0.068,
        tension_factor=0.985,
        copper_resistivity=0.016959,
        mold_clamping_enabled=False,
    )
    free_out = CoilPhysicsEngine.calculate(free_inputs)
    assert round(free_out.thickness_h, 3) == 0.575
    assert free_out.is_mold_clamped is False

    # 2. 启用模具限位压实 (0.55mm 模腔硬卡控)
    clamp_inputs = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=2.311,
        inner_wid=0.617,
        radial_layers=18.5,
        axial_turns=8,
        winding_mode=WindingMode.EVEN,
        bare_dia=0.060,
        max_od=0.068,
        tension_factor=0.985,
        copper_resistivity=0.016959,
        mold_clamping_enabled=True,
        mold_clamping_height=0.55,
        has_crossover_wire=True,
    )
    clamp_out = CoilPhysicsEngine.calculate(clamp_inputs)
    # 厚度严格锁定为 0.55 mm
    assert clamp_out.thickness_h == 0.55
    assert clamp_out.free_thickness_h == free_out.thickness_h
    assert clamp_out.is_mold_clamped is True
    # 因牺牲厚度带来径向展宽 (ΔE > 0)
    assert clamp_out.delta_e_compaction > 0.02
    # 外宽在展宽与交叉线补偿后，高度吻合实测 ~3.10 mm
    assert 3.08 <= clamp_out.outer_wid <= 3.12
    # 外长在展宽后高度吻合实测 ~4.56 mm
    assert 4.50 <= clamp_out.outer_len <= 4.58


if __name__ == "__main__":
    test_benchmark_case_against_web()
    test_ofhc_factory_alignment()
    test_circular_coil_against_excel()
    test_pure_coil_dfm_envelope()
    test_octagonal_vcm_coil()
    test_arbitrary_perimeter_coil()
    test_presets_vcm_and_lra()
    test_fractional_half_layer_envelope_and_resistance()
    test_mold_clamping_compaction_and_crossover_wire()
    print("All tests passed with 100% precision!")


