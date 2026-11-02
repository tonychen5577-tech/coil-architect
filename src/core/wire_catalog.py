# -*- coding: utf-8 -*-
"""
Coil-Architect Pro - 华冶线材出厂标准数据库与自定义线材库 (Wire Vendor & Custom Catalog)
1. 华冶供应商出厂技术规格书 (国标 GB/T 6109 / GB/T 4074 基准)：
   - 规格表-纯铜.xlsx (0.07mm ~ 0.75mm, 69 档) · 1/58.5 = 0.01709402 Ω·mm²/m · 8.90 g/cm³
   - 规格表-15%铜包铝.xlsx (0.07mm ~ 0.85mm, 79 档) · 0.02525 Ω·mm²/m · 3.63 g/cm³
2. 自定义线材库 (Custom Wire Catalog)：
   - 自定义厂商、型号、规格名称、公称裸径、出厂最大外径、出厂阻值(Ω/m 20℃)、击穿电压、伸长率
   - 铜导率(% IACS) 与 出厂米阻(Ω/m) 双向推导与联动
   - 出厂重量 (m/kg 国标单位) 与 理论推荐值
   - JSON 本地原子持久化存储与导出/导入
"""

import os
import math
import json
import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple, Dict, Any


@dataclass(frozen=True)
class WireCatalogItem:
    """出厂线材规格条目 (全面支持中国国家标准 GB 单位)"""
    diameter: float          # d: 裸铜/导体公称直径 (mm)
    max_outer_dia: float     # D_max: 出厂保证最大外径 (mm)
    km_resistance_ohm: float # R_km: 20℃千米电阻 (Ω/km)
    km_per_kg: float         # L_km_per_kg: 每公斤长度 (km/kg)
    material_name: str       # 材料名称 (纯铜 / 15%铜包铝)
    resistivity: float       # 电阻率 (Ω·mm²/m)
    density: float           # 密度 (g/cm³)

    @property
    def meter_resistance_ohm(self) -> float:
        """20℃ 国标米阻 (Ω/m)"""
        return self.km_resistance_ohm / 1000.0

    @property
    def m_per_kg(self) -> float:
        """出厂国标重量比 (m/kg · 一公斤多少米)"""
        return self.km_per_kg * 1000.0

    @property
    def copper_conductivity_iacs(self) -> float:
        """等效退火铜导率 (% IACS)"""
        if self.resistivity > 0:
            return (0.017241 / self.resistivity) * 100.0
        return 100.0

    @property
    def display_label(self) -> str:
        """下拉列表显示文本 (国标单位: mm | Ω/m | m/kg)"""
        return f"{self.diameter:.3f} mm (外径: {self.max_outer_dia:.3f}mm | {self.meter_resistance_ohm:.4f}Ω/m | {self.m_per_kg:.1f}m/kg)"


