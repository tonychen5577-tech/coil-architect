# -*- coding: utf-8 -*-
"""
生成华冶漆包线全套算法与工程计算表 Excel 工作簿
包含华冶小工具（麻瓜漆包）反编译得到的 6 大核心模块及动态工程公式：
1. 目录与材料基准表 (Overview & Material Standards)
2. 圆线电阻与公差核算 (Round Wire Resistance & Tolerance)
3. 扁线方线等效圆核算 (Flat & Square Wire Equivalent Analysis)
4. 长重换算与线密度速查 (Length-Weight & Linear Density)
5. 漆包线用漆量预估 (Paint Usage & Solid Content Estimation)
6. 拉丝配模与减面率 (Wire Drawing Die Progression)
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_huaye_excel():
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # ------------------ STYLES DEFINITION ------------------
    FONT_FAMILY = "Microsoft YaHei"
    
    # Fonts
    title_font = Font(name=FONT_FAMILY, size=16, bold=True, color="FFFFFF")
    subtitle_font = Font(name=FONT_FAMILY, size=10, italic=True, color="D9E1F2")
    sec_hdr_font = Font(name=FONT_FAMILY, size=11, bold=True, color="1B365D")
    tbl_hdr_font = Font(name=FONT_FAMILY, size=10, bold=True, color="FFFFFF")
    tbl_subhdr_font = Font(name=FONT_FAMILY, size=10, bold=True, color="1F4E79")
    regular_font = Font(name=FONT_FAMILY, size=10, color="000000")
    bold_font = Font(name=FONT_FAMILY, size=10, bold=True, color="000000")
    input_font = Font(name=FONT_FAMILY, size=10, bold=True, color="9C6500") # Gold/brown
    highlight_font = Font(name=FONT_FAMILY, size=10, bold=True, color="C00000") # Dark Red
    note_font = Font(name=FONT_FAMILY, size=9, italic=True, color="595959")
    
    # Fills
    title_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid") # Dark Navy
    sec_hdr_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid") # Soft Ice Blue
    tbl_hdr_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid") # Deep Steel Blue
    tbl_subhdr_fill = PatternFill(start_color="E9EEF4", end_color="E9EEF4", fill_type="solid")
    input_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid") # Soft Yellow for inputs
    calc_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid") # Soft Gray for readonly formulas
    res_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid") # Soft Green for key results
    accent_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid") # Soft Peach for tolerances
    
    # Borders
    thin_border_side = Side(style='thin', color="D3D3D3")
    dark_border_side = Side(style='thin', color="808080")
    double_bottom_side = Side(style='double', color="1B365D")
    
    std_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    header_border = Border(left=thin_border_side, right=thin_border_side, top=dark_border_side, bottom=dark_border_side)
    result_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=double_bottom_side)
    
    # Alignments
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_wrap_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    def apply_title_banner(ws, title_text, subtitle_text, max_col_letter="H"):
        ws.merge_cells(f"A1:{max_col_letter}1")
        cell1 = ws["A1"]
        cell1.value = f"  {title_text}"
        cell1.font = title_font
        cell1.fill = title_fill
        cell1.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 36

        ws.merge_cells(f"A2:{max_col_letter}2")
        cell2 = ws["A2"]
        cell2.value = f"  {subtitle_text}"
        cell2.font = subtitle_font
        cell2.fill = title_fill
        cell2.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[2].height = 20

    # =========================================================================
    # SHEET 1: 华冶算法导航与材料基准表 (Overview & Materials)
    # =========================================================================
    ws1 = wb.create_sheet(title="01_目录与材料基准")
    ws1.views.sheetView[0].showGridLines = True
    apply_title_banner(ws1, "华冶漆包线全套算法模型与工程仿真表", "Coil-Architect Pro · 华冶供应商算法逆向解析与工程标定手册", "G")

    ws1.merge_cells("A4:G4")
    ws1["A4"] = "一、 模块架构与功能导航"
    ws1["A4"].font = sec_hdr_font
    ws1["A4"].fill = sec_hdr_fill
    ws1["A4"].alignment = align_left
    ws1.row_dimensions[4].height = 24

    nav_headers = ["序号", "工作表名称", "核心算法与公式", "适用场景", "华冶对应模块", "在线圈设计中的建议"]
    ws1.row_dimensions[5].height = 24
    for col_idx, h in enumerate(nav_headers, start=1):
        c = ws1.cell(row=5, column=col_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    nav_data = [
        ("1", "02_圆线规格与电阻公差", "R = ρ / (π/4 · d²)，多层漆膜外径叠加与电阻极值反推", "圆线线圈设计、漆包线标称与最恶劣公差核算", "ResistanceCalc (圆线页)", "【核心推荐】加入线圈最恶劣温升与公差核算"),
        ("2", "03_扁线方线等效圆核算", "A = W·H − (4−π)·r²，等效圆 D = 2√(A/π)，外切/内切/倒角圆", "扁线/方线微型执行器线圈设计、高槽满率电磁阀", "FlatResistanceCalc / Tab3", "【核心推荐】用于方线与长方形扁线截面核算"),
        ("3", "04_长重换算与线密度", "m/kg = 4000 / (π·d²·ρ)，g/m = π·d²·ρ / 4，铜线/复合线重", "线圈称重核验、用铜成本核算、绕线米数估算", "LengthWeightApp (Tab5)", "【标配功能】核对线包下料重量与理论米数"),
        ("4", "05_漆包线用漆量预估", "m_paint = (g/m)·L / (固含·涂着率) · 损耗系数", "线材厂车间漆膜烘焙成本、绝缘漆采购预估", "PaintUsageApp (Tab6)", "【线材厂工艺】线圈设计无需关注，可作备查"),
        ("5", "06_拉丝配模与减面率", "实际减面率 = 理论减面率 · 滑差系数² − 1，模具逐级递减链", "拉丝机模具磨损配模、多道次铜杆减径工艺", "WireDrawingApp (Tab4)", "【线材厂工艺】线圈设计无需关注，线材厂专属"),
    ]

    for r_idx, row in enumerate(nav_data, start=6):
        ws1.row_dimensions[r_idx].height = 22
        for c_idx, val in enumerate(row, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            cell.font = bold_font if c_idx in (1, 2) else regular_font
            cell.border = std_border
            cell.alignment = align_center if c_idx in (1, 2) else align_left
            if "核心推荐" in str(val):
                cell.font = highlight_font
            elif "线材厂工艺" in str(val):
                cell.font = note_font

    # Materials Section
    ws1.merge_cells("A13:G13")
    ws1["A13"] = "二、 华冶线材材料物性与电阻率基准预设表（20℃ 标准环境）"
    ws1["A13"].font = sec_hdr_font
    ws1["A13"].fill = sec_hdr_fill
    ws1["A13"].alignment = align_left
    ws1.row_dimensions[13].height = 24

    mat_headers = ["材料名称", "华冶预设标识", "电阻率 ρ₂₀ (Ω·mm²/m)", "电导率 (% IACS)", "材料密度 ρ (g/cm³)", "电阻温度系数 α₂₀ (1/℃)", "工程说明与供应商背景"]
    ws1.row_dimensions[14].height = 24
    for col_idx, h in enumerate(mat_headers, start=1):
        c = ws1.cell(row=14, column=col_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    mat_data = [
        ("纯铜 (华冶实测经验值)", "1/58.5", 1/58.5, (58.5/58.0)*100, 8.90, 0.00393, "【华冶小工具默认值】实测优质无氧铜经精拔退火后电导率超国标"),
        ("纯铜 (国标 100% IACS)", "1/58", 1/58.0, 100.0, 8.90, 0.00393, "国际标准软铜参考基准 (Annealed Copper Standard)"),
        ("无氧纯铜 (高纯退火态)", "1/59", 1/59.0, (59.0/58.0)*100, 8.90, 0.00393, "高纯度 OFC 无氧铜杆，超低内阻发烧线圈与特种微电机"),
        ("15% 铜包铝 (CCAW 经验值)", "0.02525", 0.02525, (0.017241/0.02525)*100, 3.63, 0.00400, "华冶铜包铝线材实测经验值，重量仅纯铜 41%，常用于音圈减轻自重"),
        ("电工纯铝 (EC-1350)", "1/35.4", 0.02826, 61.01, 2.70, 0.00403, "普通铝线圈基准，轻量化低成本电磁线圈"),
    ]

    for r_idx, row in enumerate(mat_data, start=15):
        ws1.row_dimensions[r_idx].height = 22
        for c_idx, val in enumerate(row, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            cell.font = bold_font if c_idx == 1 else regular_font
            cell.border = std_border
            if c_idx == 1:
                cell.alignment = align_left
            elif c_idx in (2,):
                cell.alignment = align_center
            elif c_idx == 3:
                cell.alignment = align_right
                cell.number_format = "0.0000000"
            elif c_idx == 4:
                cell.alignment = align_right
                cell.number_format = "0.00%"
            elif c_idx == 5:
                cell.alignment = align_right
                cell.number_format = "0.00"
            elif c_idx == 6:
                cell.alignment = align_right
                cell.number_format = "0.00000"
            else:
                cell.alignment = align_left
                if "默认值" in str(val):
                    cell.font = highlight_font

    ws1.merge_cells("A22:G23")
    ws1["A22"] = "说明：在华冶小工具内部，纯铜材料默认关联的电阻率不是 1/58，而是 1/58.5 (≈ 0.017094 Ω·mm²/m)。这是由于华冶线材出厂铜材纯度高，实际电阻普遍比国标标称电阻低约 0.86%。在 Coil-Architect 中可以引入此参数以校准实测电阻偏差。"
    ws1["A22"].font = note_font
    ws1["A22"].alignment = align_wrap_left

    # Column widths for Sheet 1
    col_widths1 = [8, 24, 30, 24, 20, 18, 48]
    for idx, width in enumerate(col_widths1, start=1):
        ws1.column_dimensions[get_column_letter(idx)].width = width

    # =========================================================================
    # SHEET 2: 圆线规格与电阻公差 (Round Wire Resistance & Tolerance)
    # =========================================================================
    ws2 = wb.create_sheet(title="02_圆线电阻与公差核算")
    ws2.views.sheetView[0].showGridLines = True
    apply_title_banner(ws2, "漆包圆线导体电阻与多层漆膜公差核算", "ResistanceCalc 模块还原 · 支持底漆/面漆/自粘胶累计叠加与电阻极值反推", "H")

    # Inputs section
    ws2.merge_cells("A4:D4")
    ws2["A4"] = "一、 导体与绝缘涂层基本参数输入（黄色单元格可编辑）"
    ws2["A4"].font = sec_hdr_font
    ws2["A4"].fill = sec_hdr_fill
    ws2.row_dimensions[4].height = 24

    ws2.merge_cells("F4:H4")
    ws2["F4"] = "二、 测量与温度环境条件"
    ws2["F4"].font = sec_hdr_font
    ws2["F4"].fill = sec_hdr_fill
    ws2.row_dimensions[4].height = 24

    # Environment inputs
    ws2["F5"] = "测试基准长度 L"
    ws2["G5"] = 1000.0
    ws2["G5"].font = input_font
    ws2["G5"].fill = input_fill
    ws2["G5"].alignment = align_right
    ws2["G5"].number_format = "0.0"
    ws2["G5"].border = std_border
    ws2["H5"] = "米 (m)"
    ws2["H5"].font = note_font

    ws2["F6"] = "评估环境温度 T"
    ws2["G6"] = 20.0
    ws2["G6"].font = input_font
    ws2["G6"].fill = input_fill
    ws2["G6"].alignment = align_right
    ws2["G6"].number_format = "0.0"
    ws2["G6"].border = std_border
    ws2["H6"] = "摄氏度 (℃)"
    ws2["H6"].font = note_font

    ws2["F7"] = "材料电阻率 ρ₂₀"
    ws2["G7"] = "='01_目录与材料基准'!C15"  # Link to Huaye 1/58.5
    ws2["G7"].font = bold_font
    ws2["G7"].fill = calc_fill
    ws2["G7"].alignment = align_right
    ws2["G7"].number_format = "0.0000000"
    ws2["G7"].border = std_border
    ws2["H7"] = "Ω·mm²/m (华冶经验值)"
    ws2["H7"].font = note_font

    ws2["F8"] = "温度系数 α₂₀"
    ws2["G8"] = "='01_目录与材料基准'!F15"
    ws2["G8"].font = bold_font
    ws2["G8"].fill = calc_fill
    ws2["G8"].alignment = align_right
    ws2["G8"].number_format = "0.00000"
    ws2["G8"].border = std_border
    ws2["H8"] = "1/℃"
    ws2["H8"].font = note_font

    ws2["F9"] = "导体材料密度"
    ws2["G9"] = "='01_目录与材料基准'!E15"
    ws2["G9"].font = bold_font
    ws2["G9"].fill = calc_fill
    ws2["G9"].alignment = align_right
    ws2["G9"].number_format = "0.00"
    ws2["G9"].border = std_border
    ws2["H9"] = "g/cm³"
    ws2["H9"].font = note_font

    for r in range(5, 10):
        ws2[f"F{r}"].font = bold_font
        ws2[f"F{r}"].border = std_border

    # Conductor & Coating Inputs table
    layer_hdrs = ["层级名称", "厚度/直径中值 (mm)", "下公差 -tol (mm)", "上公差 +tol (mm)"]
    ws2.row_dimensions[5].height = 22
    for c_idx, h in enumerate(layer_hdrs, start=1):
        c = ws2.cell(row=5, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    # Layer defaults (Huaye round wire defaults)
    round_inputs = [
        ("裸铜导体 (Conductor)", 0.0800, 0.0050, 0.0050),
        ("第 1 涂层: 底漆 (Base Coat)", 0.0120, 0.0030, 0.0030),
        ("第 2 涂层: 面漆 (Top Coat)", 0.0040, 0.0020, 0.0020),
        ("第 3 涂层: 自粘胶 (Bonding)", 0.0020, 0.0010, 0.0010),
    ]

    for idx, (lname, mid, neg, pos) in enumerate(round_inputs, start=6):
        ws2.row_dimensions[idx].height = 20
        c1 = ws2.cell(row=idx, column=1, value=lname)
        c1.font = bold_font
        c1.border = std_border

        c2 = ws2.cell(row=idx, column=2, value=mid)
        c2.font = input_font
        c2.fill = input_fill
        c2.alignment = align_right
        c2.number_format = "0.0000"
        c2.border = std_border

        c3 = ws2.cell(row=idx, column=3, value=neg)
        c3.font = input_font
        c3.fill = input_fill
        c3.alignment = align_right
        c3.number_format = "0.0000"
        c3.border = std_border

        c4 = ws2.cell(row=idx, column=4, value=pos)
        c4.font = input_font
        c4.fill = input_fill
        c4.alignment = align_right
        c4.number_format = "0.0000"
        c4.border = std_border

    # Summary of Coating & Finished wire
    ws2.row_dimensions[10].height = 20
    ws2["A10"] = "涂层累计增加量 (漆膜总厚)"
    ws2["A10"].font = bold_font
    ws2["A10"].border = std_border
    ws2["B10"] = "=SUM(B7:B9)"
    ws2["B10"].font = bold_font
    ws2["B10"].fill = calc_fill
    ws2["B10"].alignment = align_right
    ws2["B10"].number_format = "0.0000"
    ws2["B10"].border = std_border
    ws2["C10"] = "=C9" # Outer layer negative tolerance
    ws2["C10"].font = bold_font
    ws2["C10"].fill = calc_fill
    ws2["C10"].alignment = align_right
    ws2["C10"].number_format = "0.0000"
    ws2["C10"].border = std_border
    ws2["D10"] = "=D9" # Outer layer positive tolerance
    ws2["D10"].font = bold_font
    ws2["D10"].fill = calc_fill
    ws2["D10"].alignment = align_right
    ws2["D10"].number_format = "0.0000"
    ws2["D10"].border = std_border

    ws2.row_dimensions[11].height = 22
    ws2["A11"] = "完成外径 (Finished Diameter)"
    ws2["A11"].font = Font(name=FONT_FAMILY, size=10, bold=True, color="1B365D")
    ws2["A11"].fill = res_fill
    ws2["A11"].border = result_border
    ws2["B11"] = "=B6+B10"
    ws2["B11"].font = Font(name=FONT_FAMILY, size=10, bold=True, color="1B365D")
    ws2["B11"].fill = res_fill
    ws2["B11"].alignment = align_right
    ws2["B11"].number_format = "0.0000"
    ws2["B11"].border = result_border
    ws2["C11"] = "=C10"
    ws2["C11"].font = Font(name=FONT_FAMILY, size=10, bold=True, color="1B365D")
    ws2["C11"].fill = res_fill
    ws2["C11"].alignment = align_right
    ws2["C11"].number_format = "0.0000"
    ws2["C11"].border = result_border
    ws2["D11"] = "=D10"
    ws2["D11"].font = Font(name=FONT_FAMILY, size=10, bold=True, color="1B365D")
    ws2["D11"].fill = res_fill
    ws2["D11"].alignment = align_right
    ws2["D11"].number_format = "0.0000"
    ws2["D11"].border = result_border

    # Results Table
    ws2.merge_cells("A13:H13")
    ws2["A13"] = "三、 华冶算法输出：导电截面、每米电阻与全长综合阻值公差域"
    ws2["A13"].font = sec_hdr_font
    ws2["A13"].fill = sec_hdr_fill
    ws2.row_dimensions[13].height = 24

    res_headers = ["评估参数", "公式与逻辑", "最小值 (Min)", "标称中值 (Nom)", "最大值 (Max)", "计量单位", "工程意义说明"]
    ws2.row_dimensions[14].height = 24
    for c_idx, h in enumerate(res_headers, start=1):
        c = ws2.cell(row=14, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    res_rows = [
        ("裸铜线径 (d)", "d_mid - tol ~ d_mid + tol", "=B6-C6", "=B6", "=B6+D6", "mm", "导体内部真实线径，用于计算截面积"),
        ("完成外径 (D_outer)", "d_outer - tol ~ d_outer + tol", "=B11-C11", "=B11", "=B11+D11", "mm", "【华冶算法】外径公差取决于最外层涂层公差"),
        ("导电截面积 (Area)", "A = π/4 · d²", "=PI()/4*C15^2", "=PI()/4*D15^2", "=PI()/4*E15^2", "mm²", "最小线径对应最小截面，最大线径对应最大截面"),
        ("20℃ 每米电阻 (R/m)", "R/m = ρ₂₀ / A (与截面成反比)", "=G$7/E17", "=G$7/D17", "=G$7/C17", "Ω/m", "【反比规律】最小电阻出现在最大线径，最大电阻在最小线径"),
        ("评估温度 T 每米电阻", "R_T = R₂₀ · [1 + α₂₀·(T−20)]", "=C18*(1+G$8*(G$6-20))", "=D18*(1+G$8*(G$6-20))", "=E18*(1+G$8*(G$6-20))", "Ω/m", "考虑线圈工作温升后的每米电阻"),
        (f"全长 L 米电阻 (Total R)", "R_total = R/m · L", "=C19*G$5", "=D19*G$5", "=E19*G$5", "Ω", "测试长度 L 下的总直流电阻范围"),
        ("每米导线重量 (g/m)", "g/m = A · ρ_cu", "=C17*G$9", "=D17*G$9", "=E17*G$9", "g/m", "每米裸铜重量，未计绝缘漆膜重量"),
        ("每公斤米数 (m/kg)", "L/kg = 1000 / (g/m)", "=1000/E21", "=1000/D21", "=1000/C21", "m/kg", "每公斤铜线可绕制米数（与线径平方成反比）"),
    ]

    for r_idx, (pname, fdesc, fmin, fmid, fmax, unit, note) in enumerate(res_rows, start=15):
        ws2.row_dimensions[r_idx].height = 22
        ws2.cell(row=r_idx, column=1, value=pname).font = bold_font
        ws2.cell(row=r_idx, column=2, value=fdesc).font = regular_font
        
        c_min = ws2.cell(row=r_idx, column=3, value=fmin)
        c_mid = ws2.cell(row=r_idx, column=4, value=fmid)
        c_max = ws2.cell(row=r_idx, column=5, value=fmax)

        for cell in (c_min, c_mid, c_max):
            cell.font = bold_font
            cell.fill = res_fill if "Total R" in pname or "R/m" in pname else calc_fill
            cell.alignment = align_right
            if "电阻" in pname or "Total R" in pname:
                cell.number_format = "0.00000" if "每米" in pname else "0.000"
            elif "截面积" in pname:
                cell.number_format = "0.000000"
            elif "线径" in pname or "外径" in pname:
                cell.number_format = "0.0000"
            elif "g/m" in unit:
                cell.number_format = "0.000"
            elif "m/kg" in unit:
                cell.number_format = "0.0"

        ws2.cell(row=r_idx, column=6, value=unit).alignment = align_center
        ws2.cell(row=r_idx, column=7, value=note).font = note_font

        for col in range(1, 8):
            ws2.cell(row=r_idx, column=col).border = std_border

    # Quick Reference Table for Standard Wire Sizes
    ws2.merge_cells("A25:H25")
    ws2["A25"] = "四、 华冶常用圆线线规速查对照表（基于 1/58.5 经验值计算）"
    ws2["A25"].font = sec_hdr_font
    ws2["A25"].fill = sec_hdr_fill
    ws2.row_dimensions[25].height = 24

    std_wire_hdrs = ["公称线径 d (mm)", "截面积 (mm²)", "20℃ 标称电阻 (Ω/m)", "20℃ 最大电阻 (+3%)", "20℃ 最小电阻 (-3%)", "每米重量 (g/m)", "每公斤米数 (m/kg)", "推荐载流 @5A/mm²"]
    ws2.row_dimensions[26].height = 24
    for c_idx, h in enumerate(std_wire_hdrs, start=1):
        c = ws2.cell(row=26, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    sample_diams = [0.030, 0.040, 0.050, 0.060, 0.070, 0.080, 0.090, 0.100, 0.120, 0.150, 0.180, 0.200, 0.250, 0.300, 0.400, 0.500]
    for idx, d_val in enumerate(sample_diams, start=27):
        ws2.row_dimensions[idx].height = 20
        # Col 1: d
        c1 = ws2.cell(row=idx, column=1, value=d_val)
        c1.alignment = align_right
        c1.number_format = "0.000"
        c1.font = bold_font
        c1.border = std_border

        # Col 2: Area = PI()/4 * d^2
        c2 = ws2.cell(row=idx, column=2, value=f"=PI()/4*A{idx}^2")
        c2.alignment = align_right
        c2.number_format = "0.000000"
        c2.border = std_border

        # Col 3: R/m = rho / A
        c3 = ws2.cell(row=idx, column=3, value=f"=G$7/B{idx}")
        c3.alignment = align_right
        c3.number_format = "0.0000" if d_val >= 0.1 else "0.00"
        c3.font = bold_font
        c3.border = std_border

        # Col 4: R_max (+3%)
        c4 = ws2.cell(row=idx, column=4, value=f"=C{idx}*1.03")
        c4.alignment = align_right
        c4.number_format = c3.number_format
        c4.border = std_border

        # Col 5: R_min (-3%)
        c5 = ws2.cell(row=idx, column=5, value=f"=C{idx}*0.97")
        c5.alignment = align_right
        c5.number_format = c3.number_format
        c5.border = std_border

        # Col 6: g/m = A * density
        c6 = ws2.cell(row=idx, column=6, value=f"=B{idx}*G$9")
        c6.alignment = align_right
        c6.number_format = "0.0000" if d_val < 0.1 else "0.000"
        c6.border = std_border

        # Col 7: m/kg = 1000 / g/m
        c7 = ws2.cell(row=idx, column=7, value=f"=1000/F{idx}")
        c7.alignment = align_right
        c7.number_format = "0.0"
        c7.border = std_border

        # Col 8: Current = Area * 5
        c8 = ws2.cell(row=idx, column=8, value=f"=B{idx}*5")
        c8.alignment = align_right
        c8.number_format = "0.000" if d_val < 0.1 else "0.00"
        c8.border = std_border

    # Column widths for Sheet 2
    col_widths2 = [24, 26, 18, 18, 18, 14, 40, 18]
    for idx, width in enumerate(col_widths2, start=1):
        ws2.column_dimensions[get_column_letter(idx)].width = width

    # =========================================================================
    # SHEET 3: 扁线方线等效圆核算 (Flat & Square Wire Equivalent Analysis)
    # =========================================================================
    ws3 = wb.create_sheet(title="03_扁线方线等效圆核算")
    ws3.views.sheetView[0].showGridLines = True
    apply_title_banner(ws3, "扁线与方线倒角等效圆及电磁特性核算", "FlatResistanceCalc / Tab3 算法还原 · 真实圆角面积削减 A=WH−(4−π)r²", "H")

    # Inputs Section
    ws3.merge_cells("A4:D4")
    ws3["A4"] = "一、 扁线/方线几何尺寸与漆膜参数（黄色可编辑）"
    ws3["A4"].font = sec_hdr_font
    ws3["A4"].fill = sec_hdr_fill
    ws3.row_dimensions[4].height = 24

    ws3.merge_cells("F4:H4")
    ws3["F4"] = "二、 电气与材料物性设定"
    ws3["F4"].font = sec_hdr_font
    ws3["F4"].fill = sec_hdr_fill
    ws3.row_dimensions[4].height = 24

    # Right side settings
    ws3["F5"] = "导体材料"
    ws3["G5"] = "纯铜 (华冶实测)"
    ws3["G5"].font = bold_font
    ws3["G5"].alignment = align_center
    ws3["G5"].border = std_border

    ws3["F6"] = "电阻率 ρ₂₀"
    ws3["G6"] = "='01_目录与材料基准'!C15"
    ws3["G6"].font = bold_font
    ws3["G6"].fill = calc_fill
    ws3["G6"].alignment = align_right
    ws3["G6"].number_format = "0.0000000"
    ws3["G6"].border = std_border
    ws3["H6"] = "Ω·mm²/m"
    ws3["H6"].font = note_font

    ws3["F7"] = "材料密度 ρ"
    ws3["G7"] = "='01_目录与材料基准'!E15"
    ws3["G7"].font = bold_font
    ws3["G7"].fill = calc_fill
    ws3["G7"].alignment = align_right
    ws3["G7"].number_format = "0.00"
    ws3["G7"].border = std_border
    ws3["H7"] = "g/cm³"
    ws3["H7"].font = note_font

    ws3["F8"] = "漆膜绝缘密度"
    ws3["G8"] = 1.25
    ws3["G8"].font = input_font
    ws3["G8"].fill = input_fill
    ws3["G8"].alignment = align_right
    ws3["G8"].number_format = "0.00"
    ws3["G8"].border = std_border
    ws3["H8"] = "g/cm³ (聚酯亚胺/PAI)"
    ws3["H8"].font = note_font

    for r in range(5, 9):
        ws3[f"F{r}"].font = bold_font
        ws3[f"F{r}"].border = std_border

    # Flat wire inputs
    flat_hdrs = ["几何参数项", "参数代号", "公称数值 (mm)", "下偏差 (mm)", "上偏差 (mm)", "工程说明"]
    ws3.row_dimensions[5].height = 22
    for c_idx, h in enumerate(flat_hdrs, start=1):
        c = ws3.cell(row=5, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    flat_inputs = [
        ("宽边宽度 (Width)", "W", 0.8000, 0.0050, 0.0050, "矩形长边（若为正方形方线，则 W = H）"),
        ("高边厚度 (Height)", "H", 0.3500, 0.0050, 0.0050, "矩形短边（厚度）"),
        ("倒圆角半径 (Corner Radius)", "r", 0.0800, 0.0000, 0.0000, "【华冶算法】上限为 min(W,H)/2 = 0.175mm"),
        ("漆膜单边增加厚度 (Enamel)", "t_ins", 0.0150, 0.0030, 0.0030, "单边漆膜厚度（完成外径双边各增加 2·t_ins）"),
    ]

    for idx, (pname, code, val, neg, pos, note) in enumerate(flat_inputs, start=6):
        ws3.row_dimensions[idx].height = 20
        ws3.cell(row=idx, column=1, value=pname).font = bold_font
        ws3.cell(row=idx, column=2, value=code).alignment = align_center
        
        c_val = ws3.cell(row=idx, column=3, value=val)
        c_val.font = input_font
        c_val.fill = input_fill
        c_val.alignment = align_right
        c_val.number_format = "0.0000"

        c_neg = ws3.cell(row=idx, column=4, value=neg)
        c_neg.font = input_font
        c_neg.fill = input_fill
        c_neg.alignment = align_right
        c_neg.number_format = "0.0000"

        c_pos = ws3.cell(row=idx, column=5, value=pos)
        c_pos.font = input_font
        c_pos.fill = input_fill
        c_pos.alignment = align_right
        c_pos.number_format = "0.0000"

        ws3.cell(row=idx, column=6, value=note).font = note_font

        for col in range(1, 7):
            ws3.cell(row=idx, column=col).border = std_border

    # Fillet radius validation
    ws3.row_dimensions[10].height = 20
    ws3["A10"] = "圆角有效上限约束 r_max"
    ws3["A10"].font = bold_font
    ws3["A10"].border = std_border
    ws3["B10"] = "min(W,H)/2"
    ws3["B10"].alignment = align_center
    ws3["B10"].border = std_border
    ws3["C10"] = "=MIN(C6, C7)/2"
    ws3["C10"].font = bold_font
    ws3["C10"].fill = calc_fill
    ws3["C10"].alignment = align_right
    ws3["C10"].number_format = "0.0000"
    ws3["C10"].border = std_border
    ws3["D10"] = "=IF(C8<=C10, \"圆角有效合格\", \"圆角超限(需截断)\")"
    ws3["D10"].font = highlight_font
    ws3["D10"].alignment = align_center
    ws3["D10"].border = std_border
    ws3["F10"] = "【华冶算法 clamp_r】当 r 超出半宽时自动限制在 r_max"
    ws3["F10"].font = note_font

    # Calculations Table
    ws3.merge_cells("A12:H12")
    ws3["A12"] = "三、 几何特征圆与电气参数计算输出（华冶核心算法还原）"
    ws3["A12"].font = sec_hdr_font
    ws3["A12"].fill = sec_hdr_fill
    ws3.row_dimensions[12].height = 24

    flat_calc_headers = ["计算项目", "华冶数学计算公式", "计算结果", "计量单位", "同截面圆线指标", "扁线/圆线对比", "工程指导意义"]
    ws3.row_dimensions[13].height = 24
    for c_idx, h in enumerate(flat_calc_headers, start=1):
        c = ws3.cell(row=13, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    calc_rows = [
        ("理论直角截面积", "A_box = W · H", "=C6*C7", "mm²", "=C14", "基准 (直角矩形)", "未考虑圆角削弱的虚高面积"),
        ("真实导电截面积 (Area)", "A = W·H − (4−π)·r²", "=C6*C7-(4-PI())*C8^2", "mm²", "=C15", f"=C15/C14-1", "【华冶核心】由于倒角削去 4 个角，真实面积比矩形小"),
        ("等效圆直径 (D_eq)", "D = 2 · √(A / π)", "=2*SQRT(C15/PI())", "mm", "=C16", "等效基准", "相当于同截面积圆线的线径规格"),
        ("外切圆直径 (尖角外接)", "D_circum = √(W² + H²)", "=SQRT(C6^2+C7^2)", "mm", "=C16", f"=C17/C16-1", "绕线骨架或出线孔必须能容纳的最大对角线包络"),
        ("内切圆直径 (短边相切)", "D_in = min(W, H)", "=MIN(C6, C7)", "mm", "=C16", f"=C18/C16-1", "内切圆为扁线内部能容纳的最大圆棒"),
        ("切圆角外接圆直径", "2√((W/2−r)²+(H/2−r)²) + 2r", "=2*SQRT((C6/2-C8)^2+(C7/2-C8)^2)+2*C8", "mm", "=C16", f"=C19/C16-1", "考虑真实圆角后的外接圆直径（小于无倒角对角线）"),
        ("截面周长 (Perimeter)", "P = 2(W+H) − (8−2π)r", "=2*(C6+C7)-(8-2*PI())*C8", "mm", "=PI()*C16", f"=C20/E20-1", "【散热与高频优势】扁线周长显著大于圆线，散热好、集肤小"),
        ("20℃ 每米直流电阻", "R/m = ρ₂₀ / A", "=G$6/C15", "Ω/m", "=G$6/E15", "完全相同", "扁线真实电阻（基于倒角削减后的截面积）"),
        ("完成外尺寸: 宽边 W_out", "W + 2·t_ins", "=C6+2*C9", "mm", "-", "-", "绝缘涂覆后的总成品宽边"),
        ("完成外尺寸: 高边 H_out", "H + 2·t_ins", "=C7+2*C9", "mm", "-", "-", "绝缘涂覆后的总成品高边（厚度）"),
        ("槽满率增益预估 (Slot Fill)", "扁线贴合紧密度 vs 散绕圆线", "85% ~ 92%", "%", "68% ~ 78%", "+15% ~ +20%", "【电机/电磁铁核心优势】扁线消除了圆线间的三角空隙"),
    ]

    for r_idx, (pname, formula_desc, fval, unit, round_equiv, diff_formula, note) in enumerate(calc_rows, start=14):
        ws3.row_dimensions[r_idx].height = 22
        ws3.cell(row=r_idx, column=1, value=pname).font = bold_font
        ws3.cell(row=r_idx, column=2, value=formula_desc).font = regular_font
        
        # Result cell
        c_res = ws3.cell(row=r_idx, column=3, value=fval)
        c_res.font = bold_font
        c_res.fill = res_fill if "真实导电截面积" in pname or "等效圆直径" in pname or "每米直流电阻" in pname else calc_fill
        c_res.alignment = align_right
        if "截面积" in pname:
            c_res.number_format = "0.000000"
        elif "直径" in pname or "周长" in pname or "完成外尺寸" in pname:
            c_res.number_format = "0.0000"
        elif "电阻" in pname:
            c_res.number_format = "0.00000"
        elif "%" in unit:
            c_res.alignment = align_center

        ws3.cell(row=r_idx, column=4, value=unit).alignment = align_center
        
        # Round Equiv cell
        c_round = ws3.cell(row=r_idx, column=5, value=round_equiv)
        c_round.alignment = align_right
        if "截面积" in pname:
            c_round.number_format = "0.000000"
        elif "直径" in pname or "周长" in pname:
            c_round.number_format = "0.0000"
        elif "电阻" in pname:
            c_round.number_format = "0.00000"
        elif "%" in unit:
            c_round.alignment = align_center

        # Diff cell
        c_diff = ws3.cell(row=r_idx, column=6, value=diff_formula)
        c_diff.alignment = align_right
        if isinstance(diff_formula, str) and diff_formula.startswith("="):
            c_diff.number_format = "+0.00%;-0.00%"
        else:
            c_diff.alignment = align_center

        ws3.cell(row=r_idx, column=7, value=note).font = note_font

        for col in range(1, 8):
            ws3.cell(row=r_idx, column=col).border = std_border

    # Widths for Sheet 3
    col_widths3 = [25, 30, 18, 12, 18, 18, 42, 18]
    for idx, width in enumerate(col_widths3, start=1):
        ws3.column_dimensions[get_column_letter(idx)].width = width

    # =========================================================================
    # SHEET 4: 长重换算与线密度速查 (Length-Weight & Linear Density)
    # =========================================================================
    ws4 = wb.create_sheet(title="04_长重换算与线密度")
    ws4.views.sheetView[0].showGridLines = True
    apply_title_banner(ws4, "漆包线长度重量双向换算与密度速查表", "LengthWeightApp (Tab5) 算法还原 · 铜线/铜包铝/铝线双基准核算", "H")

    # Inputs Section
    ws4.merge_cells("A4:D4")
    ws4["A4"] = "一、 漆包线规格与物性输入（黄色可编辑）"
    ws4["A4"].font = sec_hdr_font
    ws4["A4"].fill = sec_hdr_fill
    ws4.row_dimensions[4].height = 24

    ws4.merge_cells("F4:H4")
    ws4["F4"] = "二、 盘线实测与下料核算（双向换算）"
    ws4["F4"].font = sec_hdr_font
    ws4["F4"].fill = sec_hdr_fill
    ws4.row_dimensions[4].height = 24

    lw_inputs = [
        ("裸铜公称线径 d", 0.0800, "mm", "导体真实导电直径"),
        ("漆包完成外径 D_out", 0.0980, "mm", "含漆膜总外径（Grade 1/2）"),
        ("导体材料密度 ρ_cu", 8.90, "g/cm³", "纯铜=8.90, 铜包铝=3.63, 铝=2.70"),
        ("绝缘漆固化密度 ρ_ins", 1.25, "g/cm³", "聚酯亚胺/PAI 绝缘漆固化层密度"),
    ]

    for idx, (pname, val, unit, note) in enumerate(lw_inputs, start=5):
        ws4.row_dimensions[idx].height = 22
        ws4.cell(row=idx, column=1, value=pname).font = bold_font
        
        c_val = ws4.cell(row=idx, column=2, value=val)
        c_val.font = input_font
        c_val.fill = input_fill
        c_val.alignment = align_right
        c_val.number_format = "0.0000" if "线径" in pname or "外径" in pname else "0.00"

        ws4.cell(row=idx, column=3, value=unit).alignment = align_center
        ws4.cell(row=idx, column=4, value=note).font = note_font

        for col in range(1, 5):
            ws4.cell(row=idx, column=col).border = std_border

    # Right side 2-way conversion
    # Known Length -> Calc Weight
    ws4["F5"] = "已知绕线长度 L"
    ws4["F5"].font = bold_font
    ws4["F5"].border = std_border
    ws4["G5"] = 1500.0
    ws4["G5"].font = input_font
    ws4["G5"].fill = input_fill
    ws4["G5"].alignment = align_right
    ws4["G5"].number_format = "0.0"
    ws4["G5"].border = std_border
    ws4["H5"] = "米 (m)"

    ws4["F6"] = "→ 裸铜总重 (Cu Weight)"
    ws4["F6"].font = bold_font
    ws4["F6"].border = std_border
    ws4["G6"] = "=G5*C12/1000"
    ws4["G6"].font = bold_font
    ws4["G6"].fill = res_fill
    ws4["G6"].alignment = align_right
    ws4["G6"].number_format = "0.000"
    ws4["G6"].border = std_border
    ws4["H6"] = "kg"

    ws4["F7"] = "→ 漆包线成品总重"
    ws4["F7"].font = bold_font
    ws4["F7"].border = std_border
    ws4["G7"] = "=G5*C14/1000"
    ws4["G7"].font = bold_font
    ws4["G7"].fill = res_fill
    ws4["G7"].alignment = align_right
    ws4["G7"].number_format = "0.000"
    ws4["G7"].border = std_border
    ws4["H7"] = "kg (含漆膜)"

    # Known Weight -> Calc Length
    ws4["F8"] = "已知整盘线净重 M"
    ws4["F8"].font = bold_font
    ws4["F8"].border = std_border
    ws4["G8"] = 5.000
    ws4["G8"].font = input_font
    ws4["G8"].fill = input_fill
    ws4["G8"].alignment = align_right
    ws4["G8"].number_format = "0.000"
    ws4["G8"].border = std_border
    ws4["H8"] = "kg"

    ws4["F9"] = "→ 估算可绕线总长"
    ws4["F9"].font = bold_font
    ws4["F9"].border = std_border
    ws4["G9"] = "=G8*1000/C14"
    ws4["G9"].font = highlight_font
    ws4["G9"].fill = res_fill
    ws4["G9"].alignment = align_right
    ws4["G9"].number_format = "0.0"
    ws4["G9"].border = std_border
    ws4["H9"] = "米 (m)"

    # Base Metrics Section
    ws4.merge_cells("A10:H10")
    ws4["A10"] = "三、 截面积、线密度与长重指标输出（华冶核心算法）"
    ws4["A10"].font = sec_hdr_font
    ws4["A10"].fill = sec_hdr_fill
    ws4.row_dimensions[10].height = 24

    lw_metrics_hdrs = ["指标名称", "计算公式 / 逻辑", "计算数值", "单位", "工程物理意义"]
    ws4.row_dimensions[11].height = 24
    for c_idx, h in enumerate(lw_metrics_hdrs, start=1):
        c = ws4.cell(row=11, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    lw_rows = [
        ("裸铜截面积 A_cu", "PI()/4 · d²", "=PI()/4*B5^2", "mm²", "导电铜芯横截面积"),
        ("裸铜线密度 (每米克重)", "g/m = A_cu · ρ_cu", "=C11*B7", "g/m", "每米裸铜质量（不计漆膜）"),
        ("漆膜环形截面积 A_ins", "PI()/4 · (D_out² − d²)", "=PI()/4*(B6^2-B5^2)", "mm²", "绝缘漆层的环形物理横截面积"),
        ("漆膜线密度 (漆重/米)", "g/m = A_ins · ρ_ins", "=C13*B8", "g/m", "每米漆膜质量"),
        ("成品线总线密度 (总米克重)", "铜线密度 + 漆膜线密度", "=C12+C14", "g/m", "【实测基准】实际称重计入漆膜后的每米真实克重"),
        ("裸铜每公斤长度 (L_cu)", "1000 / 裸铜线密度", "=1000/C12", "m/kg", "【华冶算法】理论纯铜 1 公斤可拔丝米数"),
        ("成品每公斤长度 (L_total)", "1000 / 成品总线密度", "=1000/C15", "m/kg", "【采购实际】购买 1 公斤漆包线实际能绕出的米数"),
        ("漆膜重量占比 (Paint Mass %)", "漆膜线密度 / 成品总线密度", "=C14/C15", "%", "漆包线成品中绝缘漆所占的重量比重（细线可达 3%~8%）"),
    ]

    for r_idx, (pname, fdesc, fval, unit, note) in enumerate(lw_rows, start=12):
        ws4.row_dimensions[r_idx].height = 22
        ws4.cell(row=r_idx, column=1, value=pname).font = bold_font
        ws4.cell(row=r_idx, column=2, value=fdesc).font = regular_font
        
        c_val = ws4.cell(row=r_idx, column=3, value=fval)
        c_val.font = bold_font
        c_val.fill = res_fill if "每公斤长度" in pname or "总线密度" in pname else calc_fill
        c_val.alignment = align_right
        if "截面积" in pname:
            c_val.number_format = "0.000000"
        elif "线密度" in pname or "克重" in pname:
            c_val.number_format = "0.000"
        elif "每公斤长度" in pname:
            c_val.number_format = "0.0"
        elif "%" in unit:
            c_val.number_format = "0.00%"

        ws4.cell(row=r_idx, column=4, value=unit).alignment = align_center
        ws4.cell(row=r_idx, column=5, value=note).font = note_font

        for col in range(1, 6):
            ws4.cell(row=r_idx, column=col).border = std_border

    # Widths for Sheet 4
    col_widths4 = [26, 26, 18, 14, 38, 24, 18, 16]
    for idx, width in enumerate(col_widths4, start=1):
        ws4.column_dimensions[get_column_letter(idx)].width = width

    # =========================================================================
    # SHEET 5: 漆包线用漆量预估 (Paint Usage & Solid Content Estimation)
    # =========================================================================
    ws5 = wb.create_sheet(title="05_漆包线用漆量预估")
    ws5.views.sheetView[0].showGridLines = True
    apply_title_banner(ws5, "漆包线涂覆用漆量与固含量损耗核算", "PaintUsageApp (Tab6) 算法还原 · 揭秘线材厂内部 Excel 工艺成本模型", "H")

    # Inputs Section
    ws5.merge_cells("A4:D4")
    ws5["A4"] = "一、 铜线基准与烘焙工艺参数（黄色可编辑）"
    ws5["A4"].font = sec_hdr_font
    ws5["A4"].fill = sec_hdr_fill
    ws5.row_dimensions[4].height = 24

    ws5.merge_cells("F4:H4")
    ws5["F4"] = "二、 华冶内部 Excel 经验公式说明"
    ws5["F4"].font = sec_hdr_font
    ws5["F4"].fill = sec_hdr_fill
    ws5.row_dimensions[4].height = 24

    paint_inputs = [
        ("裸铜线径 d", 0.0580, "mm", "华冶小工具默认裸铜测试线径"),
        ("铜密度 ρ_cu", 8.90, "g/cm³", "纯铜密度标准值"),
        ("圆周率 π 取值", 3.14159, "-", "华冶原 Excel 取 3.14，现支持高精度"),
        ("每公斤裸铜长度 L", "=1000/(B7/4*B6*B5^2)", "m/kg", "【华冶原 Excel 铜系数 6.9865 = 3.14/4·8.9】"),
    ]

    for idx, (pname, val, unit, note) in enumerate(paint_inputs, start=5):
        ws5.row_dimensions[idx].height = 22
        ws5.cell(row=idx, column=1, value=pname).font = bold_font
        
        c_val = ws5.cell(row=idx, column=2, value=val)
        c_val.border = std_border
        if isinstance(val, str) and val.startswith("="):
            c_val.font = bold_font
            c_val.fill = res_fill
            c_val.alignment = align_right
            c_val.number_format = "0.0"
        else:
            c_val.font = input_font
            c_val.fill = input_fill
            c_val.alignment = align_right
            c_val.number_format = "0.0000" if idx == 5 else ("0.00" if idx == 6 else "0.00000")

        ws5.cell(row=idx, column=3, value=unit).alignment = align_center
        ws5.cell(row=idx, column=4, value=note).font = note_font

        for col in range(1, 5):
            ws5.cell(row=idx, column=col).border = std_border

    ws5.merge_cells("F5:H8")
    ws5["F5"] = "华冶原 Excel 用漆量经验公式：\n1. 每米漆膜重 g/m = π·ρ·(外径² − 内径²) / 4\n2. 每公斤铜线长度 L = 1000 / (π/4 · ρ_cu · d²)\n3. 液体漆消耗 = (g/m · L) / (固含量 · 涂着率) · 损耗系数\n注意：溶剂挥发后仅固含量部分留下形成漆膜！"
    ws5["F5"].font = note_font
    ws5["F5"].alignment = align_wrap_left

    # Multi-layer Coating Table
    ws5.merge_cells("A10:H10")
    ws5["A10"] = "三、 逐层涂覆绝缘漆消耗明细表（底漆 / 面漆 / 自粘胶）"
    ws5["A10"].font = sec_hdr_font
    ws5["A10"].fill = sec_hdr_fill
    ws5.row_dimensions[10].height = 24

    coat_hdrs = ["层级与漆种", "外径 (mm)", "膜密度 ρ", "液体漆固含量", "涂着率 (%)", "损耗/有效密度系数", "漆膜净重 (g/kg铜)", "用漆量 (g/kg铜)"]
    ws5.row_dimensions[11].height = 24
    for c_idx, h in enumerate(coat_hdrs, start=1):
        c = ws5.cell(row=11, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    coat_rows = [
        ("第 1 层: 底漆 (聚酯亚胺 PEI)", 0.0660, 1.25, 0.380, 0.960, 1.050),
        ("第 2 层: 面漆 (聚酰胺酰亚胺 PAI)", 0.0720, 1.30, 0.320, 0.950, 1.080),
        ("第 3 层: 自粘层 (改性环氧/缩醛)", 0.0780, 1.15, 0.250, 0.920, 1.100),
    ]

    for idx, (lname, d_out, rho_paint, solid_pct, coat_eff, loss_factor) in enumerate(coat_rows, start=12):
        ws5.row_dimensions[idx].height = 22
        # Col 1: Layer Name
        ws5.cell(row=idx, column=1, value=lname).font = bold_font

        # Col 2: d_out
        c2 = ws5.cell(row=idx, column=2, value=d_out)
        c2.font = input_font
        c2.fill = input_fill
        c2.alignment = align_right
        c2.number_format = "0.0000"

        # Col 3: rho_paint
        c3 = ws5.cell(row=idx, column=3, value=rho_paint)
        c3.font = input_font
        c3.fill = input_fill
        c3.alignment = align_right
        c3.number_format = "0.00"

        # Col 4: solid_pct
        c4 = ws5.cell(row=idx, column=4, value=solid_pct)
        c4.font = input_font
        c4.fill = input_fill
        c4.alignment = align_right
        c4.number_format = "0.0%"

        # Col 5: coat_eff
        c5 = ws5.cell(row=idx, column=5, value=coat_eff)
        c5.font = input_font
        c5.fill = input_fill
        c5.alignment = align_right
        c5.number_format = "0.0%"

        # Col 6: loss_factor
        c6 = ws5.cell(row=idx, column=6, value=loss_factor)
        c6.font = input_font
        c6.fill = input_fill
        c6.alignment = align_right
        c6.number_format = "0.000"

        # Col 7: Net film mass per kg copper (g/kg)
        # Inner diameter: for layer 1 it is B5, for layer 2 it is B12, for layer 3 it is B13
        d_in_ref = "B$5" if idx == 12 else f"B{idx-1}"
        c7 = ws5.cell(row=idx, column=7, value=f"=B$7*C{idx}*(B{idx}^2-{d_in_ref}^2)/4 * B$8")
        c7.font = bold_font
        c7.fill = calc_fill
        c7.alignment = align_right
        c7.number_format = "0.00"

        # Col 8: Liquid paint needed per kg copper (g/kg)
        c8 = ws5.cell(row=idx, column=8, value=f"=G{idx}/(D{idx}*E{idx})*F{idx}")
        c8.font = bold_font
        c8.fill = res_fill
        c8.alignment = align_right
        c8.number_format = "0.00"

        for col in range(1, 9):
            ws5.cell(row=idx, column=col).border = std_border

    # Totals Row
    ws5.row_dimensions[15].height = 24
    ws5["A15"] = "合计汇总 (Total Summary)"
    ws5["A15"].font = Font(name=FONT_FAMILY, size=10, bold=True, color="1B365D")
    ws5["A15"].fill = accent_fill
    ws5["A15"].border = result_border

    ws5["B15"] = "=B14"  # Finished OD
    ws5["B15"].font = bold_font
    ws5["B15"].fill = accent_fill
    ws5["B15"].alignment = align_right
    ws5["B15"].number_format = "0.0000"
    ws5["B15"].border = result_border

    for col in range(3, 7):
        c = ws5.cell(row=15, column=col, value="-")
        c.alignment = align_center
        c.fill = accent_fill
        c.border = result_border

    ws5["G15"] = "=SUM(G12:G14)"
    ws5["G15"].font = Font(name=FONT_FAMILY, size=10, bold=True, color="1B365D")
    ws5["G15"].fill = accent_fill
    ws5["G15"].alignment = align_right
    ws5["G15"].number_format = "0.00"
    ws5["G15"].border = result_border

    ws5["H15"] = "=SUM(H12:H14)"
    ws5["H15"].font = Font(name=FONT_FAMILY, size=11, bold=True, color="C00000")
    ws5["H15"].fill = accent_fill
    ws5["H15"].alignment = align_right
    ws5["H15"].number_format = "0.00"
    ws5["H15"].border = result_border

    # Practical Application Summary
    ws5.merge_cells("A17:H17")
    ws5["A17"] = "四、 批次采购与成本核算（以生产 1 吨漆包线为例）"
    ws5["A17"].font = sec_hdr_font
    ws5["A17"].fill = sec_hdr_fill
    ws5.row_dimensions[17].height = 24

    ws5["A18"] = "生产 1000 kg 裸铜漆包线需采购液体漆总重："
    ws5["A18"].font = bold_font
    ws5["E18"] = "=H15" # in kg
    ws5["E18"].font = highlight_font
    ws5["E18"].fill = res_fill
    ws5["E18"].alignment = align_right
    ws5["E18"].number_format = "0.0"
    ws5["F18"] = "公斤 (kg)"
    ws5["G18"] = "【工艺揭秘】液体漆需购买约 80~120kg，其余 70% 溶剂均挥发排入尾气焚烧炉"
    ws5["G18"].font = note_font

    # Widths for Sheet 5
    col_widths5 = [28, 16, 14, 16, 16, 18, 20, 20]
    for idx, width in enumerate(col_widths5, start=1):
        ws5.column_dimensions[get_column_letter(idx)].width = width

    # =========================================================================
    # SHEET 6: 拉丝配模与减面率 (Wire Drawing Die Progression)
    # =========================================================================
    ws6 = wb.create_sheet(title="06_拉丝配模与减面率")
    ws6.views.sheetView[0].showGridLines = True
    apply_title_banner(ws6, "拉丝机模具减面率与配模链自动计算器", "WireDrawingApp (Tab4 / 麻瓜拉丝王) 算法还原 · 滑差系数与模孔顺推/逆推", "H")

    # Inputs Section
    ws6.merge_cells("A4:D4")
    ws6["A4"] = "一、 拉丝机关键工况与模具参数输入（黄色可编辑）"
    ws6["A4"].font = sec_hdr_font
    ws6["A4"].fill = sec_hdr_fill
    ws6.row_dimensions[4].height = 24

    ws6.merge_cells("F4:H4")
    ws6["F4"] = "二、 华冶配模减面率数学公式说明"
    ws6["F4"].font = sec_hdr_font
    ws6["F4"].fill = sec_hdr_fill
    ws6.row_dimensions[4].height = 24

    die_inputs = [
        ("进线直径 d0 (Inlet)", 0.5000, "mm", "母线进入拉丝机第 1 道模具前的直径"),
        ("出线目标直径 dn (Outlet)", 0.0800, "mm", "拉丝机最终成品定径模出口直径"),
        ("过桥模理论减面率 (Pass Die)", 1.1300, "-", "中间拉细道次面积比 (A_进/A_出)，华冶默认 1.13"),
        ("过桥模滑差系数 (Slip)", 1.0100, "-", "拉丝鼓轮与铜线之间的相对滑动余量，华冶默认 1.01"),
        ("出口定径模理论减面率 (Finish Die)", 1.0870, "-", "定径模变形量稍小以保证表面光洁度，华冶默认 1.087"),
        ("出口模滑差系数 (Finish Slip)", 1.0100, "-", "出口模滑差系数"),
    ]

    for idx, (pname, val, unit, note) in enumerate(die_inputs, start=5):
        ws6.row_dimensions[idx].height = 22
        ws6.cell(row=idx, column=1, value=pname).font = bold_font
        
        c_val = ws6.cell(row=idx, column=2, value=val)
        c_val.font = input_font
        c_val.fill = input_fill
        c_val.alignment = align_right
        c_val.number_format = "0.0000" if idx in (5, 6) else "0.000"

        ws6.cell(row=idx, column=3, value=unit).alignment = align_center
        ws6.cell(row=idx, column=4, value=note).font = note_font

        for col in range(1, 5):
            ws6.cell(row=idx, column=col).border = std_border

    ws6.merge_cells("F5:H10")
    ws6["F5"] = "华冶拉丝机配模核心公式：\n1. 实际减面率 = 理论减面率 × 滑差系数² − 1\n   (过桥模实际减面率 = 1.13 × 1.01² − 1 = 15.27%)\n2. 缩径比例因子 factor = 1 / (√理论减面率 × 滑差系数)\n   (d_出 = d_进 × factor)\n3. 延伸率 = (d_进² / d_出² − 1) × 100%\n说明：多模拉丝机必须严格保证每道模具孔径单调递减！"
    ws6["F5"].font = note_font
    ws6["F5"].alignment = align_wrap_left

    # Calculated Factors
    ws6.row_dimensions[11].height = 20
    ws6["A11"] = "过桥模比例因子 factor_pass"
    ws6["A11"].font = bold_font
    ws6["A11"].border = std_border
    ws6["B11"] = "=1/(SQRT(B7)*B8)"
    ws6["B11"].font = bold_font
    ws6["B11"].fill = calc_fill
    ws6["B11"].alignment = align_right
    ws6["B11"].number_format = "0.00000"
    ws6["B11"].border = std_border
    ws6["C11"] = "-"
    ws6["C11"].alignment = align_center
    ws6["C11"].border = std_border
    ws6["D11"] = "每过一道过桥模，线径缩减为上一道的此比例"
    ws6["D11"].font = note_font
    ws6["D11"].border = std_border

    ws6.row_dimensions[12].height = 20
    ws6["A12"] = "出口模比例因子 factor_finish"
    ws6["A12"].font = bold_font
    ws6["A12"].border = std_border
    ws6["B12"] = "=1/(SQRT(B9)*B10)"
    ws6["B12"].font = bold_font
    ws6["B12"].fill = calc_fill
    ws6["B12"].alignment = align_right
    ws6["B12"].number_format = "0.00000"
    ws6["B12"].border = std_border
    ws6["C12"] = "-"
    ws6["C12"].alignment = align_center
    ws6["C12"].border = std_border
    ws6["D12"] = "最后一道成品模的缩径比例"
    ws6["D12"].font = note_font
    ws6["D12"].border = std_border

    # Dies Table (Backward/Forward Chain)
    ws6.merge_cells("A14:H14")
    ws6["A14"] = "三、 逐道拉丝模孔径推演表（由进线 0.50mm 顺推拉细至 0.08mm 示范）"
    ws6["A14"].font = sec_hdr_font
    ws6["A14"].fill = sec_hdr_fill
    ws6.row_dimensions[14].height = 24

    die_hdrs = ["模具道次", "模具类型", "入口直径 (mm)", "模孔出口直径 (mm)", "延伸率 (%)", "实际减面率 (%)", "线速度相对比", "工程状态说明"]
    ws6.row_dimensions[15].height = 24
    for c_idx, h in enumerate(die_hdrs, start=1):
        c = ws6.cell(row=15, column=c_idx, value=h)
        c.font = tbl_hdr_font
        c.fill = tbl_hdr_fill
        c.alignment = align_center
        c.border = header_border

    # We will generate 18 die rows
    for die_no in range(1, 19):
        r_idx = 15 + die_no
        ws6.row_dimensions[r_idx].height = 20
        # Col 1: Die No
        ws6.cell(row=r_idx, column=1, value=f"第 {die_no:02d} 道模具").font = bold_font
        
        # Col 2: Type
        mtype = "出口定径模" if die_no == 18 else "过桥拉细模"
        c_type = ws6.cell(row=r_idx, column=2, value=mtype)
        c_type.alignment = align_center
        if die_no == 18:
            c_type.font = highlight_font

        # Col 3: d_in
        if die_no == 1:
            f_in = "=B$5"
        else:
            f_in = f"=D{r_idx-1}"
        c_in = ws6.cell(row=r_idx, column=3, value=f_in)
        c_in.alignment = align_right
        c_in.number_format = "0.0000"

        # Col 4: d_out
        factor_ref = "B$12" if die_no == 18 else "B$11"
        c_out = ws6.cell(row=r_idx, column=4, value=f"=C{r_idx}*{factor_ref}")
        c_out.font = bold_font
        c_out.fill = res_fill if die_no == 18 else calc_fill
        c_out.alignment = align_right
        c_out.number_format = "0.0000"

        # Col 5: Elongation % = (d_in^2 / d_out^2 - 1)
        c_elong = ws6.cell(row=r_idx, column=5, value=f"=(C{r_idx}^2/D{r_idx}^2-1)")
        c_elong.alignment = align_right
        c_elong.number_format = "0.00%"

        # Col 6: Area Reduction % = (1 - d_out^2 / d_in^2)
        c_red = ws6.cell(row=r_idx, column=6, value=f"=(1-D{r_idx}^2/C{r_idx}^2)")
        c_red.alignment = align_right
        c_red.number_format = "0.00%"

        # Col 7: Velocity Ratio = d0^2 / d_out^2
        c_vel = ws6.cell(row=r_idx, column=7, value=f"=B$5^2/D{r_idx}^2")
        c_vel.alignment = align_right
        c_vel.number_format = "0.00"

        # Col 8: Note
        note_str = "最终定径出口，必须严控磨损" if die_no == 18 else "中道拉细，乳化液循环冷却"
        ws6.cell(row=r_idx, column=8, value=note_str).font = note_font

        for col in range(1, 9):
            ws6.cell(row=r_idx, column=col).border = std_border

    # Widths for Sheet 6
    col_widths6 = [18, 16, 18, 20, 16, 18, 16, 36]
    for idx, width in enumerate(col_widths6, start=1):
        ws6.column_dimensions[get_column_letter(idx)].width = width

    # Save to both target directories
    save_path_archive = r"C:\Workspace\04_Historical_Archive\02_AWA资料\技术资料\材料特性\线材\华冶线材\华冶漆包线全套算法与工程计算表.xlsx"
    save_path_workspace = os.path.abspath("华冶漆包线全套算法与工程计算表.xlsx")

    wb.save(save_path_archive)
    print(f"Saved successfully to archive: {save_path_archive}")

    wb.save(save_path_workspace)
    print(f"Saved successfully to workspace: {save_path_workspace}")

if __name__ == "__main__":
    build_huaye_excel()
