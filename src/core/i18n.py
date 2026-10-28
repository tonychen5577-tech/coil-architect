"""
=============================================================================
Module: src.core.i18n
Description: ANSV Coil-Architect Pro 全局轻量级国际化与中英双语引擎 (i18n)
支持中文 (zh_CN) 与英文 (en_US) 动态即时切换与持久化配置
=============================================================================
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal

# 语言枚举
LANG_ZH = "zh"
LANG_EN = "en"

# 配置文件路径
def _get_config_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "ANSV" / "CoilArchitect"
    base.mkdir(parents=True, exist_ok=True)
    return base / "app_config.json"


# =============================================================================
# 全球工业级中英双语核心词典库 (地道专业工业与电热仿真术语)
# =============================================================================
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ------------------ 窗口标题与全局品牌 ------------------
    "app_window_title": {
        "zh": "ANSV Coil-Architect Pro 2027 | 微型线圈设计与电热仿真工作站",
        "en": "ANSV Coil-Architect Pro 2027 | Micro-Coil Design & Electro-Thermal Simulation Workstation"
    },
    "platform_full_name": {
        "zh": "微型执行器与精密传动仿真验证平台",
        "en": "Actuator Numerical Simulation & Validation Platform"
    },
    "app_sub_title": {
        "zh": "微型线圈设计与电热仿真工作站",
        "en": "Micro Coil Design & Electro-Thermal Simulation Workstation"
    },

    # ------------------ 顶部工具栏 (Top Toolbar) ------------------
    "toolbar_project": {
        "zh": "🏷️ 项目:",
        "en": "🏷️ Project:"
    },
    "toolbar_preset": {
        "zh": "📐 预设:",
        "en": "📐 Preset:"
    },
    "preset_1": {
        "zh": "1. 手机VCM马达",
        "en": "1. Smartphone VCM Motor"
    },
    "preset_2": {
        "zh": "2. 手机LRA圆线圈",
        "en": "2. Haptic LRA Circular"
    },
    "preset_3": {
        "zh": "3. 手机LRA跑道线圈",
        "en": "3. Haptic LRA Racetrack"
    },
    "preset_4": {
        "zh": "4. VCM八角形线圈",
        "en": "4. VCM Octagonal Coil"
    },
    "preset_5": {
        "zh": "5. CAD异形线圈",
        "en": "5. Custom CAD Arbitrary"
    },
    "btn_load_project": {
        "zh": "📂 导入文件",
        "en": "📂 Import File"
    },
    "btn_save_project": {
        "zh": "💾 导出文件",
        "en": "💾 Export File"
    },
    "btn_export_report": {
        "zh": "📊 导出仿真报告",
        "en": "📊 Export Report"
    },
    "btn_license_trial": {
        "zh": "🛡️ 试用期剩 {days} 天",
        "en": "🛡️ Trial: {days} Days Left"
    },
    "btn_license_commercial": {
        "zh": "🛡️ 商业授权 (商业版)",
        "en": "🛡️ Commercial Active"
    },
    "btn_license_unauthorized": {
        "zh": "⚠️ 未激活 (点击激活)",
        "en": "⚠️ Unlicensed (Activate)"
    },
    "btn_about_system": {
        "zh": "ℹ️ 关于系统",
        "en": "ℹ️ About"
    },
    "lang_switch_tooltip": {
        "zh": "切换显示语言 (Switch Language: 中文 / English)",
        "en": "Switch display language (中文 / English)"
    },

    # ------------------ 左侧参数面板：几何与排线 ------------------
    "sec_geom_params": {
        "zh": "▶ 线圈几何与排线参数",
        "en": "▶ Coil Geometry & Winding Parameters"
    },
    "lbl_topology_type": {
        "zh": "线圈拓扑类型:",
        "en": "Topology Type:"
    },
    "topo_racetrack": {
        "zh": "跑道型线圈 (Racetrack)",
        "en": "Racetrack Coil"
    },
    "topo_octagonal": {
        "zh": "八角形线圈 (Octagonal)",
        "en": "Octagonal Coil"
    },
    "topo_circular": {
        "zh": "圆环形线圈 (Circular)",
        "en": "Circular Ring Coil"
    },
    "topo_arbitrary": {
        "zh": "异形周长线圈 (Arbitrary)",
        "en": "Arbitrary Contour Coil"
    },
    "lbl_inner_length": {
        "zh": "线圈内长 (IL)",
        "en": "Inner Length (IL)"
    },
    "lbl_inner_width": {
        "zh": "线圈内宽 (IW)",
        "en": "Inner Width (IW)"
    },
    "lbl_radial_layers": {
        "zh": "径向层数",
        "en": "Radial Layers"
    },
    "lbl_turns_per_layer": {
        "zh": "每层匝数",
        "en": "Turns per Layer"
    },
    "lbl_winding_mode": {
        "zh": "密排绕法模式:",
        "en": "Winding Pattern:"
    },
    "mode_hcp": {
        "zh": "异数交错密排 (HCP)",
        "en": "Hexagonal Close-Packed (HCP)"
    },
    "mode_orthogonal": {
        "zh": "正交矩形密排 (Square)",
        "en": "Square / Orthogonal"
    },
    "chk_crossover": {
        "zh": "计入 60° 换层交叉线",
        "en": "Include 60° Layer Crossover Wires"
    },
    "chk_die_press": {
        "zh": "启用模具限位压实",
        "en": "Enable Tooling Die Press Fit"
    },

    # ------------------ 左侧参数面板：线材与张力 ------------------
    "lbl_wire_shape": {
        "zh": "线材截面形态:",
        "en": "Wire Cross-Section Shape:"
    },
    "lbl_wire_catalog": {
        "zh": "线材出厂规格库选型 (非库内尺寸需咨询华冶定制):",
        "en": "Wire Specification Catalog (Custom sizes via Huaye):"
    },
    "lbl_square_side": {
        "zh": "正方边长 (a)",
        "en": "Square Side (a)"
    },
    "lbl_square_max_od": {
        "zh": "漆包外径 (D)",
        "en": "Insulated Outer Dia (D)"
    },
    "lbl_flat_max_w": {
        "zh": "带漆外宽 (W_out)",
        "en": "Insulated Width (W_out)"
    },
    "lbl_flat_max_h": {
        "zh": "带漆外厚 (H_out)",
        "en": "Insulated Height (H_out)"
    },
    "lbl_flat_w": {
        "zh": "宽边宽度 (W)",
        "en": "Flat Width (W)"
    },
    "lbl_flat_h": {
        "zh": "高边厚度 (H)",
        "en": "Flat Height/Thk (H)"
    },
    "lbl_flat_r": {
        "zh": "倒圆角半径 (r)",
        "en": "Corner Radius (r)"
    },
    "lbl_flat_winding_dir": {
        "zh": "扁线排线方向:",
        "en": "Winding Orientation:"
    },
    "lbl_enamel": {
        "zh": "漆膜绝缘等级:",
        "en": "Enamel Insulation Grade:"
    },
    "dfm_chip_hipot": {
        "zh": "耐压",
        "en": "Hi-Pot"
    },
    "sec_wire_params": {
        "zh": "▶ 漆包线线材与张力",
        "en": "▶ Magnet Wire & Tension Properties"
    },
    "lbl_bare_dia": {
        "zh": "铜线裸径 (d)",
        "en": "Bare Conductor Dia. (d)"
    },
    "lbl_outer_dia": {
        "zh": "漆包外径 (D)",
        "en": "Insulated Wire OD (D)"
    },
    "lbl_tension_ratio": {
        "zh": "张力拉伸系数",
        "en": "Tension Elongation Ratio"
    },
    "lbl_copper_grade": {
        "zh": "铜材电导等级:",
        "en": "Copper Conductor Grade:"
    },
    "btn_huaye_catalog": {
        "zh": "华冶线材库",
        "en": "Huaye Wire Catalog"
    },
    "btn_reset_wire": {
        "zh": "✕ 自定义",
        "en": "✕ Custom"
    },
    "grade_ofhc": {
        "zh": "高导无氧铜 OFHC",
        "en": "High Conductivity OFHC Copper"
    },
    "grade_etp": {
        "zh": "普通精炼电解铜 ETP",
        "en": "Standard Electrolytic Copper ETP"
    },

    # ------------------ 中间仿真指标卡 (Metric Cards) ------------------
    "sec_sim_results": {
        "zh": "▶ 仿真计算结果",
        "en": "▶ Simulation Outputs & Analytical Metrics"
    },
    "metric_outer_len": {
        "zh": "外廓长度 (L)",
        "en": "Outer Length (OL)"
    },
    "metric_outer_width": {
        "zh": "外廓宽度 (W)",
        "en": "Outer Width (OW)"
    },
    "metric_coil_height": {
        "zh": "线圈厚度 (H)",
        "en": "Coil Thickness (H)"
    },
    "metric_total_turns": {
        "zh": "线圈总匝数 (N)",
        "en": "Total Turns (N)"
    },
    "metric_dcr_20": {
        "zh": "20℃直流电阻",
        "en": "20°C DC Resistance"
    },
    "metric_init_res": {
        "zh": "初始测试电阻",
        "en": "Initial Test Resistance"
    },
    "metric_steady_res": {
        "zh": "工作稳态电阻",
        "en": "Steady-State Resistance"
    },
    "metric_inductance": {
        "zh": "线圈电感量 (L)",
        "en": "Inductance (L)"
    },
    "metric_term_voltage": {
        "zh": "工作端电压 (V)",
        "en": "Terminal Voltage (V)"
    },
    "metric_joule_heat": {
        "zh": "发热功耗 (P)",
        "en": "Joule Heat Power (P)"
    },
    "metric_ampere_turns": {
        "zh": "安匝数 (NI)",
        "en": "Ampere-Turns (NI)"
    },
    "metric_steady_temp": {
        "zh": "稳态工作温度 (T)",
        "en": "Steady Temperature (T)"
    },
    "metric_coil_weight": {
        "zh": "线圈重量",
        "en": "Coil Net Weight"
    },
    "metric_wire_space_factor": {
        "zh": "漆包线占空比",
        "en": "Wire Space Factor"
    },
    "metric_copper_fill_factor": {
        "zh": "纯铜截面填充率",
        "en": "Copper Fill Factor"
    },
    "metric_mean_turn_length": {
        "zh": "单匝平均周长",
        "en": "Mean Turn Length (MTL)"
    },
    "unit_turns": {
        "zh": "匝",
        "en": "turns"
    },
    "unit_layers": {
        "zh": "层",
        "en": "layers"
    },

    # ------------------ 画布与视窗选项卡 ------------------
    "tab_view_zx": {
        "zh": "Z-X 长向剖面 (X向装配公差)",
        "en": "Z-X Long Section (X-Assembly Clearance)"
    },
    "btn_view_zx": {
        "zh": "Z-X 长向",
        "en": "Z-X Length"
    },
    "btn_view_zy": {
        "zh": "Z-Y 宽向",
        "en": "Z-Y Width"
    },
    "btn_view_zoom_single": {
        "zh": "单侧放大",
        "en": "Detail Zoom"
    },
    "tab_canvas_2d_contour": {
        "zh": "2D 跑道外廓 (X-Y)",
        "en": "2D Contour (X-Y Plane)"
    },
    "tab_canvas_2d_dfm": {
        "zh": "2D 截面与限高 (DFM)",
        "en": "2D Section & DFM Height"
    },
    "tab_canvas_3d_axonometric": {
        "zh": "3D 空间斜视 (Y-Space)",
        "en": "3D Isometric View (Y-Space)"
    },

    # ------------------ DFM 制造与公差状态栏 ------------------
    "dfm_title": {
        "zh": "🛡️ 结构装配与 DFM 制造公差",
        "en": "🛡️ Mechanical Fit & DFM Tolerances"
    },
    "dfm_btn_settings": {
        "zh": "⚙️ 公差与限值设置",
        "en": "⚙️ Tolerance Settings"
    },
    "dfm_status_solved": {
        "zh": "✔ 求解完成",
        "en": "✔ Solver Converged"
    },
    "dfm_free_mode": {
        "zh": "自由参数模式 (DFM限值未开启)",
        "en": "Free Parameter Mode (DFM Limits Off)"
    },
    "dfm_airgap_ok": {
        "zh": "气隙安全 (Air Gap Pass)",
        "en": "Air Gap Pass"
    },
    "dfm_airgap_warn": {
        "zh": "气隙告警 (Air Gap Warning)",
        "en": "Air Gap Warning"
    },
    "dfm_airgap_interfere": {
        "zh": "结构干涉 (Interference Crash)",
        "en": "Interference Crash"
    },

    # ------------------ 方案比对抽屉与工程矩阵 ------------------
    "drawer_title": {
        "zh": "方案比对抽屉",
        "en": "Scheme Comparison Drawer"
    },
    "drawer_frozen_count": {
        "zh": "(已固化 {n} 组)",
        "en": "({n} schemes frozen)"
    },
    "btn_freeze_current": {
        "zh": "📌 固化当前方案",
        "en": "📌 Freeze Scheme"
    },
    "btn_copy_table": {
        "zh": "📋 复制对比表",
        "en": "📋 Copy Matrix"
    },
    "btn_export_excel": {
        "zh": "📊 导出 Excel",
        "en": "📊 Export Excel"
    },
    "btn_export_csv": {
        "zh": "📑 导出 CSV",
        "en": "📑 Export CSV"
    },
    "btn_clear_drawer": {
        "zh": "🗑️ 清空",
        "en": "🗑️ Clear"
    },
    "btn_pop_window": {
        "zh": "⛶ 弹出大窗",
        "en": "⛶ Detach Window"
    },
    "btn_embed_drawer": {
        "zh": "↘ 嵌入底部抽屉",
        "en": "↘ Embed to Drawer"
    },
    "col_live_param": {
        "zh": "实时微调 (Live) ⚡",
        "en": "Live Adjustment ⚡"
    },
    "col_baseline": {
        "zh": "[基准 📌]",
        "en": "[Baseline 📌]"
    },
    "btn_set_baseline": {
        "zh": "★ 设为基准",
        "en": "★ Set Baseline"
    },
    "btn_restore_scheme": {
        "zh": "⏮ 还原",
        "en": "⏮ Restore"
    },

    # ------------------ 状态栏 (Status Bar) ------------------
    "status_solver_ready": {
        "zh": "就绪 | 物理引擎: 高精度固定点不动点迭代模型已加载",
        "en": "Ready | Physics Engine: High-precision Fixed-point Iterative Solver Active"
    },
    "status_license_connecting": {
        "zh": "正在验证云端授权与环境指纹...",
        "en": "Verifying license anchor & environment fingerprint..."
    },
    "status_license_verified": {
        "zh": "授权有效 | 一机一码硬件数字签名已通过校验",
        "en": "License Active | Hardware Digital Signature Verified"
    },

    # ------------------ 激活弹窗双语 ------------------
    "act_dialog_title": {
        "zh": "商业授权激活与订购向导 — ANSV Coil-Architect Pro",
        "en": "License Activation & Purchase Guide — ANSV Coil-Architect Pro"
    },
    "act_header_title": {
        "zh": "ANSV Coil-Architect Pro · 商业授权激活与订购向导",
        "en": "ANSV Coil-Architect Pro · License Activation & Procurement Guide"
    },
    "act_header_sub": {
        "zh": "微型线圈设计与电热仿真工作站 | 官方正版授权认证 · 全球一机一码硬件加密防御体系",
        "en": "Micro Coil Design & Electro-Thermal Simulation | Hardware-Bound Security & Verification"
    },
    "act_tier_title": {
        "zh": "🛒 商业授权方案与双币资费 (Tier & Pricing):",
        "en": "🛒 Commercial License Tiers & Global Pricing:"
    },
    "act_promo_box": {
        "zh": "🔥 <b>限期 8 折首发特惠 (Limited-Time 20% OFF)</b>：<br>联系工程师开通即享全版本 <b>限时 8 折直降</b>（年度版立省 ¥1,120，仅需 <b>¥4,680 / $719</b>）！后续委托 ANSV 进行工程代工仿真或打样，首期软件费仍可冲抵技术服务费！",
        "en": "🔥 <b>Limited-Time 20% OFF Early Bird Discount</b>:<br>Contact our engineers to claim <b>20% instant discount</b> (Annual Commercial: <b>$719 / ¥4,680</b>, save $180)! Software license fee can be 100% credited toward future actuator simulation or prototyping services!"
    },
    "act_machine_code_title": {
        "zh": "💻 本机硬件特征码 (Machine Code):",
        "en": "💻 Local Hardware Machine Code:"
    },
    "act_btn_copy_mid": {
        "zh": "📋 复制机器码",
        "en": "📋 Copy Machine Code"
    },
    "act_btn_copy_order": {
        "zh": "💬 一键复制订购消息草稿 (微信 / WhatsApp 直发)",
        "en": "💬 Copy Order Request Message (WeChat / WhatsApp)"
    },
    "act_token_title": {
        "zh": "🔑 输入或粘贴商业许可证激活码 (License Token):",
        "en": "🔑 Paste Commercial License Token:"
    },
    "act_token_placeholder": {
        "zh": "粘贴 COIL-SEC-XXXX 格式激活码...",
        "en": "Paste COIL-SEC-XXXX activation code here..."
    },
    "act_btn_import_lic": {
        "zh": "📂 导入 license.lic 授权文件...",
        "en": "📂 Import license.lic File..."
    },
    "act_btn_cancel": {
        "zh": "暂不激活 (稍后处理)",
        "en": "Activate Later"
    },
    "act_btn_activate": {
        "zh": "立即验证并激活",
        "en": "Verify & Activate Now"
    },

    # ------------------ 关于弹窗双语 ------------------
    "about_title": {
        "zh": "关于系统 — ANSV 微型执行器与精密传动仿真验证平台",
        "en": "About System — ANSV Actuator Simulation & Validation Platform"
    },
    "about_tab_official": {
        "zh": "📢 官方公众号",
        "en": "📢 Official Channel"
    },
    "about_tab_wechat": {
        "zh": "💬 微信技术咨询",
        "en": "💬 WeChat Support"
    },
    "about_tab_whatsapp": {
        "zh": "🌐 WhatsApp (International)",
        "en": "🌐 WhatsApp (Global)"
    },
    "about_btn_create_shortcut": {
        "zh": "🖥️ 桌面快捷方式",
        "en": "🖥️ Desktop Shortcut"
    },
    "about_btn_assoc_file": {
        "zh": "🔗 关联 .ansvcoil 算例",
        "en": "🔗 Associate .ansvcoil"
    },
    "about_btn_export_log": {
        "zh": "📑 导出诊断日志",
        "en": "📑 Export Logs"
    },
    "about_btn_net_diag": {
        "zh": "🌐 网络数据库诊断",
        "en": "🌐 Network Diagnostic"
    },
    "about_btn_manual": {
        "zh": "📖 使用说明书",
        "en": "📖 User Manual (F1)"
    },
    "about_btn_check_update": {
        "zh": "🚀 检查更新",
        "en": "🚀 Check Updates"
    },
    "about_btn_ok": {
        "zh": "确定",
        "en": "OK"
    },
    # ------------------ 别名与补全词条 ------------------
        "scheme_prefix": {
        "zh": "方案",
        "en": "Scheme"
    },
    "btn_dfm_settings": {
        "zh": "⚙ 公差与限值设置",
        "en": "⚙ Tolerance / Limit Settings"
    },
    "dfm_section_title": {
        "zh": "🛡 结构装配与 DFM 制造公差",
        "en": "🛡 Structure Assembly & DFM Tolerances"
    },
    "metric_weight": {
        "zh": "线圈重量",
        "en": "Coil Weight"
    },
    "metric_wire_fill": {
        "zh": "漆包线占空比",
        "en": "Wire Space Factor"
    },
    "metric_copper_fill": {
        "zh": "纯铜截面填充率",
        "en": "Copper Fill Factor"
    },
    "metric_mlt": {
        "zh": "单匝平均周长",
        "en": "Mean Turn Length"
    },
    "unit_layer": {
        "zh": "层",
        "en": "Layers"
    },
    "unit_turn": {
        "zh": "匝",
        "en": "Turns"
    },
    "unit_ratio": {
        "zh": "系数",
        "en": "Ratio"
    },
    "tab_2d_contour": {
        "zh": "2D 跑道外廓 (X-Y)",
        "en": "2D Contour (X-Y)"
    },
    "tab_2d_circular": {
        "zh": "2D 外径轮廓 (X-Y)",
        "en": "2D Circular Contour (X-Y)"
    },
    "tab_2d_section": {
        "zh": "2D 截面与限高 (DFM)",
        "en": "2D Section / DFM Clearance"
    },
    "tab_3d_isometric": {
        "zh": "3D 空间斜视 (Y-Space)",
        "en": "3D Axonometric View"
    },
    "dfm_section_title": {
        "zh": "🛡 结构装配与 DFM 制造公差",
        "en": "🛡 Assembly & DFM Tolerance Limits"
    },
    "btn_dfm_settings": {
        "zh": "⚙ 公差与限值设置",
        "en": "⚙ Tolerance / Limit Settings"
    },
    "btn_dfm_settings_tip": {
        "zh": "点击快速定位至左侧 DFM 装配公差与安全限值配置区",
        "en": "Jump to left DFM tolerance and design safety limit settings"
    },
    "dfm_chip_x": {
        "zh": "X向",
        "en": "X-Axis"
    },
    "dfm_chip_y": {
        "zh": "Y向",
        "en": "Y-Axis"
    },
    "dfm_chip_z": {
        "zh": "Z向",
        "en": "Z-Axis"
    },
    "dfm_chip_v": {
        "zh": "端压",
        "en": "Voltage"
    },
    "dfm_chip_t": {
        "zh": "耐温",
        "en": "Temp."
    },
    "dfm_all_passed": {
        "zh": "✔ 求解完成 | R20 = {r20:.3f} Ω | 匝数 = {turns} 匝 | DFM 尺寸与公差全部合格",
        "en": "✔ Solved | R20 = {r20:.3f} Ω | Turns = {turns} T | All DFM Tolerances Passed"
    },
    "dfm_warning": {
        "zh": "⚠ 警告：存在尺寸干涉或超出设计限值，请调整参数！",
        "en": "⚠ Warning: Geometric interference or limit exceeded! Adjust parameters."
    },
    "drawer_pinned_count": {
        "zh": "已固化",
        "en": "Frozen:"
    },
    "drawer_pinned_unit": {
        "zh": "组",
        "en": "Schemes"
    },
    "btn_pin_scheme": {
        "zh": "📌 固化当前方案",
        "en": "📌 Freeze Scheme"
    },
    "btn_clear_schemes": {
        "zh": "🗑 清空",
        "en": "🗑 Clear"
    },
    "btn_popout_window": {
        "zh": "⛶ 弹出大窗",
        "en": "⛶ Pop-out"
    },
    "btn_embed_window": {
        "zh": "⇲ 嵌入底部抽屉",
        "en": "⇲ Embed in Drawer"
    },
    "btn_fold_drawer": {
        "zh": "收起 ▼",
        "en": "Collapse ▼"
    },
    "btn_unfold_drawer": {
        "zh": "展开 ▲",
        "en": "Expand ▲"
    },
    "col_metric": {
        "zh": "参数 / 指标项目",
        "en": "Parameter / Metric"
    },
    "col_live_tuning": {
        "zh": "实时微调 (Live) ⚡",
        "en": "Live Tuning ⚡"
    },
    "btn_license_expired": {
        "zh": "⚠️ 试用已到期",
        "en": "⚠️ Trial Expired"
    },
    "txt_project_placeholder": {
        "zh": "项目代号",
        "en": "Project ID"
    },
    "txt_project_tooltip": {
        "zh": "当前工程项目代号/名称（导出 Excel/CSV 报表与方案比对时将自动注入文件名与表格抬头）",
        "en": "Project ID or name (injected into exported Excel/CSV filenames and headers)"
    },
    "lbl_oct_hint": {
        "zh": "📐 图4规范: 4平直边 + 4斜边 + 8圆角 (配合四角三角磁钢)",
        "en": "📐 Fig.4 Spec: 4 Flat + 4 Bevels + 8 Fillets (for Corner Magnets)"
    },
    "lbl_oct_id1": {
        "zh": "对边内径 ID1",
        "en": "Flat Inner Dia. ID1"
    },
    "lbl_oct_id2": {
        "zh": "对角内径 ID2",
        "en": "Diagonal Inner Dia. ID2"
    },
    "lbl_oct_r1": {
        "zh": "拐角内圆角 R1",
        "en": "Corner Fillet R1"
    },
    "lbl_oct_derived": {
        "zh": "📐 几何推导尺寸: 平直长 L1 = {l1:.2f} mm  |  斜边长 L2 = {l2:.2f} mm",
        "en": "📐 Derived: Flat L1 = {l1:.2f} mm | Bevel L2 = {l2:.2f} mm"
    },
    "lbl_perim_hint": {
        "zh": "📐 异形线圈周长推算: MLT = 展开内周长 + π × 绕组厚度",
        "en": "📐 Contour MLT: Mean Turn Length = Inner Perimeter + π × Build Thickness"
    },
    "lbl_perim_cin": {
        "zh": "展开内周长 C_in",
        "en": "Inner Perimeter C_in"
    },
    "lbl_perim_max_x": {
        "zh": "参考外廓长 Max_X",
        "en": "Max Outer Length Max_X"
    },
    "lbl_perim_max_y": {
        "zh": "参考外廓宽 Max_Y",
        "en": "Max Outer Width Max_Y"
    },
    "lbl_die_press_thk": {
        "zh": "模具压实厚度",
        "en": "Die Press Fit Thickness"
    },
    "sec_thermal_env": {
        "zh": "▶ 工作环境与散热条件",
        "en": "▶ Thermal Environment & Heat Dissipation"
    },
    "lbl_cooling_condition": {
        "zh": "散热对流工况:",
        "en": "Cooling Condition:"
    },
    "env_weak_convection": {
        "zh": "模组内微弱对流",
        "en": "Internal Module Convection"
    },
    "env_fpc_enclosure": {
        "zh": "贴FPC+钢片封装",
        "en": "FPC + Steel Shim Enclosure"
    },
    "env_free_convection": {
        "zh": "悬空自然对流",
        "en": "Free Air Natural Convection"
    },
    "env_metal_case": {
        "zh": "紧密接触金属外壳",
        "en": "Tight Metal Chassis Contact"
    },
    "env_custom": {
        "zh": "自定义对流散热",
        "en": "Custom Convection"
    },
    "lbl_ambient_temp": {
        "zh": "环境温度",
        "en": "Ambient Temperature"
    },
    "lbl_test_current": {
        "zh": "测试电流",
        "en": "Drive / Test Current"
    },
    "lbl_convection_coeff": {
        "zh": "散热对流系数",
        "en": "Convection Coeff. (h)"
    },
    "sec_dfm_assembly": {
        "zh": "▶ 装配空间与公差约束 (DFM)",
        "en": "▶ Assembly Envelope & DFM Tolerances"
    },
    "chk_enable_dfm": {
        "zh": "启用 DFM 装配公差与限值检查",
        "en": "Enable DFM Assembly Clearance Check"
    },
    "lbl_limit_x": {
        "zh": "X向装配限值 (Max L)",
        "en": "X-Axis Limit (Max L)"
    },
    "lbl_limit_y": {
        "zh": "Y向装配限值 (Max W)",
        "en": "Y-Axis Limit (Max W)"
    },
    "lbl_limit_z": {
        "zh": "Z向装配限高 (Max H)",
        "en": "Z-Axis Limit (Max H)"
    },
    "lbl_limit_v": {
        "zh": "驱动电压上限 (Max V)",
        "en": "Max Drive Voltage (Max V)"
    },
    "lbl_insulation_temp_class": {
        "zh": "漆包线耐温等级:",
        "en": "Wire Insulation Thermal Class:"
    },
    "temp_class_130": {
        "zh": "130级 (B级 / 130℃)",
        "en": "Class 130 (B / 130°C)"
    },
    "temp_class_155": {
        "zh": "155级 (F级 / 155℃)",
        "en": "Class 155 (F / 155°C)"
    },
    "temp_class_180": {
        "zh": "180级 (H级 / 180℃)",
        "en": "Class 180 (H / 180°C)"
    },
    "temp_class_200": {
        "zh": "200级 (C级 / 200℃)",
        "en": "Class 200 (C / 200°C)"
    },
    "temp_class_custom": {
        "zh": "自定义耐温限值",
        "en": "Custom Temp Limit"
    },
    "lbl_limit_temp": {
        "zh": "耐温安全上限",
        "en": "Max Safe Operating Temp"
    },
    "grade_mfr": {
        "zh": "厂家出厂典型实测",
        "en": "Manufacturer Typical Value"
    },
    "grade_spec": {
        "zh": "国内厂家规格书基准",
        "en": "Domestic Specification Standard"
    },
    "grade_iacs": {
        "zh": "国际标准退火纯铜 IACS",
        "en": "International Annealed Copper IACS"
    },
    "grade_custom": {
        "zh": "自定义实测电阻率",
        "en": "Custom Resistivity"
    },
    "lbl_copper_rho": {
        "zh": "20℃铜电阻率",
        "en": "20°C Copper Resistivity"
    },
    "dialog_compare_title": {
        "zh": "📊 固化方案独立对比与工程评审矩阵",
        "en": "📊 Scheme Comparison & Engineering Review Matrix"
    },
    "status_ready": {
        "zh": "就绪 | 双核物理引擎待命",
        "en": "Ready | Dual-Core Physics Engine Standby"
    },
    "row_inner_dims": {
        "zh": "内腔内径/长宽 (mm)",
        "en": "Inner Bore / Dims (mm)"
    },
    "row_wall_thickness": {
        "zh": "单边壁厚 E (mm)",
        "en": "Wall Thickness E (mm)"
    },
    "btn_export_schemes": {
        "zh": "💾 导出方案",
        "en": "💾 Export Schemes"
    },
    "btn_import_schemes": {
        "zh": "📂 导入方案",
        "en": "📂 Import Schemes"
    },
    "row_topology": {
        "zh": "绕线拓扑",
        "en": "Coil Topology"
    },
    "row_bare_dia": {
        "zh": "铜线裸径 d (mm)",
        "en": "Bare Conductor d (mm)"
    },
    "row_outer_dia": {
        "zh": "漆包外径 D (mm)",
        "en": "Insulated Wire OD D (mm)"
    },
    "row_layers": {
        "zh": "径向层数 I (层)",
        "en": "Radial Layers I"
    },
    "row_turns_per_layer": {
        "zh": "每层匝数 J (匝)",
        "en": "Turns per Layer J"
    },
    "row_winding_mode": {
        "zh": "绕线模式",
        "en": "Winding Pattern"
    },
    "row_tension": {
        "zh": "张力系数 η",
        "en": "Tension Coeff. η"
    },
    "row_total_turns": {
        "zh": "成型总匝数 N (匝)",
        "en": "Total Turns N"
    },
    "row_outer_dims": {
        "zh": "外廓长宽/对边 (mm)",
        "en": "Outer Dimensions (mm)"
    },
    "row_coil_height": {
        "zh": "轴向成型厚度 H (mm)",
        "en": "Axial Thickness H (mm)"
    },
    "row_r20": {
        "zh": "20℃直流电阻 R20 (Ω)",
        "en": "20°C DC Res. R20 (Ω)"
    },
    "row_inductance": {
        "zh": "等效电感 L (μH)",
        "en": "Equivalent Inductance L (μH)"
    },
    "row_copper_fill": {
        "zh": "纯铜填充率 (%)",
        "en": "Copper Fill Factor (%)"
    },
    "row_dfm_status": {
        "zh": "DFM 制造公差",
        "en": "DFM Tolerance Status"
    },
    "row_action": {
        "zh": "方案操作",
        "en": "Action"
    },
}


class I18nManager(QObject):
    """
    轻量级响应式国际化单例管理器
    负责多语言查询、配置持久化与全局信号调度
    """
    language_changed = pyqtSignal(str)

    _instance: Optional["I18nManager"] = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_lang = self._load_saved_language()

    def _load_saved_language(self) -> str:
        """从持久化配置文件中读取上次用户选择的语言"""
        cfg_path = _get_config_path()
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    lang = data.get("language", LANG_ZH)
                    if lang in [LANG_ZH, LANG_EN]:
                        return lang
            except Exception:
                pass
        return LANG_ZH

    def _save_language(self, lang: str):
        """持久化保存用户的语言偏好"""
        cfg_path = _get_config_path()
        try:
            data = {}
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data["language"] = lang
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang: str):
        """设置当前语言并广播变更信号"""
        if lang not in [LANG_ZH, LANG_EN]:
            return
        if self._current_lang != lang:
            self._current_lang = lang
            self._save_language(lang)
            self.language_changed.emit(lang)

    def is_english(self) -> bool:
        return self._current_lang == LANG_EN

    def t(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        根据当前语言查询词条；支持 {var} 格式化插值
        如果未查到，返回 default 或 key 本身
        """
        entry = TRANSLATIONS.get(key)
        if entry:
            text = entry.get(self._current_lang) or entry.get(LANG_ZH) or (default if default is not None else key)
        else:
            text = default if default is not None else key

        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text


# 全局单例与快捷函数
i18n = I18nManager()

def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """全局翻译快捷函数: t('btn_export_report')"""
    return i18n.t(key, default=default, **kwargs)
