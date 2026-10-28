# -*- coding: utf-8 -*-
"""
Coil-Architect Pro - Data Models
数据模型定义：输入参数、计算结果输出与工程配置
支持跑道型、圆形、八角形及任意中线展开异形线圈；
支持圆线、正方线、长方形扁线全形态截面与华冶出厂标准线规库。
"""

from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import Optional


class CoilType(IntEnum):
    """线圈几何拓扑类型"""
    RACETRACK = 0             # 跑道型线圈 (Racetrack: 两平直边 + 两半圆端部, 如 X-LRA / 手机常规VCM)
    CIRCULAR = 1              # 圆形线圈 (Circular Coin: 经典同心圆环形线圈, 如手机转子/硬币形 Z-LRA 马达)
    OCTAGONAL = 2             # 八角形线圈 (Octagonal VCM: 4平直边 + 4斜边 + 8圆角, 经典手机摄像头对焦/防抖 VCM)
    ARBITRARY_PERIMETER = 3   # 通用中线周长/异形线圈 (Perimeter-based: 任意异形/CAD测得周长直接输入)


class WindingMode(IntEnum):
    """绕线排布模式"""
    EVEN = 0      # 同数绕线 (Mode 0: 6-6-6-6 每层同匝, 奇数层浮动0.5D, 顶部含0.5D偏移)
    VARIABLE = 1  # 异数绕线 (Mode 1: 6-5-6-5 六方密排交错 HCP, 奇数层缩进1匝, 边界端面平齐)
    ODD = 1       # 异数绕线别名 (奇偶交错/阶梯减匝排法)


class WireShape(IntEnum):
    """线材截面拓扑形状"""
    ROUND = 0             # 圆线 (Round wire)
    SQUARE = 1            # 正方形方线 (Square wire, W = H)
    RECTANGULAR = 2       # 长方形扁线 (Rectangular flat wire)


class WireCatalogType(IntEnum):
    """线材规格库来源"""
    CUSTOM = 0            # 通用自定义线规
    HUAYE_COPPER = 1      # 华冶线材 · 纯铜标准系列 (69档, 0.07~0.75mm, 1/58.5)
    HUAYE_CCAW = 2        # 华冶线材 · 15% 铜包铝系列 (79档, 0.07~0.85mm, 0.02525)
    INCOMING_MEASURED = 3 # 进料实测 · 来料参数直入 (实测米阻 + 一公斤多少米)


class WireCategory(str, Enum):
    """线材品类结构体系 (自粘线为默认，预留特种线材接口)"""
    SELF_BONDING = "SELF_BONDING"               # 复合自粘漆包线 (脱模空心线圈标配 · 华冶实测 UEW+SB 体系)
    STANDARD_ENAMELED = "STANDARD_ENAMELED"     # 普通单/双涂层漆包线 (骨架绕线 · 1UEW/2UEW/PEW)
    TRIPLE_INSULATED = "TRIPLE_INSULATED"       # 三层绝缘线 (TIW · 高压安全隔离，预留扩展接口)
    LITZ_WIRE = "LITZ_WIRE"                     # 高频多股绞合线 (利兹线/丝包线，预留扩展接口)
    FLAT_WIRE = "FLAT_WIRE"                     # 长方形/正方形扁铜线 (高槽满率大功率)


