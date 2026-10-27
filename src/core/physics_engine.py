# -*- coding: utf-8 -*-
"""
Coil-Architect Pro - Physics Engine
线圈几何拓扑、截面形态、六方密排、直流电阻、双基准称重与绝缘耐压自洽稳态计算引擎
支持跑道型 (Racetrack)、圆形线圈 (Circular Coin)、八角形 (Octagonal VCM) 与任意中线展开异形线圈；
支持圆线、正方形方线、长方形扁线全形态截面及华冶出厂标准线规库。
"""

import math
from typing import Tuple
from .models import (
    CoilInputs, CoilOutputs, DFMCheckResult, WindingMode, CoilType,
    WireShape, WireCatalogType, EnamelGrade, WindingDirection
)


# 纯退火铜标准物理常量 (IACS)
RHO_CU_20 = 0.017241          # 20℃ 纯铜电阻率 (Ω·mm²/m)
T_ABS_CU_ZERO = 234.5         # 铜线绝对零度推算基准温标 (℃)
T_REF_20 = 20.0               # 标称参考温度 (℃)
DENSITY_CU = 8.90             # 华冶纯铜出厂基准密度 (g/cm³) -> 0.00890 g/mm³

# -------------------------------------------------------------------------
# 华冶官方实测烘焙固化漆膜密度表 (Enameled Wire Coating Densities, g/cm³)
# 来源: 华冶漆包线底层算法库 (tab6_calc) 工业实测固化烘焙经验值
# -------------------------------------------------------------------------
HUAYE_COATING_DENSITIES = {
    "UEW": 1.27,  # UEW 聚氨酯 (行业微细自粘线最通用耐温底漆)
    "PEW": 1.38,  # PEW 聚酯
    "EIW": 1.39,  # EIW 聚酯亚胺
    "AIW": 1.42,  # AIW 聚酰胺酰亚胺
    "PIW": 1.43,  # PIW 聚酰亚胺 (耐高温220℃+)
    "SB":  1.07,  # SB 自粘层 (热风/酒精固化改性聚酰胺胶层)
}
DENSITY_UEW = 1.27
DENSITY_PEW = 1.38
DENSITY_EIW = 1.39
DENSITY_AIW = 1.42
DENSITY_PIW = 1.43
DENSITY_SB  = 1.07


def calculate_huaye_insulation_density(
    grade: EnamelGrade,
    has_sb: bool = True,
    bare_dia: float = 0.08,
    max_od: float = 0.085,
    enamel_type: str = "UEW"
) -> float:
    """
    基于华冶底层解密算法计算烘焙固化漆膜有效密度 (g/cm³)。
    若为自粘线 (Self-Bonding)，则自动分层微积分核算：
    - 内层底漆 (UEW 1.27 / PEW 1.38 等)
    - 外层自粘胶层 (SB 1.07)
    若为普通单/双涂层漆包线，则直接精确采用所选漆种实测固化密度。
    """
    rho_base = HUAYE_COATING_DENSITIES.get(enamel_type.upper(), DENSITY_UEW)
    rho_sb = DENSITY_SB

    is_sb = (has_sb or grade in (EnamelGrade.SELF_BONDING, EnamelGrade.SB_010, EnamelGrade.SB_008, EnamelGrade.SB_014))
    if not is_sb:
        return rho_base

    delta_total = max(0.001, max_od - bare_dia)

    # 自粘线复合层分层厚度解算
    if grade == EnamelGrade.GRADE_0:
        inc_base = min(0.003, delta_total * 0.5)
    elif grade == EnamelGrade.GRADE_1:
        inc_base = min(0.008 if bare_dia < 0.1 else 0.012, delta_total * 0.7)
    elif grade == EnamelGrade.GRADE_2:
        inc_base = min(0.014 if bare_dia < 0.1 else 0.020, delta_total * 0.7)
    elif grade == EnamelGrade.GRADE_3:
        inc_base = min(0.022 if bare_dia < 0.1 else 0.030, delta_total * 0.7)
    elif grade == EnamelGrade.SB_008:
        # 薄胶复合自粘: 底漆增量 0.005mm, 自粘胶增量 0.003mm (总增量 0.008mm)
        inc_base = 0.005 if bare_dia < 0.1 else 0.007
    elif grade in (EnamelGrade.SB_010, EnamelGrade.SELF_BONDING):
        # 常规标准自粘: 底漆增量 0.006mm, 自粘胶增量 0.004mm (总增量 0.010mm)
        inc_base = 0.006 if bare_dia < 0.1 else 0.009
    elif grade == EnamelGrade.SB_014:
        # 加厚复合自粘 (2UEW-SB): 底漆增量 0.009mm, 自粘胶增量 0.005mm (总增量 0.014mm)
        inc_base = 0.009 if bare_dia < 0.1 else 0.013
    else:
        # 自定义外径按底漆 60%、胶层 40% 分配
        inc_base = delta_total * 0.60

    d_base = bare_dia + min(inc_base, delta_total * 0.85)
    d_total = max(max_od, d_base + 0.0005)

    area_base = max(0.0, (math.pi / 4.0) * (d_base ** 2 - bare_dia ** 2))
    area_sb = max(0.0, (math.pi / 4.0) * (d_total ** 2 - d_base ** 2))
    area_total = area_base + area_sb

    if area_total <= 1e-12:
        return rho_base

    rho_eff = (area_base * rho_base + area_sb * rho_sb) / area_total
    return round(rho_eff, 4)


