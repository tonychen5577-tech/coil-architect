"""
Coil-Architect Pro - Physics Engine
线圈几何拓扑、六方密排、直流电阻、质量槽满率与电热自洽稳态计算引擎
支持跑道型 (Racetrack) 与圆形线圈 (Circular Coin) 双拓扑架构
内置 Wheeler 多层空心圆线圈高频电感解析解与安匝数磁动势解算
"""

import math
from typing import Tuple
from .models import CoilInputs, CoilOutputs, DFMCheckResult, WindingMode, CoilType


# 纯退火铜标准物理常量 (IACS)
RHO_CU_20 = 0.017241          # 20℃ 纯铜电阻率 (Ω·mm²/m)
T_ABS_CU_ZERO = 234.5         # 铜线绝对零度推算基准温标 (℃)
T_REF_20 = 20.0               # 标称参考温度 (℃)
DENSITY_CU = 8.93             # 纯铜密度 (g/cm³) -> 0.00893 g/mm³
DENSITY_INS = 1.20            # 自粘绝缘漆皮密度 (g/cm³) -> 0.00120 g/mm³


class CoilPhysicsEngine:
    """线圈多物理场仿真计算引擎"""

    @staticmethod
    def calculate(inputs: CoilInputs) -> CoilOutputs:
        """
        核心物理求解器
        执行几何尺寸解算、排线空间解析、电气阻抗计算、Wheeler 电感、质量槽满率及电-热自洽不动点迭代
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
        # 保证裸径与外径具有物理安全下限与合理性 (杜绝零截面或负漆膜)
        inputs.bare_dia = max(0.005, float(inputs.bare_dia))
        if inputs.max_od <= inputs.bare_dia + 0.002:
            inputs.max_od = round(inputs.bare_dia + 0.008, 4)

        # 跑道型线圈几何公理：内长必须大于等于内宽
        inputs.inner_len = max(0.1, float(inputs.inner_len))
        inputs.inner_wid = max(0.1, float(inputs.inner_wid))
        if inputs.coil_type == CoilType.RACETRACK and inputs.inner_len < inputs.inner_wid:
            inputs.inner_len = inputs.inner_wid

        inputs.radial_layers = max(0.5, float(inputs.radial_layers))
        inputs.axial_turns = max(1, int(inputs.axial_turns))
        inputs.tension_factor = max(0.80, min(1.00, float(inputs.tension_factor)))
        inputs.convection_h = max(1.0, float(inputs.convection_h))
        inputs.drive_current_ma = max(0.0, float(inputs.drive_current_ma))
        inputs.copper_resistivity = max(0.010, float(inputs.copper_resistivity))
        inputs.ambient_temp = max(-100.0, float(inputs.ambient_temp))

        # ---------------------------------------------------------
        # 1. 漆包线张力拉伸修正 (Tension Stretch)
        # ---------------------------------------------------------

        eta = inputs.tension_factor
        b_actual = inputs.max_od * eta      # B: 实际带漆外径 (mm)
        d_actual = inputs.bare_dia * eta    # d: 实际裸铜外径 (mm)
        out.b_actual = b_actual
        out.d_actual = d_actual

        # ---------------------------------------------------------
        # 2. 成型总匝数 N 计算
        # ---------------------------------------------------------
        i_layers = inputs.radial_layers
        j_turns = inputs.axial_turns
        if inputs.winding_mode == WindingMode.EVEN:
            # Mode 0: 同数绕线 (6-6-6-6 每层相同匝数)
            total_n = int(round(i_layers * j_turns))
        else:
            # Mode 1: 异数绕线 (6-5-6-5 六方密排 HCP，奇数层缩进1匝，端面平齐)
            total_n = int(round((i_layers * j_turns) - math.floor(i_layers / 2.0)))
        out.total_turns = total_n

        # ---------------------------------------------------------
        # 3. 壁厚与轴向厚度解算 (Hexagonal Packing & Expansion)
        # ---------------------------------------------------------
        hcp_factor = math.sqrt(3.0) / 2.0  # ≈ 0.8660254

        # 单边电气中心壁厚 (用于内圈至中心线与周长解算)
        e_elec = ((i_layers - 1.0) * hcp_factor + 1.0) * b_actual
        out.e_elec = e_elec

        # 物理外包络层数：存在半层时，最外径已进驻整层，按 math.ceil 向上取整以确保装配与模具防干涉
        i_env_layers = math.ceil(i_layers)

        # 单边外包络物理壁厚 (用于模具与外壳干涉判定，按最外层包络取值)
        if inputs.winding_mode == WindingMode.EVEN:
            e_env = ((i_env_layers - 1.0) * hcp_factor + 2.0) * b_actual
            thickness_f = (j_turns + 0.5) * b_actual * 1.01
        else:
            e_env = ((i_env_layers - 1.0) * hcp_factor + 2.0) * b_actual
            thickness_f = j_turns * b_actual * 1.01

        # 记录自由堆叠理论未压缩厚度
        free_thickness_f = thickness_f
        out.free_thickness_h = free_thickness_f
        delta_e_comp = 0.0

        # 计算轴向压实的物理与工艺下限极限 (Solid Copper Limit & Safe Insulation Limit)
        # 1. 纯铜实心刚性极限: J 匝裸铜绝对不可压缩硬下限 (穿透此极限将压断铜芯或损坏模具)
        h_solid = j_turns * d_actual
        # 2. 工艺绝缘安全压缩下限: 至少保留底漆绝缘层厚度 (防止12V耐压击穿冒红)
        h_safe_min = j_turns * d_actual + 0.35 * j_turns * max(0.002, b_actual - d_actual)
        out.h_solid_limit = h_solid
        out.h_safe_min_limit = h_safe_min

        # 模具限位压实硬卡控算法 (Mold Clamping Compaction)
        if inputs.mold_clamping_enabled and inputs.mold_clamping_height > 0:
            out.is_mold_clamped = True
            raw_mold_h = inputs.mold_clamping_height
            # 严格物理下限保护：模具实际压入厚度不可低于纯铜刚性极限 h_solid
            effective_mold_h = max(h_solid, raw_mold_h)
            thickness_f = effective_mold_h

            # 当模具强力压实且限高小于自由堆叠厚度时 (牺牲厚度，展宽宽度):
            if free_thickness_f > thickness_f:
                # 限制最大工程压缩应变不超过 25%，防止非理性发散
                strain_z = min(0.25, (free_thickness_f - thickness_f) / free_thickness_f)
                # 复合漆膜树脂流动填隙衰减系数 ~0.65
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
            inner_dia = inputs.inner_len   # 内径 ID
            outer_dia = inner_dia + 2.0 * e_env # 外径 OD
            mean_dia = (inner_dia + outer_dia) / 2.0 # 平均中径 D_m
            
            out.outer_len = outer_dia
            out.outer_wid = outer_dia
            out.mean_dia_mm = mean_dia
            out.c_inner_mm = math.pi * inner_dia
            out.c_outer_mm = math.pi * outer_dia

            # 圆形单匝平均周长 MLT = π * D_m
            mlt = math.pi * mean_dia
            total_len_mm = total_n * mlt * 1.01

            # 绕线槽与表面积几何
            area_out = (math.pi / 4.0) * (outer_dia ** 2)
            area_in = (math.pi / 4.0) * (inner_dia ** 2)
            area_face = area_out - area_in
            area_outer_side = math.pi * outer_dia * thickness_f
            area_inner_side = math.pi * inner_dia * thickness_f

            # Wheeler 多层空心圆线圈电感公式 (Brooks / Wheeler approximation)
            # L(μH) = [0.08 * D_m² * N²] / [3*D_m + 9*b + 10*t]  (尺寸单位: mm)
            b_radial = e_env
            denom = 3.0 * mean_dia + 9.0 * b_radial + 10.0 * thickness_f
            if denom > 0:
                l_uh = (0.08 * (mean_dia ** 2) * (total_n ** 2)) / denom
            else:
                l_uh = 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        elif inputs.coil_type == CoilType.OCTAGONAL:
            # -----------------------------------------------------
            # 八角形线圈 (Octagonal VCM: 经典手机摄像头模组 AF/OIS 线圈)
            # 严格依据图4工程规范: 对边内径 ID1, 对角内径 ID2, 平直内长 L1, 斜边内长 L2, 拐角内圆角 R1
            # -----------------------------------------------------
            id1 = max(0.2, inputs.oct_id1)
            r1 = max(0.01, min(inputs.oct_r1, id1 * 0.45))
            sqrt2 = math.sqrt(2.0)

            # 严格几何闭合解析解 (45°正切角倒角八边形)
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

            # 内轮廓周长 C_in = 4*L1 + 4*L2 + 2*π*R1 (8个45°拐角圆弧合成完整圆周)
            c_inner = 4.0 * l1 + 4.0 * l2 + 2.0 * math.pi * r1
            out.c_inner_mm = c_inner

            # 依据柯西-斯坦纳等距外扩定理 (Steiner's Formula):
            # 任意凸闭合曲线向外法向外扩壁厚 E, 其外周长恒为 C_in + 2*π*E
            # 单匝平均中线周长 MLT 恒为 C_in + π*E_env
            mlt = c_inner + math.pi * e_env
            c_outer = c_inner + 2.0 * math.pi * e_env
            out.c_outer_mm = c_outer

            # 外轮廓尺寸 (对边外宽与对角外宽)
            od1 = id1 + 2.0 * e_env
            od2 = id2 + 2.0 * e_env
            out.oct_od1 = od1
            out.oct_od2 = od2
            out.outer_len = od1
            out.outer_wid = od1
            out.mean_dia_mm = mlt / math.pi  # 等效展开中径

            total_len_mm = total_n * mlt * 1.01

            # 表面积与散热几何 (帕普斯定理与斯坦纳外扩)
            area_face = mlt * e_env
            area_outer_side = c_outer * thickness_f
            area_inner_side = c_inner * thickness_f

            # 等效圆电感估算 (Wheeler)
            eq_dm = out.mean_dia_mm
            denom = 3.0 * eq_dm + 9.0 * e_env + 10.0 * thickness_f
            if denom > 0:
                l_uh = (0.08 * (eq_dm ** 2) * (total_n ** 2)) / denom
            else:
                l_uh = 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        elif inputs.coil_type == CoilType.ARBITRARY_PERIMETER:
            # -----------------------------------------------------
            # 通用中线周长 / 任意异形线圈 (Perimeter-based: 直接输入 CAD 展开周长)
            # -----------------------------------------------------
            if inputs.perimeter_in > 0:
                c_inner = inputs.perimeter_in
                mlt = c_inner + math.pi * e_env
                c_outer = c_inner + 2.0 * math.pi * e_env
            elif inputs.perimeter_mean > 0:
                mlt = inputs.perimeter_mean
                c_inner = max(0.1, mlt - math.pi * e_env)
                c_outer = mlt + math.pi * e_env
            else:
                c_inner = 20.0
                mlt = c_inner + math.pi * e_env
                c_outer = c_inner + 2.0 * math.pi * e_env

            out.c_inner_mm = c_inner
            out.c_outer_mm = c_outer

            ref_len = max(1.0, inputs.arbitrary_outer_len)
            ref_wid = max(1.0, inputs.arbitrary_outer_wid)
            out.outer_len = ref_len + 2.0 * e_env
            out.outer_wid = ref_wid + 2.0 * e_env
            out.mean_dia_mm = mlt / math.pi

            total_len_mm = total_n * mlt * 1.01

            area_face = mlt * e_env
            area_outer_side = c_outer * thickness_f
            area_inner_side = c_inner * thickness_f

            eq_dm = out.mean_dia_mm
            denom = 3.0 * eq_dm + 9.0 * e_env + 10.0 * thickness_f
            if denom > 0:
                l_uh = (0.08 * (eq_dm ** 2) * (total_n ** 2)) / denom
            else:
                l_uh = 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        else:
            # 跑道型线圈 (Racetrack)
            delta_w_cross = 0.0
            if inputs.has_crossover_wire:
                # 换层交叉线/线桥在平直段外扩约 1.0 根实际线径 (覆盖60°交叉线区最大外轮廓)
                delta_w_cross = 1.0 * b_actual
            out.delta_w_crossover = delta_w_cross

            outer_len = inputs.inner_len + 2.0 * e_elec
            outer_wid = inputs.inner_wid + 2.0 * e_env + delta_w_cross
            out.outer_len = outer_len
            out.outer_wid = outer_wid
            out.mean_dia_mm = (outer_len + outer_wid) / 2.0
            out.c_inner_mm = 2.0 * (inputs.inner_len - inputs.inner_wid) + math.pi * inputs.inner_wid
            out.c_outer_mm = 2.0 * (outer_len - outer_wid) + math.pi * outer_wid

            # 跑道积分解析解: MLT = OL + OW + IL + IW + (π - 4) * E_elec
            mlt = outer_len + outer_wid + inputs.inner_len + inputs.inner_wid + (math.pi - 4.0) * e_elec
            total_len_mm = total_n * mlt * 1.01

            # 跑道绕线槽几何
            area_out = (outer_len - outer_wid) * outer_wid + (math.pi / 4.0) * (outer_wid ** 2)
            area_in = (inputs.inner_len - inputs.inner_wid) * inputs.inner_wid + (math.pi / 4.0) * (inputs.inner_wid ** 2)
            area_face = area_out - area_in
            area_outer_side = 2.0 * (outer_len + outer_wid) * thickness_f
            area_inner_side = 2.0 * (inputs.inner_len + inputs.inner_wid) * thickness_f

            # 跑道等效圆中径电感估算
            eq_dm = mlt / math.pi
            denom = 3.0 * eq_dm + 9.0 * e_env + 10.0 * thickness_f
            if denom > 0:
                l_uh = (0.08 * (eq_dm ** 2) * (total_n ** 2)) / denom
            else:
                l_uh = 0.0
            out.inductance_uh = l_uh
            out.inductance_mh = l_uh / 1000.0

        out.mlt = mlt
        out.total_wire_len_m = total_len_mm / 1000.0

        # ---------------------------------------------------------
        # 5. 裸铜截面积与冷态直流电阻 (DC Resistance)
        # ---------------------------------------------------------
        a_cu = (math.pi / 4.0) * (d_actual ** 2)
        out.a_cu = a_cu

        # 20℃ 基准冷态直流电阻 R20
        rho = inputs.copper_resistivity if inputs.copper_resistivity > 0 else 0.016959
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
        # 6. 质量与槽满率工艺指标 (Mass & Space Utilization)
        # ---------------------------------------------------------
        v_cu = total_len_mm * a_cu
        v_wire = total_len_mm * ((math.pi / 4.0) * (b_actual ** 2))
        v_ins = max(0.0, v_wire - v_cu)
        out.v_cu = v_cu
        out.v_wire = v_wire

        # 线圈净重 (克)
        weight_g = (v_cu * DENSITY_CU + v_ins * DENSITY_INS) / 1000.0
        out.weight_g = weight_g

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
        # 8. DFM 线圈物理空间与电气安全卡控判定 (极简纯粹线圈尺寸卡控)
        # ---------------------------------------------------------
        dfm = DFMCheckResult()
        dfm.enabled = inputs.dfm_enabled

        # X 向空间上限卡控 (跑道型外长 OL / 圆形线圈外径 OD <= Max_X)
        dfm.x_val = out.outer_len
        dfm.x_limit = inputs.max_x_len_limit
        dfm.x_passed = (out.outer_len <= inputs.max_x_len_limit)

        # Y 向空间上限卡控 (跑道型/异形线圈外宽 OW <= Max_Y / 圆形与八角形线圈等同外径)
        dfm.y_val = out.outer_wid
        dfm.y_limit = inputs.max_y_wid_limit if inputs.coil_type in (CoilType.RACETRACK, CoilType.ARBITRARY_PERIMETER) else inputs.max_x_len_limit
        dfm.y_passed = (out.outer_wid <= dfm.y_limit)

        # Z 向装配限高卡控 (线圈自身成型高度/厚度 F <= Max_Z，纯粹线圈空间卡控)
        dfm.z_val = thickness_f
        dfm.z_limit = inputs.max_z_h_limit
        z_pass = (thickness_f <= inputs.max_z_h_limit)
        if inputs.mold_clamping_enabled and inputs.mold_clamping_height < out.h_safe_min_limit:
            # 模具限位厚度突破绝缘/铜芯压缩安全下限，判定为 DFM 超差不合格
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
