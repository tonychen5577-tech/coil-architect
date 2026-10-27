# -*- coding: utf-8 -*-
import sys, math
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")

from src.core.wire_catalog import HUAYE_COPPER_CATALOG, HUAYE_CCAW_CATALOG

def audit_huaye_catalog():
    print("=================================================================")
    print(" 华冶漆包线出厂规格库 KM/KG (每公斤米数) 物理核算与溯源验证")
    print("=================================================================")
    
    # 1. 纯铜 69 档出厂表核算
    print("\n[1] 华冶纯铜规格表 (69档) 导体密度 8.90 g/cm³ 核算:")
    cu_max_err = 0.0
    for item in HUAYE_COPPER_CATALOG:
        d = item.diameter
        cat_km_kg = item.km_per_kg
        # 理论公式: 1 / (π/4 * d^2 * 8.90)
        theory_km_kg = 1.0 / ((math.pi / 4.0) * (d ** 2) * 8.90)
        err_pct = abs(cat_km_kg - theory_km_kg) / theory_km_kg * 100.0
        if err_pct > cu_max_err:
            cu_max_err = err_pct
    print(f"  - 校验了全部 {len(HUAYE_COPPER_CATALOG)} 档规格，最大相对偏差: {cu_max_err:.4f}%")
    assert cu_max_err < 0.05, "纯铜出厂表 KM/KG 与裸铜理论完全一致 (偏差 < 0.05%)"
    print("  ✔ 结论: 华冶纯铜出厂规格表中的 KM/KG 100% 精确对齐纯铜裸导体出厂米重标准！")

    # 2. 15% 铜包铝 79 档出厂表核算
    print("\n[2] 华冶 15% 铜包铝规格表 (79档) 导体密度 3.63 g/cm³ 核算:")
    ccaw_max_err = 0.0
    for item in HUAYE_CCAW_CATALOG:
        d = item.diameter
        cat_km_kg = item.km_per_kg
        # 理论公式: 1 / (π/4 * d^2 * 3.63)
        theory_km_kg = 1.0 / ((math.pi / 4.0) * (d ** 2) * 3.63)
        err_pct = abs(cat_km_kg - theory_km_kg) / theory_km_kg * 100.0
        if err_pct > ccaw_max_err:
            ccaw_max_err = err_pct
    print(f"  - 校验了全部 {len(HUAYE_CCAW_CATALOG)} 档规格，最大相对偏差: {ccaw_max_err:.4f}%")
    assert ccaw_max_err < 0.05, "15% 铜包铝出厂表 KM/KG 与裸导体理论完全一致 (偏差 < 0.05%)"
    print("  ✔ 结论: 华冶铜包铝规格表中的 KM/KG 100% 精确对齐 CCAW 裸导体出厂米重标准！")

    # 3. 典型规格对比表 (裸铜 vs 1UEW漆膜 vs 自粘复合层)
    print("\n[3] 典型规格带漆膜与自粘胶层后的成品每公斤米数对比:")
    print(f"{'线径d(mm)':<10} {'外径D(mm)':<10} {'裸铜米数(m/kg)':<16} {'带1UEW(m/kg)':<16} {'带UEW+SB自粘(m/kg)':<18} {'漆膜重量占比':<12}")
    
    test_dias = [0.050, 0.070, 0.080, 0.100, 0.150, 0.200, 0.350]
    for d in test_dias:
        # 纯铜裸线
        w_cu_m = (math.pi / 4.0) * (d ** 2) * 8.90
        m_kg_bare = 1000.0 / w_cu_m
        
        # 1UEW (底漆 UEW 1.27, 外径增量约 0.008)
        d_uew = d + 0.008
        w_uew_m = (math.pi / 4.0) * (d_uew ** 2 - d ** 2) * 1.27
        m_kg_uew = 1000.0 / (w_cu_m + w_uew_m)
        
        # 2UEW+SB 自粘线 (UEW 1.27 增量 0.014 + SB 1.07 增量 0.008)
        d_base = d + 0.014
        d_sb = d + 0.022
        w_base_m = (math.pi / 4.0) * (d_base ** 2 - d ** 2) * 1.27
        w_sb_m = (math.pi / 4.0) * (d_sb ** 2 - d_base ** 2) * 1.07
        w_total_sb_m = w_cu_m + w_base_m + w_sb_m
        m_kg_sb = 1000.0 / w_total_sb_m
        ins_pct = (w_base_m + w_sb_m) / w_total_sb_m * 100.0
        
        print(f"{d:<10.3f} {d_sb:<10.3f} {m_kg_bare:<16.1f} {m_kg_uew:<16.1f} {m_kg_sb:<18.1f} {ins_pct:<12.2f}%")

if __name__ == "__main__":
    audit_huaye_catalog()
