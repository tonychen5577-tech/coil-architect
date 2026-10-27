# -*- coding: utf-8 -*-

def clean_legacy():
    # 1. Clean physics_engine.py
    with open("src/core/physics_engine.py", "r", encoding="utf-8") as f:
        pe_code = f.read()

    # Remove DENSITY_INS = 1.25
    pe_target_1 = '''DENSITY_CU = 8.90             # 纯铜基准密度 (g/cm³) -> 0.00890 g/mm³
DENSITY_INS = 1.25            # 基准绝缘固化密度 (g/cm³)'''

    pe_replace_1 = '''DENSITY_CU = 8.90             # 华冶纯铜出厂基准密度 (g/cm³) -> 0.00890 g/mm³'''

    if pe_target_1 in pe_code:
        pe_code = pe_code.replace(pe_target_1, pe_replace_1, 1)
        print("Removed legacy DENSITY_INS = 1.25")
    else:
        print("pe_target_1 not found!")

    # Clean legacy condition in weight calculation
    pe_target_2 = '''        # 华冶实测烘焙固化漆膜密度自动精确匹配 (UEW 1.27, PEW 1.38, EIW 1.39, AIW 1.42, PIW 1.43, SB 1.07)
        if inputs.insulation_density > 0 and abs(inputs.insulation_density - 1.25) > 1e-3:
            rho_ins = inputs.insulation_density
        else:'''

    pe_replace_2 = '''        # 华冶实测烘焙固化漆膜密度自动精确匹配 (UEW 1.27, PEW 1.38, EIW 1.39, AIW 1.42, PIW 1.43, SB 1.07)
        if inputs.insulation_density > 0:
            rho_ins = inputs.insulation_density
        else:'''

    if pe_target_2 in pe_code:
        pe_code = pe_code.replace(pe_target_2, pe_replace_2, 1)
        print("Cleaned legacy 1.25 comparison branch")
    else:
        print("pe_target_2 not found!")

    with open("src/core/physics_engine.py", "w", encoding="utf-8") as f:
        f.write(pe_code)
    print("Saved physics_engine.py")

    # 2. Clean models.py
    with open("src/core/models.py", "r", encoding="utf-8") as f:
        models_code = f.read()

    m_target = "insulation_density: float = 1.25 # 实际采用的漆膜固化密度 (g/cm³)"
    m_replace = "insulation_density: float = 1.27 # 实际采用的漆膜固化密度 (g/cm³, 华冶实测基准)"

    if m_target in models_code:
        models_code = models_code.replace(m_target, m_replace, 1)
        print("Updated models.py insulation_density default")
    else:
        print("m_target not found!")

    with open("src/core/models.py", "w", encoding="utf-8") as f:
        f.write(models_code)
    print("Saved models.py")

if __name__ == "__main__":
    clean_legacy()
