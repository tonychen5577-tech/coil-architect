import sys
import math
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.core.models import CoilInputs, CoilType, WindingMode
from src.core.physics_engine import CoilPhysicsEngine

id1 = 7.10
id2 = 7.05
r1 = 0.30
target_od1 = 7.76
target_od2 = 7.71
target_thk = 0.67
target_r = 19.5

results = []

# Analytical relation:
# e_env = 0.33 mm
# thickness_f = 0.67 mm
# j_turns ranges from 6 to 18
# For each j_turns:
# b_actual ≈ 0.67 / (1.01 * j_turns) if HCP or 0.67 / (1.01 * (j_turns + 0.5)) if EVEN

for turns in range(6, 18):
    for mode in [WindingMode.VARIABLE, WindingMode.EVEN]:
        for layers in [x * 0.5 for x in range(4, 25)]:
            # Test tension factors
            for tension in [0.98, 0.985, 0.99, 0.995, 1.0]:
                # b_actual estimate
                if mode == WindingMode.VARIABLE:
                    b_est = target_thk / (turns * 1.01)
                else:
                    b_est = target_thk / ((turns + 0.5) * 1.01)
                
                od_nom = round(b_est / tension, 4)
                
                # Check wire sizes near od_nom
                for od_try in [od_nom - 0.003, od_nom - 0.002, od_nom - 0.001, od_nom, od_nom + 0.001, od_nom + 0.002, od_nom + 0.003]:
                    od_try = round(od_try, 4)
                    if od_try < 0.020: continue
                    
                    # Typical paint thickness for fine wire: 0.007 to 0.012 mm
                    for paint in [0.007, 0.008, 0.009, 0.010, 0.011, 0.012]:
                        bare_try = round(od_try - paint, 4)
                        if bare_try < 0.015: continue
                        
                        inp = CoilInputs(
                            coil_type=CoilType.OCTAGONAL,
                            oct_id1=id1,
                            oct_id2=id2,
                            oct_r1=r1,
                            radial_layers=layers,
                            axial_turns=turns,
                            bare_dia=bare_try,
                            max_od=od_try,
                            tension_factor=tension,
                            winding_mode=mode,
                            copper_resistivity=0.016959
                        )
                        out = CoilPhysicsEngine.calculate(inp)
                        
                        err_od1 = abs(out.oct_od1 - target_od1)
                        err_od2 = abs(out.oct_od2 - target_od2)
                        err_thk = abs(out.thickness_h - target_thk)
                        err_r = abs(out.r20 - target_r)
                        
                        if err_od1 <= 0.02 and err_od2 <= 0.02 and err_thk <= 0.02 and err_r <= 3.0:
                            results.append({
                                'bare': bare_try, 'od': od_try, 'tension': tension,
                                'layers': layers, 'turns': turns, 'mode': 'HCP' if mode == WindingMode.VARIABLE else 'EVEN',
                                'od1': out.oct_od1, 'od2': out.oct_od2, 'thk': out.thickness_h,
                                'r20': out.r20, 'turns_total': out.total_turns,
                                'err_od1': err_od1, 'err_od2': err_od2, 'err_thk': err_thk, 'err_r': err_r,
                                'score': err_od1 * 50 + err_od2 * 50 + err_thk * 50 + err_r
                            })

results.sort(key=lambda x: x['score'])
print(f"Total matching solutions found: {len(results)}")
print(f"{'No.':<4}{'Bare(mm)':<10}{'OD(mm)':<10}{'Layers':<8}{'Turns':<8}{'Mode':<6}{'N':<6}{'OD1':<8}{'OD2':<8}{'Thk':<8}{'R20(Ω)':<10}{'Tension':<8}")
print("-" * 92)

seen = set()
count = 0
for r in results:
    # Deduplicate by key parameters
    key = (r['bare'], r['od'], r['layers'], r['turns'], r['mode'])
    if key in seen:
        continue
    seen.add(key)
    count += 1
    print(f"{count:<4}{r['bare']:<10.3f}{r['od']:<10.3f}{r['layers']:<8.1f}{r['turns']:<8}{r['mode']:<6}{r['turns_total']:<6}{r['od1']:<8.3f}{r['od2']:<8.3f}{r['thk']:<8.3f}{r['r20']:<10.2f}{r['tension']:<8.3f}")
    if count >= 25:
        break