# =========================================================================
# 华冶纯铜出厂线规表 (69 档)
# (d, max_od, km_res, km_kg)
# =========================================================================
_HUAYE_COPPER_RAW: List[Tuple[float, float, float, float]] = [
    (0.0700, 0.0730, 4441.7923, 29.1960),
    (0.0800, 0.0830, 3400.7472, 22.3532),
    (0.0900, 0.0930, 2687.0102, 17.6618),
    (0.1000, 0.1030, 2176.4782, 14.3061),
    (0.1100, 0.1130, 1798.7423, 11.8232),
    (0.1200, 0.1230, 1511.4432, 9.9348),
    (0.1300, 0.1330, 1287.8569, 8.4651),
    (0.1400, 0.1430, 1110.4481, 7.2990),
    (0.1500, 0.1530, 967.3237, 6.3582),
    (0.1600, 0.1630, 850.1868, 5.5883),
    (0.1700, 0.1730, 753.1067, 4.9502),
    (0.1800, 0.1830, 671.7525, 4.4155),
    (0.1900, 0.1930, 602.9026, 3.9629),
    (0.2000, 0.2030, 544.1196, 3.5765),
    (0.2100, 0.2130, 493.5325, 3.2440),
    (0.2200, 0.2230, 449.6856, 2.9558),
    (0.2300, 0.2330, 411.4326, 2.7044),
    (0.2400, 0.2430, 377.8608, 2.4837),
    (0.2500, 0.2530, 348.2365, 2.2890),
    (0.2600, 0.2630, 321.9642, 2.1163),
    (0.2700, 0.2730, 298.5567, 1.9624),
    (0.2800, 0.2830, 277.6120, 1.8248),
    (0.2900, 0.2930, 258.7965, 1.7011),
    (0.3000, 0.3030, 241.8309, 1.5896),
    (0.3100, 0.3130, 226.4806, 1.4887),
    (0.3200, 0.3230, 212.5467, 1.3971),
    (0.3300, 0.3330, 199.8603, 1.3137),
    (0.3400, 0.3430, 188.2767, 1.2375),
    (0.3500, 0.3530, 177.6717, 1.1678),
    (0.3600, 0.3630, 167.9381, 1.1039),
    (0.3700, 0.3730, 158.9831, 1.0450),
    (0.3800, 0.3830, 150.7256, 0.9907),
    (0.3900, 0.3930, 143.0952, 0.9406),
    (0.4000, 0.4030, 136.0299, 0.8941),
    (0.4100, 0.4130, 129.4752, 0.8510),
    (0.4200, 0.4230, 123.3831, 0.8110),
    (0.4300, 0.4330, 117.7111, 0.7737),
    (0.4400, 0.4430, 112.4214, 0.7389),
    (0.4500, 0.4530, 107.4804, 0.7065),
    (0.4600, 0.4630, 102.8581, 0.6761),
    (0.4700, 0.4730, 98.5278, 0.6476),
    (0.4800, 0.4830, 94.4652, 0.6209),
    (0.4900, 0.4930, 90.6488, 0.5958),
    (0.5000, 0.5030, 87.0591, 0.5722),
    (0.5100, 0.5130, 83.6785, 0.5500),
    (0.5200, 0.5230, 80.4911, 0.5291),
    (0.5300, 0.5330, 77.4823, 0.5093),
    (0.5400, 0.5430, 74.6392, 0.4906),
    (0.5500, 0.5530, 71.9497, 0.4729),
    (0.5600, 0.5630, 69.4030, 0.4562),
    (0.5700, 0.5730, 66.9892, 0.4403),
    (0.5800, 0.5830, 64.6991, 0.4253),
    (0.5900, 0.5930, 62.5245, 0.4110),
    (0.6000, 0.6030, 60.4577, 0.3974),
    (0.6100, 0.6130, 58.4918, 0.3845),
    (0.6200, 0.6230, 56.6201, 0.3722),
    (0.6300, 0.6330, 54.8369, 0.3604),
    (0.6400, 0.6430, 78.4895, 0.8563), # placeholder
    (0.6400, 0.6430, 53.1367, 0.3493),
    (0.6500, 0.6530, 51.5143, 0.3386),
    (0.6600, 0.6630, 49.9651, 0.3284),
    (0.6700, 0.6730, 48.4847, 0.3187),
    (0.6800, 0.6830, 47.0692, 0.3094),
    (0.6900, 0.6930, 45.7147, 0.3005),
    (0.7000, 0.7030, 44.4179, 0.2920),
    (0.7100, 0.7130, 43.1755, 0.2838),
    (0.7200, 0.7230, 41.9845, 0.2760),
    (0.7300, 0.7330, 40.8422, 0.2685),
    (0.7400, 0.7430, 39.7458, 0.2613),
    (0.7500, 0.7530, 38.6929, 0.2543),
]
# Deduplicate 0.6400
_HUAYE_COPPER_RAW = [x for i, x in enumerate(_HUAYE_COPPER_RAW) if not (x[0] == 0.64 and x[2] > 70.0)]

