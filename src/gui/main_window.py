"""
Coil-Architect Pro - Main Window
工业级高对比度双核物理仿真工作站主窗口
"""

import os
import json
import math
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QComboBox, QFrame, QSplitter, 
    QScrollArea, QFileDialog, QMessageBox, QStatusBar, QCheckBox,
    QLineEdit, QInputDialog
)

from ..core.models import CoilInputs, CoilOutputs, WindingMode, CoilType
from ..core.physics_engine import CoilPhysicsEngine
from .styles import LIGHT_INDUSTRIAL_QSS
from .widgets.slider_spin_box import FloatSliderBox, IntSliderBox
from .widgets.metric_card import MetricCard
from .widgets.dfm_indicator import DFMStatusStrip
from .widgets.coil_canvas import CoilDualCanvasWidget
from .widgets.comparison_drawer import ComparisonDrawer, SchemeSnapshot
from .utils import atomic_write_json, atomic_write_text
from .about_dialog import AboutDialog
from src.version import APP_NAME, APP_TITLE, APP_VERSION, APP_BUILD, APP_AUTHOR, OFFICIAL_URL, COPYRIGHT_TEXT, CORE_ENGINE_AUTHOR
from src.utils.logger import get_logger
from pathlib import Path

logger = get_logger("MainWindow")


