"""
Coil-Architect Pro - Professional Excel Report Generator
生成工业级工程评审数据报告 (.xlsx)
包含：线圈参数规格、电气温升指标、排线几何尺寸与 DFM 模具安全性判定
"""

import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from ..core.models import CoilInputs, CoilOutputs, WindingMode, CoilType


class ExcelReportGenerator:
    """Excel 评审报告导出生成器"""

    @staticmethod
    def generate(inputs: CoilInputs, outputs: CoilOutputs, save_path: str, project_name: str = "Coli-Architect") -> str:
        wb = Workbook()
        ws = wb.active
        ws.title = "线圈工程评审报告"

        # 设置网格线可见
        ws.views.sheetView[0].showGridLines = True

        # 配色定义 (对齐 Clean White 工业设计)
        c_header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid") # 天蓝
        c_section_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid") # 淡灰
        c_highlight_fill = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid") # 琥珀淡黄
        c_pass_fill = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid") # 翡翠淡绿
        c_fail_fill = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid") # 预警淡红

        font_title = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
        font_section = Font(name="Segoe UI", size=11, bold=True, color="0F172A")
        font_bold = Font(name="Segoe UI", size=10, bold=True, color="334155")
        font_regular = Font(name="Segoe UI", size=10, color="0F172A")
        font_unit = Font(name="Segoe UI", size=9, color="64748B", italic=True)

        font_pass = Font(name="Segoe UI", size=10, bold=True, color="059669")
        font_fail = Font(name="Segoe UI", size=10, bold=True, color="DC2626")

        thin_side = Side(border_style="thin", color="CBD5E1")
        border_box = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # 1. 报告大标题
        ws.merge_cells("A1:E1")
        cell_title = ws["A1"]
        cell_title.value = "Coil-Architect Pro - 电磁线圈多物理场工程评审报告"
        cell_title.font = font_title
        cell_title.fill = c_header_fill
        cell_title.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 36

        # 2. 项目工程名称与元数据栏
        ws.merge_cells("A2:E2")
        cell_meta = ws["A2"]
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cell_meta.value = f"工程项目名称: {project_name}   |   评审导出时间: {now_str}   |   仿真平台: Coil-Architect Pro (ansv.net)"
        cell_meta.font = Font(name="Segoe UI", size=9.5, bold=True, color="0369A1")
        cell_meta.fill = PatternFill(start_color="F0F9FF", end_color="F0F9FF", fill_type="solid")
        cell_meta.alignment = Alignment(horizontal="center", vertical="center")
        cell_meta.border = border_box
        ws.row_dimensions[2].height = 24

        # 3. 写入辅助函数
        curr_row = 3

        def write_section(title_text: str):
            nonlocal curr_row
            ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=5)
            c = ws.cell(row=curr_row, column=1)
            c.value = f"【 {title_text} 】"
            c.font = font_section
            c.fill = c_section_fill
            c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            ws.row_dimensions[curr_row].height = 24
            curr_row += 1

        def write_row_item(param_name: str, symbol: str, val_str: str, unit: str, remark: str = "", is_hl: bool = False):
            nonlocal curr_row
            row_cells = [
                ws.cell(row=curr_row, column=1, value=param_name),
                ws.cell(row=curr_row, column=2, value=symbol),
                ws.cell(row=curr_row, column=3, value=val_str),
                ws.cell(row=curr_row, column=4, value=unit),
                ws.cell(row=curr_row, column=5, value=remark),
            ]
            for idx, c in enumerate(row_cells):
                c.border = border_box
                c.font = font_bold if idx in [0, 2] else (font_unit if idx == 3 else font_regular)
                c.alignment = Alignment(horizontal="center" if idx in [1, 3] else ("right" if idx == 2 else "left"), vertical="center", wrap_text=False)
                if is_hl:
                    c.fill = c_highlight_fill
            ws.row_dimensions[curr_row].height = 22
            curr_row += 1

        # 表头行
        def write_header():
            nonlocal curr_row
            headers = ["参数/指标名称", "物理符号", "数值", "单位", "工程备注与判定"]
            for col_idx, text in enumerate(headers, start=1):
                c = ws.cell(row=curr_row, column=col_idx, value=text)
                c.font = font_bold
                c.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
                c.border = border_box
            ws.row_dimensions[curr_row].height = 26
            curr_row += 1

        write_header()

        # 一、输入几何与工艺
        write_section("1. 几何尺寸与绕线工艺输入 (Inputs)")
        write_row_item("工程项目名称", "Project", project_name, "--", "当前仿真归属工程项目代号", is_hl=True)
        if inputs.coil_type == CoilType.CIRCULAR:
            coil_type_str = "圆形线圈 (Circular Coil / VLRA / 喇叭)"
        elif inputs.coil_type == CoilType.OCTAGONAL:
            coil_type_str = "八角形线圈 (Octagonal VCM Coil / 手机镜头对焦防抖)"
        elif inputs.coil_type == CoilType.ARBITRARY_PERIMETER:
            coil_type_str = "通用异形线圈 (CAD任意周长推算)"
        else:
            coil_type_str = "跑道型线圈 (Racetrack Coil / 手机VCM)"
        write_row_item("线圈拓扑类型", "Type", coil_type_str, "--", "模型几何拓扑模式")
        if inputs.coil_type == CoilType.CIRCULAR:
            write_row_item("线圈内径", "ID", f"{inputs.inner_len:.2f}", "mm", "模具内芯定位圆柱直径")
        elif inputs.coil_type == CoilType.OCTAGONAL:
            write_row_item("八角形对边内跨距", "ID1", f"{inputs.oct_id1:.2f}", "mm", "水平/竖直对边内跨距")
            write_row_item("八角形对角内跨距", "ID2", f"{inputs.oct_id2:.2f}", "mm", "45°对角内跨距")
            write_row_item("水平/竖直平边长", "L1", f"{inputs.oct_l1:.2f}", "mm", "图4平直边基准长度")
            write_row_item("45°倒角斜边长", "L2", f"{inputs.oct_l2:.2f}", "mm", "图4斜边基准长度")
            write_row_item("倒角内圆角半径", "R1", f"{inputs.oct_r1:.2f}", "mm", "拐角过渡圆角半径")
        elif inputs.coil_type == CoilType.ARBITRARY_PERIMETER:
            write_row_item("内壁轮廓周长", "C_inner", f"{inputs.perimeter_in:.2f}", "mm", "CAD实测内壁展开周长")
            write_row_item("参考外廓长度", "Ref_L", f"{inputs.arbitrary_outer_len:.2f}", "mm", "参考包络长度")
            write_row_item("参考外廓宽度", "Ref_W", f"{inputs.arbitrary_outer_wid:.2f}", "mm", "参考包络宽度")
        else:
            write_row_item("线圈内长", "IL", f"{inputs.inner_len:.2f}", "mm", "绕线模具内芯长度")
            write_row_item("线圈内宽", "IW", f"{inputs.inner_wid:.2f}", "mm", "绕线模具内芯宽度")

        write_row_item("径向绕线层数", "I", str(inputs.radial_layers), "层", "决定单边壁厚")
        write_row_item("轴向绕线匝数", "J", str(inputs.axial_turns), "匝", "决定线圈总厚度高度")
        mode_desc = "异数交错六方密排 (HCP)" if inputs.winding_mode == WindingMode.VARIABLE else "同数规整网格排法"
        write_row_item("绕线排布模式", "Mode", mode_desc, "--", "最外层缩进，端面平齐")
        write_row_item("漆包线导体标称直径", "d_nom", f"{inputs.bare_dia:.3f}", "mm", "纯铜芯标称线径")
        write_row_item("带漆膜标称最大外径", "B_nom", f"{inputs.max_od:.3f}", "mm", "标准自粘漆膜外径")
        write_row_item("铜导体基准电阻率", "ρ_cu", f"{inputs.copper_resistivity:.6f}", "Ω·mm²/m", "OFHC高导电率无氧铜/实测值")
        write_row_item("张力拉伸修正系数", "η_tension", f"{inputs.tension_factor:.3f}", "--", "高速绕线拉伸变细修正")
        write_row_item("环境初始温度", "Ta", f"{inputs.ambient_temp:.1f}", "℃", "标称参考温度")
        write_row_item("驱动测试电流", "I_test", f"{inputs.drive_current_ma:.1f}", "mA", "额定工作电流")
        write_row_item("对流散热系数", "h", f"{inputs.convection_h:.1f}", "W/(m²·K)", "机壳内部微弱对流")

        curr_row += 1
        # 二、输出外廓与匝数
        write_section("2. 线圈成型外廓与排布指标 (Geometry Outputs)")
        write_row_item("成型有效总匝数", "N", str(outputs.total_turns), "匝", "实际导电总匝数", is_hl=True)
        if inputs.coil_type == CoilType.CIRCULAR:
            write_row_item("实际外廓外径", "OD", f"{outputs.outer_len:.3f}", "mm", "圆形外边缘包络直径")
            write_row_item("绕组平均展开中径", "Dm", f"{outputs.mean_dia_mm:.3f}", "mm", "(ID + OD) / 2")
        elif inputs.coil_type == CoilType.OCTAGONAL:
            write_row_item("对边外廓跨距", "OD1", f"{outputs.oct_od1:.3f}", "mm", "ID1 + 2 * E_env", is_hl=True)
            write_row_item("对角外廓跨距", "OD2", f"{outputs.oct_od2:.3f}", "mm", "ID2 + 2 * E_env", is_hl=True)
            write_row_item("内轮廓总周长", "C_inner", f"{outputs.c_inner_mm:.3f}", "mm", "4*L1 + 4*L2 + 2*π*R1")
            write_row_item("外轮廓总周长", "C_outer", f"{outputs.c_outer_mm:.3f}", "mm", "C_in + 2*π*E_env (斯坦纳等距)")
        elif inputs.coil_type == CoilType.ARBITRARY_PERIMETER:
            write_row_item("内轮廓总周长", "C_inner", f"{outputs.c_inner_mm:.3f}", "mm", "CAD内壁周长基准")
            write_row_item("外轮廓总周长", "C_outer", f"{outputs.c_outer_mm:.3f}", "mm", "C_in + 2*π*E_env (斯坦纳等距)")
            write_row_item("外廓包络长度", "OL", f"{outputs.outer_len:.3f}", "mm", "Ref_L + 2*E_env")
            write_row_item("外廓包络宽度", "OW", f"{outputs.outer_wid:.3f}", "mm", "Ref_W + 2*E_env")
        else:
            write_row_item("实际外廓长度", "OL", f"{outputs.outer_len:.3f}", "mm", "跑道两端外轮廓")
            write_row_item("实际外廓宽度", "OW", f"{outputs.outer_wid:.3f}", "mm", "跑道侧边外包络")

        write_row_item("Z向总占位厚度", "F / Thickness", f"{outputs.thickness_h:.3f}", "mm", "轴向高度 (含1%蓬松系数)")
        write_row_item("单边外包络壁厚", "E_env", f"{outputs.e_env:.3f}", "mm", "模具干涉判定壁厚")
        write_row_item("平均单匝展开周长", "MLT", f"{outputs.mlt:.3f}", "mm", "解析积分计算所得")
        write_row_item("漆包线总长度", "L_tot", f"{outputs.total_wire_len_m:.3f}", "m", "单只线圈消耗线长")

        curr_row += 1
        # 三、电气性能、电磁指标与质量
        write_section("3. 电气阻抗、电感与质量槽满率 (Electrical & Magnetic)")
        write_row_item("20℃本征冷态电阻", "R20", f"{outputs.r20:.4f}", "Ω", "出厂检验基准阻抗", is_hl=True)
        write_row_item("理论单线标称米阻", "R/m", f"{outputs.rho_per_meter:.4f}", "Ω/m", "每米单线理论阻抗")
        write_row_item("环境态初始冷阻", "R_init", f"{outputs.r_init:.4f}", "Ω", f"基于环境温度 {inputs.ambient_temp}℃")
        write_row_item("热态平衡电阻", "DCR_hot", f"{outputs.dcr_hot:.4f}", "Ω", "电热自洽稳态阻抗", is_hl=True)
        write_row_item("Wheeler空心电感", "L", f"{outputs.inductance_uh:.2f}", "μH", f"折合 {outputs.inductance_mh:.4f} mH", is_hl=True)
        write_row_item("电磁激励安匝数", "ΣI (AT)", f"{outputs.ampere_turns:.2f}", "AT", "N × I 电磁激励源能力")
        write_row_item("所需驱动端电压", "V_term", f"{outputs.v_term:.4f}", "V", "驱动芯片额定输出")
        write_row_item("稳态焦耳发热功耗", "P", f"{outputs.joule_power_mw:.2f}", "mW", "I²R 静态耗散功率")
        write_row_item("线圈有效动质量", "Weight", f"{outputs.weight_g:.4f}", "g", f"约 {outputs.weight_g * 1000:.1f} mg")
        write_row_item("漆包线空间占空比", "Wire Fill", f"{outputs.wire_fill_factor:.2f}", "%", "含自粘漆皮利用率", is_hl=True)
        write_row_item("微观纯铜空间填充率", "Cu Fill", f"{outputs.copper_fill_factor:.2f}", "%", "纯铜占空比")

        curr_row += 1
        # 四、电热自洽温升
        write_section("4. 电-热自洽稳态温升 (Thermal Simulation)")
        write_row_item("稳态绝热极限温升", "ΔT", f"{outputs.delta_t:.2f}", "℃", "牛顿冷却平衡温升")
        write_row_item("最终稳态结温", "T_final", f"{outputs.t_final:.2f}", "℃", "线圈极限工作温度", is_hl=True)
        write_row_item("有效对流散热表面积", "A_cooling", f"{outputs.total_cooling_area_m2 * 1e6:.2f}", "mm²", "上下端面+内外侧壁")

        curr_row += 1
        # 五、DFM 模具干涉判定
        write_section("5. DFM 工程装配空间与安全卡控判定 (DFM Verdict)")
        if inputs.coil_type == CoilType.CIRCULAR:
            dfm_items = [
                ("外径结构空间限制 (OD)", outputs.outer_len, inputs.max_x_len_limit, "mm", outputs.dfm.x_passed, f"上限 ≤ {inputs.max_x_len_limit:.2f} mm"),
                ("Z向高度空间限制 (F)", outputs.thickness_h, inputs.max_z_h_limit, "mm", outputs.dfm.z_passed, f"上限 ≤ {inputs.max_z_h_limit:.2f} mm"),
                ("IC 驱动端电压超限", outputs.v_term, inputs.max_v_term_limit, "V", outputs.dfm.voltage_passed, f"上限 ≤ {inputs.max_v_term_limit:.2f} V"),
                ("漆包线/骨架耐温崩溃", outputs.t_final, inputs.max_temp_limit, "℃", outputs.dfm.temp_passed, f"上限 ≤ {inputs.max_temp_limit:.2f} ℃"),
            ]
        elif inputs.coil_type == CoilType.OCTAGONAL:
            dfm_items = [
                ("对边外跨度空间限制 (OD1)", outputs.oct_od1, inputs.max_x_len_limit, "mm", outputs.dfm.x_passed, f"上限 ≤ {inputs.max_x_len_limit:.2f} mm"),
                ("对角外跨度空间限制 (OD2)", outputs.oct_od2, inputs.max_y_wid_limit, "mm", outputs.dfm.y_passed, f"上限 ≤ {inputs.max_y_wid_limit:.2f} mm"),
                ("Z向高度空间限制 (F)", outputs.thickness_h, inputs.max_z_h_limit, "mm", outputs.dfm.z_passed, f"上限 ≤ {inputs.max_z_h_limit:.2f} mm"),
                ("IC 驱动端电压超限", outputs.v_term, inputs.max_v_term_limit, "V", outputs.dfm.voltage_passed, f"上限 ≤ {inputs.max_v_term_limit:.2f} V"),
                ("漆包线/骨架耐温崩溃", outputs.t_final, inputs.max_temp_limit, "℃", outputs.dfm.temp_passed, f"上限 ≤ {inputs.max_temp_limit:.2f} ℃"),
            ]
        else:
            dfm_items = [
                ("X向长度空间限制 (OL)", outputs.outer_len, inputs.max_x_len_limit, "mm", outputs.dfm.x_passed, f"上限 ≤ {inputs.max_x_len_limit:.2f} mm"),
                ("Y向宽度空间限制 (OW)", outputs.outer_wid, inputs.max_y_wid_limit, "mm", outputs.dfm.y_passed, f"上限 ≤ {inputs.max_y_wid_limit:.2f} mm"),
                ("Z向高度空间限制 (F)", outputs.thickness_h, inputs.max_z_h_limit, "mm", outputs.dfm.z_passed, f"上限 ≤ {inputs.max_z_h_limit:.2f} mm"),
                ("IC 驱动端电压超限", outputs.v_term, inputs.max_v_term_limit, "V", outputs.dfm.voltage_passed, f"上限 ≤ {inputs.max_v_term_limit:.2f} V"),
                ("漆包线/骨架耐温崩溃", outputs.t_final, inputs.max_temp_limit, "℃", outputs.dfm.temp_passed, f"上限 ≤ {inputs.max_temp_limit:.2f} ℃"),
            ]
        for name, curr_val, limit_val, unit, passed, limit_str in dfm_items:
            c1 = ws.cell(row=curr_row, column=1, value=name)
            c2 = ws.cell(row=curr_row, column=2, value="DFM-Check")
            c3 = ws.cell(row=curr_row, column=3, value=f"{curr_val:.3f}")
            c4 = ws.cell(row=curr_row, column=4, value=limit_str)
            c5 = ws.cell(row=curr_row, column=5, value="✓ 合格通过" if passed else "✖ 超标干涉报警")
            c1.font = font_bold
            c3.font = font_bold
            c5.font = font_pass if passed else font_fail
            c5.fill = c_pass_fill if passed else c_fail_fill
            for c in [c1, c2, c3, c4, c5]:
                c.border = border_box
                c.alignment = Alignment(horizontal="center" if c in [c2, c4, c5] else ("right" if c == c3 else "left"), vertical="center", wrap_text=False)
            ws.row_dimensions[curr_row].height = 22
            curr_row += 1

        # 动态智能计算列宽 (基于中文字符 2.3 权重与安全边距，确保任意屏幕与 Excel 版本均 100% 完整显示，无需手动调整)
        for col in ws.columns:
            col_idx = col[0].column
            col_letter = get_column_letter(col_idx)
            max_len = 0.0
            for cell in col:
                if cell.row > 3 and cell.value is not None:
                    s_val = str(cell.value)
                    if col_idx == 1 and s_val.startswith("【"):
                        continue
                    w = sum(2.3 if ord(ch) > 127 else 1.15 for ch in s_val)
                    if w > max_len:
                        max_len = w
            base_min = {1: 38, 2: 18, 3: 24, 4: 18, 5: 36}.get(col_idx, 20)
            ws.column_dimensions[col_letter].width = max(max_len + 5.0, base_min)

        wb.save(save_path)
        return save_path
