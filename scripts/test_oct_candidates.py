import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.core.models import CoilInputs, CoilType, WindingMode
from src.core.physics_engine import CoilPhysicsEngine

id1 = 7.10
id2 = 7.05
r1 = 0.30

candidates = [
    # Option 1: 6 layers, 13 turns, HCP mode (75 turns)
    {'desc': '方案1 (常用0.045微细线+13匝HCP)', 'layers': 6.0, 'turns': 13, 'bare': 0.045, 'od': 0.052, 'tension': 0.995, 'mode': WindingMode.VARIABLE, 'mold': False, 'mold_h': 0.67},
    {'desc': '方案1B (常用0.045微细线+13匝HCP+模压0.67)', 'layers': 6.0, 'turns': 13, 'bare': 0.045, 'od': 0.052, 'tension': 0.995, 'mode': WindingMode.VARIABLE, 'mold': True, 'mold_h': 0.67},

    # Option 2: 6 layers, 12 turns, EVEN mode (72 turns)
    {'desc': '方案2 (常用0.045线+12匝同数EVEN)', 'layers': 6.0, 'turns': 12, 'bare': 0.045, 'od': 0.053, 'tension': 0.990, 'mode': WindingMode.EVEN, 'mold': False, 'mold_h': 0.67},

    # Option 3: 5.5 layers, 13 turns, HCP mode (70 turns)
    {'desc': '方案3 (5.5层半层起绕+13匝HCP)', 'layers': 5.5, 'turns': 13, 'bare': 0.044, 'od': 0.052, 'tension': 0.995, 'mode': WindingMode.VARIABLE, 'mold': False, 'mold_h': 0.67},

    # Option 4: 5.5 layers, 12 turns, EVEN mode (66 turns)
    {'desc': '方案4 (5.5层半层起绕+12匝EVEN)', 'layers': 5.5, 'turns': 12, 'bare': 0.043, 'od': 0.053, 'tension': 0.985, 'mode': WindingMode.EVEN, 'mold': False, 'mold_h': 0.67},

    # Option 5: 6 layers, 13 turns, HCP with 0.046/0.053
    {'desc': '方案5 (0.046线+13匝HCP)', 'layers': 6.0, 'turns': 13, 'bare': 0.046, 'od': 0.053, 'tension': 0.980, 'mode': WindingMode.VARIABLE, 'mold': False, 'mold_h': 0.67},
]

for c in candidates:
    inp = CoilInputs(
        coil_type=CoilType.OCTAGONAL,
        oct_id1=id1,
        oct_id2=id2,
        oct_r1=r1,
        radial_layers=c['layers'],
        axial_turns=c['turns'],
        bare_dia=c['bare'],
        max_od=c['od'],
        tension_factor=c['tension'],
        winding_mode=c['mode'],
        mold_clamping_enabled=c['mold'],
        mold_clamping_height=c['mold_h'],
        copper_resistivity=0.016959
    )
    out = CoilPhysicsEngine.calculate(inp)
    mode_str = 'HCP' if c['mode'] == WindingMode.VARIABLE else 'EVEN'
    mold_str = f"模压={c['mold_h']}mm" if c['mold'] else "自然排线"
    print(f"[{c['desc']}]")
    print(f"  参数: 铜裸径={c['bare']:.3f}mm, 带漆外径={c['od']:.3f}mm, 径向层数={c['layers']}, 每层匝数={c['turns']}, 排法={mode_str}, 张力={c['tension']}")
    print(f"  结果: 总匝数={out.total_turns}匝 | OD1={out.oct_od1:.3f}mm, OD2={out.oct_od2:.3f}mm | 厚度={out.thickness_h:.3f}mm | R20={out.r20:.3f}Ω (目标19.5±3Ω)")
    print(f"  L1={out.oct_od1 - 2*out.e_env:.3f}mm, L2={out.oct_od2 - 2*out.e_env:.3f}mm, 展开中径={out.mean_dia_mm:.3f}mm, 估算电感={out.inductance_uh:.2f}μH")
    print("-" * 80)