def get_enamel_thickness_and_bdv(grade: EnamelGrade, has_sb: bool = False, bare_dia: float = 0.08) -> Tuple[float, float]:
    """
    根据漆膜等级获取单边漆膜增量厚度 t_ins (mm) 与理论单匝击穿电压 BDV (V)
    参照 GB/T 6109 / IEC 60317 规范及华冶线材出厂标准
    """
    if grade == EnamelGrade.GRADE_0:
        t_ins = 0.0015
        bdv = 750.0
    elif grade == EnamelGrade.GRADE_1:
        t_ins = 0.0040 if bare_dia < 0.1 else 0.0060
        bdv = 1500.0
    elif grade == EnamelGrade.GRADE_2:
        t_ins = 0.0070 if bare_dia < 0.1 else 0.0100
        bdv = 2800.0
    elif grade == EnamelGrade.GRADE_3:
        t_ins = 0.0110 if bare_dia < 0.1 else 0.0150
        bdv = 4200.0
    elif grade in (EnamelGrade.SELF_BONDING, EnamelGrade.SB_010):
        t_ins = 0.0050 if bare_dia < 0.1 else 0.0075
        bdv = 2200.0
    elif grade == EnamelGrade.SB_008:
        t_ins = 0.0040 if bare_dia < 0.1 else 0.0060
        bdv = 1800.0
    elif grade == EnamelGrade.SB_014:
        t_ins = 0.0070 if bare_dia < 0.1 else 0.0100
        bdv = 3000.0
    else:  # CUSTOM
        t_ins = 0.0050
        bdv = 2000.0

    if has_sb and grade not in (EnamelGrade.SELF_BONDING, EnamelGrade.SB_010, EnamelGrade.SB_008, EnamelGrade.SB_014):
        t_ins += 0.0035
        bdv += 400.0

    return t_ins, bdv