class EnamelGrade(IntEnum):
    """漆膜绝缘厚度与自粘层等级体系"""
    GRADE_0 = 0           # 0 级 (超薄微细涂层 / Ultra-Thin, 外径增量约 +0.003mm)
    GRADE_1 = 1           # 1 级 (单涂层 1UEW/1PEW, 外径增量约 +0.008mm)
    GRADE_2 = 2           # 2 级 (加厚双涂层 2UEW/2PEW · 工业常规, 外径增量约 +0.014mm)
    GRADE_3 = 3           # 3 级 (超厚特种涂层 3UEW, 外径增量约 +0.022mm)
    SELF_BONDING = 4      # 复合自粘层 (常规标准自粘 +0.010mm 别名)
    SB_010 = 4            # 常规标准自粘 (1UEW-SB / 2UEW-SB, 漆膜+自粘层外径增量 +0.010mm · +0.01 标配)
    SB_008 = 5            # 薄胶复合自粘 (1UEW-SB 薄胶型, 漆膜+自粘层外径增量 +0.008mm)
    SB_014 = 6            # 加厚复合自粘 (2UEW-SB 加厚型, 漆膜+自粘层外径增量 +0.014mm)
    CUSTOM = 7            # 自定义外径 (保持手动输入设定)


class WindingDirection(IntEnum):
    """扁线排线方向"""
    FLATWISE = 0          # 平绕 / 卧绕 (厚度朝向轴向高度，端面平，壁厚较大)
    EDGEWISE = 1          # 立绕 / 侧绕 (宽度朝向轴向高度，端面高，散热极好)