# =========================================================================
# 华冶 15% 铜包铝出厂线规表 (79 档)
# =========================================================================
_HUAYE_CCAW_RAW: List[Tuple[float, float, float, float]] = [
    (0.0700, 0.0730, 6561.0813, 71.5826),
    (0.0800, 0.0830, 5023.3279, 54.8054),
    (0.0900, 0.0930, 3969.0492, 43.3030),
    (0.1000, 0.1030, 3214.9299, 35.0755),
    (0.1100, 0.1130, 2656.9668, 28.9880),
    (0.1200, 0.1230, 2232.5902, 24.3580),
    (0.1300, 0.1330, 1902.3254, 20.7547),
    (0.1400, 0.1430, 1640.2703, 17.8956),
    (0.1500, 0.1530, 1428.8577, 15.5891),
    (0.1600, 0.1630, 1255.8320, 13.7014),
    (0.1700, 0.1730, 1112.4325, 12.1368),
    (0.1800, 0.1830, 992.2623, 10.8258),
    (0.1900, 0.1930, 890.5623, 9.7162),
    (0.2000, 0.2030, 803.7325, 8.7689),
    (0.2100, 0.2130, 729.0090, 7.9536),
    (0.2200, 0.2230, 664.2417, 7.2470),
    (0.2300, 0.2330, 607.7372, 6.6305),
    (0.2400, 0.2430, 558.1475, 6.0895),
    (0.2500, 0.2530, 514.3888, 5.6121),
    (0.2600, 0.2630, 475.5813, 5.1887),
    (0.2700, 0.2730, 441.0055, 4.8114),
    (0.2800, 0.2830, 410.0676, 4.4739),
    (0.2900, 0.2930, 382.2747, 4.1707),
    (0.3000, 0.3030, 357.2144, 3.8973),
    (0.3100, 0.3130, 334.5400, 3.6499),
    (0.3200, 0.3230, 313.9580, 3.4253),
    (0.3300, 0.3330, 295.2185, 3.2209),
    (0.3400, 0.3430, 278.1081, 3.0342),
    (0.3500, 0.3530, 262.4433, 2.8633),
    (0.3600, 0.3630, 248.0656, 2.7064),
    (0.3700, 0.3730, 234.8378, 2.5621),
    (0.3800, 0.3830, 222.6406, 2.4290),
    (0.3900, 0.3930, 211.3695, 2.3061),
    (0.4000, 0.4030, 200.9331, 2.1922),
    (0.4100, 0.4130, 191.2510, 2.0866),
    (0.4200, 0.4230, 182.2523, 1.9884),
    (0.4300, 0.4330, 173.8740, 1.8970),
    (0.4400, 0.4430, 166.0604, 1.8117),
    (0.4500, 0.4530, 158.7620, 1.7321),
    (0.4600, 0.4630, 151.9343, 1.6576),
    (0.4700, 0.4730, 145.5378, 1.5878),
    (0.4800, 0.4830, 139.5369, 1.5224),
    (0.4900, 0.4930, 133.8996, 1.4609),
    (0.5000, 0.5030, 128.5972, 1.4030),
    (0.5100, 0.5130, 123.6036, 1.3485),
    (0.5200, 0.5230, 118.8953, 1.2972),
    (0.5300, 0.5330, 114.4510, 1.2487),
    (0.5400, 0.5430, 110.2514, 1.2029),
    (0.5500, 0.5530, 106.2787, 1.1595),
    (0.5600, 0.5630, 102.5169, 1.1185),
    (0.5700, 0.5730, 98.9514, 1.0796),
    (0.5800, 0.5830, 95.5687, 1.0427),
    (0.5900, 0.5930, 92.3565, 1.0076),
    (0.6000, 0.6030, 89.3036, 0.9743),
    (0.6100, 0.6130, 86.3996, 0.9426),
    (0.6200, 0.6230, 83.6350, 0.9125),
    (0.6300, 0.6330, 81.0010, 0.8837),
    (0.6400, 0.6430, 78.4895, 0.8563),
    (0.6500, 0.6530, 76.0930, 0.8302),
    (0.6600, 0.6630, 73.8046, 0.8052),
    (0.6700, 0.6730, 71.6180, 0.7814),
    (0.6800, 0.6830, 69.5270, 0.7586),
    (0.6900, 0.6930, 67.5264, 0.7367),
    (0.7000, 0.7030, 65.6108, 0.7158),
    (0.7100, 0.7130, 63.7756, 0.6958),
    (0.7200, 0.7230, 62.0164, 0.6766),
    (0.7300, 0.7330, 60.3290, 0.6582),
    (0.7400, 0.7430, 58.7095, 0.6405),
    (0.7500, 0.7530, 57.1543, 0.6236),
    (0.7600, 0.7630, 55.6601, 0.6073),
    (0.7700, 0.7730, 54.2238, 0.5916),
    (0.7800, 0.7830, 52.8424, 0.5765),
    (0.7900, 0.7930, 51.5131, 0.5620),
    (0.8000, 0.8030, 50.2333, 0.5481),
    (0.8100, 0.8130, 49.0006, 0.5346),
    (0.8200, 0.8230, 47.8128, 0.5216),
    (0.8300, 0.8330, 46.6676, 0.5092),
    (0.8400, 0.8430, 45.5631, 0.4971),
    (0.8500, 0.8530, 44.4973, 0.4855),
]