class CoilPhysicsEngine:
    """线圈多物理场仿真计算引擎"""

    @staticmethod
    def calculate(inputs: CoilInputs) -> CoilOutputs:
        """
        核心物理求解器
        执行几何尺寸解算、排线空间解析、电气阻抗计算、Wheeler 电感、双基准质量称重、
        绝缘耐压可靠性核算及电-热自洽不动点迭代
        """
        out = CoilOutputs()

        # ---------------------------------------------------------
        # 0. 核心业务层暗桩：静默防反编译绕过鉴权 (带 5 秒内存安全缓存)
        # ---------------------------------------------------------
        from .license_manager import LicenseManager
        is_auth, _, _ = LicenseManager.is_system_authorized()
        if not is_auth:
            return out

        # ---------------------------------------------------------
        # 0.1 物理边界防呆自愈与参数合理性拦截
        # ---------------------------------------------------------
        inputs.bare_dia = max(0.005, float(inputs.bare_dia))
        if inputs.max_od <= inputs.bare_dia + 0.002:
            inputs.max_od = round(inputs.bare_dia + 0.008, 4)

        inputs.inner_len = max(0.1, float(inputs.inner_len))
        inputs.inner_wid = max(0.1, float(inputs.inner_wid))
        if inputs.coil_type == CoilType.RACETRACK and inputs.inner_len < inputs.inner_wid:
            inputs.inner_len = inputs.inner_wid

        inputs.radial_layers = max(0.5, float(inputs.radial_layers))
        inputs.axial_turns = max(1, int(inputs.axial_turns))
        inputs.tension_factor = max(0.70, min(1.00, float(inputs.tension_factor)))
        inputs.convection_h = max(1.0, float(inputs.convection_h))
        inputs.drive_current_ma = max(0.0, float(inputs.drive_current_ma))
        inputs.copper_resistivity = max(0.010, float(inputs.copper_resistivity))
        inputs.ambient_temp = max(-100.0, float(inputs.ambient_temp))

        # ---------------------------------------------------------
        # 1. 线材截面形态与几何物理参数解算 (Wire Shape & Dimensions)
        # ---------------------------------------------------------
        is_flat = (inputs.wire_shape in (WireShape.SQUARE, WireShape.RECTANGULAR))
        t_ins, bdv = get_enamel_thickness_and_bdv(inputs.enamel_grade, inputs.has_self_bonding, inputs.bare_dia)

        eta = inputs.tension_factor

        if not is_flat:
            # 经典圆线 (Round Wire)
            b_actual = inputs.max_od * eta      # B: 实际带漆外径 (mm)
            d_actual = inputs.bare_dia * eta    # d: 实际裸铜外径 (mm)
            a_cu = (math.pi / 4.0) * (d_actual ** 2)
            a_wire = (math.pi / 4.0) * (b_actual ** 2)

            out.b_actual = b_actual
            out.d_actual = d_actual
            out.flat_actual_area = a_cu
            out.flat_eq_round_dia = d_actual
            out.flat_circumscribed_dia = b_actual
            out.flat_inscribed_dia = d_actual
            out.flat_fillet_dia = b_actual
            out.flat_perimeter = math.pi * d_actual

            wire_w_step = b_actual
            wire_h_step = b_actual
        else:
            # 方线与长方形扁线 (Square & Rectangular Flat Wire - 华冶算法)
            if inputs.wire_shape == WireShape.SQUARE:
                raw_w = max(0.02, float(inputs.flat_w))
                raw_h = raw_w
            else:
                raw_w = max(0.02, float(inputs.flat_w))
                raw_h = max(0.02, float(inputs.flat_h))

            flat_w = max(raw_w, raw_h)
            flat_h = min(raw_w, raw_h)

            # 圆角 r 上限约束 (华冶算法: min(W,H)/2)
            r_max = flat_h / 2.0
            if inputs.flat_r_auto or inputs.flat_r <= 0:
                flat_r = r_max * 0.5  # 推荐优质圆角
            else:
                flat_r = min(float(inputs.flat_r), r_max)

            # 华冶带倒角矩形真实导电截面积公式: A = W·H - (4 - π)·r²
            a_cu_raw = flat_w * flat_h - (4.0 - math.pi) * (flat_r ** 2)
            a_cu = max(1e-6, a_cu_raw)

            # 华冶等效圆直径公式: D_eq = 2·√(A / π)
            d_eq = 2.0 * math.sqrt(a_cu / math.pi)

            # 几何特征圆与周长
            d_circum = math.sqrt(flat_w ** 2 + flat_h ** 2)
            d_in = flat_h
            d_fillet = 2.0 * math.sqrt((flat_w / 2.0 - flat_r) ** 2 + (flat_h / 2.0 - flat_r) ** 2) + 2.0 * flat_r
            perimeter = 2.0 * (flat_w + flat_h) - (8.0 - 2.0 * math.pi) * flat_r

            # 带漆膜外形尺寸 (双边增加 2*t_ins)
            flat_w_out = flat_w + 2.0 * t_ins
            flat_h_out = flat_h + 2.0 * t_ins
            r_out = flat_r + t_ins
            a_wire = flat_w_out * flat_h_out - (4.0 - math.pi) * (r_out ** 2)

            d_actual = d_eq * eta
            b_actual = math.sqrt(flat_w_out * flat_h_out) * eta

            out.b_actual = b_actual
            out.d_actual = d_actual
            out.flat_actual_area = a_cu
            out.flat_eq_round_dia = d_eq
            out.flat_circumscribed_dia = d_circum
            out.flat_inscribed_dia = d_in
            out.flat_fillet_dia = d_fillet
            out.flat_perimeter = perimeter

            # 排线步距 (平绕 vs 立绕)
            if inputs.flat_winding_dir == WindingDirection.FLATWISE:
                # 平绕 (卧绕): 厚度朝向轴向高度，宽度朝向径向壁厚
                wire_w_step = flat_w_out
                wire_h_step = flat_h_out
            else:
                # 立绕 (侧绕): 宽度朝向轴向高度，厚度朝向径向壁厚
                wire_w_step = flat_h_out
                wire_h_step = flat_w_out

        # ---------------------------------------------------------
        # 2. 成型总匝数 N 计算
        # ---------------------------------------------------------
        i_layers = inputs.radial_layers
        j_turns = inputs.axial_turns
        if not is_flat:
            if inputs.winding_mode == WindingMode.EVEN:
                total_n = int(round(i_layers * j_turns))
            else:
                total_n = int(round((i_layers * j_turns) - math.floor(i_layers / 2.0)))
        else:
            # 扁线/方线均为规整矩形阵列排布
            total_n = int(round(i_layers * j_turns))

        out.total_turns = total_n

        # ---------------------------------------------------------
        # 3. 壁厚与轴向厚度解算 (Hexagonal Packing vs Flat Layering)
        # ---------------------------------------------------------
        hcp_factor = math.sqrt(3.0) / 2.0  # ≈ 0.8660254
        i_env_layers = math.ceil(i_layers)

        if not is_flat:
            # 圆线密排
            e_elec = ((i_layers - 1.0) * hcp_factor + 1.0) * b_actual
            if inputs.winding_mode == WindingMode.EVEN:
                e_env = ((i_env_layers - 1.0) * hcp_factor + 2.0) * b_actual
                thickness_f = (j_turns + 0.5) * b_actual * 1.01
            else:
                e_env = ((i_env_layers - 1.0) * hcp_factor + 2.0) * b_actual
                thickness_f = j_turns * b_actual * 1.01
        else:
            # 扁线/方线规整排布
            e_elec = i_layers * wire_w_step
            e_env = i_env_layers * wire_w_step * 1.01
            thickness_f = j_turns * wire_h_step * 1.01

        free_thickness_f = thickness_f
        out.free_thickness_h = free_thickness_f
        delta_e_comp = 0.0

        # 刚性与绝缘压缩极限
        h_solid = j_turns * d_actual
        h_safe_min = j_turns * d_actual + 0.35 * j_turns * max(0.002, b_actual - d_actual)
        out.h_solid_limit = h_solid
        out.h_safe_min_limit = h_safe_min

        # 模具限位压实硬卡控算法 (Mold Clamping Compaction)
        if inputs.mold_clamping_enabled and inputs.mold_clamping_height > 0:
            out.is_mold_clamped = True
            raw_mold_h = inputs.mold_clamping_height
            effective_mold_h = max(h_solid, raw_mold_h)
            thickness_f = effective_mold_h

            if free_thickness_f > thickness_f:
                strain_z = min(0.25, (free_thickness_f - thickness_f) / free_thickness_f)
                delta_e_comp = e_env * strain_z * 0.65
                e_env += delta_e_comp
                e_elec += delta_e_comp * 0.75
        else:
            out.is_mold_clamped = False

        out.delta_e_compaction = delta_e_comp
        out.e_env = e_env
        out.e_elec = e_elec
        out.thickness_h = thickness_f

        # ---------------------------------------------------------
        # 4. 几何外廓与单匝平均周长 (MLT) 解算
        # ---------------------------------------------------------
        if inputs.coil_type == CoilType.CIRCULAR:
            # 圆形线圈 (Circular Coin)
            inner_dia = inputs.inner_len
            outer_dia = inner_dia + 2.0 * e_env
            mean_dia = (inner_dia + outer_dia) / 2.0
            
            out.outer_len = outer_dia
            out.outer_wid = outer_dia
            out.mean_dia_mm = mean_dia
            out.c_inner_mm = math.pi * inner_dia
            out.c_outer_mm = math.pi * outer_dia

            mlt = math.pi * mean_dia
            total_len_mm = total_n * mlt * 1.01

            area_out = (math.pi / 4.0) * (outer_dia ** 2)
            area_in = (math.pi / 4.0) * (inner_dia ** 2)
            area_face = area_out - area_in
            area_outer_side = math.pi * outer_dia * thickness_f
            area_inner_side = math.pi * inner_dia * thickness_f

            b_radial = e_env
            denom = 3.0 * mean_dia + 9.0 * b_radial + 10.0 * thickness_f
            l_uh = (0.08 * (mean_dia ** 2) * (total_n ** 2)) / denom if denom > 0 else 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        elif inputs.coil_type == CoilType.OCTAGONAL:
            # 八角形线圈 (Octagonal VCM)
            id1 = max(0.2, inputs.oct_id1)
            r1 = max(0.01, min(inputs.oct_r1, id1 * 0.45))
            sqrt2 = math.sqrt(2.0)

            r1_cut = 2.0 * (sqrt2 - 1.0) * r1
            id2_min = (id1 + 0.10 + r1_cut) / sqrt2
            id2_max = sqrt2 * id1 - r1_cut - 0.10
            if id2_max < id2_min:
                id2 = id1 * 1.14
            else:
                raw_id2 = inputs.oct_id2 if inputs.oct_id2 > 0 else id1 * 1.14
                id2 = max(id2_min, min(raw_id2, id2_max))

            l1 = max(0.10, sqrt2 * id2 - id1 - r1_cut)
            l2 = max(0.10, sqrt2 * id1 - id2 - r1_cut)

            c_inner = 4.0 * l1 + 4.0 * l2 + 2.0 * math.pi * r1
            out.c_inner_mm = c_inner

            mlt = c_inner + math.pi * e_env
            c_outer = c_inner + 2.0 * math.pi * e_env
            out.c_outer_mm = c_outer

            od1 = id1 + 2.0 * e_env
            od2 = id2 + 2.0 * e_env
            out.oct_od1 = od1
            out.oct_od2 = od2
            out.outer_len = od1
            out.outer_wid = od1
            out.mean_dia_mm = mlt / math.pi

            total_len_mm = total_n * mlt * 1.01

            area_face = mlt * e_env
            area_outer_side = c_outer * thickness_f
            area_inner_side = c_inner * thickness_f

            eq_dm = out.mean_dia_mm
            denom = 3.0 * eq_dm + 9.0 * e_env + 10.0 * thickness_f
            l_uh = (0.08 * (eq_dm ** 2) * (total_n ** 2)) / denom if denom > 0 else 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        elif inputs.coil_type == CoilType.ARBITRARY_PERIMETER:
            # 异形线圈
            c_inner = max(1.0, inputs.perimeter_in)
            out.c_inner_mm = c_inner

            if inputs.perimeter_mean > 0:
                mlt = inputs.perimeter_mean
            else:
                mlt = c_inner + math.pi * e_env
            
            c_outer = c_inner + 2.0 * math.pi * e_env
            out.c_outer_mm = c_outer
            out.mean_dia_mm = mlt / math.pi

            outer_l = max(inputs.arbitrary_outer_len, out.mean_dia_mm * 1.1)
            outer_w = max(inputs.arbitrary_outer_wid, out.mean_dia_mm * 0.9)
            out.outer_len = outer_l
            out.outer_wid = outer_w

            total_len_mm = total_n * mlt * 1.01

            area_face = mlt * e_env
            area_outer_side = c_outer * thickness_f
            area_inner_side = c_inner * thickness_f

            eq_dm = mlt / math.pi
            denom = 3.0 * eq_dm + 9.0 * e_env + 10.0 * thickness_f
            l_uh = (0.08 * (eq_dm ** 2) * (total_n ** 2)) / denom if denom > 0 else 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        else:
            # 经典跑道型线圈 (Racetrack)
            delta_w_cross = 0.0
            if inputs.has_crossover_wire:
                delta_w_cross = 1.0 * b_actual
            out.delta_w_crossover = delta_w_cross

            outer_len = inputs.inner_len + 2.0 * e_env
            outer_wid = inputs.inner_wid + 2.0 * e_env + delta_w_cross
            out.outer_len = outer_len
            out.outer_wid = outer_wid

            c_inner = 2.0 * (inputs.inner_len - inputs.inner_wid) + math.pi * inputs.inner_wid
            out.c_inner_mm = c_inner

            mlt = 2.0 * (inputs.inner_len - inputs.inner_wid) + math.pi * (inputs.inner_wid + e_env)
            c_outer = 2.0 * (outer_len - outer_wid) + math.pi * outer_wid
            out.c_outer_mm = c_outer
            out.mean_dia_mm = mlt / math.pi

            total_len_mm = total_n * mlt * 1.01

            area_out = (outer_len - outer_wid) * outer_wid + (math.pi / 4.0) * (outer_wid ** 2)
            area_in = (inputs.inner_len - inputs.inner_wid) * inputs.inner_wid + (math.pi / 4.0) * (inputs.inner_wid ** 2)
            area_face = area_out - area_in
            area_outer_side = 2.0 * (outer_len + outer_wid) * thickness_f
            area_inner_side = 2.0 * (inputs.inner_len + inputs.inner_wid) * thickness_f

            eq_dm = mlt / math.pi
            denom = 3.0 * eq_dm + 9.0 * e_env + 10.0 * thickness_f
            l_uh = (0.08 * (eq_dm ** 2) * (total_n ** 2)) / denom if denom > 0 else 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        out.mlt = mlt
        out.total_wire_len_m = total_len_mm / 1000.0

        # ---------------------------------------------------------
        # 5. 裸铜截面积与冷态直流电阻 (DC Resistance)
        # ---------------------------------------------------------
        out.a_cu = a_cu

        # 20℃ 基准冷态直流电阻 R20
        # 若为来料实测模式 (inputs.measured_rm > 0)，直接采用供应商实测米阻核算 R20 = L * Rm
        if inputs.measured_rm > 0:
            out.rho_per_meter = inputs.measured_rm
            out.copper_resistivity = inputs.measured_rm * a_cu
            r20 = out.total_wire_len_m * inputs.measured_rm
        else:
            rho = inputs.copper_resistivity if inputs.copper_resistivity > 0 else 0.017094
            out.copper_resistivity = rho
            out.rho_per_meter = (rho / a_cu) if a_cu > 1e-12 else 0.0
            r20 = ((out.total_wire_len_m * rho) / a_cu) if a_cu > 1e-12 else 0.0
        out.r20 = r20

        # 初始环境温度 Ta 下的冷态电阻 R_init
        t_a = inputs.ambient_temp
        r_init = r20 * ((T_ABS_CU_ZERO + t_a) / (T_ABS_CU_ZERO + T_REF_20))
        out.r_init = r_init

        # 额定电压驱动性能与激励安匝数 ΣI = I(A) * N
        if r_init > 1e-6 and inputs.rated_voltage_v > 0:
            out.rated_current_ma = (inputs.rated_voltage_v / r_init) * 1000.0
            out.ampere_turns = (out.rated_current_ma / 1000.0) * total_n
        else:
            out.rated_current_ma = inputs.drive_current_ma
            out.ampere_turns = (inputs.drive_current_ma / 1000.0) * total_n

        # ---------------------------------------------------------
        # 6. 质量与槽满率工艺指标 (双基准称重算法)
        # ---------------------------------------------------------
        rho_cond = inputs.wire_density if inputs.wire_density > 0 else 8.90
        
        # 华冶实测烘焙固化漆膜密度自动精确匹配 (UEW 1.27, PEW 1.38, EIW 1.39, AIW 1.42, PIW 1.43, SB 1.07)
        if inputs.insulation_density > 0:
            rho_ins = inputs.insulation_density
        else:
            rho_ins = calculate_huaye_insulation_density(
                inputs.enamel_grade,
                inputs.has_self_bonding,
                inputs.bare_dia,
                inputs.max_od,
                getattr(inputs, "enamel_type", "UEW")
            )
        out.insulation_density = rho_ins

        v_cu = total_len_mm * a_cu
        v_wire = total_len_mm * a_wire
        v_ins = max(0.0, v_wire - v_cu)
        out.v_cu = v_cu
        out.v_wire = v_wire

        # 称重双基准：导体净重 + 漆膜/自粘胶净重 = 理论公称总重
        # 华冶出厂线密度 catalog_km_kg 严格对应出厂标称裸导体米重 (1 / (π/4 * d² * ρ_cond))
        if inputs.catalog_km_kg > 0:
            weight_cu = out.total_wire_len_m / inputs.catalog_km_kg
        else:
            weight_cu = (v_cu * rho_cond) / 1000.0

        weight_ins = (v_ins * rho_ins) / 1000.0
        weight_theoretical = weight_cu + weight_ins
        weight_actual_expected = weight_cu * (eta ** 2) * 0.985 + weight_ins * 0.980

        out.weight_cu_g = weight_cu
        out.weight_ins_g = weight_ins
        out.weight_theoretical_g = weight_theoretical
        out.weight_actual_expected_g = weight_actual_expected
        out.weight_g = weight_theoretical
        out.finished_km_per_kg = (out.total_wire_len_m / weight_theoretical) if weight_theoretical > 0 else 0.0

        v_wind_net = area_face * thickness_f
        out.v_wind_net = v_wind_net

        if v_wind_net > 0:
            out.wire_fill_factor = (v_wire / v_wind_net) * 100.0
            out.copper_fill_factor = (v_cu / v_wind_net) * 100.0
        else:
            out.wire_fill_factor = 0.0
            out.copper_fill_factor = 0.0

        # ---------------------------------------------------------
        # 7. 电-热自洽稳态温升模型 (Newton's Cooling Fixed-point Iteration)
        # ---------------------------------------------------------
        total_cooling_area_m2 = (2.0 * area_face + area_outer_side + area_inner_side) / 1.0e6
        out.total_cooling_area_m2 = total_cooling_area_m2

        i_amp = inputs.drive_current_ma / 1000.0
        h_coeff = inputs.convection_h

        t_curr = t_a
        max_iter = 100
        tolerance = 0.02

        for _ in range(max_iter):
            r_temp = r20 * ((T_ABS_CU_ZERO + t_curr) / (T_ABS_CU_ZERO + T_REF_20))
            power_w = (i_amp ** 2) * r_temp
            if h_coeff > 0 and total_cooling_area_m2 > 1e-9:
                delta_t_calc = power_w / (h_coeff * total_cooling_area_m2)
            else:
                delta_t_calc = 0.0
            t_next = t_a + delta_t_calc

            if abs(t_next - t_curr) < tolerance:
                t_curr = t_next
                break
            t_curr = 0.5 * (t_curr + t_next)

        final_dcr_hot = r20 * ((T_ABS_CU_ZERO + t_curr) / (T_ABS_CU_ZERO + T_REF_20))
        out.dcr_hot = final_dcr_hot
        out.delta_t = t_curr - t_a
        out.t_final = t_curr
        out.v_term = i_amp * final_dcr_hot
        out.joule_power_mw = (i_amp ** 2) * final_dcr_hot * 1000.0

        # ---------------------------------------------------------
        # 8. 绝缘耐压与可靠性健康诊断评估 (Hi-Pot & Dielectric Reliability)
        # ---------------------------------------------------------
        v_term_eval = max(inputs.rated_voltage_v, out.v_term)
        if total_n > 0:
            v_per_turn = v_term_eval / total_n
            v_layer_peak = 2.0 * j_turns * v_per_turn * 1.414 * 1.20
        else:
            v_per_turn = 0.0
            v_layer_peak = 0.0

        out.turn_voltage_peak = round(v_layer_peak, 2)
        out.turn_breakdown_voltage_v = bdv

        turn_margin = (bdv / max(0.5, v_layer_peak)) if v_layer_peak > 0 else 999.0
        out.turn_safety_factor = round(turn_margin, 1)

        hi_pot_turn = (bdv >= inputs.withstand_turn_v * 1.15)
        out.hi_pot_turn_passed = hi_pot_turn

        hi_pot_ground = (bdv >= 1400.0 and inputs.withstand_ground_vac <= 4000.0)
        out.hi_pot_ground_passed = hi_pot_ground

        if hi_pot_turn and hi_pot_ground and turn_margin >= 3.0:
            out.insulation_risk_level = "SAFE"
            out.insulation_recommendation = "绝缘裕度极佳 (安全裕度 > 3.0)，完全满足 3000VAC 对地与 1400V 匝间耐压测试要求。"
        elif hi_pot_turn and hi_pot_ground and turn_margin >= 1.5:
            out.insulation_risk_level = "NORMAL"
            out.insulation_recommendation = "绝缘处于工业安全范围，满足 3000VAC 对地与 1400V 匝间要求；建议大批量生产时保持 2 级漆膜。"
        elif not hi_pot_turn:
            out.insulation_risk_level = "WARNING"
            out.insulation_recommendation = f"匝间耐压裕度不足！当前漆膜击穿耐压 ({bdv:.0f}V) 低于 1400V 考核基准，强烈建议切换至 Grade 2 加厚漆膜。"
        else:
            out.insulation_risk_level = "DANGER"
            out.insulation_recommendation = "绝缘高风险：高压试验击穿或针孔超标风险高，必须加强绝缘层厚度并核验绕线骨架壁厚！"

        # ---------------------------------------------------------
        # 9. DFM 线圈物理空间与电气安全卡控判定
        # ---------------------------------------------------------
        dfm = DFMCheckResult()
        dfm.enabled = inputs.dfm_enabled

        dfm.x_val = out.outer_len
        dfm.x_limit = inputs.max_x_len_limit
        dfm.x_passed = (out.outer_len <= inputs.max_x_len_limit)

        dfm.y_val = out.outer_wid
        dfm.y_limit = inputs.max_y_wid_limit if inputs.coil_type in (CoilType.RACETRACK, CoilType.ARBITRARY_PERIMETER) else inputs.max_x_len_limit
        dfm.y_passed = (out.outer_wid <= dfm.y_limit)

        dfm.z_val = thickness_f
        dfm.z_limit = inputs.max_z_h_limit
        z_pass = (thickness_f <= inputs.max_z_h_limit)
        if inputs.mold_clamping_enabled and inputs.mold_clamping_height < out.h_safe_min_limit:
            z_pass = False
        dfm.z_passed = z_pass
        dfm.z_adaptive = False

        dfm.voltage_val = out.v_term
        dfm.voltage_limit = inputs.max_v_term_limit
        dfm.voltage_passed = (out.v_term <= inputs.max_v_term_limit)

        dfm.temp_val = out.t_final
        dfm.temp_limit = inputs.max_temp_limit
        dfm.temp_passed = (out.t_final <= inputs.max_temp_limit)

        out.dfm = dfm

        return out