@dataclass
class CoilInputs:
    """线圈仿真输入参数"""
    # 拓扑类型
    coil_type: CoilType = CoilType.RACETRACK
    
    # 几何与模具参数
    # 当 coil_type 为 RACETRACK 时: inner_len 为内长 IL, inner_wid 为内宽 IW
    # 当 coil_type 为 CIRCULAR 时: inner_len/inner_wid 统一定义为内径 ID (mm)
    inner_len: float = 4.86       # IL / ID: 线圈内长 / 内径 (mm)
    inner_wid: float = 1.50       # IW: 线圈内宽 (仅跑道型生效) (mm)
    radial_layers: float = 14.0   # I: 绕线径向层数 (影响壁厚, 支持0.5半层)
    axial_turns: int = 12         # J: 绕线轴向匝数 (影响高度)
    winding_mode: WindingMode = WindingMode.VARIABLE  # 绕线模式 (0: 同数, 1: 异数)

    # 八角形线圈专属几何参数 (实测/图纸工程规范: 手机摄像头对焦/防抖 VCM 专用)
    oct_id1: float = 7.10         # ID1: 对边内径 (两平直边内侧跨距, mm)
    oct_id2: float = 7.05         # ID2: 对角内径 (45°斜边内侧跨距, mm)
    oct_l1: float = 2.62          # L1: 平直段内长 (mm)
    oct_l2: float = 2.74          # L2: 45°斜边段内长 (mm)
    oct_r1: float = 0.30          # 内R R1: 8个拐角内圆角半径 (mm)

    # 通用异形线圈参数 (基于 CAD 展开周长 / 中线周长)
    perimeter_in: float = 20.0    # C_in: CAD 测得的内轮廓展开周长 (mm)
    perimeter_mean: float = 0.0   # C_mean: 中线周长 (为0时自动根据壁厚推导: C_in + π*E)
    arbitrary_outer_len: float = 7.0 # 异形线圈外形参考长 (mm, 用于DFM卡控)
    arbitrary_outer_wid: float = 5.0 # 异形线圈外形参考宽 (mm, 用于DFM卡控)
    
    # 线材截面形态与规格库配置
    wire_shape: WireShape = WireShape.ROUND
    wire_catalog_type: WireCatalogType = WireCatalogType.CUSTOM
    wire_category: WireCategory = WireCategory.SELF_BONDING # 默认设定为自粘线 (脱模空心线圈标配)
    enamel_grade: EnamelGrade = EnamelGrade.SB_010
    has_self_bonding: bool = True # 默认启用复合自粘胶层
    enamel_type: str = "UEW"      # 默认底漆漆种 (华冶实测固化密度: UEW 1.27, PEW 1.38, EIW 1.39, AIW 1.42, PIW 1.43, SB 1.07)
    catalog_km_kg: float = 0.0    # 华冶出厂线密度或实测线密度 (km/kg, 严格对应出厂/实测裸导体标称米重)
    measured_rm: float = 0.0      # 来料实测常温米阻 (Ω/m, >0 时直接用于精确计算 R20 = L_m * measured_rm)
    wire_density: float = 8.90    # 导体密度 (纯铜 8.90, CCAW 3.63, 纯铝 2.70 g/cm³)
    insulation_density: float = 0.0 # 绝缘漆膜固化密度 (g/cm³, <=0 时由华冶固化密度算法自动精确匹配)

    # 圆线工艺特性
    bare_dia: float = 0.075       # d_nom: 裸铜导体标称直径 (mm)
    max_od: float = 0.085         # B_nom: 带漆膜标称外径 (mm)
    tension_factor: float = 0.99  # η_tension: 绕线张力拉伸修正系数 (0.95 ~ 1.00)
    copper_resistivity: float = 0.017094  # ρ: 20℃材料电阻率 (默认华冶实测经验 1/58.5: 0.01709402 Ω·mm²/m)

    # 方线与扁线专属几何参数
    flat_w: float = 0.80          # W: 宽边公称宽度 (mm)
    flat_h: float = 0.35          # H: 高边公称厚度 (mm)
    flat_max_w: float = 0.0       # W_out: 带漆外宽 (mm, <=0 时根据漆膜等级自动解算)
    flat_max_h: float = 0.0       # H_out: 带漆外厚 (mm, <=0 时根据漆膜等级自动解算)
    flat_r: float = 0.08          # r: 倒圆角半径 (mm)
    flat_r_auto: bool = True      # 是否自动按 min(W,H)/2 约束理论推荐圆角
    flat_winding_dir: WindingDirection = WindingDirection.FLATWISE # 扁线排线方向 (平绕/立绕)
    
    # 绝缘耐压与可靠性卡控要求
    withstand_ground_vac: float = 3000.0 # 对地/对轭铁耐压要求 (VAC, 50Hz, 5s, <1mA)
    withstand_turn_v: float = 1400.0     # 匝间耐压要求 (Vpk, 50Hz, 1min, 升压速率100V/s, <1mA)
    pinhole_max_per_30m: int = 5         # 针孔数上限要求 (盐水测试 <= 5个/30m)

    # 模具限位压实与工艺外扩算法 (Mold Clamping Compaction)
    mold_clamping_enabled: bool = False   # 是否启用模具限位压实硬卡控
    mold_clamping_height: float = 0.55    # H_mold: 模具限位型腔厚度 (mm)
    has_crossover_wire: bool = False      # 是否计入换层交叉线/线桥外宽增量
    
    # 热与电气工况
    ambient_temp: float = 20.0    # Ta: 环境温度 (℃)
    drive_current_ma: float = 10.0 # I_test: 测试驱动电流 (mA)
    rated_voltage_v: float = 1.8  # U: 额定工作电压 (Vrms)
    convection_h: float = 25.0    # h: 表面综合对流换热系数 (W/(m²·K))
    
    # DFM 线圈装配空间与电气安全限值 (线圈物理包络边界 Keep-out Box)
    dfm_enabled: bool = False     # 是否启用 DFM 装配公差与安全限值检查 (默认关闭)
    max_x_len_limit: float = 7.20 # X 向结构空间上限 (mm，跑道外长 / 圆线圈外径 / 八角形外宽)
    max_y_wid_limit: float = 3.82 # Y 向结构空间上限 (mm，跑道外宽)
    max_z_h_limit: float = 1.05   # Z 向装配限高上限 (mm，线圈成型厚度 F 上限)
    max_v_term_limit: float = 2.80# 驱动电压上限 (V)
    max_temp_limit: float = 155.0 # 漆包线耐温等级安全限值 (℃, 预设130/155/180/200级)

    # 兼容历史算例字段
    zlra_z_adaptive: bool = False
    zlra_vibe_space_mm: float = 0.50
    zlra_safety_gap_mm: float = 0.08
    zlra_stroke_mm: float = 0.50

    @property
    def zlra_total_gap_mm(self) -> float:
        return self.zlra_vibe_space_mm + self.zlra_safety_gap_mm