class MainWindow(QMainWindow):
    """Coil-Architect Pro 主工作站"""

    signal_cloud_status = pyqtSignal(bool, str, str)  # (is_online, message, base_url)
    signal_remote_command = pyqtSignal(str, str)      # (command, payload)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} {APP_VERSION}")
        self.resize(1380, 860)
        self.setMinimumSize(1100, 720)

        self.inputs = CoilInputs()
        self.outputs = CoilOutputs()
        self._is_syncing_params = False

        # 连接云端协同信号
        self.signal_cloud_status.connect(self._on_cloud_status_received)
        self.signal_remote_command.connect(self._on_remote_command_received)

        # 加载 Clean White 工业样式
        self.setStyleSheet(LIGHT_INDUSTRIAL_QSS)

        self._init_ui()
        self._load_preset(self.combo_presets.itemText(0))
        self.run_simulation()

        # 启动后台授权检测与守护引擎 (每 30 分钟静默检测一次授权服务器)
        try:
            from src.core.cloud_client import CloudClient
            CloudClient.start_background_sync(
                interval_sec=1800.0,
                on_status_callback=lambda ok, msg, url: self.signal_cloud_status.emit(ok, msg, url),
                on_command_callback=lambda cmd, payload: self.signal_remote_command.emit(cmd, payload)
            )
        except Exception as e:
            logger.debug(f"启动云端心跳失败: {e}")

    def _init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # 1. 顶部全局导航工具条
        top_bar = self._create_top_toolbar()
        root_layout.addWidget(top_bar)

        # 2. 主工作区分割器 (左侧参数控制，右侧仿真计算结果与图纸视口)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)

        # 左侧参数区
        left_panel = self._create_left_parameter_panel()
        self.splitter.addWidget(left_panel)

        # 右侧仿真结果与图纸区
        right_panel = self._create_right_twin_panel()
        self.splitter.addWidget(right_panel)

        # 设置弹性比例：左 0 (锁死左栏，绝不随输出内容自动拉伸)，右 1 (右栏自适应吸收窗口缩放)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self._splitter_left_width = 440
        self.splitter.setSizes([self._splitter_left_width, 940])
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        root_layout.addWidget(self.splitter, 1)

        # 3. 底部状态栏与常驻三行版权 (依据规范 04.二)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 | 物理引擎: 高精度固定点不动点迭代模型已加载")
        self._setup_statusbar_copyright()
        self._setup_tooltips()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "splitter") and hasattr(self, "_splitter_left_width"):
            sizes = self.splitter.sizes()
            total_w = sum(sizes) if sizes else self.splitter.width()
            self.splitter.setSizes([self._splitter_left_width, max(100, total_w - self._splitter_left_width)])

    def _on_splitter_moved(self, pos: int, index: int):
        """记录用户手工拖拽的左栏宽度，锁定禁止内容变化导致自适应跳动"""
        if pos and pos > 100:
            self._splitter_left_width = pos
        else:
            sizes = self.splitter.sizes()
            if sizes and len(sizes) >= 2:
                self._splitter_left_width = sizes[0]

    def _on_dfm_enabled_toggled(self, checked: bool):
        """响应 DFM 卡控总开关切换 (默认关闭)"""
        if hasattr(self, "w_dfm_panel"):
            self.w_dfm_panel.setEnabled(checked)
        self.run_simulation()

    def _setup_tooltips(self):
        """为所有输入控件、选项卡与 16 宫格输出卡片配置高对比度工程释义 Tooltip"""
        # 1. 顶部工具栏
        self.combo_presets.setToolTip("【工程预设 (Engineering Presets)】\n快速加载工业对标标准工程算例（含手机摄像头VCM对焦马达、0825硬币式Z-LRA震动马达、X-LRA跑道线圈、图4八角形线圈等），自动填充标准几何、线径、张力与热学工况。")

        # 2. 卡片 1: 几何与模具拓扑
        self.combo_coil_type.setToolTip("【线圈拓扑类型 (Coil Topology)】\n选择线圈物理几何构型：\n• 跑道型线圈 (Racetrack)：适用于横向线性马达 (X-LRA)、长条音圈马达 (VCM)\n• 圆线圈 (Circular)：适用于硬币式震动马达 (Z-LRA)、空心杯电机\n• 八角形线圈 (Octagonal)：标准45°倒角八边形，契合手机摄像头紧凑防抖磁钢结构\n• 通用异形线圈：基于 CAD 测得的内轮廓展开周长推导中线周长与阻抗")
        self.sb_inner_len.setToolTip("【线圈内长 (Inner Length IL)】\n跑道型绕线模具内芯的长边直线跨距（圆线圈模式下自动切换为线圈内径 ID）。内长直接决定内腔开孔长边尺寸与磁芯配合间隙。")
        self.sb_inner_wid.setToolTip("【线圈内宽 (Inner Width IW)】\n跑道型绕线模具内芯的短边直线跨距，跑道型内侧圆角半径由内宽的一半决定 (R = IW/2)。圆线圈模式下锁定等于内径。")

        if hasattr(self, "sb_oct_id1"):
            self.sb_oct_id1.setToolTip("【对边内径 (Octagonal ID1)】\n八角形线圈两平直边内表面之间的垂直法向跨距 (mm)，作为八角形模具平直侧基准尺寸。")
        if hasattr(self, "sb_oct_id2"):
            self.sb_oct_id2.setToolTip("【对角内径 (Octagonal ID2)】\n八角形线圈相对两 45° 倒角斜边内表面之间的法向跨距 (mm)。")
        if hasattr(self, "sb_oct_l1"):
            self.sb_oct_l1.setToolTip("【平直段内长 (Octagonal L1)】\n八角形平直段内表面长度 (mm)，由几何关系根据 ID1、ID2 及拐角半径 R1 闭式反推联动。")
        if hasattr(self, "sb_oct_l2"):
            self.sb_oct_l2.setToolTip("【斜边段内长 (Octagonal L2)】\n八角形 45° 倒角斜边段内表面长度 (mm)，契合摄像头防抖对角磁钢。")
        if hasattr(self, "sb_oct_r1"):
            self.sb_oct_r1.setToolTip("【内拐角半径 (Octagonal R1)】\n八角形线圈 8 个内拐角过渡倒角半径 (mm)，消除应力集中并防止高速绕线挂破绝缘漆。")
        if hasattr(self, "lbl_oct_derived"):
            self.lbl_oct_derived.setToolTip("【八角形几何推导参考尺寸】\n由对边内径 ID1、对角内径 ID2 及拐角半径 R1 严格通过闭合几何方程解析计算得出的平直段长 L1 与 45° 斜边长 L2。")

        if hasattr(self, "sb_perim_in"):
            self.sb_perim_in.setToolTip("【内周长展开 (CAD C_inner)】\n在二维或三维 CAD 软件中沿线圈内腔壁测得的实际内轮廓展开周长 (mm)。")
        if hasattr(self, "sb_perim_outer_len"):
            self.sb_perim_outer_len.setToolTip("【异形参考外长 (Max Outer X)】\n异形线圈沿长轴方向的最大包络参考尺寸 (mm)，用于装配干涉卡控。")
        if hasattr(self, "sb_perim_outer_wid"):
            self.sb_perim_outer_wid.setToolTip("【异形参考外宽 (Max Outer Y)】\n异形线圈沿短轴方向的最大包络参考尺寸 (mm)，用于装配干涉卡控。")

        self.sb_radial_layers.setToolTip("【径向层数】\n线圈壁厚方向紧密排布的线圈层数，支持 0.5 半层（如 18.5 层），用于模拟单层起绕与出线。")
        self.sb_axial_turns.setToolTip("【每层匝数】\n沿线圈高度方向每层紧密排列的导线圈数，决定线圈轴向绕线高度。")
        self.combo_mode.setToolTip("【密排排法】\n• 异数交错密排 (HCP)：相邻层导线嵌入下层两线间的凹槽，层高约 0.866 倍线径，紧密节省空间\n• 同数交错密排：各层匝数相等")

        if hasattr(self, "chk_crossover"):
            self.chk_crossover.setToolTip("【60° 换层交叉线】\n跑道线圈每层爬升换层时在圆弧区产生的交叉搭接，会导致局部宽度微量增加。")
        if hasattr(self, "chk_mold_clamping"):
            self.chk_mold_clamping.setToolTip("【模具限位压实】\n模拟治具模具将线圈轴向高度压实至设定型腔厚度。")
        if hasattr(self, "sb_mold_height"):
            self.sb_mold_height.setToolTip("【模具压实厚度】\n模具型腔限位厚度 (mm)。受不可压缩铜截面积物理下限保护。")

        # 3. 卡片 2: 线材规格与张力
        self.sb_bare_dia.setToolTip("【铜线裸径】\n纯铜导体的标称截面直径 (mm)，直接决定铜截面积与电阻大小。")
        self.sb_max_od.setToolTip("【漆包外径】\n带绝缘漆膜和自粘胶层的导线最大外径 (mm)，决定线圈排线实际占位。")
        self.sb_tension.setToolTip("【张力拉伸系数】\n绕线机张力引起的导线微量塑性拉伸系数。张力偏大会使导线微量变细、实测电阻升高。")
        self.combo_copper_grade.setToolTip("【铜材电阻率规格】\n选择标准铜材电导等级或实测电阻率。高导无氧铜 (OFHC) 典型为 0.016959 Ω·mm²/m。")
        self.sb_copper_rho.setToolTip("【20℃铜电阻率】\n20℃ 环境下铜材的体电阻率 (Ω·mm²/m)。")

        # 4. 卡片 3: 热与散热工况
        self.combo_thermal_env.setToolTip("【散热环境预设】\n选择线圈典型的安装与散热工况，快速匹配表面换热系数。")
        self.sb_ambient_temp.setToolTip("【环境温度】\n线圈工作环境的基础温度 (℃)。")
        self.sb_drive_current.setToolTip("【测试电流】\n流过线圈的连续工作电流 (mA)。")
        self.sb_convection_h.setToolTip("【散热对流系数】\n线圈表面与周围环境的综合换热系数 (W/(m²·K))。")

        # 5. 卡片 4: DFM 限值
        if hasattr(self, "chk_dfm_enabled"):
            self.chk_dfm_enabled.setToolTip("【装配空间与安全卡控】\n开启后，系统将对比尺寸、高度、电压与温度是否超标，并以红绿灯提示。默认关闭为自由设计模式。")
        self.sb_limit_x.setToolTip("【X向装配限值】\n装配结构允许线圈沿 X 向（长边）的最大尺寸 (mm)。")
        self.sb_limit_y.setToolTip("【Y向装配限值】\n装配结构允许线圈沿 Y 向（短边）的最大尺寸 (mm)。")
        self.sb_limit_z.setToolTip("【Z向装配限高】\n机构空间允许线圈轴向高度/成型厚度的最大尺寸 (mm)。")
        self.sb_limit_v.setToolTip("【端电压上限】\n驱动芯片 (IC) 输出引脚的最大允许驱动电压 (V)。")
        self.combo_temp_class.setToolTip("【漆包线耐温等级】\n常用耐温标准：120级 (120℃)、155级 (155℃)、180级 (180℃)。")
        self.sb_limit_t.setToolTip("【耐温等级上限】\n漆包线绝缘层允许承受的最高长期工作温度 (℃)。")

        # 6. 右侧 16 宫格仿真指标卡片
        self.card_ol.setToolTip("【外廓长度】\n线圈长边方向的最大外尺寸 (mm)。圆线圈模式下即为线圈外径。")
        self.card_ow.setToolTip("【外廓宽度】\n线圈短边方向的最大外尺寸 (mm)。已计入排线叠层、换层引线增量或模具压实后的实际宽度。")
        self.card_thk.setToolTip("【线圈厚度】\n线圈沿轴向的总高度/厚度 (mm)。未压实时为自然排线成型厚度，开启压实时为模具限位厚度。")
        self.card_n.setToolTip("【线圈总匝数】\n线圈实际导线总圈数 N（总匝数 = 径向层数 × 每层匝数）。")

        self.card_r20.setToolTip("【20℃直流电阻】\n在标准 20℃ 温度下的直流电阻 (Ω)。标题栏显示标称米阻 (Ω/m)，为出厂检验 (IQC/OQC) 的核心对标指标。")
        self.card_r_init.setToolTip("【初始测试电阻】\n在当前设定环境温度 (Ta) 下、线圈未通电时的初始直流电阻 (Ω)。")
        self.card_dcr_hot.setToolTip("【工作稳态电阻】\n线圈通电发热稳定后的直流电阻 (Ω)。温度上升导致阻值增大，会引起实际驱动电流或推力衰减。")
        self.card_inductance.setToolTip("【线圈电感量】\n空心多层绕组的估算自感值 (μH)，基于标准空心多层电感公式计算。")

        self.card_v_term.setToolTip("【工作端电压】\n线圈流过设定测试电流时所需的驱动端电压 U = I × R (V)。需确保在驱动芯片供电能力范围内。")
        self.card_power.setToolTip("【发热功耗】\n通电时线圈产生的焦耳热发热功率 P = I² × R (mW)，会引起线圈及周边结构温升。")
        self.card_ampere_turns.setToolTip("【安匝数 NI】\n磁动势核心参数 NI = 匝数 × 电流 (A·t)。在气隙磁场一定时，直接决定马达或执行器的输出电磁力。")
        self.card_t_final.setToolTip("【稳态工作温度】\n通电发热达到热平衡后的线圈最高工作温度 (℃)。不得超过漆包线绝缘耐温极限。")

        self.card_weight.setToolTip("【线圈重量】\n线圈导线的纯铜质量 (g)，由线长、铜截面积与铜密度 (8.96 g/cm³) 严格计算。")
        self.card_wire_fill.setToolTip("【漆包线占空比】\n全部漆包线（含外漆）截面积与绕线区矩形截面的比例 (%)，反映绕组排线紧密程度。")
        self.card_cu_fill.setToolTip("【纯铜截面填充率】\n纯铜导体的实际导电面积与绕线区截面的比例 (%)，衡量有效导电金属的截面利用率。")
        self.card_mlt.setToolTip("【单匝平均周长】\n各层绕组的平均单圈周长 (mm)。线圈总线长 = 单匝平均周长 × 总匝数。")

        # 7. 矢量画布与状态带
        if hasattr(self, "canvas_widget") and hasattr(self.canvas_widget, "tab_macro"):
            self.canvas_widget.tab_macro.setTabToolTip(0, "【2D 跑道外廓 / 外径轮廓】\n线圈俯视 X-Y 坐标外廓轮廓、线圈内腔开孔、四角圆弧及 60° 换层引线特征。")
            self.canvas_widget.tab_macro.setTabToolTip(1, "【2D 截面与限高分析】\n线圈轴向成型厚度与装配外壳限高安全余量分析，排查 Z 向干涉风险。")
            self.canvas_widget.tab_macro.setTabToolTip(2, "【3D 空间斜视】\n三维等轴测立体透视，全面呈现线圈在机构三维空间笼内的装配容差。")
        if hasattr(self, "dfm_strip"):
            self.dfm_strip.setToolTip("【DFM 模具装配与安全卡控状态带】\n实时卡控包络尺寸、限高、端电压与耐温等级。点击右侧齿轮可快速定位至左侧限值设定区。")
        if hasattr(self, "comparison_drawer"):
            self.comparison_drawer.setToolTip("【方案比对抽屉】\n记录手动固化的参数方案并进行横向对比分析，支持基准比对、一键还原与报表导出。")

    def _setup_statusbar_copyright(self):
        """配置右下角三行常驻版权信息与云端实时状态 (规范 04.二)"""
        # 授权服务器在线状态指示与快捷检测按钮
        self.btn_cloud_status = QPushButton("⏳ 授权服务器连接中...")
        self.btn_cloud_status.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
                margin-right: 14px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0284C7;
                border-color: #0284C7;
            }
        """)
        self.btn_cloud_status.setToolTip("点击立即检测授权服务器连通性与最新商业状态")
        self.btn_cloud_status.clicked.connect(self._on_cloud_status_clicked)
        self.status_bar.addPermanentWidget(self.btn_cloud_status)

        copyright_widget = QWidget()
        copy_layout = QVBoxLayout(copyright_widget)
        copy_layout.setContentsMargins(0, 0, 8, 2)
        copy_layout.setSpacing(0)

        lbl_c1 = QLabel(f"Core Architecture & Algorithm: {CORE_ENGINE_AUTHOR} (<a href='{OFFICIAL_URL}' style='color:#0284C7; text-decoration:none;'>{OFFICIAL_URL.replace('https://', '')}</a>)")
        lbl_c1.setOpenExternalLinks(True)
        lbl_c1.setStyleSheet("font-size: 10px; color: #64748B; line-height: 1.1;")
        lbl_c1.setAlignment(Qt.AlignmentFlag.AlignRight)
        copy_layout.addWidget(lbl_c1)

        lbl_c2 = QLabel(f"{APP_NAME} {APP_VERSION} | Build {APP_BUILD}")
        lbl_c2.setStyleSheet("font-size: 10px; color: #334155; font-weight: 700; line-height: 1.1;")
        lbl_c2.setAlignment(Qt.AlignmentFlag.AlignRight)
        copy_layout.addWidget(lbl_c2)

        lbl_c3 = QLabel(f"Copyright © 2026 <a href='{OFFICIAL_URL}' style='color:#0284C7; text-decoration:none;'>{OFFICIAL_URL.replace('https://', '')}</a> & {CORE_ENGINE_AUTHOR}. All rights reserved.")
        lbl_c3.setOpenExternalLinks(True)
        lbl_c3.setStyleSheet("font-size: 9.5px; color: #94A3B8; line-height: 1.1;")
        lbl_c3.setAlignment(Qt.AlignmentFlag.AlignRight)
        copy_layout.addWidget(lbl_c3)

        self.status_bar.addPermanentWidget(copyright_widget)

    def _on_cloud_status_received(self, ok: bool, msg: str, target: str):
        """线程安全槽：刷新状态栏授权服务器连接状态"""
        if not hasattr(self, "btn_cloud_status"):
            return
        if ok:
            domain = target.replace("https://", "").replace("http://", "")
            self.btn_cloud_status.setText("🟢 授权服务器已连接")
            self.btn_cloud_status.setStyleSheet("""
                QPushButton {
                    background-color: #ECFDF5;
                    color: #059669;
                    border: 1px solid #A7F3D0;
                    border-radius: 4px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    margin-right: 14px;
                }
                QPushButton:hover {
                    background-color: #D1FAE5;
                }
            """)
            self.btn_cloud_status.setToolTip(
                f"已连接至官方授权中心: {domain}\n"
                "✓ 本工位机线圈物理仿真设计数据 100% 留存在本地，绝不上云。\n"
                "✓ 仅执行商业授权校验与版本检测 (每 30 分钟心跳一次)。\n"
                "点击可立即测试授权连通性。"
            )
        else:
            self.btn_cloud_status.setText("⚪ 本地授权模式")
            self.btn_cloud_status.setStyleSheet("""
                QPushButton {
                    background-color: #F8FAFC;
                    color: #94A3B8;
                    border: 1px solid #E2E8F0;
                    border-radius: 4px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    margin-right: 14px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                }
            """)
            self.btn_cloud_status.setToolTip(
                f"{msg}\n"
                "当前线圈仿真全功能不受影响，本地商业授权持续有效。\n"
                "设计数据 100% 保存在本地，点击可重试连接官方授权服务器。"
            )

    def _on_cloud_status_clicked(self):
        """点击底部授权状态指示按钮立即触发一次检测"""
        self.btn_cloud_status.setText("🔄 授权验证中...")
        from src.core.cloud_client import CloudClient
        CloudClient.trigger_sync_now()

    def _on_remote_command_received(self, cmd: str, payload: str):
        """响应来自 Cloudflare 边缘控制台的远程指令 (对标 Gear)"""
        cmd_upper = (cmd or "").upper().strip()
        logger.warning(f"MainWindow 捕获云端远程遥控指令: {cmd_upper}")

        if cmd_upper in ("LOCK_APP", "REVOKE_LICENSE"):
            if getattr(self, "_remote_locked_flag", False):
                return
            self._remote_locked_flag = True

            # 停止云端心跳
            from src.core.cloud_client import CloudClient
            CloudClient.stop_background_sync()

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("商业授权终止通知")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setText(
                "【当前工位机商业授权已被管理员在云端控制台吊销 / 终止】\n\n"
                "软件已安全锁定并清除本地授权凭证。\n"
                "如需恢复或重新开通授权，请联系 ANSV 官方管理员重新签发。"
            )
            btn_exit = msg_box.addButton("关闭退出", QMessageBox.ButtonRole.AcceptRole)
            msg_box.setDefaultButton(btn_exit)
            msg_box.exec()

            self.close()
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.quit()

        elif cmd_upper == "UPDATE_LICENSE":
            self.status_bar.showMessage("🎉 云端已远程下发最新商业授权，系统已自动刷新生效！", 5000)
            QMessageBox.information(
                self,
                "云端授权更新成功",
                "管理员已通过云端控制台为您延长了商业授权 / 升级了方案版本！\n\n当前授权凭证已在本地自动刷新生效。"
            )

        elif cmd_upper == "FORCE_SYNC_CASES":
            self.status_bar.showMessage("📐 云端标杆案例库已更新", 4000)

    def closeEvent(self, event):
        """主窗口关闭时安全销毁后台守护线程"""
        try:
            from src.core.cloud_client import CloudClient
            CloudClient.stop_background_sync()
        except Exception:
            pass
        super().closeEvent(event)

    def _show_about_dialog(self):
        """弹出 16:9 工业标准关于系统对话框"""
        dlg = AboutDialog(self)
        dlg.exec()

    def _create_top_toolbar(self) -> QWidget:
        bar = QFrame(self)
        bar.setObjectName("topToolbarFrame")
        bar.setStyleSheet("""
            #topToolbarFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Logo / 标题
        lbl_brand = QLabel("🌀 Coil-Architect Pro")
        lbl_brand.setStyleSheet("font-size: 15px; font-weight: 800; color: #0284C7;")
        layout.addWidget(lbl_brand)

        lbl_sub = QLabel("精密线圈多物理场仿真工作站")
        lbl_sub.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        layout.addWidget(lbl_sub)

        layout.addSpacing(15)

        # 项目名称输入框 (预设: Coli-Architect)
        lbl_proj = QLabel("🏷️ 项目名称:")
        lbl_proj.setStyleSheet("font-size: 11px; font-weight: 700; color: #1E293B; margin-left: 2px;")
        layout.addWidget(lbl_proj)

        self.txt_project_name = QLineEdit("Coli-Architect")
        self.txt_project_name.setPlaceholderText("预设: Coli-Architect")
        self.txt_project_name.setToolTip("当前工程项目代号/名称（导出 Excel/CSV 报表与方案比对时将自动注入文件名与表格抬头）")
        self.txt_project_name.setFixedWidth(150)
        self.txt_project_name.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #0284C7;
                background-color: #F8FAFC;
            }
        """)
        layout.addWidget(self.txt_project_name)

        layout.addSpacing(10)

        # 快速预设方案
        lbl_preset = QLabel("工程预设:")
        lbl_preset.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        layout.addWidget(lbl_preset)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "1. 手机VCM马达",
            "2. 手机LRA圆线圈",
            "3. 手机LRA跑道线圈",
            "4. VCM八角形线圈",
            "5. CAD异形线圈"
        ])
        self.combo_presets.currentTextChanged.connect(self._load_preset)
        self.combo_presets.setFixedWidth(270)
        layout.addWidget(self.combo_presets)

        layout.addStretch()

        # 算例操作按钮
        btn_open = QPushButton("📂 载入算例")
        btn_open.clicked.connect(self._import_project)
        layout.addWidget(btn_open)

        btn_save = QPushButton("💾 保存算例")
        btn_save.clicked.connect(self._export_project)
        layout.addWidget(btn_save)

        btn_export = QPushButton("📊 导出评审报告 (Excel)")
        btn_export.clicked.connect(self._export_report)
        btn_export.setProperty("class", "SuccessBtn")
        layout.addWidget(btn_export)

        layout.addSpacing(10)

        # 商业授权指示灯
        license_chip = QLabel("🛡 正式商业授权 (ANSV 工业版)")
        license_chip.setStyleSheet("""
            background-color: #ECFDF5;
            color: #059669;
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
        """)
        layout.addWidget(license_chip)

        # 关于系统按钮 (规范 04.二)
        btn_about = QPushButton("ℹ️ 关于系统")
        btn_about.clicked.connect(self._show_about_dialog)
        layout.addWidget(btn_about)

        return bar

    def get_project_name(self) -> str:
        """获取当前工程项目名称 (去除首尾空格，若未填则保底默认 Coli-Architect)"""
        if hasattr(self, "txt_project_name"):
            val = self.txt_project_name.text().strip()
            if val:
                return val
        return "Coli-Architect"


    def _create_left_parameter_panel(self) -> QWidget:
        """左侧参数化精细控制区"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(440)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 4, 10, 4)
        layout.setSpacing(10)

        # 卡片 1: 线圈几何与排线参数
        grp_geo = QFrame()
        grp_geo.setProperty("class", "CardFrame")
        layout_geo = QVBoxLayout(grp_geo)
        layout_geo.setSpacing(6)
        lbl_geo = QLabel("▶ 线圈几何与排线参数")
        lbl_geo.setProperty("class", "SectionTitle")
        layout_geo.addWidget(lbl_geo)

        lbl_type = QLabel("线圈拓扑类型:")
        lbl_type.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 2px;")
        layout_geo.addWidget(lbl_type)
        self.combo_coil_type = QComboBox()
        self.combo_coil_type.addItem("跑道型线圈 (Racetrack)", CoilType.RACETRACK)
        self.combo_coil_type.addItem("圆形线圈 (Circular)", CoilType.CIRCULAR)
        self.combo_coil_type.addItem("八角形线圈 (Octagonal)", CoilType.OCTAGONAL)
        self.combo_coil_type.addItem("CAD异形线圈", CoilType.ARBITRARY_PERIMETER)
        self.combo_coil_type.currentIndexChanged.connect(self._on_coil_type_changed)
        layout_geo.addWidget(self.combo_coil_type)

        # 跑道型与圆线圈专属尺寸
        self.sb_inner_len = FloatSliderBox("线圈内长 (IL)", "mm", 0.5, 40.0, 4.86, 0.01)
        self.sb_inner_wid = FloatSliderBox("线圈内宽 (IW)", "mm", 0.2, 20.0, 1.50, 0.01)
        layout_geo.addWidget(self.sb_inner_len)
        layout_geo.addWidget(self.sb_inner_wid)

        # 八角形线圈专属面板 (严格遵循图4工程图规范)
        self.w_oct_panel = QFrame()
        layout_oct = QVBoxLayout(self.w_oct_panel)
        layout_oct.setContentsMargins(0, 0, 0, 0)
        layout_oct.setSpacing(4)
        lbl_oct_hint = QLabel("📐 图4规范: 4平直边 + 4斜边 + 8圆角 (配合四角三角磁钢)")
        lbl_oct_hint.setStyleSheet("font-size: 10px; font-weight: 700; color: #0284C7; background: #F0F9FF; padding: 4px 6px; border-radius: 4px; border: 1px solid #BAE6FD;")
        layout_oct.addWidget(lbl_oct_hint)

        self.sb_oct_id1 = FloatSliderBox("对边内径 ID1", "mm", 1.0, 25.0, 7.10, 0.01)
        self.sb_oct_id2 = FloatSliderBox("对角内径 ID2", "mm", 1.0, 30.0, 7.05, 0.01)
        self.sb_oct_r1 = FloatSliderBox("拐角内圆角 R1", "mm", 0.05, 1.50, 0.30, 0.01)

        self._oct_l1 = 2.62
        self._oct_l2 = 2.74
        self.lbl_oct_derived = QLabel("📐 几何推导尺寸: 平直长 L1 = 2.62 mm  |  斜边长 L2 = 2.74 mm")
        self.lbl_oct_derived.setStyleSheet("font-size: 10px; font-weight: 600; color: #0369A1; background: #F0F9FF; padding: 5px 8px; border-radius: 4px; border: 1px solid #BAE6FD;")

        # 保持 dummy 兼容性，避免任何旧属性调用遗漏
        class _OctLCompat:
            def __init__(self, init_val): self._v = init_val
            def value(self): return self._v
            def setValue(self, v): self._v = float(v)
            def blockSignals(self, _): pass
            def setToolTip(self, _): pass
        self.sb_oct_l1 = _OctLCompat(2.62)
        self.sb_oct_l2 = _OctLCompat(2.74)

        self.sb_oct_id1.valueChanged.connect(self._on_oct_params_changed)
        self.sb_oct_id2.valueChanged.connect(self._on_oct_params_changed)
        self.sb_oct_r1.valueChanged.connect(self._on_oct_params_changed)

        layout_oct.addWidget(self.sb_oct_id1)
        layout_oct.addWidget(self.sb_oct_id2)
        layout_oct.addWidget(self.sb_oct_r1)
        layout_oct.addWidget(self.lbl_oct_derived)
        self.w_oct_panel.setVisible(False)
        layout_geo.addWidget(self.w_oct_panel)

        # 通用异形线圈专属面板 (中线/内周长推算)
        self.w_perim_panel = QFrame()
        layout_perim = QVBoxLayout(self.w_perim_panel)
        layout_perim.setContentsMargins(0, 0, 0, 0)
        layout_perim.setSpacing(4)
        lbl_perim_hint = QLabel("📐 异形线圈周长推算: MLT = 展开内周长 + π × 绕组厚度")
        lbl_perim_hint.setStyleSheet("font-size: 10px; font-weight: 700; color: #0D9488; background: #F0FDFA; padding: 4px 6px; border-radius: 4px; border: 1px solid #99F6E4;")
        layout_perim.addWidget(lbl_perim_hint)

        self.sb_perim_in = FloatSliderBox("展开内周长 C_in", "mm", 1.0, 200.0, 20.0, 0.05)
        self.sb_perim_outer_len = FloatSliderBox("参考外廓长 Max_X", "mm", 1.0, 50.0, 7.0, 0.05)
        self.sb_perim_outer_wid = FloatSliderBox("参考外廓宽 Max_Y", "mm", 1.0, 50.0, 5.0, 0.05)

        self.sb_perim_in.valueChanged.connect(self.run_simulation)
        self.sb_perim_outer_len.valueChanged.connect(self.run_simulation)
        self.sb_perim_outer_wid.valueChanged.connect(self.run_simulation)

        layout_perim.addWidget(self.sb_perim_in)
        layout_perim.addWidget(self.sb_perim_outer_len)
        layout_perim.addWidget(self.sb_perim_outer_wid)
        self.w_perim_panel.setVisible(False)
        layout_geo.addWidget(self.w_perim_panel)

        self.sb_radial_layers = FloatSliderBox("径向层数", "层", 0.5, 50.0, 14.0, 0.5, decimals=1)
        self.sb_axial_turns = IntSliderBox("每层匝数", "匝", 1, 80, 12)

        layout_geo.addWidget(self.sb_radial_layers)
        layout_geo.addWidget(self.sb_axial_turns)

        lbl_mode = QLabel("密排排法模式:")
        lbl_mode.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 4px;")
        layout_geo.addWidget(lbl_mode)

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("异数交错密排 (HCP)", WindingMode.VARIABLE)
        self.combo_mode.addItem("同数交错密排", WindingMode.EVEN)
        layout_geo.addWidget(self.combo_mode)

        # 换层交叉线与模具限位压实
        self.chk_crossover = QCheckBox("计入 60° 换层交叉线")
        self.chk_crossover.setStyleSheet("font-size: 11px; font-weight: 600; color: #D97706; margin-top: 6px;")
        layout_geo.addWidget(self.chk_crossover)

        self.chk_mold_clamping = QCheckBox("启用模具限位压实")
        self.chk_mold_clamping.setStyleSheet("font-size: 11px; font-weight: 600; color: #0284C7; margin-top: 4px;")
        layout_geo.addWidget(self.chk_mold_clamping)

        self.w_mold_panel = QWidget()
        layout_mold = QVBoxLayout(self.w_mold_panel)
        layout_mold.setContentsMargins(0, 0, 0, 0)
        layout_mold.setSpacing(4)
        self.sb_mold_height = FloatSliderBox("模具压实厚度", "mm", 0.10, 5.00, 0.55, 0.01, decimals=2)
        layout_mold.addWidget(self.sb_mold_height)
        self.w_mold_panel.setVisible(False)
        layout_geo.addWidget(self.w_mold_panel)

        self.chk_crossover.toggled.connect(self.run_simulation)
        self.chk_mold_clamping.toggled.connect(lambda checked: self.w_mold_panel.setVisible(checked))
        self.chk_mold_clamping.toggled.connect(self.run_simulation)
        self.sb_mold_height.valueChanged.connect(self.run_simulation)

        layout.addWidget(grp_geo)

        # 卡片 2: 漆包线线材与张力
        grp_wire = QFrame()
        grp_wire.setProperty("class", "CardFrame")
        layout_wire = QVBoxLayout(grp_wire)
        layout_wire.setSpacing(6)
        lbl_wire = QLabel("▶ 漆包线线材与张力")
        lbl_wire.setProperty("class", "SectionTitle")
        layout_wire.addWidget(lbl_wire)

        self.sb_bare_dia = FloatSliderBox("铜线裸径 (d)", "mm", 0.010, 0.800, 0.075, 0.001)
        self.sb_max_od = FloatSliderBox("漆包外径 (D)", "mm", 0.012, 1.000, 0.085, 0.001)
        self.sb_tension = FloatSliderBox("张力拉伸系数", "系数", 0.85, 1.00, 0.99, 0.005)

        layout_wire.addWidget(self.sb_bare_dia)
        layout_wire.addWidget(self.sb_max_od)
        layout_wire.addWidget(self.sb_tension)

        lbl_rho = QLabel("铜材电导等级:")
        lbl_rho.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 4px;")
        layout_wire.addWidget(lbl_rho)

        self.combo_copper_grade = QComboBox()
        self.combo_copper_grade.addItem("高导电率无氧铜 OFHC", 0.016959)
        self.combo_copper_grade.addItem("厂家出厂典型实测", 0.016920)
        self.combo_copper_grade.addItem("国内厂家规格书基准", 0.017100)
        self.combo_copper_grade.addItem("国际标准退火纯铜 IACS", 0.017241)
        self.combo_copper_grade.addItem("自定义实测电阻率", -1.0)
        self.combo_copper_grade.currentIndexChanged.connect(self._on_copper_grade_changed)
        layout_wire.addWidget(self.combo_copper_grade)

        self.sb_copper_rho = FloatSliderBox("20℃铜电阻率", "Ω·mm²/m", 0.0150, 0.0200, 0.016959, 0.00001, decimals=6)
        self.sb_copper_rho.valueChanged.connect(self._on_copper_rho_slider_changed)
        layout_wire.addWidget(self.sb_copper_rho)

        layout.addWidget(grp_wire)

        # 卡片 3: 工作环境与散热条件
        grp_thermal = QFrame()
        grp_thermal.setProperty("class", "CardFrame")
        layout_thermal = QVBoxLayout(grp_thermal)
        layout_thermal.setSpacing(6)
        lbl_thermal = QLabel("▶ 工作环境与散热条件")
        lbl_thermal.setProperty("class", "SectionTitle")
        layout_thermal.addWidget(lbl_thermal)

        lbl_env = QLabel("散热对流工况:")
        lbl_env.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 2px;")
        layout_thermal.addWidget(lbl_env)

        self.combo_thermal_env = QComboBox()
        self.combo_thermal_env.addItem("模组内微弱对流", 25.0)
        self.combo_thermal_env.addItem("贴FPC+钢片封装", 40.0)
        self.combo_thermal_env.addItem("悬空自然对流", 15.0)
        self.combo_thermal_env.addItem("紧密接触金属外壳", 50.0)
        self.combo_thermal_env.addItem("自定义对流散热", -1.0)
        self.combo_thermal_env.currentIndexChanged.connect(self._on_thermal_env_changed)
        layout_thermal.addWidget(self.combo_thermal_env)

        self.sb_ambient_temp = FloatSliderBox("环境温度", "℃", -20.0, 85.0, 20.0, 0.5)
        self.sb_drive_current = FloatSliderBox("测试电流", "mA", 0.0, 500.0, 10.0, 1.0)
        self.sb_convection_h = FloatSliderBox("散热对流系数", "W/(m²·K)", 5.0, 100.0, 25.0, 1.0)
        self.sb_convection_h.valueChanged.connect(self._on_convection_h_slider_changed)

        layout_thermal.addWidget(self.sb_ambient_temp)
        layout_thermal.addWidget(self.sb_drive_current)
        layout_thermal.addWidget(self.sb_convection_h)

        layout.addWidget(grp_thermal)

        # 卡片 4: 装配空间与安全卡控 (DFM)
        self.grp_dfm = QFrame()
        self.grp_dfm.setProperty("class", "CardFrame")
        layout_dfm = QVBoxLayout(self.grp_dfm)
        layout_dfm.setSpacing(6)
        lbl_dfm = QLabel("▶ 装配空间与安全卡控 (DFM)")
        lbl_dfm.setProperty("class", "SectionTitle")
        layout_dfm.addWidget(lbl_dfm)

        # DFM 卡限总开关 (默认关闭，避免自由设计/微调匝数电阻时频繁红标报警)
        self.chk_dfm_enabled = QCheckBox("启用装配空间与安全卡控 (DFM)")
        self.chk_dfm_enabled.setChecked(False)
        self.chk_dfm_enabled.setStyleSheet("font-size: 11px; font-weight: 700; color: #0284C7; margin-bottom: 4px;")
        self.chk_dfm_enabled.toggled.connect(self._on_dfm_enabled_toggled)
        layout_dfm.addWidget(self.chk_dfm_enabled)

        # 内部限值面板容器 (未勾选时置灰，直观展现自由设计状态)
        self.w_dfm_panel = QWidget()
        layout_dfm_panel = QVBoxLayout(self.w_dfm_panel)
        layout_dfm_panel.setContentsMargins(0, 0, 0, 0)
        layout_dfm_panel.setSpacing(6)

        self.sb_limit_x = FloatSliderBox("X向装配限值", "mm", 1.0, 30.0, 7.20, 0.05)
        self.sb_limit_y = FloatSliderBox("Y向装配限值", "mm", 1.0, 20.0, 3.82, 0.05)
        self.sb_limit_z = FloatSliderBox("Z向装配限高", "mm", 0.2, 10.0, 1.05, 0.02)
        self.sb_limit_v = FloatSliderBox("端电压上限", "V", 0.5, 12.0, 2.80, 0.05)

        # 漆包线耐温等级快捷选择 (预设 120等级 / 155等级 / 180等级)
        lbl_temp_class = QLabel("漆包线耐温等级:")
        lbl_temp_class.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        layout_dfm_panel.addWidget(lbl_temp_class)

        self.combo_temp_class = QComboBox()
        self.combo_temp_class.addItem("120等级 (120℃)", 120.0)
        self.combo_temp_class.addItem("155等级 (155℃)", 155.0)
        self.combo_temp_class.addItem("180等级 (180℃)", 180.0)
        self.combo_temp_class.addItem("自定义耐温等级", None)
        self.combo_temp_class.setCurrentIndex(1)  # 默认 155等级
        self.combo_temp_class.currentIndexChanged.connect(self._on_temp_class_changed)
        layout_dfm_panel.addWidget(self.combo_temp_class)

        self.sb_limit_t = FloatSliderBox("耐温等级上限", "℃", 60.0, 220.0, 155.0, 5.0)
        self.sb_limit_t.valueChanged.connect(self._on_limit_t_slider_changed)

        layout_dfm_panel.addWidget(self.sb_limit_x)
        layout_dfm_panel.addWidget(self.sb_limit_y)
        layout_dfm_panel.addWidget(self.sb_limit_z)
        layout_dfm_panel.addWidget(self.sb_limit_v)
        layout_dfm_panel.addWidget(self.sb_limit_t)

        self.w_dfm_panel.setEnabled(False)
        layout_dfm.addWidget(self.w_dfm_panel)

        layout.addWidget(self.grp_dfm)

        # 信号绑定：针对几何与线材核心参数挂载专业防呆联动槽，其余直接挂载仿真重算
        self.sb_bare_dia.valueChanged.connect(self._on_bare_dia_changed)
        self.sb_max_od.valueChanged.connect(self._on_max_od_changed)
        self.sb_inner_len.valueChanged.connect(self._on_inner_len_changed)
        self.sb_inner_wid.valueChanged.connect(self._on_inner_wid_changed)

        for widget in [
            self.sb_radial_layers, self.sb_axial_turns, 
            self.sb_tension, self.sb_copper_rho,
            self.sb_ambient_temp, self.sb_drive_current, 
            self.sb_convection_h,
            self.sb_limit_x, self.sb_limit_y, self.sb_limit_z,
            self.sb_limit_v
        ]:
            widget.valueChanged.connect(self.run_simulation)

        self.combo_mode.currentIndexChanged.connect(self.run_simulation)

        layout.addStretch()
        self.scroll_left = scroll
        scroll.setWidget(container)
        return scroll

    def _create_right_twin_panel(self) -> QWidget:
        """右侧仿真计算结果面板与物理视口"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # 1. 仿真计算结果 (16 宫格卡片)
        twin_frame = QFrame()
        twin_frame.setObjectName("twinBusFrame")
        twin_frame.setStyleSheet("""
            #twinBusFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        layout_twin = QVBoxLayout(twin_frame)
        layout_twin.setContentsMargins(8, 6, 8, 6)
        layout_twin.setSpacing(6)

        lbl_twin_title = QLabel("▶ 仿真计算结果")
        lbl_twin_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0284C7;")
        layout_twin.addWidget(lbl_twin_title)

        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(8)

        # 4 列布局 (16 宫格全物理指标矩阵)
        col1 = QVBoxLayout()
        self.card_ol = MetricCard("外廓长度 (L)", "mm")
        self.card_ow = MetricCard("外廓宽度 (W)", "mm")
        self.card_thk = MetricCard("线圈厚度 (H)", "mm")
        self.card_n = MetricCard("线圈总匝数 (N)", "匝", accent_color="#D97706")
        col1.addWidget(self.card_ol)
        col1.addWidget(self.card_ow)
        col1.addWidget(self.card_thk)
        col1.addWidget(self.card_n)

        col2 = QVBoxLayout()
        self.card_r20 = MetricCard("20℃直流电阻", "Ω")
        self.card_r_init = MetricCard("初始测试电阻", "Ω")
        self.card_dcr_hot = MetricCard("工作稳态电阻", "Ω", accent_color="#D97706")
        self.card_inductance = MetricCard("线圈电感量 (L)", "μH", accent_color="#0284C7")
        col2.addWidget(self.card_r20)
        col2.addWidget(self.card_r_init)
        col2.addWidget(self.card_dcr_hot)
        col2.addWidget(self.card_inductance)

        col3 = QVBoxLayout()
        self.card_v_term = MetricCard("工作端电压 (V)", "V")
        self.card_power = MetricCard("发热功耗 (P)", "mW")
        self.card_ampere_turns = MetricCard("安匝数 (NI)", "AT", accent_color="#7C3AED")
        self.card_t_final = MetricCard("稳态工作温度 (T)", "℃", accent_color="#DC2626")
        col3.addWidget(self.card_v_term)
        col3.addWidget(self.card_power)
        col3.addWidget(self.card_ampere_turns)
        col3.addWidget(self.card_t_final)

        col4 = QVBoxLayout()
        self.card_weight = MetricCard("线圈重量", "g")
        self.card_wire_fill = MetricCard("漆包线占空比", "%", accent_color="#D97706")
        self.card_cu_fill = MetricCard("纯铜截面填充率", "%")
        self.card_mlt = MetricCard("单匝平均周长", "mm")
        col4.addWidget(self.card_weight)
        col4.addWidget(self.card_wire_fill)
        col4.addWidget(self.card_cu_fill)
        col4.addWidget(self.card_mlt)

        grid_layout.addLayout(col1)
        grid_layout.addLayout(col2)
        grid_layout.addLayout(col3)
        grid_layout.addLayout(col4)
        layout_twin.addLayout(grid_layout)

        layout.addWidget(twin_frame)

        # 2. 核心双矢量视口 (左：微观排线；右：跑道/圆线圈 2D 轮廓与空间装配截面)
        self.canvas_widget = CoilDualCanvasWidget(self)
        layout.addWidget(self.canvas_widget, 1)

        # 3. 底部 DFM 空间与电气安全卡控条
        self.dfm_strip = DFMStatusStrip(self)
        self.dfm_strip.settingsClicked.connect(self._scroll_to_dfm)
        layout.addWidget(self.dfm_strip)

        # 4. 底部方案比对与调参记录抽屉 (纯手动固化与横向对比矩阵)
        self.comparison_drawer = ComparisonDrawer(self)
        self.comparison_drawer.restore_requested.connect(self._restore_scheme_inputs)
        self.comparison_drawer.status_message.connect(lambda msg: self.status_bar.showMessage(msg, 3500))
        layout.addWidget(self.comparison_drawer)

        # 用 QScrollArea 容器包裹整个右侧视口，防止笔记本小屏幕展开抽屉时挤压截断上方 DFM 状态条
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setWidget(panel)
        self.scroll_right = scroll

        return scroll

    def _scroll_to_dfm(self):
        """平滑滚动至左侧 DFM 卡控阈值设定区"""
        self.scroll_left.ensureWidgetVisible(self.grp_dfm)
        self.status_bar.showMessage("已定位至左侧 DFM 模具装配与安全卡控限值设定面板", 3000)

    def _on_bare_dia_changed(self, bare_dia: float):
        """标称铜裸径变动响应"""
        curr_max_od = self.sb_max_od.value()
        if curr_max_od < bare_dia + 0.002:
            self.status_bar.showMessage(f"💡 提示: 标称外径 ({curr_max_od:.3f}mm) 应大于铜裸径 ({bare_dia:.3f}mm) 加漆膜厚度", 3000)
        self.run_simulation()

    def _on_max_od_changed(self, max_od: float):
        """标称最大外径变动响应 (绝不篡改用户的裸铜径输入)"""
        curr_bare = self.sb_bare_dia.value()
        if curr_bare > max_od - 0.002:
            self.status_bar.showMessage(f"💡 提示: 最大外径 ({max_od:.3f}mm) 需包含漆膜，求解器已进行物理安全自适应", 3000)
        self.run_simulation()

    def _on_inner_len_changed(self, inner_len: float):
        """内长变动防呆联动"""
        if getattr(self, "_is_syncing_params", False):
            return
        self._is_syncing_params = True
        try:
            c_type = self.combo_coil_type.currentData() if hasattr(self, "combo_coil_type") else CoilType.RACETRACK
            if c_type == CoilType.CIRCULAR:
                # 圆形线圈：内宽严格等于内长 (作为内径 ID)
                self.sb_inner_wid.setValue(inner_len)
            else:
                # 跑道型线圈：内宽不得超过内长 (保证平直段长度 >= 0)
                if self.sb_inner_wid.value() > inner_len:
                    self.sb_inner_wid.setValue(inner_len)
            # 联动 DFM X 空间限值下限 (不得小于内孔)
            if self.sb_limit_x.value() < inner_len + 0.2:
                self.sb_limit_x.setValue(round(inner_len + 1.5, 2))
        finally:
            self._is_syncing_params = False
        self.run_simulation()

    def _on_inner_wid_changed(self, inner_wid: float):
        """内宽变动防呆联动"""
        if getattr(self, "_is_syncing_params", False):
            return
        self._is_syncing_params = True
        try:
            c_type = self.combo_coil_type.currentData() if hasattr(self, "combo_coil_type") else CoilType.RACETRACK
            if c_type == CoilType.RACETRACK:
                # 跑道型线圈：若内宽调大超过内长，自动推大内长
                if inner_wid > self.sb_inner_len.value():
                    self.sb_inner_len.setValue(inner_wid)
                    self.status_bar.showMessage("几何公理联动: 跑道线圈内长 (Inner_Len) 已自动延展以满足 内长 ≥ 内宽", 3000)
                # 联动 DFM Y 空间限值下限 (不得小于内孔)
                if self.sb_limit_y.value() < inner_wid + 0.2:
                    self.sb_limit_y.setValue(round(inner_wid + 1.0, 2))
        finally:
            self._is_syncing_params = False
        self.run_simulation()

    def _on_oct_params_changed(self, _=None):
        """八角形线圈 ID1/ID2/R1 变动自动推导边长 L1/L2 并动态约束防呆"""
        if getattr(self, "_is_syncing_params", False):
            return
        self._is_syncing_params = True
        try:
            id1 = self.sb_oct_id1.value() if hasattr(self, "sb_oct_id1") else 7.10
            r1 = self.sb_oct_r1.value() if hasattr(self, "sb_oct_r1") else 0.30
            sqrt2 = math.sqrt(2.0)
            r1_cut = 2.0 * (sqrt2 - 1.0) * r1

            # 严格几何上下限约束 (保证平直长 L1 >= 0.20 mm 且斜边长 L2 >= 0.20 mm)
            id2_min = max(0.5, (id1 + 0.20 + r1_cut) / sqrt2)
            id2_max = max(id2_min + 0.1, sqrt2 * id1 - r1_cut - 0.20)

            if hasattr(self, "sb_oct_id2"):
                self.sb_oct_id2.setRange(round(id2_min, 2), round(id2_max, 2))
                id2 = self.sb_oct_id2.value()
            else:
                id2 = id1 * 1.14

            calc_l1 = max(0.20, sqrt2 * id2 - id1 - r1_cut)
            calc_l2 = max(0.20, sqrt2 * id1 - id2 - r1_cut)

            self._oct_l1 = calc_l1
            self._oct_l2 = calc_l2
            if hasattr(self, "sb_oct_l1"):
                self.sb_oct_l1.setValue(calc_l1)
            if hasattr(self, "sb_oct_l2"):
                self.sb_oct_l2.setValue(calc_l2)

            if hasattr(self, "lbl_oct_derived"):
                self.lbl_oct_derived.setText(
                    f"📐 闭式几何推导参考尺寸: 平直长 L1 = {calc_l1:.2f} mm  |  斜边长 L2 = {calc_l2:.2f} mm"
                )

            # 几何与装配空间联动：当八角形内径增大时，自动延展外廓 DFM 空间限值
            min_req_limit = round(max(id1 + 3.0, id2 * 1.05 + 1.5), 1)
            if hasattr(self, "sb_limit_x") and self.sb_limit_x.value() < min_req_limit:
                self.sb_limit_x.setValue(min_req_limit)
            if hasattr(self, "sb_limit_y") and self.sb_limit_y.value() < min_req_limit:
                self.sb_limit_y.setValue(min_req_limit)
        finally:
            self._is_syncing_params = False
        self.run_simulation()

    def _on_coil_type_changed(self, idx: int):
        """响应线圈拓扑切换 (跑道型 / 圆形 / 八角形 / 通用异形)"""
        coil_type = self.combo_coil_type.currentData()

        # 显隐八角形与通用异形参数面板
        if hasattr(self, "w_oct_panel"):
            self.w_oct_panel.setVisible(coil_type == CoilType.OCTAGONAL)
        if hasattr(self, "w_perim_panel"):
            self.w_perim_panel.setVisible(coil_type == CoilType.ARBITRARY_PERIMETER)

        # 显隐跑道型专属的 60° 换层交叉线与模具限位压实选项 (圆线圈/八角形/异形不显示)
        is_racetrack = (coil_type == CoilType.RACETRACK)
        if hasattr(self, "chk_crossover"):
            self.chk_crossover.setVisible(is_racetrack)
        if hasattr(self, "chk_mold_clamping"):
            self.chk_mold_clamping.setVisible(is_racetrack)
        if hasattr(self, "w_mold_panel"):
            self.w_mold_panel.setVisible(is_racetrack and self.chk_mold_clamping.isChecked())

        is_std = (coil_type in (CoilType.RACETRACK, CoilType.CIRCULAR))
        self.sb_inner_len.setVisible(is_std)
        self.sb_inner_wid.setVisible(is_std)

        if coil_type == CoilType.CIRCULAR:
            self.sb_inner_len.lbl_title.setText("线圈内径 (Inner Dia ID)")
            self.sb_inner_wid.lbl_title.setText("线圈内宽 (圆线圈锁定为内径)")
            self.sb_inner_wid.setEnabled(False)
            self.sb_inner_wid.setValue(self.sb_inner_len.value())
            self.sb_limit_x.lbl_title.setText("外径结构空间上限 (Max OD)")
            self.sb_limit_y.lbl_title.setText("Y 空间上限 (圆线圈等同X向)")
            self.sb_limit_y.setEnabled(False)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText("Z 向装配限高上限 (Max Z)")
        elif coil_type == CoilType.OCTAGONAL:
            self.sb_limit_x.lbl_title.setText("X/对边外形空间上限 (Max X/OD1)")
            self.sb_limit_y.lbl_title.setText("Y/对角外形空间上限 (Max Y/OD2)")
            self.sb_limit_y.setEnabled(True)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText("Z 向装配限高上限 (Max Z)")
            # 自动根据 ID1/ID2 预设合理的 VCM 模组空间上限 (通常 9.5~10.5 mm)
            if hasattr(self, "sb_oct_id1"):
                id1_v = self.sb_oct_id1.value()
                id2_v = self.sb_oct_id2.value() if hasattr(self, "sb_oct_id2") else id1_v * 1.14
                req_lim = max(9.50, round(max(id1_v + 3.0, id2_v + 2.5), 1))
                if self.sb_limit_x.value() < req_lim:
                    self.sb_limit_x.setValue(req_lim)
                if self.sb_limit_y.value() < req_lim:
                    self.sb_limit_y.setValue(req_lim)
        elif coil_type == CoilType.ARBITRARY_PERIMETER:
            self.sb_limit_x.lbl_title.setText("X 向参考装配上限 (Max X)")
            self.sb_limit_y.lbl_title.setText("Y 向参考装配上限 (Max Y)")
            self.sb_limit_y.setEnabled(True)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText("Z 向装配限高上限 (Max Z)")
            if hasattr(self, "sb_perim_outer_len") and self.sb_limit_x.value() < self.sb_perim_outer_len.value() + 1.0:
                self.sb_limit_x.setValue(max(9.00, round(self.sb_perim_outer_len.value() + 2.0, 2)))
                self.sb_limit_y.setValue(max(8.00, round(self.sb_perim_outer_wid.value() + 2.0, 2)))
        else:
            self.sb_inner_len.lbl_title.setText("线圈内长 (Inner_Len)")
            self.sb_inner_wid.lbl_title.setText("线圈内宽 (Inner_Wid)")
            self.sb_inner_wid.setEnabled(True)
            self.sb_limit_x.lbl_title.setText("X 向结构空间上限 (Max X)")
            self.sb_limit_y.lbl_title.setText("Y 向结构空间上限 (Max Y)")
            self.sb_limit_y.setEnabled(True)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText("Z 向装配限高上限 (Max Z)")
            # 跑道型防呆：内长必须 >= 内宽
            if self.sb_inner_wid.value() > self.sb_inner_len.value():
                self.sb_inner_len.setValue(self.sb_inner_wid.value())
        self.run_simulation()

    def _on_copper_grade_changed(self, idx: int):
        """响应铜材电导等级切换"""
        rho_val = self.combo_copper_grade.currentData()
        if rho_val is not None and rho_val > 0:
            self.sb_copper_rho.setValue(rho_val)
        self.run_simulation()

    def _on_copper_rho_slider_changed(self):
        """响应用户手动滑动/输入实测电阻率"""
        curr_val = round(self.sb_copper_rho.value(), 6)
        self.combo_copper_grade.blockSignals(True)
        if abs(curr_val - 0.016959) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(0)
        elif abs(curr_val - 0.016920) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(1)
        elif abs(curr_val - 0.017100) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(2)
        elif abs(curr_val - 0.017241) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(3)
        else:
            self.combo_copper_grade.setCurrentIndex(4) # 自定义
        self.combo_copper_grade.blockSignals(False)
        self.run_simulation()

    def _on_thermal_env_changed(self, idx: int):
        """响应散热对流工况快捷预设切换"""
        h_val = self.combo_thermal_env.currentData()
        if h_val is not None and h_val > 0:
            self.sb_convection_h.setValue(h_val)
        self.run_simulation()

    def _on_convection_h_slider_changed(self):
        """响应用户手动微调散热对流系数"""
        curr_h = round(self.sb_convection_h.value(), 1)
        self.combo_thermal_env.blockSignals(True)
        if abs(curr_h - 25.0) < 0.1:
            self.combo_thermal_env.setCurrentIndex(0)
        elif abs(curr_h - 40.0) < 0.1:
            self.combo_thermal_env.setCurrentIndex(1)
        elif abs(curr_h - 15.0) < 0.1:
            self.combo_thermal_env.setCurrentIndex(2)
        elif abs(curr_h - 50.0) < 0.1:
            self.combo_thermal_env.setCurrentIndex(3)
        else:
            self.combo_thermal_env.setCurrentIndex(4) # 自定义
        self.combo_thermal_env.blockSignals(False)
        self.run_simulation()

    def _on_temp_class_changed(self, idx: int):
        """响应耐温等级快捷切换 (120 / 155 / 180 / 自定义)"""
        val = self.combo_temp_class.currentData()
        if val is not None and val > 0:
            self.sb_limit_t.blockSignals(True)
            self.sb_limit_t.setValue(val)
            self.sb_limit_t.blockSignals(False)
        self.run_simulation()

    def _on_limit_t_slider_changed(self, curr_val: float = None):
        """响应耐温上限滑块拖拽并反向同步下拉框"""
        if curr_val is None:
            curr_val = self.sb_limit_t.value()
        curr_val = round(curr_val, 1)
        self.combo_temp_class.blockSignals(True)
        if abs(curr_val - 120.0) < 0.1:
            self.combo_temp_class.setCurrentIndex(0)
        elif abs(curr_val - 155.0) < 0.1:
            self.combo_temp_class.setCurrentIndex(1)
        elif abs(curr_val - 180.0) < 0.1:
            self.combo_temp_class.setCurrentIndex(2)
        else:
            self.combo_temp_class.setCurrentIndex(3)
        self.combo_temp_class.blockSignals(False)
        self.run_simulation()

    def _collect_inputs(self) -> CoilInputs:
        """从控件抽取参数模型 (含用户自定义 DFM 上下限与铜材实测电阻率)"""
        c_type = self.combo_coil_type.currentData() if hasattr(self, "combo_coil_type") else CoilType.RACETRACK
        in_len = self.sb_inner_len.value()
        in_wid = in_len if c_type == CoilType.CIRCULAR else self.sb_inner_wid.value()

        return CoilInputs(
            coil_type=c_type,
            inner_len=in_len,
            inner_wid=in_wid,
            radial_layers=self.sb_radial_layers.value(),
            axial_turns=self.sb_axial_turns.value(),
            winding_mode=self.combo_mode.currentData(),
            oct_id1=self.sb_oct_id1.value() if hasattr(self, "sb_oct_id1") else 7.10,
            oct_id2=self.sb_oct_id2.value() if hasattr(self, "sb_oct_id2") else 7.05,
            oct_l1=self.sb_oct_l1.value() if hasattr(self, "sb_oct_l1") else 2.62,
            oct_l2=self.sb_oct_l2.value() if hasattr(self, "sb_oct_l2") else 2.74,
            oct_r1=self.sb_oct_r1.value() if hasattr(self, "sb_oct_r1") else 0.30,
            perimeter_in=self.sb_perim_in.value() if hasattr(self, "sb_perim_in") else 20.0,
            perimeter_mean=0.0,
            arbitrary_outer_len=self.sb_perim_outer_len.value() if hasattr(self, "sb_perim_outer_len") else 7.0,
            arbitrary_outer_wid=self.sb_perim_outer_wid.value() if hasattr(self, "sb_perim_outer_wid") else 5.0,
            bare_dia=self.sb_bare_dia.value(),
            max_od=self.sb_max_od.value(),
            tension_factor=self.sb_tension.value(),
            copper_resistivity=self.sb_copper_rho.value() if hasattr(self, "sb_copper_rho") else 0.016959,
            mold_clamping_enabled=(c_type == CoilType.RACETRACK and self.chk_mold_clamping.isChecked()) if hasattr(self, "chk_mold_clamping") else False,
            mold_clamping_height=self.sb_mold_height.value() if hasattr(self, "sb_mold_height") else 0.55,
            has_crossover_wire=(c_type == CoilType.RACETRACK and self.chk_crossover.isChecked()) if hasattr(self, "chk_crossover") else False,
            ambient_temp=self.sb_ambient_temp.value(),
            drive_current_ma=self.sb_drive_current.value(),
            convection_h=self.sb_convection_h.value(),
            dfm_enabled=self.chk_dfm_enabled.isChecked() if hasattr(self, "chk_dfm_enabled") else False,
            max_x_len_limit=self.sb_limit_x.value(),
            max_y_wid_limit=self.sb_limit_y.value() if c_type in (CoilType.RACETRACK, CoilType.OCTAGONAL, CoilType.ARBITRARY_PERIMETER) else self.sb_limit_x.value(),
            max_z_h_limit=self.sb_limit_z.value(),
            max_v_term_limit=self.sb_limit_v.value(),
            max_temp_limit=self.sb_limit_t.value()
        )

    def run_simulation(self):
        """执行物理引擎计算并刷新全界面 (60FPS 极速响应，内置工业级异常自愈护盾)"""
        try:
            self.inputs = self._collect_inputs()
            self.outputs = CoilPhysicsEngine.calculate(self.inputs)

            # 1. 刷新 16 宫格 KPI 卡片
            is_circular = (self.inputs.coil_type == CoilType.CIRCULAR)
            is_oct = (self.inputs.coil_type == CoilType.OCTAGONAL)
            is_perim = (self.inputs.coil_type == CoilType.ARBITRARY_PERIMETER)

            if is_circular:
                self.card_ol.lbl_title.setText("线圈外径 (OD)")
                self.card_ol.setValue(f"{self.outputs.outer_len:.3f}")
                self.card_ow.lbl_title.setText("平均中径 (MD)")
                self.card_ow.setValue(f"{self.outputs.mean_dia_mm:.3f}")
            elif is_oct:
                self.card_ol.lbl_title.setText("对边外宽 OD1")
                self.card_ol.setValue(f"{self.outputs.oct_od1:.3f}")
                self.card_ow.lbl_title.setText("对角外宽 OD2")
                self.card_ow.setValue(f"{self.outputs.oct_od2:.3f}")
            elif is_perim:
                self.card_ol.lbl_title.setText("参考外长 (L)")
                self.card_ol.setValue(f"{self.outputs.outer_len:.3f}")
                self.card_ow.lbl_title.setText("展开内周长")
                self.card_ow.setValue(f"{self.outputs.c_inner_mm:.2f}")
            else:
                self.card_ol.lbl_title.setText("外廓长度 (L)")
                self.card_ol.setValue(f"{self.outputs.outer_len:.3f}")
                self.card_ow.lbl_title.setText("外廓宽度 (W)")
                self.card_ow.setValue(f"{self.outputs.outer_wid:.3f}")

            if self.outputs.is_mold_clamped:
                self.card_thk.lbl_title.setText("模压厚度 (H)")
                self.card_thk.setValue(f"{self.outputs.thickness_h:.3f}")
            else:
                self.card_thk.lbl_title.setText("线圈厚度 (H)")
                self.card_thk.setValue(f"{self.outputs.thickness_h:.3f}")

            # 动态更新模具压实厚度下限极限与安全提示
            if hasattr(self, "sb_mold_height") and self.outputs.h_solid_limit > 0:
                h_min = round(self.outputs.h_solid_limit, 2)
                h_safe = round(self.outputs.h_safe_min_limit, 2)
                if self.sb_mold_height.min_val != h_min:
                    self.sb_mold_height.min_val = h_min
                    self.sb_mold_height.slider.setMinimum(int(round(h_min * self.sb_mold_height.scale)))
                    self.sb_mold_height.spin.setMinimum(h_min)
                self.sb_mold_height.lbl_title.setText(f"模具压实厚度 (≥{h_safe:.2f}mm)")

            self.card_n.setValue(str(self.outputs.total_turns))

            # 20℃冷态电阻 (米阻展示于 Tooltip，标题极简纯粹)
            self.card_r20.lbl_title.setText("20℃直流电阻")
            self.card_r20.setToolTip(f"【20℃直流电阻】\n当前阻值: {self.outputs.r20:.3f} Ω\n标称米阻: {self.outputs.rho_per_meter:.3f} Ω/m\n线圈线长: {self.outputs.total_wire_len_m:.3f} m")
            self.card_r20.setValue(f"{self.outputs.r20:.3f}")
            self.card_r_init.setValue(f"{self.outputs.r_init:.3f}")
            self.card_dcr_hot.setValue(f"{self.outputs.dcr_hot:.3f}")

            # Wheeler 电感友好展示 (微亨与毫亨自适应)
            if self.outputs.inductance_uh >= 1000.0:
                self.card_inductance.lbl_unit.setText("mH")
                self.card_inductance.setValue(f"{self.outputs.inductance_mh:.3f}")
            else:
                self.card_inductance.lbl_unit.setText("μH")
                self.card_inductance.setValue(f"{self.outputs.inductance_uh:.1f}")

            self.card_v_term.setValue(f"{self.outputs.v_term:.3f}")
            self.card_power.setValue(f"{self.outputs.joule_power_mw:.1f}")
            self.card_ampere_turns.setValue(f"{self.outputs.ampere_turns:.2f}")
            self.card_t_final.setValue(f"{self.outputs.t_final:.1f}")

            # 重量与槽满率
            self.card_weight.setValue(f"{self.outputs.weight_g:.3f}")
            self.card_wire_fill.setValue(f"{self.outputs.wire_fill_factor:.2f}")
            self.card_cu_fill.setValue(f"{self.outputs.copper_fill_factor:.2f}")
            self.card_mlt.setValue(f"{self.outputs.mlt:.3f}")

            # 2. 刷新矢量画布
            self.canvas_widget.updateCoil(self.inputs, self.outputs)

            # 3. 刷新 DFM 红绿指示灯 (实时使用用户设定的卡控限值)
            self.dfm_strip.updateDFM(self.outputs.dfm, self.outputs.r20, self.outputs.total_turns)

            # 4. 实时刷新方案比对抽屉中的 Live 列
            if hasattr(self, "comparison_drawer"):
                self.comparison_drawer.update_live(self.inputs, self.outputs)

            # 5. 锁定左栏宽度，杜绝因数值变化/文本变长引起的分隔器宽度自动抖动
            if hasattr(self, "splitter") and hasattr(self, "_splitter_left_width"):
                current_sizes = self.splitter.sizes()
                if current_sizes and current_sizes[0] != self._splitter_left_width:
                    total_w = current_sizes[0] + current_sizes[1]
                    self.splitter.setSizes([self._splitter_left_width, max(100, total_w - self._splitter_left_width)])
        except Exception as e:
            logger.error(f"仿真计算异常拦截 (系统已自愈保护): {e}", exc_info=True)
            self.status_bar.showMessage(f"⚠️ 参数计算异常已拦截: {e}", 3000)

    def _restore_scheme_inputs(self, snapshot: SchemeSnapshot):
        """一键从方案快照中恢复全套输入参数并重新运行仿真"""
        inp = snapshot.inputs
        self._is_syncing_params = True
        try:
            # 1. 恢复线圈拓扑
            self.combo_coil_type.setCurrentIndex(int(inp.coil_type))

            # 2. 恢复几何参数
            if inp.coil_type in (CoilType.RACETRACK, CoilType.CIRCULAR):
                self.sb_inner_len.setValue(inp.inner_len)
                self.sb_inner_wid.setValue(inp.inner_wid)
            elif inp.coil_type == CoilType.OCTAGONAL:
                if hasattr(self, "sb_oct_id1"):
                    self.sb_oct_id1.setValue(inp.oct_id1)
                if hasattr(self, "sb_oct_r1"):
                    self.sb_oct_r1.setValue(inp.oct_r1)
                if hasattr(self, "sb_oct_id2"):
                    self.sb_oct_id2.setValue(inp.oct_id2)
                if hasattr(self, "sb_oct_l1"):
                    self.sb_oct_l1.setValue(inp.oct_l1)
                if hasattr(self, "sb_oct_l2"):
                    self.sb_oct_l2.setValue(inp.oct_l2)
            elif inp.coil_type == CoilType.ARBITRARY_PERIMETER:
                if hasattr(self, "sb_perim_in"):
                    self.sb_perim_in.setValue(inp.perimeter_in)
                if hasattr(self, "sb_perim_outer_len"):
                    self.sb_perim_outer_len.setValue(inp.arbitrary_outer_len)
                if hasattr(self, "sb_perim_outer_wid"):
                    self.sb_perim_outer_wid.setValue(inp.arbitrary_outer_wid)

            # 3. 恢复绕线工艺与漆包线参数
            self.sb_radial_layers.setValue(inp.radial_layers)
            self.sb_axial_turns.setValue(inp.axial_turns)
            self.sb_bare_dia.setValue(inp.bare_dia)
            self.sb_max_od.setValue(inp.max_od)
            self.sb_tension.setValue(inp.tension_factor)
            mode_idx = 0 if inp.winding_mode == WindingMode.VARIABLE else 1
            self.combo_mode.setCurrentIndex(mode_idx)

            # 4. 恢复电气热学参数
            if hasattr(self, "sb_copper_rho"):
                self.sb_copper_rho.setValue(inp.copper_resistivity)
            self.sb_ambient_temp.setValue(inp.ambient_temp)
            self.sb_drive_current.setValue(inp.drive_current_ma)
            self.sb_convection_h.setValue(inp.convection_h)

            # 5. 模具压实与换层 (仅跑道型)
            if hasattr(self, "chk_mold_clamping"):
                self.chk_mold_clamping.setChecked(inp.mold_clamping_enabled)
            if hasattr(self, "sb_mold_height"):
                self.sb_mold_height.setValue(inp.mold_clamping_height)
            if hasattr(self, "chk_crossover"):
                self.chk_crossover.setChecked(getattr(inp, "has_crossover_wire", False))

        finally:
            self._is_syncing_params = False

        c_type = self.combo_coil_type.currentData() if hasattr(self, "combo_coil_type") else CoilType.RACETRACK
        if c_type in (CoilType.RACETRACK, CoilType.CIRCULAR):
            self._on_inner_len_changed(self.sb_inner_len.value())
        elif c_type == CoilType.OCTAGONAL:
            self._on_oct_params_changed()
        self._on_bare_dia_changed(self.sb_bare_dia.value())
        self.run_simulation()
        self.status_bar.showMessage(f"✓ 已成功还原方案 [{snapshot.name}] 的全套输入参数！", 3500)

    def _load_preset(self, name: str):
        """加载经典工业预设 (含匹配的模具空间限值)"""
        if getattr(self, "_is_syncing_params", False):
            return
        self._is_syncing_params = True
        try:
            if hasattr(self, "chk_mold_clamping"):
                self.chk_mold_clamping.setChecked(False)
                self.chk_crossover.setChecked(False)
            if hasattr(self, "chk_dfm_enabled"):
                self.chk_dfm_enabled.setChecked(False)

            if "1." in name or "VCM马达" in name or "0.045" in name:
                # 1. 手机VCM马达 (跑道型 / 图1基准)
                self.combo_coil_type.setCurrentIndex(0)  # 跑道型
                self.sb_inner_len.setValue(5.30)
                self.sb_inner_wid.setValue(0.92)
                self.sb_radial_layers.setValue(12)
                self.sb_axial_turns.setValue(12)
                self.sb_bare_dia.setValue(0.045)
                self.sb_max_od.setValue(0.055)
                self.sb_tension.setValue(0.99)
                if hasattr(self, "sb_copper_rho"):
                    self.sb_copper_rho.setValue(0.016959) # 高导电率 OFHC
                    self.combo_copper_grade.setCurrentIndex(0)
                self.sb_ambient_temp.setValue(25.0)
                self.sb_drive_current.setValue(60.0)
                self.sb_convection_h.setValue(40.0)
                if hasattr(self, "combo_thermal_env"):
                    self.combo_thermal_env.setCurrentIndex(1) # 贴FPC+钢片
                self.combo_mode.setCurrentIndex(0)  # 异数模式 (138匝)
                self.sb_limit_x.setValue(7.20)
                self.sb_limit_y.setValue(3.00)
                self.sb_limit_z.setValue(0.85)
                self.sb_limit_v.setValue(2.50)
                if hasattr(self, "combo_temp_class"):
                    self.combo_temp_class.setCurrentIndex(1) # 155等级
                self.sb_limit_t.setValue(155.0)

            elif "2." in name or "LRA圆线圈" in name or "0825" in name or "VLRA" in name:
                # 2. 手机LRA圆线圈 (硬币式0825 Z-LRA / 图2基准)
                self.combo_coil_type.setCurrentIndex(1)  # 圆形线圈
                self.sb_inner_len.setValue(2.12)
                self.sb_radial_layers.setValue(6)
                self.sb_axial_turns.setValue(23)
                self.sb_bare_dia.setValue(0.033)
                self.sb_max_od.setValue(0.040)
                self.sb_tension.setValue(0.990)
                if hasattr(self, "sb_copper_rho"):
                    self.sb_copper_rho.setValue(0.016959)
                    self.combo_copper_grade.setCurrentIndex(0)
                self.sb_ambient_temp.setValue(20.0)
                self.sb_drive_current.setValue(40.0)
                self.sb_convection_h.setValue(35.0)
                if hasattr(self, "combo_thermal_env"):
                    self.combo_thermal_env.setCurrentIndex(0)
                self.combo_mode.setCurrentIndex(0)  # 异数 HCP (135匝)
                self.sb_limit_x.setValue(10.00)
                self.sb_limit_y.setValue(10.00)
                self.sb_limit_z.setValue(3.50)
                self.sb_limit_v.setValue(3.50)
                if hasattr(self, "combo_temp_class"):
                    self.combo_temp_class.setCurrentIndex(1) # 155等级
                self.sb_limit_t.setValue(155.0)

            elif "3." in name or "LRA跑道线圈" in name or "LRA马达跑道线圈" in name or "147匝" in name or "8Ω" in name:
                # 3. 手机LRA马达跑道线圈 (图3工程图纸规范: 19层 8匝 异数平齐模式 自然厚度0.541mm)
                self.combo_coil_type.setCurrentIndex(0)  # 跑道型
                self.sb_inner_len.setValue(2.30)
                self.sb_inner_wid.setValue(0.60)
                self.sb_radial_layers.setValue(19.0)
                self.sb_axial_turns.setValue(8)
                self.sb_bare_dia.setValue(0.060)
                self.sb_max_od.setValue(0.068)
                self.sb_tension.setValue(0.985)
                if hasattr(self, "sb_copper_rho"):
                    self.sb_copper_rho.setValue(0.016920)
                    self.combo_copper_grade.setCurrentIndex(1) # 厂家出厂典型实测
                self.sb_ambient_temp.setValue(20.0)
                self.sb_drive_current.setValue(50.0)
                self.sb_convection_h.setValue(35.0)
                if hasattr(self, "combo_thermal_env"):
                    self.combo_thermal_env.setCurrentIndex(0)
                self.combo_mode.setCurrentIndex(0)  # 异数交错模式 (HCP 6-5-6-5: 奇数层缩进1匝, 边界端面平齐)
                if hasattr(self, "chk_mold_clamping"):
                    self.chk_mold_clamping.setChecked(False)
                if hasattr(self, "chk_crossover"):
                    self.chk_crossover.setChecked(True)
                self.sb_limit_x.setValue(4.60)
                self.sb_limit_y.setValue(3.15)
                self.sb_limit_z.setValue(0.57)
                self.sb_limit_v.setValue(1.50)
                if hasattr(self, "combo_temp_class"):
                    self.combo_temp_class.setCurrentIndex(1) # 155等级
                self.sb_limit_t.setValue(155.0)

            elif "4." in name or "八角形" in name:
                # 4. VCM八角形线圈 (实测对边7.1/对角7.05/厚度0.67/电阻19.5Ω)
                self.combo_coil_type.setCurrentIndex(2)  # 八角形
                if hasattr(self, "sb_oct_id1"):
                    self.sb_oct_id1.setValue(7.10)
                if hasattr(self, "sb_oct_r1"):
                    self.sb_oct_r1.setValue(0.30)
                if hasattr(self, "sb_oct_id2"):
                    self.sb_oct_id2.setValue(7.05)
                if hasattr(self, "sb_oct_l1"):
                    self.sb_oct_l1.setValue(2.62)
                if hasattr(self, "sb_oct_l2"):
                    self.sb_oct_l2.setValue(2.74)
                self.sb_radial_layers.setValue(6.0)
                self.sb_axial_turns.setValue(13)
                self.sb_bare_dia.setValue(0.045)
                self.sb_max_od.setValue(0.053)
                self.sb_tension.setValue(0.99)
                if hasattr(self, "sb_copper_rho"):
                    self.sb_copper_rho.setValue(0.016959)
                    self.combo_copper_grade.setCurrentIndex(0)
                self.sb_ambient_temp.setValue(25.0)
                self.sb_drive_current.setValue(80.0)
                self.sb_convection_h.setValue(35.0)
                self.combo_mode.setCurrentIndex(0)  # 异数 HCP
                self.sb_limit_x.setValue(8.50)
                self.sb_limit_y.setValue(8.50)
                self.sb_limit_z.setValue(0.80)
                self.sb_limit_v.setValue(2.50)
                if hasattr(self, "combo_temp_class"):
                    self.combo_temp_class.setCurrentIndex(1)
                self.sb_limit_t.setValue(155.0)

            elif "5." in name or "异形" in name:
                # 5. CAD任意异形 (中线周长推算)
                self.combo_coil_type.setCurrentIndex(3)  # 通用异形
                if hasattr(self, "sb_perim_in"):
                    self.sb_perim_in.setValue(24.50)
                    self.sb_perim_outer_len.setValue(8.0)
                    self.sb_perim_outer_wid.setValue(6.0)
                self.sb_radial_layers.setValue(10)
                self.sb_axial_turns.setValue(12)
                self.sb_bare_dia.setValue(0.060)
                self.sb_max_od.setValue(0.070)
                self.sb_tension.setValue(0.99)
                self.combo_mode.setCurrentIndex(0)
                self.sb_limit_x.setValue(9.50)
                self.sb_limit_y.setValue(7.50)
                self.sb_limit_z.setValue(1.10)
                self.sb_limit_v.setValue(3.50)
                if hasattr(self, "combo_temp_class"):
                    self.combo_temp_class.setCurrentIndex(0) # 120等级
                self.sb_limit_t.setValue(120.0)

        finally:
            self._is_syncing_params = False

        c_type = self.combo_coil_type.currentData() if hasattr(self, "combo_coil_type") else CoilType.RACETRACK
        if c_type in (CoilType.RACETRACK, CoilType.CIRCULAR):
            self._on_inner_len_changed(self.sb_inner_len.value())
        elif c_type == CoilType.OCTAGONAL:
            self._on_oct_params_changed()
        self._on_bare_dia_changed(self.sb_bare_dia.value())
        self.run_simulation()

    def _export_project(self):
        """保存算例配置文件 (.ansv / .json)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        proj_name = self.get_project_name()
        default_filename = f"{proj_name}_线圈工程算例_{timestamp}.ansv"
        path, _ = QFileDialog.getSaveFileName(self, "保存线圈算例", default_filename, "ANSV 算例文件 (*.ansv);;JSON 算例文件 (*.json)")
        if not path:
            return
        data = {
            "version": "1.0.0",
            "project_name": proj_name,
            "inputs": {
                "coil_type": int(self.inputs.coil_type),
                "inner_len": self.inputs.inner_len,
                "inner_wid": self.inputs.inner_wid,
                "radial_layers": self.inputs.radial_layers,
                "axial_turns": self.inputs.axial_turns,
                "winding_mode": int(self.inputs.winding_mode),
                "bare_dia": self.inputs.bare_dia,
                "max_od": self.inputs.max_od,
                "tension_factor": self.inputs.tension_factor,
                "copper_resistivity": getattr(self.inputs, "copper_resistivity", 0.016959),
                "ambient_temp": self.inputs.ambient_temp,
                "drive_current_ma": self.inputs.drive_current_ma,
                "convection_h": self.inputs.convection_h,
                "max_x_len_limit": self.inputs.max_x_len_limit,
                "max_y_wid_limit": self.inputs.max_y_wid_limit,
                "max_z_h_limit": self.inputs.max_z_h_limit,
                "max_v_term_limit": self.inputs.max_v_term_limit,
                "max_temp_limit": self.inputs.max_temp_limit,
                "dfm_enabled": getattr(self.inputs, "dfm_enabled", False),
                "oct_id1": getattr(self.inputs, "oct_id1", 6.80),
                "oct_id2": getattr(self.inputs, "oct_id2", 7.60),
                "oct_l1": getattr(self.inputs, "oct_l1", 3.20),
                "oct_l2": getattr(self.inputs, "oct_l2", 1.80),
                "oct_r1": getattr(self.inputs, "oct_r1", 0.50),
                "perimeter_in": getattr(self.inputs, "perimeter_in", 22.0),
                "perimeter_mean": getattr(self.inputs, "perimeter_mean", 0.0),
                "arbitrary_outer_len": getattr(self.inputs, "arbitrary_outer_len", 8.0),
                "arbitrary_outer_wid": getattr(self.inputs, "arbitrary_outer_wid", 6.0),
            }
        }
        atomic_write_json(Path(path), data)
        self.status_bar.showMessage(f"算例已成功原子持久化保存至: {os.path.basename(path)}", 4000)

    def _import_project(self):
        """导入算例配置文件"""
        path, _ = QFileDialog.getOpenFileName(self, "载入线圈算例", "", "ANSV 算例文件 (*.ansv);;JSON 算例文件 (*.json)")
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            inp = data.get("inputs", {})
            if "project_name" in data and hasattr(self, "txt_project_name"):
                self.txt_project_name.setText(data["project_name"])
            self._is_syncing_params = True
            try:
                c_type = inp.get("coil_type", 0)
                self.combo_coil_type.setCurrentIndex(c_type)
                self.sb_inner_len.setValue(inp.get("inner_len", 4.86))
                self.sb_inner_wid.setValue(inp.get("inner_wid", 1.50))
                self.sb_radial_layers.setValue(inp.get("radial_layers", 14))
                self.sb_axial_turns.setValue(inp.get("axial_turns", 12))
                self.sb_bare_dia.setValue(inp.get("bare_dia", 0.075))
                self.sb_max_od.setValue(inp.get("max_od", 0.085))
                self.sb_tension.setValue(inp.get("tension_factor", 0.99))
                if hasattr(self, "sb_copper_rho"):
                    self.sb_copper_rho.setValue(inp.get("copper_resistivity", 0.016959))
                self.sb_ambient_temp.setValue(inp.get("ambient_temp", 20.0))
                self.sb_drive_current.setValue(inp.get("drive_current_ma", 10.0))
                self.sb_convection_h.setValue(inp.get("convection_h", 25.0))
                
                # DFM 限值恢复
                if hasattr(self, "chk_dfm_enabled"):
                    self.chk_dfm_enabled.setChecked(inp.get("dfm_enabled", False))
                self.sb_limit_x.setValue(inp.get("max_x_len_limit", 7.20))
                self.sb_limit_y.setValue(inp.get("max_y_wid_limit", 3.82))
                self.sb_limit_z.setValue(inp.get("max_z_h_limit", 1.05))
                self.sb_limit_v.setValue(inp.get("max_v_term_limit", 2.80))
                self.sb_limit_t.setValue(inp.get("max_temp_limit", 110.0))

                # 异形线圈参数恢复
                if hasattr(self, "sb_oct_id1"):
                    self.sb_oct_id1.setValue(inp.get("oct_id1", 6.80))
                if hasattr(self, "sb_oct_id2"):
                    self.sb_oct_id2.setValue(inp.get("oct_id2", 7.60))
                if hasattr(self, "sb_oct_l1"):
                    self.sb_oct_l1.setValue(inp.get("oct_l1", 3.20))
                if hasattr(self, "sb_oct_l2"):
                    self.sb_oct_l2.setValue(inp.get("oct_l2", 1.80))
                if hasattr(self, "sb_oct_r1"):
                    self.sb_oct_r1.setValue(inp.get("oct_r1", 0.50))
                if hasattr(self, "sb_perim_in"):
                    self.sb_perim_in.setValue(inp.get("perimeter_in", 22.0))
                if hasattr(self, "sb_arb_outer_len"):
                    self.sb_arb_outer_len.setValue(inp.get("arbitrary_outer_len", 8.0))
                if hasattr(self, "sb_arb_outer_wid"):
                    self.sb_arb_outer_wid.setValue(inp.get("arbitrary_outer_wid", 6.0))

                mode_idx = 0 if inp.get("winding_mode", 1) == 1 else 1
                self.combo_mode.setCurrentIndex(mode_idx)
            finally:
                self._is_syncing_params = False

            # 强制同步工艺与几何防呆下限
            c_type = self.combo_coil_type.currentData() if hasattr(self, "combo_coil_type") else CoilType.RACETRACK
            if c_type in (CoilType.RACETRACK, CoilType.CIRCULAR):
                self._on_inner_len_changed(self.sb_inner_len.value())
            self._on_bare_dia_changed(self.sb_bare_dia.value())
            self.run_simulation()
            self.status_bar.showMessage(f"已成功加载算例: {os.path.basename(path)}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法解析算例文件: {str(e)}")

    def _export_report(self):
        """导出工程评审报表 (支持 Excel .xlsx 或 CSV)"""
        # 1. 弹出项目名称确认输入框，默认带出预设 Coli-Architect
        current_name = self.get_project_name()
        proj_name, ok = QInputDialog.getText(
            self, 
            "导出评审报告 - 确认项目名称", 
            "请输入工程项目名称 (将注入文件名与报表元数据):", 
            QLineEdit.EchoMode.Normal, 
            current_name
        )
        if not ok:
            return
        proj_name = proj_name.strip() if proj_name else "Coli-Architect"
        if not proj_name:
            proj_name = "Coli-Architect"
        if hasattr(self, "txt_project_name"):
            self.txt_project_name.setText(proj_name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{proj_name}_线圈工程评审报告_{timestamp}.xlsx"
        path, sel_filter = QFileDialog.getSaveFileName(
            self, 
            "导出工程评审报告", 
            default_filename, 
            "Excel 工作簿 (*.xlsx);;CSV 文本报表 (*.csv)"
        )
        if not path:
            return
        
        if path.lower().endswith(".xlsx") or "xlsx" in sel_filter.lower():
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            from ..export.report_excel import ExcelReportGenerator
            ExcelReportGenerator.generate(self.inputs, self.outputs, path, project_name=proj_name)
            self.status_bar.showMessage(f"Excel 评审报告已成功导出: {os.path.basename(path)}", 4000)
            QMessageBox.information(self, "导出成功", f"线圈多物理场评审报告已导出至:\n{path}")
        else:
            self._export_csv_file(path, project_name=proj_name)

    def _export_csv_file(self, path: str, project_name: str = "Coli-Architect"):
        c_type = self.inputs.coil_type
        if c_type == CoilType.CIRCULAR:
            c_type_name = "圆形线圈 (Circular)"
            dim_row1 = f"实际外廓外径 (OD),{self.outputs.outer_len:.3f},mm"
            dim_row2 = f"绕组平均中径 (Dm),{self.outputs.mean_dia_mm:.3f},mm"
        elif c_type == CoilType.OCTAGONAL:
            c_type_name = "八角形线圈 (Octagonal VCM)"
            dim_row1 = f"对边外跨距 (OD1),{self.outputs.oct_od1:.3f},mm"
            dim_row2 = f"对角外跨距 (OD2),{self.outputs.oct_od2:.3f},mm"
        elif c_type == CoilType.ARBITRARY_PERIMETER:
            c_type_name = "通用异形线圈 (Arbitrary Perimeter)"
            dim_row1 = f"内周长 (C_in),{self.outputs.c_inner_mm:.3f},mm"
            dim_row2 = f"外周长 (C_out),{self.outputs.c_outer_mm:.3f},mm"
        else:
            c_type_name = "跑道型线圈 (Racetrack)"
            dim_row1 = f"实际外廓长度 (OL),{self.outputs.outer_len:.3f},mm"
            dim_row2 = f"实际外廓宽度 (OW),{self.outputs.outer_wid:.3f},mm"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "Coil-Architect Pro - 工程仿真数据报表",
            f"工程项目名称,{project_name}",
            f"评审导出时间,{now_str}",
            "官方仿真平台,ansv.net (ANSV 微型执行器与精密传动平台)",
            f"线圈拓扑类型,{c_type_name}",
            f"有效成型总匝数 (N),{self.outputs.total_turns},匝",
            dim_row1,
            dim_row2,
            f"Z向占位高度 (Thickness),{self.outputs.thickness_h:.3f},mm",
            f"铜导体电阻率 (ρ_cu),{self.inputs.copper_resistivity:.6f},Ω·mm²/m",
            f"理论单线标称米阻 (R/m),{self.outputs.rho_per_meter:.4f},Ω/m",
            f"20℃冷态电阻 (R20),{self.outputs.r20:.4f},Ω",
            f"测试初始电阻 (R_init),{self.outputs.r_init:.4f},Ω",
            f"热态平衡电阻 (DCR_hot),{self.outputs.dcr_hot:.4f},Ω",
            f"Wheeler多层空心电感 (L),{self.outputs.inductance_uh:.2f},μH",
            f"电磁激励安匝数 (ΣI),{self.outputs.ampere_turns:.2f},AT",
            f"所需驱动端电压 (V_term),{self.outputs.v_term:.4f},V",
            f"稳态焦耳功耗 (Power),{self.outputs.joule_power_mw:.2f},mW",
            f"稳态极限结温 (T_final),{self.outputs.t_final:.2f},℃",
            f"漆包线占空比 (Wire Fill),{self.outputs.wire_fill_factor:.2f},%",
            f"纯铜空间填充率 (Cu Fill),{self.outputs.copper_fill_factor:.2f},%",
            f"线圈净重 (Weight),{self.outputs.weight_g:.4f},g",
            f"平均单匝展开周长 (MLT),{self.outputs.mlt:.3f},mm",
            f"DFM卡控状态,{ '全部合格' if self.outputs.dfm.all_passed else '存在超标项' }"
        ]
        atomic_write_text(Path(path), "\n".join(lines), encoding="utf-8-sig")
        self.status_bar.showMessage(f"CSV 报表已成功原子持久化导出: {os.path.basename(path)}", 4000)

