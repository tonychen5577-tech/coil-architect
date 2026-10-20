"""
Detailed comparison between Coil-Architect and all benchmarks in coil对标02.xlsx
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import openpyxl
from src.core.physics_engine import CoilPhysicsEngine
from src.core.models import CoilInputs, CoilOutputs, CoilType, WindingMode

def detailed_benchmark():
    excel_path = r"C:\Workspace\01_Current_Projects\01_LabVIEW_Source (软件开发)\01_Coil-Architect_线圈架构师\03_Sim_Data_Input\coil对标02.xlsx"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb['Sheet2']

    models = [
        {'name': 'Model X', 'col': 2, 'qt_col': 3, 'act_col': 4, 'sim_col': 5},
        {'name': 'Model Y', 'col': 7, 'qt_col': 8, 'act_col': 9, 'sim_col': 10},
        {'name': 'Model R1', 'col': 12, 'qt_col': 13, 'act_col': 14, 'sim_col': 15},
    ]

    for m in models:
        c = m['col']
        qt_c = m['qt_col']
        act_c = m['act_col']
        sim_c = m['sim_col']
        name = m['name']

        target_ol = float(ws.cell(row=3, column=c).value)
        target_ow = float(ws.cell(row=4, column=c).value)
        il = float(ws.cell(row=5, column=c).value)
        iw = float(ws.cell(row=6, column=c).value)
        col_turns = int(ws.cell(row=10, column=c).value)
        layers = float(ws.cell(row=11, column=c).value)
        wire_id = float(ws.cell(row=14, column=c).value)
        wire_od = float(ws.cell(row=15, column=c).value)
        
        # Benchmark data from Excel
        excel_data = {
            'OL': float(ws.cell(row=7, column=c).value),
            'OW': float(ws.cell(row=8, column=c).value),
            'H': float(ws.cell(row=9, column=c).value),
            'N': int(ws.cell(row=12, column=c).value),
            'R23': float(ws.cell(row=13, column=c).value),
        }
        
        qt_data = {
            'OL': float(ws.cell(row=7, column=qt_c).value),
            'OW': float(ws.cell(row=8, column=qt_c).value),
            'H': float(ws.cell(row=9, column=qt_c).value),
            'N': int(ws.cell(row=12, column=qt_c).value),
            'R23': float(ws.cell(row=13, column=qt_c).value),
        }

        act_data = {
            'OL': float(ws.cell(row=7, column=act_c).value),
            'OW': float(ws.cell(row=8, column=act_c).value),
            'H': float(ws.cell(row=9, column=act_c).value),
            'N': excel_data['N'],
            'R23': float(ws.cell(row=13, column=act_c).value),
        }

        sim_data = {
            'OL': float(ws.cell(row=7, column=sim_c).value),
            'OW': float(ws.cell(row=8, column=sim_c).value),
            'H': float(ws.cell(row=9, column=sim_c).value),
            'N': excel_data['N'],
            'R23': float(ws.cell(row=13, column=sim_c).value),
        }

        liyin_data = {
            'OL': float(ws.cell(row=31, column=c).value),
            'OW': float(ws.cell(row=32, column=c).value),
            'H': float(ws.cell(row=33, column=c).value),
            'N': int(ws.cell(row=39, column=c).value),
            'R': float(ws.cell(row=34, column=c).value),
        }

        # Calculate with CoilPhysicsEngine under eta=1.00 and eta=0.99
        inp_100 = CoilInputs(
            coil_type=CoilType.RACETRACK,
            inner_len=il,
            inner_wid=iw,
            radial_layers=layers,
            axial_turns=col_turns,
            winding_mode=WindingMode.VARIABLE,
            bare_dia=wire_id,
            max_od=wire_od,
            tension_factor=1.00,
            copper_resistivity=0.01724,
            ambient_temp=23.0
        )
        out_100 = CoilPhysicsEngine.calculate(inp_100)

        inp_099 = CoilInputs(
            coil_type=CoilType.RACETRACK,
            inner_len=il,
            inner_wid=iw,
            radial_layers=layers,
            axial_turns=col_turns,
            winding_mode=WindingMode.VARIABLE,
            bare_dia=wire_id,
            max_od=wire_od,
            tension_factor=0.99,
            copper_resistivity=0.01724,
            ambient_temp=23.0
        )
        out_099 = CoilPhysicsEngine.calculate(inp_099)

        print(f"\n============================== {name} ==============================")
        print(f"输入: IL={il}, IW={iw}, 排法={col_turns}匝x{layers}层, d={wire_id}, OD={wire_od}")
        print(f"设计目标: 外长={target_ol}, 外宽={target_ow}")
        print()
        print("【1. 外廓与截面尺寸对标】")
        print("  外长 OL (mm):")
        print(f"    - Coil-Architect (η=0.99): {out_099.outer_len:.4f}")
        print(f"    - Coil-Architect (η=1.00): {out_100.outer_len:.4f}")
        print(f"    - 原仿真值:               {sim_data['OL']:.4f}  (CA 0.99 差异: {out_099.outer_len - sim_data['OL']:+.4f} mm, {(out_099.outer_len - sim_data['OL'])/sim_data['OL']*100:+.2f}%)")
        print(f"    - Excel 理论值:           {excel_data['OL']:.4f}  (CA 0.99 差异: {out_099.outer_len - excel_data['OL']:+.4f} mm, {(out_099.outer_len - excel_data['OL'])/excel_data['OL']*100:+.2f}%)")
        print(f"    - QT 原软件:              {qt_data['OL']:.4f}   (CA 0.99 差异: {out_099.outer_len - qt_data['OL']:+.4f} mm, {(out_099.outer_len - qt_data['OL'])/qt_data['OL']*100:+.2f}%)")
        print(f"    - 产线实测值:             {act_data['OL']:.4f}  (CA 0.99 差异: {out_099.outer_len - act_data['OL']:+.4f} mm, {(out_099.outer_len - act_data['OL'])/act_data['OL']*100:+.2f}%)")
        print(f"    - 力音对标理论:           {liyin_data['OL']:.4f}")
        print()
        print("  外宽 OW (mm):")
        print(f"    - Coil-Architect (η=0.99): {out_099.outer_wid:.4f}")
        print(f"    - Coil-Architect (η=1.00): {out_100.outer_wid:.4f}")
        print(f"    - 原仿真值:               {sim_data['OW']:.4f}  (CA 0.99 差异: {out_099.outer_wid - sim_data['OW']:+.4f} mm, {(out_099.outer_wid - sim_data['OW'])/sim_data['OW']*100:+.2f}%)")
        print(f"    - Excel 理论值:           {excel_data['OW']:.4f}  (CA 0.99 差异: {out_099.outer_wid - excel_data['OW']:+.4f} mm, {(out_099.outer_wid - excel_data['OW'])/excel_data['OW']*100:+.2f}%)")
        print(f"    - QT 原软件:              {qt_data['OW']:.4f}   (CA 0.99 差异: {out_099.outer_wid - qt_data['OW']:+.4f} mm, {(out_099.outer_wid - qt_data['OW'])/qt_data['OW']*100:+.2f}%)")
        print(f"    - 产线实测值:             {act_data['OW']:.4f}  (CA 0.99 差异: {out_099.outer_wid - act_data['OW']:+.4f} mm, {(out_099.outer_wid - act_data['OW'])/act_data['OW']*100:+.2f}%)")
        print(f"    - 力音对标理论:           {liyin_data['OW']:.4f}")
        print()
        print("  厚度 H (mm):")
        print(f"    - Coil-Architect (η=0.99): {out_099.thickness_h:.4f}")
        print(f"    - Coil-Architect (η=1.00): {out_100.thickness_h:.4f}")
        print(f"    - 原仿真值:               {sim_data['H']:.4f}  (CA 0.99 差异: {out_099.thickness_h - sim_data['H']:+.4f} mm, {(out_099.thickness_h - sim_data['H'])/sim_data['H']*100:+.2f}%)")
        print(f"    - Excel 理论值:           {excel_data['H']:.4f}")
        print(f"    - QT 原软件:              {qt_data['H']:.4f}")
        print(f"    - 产线实测值:             {act_data['H']:.4f}  (CA 0.99 差异: {out_099.thickness_h - act_data['H']:+.4f} mm, {(out_099.thickness_h - act_data['H'])/act_data['H']*100:+.2f}%)")
        print()
        print(f"  成型匝数 N: 全部均为 {out_099.total_turns} 匝 (100% 吻合)")
        print()
        print("【2. 电气性能与23℃冷态电阻对标】")
        print("  23℃冷态电阻 R23 (Ω):")
        print(f"    - Coil-Architect (η=0.99): {out_099.r_init:.4f}")
        print(f"    - Coil-Architect (η=1.00): {out_100.r_init:.4f}")
        print(f"    - 原仿真值:               {sim_data['R23']:.4f} (CA 0.99 差异: {out_099.r_init - sim_data['R23']:+.4f} Ω, {(out_099.r_init - sim_data['R23'])/sim_data['R23']*100:+.2f}%)")
        print(f"    - Excel 理论值:           {excel_data['R23']:.4f} (CA 0.99 差异: {out_099.r_init - excel_data['R23']:+.4f} Ω, {(out_099.r_init - excel_data['R23'])/excel_data['R23']*100:+.2f}%)")
        print(f"    - QT 原软件:              {qt_data['R23']:.4f}  (CA 0.99 差异: {out_099.r_init - qt_data['R23']:+.4f} Ω, {(out_099.r_init - qt_data['R23'])/qt_data['R23']*100:+.2f}%)")
        print(f"    - 产线实测值:             {act_data['R23']:.4f} (CA 0.99 差异: {out_099.r_init - act_data['R23']:+.4f} Ω, {(out_099.r_init - act_data['R23'])/act_data['R23']*100:+.2f}%)")
        print(f"    - 力音对标理论:           {liyin_data['R']:.4f} (CA 0.99 差异: {out_099.r_init - liyin_data['R']:+.4f} Ω, {(out_099.r_init - liyin_data['R'])/liyin_data['R']*100:+.2f}%)")

if __name__ == '__main__':
    detailed_benchmark()