@dataclass
class DFMCheckResult:
    """DFM 结构装配公差与设计限值检查结果 (线圈成型尺寸与公差校验)"""
    enabled: bool = False         # DFM 限值总开关状态 (默认关闭)
    x_passed: bool = True
    x_val: float = 0.0
    x_limit: float = 7.20
    
    y_passed: bool = True
    y_val: float = 0.0
    y_limit: float = 3.82
    
    z_passed: bool = True
    z_val: float = 0.0
    z_limit: float = 1.05
    z_adaptive: bool = False      # 兼容字段
    z_vibe_space: float = 0.50    # 兼容字段
    z_safety_gap: float = 0.08    # 兼容字段
    z_stroke: float = 0.50        # 兼容字段
    
    voltage_passed: bool = True
    voltage_val: float = 0.0
    voltage_limit: float = 2.80
    
    temp_passed: bool = True
    temp_val: float = 0.0
    temp_limit: float = 110.0
    
    @property
    def all_passed(self) -> bool:
        if not self.enabled:
            return True
        return (self.x_passed and self.y_passed and self.z_passed and 
                self.voltage_passed and self.temp_passed)


@dataclass
class CoilOutputs:
    """线圈仿真全套输出结果"""
    # 尺寸与排布指标
    total_turns: int = 0          # N: 有效成型总匝数
    b_actual: float = 0.0         # B: 张力拉伸后实际带漆外径 (mm)
    d_actual: float = 0.0         # d: 张力拉伸后实际裸铜外径 (mm)
    e_elec: float = 0.0           # E_elec: 单边电气壁厚 (mm)
    e_env: float = 0.0            # E_env: 单边外包络物理壁厚 (mm)
    outer_len: float = 0.0        # OL / OD: 实际外廓长度 / 外径 (mm)
    outer_wid: float = 0.0        # OW / OD: 实际外廓宽度 / 外径 (mm)
    thickness_h: float = 0.0      # F: Z向占位高度/厚度 (mm)
    free_thickness_h: float = 0.0 # F_free: 自由堆叠未压缩理论厚度 (mm)
    h_solid_limit: float = 0.0    # H_solid: 纯铜实心不可压缩刚性极限 (mm)
    h_safe_min_limit: float = 0.0 # H_safe: 工艺绝缘安全压缩下限极限 (mm)
    is_mold_clamped: bool = False # 是否启用了模具限位压实
    delta_e_compaction: float = 0.0 # ΔE: 轴向压缩导致的径向壁厚展宽量 (mm)
    delta_w_crossover: float = 0.0  # ΔW_cross: 换层交叉线导致的局部外宽增量 (mm)
    mlt: float = 0.0              # MLT: 平均单匝周长 (mm)
    total_wire_len_m: float = 0.0 # L_tot / 1000: 漆包线总长度 (m)
    mean_dia_mm: float = 0.0      # D_m: 平均中径 (mm)
    c_inner_mm: float = 0.0       # C_in: 内轮廓单匝展开周长 (mm)
    c_outer_mm: float = 0.0       # C_out: 外轮廓单匝展开周长 (mm)
    oct_od1: float = 0.0          # OD1: 八角形实际外对边宽 (mm, = ID1 + 2*E)
    oct_od2: float = 0.0          # OD2: 八角形实际外对角宽 (mm, = ID2 + 2*E)

    # 扁线/方线截面特征输出 (华冶算法)
    flat_actual_area: float = 0.0        # A: 真实导电截面积 (mm², 倒角削减后)
    flat_eq_round_dia: float = 0.0       # D_eq: 等效圆直径 (mm)
    flat_circumscribed_dia: float = 0.0  # D_circum: 尖角外接圆直径 (mm)
    flat_inscribed_dia: float = 0.0      # D_in: 内切圆直径 (mm)
    flat_fillet_dia: float = 0.0         # D_fillet: 考虑倒角的外接圆直径 (mm)
    flat_perimeter: float = 0.0          # P: 扁线截面单圈周长 (mm)
    flat_r: float = 0.0                  # r: 实际采用的倒圆角半径 (mm)
    is_sharp_corner_risk: bool = False   # 是否触发尖角缩漆风险预警 (<0.020mm)
    
    # 电气性能指标
    a_cu: float = 0.0             # A_cu: 裸铜截面积 (mm²)
    copper_resistivity: float = 0.017094  # ρ: 计算采用的铜电阻率 (Ω·mm²/m)
    rho_per_meter: float = 0.0    # 实际单线米阻 (Ω/m)
    r20: float = 0.0              # R20: 20℃本征冷态直流电阻 (Ω)
    r_init: float = 0.0           # R_init: 当前环境温度下的初始冷态电阻 (Ω)
    dcr_hot: float = 0.0          # DCR_hot: 热态自洽平衡电阻 (Ω)
    v_term: float = 0.0           # V_term: 稳态所需端电压 (V)
    joule_power_mw: float = 0.0   # P: 焦耳耗散功率 (mW)
    rated_current_ma: float = 0.0 # I_rated: 额定电压下的驱动电流 (mA)
    ampere_turns: float = 0.0     # ΣI / AT: 安匝数 (A·turns)
    inductance_uh: float = 0.0    # L: Wheeler 空心电感 (μH)
    inductance_mh: float = 0.0    # L: Wheeler 空心电感 (mH)
    
    # 质量与槽满率（称重双基准）
    v_cu: float = 0.0             # V_cu: 纯铜体积 (mm³)
    v_wire: float = 0.0           # V_wire: 漆包线总体积 (mm³)
    v_wind_net: float = 0.0       # V_wind_net: 绕线槽净容积 (mm³)
    weight_g: float = 0.0         # Weight: 最终输出线圈有效动质量 (g)
    weight_cu_g: float = 0.0      # 纯铜/导体净重 (g)
    weight_ins_g: float = 0.0     # 绝缘漆膜净重 (g)
    weight_theoretical_g: float = 0.0 # 理论公称总重 (g = Cu + Ins)
    weight_actual_expected_g: float = 0.0 # 车间实测预测重量 (g, 考虑拉细负公差与张力修正)
    wire_fill_factor: float = 0.0 # 绕线区漆包线占空比 (%)
    copper_fill_factor: float = 0.0# 微观纯铜空间填充率 (%)
    insulation_density: float = 1.27 # 实际采用的漆膜固化密度 (g/cm³, 华冶实测基准)
    finished_km_per_kg: float = 0.0 # 成品线实际千米重量比 (km/kg, 含漆膜与自粘层)
    
    # 热学稳态
    delta_t: float = 0.0          # 温升 (℃)
    t_final: float = 0.0          # 稳态极限结温 (℃)
    total_cooling_area_m2: float = 0.0 # 总散热有效表面积 (m²)
    
    # 绝缘耐压与可靠性评估指标
    turn_voltage_peak: float = 0.0       # 工作状态单匝最大瞬态峰值压差 (V)
    turn_breakdown_voltage_v: float = 0.0# 所选漆膜等级理论匝间击穿电压 (V)
    turn_safety_factor: float = 0.0      # 匝间绝缘击穿安全裕度 (BDV / V_turn)
    hi_pot_ground_passed: bool = True    # 对地 3000VAC 绝缘耐压判定
    hi_pot_turn_passed: bool = True      # 匝间 1400V 耐压判定
    insulation_risk_level: str = "NORMAL"# 绝缘风险评级 ("SAFE", "NORMAL", "WARNING", "DANGER")
    insulation_recommendation: str = ""  # 绝缘工艺建议

    # DFM 校验
    dfm: DFMCheckResult = field(default_factory=DFMCheckResult)