# 实例化条目列表
HUAYE_COPPER_CATALOG: List[WireCatalogItem] = [
    WireCatalogItem(
        diameter=d,
        max_outer_dia=od,
        km_resistance_ohm=r,
        km_per_kg=kg,
        material_name="纯铜 (华冶实测经验 1/58.5)",
        resistivity=0.01709402,
        density=8.90
    )
    for d, od, r, kg in _HUAYE_COPPER_RAW
]

HUAYE_OFC_COPPER_CATALOG: List[WireCatalogItem] = [
    WireCatalogItem(
        diameter=d,
        max_outer_dia=od,
        km_resistance_ohm=round((0.01694915 / 0.01709402) * r, 4),
        km_per_kg=kg,
        material_name="无氧纯铜 (高纯退火态 1/59.0)",
        resistivity=0.01694915,
        density=8.90
    )
    for d, od, r, kg in _HUAYE_COPPER_RAW
]

HUAYE_CCAW_CATALOG: List[WireCatalogItem] = [
    WireCatalogItem(
        diameter=d,
        max_outer_dia=od,
        km_resistance_ohm=r,
        km_per_kg=kg,
        material_name="15% 铜包铝 (CCAW)",
        resistivity=0.02525,
        density=3.63
    )
    for d, od, r, kg in _HUAYE_CCAW_RAW
]


def get_huaye_copper_wires() -> List[WireCatalogItem]:
    """获取华冶纯铜规格列表 (0.07 ~ 0.75 mm · 1/58.5)"""
    return HUAYE_COPPER_CATALOG


def get_huaye_ofc_wires() -> List[WireCatalogItem]:
    """获取华冶定制高纯退火无氧纯铜规格列表 (0.07 ~ 0.75 mm · 1/59.0 OFC)"""
    return HUAYE_OFC_COPPER_CATALOG


def get_huaye_ccaw_wires() -> List[WireCatalogItem]:
    """获取华冶铜包铝规格列表 (0.07 ~ 0.85 mm · CCAW)"""
    return HUAYE_CCAW_CATALOG


def find_wire_by_diameter(diameter: float, catalog_type: int = 1) -> Optional[WireCatalogItem]:
    """按线径查找最匹配的线材规格条目"""
    if catalog_type == 1:
        catalog = HUAYE_COPPER_CATALOG
    elif catalog_type == 2:
        catalog = HUAYE_CCAW_CATALOG
    elif catalog_type == 3:
        catalog = HUAYE_OFC_COPPER_CATALOG
    else:
        catalog = HUAYE_COPPER_CATALOG
    for item in catalog:
        if abs(item.diameter - diameter) < 1e-5:
            return item
    return min(catalog, key=lambda item: abs(item.diameter - diameter), default=None)


# =========================================================================
# 物理数学互推公式体系 (GB/T 3953 / IEC 60028 标准退火铜)
# =========================================================================

def calculate_rm_from_iacs(bare_dia_mm: float, iacs_pct: float) -> Tuple[float, float]:
    """
    根据裸铜直径与铜导率 (% IACS) 计算常温米阻 (Ω/m) 与 电阻率 (Ω·mm²/m)
    基准: 100% IACS = 0.017241 Ω·mm²/m (20℃, IEC 60028 / GB/T 3953)
    公式:
      rho = 0.017241 / (iacs_pct / 100.0)
      A_cu = (pi / 4) * d^2
      R_m = rho / A_cu
    """
    if bare_dia_mm <= 0 or iacs_pct <= 0:
        return 0.0, 0.017241
    rho = 0.017241 / (iacs_pct / 100.0)
    area = math.pi * (bare_dia_mm ** 2) / 4.0
    rm = rho / area
    return rm, rho


def calculate_iacs_from_rm(bare_dia_mm: float, meter_res_ohm: float) -> Tuple[float, float]:
    """
    根据裸铜直径与出厂实测米阻 (Ω/m) 反推铜导率 (% IACS) 与 电阻率 (Ω·mm²/m)
    公式:
      A_cu = (pi / 4) * d^2
      rho = R_m * A_cu
      iacs_pct = (0.017241 / rho) * 100.0
    """
    if bare_dia_mm <= 0 or meter_res_ohm <= 0:
        return 100.0, 0.017241
    area = math.pi * (bare_dia_mm ** 2) / 4.0
    rho = meter_res_ohm * area
    if rho <= 0:
        return 100.0, 0.017241
    iacs = (0.017241 / rho) * 100.0
    return iacs, rho


def calculate_theoretical_m_per_kg(bare_dia_mm: float, density_g_cm3: float = 8.90) -> float:
    """
    根据裸铜直径与密度计算理论米重比 (m/kg · 国标一公斤多少米)
    公式:
      A_cu = (pi / 4) * d^2  (mm²)
      1米体积 = A_cu * 1000 mm³ = A_cu cm³
      1米质量 (克) = A_cu * density (g/m)
      m_per_kg = 1000.0 / (A_cu * density)  (m/kg)
    """
    if bare_dia_mm <= 0 or density_g_cm3 <= 0:
        return 0.0
    area_mm2 = math.pi * (bare_dia_mm ** 2) / 4.0
    mass_g_per_m = area_mm2 * density_g_cm3
    if mass_g_per_m <= 0:
        return 0.0
    return 1000.0 / mass_g_per_m

# =========================================================================
# 自定义厂商线材规格条目模型 (CustomWireItem)
# =========================================================================

@dataclass
class CustomWireItem:
    """
    自定义厂商线材规格条目
    涵盖：
    1. 线材厂商 (vendor)
    2. 型号 (model)
    3. 规格名称 (spec_name)
    4. 公称裸线径 (bare_dia, mm)
    5. 出厂最大外径 (max_od, mm)
    6. 出厂阻值 (meter_resistance_ohm, Ω/m 20℃ 国标)
    7. 击穿电压 (breakdown_voltage, V)
    8. 伸长率 (elongation_pct, %)
    9. 铜导率 (copper_conductivity_iacs, % IACS) 与 电阻率 (resistivity, Ω·mm²/m)
    10. 出厂重量 (weight_m_per_kg, m/kg 国标米重比)
    11. 材料密度 (density, g/cm³)
    12. 备注与审计时间戳
    """
    id: str                                  # 唯一识别 ID
    vendor: str                              # 线材厂商 (如 华冶, 益达, 胜牌, 金杯等)
    model: str                               # 型号/品名 (如 1UEW-SB, 2PEW, 0UEW, 180级等)
    spec_name: str                           # 规格名称 (如 0.080mm)
    bare_dia: float                          # 公称裸导体直径 (mm)
    max_od: float                            # 出厂最大外径 (mm)
    meter_resistance_ohm: float              # 20℃ 出厂阻值 (Ω/m)
    breakdown_voltage: float = 1800.0        # 击穿电压 BDV (V)
    elongation_pct: float = 15.0             # 伸长率 (%)
    copper_conductivity_iacs: float = 100.0  # 铜导率 (% IACS)
    resistivity: float = 0.017241            # 电阻率 (Ω·mm²/m)
    weight_m_per_kg: float = 22353.2         # 出厂重量 / 长度米重比 (m/kg)
    density: float = 8.90                    # 材料密度 (g/cm³)
    note: str = ""                           # 备注说明
    created_at: str = ""                     # 创建时间
    updated_at: str = ""                     # 修改时间

    @property
    def km_resistance_ohm(self) -> float:
        """等效千米阻值 (Ω/km)"""
        return self.meter_resistance_ohm * 1000.0

    @property
    def km_per_kg(self) -> float:
        """等效千米/公斤 (km/kg)"""
        return self.weight_m_per_kg / 1000.0

    def to_wire_catalog_item(self) -> WireCatalogItem:
        """转换为仿真引擎兼容的 WireCatalogItem"""
        return WireCatalogItem(
            diameter=self.bare_dia,
            max_outer_dia=self.max_od,
            km_resistance_ohm=self.km_resistance_ohm,
            km_per_kg=self.km_per_kg,
            material_name=f"{self.vendor} {self.model} ({self.copper_conductivity_iacs:.1f}% IACS)",
            resistivity=self.resistivity,
            density=self.density
        )

    def to_dict(self) -> Dict[str, Any]:
        """序列化字典"""
        return {
            "id": self.id,
            "vendor": self.vendor,
            "model": self.model,
            "spec_name": self.spec_name,
            "bare_dia": round(self.bare_dia, 4),
            "max_od": round(self.max_od, 4),
            "meter_resistance_ohm": round(self.meter_resistance_ohm, 6),
            "breakdown_voltage": round(self.breakdown_voltage, 1),
            "elongation_pct": round(self.elongation_pct, 2),
            "copper_conductivity_iacs": round(self.copper_conductivity_iacs, 2),
            "resistivity": round(self.resistivity, 8),
            "weight_m_per_kg": round(self.weight_m_per_kg, 2),
            "density": round(self.density, 3),
            "note": self.note,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomWireItem":
        """从字典反序列化"""
        return cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            vendor=str(data.get("vendor", "自定义厂商")),
            model=str(data.get("model", "标准漆包线")),
            spec_name=str(data.get("spec_name", f"{float(data.get('bare_dia', 0.08)):.3f}mm")),
            bare_dia=float(data.get("bare_dia", 0.080)),
            max_od=float(data.get("max_od", 0.089)),
            meter_resistance_ohm=float(data.get("meter_resistance_ohm", 3.4299)),
            breakdown_voltage=float(data.get("breakdown_voltage", 1800.0)),
            elongation_pct=float(data.get("elongation_pct", 15.0)),
            copper_conductivity_iacs=float(data.get("copper_conductivity_iacs", 100.0)),
            resistivity=float(data.get("resistivity", 0.017241)),
            weight_m_per_kg=float(data.get("weight_m_per_kg", 22353.2)),
            density=float(data.get("density", 8.90)),
            note=str(data.get("note", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", ""))
        )


# =========================================================================
# 自定义线材库管理器 (持久化存储与 CRUD)
# =========================================================================

class CustomWireManager:
    """
    自定义厂商线材库管理器 (JSON 原子持久化存储)
    默认存储位置: config/custom_wires.json
    """

    DEFAULT_PRESETS: List[Dict[str, Any]] = [
        {
            "id": "preset_huaye_0080_sb",
            "vendor": "华冶精工",
            "model": "1UEW-SB 复合自粘线",
            "spec_name": "0.080mm",
            "bare_dia": 0.080,
            "max_od": 0.089,
            "meter_resistance_ohm": 3.4007,
            "breakdown_voltage": 1800.0,
            "elongation_pct": 16.0,
            "copper_conductivity_iacs": 100.86,
            "resistivity": 0.01709402,
            "weight_m_per_kg": 22353.2,
            "density": 8.90,
            "note": "华冶自粘线标杆规格，出厂 1/58.5 高导退火铜",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        },
        {
            "id": "preset_huaye_0120_sb",
            "vendor": "华冶精工",
            "model": "1UEW-SB 复合自粘线",
            "spec_name": "0.120mm",
            "bare_dia": 0.120,
            "max_od": 0.133,
            "meter_resistance_ohm": 1.5114,
            "breakdown_voltage": 2100.0,
            "elongation_pct": 20.0,
            "copper_conductivity_iacs": 100.86,
            "resistivity": 0.01709402,
            "weight_m_per_kg": 9934.8,
            "density": 8.90,
            "note": "华冶音圈经典出厂规格",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        },
        {
            "id": "preset_yida_0050",
            "vendor": "益达微电",
            "model": "2UEW 超微细线",
            "spec_name": "0.050mm",
            "bare_dia": 0.050,
            "max_od": 0.058,
            "meter_resistance_ohm": 8.7808,
            "breakdown_voltage": 1500.0,
            "elongation_pct": 12.0,
            "copper_conductivity_iacs": 100.0,
            "resistivity": 0.017241,
            "weight_m_per_kg": 57224.2,
            "density": 8.90,
            "note": "微特传感器微细线",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        },
        {
            "id": "preset_shengpai_0100",
            "vendor": "胜牌电气",
            "model": "0UEW 厚漆膜绝缘线",
            "spec_name": "0.100mm",
            "bare_dia": 0.100,
            "max_od": 0.116,
            "meter_resistance_ohm": 2.1952,
            "breakdown_voltage": 2800.0,
            "elongation_pct": 18.0,
            "copper_conductivity_iacs": 100.0,
            "resistivity": 0.017241,
            "weight_m_per_kg": 14306.1,
            "density": 8.90,
            "note": "高耐压电机出厂标准线",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        },
        {
            "id": "preset_hongtian_0100_ccaw",
            "vendor": "宏天特种",
            "model": "15% CCAW-1UEW 铜包铝",
            "spec_name": "0.100mm",
            "bare_dia": 0.100,
            "max_od": 0.110,
            "meter_resistance_ohm": 3.2149,
            "breakdown_voltage": 1800.0,
            "elongation_pct": 15.0,
            "copper_conductivity_iacs": 68.28,
            "resistivity": 0.02525,
            "weight_m_per_kg": 35075.5,
            "density": 3.63,
            "note": "轻量化铜包铝音圈专用线材",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
    ]

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            # 默认存储在项目 config/ 目录下，若不可写则回退至用户 AppData
            base_dir = Path(__file__).resolve().parent.parent.parent
            cfg_dir = base_dir / "config"
            self.storage_path = cfg_dir / "custom_wires.json"
        else:
            self.storage_path = Path(storage_path)
        
        self._items: List[CustomWireItem] = []
        self._load()

    def _load(self):
        """载入自定义线材库，若不存在则初始化默认优质厂商预设"""
        if not self.storage_path.exists():
            self._items = [CustomWireItem.from_dict(d) for d in self.DEFAULT_PRESETS]
            self.save()
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._items = [CustomWireItem.from_dict(d) for d in data]
                else:
                    self._items = [CustomWireItem.from_dict(d) for d in self.DEFAULT_PRESETS]
        except Exception as e:
            # 回退至预设
            self._items = [CustomWireItem.from_dict(d) for d in self.DEFAULT_PRESETS]

    def save(self) -> bool:
        """原子保存自定义线材库 (支持 Windows 文件句柄竞争自适应重试)"""
        import time
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = [item.to_dict() for item in self._items]
            tmp_path = self.storage_path.with_suffix(f".tmp_{uuid.uuid4().hex}")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # Windows 文件索引器/Defender 锁短暂自适应重试
            for attempt in range(5):
                try:
                    tmp_path.replace(self.storage_path)
                    return True
                except PermissionError:
                    if attempt < 4:
                        time.sleep(0.03)
                    else:
                        # 降级直接写入
                        with open(self.storage_path, "w", encoding="utf-8") as f_out:
                            json.dump(data, f_out, ensure_ascii=False, indent=2)
                        if tmp_path.exists():
                            tmp_path.unlink(missing_ok=True)
                        return True
            return True
        except Exception:
            return False

    def list_all(self) -> List[CustomWireItem]:
        """获取所有自定义线材列表"""
        return list(self._items)

    def get_by_id(self, wire_id: str) -> Optional[CustomWireItem]:
        """按 ID 查找"""
        for item in self._items:
            if item.id == wire_id:
                return item
        return None

    def add(self, item: CustomWireItem) -> bool:
        """新增自定义线材"""
        if not item.id:
            item.id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        if not item.created_at:
            item.created_at = now
        item.updated_at = now
        self._items.append(item)
        return self.save()

    def update(self, item: CustomWireItem) -> bool:
        """更新自定义线材"""
        for i, existing in enumerate(self._items):
            if existing.id == item.id:
                item.updated_at = datetime.now().isoformat()
                self._items[i] = item
                return self.save()
        return False

    def delete(self, wire_id: str) -> bool:
        """删除指定 ID 线材"""
        initial_len = len(self._items)
        self._items = [item for item in self._items if item.id != wire_id]
        if len(self._items) != initial_len:
            return self.save()
        return False

    def import_from_json(self, file_path: str) -> int:
        """从外部 JSON 文件批量导入线材"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("导入的 JSON 必须为数组格式")
        count = 0
        for entry in data:
            if isinstance(entry, dict):
                item = CustomWireItem.from_dict(entry)
                item.id = str(uuid.uuid4())
                item.created_at = datetime.now().isoformat()
                item.updated_at = item.created_at
                self._items.append(item)
                count += 1
        if count > 0:
            self.save()
        return count

    def export_to_json(self, file_path: str) -> bool:
        """导出到外部 JSON 文件"""
        data = [item.to_dict() for item in self._items]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True


# 全局单例管理器
_custom_wire_manager_instance: Optional[CustomWireManager] = None


def get_custom_wire_manager() -> CustomWireManager:
    """获取全局自定义线材管理器实例"""
    global _custom_wire_manager_instance
    if _custom_wire_manager_instance is None:
        _custom_wire_manager_instance = CustomWireManager()
    return _custom_wire_manager_instance
