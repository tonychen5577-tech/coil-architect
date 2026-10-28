"""
Coil-Architect Pro - Main Window
工业级高对比度双核物理仿真工作站主窗口
"""

import os
import json
import math
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QTimer
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QFrame, QSplitter,
    QScrollArea, QFileDialog, QMessageBox, QStatusBar, QCheckBox,
    QLineEdit, QInputDialog, QApplication, QScrollBar, QSizePolicy
)

from ..core.models import CoilInputs, CoilOutputs, WindingMode, CoilType, WireShape, WireCatalogType, EnamelGrade, WindingDirection
from ..core.wire_catalog import WireCatalogItem, get_huaye_copper_wires, get_huaye_ccaw_wires, find_wire_by_diameter
from ..core.physics_engine import CoilPhysicsEngine
from .styles import LIGHT_INDUSTRIAL_QSS
from .widgets.slider_spin_box import FloatSliderBox, IntSliderBox
from .widgets.metric_card import MetricCard
from .widgets.dfm_indicator import DFMStatusStrip
from .widgets.coil_canvas import CoilDualCanvasWidget
from .widgets.comparison_drawer import ComparisonDrawer, SchemeSnapshot
from .utils import atomic_write_json, atomic_write_text, sanitize_filename_ascii, parse_coil_type, parse_winding_mode
from .about_dialog import AboutDialog
from src.gui.icon_helper import get_ansv_logo_pixmap
from src.core.ota_updater import OtaUpdater, OtaChecker
from src.version import APP_NAME, APP_TITLE, APP_VERSION, APP_BUILD, APP_AUTHOR, OFFICIAL_URL, COPYRIGHT_TEXT, CORE_ENGINE_AUTHOR
from src.core.i18n import i18n, t, LANG_ZH, LANG_EN
from src.utils.logger import get_logger
from pathlib import Path

logger = get_logger("MainWindow")


class ParamInteractionFilter(QObject):
    """
    未激活评估模式操作守卫过滤器：
    - 允许操作员自由滚动阅读所有参数卡片、查看 2D 轮廓与微观排线剖面、浏览指标卡；
    - 允许操作员点击【关于系统】与【点击激活】；
    - 拦截在未激活状态下对参数控件（滑块、输入框、复选框、下拉框）的点击与修改，以及算例导出等业务操作；
    - 在用户尝试操作时，友好弹出商业授权激活窗口，激活成功即刻解锁，取消则保留原样不破坏界面。
    """
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def eventFilter(self, watched, event):
        mw = self.main_window
        # 1. 已授权或未初始化完成时，完全放行
        if getattr(mw, "is_authorized", False) or not getattr(mw, "_initialization_done", False):
            return False

        # 2. 正在弹激活窗口时，防重入放行
        if getattr(mw, "_is_prompting_activation", False):
            return False

        # 3. 如果点击对象不在 main_window 内部（例如激活弹窗或关于窗口自身），放行
        try:
            w_win = watched.window()
            if w_win is not mw:
                return False
        except Exception:
            return False

        # 4. 允许滚轮和滚动条拖动浏览
        if isinstance(watched, QScrollBar):
            return False

        # 允许点击顶部关于按钮和授权按钮
        if hasattr(mw, "btn_license") and (watched is mw.btn_license or mw.btn_license.isAncestorOf(watched)):
            return False
        if hasattr(mw, "btn_about") and (watched is mw.btn_about or mw.btn_about.isAncestorOf(watched)):
            return False

        # 允许抽屉的折叠/展开按钮、弹出大窗按钮和抽屉内部的滚动条
        if hasattr(mw, "drawer"):
            if hasattr(mw.drawer, "btn_toggle") and (watched is mw.drawer.btn_toggle or mw.drawer.btn_toggle.isAncestorOf(watched)):
                return False
            if hasattr(mw.drawer, "btn_fold") and (watched is mw.drawer.btn_fold or mw.drawer.btn_fold.isAncestorOf(watched)):
                return False
            if hasattr(mw.drawer, "btn_popout") and (watched is mw.drawer.btn_popout or mw.drawer.btn_popout.isAncestorOf(watched)):
                return False

        # 允许右侧 2D 画布区和 KPI 卡片交互浏览 (缩放、平移画布)
        if hasattr(mw, "scroll_right") and (watched is mw.scroll_right or mw.scroll_right.isAncestorOf(watched)):
            return False

        # 5. 判定是否为受控操作区域：
        is_left_param = hasattr(mw, "scroll_left") and (watched is mw.scroll_left or mw.scroll_left.isAncestorOf(watched))
        is_top_input = (
            (hasattr(mw, "combo_presets") and (watched is mw.combo_presets or mw.combo_presets.isAncestorOf(watched))) or
            (hasattr(mw, "txt_project_name") and (watched is mw.txt_project_name or mw.txt_project_name.isAncestorOf(watched))) or
            (hasattr(mw, "btn_open") and (watched is mw.btn_open or mw.btn_open.isAncestorOf(watched))) or
            (hasattr(mw, "btn_save") and (watched is mw.btn_save or mw.btn_save.isAncestorOf(watched))) or
            (hasattr(mw, "btn_export") and (watched is mw.btn_export or mw.btn_export.isAncestorOf(watched)))
        )
        is_drawer_op = hasattr(mw, "drawer") and (watched is mw.drawer or mw.drawer.isAncestorOf(watched))

        if is_left_param or is_top_input or is_drawer_op:
            evt_type = event.type()
            # 拦截鼠标点击尝试操作
            if evt_type == QEvent.Type.MouseButtonPress:
                QTimer.singleShot(0, lambda: mw.check_authorization_or_prompt("调整参数与工程计算"))
                return True

            # 拦截键盘输入尝试改动
            if evt_type == QEvent.Type.KeyPress:
                key = event.key()
                # 放行纯导航键（Tab, 方向键等用于焦点移动）
                if key in (
                    Qt.Key.Key_Tab, Qt.Key.Key_Backtab,
                    Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right,
                    Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt
                ):
                    return False
                QTimer.singleShot(0, lambda: mw.check_authorization_or_prompt("输入参数"))
                return True

        return False


class MainWindow(QMainWindow):
    """Coil-Architect Pro 主工作站"""

    signal_cloud_status = pyqtSignal(bool, str, str)  # (is_online, message, base_url)
    signal_remote_command = pyqtSignal(str, str)      # (command, payload)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} {APP_VERSION}")
        self.resize(1380, 860)
        self.setMinimumSize(1200, 700)

        self.inputs = CoilInputs()
        self.outputs = CoilOutputs()
        self._is_syncing_params = False

        self.is_authorized = False
        self.lic_data = {}
        self._initialization_done = False
        self._is_prompting_activation = False
        self._current_preset_name = ""

        # 连接云端协同信号
        self.signal_cloud_status.connect(self._on_cloud_status_received)
        self.signal_remote_command.connect(self._on_remote_command_received)

        # 加载 Clean White 工业样式
        self.setStyleSheet(LIGHT_INDUSTRIAL_QSS)

        self._init_ui()
        self._load_preset(self.combo_presets.itemText(0))
        self.run_simulation()

        # 标记系统启动初始化完成（此后所有用户主动操作均受授权拦截守卫保护）
        self._initialization_done = True
        self._current_preset_name = self.combo_presets.itemText(0)

        # 全局安装参数操作拦截过滤器 (未激活状态下允许观摩，操作时弹出激活)
        self._param_interaction_filter = ParamInteractionFilter(self)
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self._param_interaction_filter)

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

        # 全局快捷键 Ctrl+D 极速呼出数据库网络通信与诊断中心 (对标 Gear 规范)
        from PyQt6.QtGui import QKeySequence, QShortcut
        self.shortcut_db = QShortcut(QKeySequence("Ctrl+D"), self)
        self.shortcut_db.activated.connect(self._open_cloud_config_dialog)

        # 软件本体静默 OTA 自动检查与升级服务 (对标 Gear 规范)
        self.ota_updater = OtaUpdater.get_instance()
        self.ota_updater.update_available.connect(self._on_ota_available)
        self.ota_updater.update_download_progress.connect(self._on_ota_download_progress)
        self.ota_updater.update_download_ready.connect(self._on_ota_download_ready)
        self.ota_updater.update_download_failed.connect(self._on_ota_download_failed)
        self.ota_checker = None

        # 检查是否刚由 OTA 自动完成版本升级 (微信式体验：第二次打开时友好展示升级就绪致意)
        upgraded_msg = self.ota_updater.check_and_clear_updated_flag()
        if upgraded_msg:
            QTimer.singleShot(1000, lambda: self.status_bar.showMessage(upgraded_msg, 10000))

        # 启动后台静默 OTA 自动巡检 (5秒后启动，避开主界面初次加载资源争用)
        QTimer.singleShot(5000, self._start_silent_ota_checker)

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

        # 4. 全局快捷键: F1 快速打开 HTML 用户说明书
        from PyQt6.QtGui import QKeySequence, QShortcut
        self.sc_manual = QShortcut(QKeySequence("F1"), self)
        self.sc_manual.activated.connect(self._open_user_manual)

        # 5. 接入全局国际化响应式中英双语调度
        i18n.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _on_language_selector_changed(self, index: int):
        """语言下拉框切换响应"""
        new_lang = self.combo_lang.currentData()
        if new_lang and new_lang != i18n.current_language:
            i18n.set_language(new_lang)

    def _update_combo_items(self, combo: QComboBox, items: list):
        """无缝刷新 QComboBox 选项文本并保持当前选中项不变，防信号级联"""
        curr_data = combo.currentData()
        curr_idx = combo.currentIndex()
        combo.blockSignals(True)
        combo.clear()
        for text, data in items:
            combo.addItem(text, data)
        for i in range(combo.count()):
            if combo.itemData(i) == curr_data:
                combo.setCurrentIndex(i)
                break
        else:
            if 0 <= curr_idx < combo.count():
                combo.setCurrentIndex(curr_idx)
        combo.blockSignals(False)

    def retranslate_ui(self):
        """
        根据全局 i18n 当前语言设置，无缝重载主界面所有文本、标签、下拉选项与子组件
        """
        # 1. 主窗口标题
        self.setWindowTitle(f"{t('app_window_title', 'ANSV Coil-Architect Pro 2027 | 微型线圈设计与电热仿真工作站')} (Build {APP_BUILD})")

        # 2. 顶部工具栏
        if hasattr(self, "lbl_sub"):
            self.lbl_sub.setText(t("platform_full_name", "微型执行器与精密传动仿真验证平台"))
        if hasattr(self, "lbl_proj"):
            self.lbl_proj.setText(t("toolbar_project", "🏷️ 项目:"))
        if hasattr(self, "txt_project_name"):
            self.txt_project_name.setPlaceholderText(t("txt_project_placeholder", "项目代号"))
            self.txt_project_name.setToolTip(t("txt_project_tooltip", "当前工程项目代号/名称（导出 Excel/CSV 报表与方案比对时将自动注入文件名与表格抬头）"))
        if hasattr(self, "lbl_preset"):
            self.lbl_preset.setText(t("toolbar_preset", "📐 预设:"))
        if hasattr(self, "combo_presets"):
            preset_items = [
                (t("preset_1", "1. 手机VCM马达"), "1. 手机VCM马达"),
                (t("preset_2", "2. 手机LRA圆线圈"), "2. 手机LRA圆线圈"),
                (t("preset_3", "3. 手机LRA跑道线圈"), "3. 手机LRA跑道线圈"),
                (t("preset_4", "4. VCM八角形线圈"), "4. VCM八角形线圈"),
                (t("preset_5", "5. CAD异形线圈"), "5. CAD异形线圈"),
            ]
            self._update_combo_items(self.combo_presets, preset_items)
        if hasattr(self, "btn_open"):
            self.btn_open.setText(t("btn_load_project", "📂 导入文件"))
        if hasattr(self, "btn_save"):
            self.btn_save.setText(t("btn_save_project", "💾 导出文件"))
        if hasattr(self, "btn_export"):
            self.btn_export.setText(t("btn_export_report", "📊 导出仿真报告"))
            self.btn_export.setFixedWidth(108 if i18n.is_english() else 116)
        if hasattr(self, "btn_about"):
            self.btn_about.setText(t("btn_about_system", "ℹ️ 关于系统"))
        self._refresh_license_status()

        # 保持语言下拉框选中项同步
        if hasattr(self, "combo_lang"):
            target_idx = 1 if i18n.current_language == LANG_EN else 0
            if self.combo_lang.currentIndex() != target_idx:
                self.combo_lang.blockSignals(True)
                self.combo_lang.setCurrentIndex(target_idx)
                self.combo_lang.blockSignals(False)

        # 3. 左侧参数面板 - 卡片1: 几何与排线
        if hasattr(self, "lbl_geo"):
            self.lbl_geo.setText(t("sec_geom_params", "▶ 线圈几何与排线参数"))
        if hasattr(self, "lbl_type"):
            self.lbl_type.setText(t("lbl_topology_type", "线圈拓扑类型:"))
        if hasattr(self, "combo_coil_type"):
            types_list = [
                (t("topo_racetrack", "跑道型线圈 (Racetrack)"), CoilType.RACETRACK),
                (t("topo_circular", "圆形线圈 (Circular)"), CoilType.CIRCULAR),
                (t("topo_octagonal", "八角形线圈 (Octagonal)"), CoilType.OCTAGONAL),
                (t("topo_arbitrary", "CAD异形线圈"), CoilType.ARBITRARY_PERIMETER),
            ]
            self._update_combo_items(self.combo_coil_type, types_list)
        if hasattr(self, "sb_inner_len"):
            self.sb_inner_len.setTitle(t("lbl_inner_length", "线圈内长 (IL)"))
        if hasattr(self, "sb_inner_wid"):
            self.sb_inner_wid.setTitle(t("lbl_inner_width", "线圈内宽 (IW)"))

        if hasattr(self, "lbl_oct_hint"):
            self.lbl_oct_hint.setText(t("lbl_oct_hint", "📐 图4规范: 4平直边 + 4斜边 + 8圆角 (配合四角三角磁钢)"))
        if hasattr(self, "sb_oct_id1"):
            self.sb_oct_id1.setTitle(t("lbl_oct_id1", "对边内径 ID1"))
        if hasattr(self, "sb_oct_id2"):
            self.sb_oct_id2.setTitle(t("lbl_oct_id2", "对角内径 ID2"))
        if hasattr(self, "sb_oct_r1"):
            self.sb_oct_r1.setTitle(t("lbl_oct_r1", "拐角内圆角 R1"))
        if hasattr(self, "lbl_oct_derived"):
            l1_val = getattr(self, "_oct_l1", 2.62)
            l2_val = getattr(self, "_oct_l2", 2.74)
            self.lbl_oct_derived.setText(t("lbl_oct_derived", "📐 几何推导尺寸: 平直长 L1 = {l1:.2f} mm  |  斜边长 L2 = {l2:.2f} mm", l1=l1_val, l2=l2_val))

        if hasattr(self, "lbl_perim_hint"):
            self.lbl_perim_hint.setText(t("lbl_perim_hint", "📐 异形线圈周长推算: MLT = 展开内周长 + π × 绕组厚度"))
        if hasattr(self, "sb_perim_in"):
            self.sb_perim_in.setTitle(t("lbl_perim_cin", "展开内周长 C_in"))
        if hasattr(self, "sb_perim_outer_len"):
            self.sb_perim_outer_len.setTitle(t("lbl_perim_max_x", "参考外廓长 Max_X"))
        if hasattr(self, "sb_perim_outer_wid"):
            self.sb_perim_outer_wid.setTitle(t("lbl_perim_max_y", "参考外廓宽 Max_Y"))

        if hasattr(self, "sb_radial_layers"):
            self.sb_radial_layers.setTitle(t("lbl_radial_layers", "径向层数"))
            self.sb_radial_layers.setUnit(t("unit_layer", "层"))
        if hasattr(self, "sb_axial_turns"):
            self.sb_axial_turns.setTitle(t("lbl_turns_per_layer", "每层匝数"))
            self.sb_axial_turns.setUnit(t("unit_turn", "匝"))

        if hasattr(self, "lbl_mode"):
            self.lbl_mode.setText(t("lbl_winding_mode", "密排排法模式:"))
        if hasattr(self, "combo_mode"):
            modes_list = [
                (t("mode_hcp", "异数交错密排 (HCP)"), WindingMode.VARIABLE),
                (t("mode_orthogonal", "同数交错密排"), WindingMode.EVEN),
            ]
            self._update_combo_items(self.combo_mode, modes_list)

        if hasattr(self, "chk_crossover"):
            self.chk_crossover.setText(t("chk_crossover", "计入 60° 换层交叉线"))
        if hasattr(self, "chk_mold_clamping"):
            self.chk_mold_clamping.setText(t("chk_die_press", "启用模具限位压实"))
        if hasattr(self, "sb_mold_height"):
            self.sb_mold_height.setTitle(t("lbl_die_press_thk", "模具压实厚度"))

        # 左侧参数面板 - 卡片2: 线材与张力
        if hasattr(self, "lbl_wire_shape"):
            self.lbl_wire_shape.setText(t("lbl_wire_shape", "线材截面形态:"))
        if hasattr(self, "lbl_wire_catalog"):
            self.lbl_wire_catalog.setText(t("lbl_wire_catalog", "线材出厂规格库选型 (非库内尺寸需咨询华冶定制):"))
        if hasattr(self, "lbl_enamel"):
            self.lbl_enamel.setText(t("lbl_enamel", "漆膜绝缘等级:"))
        if hasattr(self, "lbl_flat_winding_dir"):
            self.lbl_flat_winding_dir.setText(t("lbl_flat_winding_dir", "扁线排线方向:"))
        if hasattr(self, "chk_self_bonding"):
            self.chk_self_bonding.setText(t("chk_self_bonding", "复合热风/酒精自粘胶层 (Self-Bonding)"))
        if hasattr(self, "sb_withstand_ground"):
            self.sb_withstand_ground.setTitle(t("lbl_withstand_ground", "对地/轭铁耐压要求"))
        if hasattr(self, "sb_withstand_turn"):
            self.sb_withstand_turn.setTitle(t("lbl_withstand_turn", "匝间冲击耐压要求"))
        if hasattr(self, "lbl_wire"):
            self.lbl_wire.setText(t("sec_wire_params", "▶ 漆包线线材与张力"))
        if hasattr(self, "sb_bare_dia"):
            self.sb_bare_dia.setTitle(t("lbl_bare_dia", "铜线裸径 (d)"))
        if hasattr(self, "sb_max_od"):
            self.sb_max_od.setTitle(t("lbl_outer_dia", "漆包外径 (D)"))
        if hasattr(self, "lbl_enamel"):
            self.lbl_enamel.setText(t("lbl_enamel_grade", "漆膜绝缘与自粘等级:"))
        if hasattr(self, "combo_enamel_grade"):
            is_en = i18n.is_english()
            if is_en:
                enamel_items = [
                    ("Std Self-Bonding (Enamel+Bond +0.010mm · Standard)", EnamelGrade.SB_010),
                    ("Thin Self-Bonding (Enamel+Bond +0.008mm)", EnamelGrade.SB_008),
                    ("Heavy Self-Bonding (Enamel+Bond +0.014mm · 2UEW-SB)", EnamelGrade.SB_014),
                    ("Grade 0 Ultra-Thin (Non-SB 1UEW, OD+0.003mm)", EnamelGrade.GRADE_0),
                    ("Grade 1 Single Coat (Non-SB 1UEW, OD+0.008mm)", EnamelGrade.GRADE_1),
                    ("Grade 2 Heavy Dual Coat (Non-SB 2UEW, OD+0.014mm)", EnamelGrade.GRADE_2),
                    ("Grade 3 Triple Coat (Non-SB 3UEW, OD+0.022mm)", EnamelGrade.GRADE_3),
                    ("Custom Outer Dia (Keep Manual Input)", EnamelGrade.CUSTOM),
                ]
            else:
                enamel_items = [
                    ("常规标准自粘 (漆膜+胶厚 +0.010mm · +0.01 标配)", EnamelGrade.SB_010),
                    ("薄胶复合自粘 (漆膜+胶厚 +0.008mm)", EnamelGrade.SB_008),
                    ("加厚复合自粘 (漆膜+胶厚 +0.014mm · 2UEW-SB)", EnamelGrade.SB_014),
                    ("0 级超薄漆膜 (非自粘 1UEW, 外径+0.003mm)", EnamelGrade.GRADE_0),
                    ("1 级单涂层 (非自粘 1UEW, 外径+0.008mm)", EnamelGrade.GRADE_1),
                    ("2 级加厚双涂层 (非自粘 2UEW, 外径+0.014mm)", EnamelGrade.GRADE_2),
                    ("3 级特厚涂层 (非自粘 3UEW, 外径+0.022mm)", EnamelGrade.GRADE_3),
                    ("自定义外径 (保持手动输入设定)", EnamelGrade.CUSTOM),
                ]
            self._update_combo_items(self.combo_enamel_grade, enamel_items)
        if hasattr(self, "chk_self_bonding"):
            self.chk_self_bonding.setText(t("chk_self_bonding", "复合热风/酒精自粘胶层 (Self-Bonding · 标配)"))
        if hasattr(self, "sb_tension"):
            self.sb_tension.setTitle(t("lbl_tension_ratio", "张力拉伸系数"))
            self.sb_tension.setUnit(t("unit_ratio", "系数"))
        if hasattr(self, "lbl_rho"):
            self.lbl_rho.setText(t("lbl_copper_grade", "铜材电导等级:"))
        if hasattr(self, "combo_copper_grade"):
            is_en = i18n.is_english()
            if is_en:
                cu_grades = [
                    ("Pure Copper (Huaye Measured: 1/58.5)", (0.01709402, 8.90)),
                    ("Pure Copper (IACS 100%: 1/58)", (0.01724138, 8.90)),
                    ("Oxygen-Free Copper (OFC Annealed: 1/59)", (0.01694915, 8.90)),
                    ("15% Copper-Clad Aluminum (CCAW)", (0.02525000, 3.63)),
                    ("Electrical Aluminum (EC-1350)", (0.02826000, 2.70)),
                    ("Custom Measured Resistivity...", (-1.0, 8.90)),
                ]
            else:
                cu_grades = [
                    ("纯铜 (华冶实测经验值)", (0.01709402, 8.90)),
                    ("纯铜 (国标 100% IACS)", (0.01724138, 8.90)),
                    ("无氧纯铜 (高纯退火态)", (0.01694915, 8.90)),
                    ("15% 铜包铝 (CCAW 经验值)", (0.02525000, 3.63)),
                    ("电工纯铝 (EC-1350)", (0.02826000, 2.70)),
                    ("自定义实测电阻率...", (-1.0, 8.90)),
                ]
            self._update_combo_items(self.combo_copper_grade, cu_grades)
        if hasattr(self, "sb_copper_rho"):
            self.sb_copper_rho.setTitle(t("lbl_copper_rho", "20℃铜电阻率"))
        if hasattr(self, "btn_open_catalog"):
            self.btn_open_catalog.setText(t("btn_huaye_catalog", "华冶线材库"))
        if hasattr(self, "btn_incoming_wire"):
            self.btn_incoming_wire.setText(t("btn_incoming_wire", "⚡ 来料参数"))
        if hasattr(self, "btn_reset_wire"):
            self.btn_reset_wire.setText(t("btn_reset_wire", "✕ 自定义"))

        # 左侧参数面板 - 卡片3: 工作环境与散热条件
        if hasattr(self, "lbl_thermal"):
            self.lbl_thermal.setText(t("sec_thermal_env", "▶ 工作环境与散热条件"))
        if hasattr(self, "lbl_env"):
            self.lbl_env.setText(t("lbl_cooling_condition", "散热对流工况:"))
        if hasattr(self, "combo_thermal_env"):
            env_items = [
                (t("env_weak_convection", "模组内微弱对流"), 25.0),
                (t("env_fpc_enclosure", "贴FPC+钢片封装"), 40.0),
                (t("env_free_convection", "悬空自然对流"), 15.0),
                (t("env_metal_case", "紧密接触金属外壳"), 50.0),
                (t("env_custom", "自定义对流散热"), -1.0),
            ]
            self._update_combo_items(self.combo_thermal_env, env_items)
        if hasattr(self, "sb_ambient_temp"):
            self.sb_ambient_temp.setTitle(t("lbl_ambient_temp", "环境温度"))
        if hasattr(self, "sb_drive_current"):
            self.sb_drive_current.setTitle(t("lbl_test_current", "测试电流"))
        if hasattr(self, "sb_convection_h"):
            self.sb_convection_h.setTitle(t("lbl_convection_coeff", "散热对流系数"))

        # 左侧参数面板 - 卡片4: DFM 装配公差与限值
        if hasattr(self, "lbl_dfm_title"):
            self.lbl_dfm_title.setText(t("sec_dfm_assembly", "▶ 装配空间与公差约束 (DFM)"))
        if hasattr(self, "chk_dfm_enabled"):
            self.chk_dfm_enabled.setText(t("chk_enable_dfm", "启用 DFM 装配公差与限值检查"))
        if hasattr(self, "sb_limit_x"):
            self.sb_limit_x.setTitle(t("lbl_limit_x", "X向装配限值 (Max L)"))
        if hasattr(self, "sb_limit_y"):
            self.sb_limit_y.setTitle(t("lbl_limit_y", "Y向装配限值 (Max W)"))
        if hasattr(self, "sb_limit_z"):
            self.sb_limit_z.setTitle(t("lbl_limit_z", "Z向装配限高 (Max H)"))
        if hasattr(self, "sb_limit_v"):
            self.sb_limit_v.setTitle(t("lbl_limit_v", "驱动电压上限 (Max V)"))
        if hasattr(self, "lbl_temp_class"):
            self.lbl_temp_class.setText(t("lbl_insulation_temp_class", "漆包线耐温等级:"))
        if hasattr(self, "combo_temp_class"):
            temp_classes = [
                (t("temp_class_130", "130级 (B级 / 130℃)"), 130.0),
                (t("temp_class_155", "155级 (F级 / 155℃)"), 155.0),
                (t("temp_class_180", "180级 (H级 / 180℃)"), 180.0),
                (t("temp_class_200", "200级 (C级 / 200℃)"), 200.0),
                (t("temp_class_custom", "自定义耐温限值"), None),
            ]
            self._update_combo_items(self.combo_temp_class, temp_classes)
        if hasattr(self, "sb_limit_t"):
            self.sb_limit_t.setTitle(t("lbl_limit_temp", "耐温安全上限"))

        # 4. 右侧面板 - 仿真计算结果 (16 宫格卡片)
        if hasattr(self, "lbl_twin_title"):
            self.lbl_twin_title.setText(t("sec_sim_results", "▶ 仿真计算结果"))
        if hasattr(self, "card_ol"):
            self.card_ol.setTitle(t("metric_outer_len", "外廓长度 (L)"))
        if hasattr(self, "card_ow"):
            self.card_ow.setTitle(t("metric_outer_width", "外廓宽度 (W)"))
        if hasattr(self, "card_thk"):
            self.card_thk.setTitle(t("metric_coil_height", "线圈厚度 (H)"))
        if hasattr(self, "card_n"):
            self.card_n.setTitle(t("metric_total_turns", "线圈总匝数 (N)"))
            self.card_n.setUnit(t("unit_turn", "匝"))
        if hasattr(self, "card_r20"):
            self.card_r20.setTitle(t("metric_dcr_20", "20℃直流电阻"))
        if hasattr(self, "card_r_init"):
            self.card_r_init.setTitle(t("metric_init_res", "初始测试电阻"))
        if hasattr(self, "card_dcr_hot"):
            self.card_dcr_hot.setTitle(t("metric_steady_res", "工作稳态电阻"))
        if hasattr(self, "card_inductance"):
            self.card_inductance.setTitle(t("metric_inductance", "线圈电感量 (L)"))
        if hasattr(self, "card_v_term"):
            self.card_v_term.setTitle(t("metric_term_voltage", "工作端电压 (V)"))
        if hasattr(self, "card_power"):
            self.card_power.setTitle(t("metric_joule_heat", "发热功耗 (P)"))
        if hasattr(self, "card_ampere_turns"):
            self.card_ampere_turns.setTitle(t("metric_ampere_turns", "安匝数 (NI)"))
        if hasattr(self, "card_t_final"):
            self.card_t_final.setTitle(t("metric_steady_temp", "稳态工作温度 (T)"))
        if hasattr(self, "card_weight"):
            self.card_weight.setTitle(t("metric_weight", "线圈重量"))
        if hasattr(self, "card_wire_fill"):
            self.card_wire_fill.setTitle(t("metric_wire_fill", "漆包线占空比"))
        if hasattr(self, "card_cu_fill"):
            self.card_cu_fill.setTitle(t("metric_copper_fill", "纯铜截面填充率"))
        if hasattr(self, "card_mlt"):
            self.card_mlt.setTitle(t("metric_mlt", "单匝平均周长"))

        # 5. 子组件刷新
        if hasattr(self, "canvas_widget") and hasattr(self.canvas_widget, "retranslate_ui"):
            self.canvas_widget.retranslate_ui()
        if hasattr(self, "dfm_strip") and hasattr(self.dfm_strip, "retranslate_ui"):
            self.dfm_strip.retranslate_ui()
        if hasattr(self, "comparison_drawer") and hasattr(self.comparison_drawer, "retranslate_ui"):
            self.comparison_drawer.retranslate_ui()

        # 6. 状态栏、Tooltip 与云端指示灯刷新
        if hasattr(self, "_setup_tooltips"):
            self._setup_tooltips()
        if hasattr(self, "_refresh_cloud_status_ui"):
            self._refresh_cloud_status_ui()
        if hasattr(self, "status_bar"):
            if getattr(self, "_ota_ready_version", None):
                clean_ver = self._ota_ready_version
                is_en = i18n.is_english()
                self.status_bar.showMessage(
                    f"✨ Update Ready: Patch (v{clean_ver}) staged in background — will apply automatically on next exit"
                    if is_en else
                    f"✨ 版本更新... 优化补丁已在后台就绪 (v{clean_ver})，将在软件下次退出时自动生效",
                    25000
                )
            else:
                self.status_bar.showMessage(t("status_ready", "就绪 | 双核物理引擎待命"))

        # 7. 重新触发当前拓扑动态标签与仿真计算 (确保 KPI 卡片标题与动态限值标签 100% 同步到当前语言)
        if hasattr(self, "combo_coil_type"):
            self._on_coil_type_changed(self.combo_coil_type.currentIndex())
        else:
            self.run_simulation()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "splitter") and hasattr(self, "_splitter_left_width"):
            sizes = self.splitter.sizes()
            total_w = sum(sizes) if sizes else self.splitter.width()
            self.splitter.setSizes([self._splitter_left_width, max(100, total_w - self._splitter_left_width)])

    def event(self, event: QEvent):
        """
        拦截由子控件鼠标悬浮触发的空白 QStatusTipEvent ("")，
        防止鼠标划过工作区任意控件时瞬间清空左下角 status_bar 正在显示的静默下载进度或系统提示语。
        """
        if event.type() == QEvent.Type.StatusTip:
            tip = event.tip() if hasattr(event, "tip") else ""
            if not tip:
                return True
        return super().event(event)

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
        """为所有输入控件、选项卡与 16 宫格输出卡片配置高对比度工程释义 Tooltip (支持中英双语切换)"""
        is_en = i18n.is_english()
        if is_en:
            if hasattr(self, "btn_open"):
                self.btn_open.setToolTip("Load an .ansvcoil project case file")
            if hasattr(self, "btn_save"):
                self.btn_save.setToolTip("Save current coil parameters & DFM constraints as an .ansvcoil project case")
            if hasattr(self, "btn_export"):
                self.btn_export.setToolTip("Export multi-physics engineering evaluation report (.xlsx / .csv)")
            self.combo_presets.setToolTip("[Engineering Presets]\nQuickly load industry benchmark coil cases (Smartphone VCM, 0825 Coin Z-LRA, X-LRA Racetrack, Octagonal AF/OIS Coil, CAD Custom Perimeter).")
            self.combo_coil_type.setToolTip("[Coil Topology]\nSelect physical coil geometry:\n• Racetrack: Linear actuators (X-LRA) & voice coil motors (VCM)\n• Circular: Coin actuators (Z-LRA) & speakers\n• Octagonal: 45° chamfered octagon for compact OIS/AF corner magnets\n• Custom Perimeter: Steiner offset solver based on CAD inner perimeter")
            self.sb_inner_len.setToolTip("[Inner Length IL / Inner Diameter ID]\nStraight mandrel span along the major axis (or inner diameter ID in Circular mode).")
            self.sb_inner_wid.setToolTip("[Inner Width IW]\nStraight mandrel span along the minor axis (inner corner radius R = IW/2).")
            if hasattr(self, "sb_oct_id1"):
                self.sb_oct_id1.setToolTip("[Octagonal Flat Inner Span ID1]\nNormal inner span between opposite straight sides (mm).")
            if hasattr(self, "sb_oct_id2"):
                self.sb_oct_id2.setToolTip("[Octagonal Chamfer Inner Span ID2]\nNormal inner span between opposite 45° chamfer sides (mm).")
            if hasattr(self, "sb_oct_l1"):
                self.sb_oct_l1.setToolTip("[Straight Segment Length L1]\nAnalytically derived flat side length from ID1, ID2 and R1 (mm).")
            if hasattr(self, "sb_oct_l2"):
                self.sb_oct_l2.setToolTip("[Chamfer Segment Length L2]\nAnalytically derived 45° bevel edge length (mm).")
            if hasattr(self, "sb_oct_r1"):
                self.sb_oct_r1.setToolTip("[Inner Corner Fillet R1]\nMandrel corner transition radius across all 8 vertices (mm).")
            if hasattr(self, "lbl_oct_derived"):
                self.lbl_oct_derived.setToolTip("[Octagonal Derived Geometry]\nClosed-form analytical lengths L1 and L2 solved from ID1, ID2, and R1.")
            if hasattr(self, "sb_perim_in"):
                self.sb_perim_in.setToolTip("[Inner Contour Perimeter C_in]\nMeasured inner perimeter along the mandrel wall in CAD (mm).")
            if hasattr(self, "sb_perim_outer_len"):
                self.sb_perim_outer_len.setToolTip("[Reference Outer Length Max_X]\nReference bounding length along the X axis (mm).")
            if hasattr(self, "sb_perim_outer_wid"):
                self.sb_perim_outer_wid.setToolTip("[Reference Outer Width Max_Y]\nReference bounding width along the Y axis (mm).")
            self.sb_radial_layers.setToolTip("[Radial Winding Layers]\nNumber of radial winding layers (supports 0.5 half-layer for single-ended lead exit).")
            self.sb_axial_turns.setToolTip("[Turns per Layer]\nNumber of turns per layer along the axial Z height.")
            self.combo_mode.setToolTip("[Packing Mode]\n• Variable HCP (Staggered): Adjacent layers nest into valleys (~0.866 pitch)\n• Equal Grid (Orthogonal): All layers have identical turn counts")
            if hasattr(self, "chk_crossover"):
                self.chk_crossover.setToolTip("[60° Layer Crossover Wire]\nAccounts for localized radial bulge in the end-turn arc caused by layer transitions.")
            if hasattr(self, "chk_mold_clamping"):
                self.chk_mold_clamping.setToolTip("[Die-Press Compaction]\nSimulates fixture compaction of axial coil height to a target cavity thickness.")
            if hasattr(self, "sb_mold_height"):
                self.sb_mold_height.setToolTip("[Die-Press Target Thickness]\nTarget cavity thickness (mm), bounded by incompressible copper volume.")
            self.sb_bare_dia.setToolTip("[Bare Copper Diameter d]\nNominal bare copper conductor diameter (mm).")
            self.sb_max_od.setToolTip("[Over-Enamel Diameter D]\nMaximum wire outer diameter including insulation and self-bonding coat (mm).")
            self.sb_tension.setToolTip("[Tension Necking Factor]\nConductor cross-section thinning factor induced by high-speed winding tension.")
            self.combo_copper_grade.setToolTip("[Copper Conductivity Grade]\nSelect standard copper resistivity grade (OFHC = 0.016959 Ω·mm²/m) or custom value.")
            self.sb_copper_rho.setToolTip("[20℃ Copper Resistivity]\nBulk copper electrical resistivity at 20℃ (Ω·mm²/m).")
            self.combo_thermal_env.setToolTip("[Cooling Condition Preset]\nSelect typical mounting & heat dissipation environment.")
            self.sb_ambient_temp.setToolTip("[Ambient Temperature]\nBaseline ambient operating temperature Ta (℃).")
            self.sb_drive_current.setToolTip("[Test Drive Current]\nContinuous DC excitation current (mA).")
            self.sb_convection_h.setToolTip("[Convection Coefficient h]\nEffective surface heat transfer coefficient (W/(m²·K)).")
            if hasattr(self, "chk_dfm_enabled"):
                self.chk_dfm_enabled.setToolTip("[DFM Assembly & Safety Check]\nEnables real-time verification of outer dimensions, height, voltage, and thermal limits.")
            self.sb_limit_x.setToolTip("[X-Axis Assembly Limit]\nMaximum allowable outer length/span along X (mm).")
            self.sb_limit_y.setToolTip("[Y-Axis Assembly Limit]\nMaximum allowable outer width/span along Y (mm).")
            self.sb_limit_z.setToolTip("[Z-Axis Height Limit]\nMaximum allowable axial thickness H (mm).")
            self.sb_limit_v.setToolTip("[Driver Voltage Limit]\nMaximum compliance voltage of the driver IC (V).")
            self.combo_temp_class.setToolTip("[Enamel Thermal Class]\nStandard NEMA/IEC insulation thermal ratings: Class B (130℃), F (155℃), H (180℃), C (200℃).")
            self.sb_limit_t.setToolTip("[Max Safe Temperature]\nMaximum continuous operating temperature rating (℃).")
            self.card_ol.setToolTip("[Outer Length / OD]\nMolded outer length (or outer diameter in Circular mode) (mm).")
            self.card_ow.setToolTip("[Outer Width / Span]\nMolded outer width including enamel build and crossover increment (mm).")
            self.card_thk.setToolTip("[Coil Height H]\nTotal axial thickness along the Z axis (mm).")
            self.card_n.setToolTip("[Total Turns N]\nTotal effective conductive turns.")
            self.card_r20.setToolTip("[20℃ Cold DCR]\nBaseline DC resistance at 20℃ (Ω) for IQC/OQC inspection.")
            self.card_r_init.setToolTip("[Initial Ambient DCR]\nCold DC resistance at the specified ambient temperature Ta (Ω).")
            self.card_dcr_hot.setToolTip("[Steady-State Hot DCR]\nElectro-thermally coupled resistance at thermal equilibrium (Ω).")
            self.card_inductance.setToolTip("[Air-Core Inductance L]\nMulti-layer air-core self-inductance calculated via Wheeler's formula (μH/mH).")
            self.card_v_term.setToolTip("[Terminal Voltage V]\nRequired steady-state drive voltage V = I × DCR_hot (V).")
            self.card_power.setToolTip("[Joule Heat Power P]\nSteady-state thermal dissipation P = I² × DCR_hot (mW).")
            self.card_ampere_turns.setToolTip("[Ampere-Turns NI]\nMagnetomotive force NI = N × I (AT), proportional to Lorentz driving force.")
            self.card_t_final.setToolTip("[Steady-State Temp T]\nEquilibrium coil temperature T_final = Ta + ΔT (℃).")
            self.card_weight.setToolTip("[Coil Mass]\nTotal moving mass of the winding (g).")
            self.card_wire_fill.setToolTip("[Enamel Wire Fill Factor]\nRatio of total enameled wire area to winding window cross-section (%).")
            self.card_cu_fill.setToolTip("[Bare Copper Fill Factor]\nRatio of pure bare copper conductor area to winding window cross-section (%).")
            self.card_mlt.setToolTip("[Mean Length per Turn MLT]\nAverage perimeter per turn integrated across all radial layers (mm).")
            if hasattr(self, "canvas_widget") and hasattr(self.canvas_widget, "tab_macro"):
                self.canvas_widget.tab_macro.setTabToolTip(0, "[2D Top Profile]\nTop-down X-Y outer envelope, inner mandrel opening, and 60° crossover lead geometry.")
                self.canvas_widget.tab_macro.setTabToolTip(1, "[2D Cross-Section & Z-Clearance]\nISO 129 section view and axial Z-height clearance analysis.")
                self.canvas_widget.tab_macro.setTabToolTip(2, "[3D Isometric Cage]\n3D isometric visualization of the coil inside the DFM bounding envelope.")
            if hasattr(self, "dfm_strip"):
                self.dfm_strip.setToolTip("[DFM Tolerance Verdict Strip]\nReal-time monitoring of X/Y/Z dimensions, voltage, and thermal limits.")
            if hasattr(self, "comparison_drawer"):
                self.comparison_drawer.setToolTip("[Scheme Comparison Matrix]\nFreeze parameter snapshots for side-by-side delta comparison, one-click restore, and Excel/CSV export.")
            return

        if hasattr(self, "btn_open"):
            self.btn_open.setToolTip("导入 .ansvcoil 专属工程文件或历史设计方案")
        if hasattr(self, "btn_save"):
            self.btn_save.setToolTip("将当前仿真参数与约束导出为 .ansvcoil 专属工程文件")
        if hasattr(self, "btn_export"):
            self.btn_export.setToolTip("导出专业工业级 Excel (含二维高清工程制图与公差校核) 仿真报告")

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
            self.sb_perim_outer_len.setToolTip("【异形参考外长 (Max Outer X)】\n异形线圈沿长轴方向的最大包络参考尺寸 (mm)，用于装配干涉与尺寸包络检查。")
        if hasattr(self, "sb_perim_outer_wid"):
            self.sb_perim_outer_wid.setToolTip("【异形参考外宽 (Max Outer Y)】\n异形线圈沿短轴方向的最大包络参考尺寸 (mm)，用于装配干涉与尺寸包络检查。")

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
            self.chk_dfm_enabled.setToolTip("【装配公差与安全限值】\n开启后，系统将自动对比尺寸、高度、电压与温度是否超出公差限值，并在超差时以红灯预警。未开启时处于自由参数模式。")
        self.sb_limit_x.setToolTip("【X向装配限值】\n装配结构允许线圈沿 X 向（长边）的最大尺寸 (mm)。")
        self.sb_limit_y.setToolTip("【Y向装配限值】\n装配结构允许线圈沿 Y 向（短边）的最大尺寸 (mm)。")
        self.sb_limit_z.setToolTip("【Z向装配限高】\n机构空间允许线圈轴向高度/成型厚度的最大尺寸 (mm)。")
        self.sb_limit_v.setToolTip("【驱动电压上限】\n驱动芯片 (IC) 输出引脚的最大允许驱动电压 (V)。")
        self.combo_temp_class.setToolTip("【漆包线耐温等级】\n常用绝缘耐温标准：130级 (B级 / 130℃)、155级 (F级 / 155℃)、180级 (H级 / 180℃)、200级 (C级 / 200℃)。")
        self.sb_limit_t.setToolTip("【耐温安全上限】\n漆包线绝缘层允许承受的最高长期工作结温 (℃)。")

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
            self.dfm_strip.setToolTip("【DFM 结构装配与制造公差】\n实时监控线圈外形尺寸、极限厚度、驱动端电压与耐温上限，点击设置按钮可快速定位修改限值。")
        if hasattr(self, "comparison_drawer"):
            self.comparison_drawer.setToolTip("【方案比对抽屉】\n记录手动固化的参数方案并进行横向对比分析，支持基准比对、一键还原与报表导出。")

    def _setup_statusbar_copyright(self):
        """配置右下角三行常驻版权信息与云端实时状态 (规范 04.二)"""
        # 授权服务器在线状态指示与快捷检测按钮
        self._last_cloud_state = None  # None = connecting, or (ok, msg, target)
        self.btn_cloud_status = QPushButton()
        self.btn_cloud_status.clicked.connect(self._on_cloud_status_clicked)
        self.status_bar.addPermanentWidget(self.btn_cloud_status)
        self._refresh_cloud_status_ui()

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

    def _refresh_cloud_status_ui(self):
        """根据当前语言与最近一次云端心跳状态刷新右下角状态指示灯"""
        if not hasattr(self, "btn_cloud_status"):
            return
        is_en = i18n.is_english()
        state = getattr(self, "_last_cloud_state", None)
        if state is None:
            self.btn_cloud_status.setText("⏳ Connecting License Server..." if is_en else "⏳ 授权服务器连接中...")
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
            self.btn_cloud_status.setToolTip(
                "Click to diagnose license server connectivity & commercial status"
                if is_en else
                "点击立即检测授权服务器连通性与最新商业状态"
            )
            return

        ok, msg, target = state
        if ok:
            domain = target.replace("https://", "").replace("http://", "")
            self.btn_cloud_status.setText("🟢 License Server Connected" if is_en else "🟢 授权服务器已连接")
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
                f"Connected to Official License Center: {domain}\n"
                "✓ 100% of coil simulation data remains strictly on your local workstation.\n"
                "✓ Only performs license verification & OTA checks (every 30 mins).\n"
                "Click to open Network & Database Diagnostics (Ctrl+D)."
                if is_en else
                f"已连接至官方授权中心: {domain}\n"
                "✓ 本工位机线圈物理仿真设计数据 100% 留存在本地，绝不上云。\n"
                "✓ 仅执行商业授权校验与版本检测 (每 30 分钟心跳一次)。\n"
                "点击可打开数据库通信与网络诊断中心 (Ctrl+D)。"
            )
        else:
            self.btn_cloud_status.setText("⚪ Server Offline (Diagnose)" if is_en else "⚪ 数据库未连通 (点击诊断)")
            self.btn_cloud_status.setStyleSheet("""
                QPushButton {
                    background-color: #FEF2F2;
                    color: #B91C1C;
                    border: 1px solid #FECACA;
                    border-radius: 4px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    margin-right: 14px;
                }
                QPushButton:hover {
                    background-color: #FEE2E2;
                }
            """)
            self.btn_cloud_status.setToolTip(
                f"{msg}\n"
                "Database connection is currently offline in this network environment.\n"
                "Click to open Network & Environment Diagnostics (Shortcut: Ctrl+D)."
                if is_en else
                f"{msg}\n"
                "当前内网环境下数据库未建立连接。\n"
                "点击立即打开数据库通信与环境诊断中心 (快捷键: Ctrl+D)。"
            )

    def _on_cloud_status_received(self, ok: bool, msg: str, target: str):
        """线程安全槽：刷新状态栏授权服务器连接状态"""
        self._last_cloud_state = (ok, msg, target)
        self._refresh_cloud_status_ui()

    def _on_cloud_status_clicked(self):
        """点击底部授权状态指示按钮打开网络通信与环境诊断中心"""
        self._open_cloud_config_dialog()

    def _open_cloud_config_dialog(self):
        """打开企业内网数据库与通信诊断中心 (对标 Gear 规范)"""
        from src.gui.cloud_config_dialog import open_cloud_config_dialog
        open_cloud_config_dialog(self)

    def _on_remote_command_received(self, cmd: str, payload: str):
        """响应来自 Cloudflare 边缘控制台的远程指令 (对标 Gear)"""
        cmd_upper = (cmd or "").upper().strip()
        logger.warning(f"MainWindow 捕获云端远程遥控指令: {cmd_upper}")

        is_en = i18n.is_english()
        if cmd_upper in ("LOCK_APP", "REVOKE_LICENSE"):
            if getattr(self, "_remote_locked_flag", False):
                return
            self._remote_locked_flag = True

            from src.core.license_manager import LicenseManager, get_machine_code
            # 1. 彻底销毁本地凭证并刷新界面状态
            LicenseManager.revoke_local_license(reason="当前工位机商业授权已被管理员在云端取消，已退回未激活评估状态")
            self._refresh_license_status()

            # 2. 状态栏警告提示
            self.status_bar.showMessage(
                "⚠️ Commercial license cancelled by admin. Reverted to unactivated evaluation mode."
                if is_en else
                "⚠️ 商业授权已被管理员在后台取消，软件已退回【未激活评估状态】（本地凭证已彻底销毁）。",
                8000
            )

            from src.version import OFFICIAL_EMAIL, WECHAT_CONTACT_ID, WECHAT_OFFICIAL_ACCOUNT, OFFICIAL_URL
            mid = get_machine_code()

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("License Revoked - Reverted to Unactivated" if is_en else "授权取消通知 · 软件已退回未激活状态")
            msg_box.setIcon(QMessageBox.Icon.Warning)

            if is_en:
                msg_text = (
                    "<b>[Workstation Commercial License Cancelled by Administrator]</b><br><br>"
                    "The workstation license has been cancelled and local license file (.lic) cleared.<br>"
                    "The application has cleanly reverted to <b>Unactivated Evaluation Mode</b>.<br><br>"
                    "To re-authorize or upgrade, please contact administrator or click below to enter activation wizard:<br><br>"
                    f"• <b>Support Email:</b> <a href='mailto:{OFFICIAL_EMAIL}' style='color:#0284C7;'>{OFFICIAL_EMAIL}</a><br>"
                    f"• <b>WeChat Support:</b> <code style='color:#059669; font-weight:bold;'>{WECHAT_CONTACT_ID}</code><br>"
                    f"• <b>Machine ID:</b> <code style='color:#475569;'>{mid}</code>"
                )
            else:
                msg_text = (
                    "<b>【工位机商业授权已被管理员在云端取消】</b><br><br>"
                    "云端凭证已注销，本地许可凭证 (license.lic) 已彻底安全销毁。<br>"
                    "当前软件已自动退回为 <b>【未激活评估状态】</b>。<br><br>"
                    "如需重新开通或恢复激活，请联系管理员在后台下发新授权，或点击下方【输入/申请授权码】打开激活向导：<br><br>"
                    f"• <b>技术支持邮箱:</b> <a href='mailto:{OFFICIAL_EMAIL}' style='color:#0284C7;'>{OFFICIAL_EMAIL}</a><br>"
                    f"• <b>工程师微信:</b> <code style='color:#059669; font-weight:bold;'>{WECHAT_CONTACT_ID}</code><br>"
                    f"• <b>官方服务门户:</b> <a href='{OFFICIAL_URL}' style='color:#0284C7;'>{OFFICIAL_URL}</a><br>"
                    f"• <b>工位机器码:</b> <code style='color:#475569;'>{mid}</code>"
                )

            msg_box.setText(msg_text)
            btn_wizard = msg_box.addButton("Enter Activation Wizard" if is_en else "🔑 输入/申请新授权码", QMessageBox.ButtonRole.ActionRole)
            btn_copy = msg_box.addButton("📋 Copy Info" if is_en else "📋 复制机器码与联系方式", QMessageBox.ButtonRole.ActionRole)
            btn_ok = msg_box.addButton("OK (Evaluation Mode)" if is_en else "以评估模式浏览", QMessageBox.ButtonRole.AcceptRole)
            msg_box.setDefaultButton(btn_wizard)

            while True:
                msg_box.exec()
                if msg_box.clickedButton() == btn_copy:
                    from PyQt6.QtWidgets import QApplication
                    clipboard = QApplication.clipboard()
                    contact_copy = (
                        f"【ANSV Coil-Architect Pro 授权恢复申请】\n"
                        f"机器码 (Machine ID): {mid}\n"
                        f"支持邮箱: {OFFICIAL_EMAIL}\n"
                        f"微信支持: {WECHAT_CONTACT_ID}\n"
                        f"服务门户: {OFFICIAL_URL}"
                    )
                    clipboard.setText(contact_copy)
                    btn_copy.setText("✅ 已复制到剪贴板")
                    continue
                elif msg_box.clickedButton() == btn_wizard:
                    self._remote_locked_flag = False
                    self._open_activation_dialog()
                    break
                else:
                    self._remote_locked_flag = False
                    break

        elif cmd_upper == "UPDATE_LICENSE":
            logger.info("MainWindow 捕获云端远程授权下发指令: UPDATE_LICENSE，刷新状态与界面...")
            self._remote_locked_flag = False
            # 1. 若当前正打开激活向导弹窗，自动关闭它
            if hasattr(self, "_current_activation_dialog") and self._current_activation_dialog:
                try:
                    self._current_activation_dialog.accept()
                except Exception:
                    pass
                self._current_activation_dialog = None

            # 2. 刷新主界面顶部授权按钮与功能守卫状态
            self._refresh_license_status()

            # 3. 状态栏高亮提示
            self.status_bar.showMessage(
                "🎉 Cloud commercial license activated and applied automatically!"
                if is_en else
                "🎉 云端已远程下发最新商业授权，系统已自动刷新激活并解除全部限制！",
                6000
            )

            # 4. 弹出详细商业授权凭证卡片弹窗 (直观展示激活凭证与特权信息)
            try:
                from src.gui.activation_dialog import show_license_activated_dialog
                show_license_activated_dialog(self)
            except Exception as e:
                logger.error(f"弹出授权凭证窗口异常: {e}")



    def closeEvent(self, event):
        """
        主窗口关闭安全销毁守护线程与资源，并在更新就绪时拉起影子替换 (100% 对齐 Gear 工业级规范)
        微信式体验：关闭时后台静默覆盖，绝不自动弹起新程序，下次打开直接为新版本
        """
        logger.info("[CloseEvent] 主窗口接收到关闭事件，正在安全释放资源并检查 OTA 更新...")

        # 1. 移除全局事件过滤器
        if hasattr(self, "_param_interaction_filter"):
            try:
                from PyQt6.QtWidgets import QApplication
                app_inst = QApplication.instance()
                if app_inst:
                    app_inst.removeEventFilter(self._param_interaction_filter)
            except Exception:
                pass

        # 2. 停止云端后台数据同步线程
        try:
            from src.core.cloud_client import CloudClient
            CloudClient.stop_background_sync()
        except Exception:
            pass

        # 3. 停止 OTA 后台静默检测线程
        if hasattr(self, "ota_checker") and self.ota_checker:
            try:
                self.ota_checker.stop()
            except Exception:
                pass
            self.ota_checker = None

        # 4. 检查是否有静默下载就绪的 OTA 补丁包，触发影子替换
        try:
            from src.core.ota_updater import OtaUpdater
            updater = getattr(self, "ota_updater", None) or OtaUpdater.get_instance()
            if updater:
                ready, meta = updater.is_update_ready()
                logger.info(f"[CloseEvent] OTA 更新就绪状态检查: ready={ready}, meta={meta.get('version') if meta else None}")
                if ready:
                    logger.info("[CloseEvent] 检测到更新包已就绪，正在拉起后台脱离影子替换进程 (restart_after=False)...")
                    ok = updater.launch_shadow_replacement(restart_after=False)
                    logger.info(f"[CloseEvent] 后台影子替换脚本拉起结果: {ok}")
        except Exception as e:
            logger.error(f"[CloseEvent] 检查或拉起影子替换异常: {e}")

        event.accept()
        super().closeEvent(event)

    def _start_silent_ota_checker(self):
        """启动后台静默 OTA 巡检线程 (首轮延迟，周期巡检)"""
        if not self.ota_checker:
            self.ota_checker = OtaChecker(self.ota_updater, interval_sec=3600, parent=self)
            self.ota_checker.start()

    def _on_ota_available(self, info: dict):
        ver = str(info.get("latest_version") or info.get("version") or "").lstrip("vV")
        logger.info(f"[OTA] 检测到可用新版本: v{ver}，后台正在静默拉取增量包...")
        if hasattr(self, "status_bar"):
            is_en = i18n.is_english()
            self.status_bar.showMessage(
                f"⬇️ New update detected (v{ver})... preparing silent background download..."
                if is_en else
                f"⬇️ 发现新版优化 (v{ver})... 正在后台静默拉取升级包...",
                6000
            )

    def _on_ota_download_progress(self, current_bytes: int, total_bytes: int, speed_mbps: float):
        if total_bytes > 0:
            pct = min(100.0, (current_bytes / total_bytes) * 100.0)
            cur_mb = current_bytes / (1024 * 1024)
            tot_mb = total_bytes / (1024 * 1024)
            if hasattr(self, "status_bar"):
                is_en = i18n.is_english()
                self.status_bar.showMessage(
                    f"⬇️ Downloading update silently ({pct:.0f}% | {cur_mb:.1f}MB/{tot_mb:.1f}MB · {speed_mbps:.1f} MB/s)"
                    if is_en else
                    f"⬇️ 发现新版优化... 静默下载中 ({pct:.0f}% | {cur_mb:.1f}MB/{tot_mb:.1f}MB · {speed_mbps:.1f} MB/s)",
                    5000
                )

    def _on_ota_download_ready(self, version: str, zip_path: str):
        clean_ver = str(version or "").lstrip("vV")
        logger.info(f"[OTA] 升级包已在后台下载就绪: v{clean_ver} -> {zip_path}")
        self._ota_ready_version = clean_ver
        if hasattr(self, "status_bar"):
            is_en = i18n.is_english()
            self.status_bar.showMessage(
                f"✨ Update Ready: Patch (v{clean_ver}) staged in background — will apply automatically on next exit"
                if is_en else
                f"✨ 版本更新... 优化补丁已在后台就绪 (v{clean_ver})，将在软件下次退出时自动生效",
                25000
            )

    def _on_ota_download_failed(self, error_msg: str):
        logger.debug(f"[OTA] 静默更新未完成: {error_msg}")

    def _open_update_dialog(self):
        """打开在线自动升级对话框"""
        from src.gui.update_dialog import UpdateDialog
        dlg = UpdateDialog(self)
        dlg.exec()

    def _open_user_manual(self):
        """根据当前语言环境打开对应语言的离线 HTML 用户使用说明书"""
        import sys
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        app_dir = Path(__file__).resolve().parent.parent.parent
        exe_dir = Path(sys.executable).resolve().parent
        is_en = i18n.is_english()
        if is_en:
            candidates = [
                exe_dir / "Coil-Architect-Pro_User_Manual.html",
                app_dir / "Coil-Architect-Pro_User_Manual.html",
                app_dir / "docs" / "Coil-Architect-Pro_User_Manual.html",
                exe_dir / "docs" / "Coil-Architect-Pro_User_Manual.html",
                exe_dir / "README_EN.html",
                app_dir / "README_EN.html",
                exe_dir / "Coil-Architect-Pro_使用说明书.html",
                app_dir / "Coil-Architect-Pro_使用说明书.html",
            ]
            fallback_url = "https://github.com/tonychen5577-tech/coil-architect"
        else:
            candidates = [
                exe_dir / "Coil-Architect-Pro_使用说明书.html",
                app_dir / "Coil-Architect-Pro_使用说明书.html",
                app_dir / "docs" / "Coil-Architect-Pro_使用说明书.html",
                exe_dir / "docs" / "Coil-Architect-Pro_使用说明书.html",
                exe_dir / "README.html",
                app_dir / "README.html",
            ]
            fallback_url = "https://github.com/tonychen5577-tech/coil-architect/blob/main/README_CN.md"

        for p in candidates:
            if p.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.resolve())))
                return
        QDesktopServices.openUrl(QUrl(fallback_url))

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
        layout.setSpacing(6)

        # 1. 40px ANSV 纯净官方科技圆环 Logo (透明底平滑缩放，无多余边框)
        lbl_logo = QLabel()
        lbl_logo.setObjectName("lblTopToolbarAnsvLogo")
        lbl_logo.setPixmap(get_ansv_logo_pixmap(40))
        lbl_logo.setFixedSize(40, 40)
        lbl_logo.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(lbl_logo)

        # 2. 标题区 (第一行: ANSV 英文首字母加粗天蓝高亮解码；第二行: ANSV 官方中文全称)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)

        self.lbl_brand = QLabel()
        lbl_brand = self.lbl_brand
        lbl_brand.setObjectName("lblTopToolbarBrand")
        lbl_brand.setTextFormat(Qt.TextFormat.RichText)
        lbl_brand.setText(
            "<span style='color:#0284C7; font-weight:900; font-size:13px;'>A</span><span style='color:#475569; font-weight:600; font-size:11px;'>ctuator </span>"
            "<span style='color:#0284C7; font-weight:900; font-size:13px;'>N</span><span style='color:#475569; font-weight:600; font-size:11px;'>umerical </span>"
            "<span style='color:#0284C7; font-weight:900; font-size:13px;'>S</span><span style='color:#475569; font-weight:600; font-size:11px;'>imulation </span>"
            "<span style='color:#94A3B8; font-weight:600; font-size:11px;'>&amp; </span>"
            "<span style='color:#0284C7; font-weight:900; font-size:13px;'>V</span><span style='color:#475569; font-weight:600; font-size:11px;'>alidation</span>"
        )
        lbl_brand.setStyleSheet("line-height: 1.1; background: transparent; border: none;")

        self.lbl_sub = QLabel("微型执行器与精密传动仿真验证平台")
        lbl_sub = self.lbl_sub
        lbl_sub.setObjectName("lblTopToolbarSub")
        lbl_sub.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748B; line-height: 1.1; background: transparent; border: none;")

        title_box.addWidget(lbl_brand)
        title_box.addWidget(lbl_sub)
        layout.addLayout(title_box)

        layout.addSpacing(10)

        # 2. 项目名称输入区 (锁死尺寸，防止横向拉伸挤占按钮空间)
        self.lbl_proj = QLabel("🏷️ 项目:")
        lbl_proj = self.lbl_proj
        lbl_proj.setStyleSheet("font-size: 11px; font-weight: 700; color: #1E293B;")
        lbl_proj.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(lbl_proj)

        self.txt_project_name = QLineEdit("Coli-Architect")
        self.txt_project_name.setPlaceholderText("项目代号")
        self.txt_project_name.setToolTip("当前工程项目代号/名称（导出 Excel/CSV 报表与方案比对时将自动注入文件名与表格抬头）")
        self.txt_project_name.setFixedWidth(110)
        self.txt_project_name.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.txt_project_name.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 3px 6px;
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

        layout.addSpacing(4)

        # 3. 快速预设方案下拉框 (按用户要求优化超长文本框：从 270px 收敛至 145px)
        self.lbl_preset = QLabel("📐 预设:")
        lbl_preset = self.lbl_preset
        lbl_preset.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        lbl_preset.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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
        self.combo_presets.setFixedWidth(162)
        self.combo_presets.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.combo_presets)

        # 4. 中间自适应弹性占位条 (窗口缩放、拉大拉小时由其弹性吸收，两侧控件位置绝对锁定、绝不重叠)
        layout.addStretch(1)

        # 5. 算例与报表操作按钮组 (锁死固定尺寸，文字 100% 完整显示)
        self.btn_open = QPushButton("📂 导入文件")
        self.btn_open.setToolTip("导入 .ansvcoil 专属工程文件或历史设计方案")
        self.btn_open.setFixedWidth(86)
        self.btn_open.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_open.setStyleSheet("padding: 4px 6px; font-size: 11px; font-weight: 600;")
        self.btn_open.clicked.connect(self._import_project)
        layout.addWidget(self.btn_open)

        self.btn_save = QPushButton("💾 导出文件")
        self.btn_save.setToolTip("将当前仿真参数与约束导出为 .ansvcoil 专属工程文件")
        self.btn_save.setFixedWidth(86)
        self.btn_save.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_save.setStyleSheet("padding: 4px 6px; font-size: 11px; font-weight: 600;")
        self.btn_save.clicked.connect(self._export_project)
        layout.addWidget(self.btn_save)

        self.btn_export = QPushButton("📊 导出仿真报告")
        self.btn_export.setToolTip("导出专业工业级 Excel (含二维高清工程制图与公差校核) 仿真报告")
        self.btn_export.setProperty("class", "SuccessBtn")
        self.btn_export.setFixedWidth(116)
        self.btn_export.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_export.setStyleSheet("padding: 4px 6px; font-size: 11px; font-weight: 700;")
        self.btn_export.clicked.connect(self._export_report)
        layout.addWidget(self.btn_export)

        layout.addSpacing(4)

        # 6. 商业授权状态指示按钮 (固定 130px，完整容纳试用与商业版状态)
        self.btn_license = QPushButton("🛡️ 正式商业授权")
        self.btn_license.setFixedWidth(130)
        self.btn_license.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_license.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_license.clicked.connect(self._on_license_chip_clicked)
        layout.addWidget(self.btn_license)
        self._refresh_license_status()

        # 7. 关于系统按钮 (固定 82px)
        self.btn_about = QPushButton("ℹ️ 关于系统")
        self.btn_about.setFixedWidth(82)
        self.btn_about.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_about.setStyleSheet("padding: 4px 6px; font-size: 11px; font-weight: 600;")
        self.btn_about.clicked.connect(self._show_about_dialog)
        layout.addWidget(self.btn_about)

        # 8. 语言无缝即时切换下拉框 (中英双语，持久化保存至 AppData)
        self.combo_lang = QComboBox()
        self.combo_lang.setObjectName("comboLanguage")
        self.combo_lang.addItem("🇨🇳 简体中文", LANG_ZH)
        self.combo_lang.addItem("🇬🇧 English", LANG_EN)
        self.combo_lang.setFixedWidth(106)
        self.combo_lang.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.combo_lang.setToolTip("切换系统显示语言 / Switch Language (中文 / English)")
        self.combo_lang.setStyleSheet("""
            QComboBox {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 600;
                color: #0F172A;
            }
            QComboBox:hover {
                border-color: #0284C7;
                background-color: #F0F9FF;
            }
        """)
        idx = 1 if i18n.current_language == LANG_EN else 0
        self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(self._on_language_selector_changed)
        layout.addWidget(self.combo_lang)

        return bar

    def _refresh_license_status(self):
        """动态刷新顶部授权指示灯的文本、样式与提示 (锁死尺寸自适应文字)"""
        from src.core.license_manager import LicenseManager
        auth_ok, auth_msg, lic_data = LicenseManager.is_system_authorized()
        self.is_authorized = auth_ok
        self.lic_data = lic_data

        if not hasattr(self, "btn_license"):
            return

        is_en = i18n.is_english()
        if auth_ok:
            is_trial = lic_data.get("is_trial", False) if lic_data else False
            if is_trial:
                days_left = lic_data.get("days_left", 7)
                exp_date = lic_data.get("exp_date", "")
                self.btn_license.setText(t("btn_license_trial", "⏱️ 试用期剩 {days} 天", days=days_left))
                self.btn_license.setStyleSheet("""
                    QPushButton {
                        background-color: #F0F9FF;
                        color: #0284C7;
                        border: 1px solid #BAE6FD;
                        border-radius: 4px;
                        padding: 3px 6px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background-color: #E0F2FE;
                        border-color: #38BDF8;
                    }
                """)
                if is_en:
                    self.btn_license.setToolTip(
                        f"7-Day Full-Feature Trial Active | {days_left} Days Left\n"
                        f"Valid Until: {exp_date}\n"
                        f"100% of electromagnetic simulation, scheme matrix & Excel/CSV export features unlocked.\n"
                        f"Click to view trial details or upgrade to a Commercial License."
                    )
                else:
                    self.btn_license.setToolTip(
                        f"7天全功能免激活试用中 | 剩余: {days_left} 天\n"
                        f"有效期至: {exp_date}\n"
                        f"试用期内所有电磁仿真、方案比对及报表导出功能 100% 完整可用\n"
                        f"点击可查看试用详情或升级正式商业版"
                    )
            else:
                lic_type = (lic_data.get("type") or lic_data.get("plan") or "商业版") if lic_data else "商业版"
                raw_exp = (lic_data.get("exp") or lic_data.get("exp_date") or "永久有效") if lic_data else "永久有效"
                if raw_exp in ("2099-12-31", "PERMANENT", "永久有效"):
                    exp_date = "永久有效"
                else:
                    exp_date = raw_exp
                if is_en:
                    if lic_type == "商业版":
                        lic_type = "Commercial"
                    if exp_date in ("永久有效", "PERMANENT"):
                        exp_date = "Permanent"
                self.btn_license.setText(t("btn_license_commercial", "🛡️ 商业授权 ({type})", type=lic_type))
                self.btn_license.setStyleSheet("""
                    QPushButton {
                        background-color: #ECFDF5;
                        color: #059669;
                        border: 1px solid #A7F3D0;
                        border-radius: 4px;
                        padding: 3px 6px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background-color: #D1FAE5;
                        border-color: #6EE7B7;
                    }
                """)
                if is_en:
                    self.btn_license.setToolTip(f"Commercial License Active | Tier: {lic_type}\nValid Until: {exp_date}\nClick to view license certificate details")
                else:
                    self.btn_license.setToolTip(f"商业授权有效 | 类型: {lic_type}\n有效期至: {exp_date}\n点击可查看授权详情")
        else:
            is_trial_expired = lic_data.get("is_trial", False) if lic_data else False
            btn_txt = t("btn_license_expired", "⚠️ 试用已到期") if is_trial_expired else t("btn_license_unauthorized", "⚠️ 未激活 (点击激活)")
            self.btn_license.setText(btn_txt)
            self.btn_license.setStyleSheet("""
                QPushButton {
                    background-color: #FEF3C7;
                    color: #B45309;
                    border: 1px solid #FCD34D;
                    border-radius: 4px;
                    padding: 3px 6px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #FDE68A;
                    border-color: #F59E0B;
                }
            """)
            if is_en:
                self.btn_license.setToolTip("Currently in unactivated evaluation mode.\nClick to enter a license token and unlock all parameter tuning, comparison & export features.")
            else:
                self.btn_license.setToolTip("当前处于未激活评估模式\n点击立即输入授权激活码，解锁全部参数调节、方案比对及报表导出功能")

    def _on_license_chip_clicked(self):
        """点击顶部商业授权指示灯响应"""
        is_en = i18n.is_english()
        if getattr(self, "is_authorized", False):
            lic = getattr(self, "lic_data", {}) or {}
            is_trial = lic.get("is_trial", False)
            if is_trial:
                days_left = lic.get("days_left", 7)
                exp_date = lic.get("exp_date", "")
                start_date = lic.get("start_date", "")

                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Information)
                if is_en:
                    msg_box.setWindowTitle("7-Day Full-Feature Evaluation Details")
                    msg_box.setText(
                        f"⏱️ ANSV Coil-Architect Pro — 7-Day Full-Feature Evaluation Active\n\n"
                        f"• Evaluation Mode: 7-Day Zero-Activation Full-Feature Trial\n"
                        f"• Trial Period: {start_date} to {exp_date}\n"
                        f"• Remaining Days: {days_left} days left\n"
                        f"• Feature Status: Dual-core physics solver, 2D/3D engineering drawings, scheme comparison matrix & Excel/CSV export are 100% unlocked!\n\n"
                        f"Would you like to view Commercial License options or enter an activation token now?"
                    )
                    btn_upgrade = msg_box.addButton("🛒 Order Commercial / Enter Token", QMessageBox.ButtonRole.AcceptRole)
                    btn_continue = msg_box.addButton("Continue Trial", QMessageBox.ButtonRole.RejectRole)
                else:
                    msg_box.setWindowTitle("7天全功能免激活试用详情")
                    msg_box.setText(
                        f"⏱️ ANSV Coil-Architect Pro 全功能免激活试用中\n\n"
                        f"• 试用模式: 7天免激活全功能评估\n"
                        f"• 试用周期: {start_date} 至 {exp_date}\n"
                        f"• 剩余天数: 还有 {days_left} 天\n"
                        f"• 功能状态: 双核物理求解器、2D孪生图纸、方案对比矩阵与 Excel 导出等 100% 全功能已解锁！\n\n"
                        f"是否需要现在查看商业订购方案或输入正式商业激活码？"
                    )
                    btn_upgrade = msg_box.addButton("🛒 订购商业版 / 输入激活码", QMessageBox.ButtonRole.AcceptRole)
                    btn_continue = msg_box.addButton("继续试用", QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(btn_continue)

                btn_upgrade.setStyleSheet("""
                    QPushButton {
                        background-color: #0284C7;
                        color: #FFFFFF;
                        border: 1px solid #0369A1;
                        border-radius: 4px;
                        padding: 6px 14px;
                        font-size: 11.5px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #0369A1;
                    }
                """)
                btn_continue.setStyleSheet("""
                    QPushButton {
                        background-color: #F1F5F9;
                        color: #475569;
                        border: 1px solid #CBD5E1;
                        border-radius: 4px;
                        padding: 6px 14px;
                        font-size: 11.5px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #E2E8F0;
                        color: #1E293B;
                    }
                """)

                msg_box.exec()
                if msg_box.clickedButton() == btn_upgrade:
                    self.check_authorization_or_prompt("Commercial License Upgrade" if is_en else "商业授权升级", force_prompt=True)
            else:
                # 商业正式版：直接展示【商业授权凭证详情卡片】，免输激活码
                try:
                    from src.gui.activation_dialog import show_license_activated_dialog
                    show_license_activated_dialog(self, lic)
                except Exception as e:
                    logger.error(f"弹出商业授权凭证卡片异常: {e}")
        else:
            self.check_authorization_or_prompt("Commercial License Activation" if is_en else "商业授权激活", force_prompt=True)

    def check_authorization_or_prompt(self, action_name: str = "", force_prompt: bool = False) -> bool:
        """
        检查商业授权状态；若未激活或强制要求升级激活则弹出激活对话框。
        返回 True 表示已激活，可以继续操作；返回 False 表示未激活或取消激活，应阻断操作。
        """
        from src.core.license_manager import LicenseManager
        is_en = i18n.is_english()
        auth_ok, auth_msg, lic_data = LicenseManager.is_system_authorized()
        if auth_ok and not force_prompt:
            if not getattr(self, "is_authorized", False):
                self._refresh_license_status()
            return True

        if getattr(self, "_is_prompting_activation", False):
            return False

        self._is_prompting_activation = True
        try:
            if hasattr(self, "status_bar"):
                if is_en:
                    msg_suffix = f"[{action_name}]" if action_name else "parameter tuning & simulation"
                    self.status_bar.showMessage(f"💡 Notice: {msg_suffix} requires a commercial license. Opening Activation Center...", 3000)
                else:
                    msg_suffix = f"【{action_name}】" if action_name else "参数调节与工程计算"
                    self.status_bar.showMessage(f"💡 提示: 执行{msg_suffix}需要商业授权，已为您调出激活窗口...", 3000)

            from src.gui.activation_dialog import ActivationDialog
            dlg = ActivationDialog(self)
            self._current_activation_dialog = dlg
            dlg.exec()
            self._current_activation_dialog = None

            # 重新检测授权状态
            auth_ok_now, auth_msg_now, lic_data_now = LicenseManager.is_system_authorized()
            self._refresh_license_status()

            if auth_ok_now:
                is_trial_now = lic_data_now.get("is_trial", False) if lic_data_now else False
                if not is_trial_now:
                    if hasattr(self, "status_bar"):
                        self.status_bar.showMessage(
                            "🎉 Commercial License activated! Thank you for your support."
                            if is_en else
                            "🎉 正式商业授权已成功激活！感谢您的支持。",
                            5000
                        )
                else:
                    if hasattr(self, "status_bar"):
                        self.status_bar.showMessage(
                            "⏱️ 7-Day Full-Feature Evaluation is active."
                            if is_en else
                            "⏱️ 7天全功能免费试用生效中。",
                            4000
                        )
                return True
            else:
                if hasattr(self, "status_bar"):
                    self.status_bar.showMessage(
                        "⚠️ Unactivated evaluation mode: action blocked. Please activate to continue."
                        if is_en else
                        "⚠️ 当前处于未激活评估模式，操作已被拦截。请激活后再试。",
                        4000
                    )
                return False
        finally:
            self._is_prompting_activation = False



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
        scroll.setMinimumWidth(380)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 4, 10, 4)
        layout.setSpacing(10)

        # 卡片 1: 线圈几何与排线参数
        grp_geo = QFrame()
        grp_geo.setProperty("class", "CardFrame")
        layout_geo = QVBoxLayout(grp_geo)
        layout_geo.setSpacing(6)
        self.lbl_geo = QLabel("▶ 线圈几何与排线参数")
        lbl_geo = self.lbl_geo
        lbl_geo.setProperty("class", "SectionTitle")
        layout_geo.addWidget(lbl_geo)

        self.lbl_type = QLabel("线圈拓扑类型:")
        lbl_type = self.lbl_type
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
        self.sb_inner_len = FloatSliderBox("线圈内长 (IL)", "mm", 0.2, 500.0, 4.86, 0.01)
        self.sb_inner_wid = FloatSliderBox("线圈内宽 (IW)", "mm", 0.1, 300.0, 1.50, 0.01)
        layout_geo.addWidget(self.sb_inner_len)
        layout_geo.addWidget(self.sb_inner_wid)

        # 八角形线圈专属面板 (严格遵循图4工程图规范)
        self.w_oct_panel = QFrame()
        layout_oct = QVBoxLayout(self.w_oct_panel)
        layout_oct.setContentsMargins(0, 0, 0, 0)
        layout_oct.setSpacing(4)
        self.lbl_oct_hint = QLabel("📐 图4规范: 4平直边 + 4斜边 + 8圆角 (配合四角三角磁钢)")
        lbl_oct_hint = self.lbl_oct_hint
        lbl_oct_hint.setStyleSheet("font-size: 10px; font-weight: 700; color: #0284C7; background: #F0F9FF; padding: 4px 6px; border-radius: 4px; border: 1px solid #BAE6FD;")
        layout_oct.addWidget(lbl_oct_hint)

        self.sb_oct_id1 = FloatSliderBox("对边内径 ID1", "mm", 0.5, 200.0, 7.10, 0.01)
        self.sb_oct_id2 = FloatSliderBox("对角内径 ID2", "mm", 0.5, 250.0, 7.05, 0.01)
        self.sb_oct_r1 = FloatSliderBox("拐角内圆角 R1", "mm", 0.01, 30.0, 0.30, 0.01)

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
        self.lbl_perim_hint = QLabel("📐 异形线圈周长推算: MLT = 展开内周长 + π × 绕组厚度")
        lbl_perim_hint = self.lbl_perim_hint
        lbl_perim_hint.setStyleSheet("font-size: 10px; font-weight: 700; color: #0D9488; background: #F0FDFA; padding: 4px 6px; border-radius: 4px; border: 1px solid #99F6E4;")
        layout_perim.addWidget(lbl_perim_hint)

        self.sb_perim_in = FloatSliderBox("展开内周长 C_in", "mm", 1.0, 2000.0, 20.0, 0.05)
        self.sb_perim_outer_len = FloatSliderBox("参考外廓长 Max_X", "mm", 1.0, 800.0, 7.0, 0.05)
        self.sb_perim_outer_wid = FloatSliderBox("参考外廓宽 Max_Y", "mm", 1.0, 800.0, 5.0, 0.05)

        self.sb_perim_in.valueChanged.connect(self.run_simulation)
        self.sb_perim_outer_len.valueChanged.connect(self.run_simulation)
        self.sb_perim_outer_wid.valueChanged.connect(self.run_simulation)

        layout_perim.addWidget(self.sb_perim_in)
        layout_perim.addWidget(self.sb_perim_outer_len)
        layout_perim.addWidget(self.sb_perim_outer_wid)
        self.w_perim_panel.setVisible(False)
        layout_geo.addWidget(self.w_perim_panel)

        self.sb_radial_layers = FloatSliderBox("径向层数", "层", 0.5, 300.0, 14.0, 0.5, decimals=1)
        self.sb_axial_turns = IntSliderBox("每层匝数", "匝", 1, 3000, 12)

        layout_geo.addWidget(self.sb_radial_layers)
        layout_geo.addWidget(self.sb_axial_turns)

        self.lbl_mode = QLabel("密排排法模式:")
        lbl_mode = self.lbl_mode
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
        self.sb_mold_height = FloatSliderBox("模具压实厚度", "mm", 0.05, 100.00, 0.55, 0.01, decimals=2)
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
        self.lbl_wire = QLabel("▶ 漆包线线材与张力")
        lbl_wire = self.lbl_wire
        lbl_wire.setProperty("class", "SectionTitle")
        layout_wire.addWidget(lbl_wire)

        # 1. 线材截面形态选择 (圆线 / 正方线 / 长方扁线)
        self.lbl_wire_shape = QLabel("线材截面形态:")
        self.lbl_wire_shape.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        layout_wire.addWidget(self.lbl_wire_shape)

        self.combo_wire_shape = QComboBox()
        self.combo_wire_shape.addItem("经典圆线 (Round Wire)", WireShape.ROUND)
        self.combo_wire_shape.addItem("正方形方线 (Square Wire)", WireShape.SQUARE)
        self.combo_wire_shape.addItem("长方形扁线 (Rectangular Flat)", WireShape.RECTANGULAR)
        self.combo_wire_shape.currentIndexChanged.connect(self._on_wire_shape_changed)
        layout_wire.addWidget(self.combo_wire_shape)

        # 2. 华冶线材出厂标准库选型 (专业弹窗形式，取代过长下拉菜单)
        self.lbl_wire_catalog = QLabel("线材出厂规格库选型 (非库内尺寸需咨询华冶定制):")
        self.lbl_wire_catalog.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 4px;")
        layout_wire.addWidget(self.lbl_wire_catalog)

        wire_btn_layout = QHBoxLayout()
        wire_btn_layout.setSpacing(6)

        self.btn_open_catalog = QPushButton("华冶线材库")
        self.btn_open_catalog.setToolTip("打开华冶漆包线出厂标准数据库（注：其他非材料库尺寸，需咨询华冶定制）")
        self.btn_open_catalog.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_catalog.setStyleSheet("""
            QPushButton {
                background-color: #F0F9FF;
                border: 1px solid #0284C7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                color: #0284C7;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0369A1;
                color: #0369A1;
            }
        """)
        self.btn_open_catalog.clicked.connect(self._open_wire_catalog_dialog)

        self.btn_incoming_wire = QPushButton("⚡ 来料参数")
        self.btn_incoming_wire.setToolTip("直接输入线材供应商出厂检验或进料实测参数：实测米阻 (Ω/m) 与 一公斤多少米 (km/kg)")
        self.btn_incoming_wire.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_incoming_wire.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                border: 1px solid #16A34A;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                color: #16A34A;
            }
            QPushButton:hover {
                background-color: #DCFCE7;
                border-color: #15803D;
                color: #15803D;
            }
        """)
        self.btn_incoming_wire.clicked.connect(self._open_incoming_wire_dialog)

        self.btn_reset_wire = QPushButton("✕ 自定义")
        self.btn_reset_wire.setToolTip("解除华冶出厂库锁定，恢复自由调整线径、外径与材质电导率")
        self.btn_reset_wire.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_wire.setVisible(False)
        self.btn_reset_wire.setStyleSheet("""
            QPushButton {
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #DC2626;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                border-color: #F87171;
                color: #B91C1C;
            }
        """)
        self.btn_reset_wire.clicked.connect(self._clear_catalog_wire)

        wire_btn_layout.addWidget(self.btn_open_catalog)
        wire_btn_layout.addWidget(self.btn_incoming_wire)
        wire_btn_layout.addWidget(self.btn_reset_wire)
        wire_btn_layout.addStretch()
        layout_wire.addLayout(wire_btn_layout)

        # 选定线规状态标签 (单独一行显示，防止挤压左侧输入框；鼠标悬停展示完整出厂/来料参数)
        self.lbl_catalog_selected = QLabel("已选: 自定义线规")
        self.lbl_catalog_selected.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #475569;
                padding: 4px 8px;
                background-color: #F8FAFC;
                border: 1px dashed #CBD5E1;
                border-radius: 4px;
                margin-top: 3px;
                margin-bottom: 2px;
            }
        """)
        self.lbl_catalog_selected.setWordWrap(True)
        self.lbl_catalog_selected.setToolTip("当前处于自定义线规模式（所有参数已解锁）。可通过【华冶线材库】或【⚡ 来料参数】快速导入标准数据。")
        layout_wire.addWidget(self.lbl_catalog_selected)

        # 3. 圆线专属参数容器
        self.container_round_wire = QWidget()
        layout_rw = QVBoxLayout(self.container_round_wire)
        layout_rw.setContentsMargins(0, 0, 0, 0)
        layout_rw.setSpacing(6)

        self.sb_bare_dia = FloatSliderBox("铜线裸径 (d)", "mm", 0.010, 3.500, 0.075, 0.001)
        self.sb_max_od = FloatSliderBox("漆包外径 (D)", "mm", 0.012, 4.000, 0.085, 0.001)
        layout_rw.addWidget(self.sb_bare_dia)
        layout_rw.addWidget(self.sb_max_od)
        layout_wire.addWidget(self.container_round_wire)

        # 4. 方线/扁线专属参数容器 (默认隐藏)
        self.container_flat_wire = QWidget()
        self.container_flat_wire.setVisible(False)
        layout_fw = QVBoxLayout(self.container_flat_wire)
        layout_fw.setContentsMargins(0, 0, 0, 0)
        layout_fw.setSpacing(6)

        self.sb_flat_w = FloatSliderBox("宽边宽度 (W)", "mm", 0.020, 15.000, 0.800, 0.005)
        self.sb_flat_h = FloatSliderBox("高边厚度 (H)", "mm", 0.020, 10.000, 0.350, 0.005)
        self.sb_flat_r = FloatSliderBox("倒圆角半径 (r)", "mm", 0.000, 5.000, 0.080, 0.005)
        self.sb_flat_w.valueChanged.connect(self._on_flat_dim_changed)
        self.sb_flat_h.valueChanged.connect(self._on_flat_dim_changed)
        self.sb_flat_r.valueChanged.connect(self._on_flat_dim_changed)

        self.lbl_flat_winding_dir = QLabel("扁线排线方向:")
        self.lbl_flat_winding_dir.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 4px;")
        self.combo_flat_winding_dir = QComboBox()
        self.combo_flat_winding_dir.addItem("平绕 / 卧绕 (Flatwise · 端面薄)", WindingDirection.FLATWISE)
        self.combo_flat_winding_dir.addItem("立绕 / 侧绕 (Edgewise · 高散热)", WindingDirection.EDGEWISE)
        self.combo_flat_winding_dir.currentIndexChanged.connect(self.run_simulation)

        self.lbl_flat_summary = QLabel("📐 真实截面: 0.273 mm² | 等效圆径: 0.590 mm")
        self.lbl_flat_summary.setStyleSheet("font-size: 10px; color: #0284C7; font-weight: 600; padding: 2px 0px;")

        layout_fw.addWidget(self.sb_flat_w)
        layout_fw.addWidget(self.sb_flat_h)
        layout_fw.addWidget(self.sb_flat_r)
        layout_fw.addWidget(self.lbl_flat_winding_dir)
        layout_fw.addWidget(self.combo_flat_winding_dir)
        layout_fw.addWidget(self.lbl_flat_summary)
        layout_wire.addWidget(self.container_flat_wire)

        # 5. 漆膜等级细化与自粘胶层
        self.lbl_enamel = QLabel("漆膜绝缘与自粘等级:")
        self.lbl_enamel.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 4px;")
        layout_wire.addWidget(self.lbl_enamel)

        self.combo_enamel_grade = QComboBox()
        self.combo_enamel_grade.addItem("常规标准自粘 (漆膜+胶厚 +0.010mm · +0.01 标配)", EnamelGrade.SB_010)
        self.combo_enamel_grade.addItem("薄胶复合自粘 (漆膜+胶厚 +0.008mm)", EnamelGrade.SB_008)
        self.combo_enamel_grade.addItem("加厚复合自粘 (漆膜+胶厚 +0.014mm · 2UEW-SB)", EnamelGrade.SB_014)
        self.combo_enamel_grade.addItem("0 级超薄漆膜 (非自粘 1UEW, 外径+0.003mm)", EnamelGrade.GRADE_0)
        self.combo_enamel_grade.addItem("1 级单涂层 (非自粘 1UEW, 外径+0.008mm)", EnamelGrade.GRADE_1)
        self.combo_enamel_grade.addItem("2 级加厚双涂层 (非自粘 2UEW, 外径+0.014mm)", EnamelGrade.GRADE_2)
        self.combo_enamel_grade.addItem("3 级特厚涂层 (非自粘 3UEW, 外径+0.022mm)", EnamelGrade.GRADE_3)
        self.combo_enamel_grade.addItem("自定义外径 (保持手动输入设定)", EnamelGrade.CUSTOM)
        self.combo_enamel_grade.setCurrentIndex(0) # 默认常规标准自粘 (+0.010mm)
        self.combo_enamel_grade.currentIndexChanged.connect(self._on_enamel_grade_changed)
        layout_wire.addWidget(self.combo_enamel_grade)

        self.chk_self_bonding = QCheckBox("复合热风/酒精自粘胶层 (Self-Bonding · 标配)")
        self.chk_self_bonding.setChecked(True) # 默认设定为自粘线 (脱模空心微特线圈标配)
        self.chk_self_bonding.setToolTip("【复合自粘线】采用华冶实测烘焙固化双层密度计算：内层 UEW (1.27 g/cm³) + 外层自粘胶 SB (1.07 g/cm³)")
        self.chk_self_bonding.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569; margin: 2px 0px;")
        self.chk_self_bonding.toggled.connect(self._on_self_bonding_toggled)
        layout_wire.addWidget(self.chk_self_bonding)

        # 6. 张力与材料电导率
        self.sb_tension = FloatSliderBox("张力拉伸系数", "系数", 0.70, 1.00, 0.99, 0.005)
        layout_wire.addWidget(self.sb_tension)

        self.lbl_rho = QLabel("导体材质与电导基准:")
        lbl_rho = self.lbl_rho
        lbl_rho.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155; margin-top: 4px;")
        layout_wire.addWidget(lbl_rho)

        self.combo_copper_grade = QComboBox()
        self.combo_copper_grade.addItem("纯铜 (华冶实测经验值)", (0.01709402, 8.90))
        self.combo_copper_grade.addItem("纯铜 (国标 100% IACS)", (0.01724138, 8.90))
        self.combo_copper_grade.addItem("无氧纯铜 (高纯退火态)", (0.01694915, 8.90))
        self.combo_copper_grade.addItem("15% 铜包铝 (CCAW 经验值)", (0.02525000, 3.63))
        self.combo_copper_grade.addItem("电工纯铝 (EC-1350)", (0.02826000, 2.70))
        self.combo_copper_grade.addItem("自定义实测电阻率...", (-1.0, 8.90))
        self.combo_copper_grade.currentIndexChanged.connect(self._on_copper_grade_changed)
        layout_wire.addWidget(self.combo_copper_grade)

        self.sb_copper_rho = FloatSliderBox("20℃材料电阻率", "Ω·mm²/m", 0.0100, 0.0500, 0.017094, 0.00001, decimals=6)
        self.sb_copper_rho.valueChanged.connect(self._on_copper_rho_slider_changed)
        layout_wire.addWidget(self.sb_copper_rho)

        layout.addWidget(grp_wire)

        # 卡片 3: 工作环境与散热条件
        grp_thermal = QFrame()
        grp_thermal.setProperty("class", "CardFrame")
        layout_thermal = QVBoxLayout(grp_thermal)
        layout_thermal.setSpacing(6)
        self.lbl_thermal = QLabel("▶ 工作环境与散热条件")
        lbl_thermal = self.lbl_thermal
        lbl_thermal.setProperty("class", "SectionTitle")
        layout_thermal.addWidget(lbl_thermal)

        self.lbl_env = QLabel("散热对流工况:")
        lbl_env = self.lbl_env
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

        self.sb_ambient_temp = FloatSliderBox("环境温度", "℃", -50.0, 180.0, 20.0, 0.5)
        self.sb_drive_current = FloatSliderBox("测试电流", "mA", 0.0, 20000.0, 10.0, 1.0)
        self.sb_convection_h = FloatSliderBox("散热对流系数", "W/(m²·K)", 1.0, 500.0, 25.0, 1.0)
        self.sb_convection_h.valueChanged.connect(self._on_convection_h_slider_changed)

        layout_thermal.addWidget(self.sb_ambient_temp)
        layout_thermal.addWidget(self.sb_drive_current)
        layout_thermal.addWidget(self.sb_convection_h)

        layout.addWidget(grp_thermal)

        # 卡片 4: 装配空间与公差约束 (DFM)
        self.grp_dfm = QFrame()
        self.grp_dfm.setProperty("class", "CardFrame")
        layout_dfm = QVBoxLayout(self.grp_dfm)
        layout_dfm.setSpacing(6)
        self.lbl_dfm_title = QLabel("▶ 装配空间与公差约束 (DFM)")
        lbl_dfm = self.lbl_dfm_title
        lbl_dfm.setProperty("class", "SectionTitle")
        layout_dfm.addWidget(lbl_dfm)

        # DFM 公差限值总开关 (默认关闭，自由调参不报警)
        self.chk_dfm_enabled = QCheckBox("启用 DFM 装配公差与限值检查")
        self.chk_dfm_enabled.setChecked(False)
        self.chk_dfm_enabled.setStyleSheet("font-size: 11px; font-weight: 700; color: #0284C7; margin-bottom: 4px;")
        self.chk_dfm_enabled.toggled.connect(self._on_dfm_enabled_toggled)
        layout_dfm.addWidget(self.chk_dfm_enabled)

        # 内部限值面板容器 (未勾选时置灰，直观展现自由设计状态)
        self.w_dfm_panel = QWidget()
        layout_dfm_panel = QVBoxLayout(self.w_dfm_panel)
        layout_dfm_panel.setContentsMargins(0, 0, 0, 0)
        layout_dfm_panel.setSpacing(6)

        self.sb_limit_x = FloatSliderBox("X向装配限值 (Max L)", "mm", 1.0, 600.0, 7.20, 0.05)
        self.sb_limit_y = FloatSliderBox("Y向装配限值 (Max W)", "mm", 1.0, 400.0, 3.82, 0.05)
        self.sb_limit_z = FloatSliderBox("Z向装配限高 (Max H)", "mm", 0.1, 150.0, 1.05, 0.02)
        self.sb_limit_v = FloatSliderBox("驱动电压上限 (Max V)", "V", 0.1, 120.0, 2.80, 0.05)

        # 漆包线绝缘耐温等级快捷选择
        self.lbl_temp_class = QLabel("漆包线耐温等级:")
        lbl_temp_class = self.lbl_temp_class
        lbl_temp_class.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        layout_dfm_panel.addWidget(lbl_temp_class)

        self.combo_temp_class = QComboBox()
        self.combo_temp_class.addItem("130级 (B级 / 130℃)", 130.0)
        self.combo_temp_class.addItem("155级 (F级 / 155℃)", 155.0)
        self.combo_temp_class.addItem("180级 (H级 / 180℃)", 180.0)
        self.combo_temp_class.addItem("200级 (C级 / 200℃)", 200.0)
        self.combo_temp_class.addItem("自定义耐温限值", None)
        self.combo_temp_class.setCurrentIndex(1)  # 默认 155级 (F级)
        self.combo_temp_class.currentIndexChanged.connect(self._on_temp_class_changed)
        layout_dfm_panel.addWidget(self.combo_temp_class)

        self.sb_limit_t = FloatSliderBox("耐温安全上限", "℃", 40.0, 350.0, 155.0, 5.0)
        self.sb_limit_t.valueChanged.connect(self._on_limit_t_slider_changed)

        layout_dfm_panel.addWidget(self.sb_limit_x)
        layout_dfm_panel.addWidget(self.sb_limit_y)
        layout_dfm_panel.addWidget(self.sb_limit_z)
        layout_dfm_panel.addWidget(self.sb_limit_v)
        layout_dfm_panel.addWidget(self.sb_limit_t)

        self.sb_withstand_ground = FloatSliderBox("对地/轭铁耐压要求", "VAC", 100, 20000, 3000, 100)
        self.sb_withstand_turn = FloatSliderBox("匝间冲击耐压要求", "V", 50, 10000, 1400, 50)
        self.sb_withstand_ground.valueChanged.connect(self.run_simulation)
        self.sb_withstand_turn.valueChanged.connect(self.run_simulation)
        layout_dfm_panel.addWidget(self.sb_withstand_ground)
        layout_dfm_panel.addWidget(self.sb_withstand_turn)

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

        self.lbl_twin_title = QLabel("▶ 仿真计算结果")
        lbl_twin_title = self.lbl_twin_title
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
        self.drawer = self.comparison_drawer
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
        """平滑滚动至左侧 DFM 装配公差与设计限值参数区"""
        self.scroll_left.ensureWidgetVisible(self.grp_dfm)
        self.status_bar.showMessage("已定位至左侧 DFM 装配公差与安全限值配置区", 3000)

    def _sync_grade_from_od(self):
        """当用户在自定义模式下调整裸径或外径时，自动智能对齐下拉框与自粘勾选，绝不篡改用户的外径数值"""
        if getattr(self, "_is_syncing_wire_grade", False):
            return
        if getattr(self, "_current_catalog_item", None) is not None:
            return
        if not hasattr(self, "sb_bare_dia") or not hasattr(self, "sb_max_od") or not hasattr(self, "combo_enamel_grade"):
            return

        bare = self.sb_bare_dia.value()
        od = self.sb_max_od.value()
        delta = round(od - bare, 4)
        has_sb = self.chk_self_bonding.isChecked() if hasattr(self, "chk_self_bonding") else True

        target_grade = EnamelGrade.CUSTOM
        target_sb = has_sb

        if abs(delta - 0.010) <= 0.0006:
            target_grade = EnamelGrade.SB_010
            target_sb = True
        elif abs(delta - 0.008) <= 0.0006:
            target_grade = EnamelGrade.SB_008 if has_sb else EnamelGrade.GRADE_1
        elif abs(delta - 0.014) <= 0.0006:
            target_grade = EnamelGrade.SB_014 if has_sb else EnamelGrade.GRADE_2
        elif abs(delta - 0.003) <= 0.0006:
            target_grade = EnamelGrade.GRADE_0
            target_sb = False
        elif abs(delta - 0.022) <= 0.0006:
            target_grade = EnamelGrade.GRADE_3
            target_sb = False
        else:
            target_grade = EnamelGrade.CUSTOM

        self._is_syncing_wire_grade = True
        try:
            for i in range(self.combo_enamel_grade.count()):
                if self.combo_enamel_grade.itemData(i) == target_grade:
                    self.combo_enamel_grade.blockSignals(True)
                    self.combo_enamel_grade.setCurrentIndex(i)
                    self.combo_enamel_grade.blockSignals(False)
                    break
            if hasattr(self, "chk_self_bonding") and self.chk_self_bonding.isChecked() != target_sb:
                self.chk_self_bonding.blockSignals(True)
                self.chk_self_bonding.setChecked(target_sb)
                self.chk_self_bonding.blockSignals(False)
        finally:
            self._is_syncing_wire_grade = False

    def _on_bare_dia_changed(self, bare_dia: float):
        """标称铜裸径变动响应"""
        curr_max_od = self.sb_max_od.value()
        if curr_max_od < bare_dia + 0.002:
            self.status_bar.showMessage(f"💡 提示: 标称外径 ({curr_max_od:.3f}mm) 应大于铜裸径 ({bare_dia:.3f}mm) 加漆膜厚度", 3000)
        self._sync_grade_from_od()
        self.run_simulation()

    def _on_max_od_changed(self, max_od: float):
        """标称最大外径变动响应 (绝不篡改用户的裸铜径输入)"""
        curr_bare = self.sb_bare_dia.value()
        if curr_bare > max_od - 0.002:
            self.status_bar.showMessage(f"💡 提示: 最大外径 ({max_od:.3f}mm) 需包含漆膜，求解器已进行物理安全自适应", 3000)
        self._sync_grade_from_od()
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
                    t("lbl_oct_derived", "📐 几何推导尺寸: 平直长 L1 = {l1:.2f} mm  |  斜边长 L2 = {l2:.2f} mm", l1=calc_l1, l2=calc_l2)
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

        is_en = i18n.is_english()
        if coil_type == CoilType.CIRCULAR:
            self.sb_inner_len.lbl_title.setText("Inner Diameter (ID)" if is_en else "线圈内径 (Inner Dia ID)")
            self.sb_inner_wid.lbl_title.setText("Inner Width (= ID)" if is_en else "线圈内宽 (圆线圈锁定为内径)")
            self.sb_inner_wid.setEnabled(False)
            self.sb_inner_wid.setValue(self.sb_inner_len.value())
            self.sb_limit_x.lbl_title.setText("Max Outer Dia (Max OD)" if is_en else "外径结构空间上限 (Max OD)")
            self.sb_limit_y.lbl_title.setText("Y Limit (= Max OD)" if is_en else "Y 空间上限 (圆线圈等同X向)")
            self.sb_limit_y.setEnabled(False)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText(t("lbl_limit_z", "Z向装配限高 (Max H)"))
        elif coil_type == CoilType.OCTAGONAL:
            self.sb_limit_x.lbl_title.setText("Max Flat Width (Max OD1)" if is_en else "X/对边外形空间上限 (Max X/OD1)")
            self.sb_limit_y.lbl_title.setText("Max Diag Width (Max OD2)" if is_en else "Y/对角外形空间上限 (Max Y/OD2)")
            self.sb_limit_y.setEnabled(True)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText(t("lbl_limit_z", "Z向装配限高 (Max H)"))
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
            self.sb_limit_x.lbl_title.setText("Ref Max X Limit" if is_en else "X 向参考装配上限 (Max X)")
            self.sb_limit_y.lbl_title.setText("Ref Max Y Limit" if is_en else "Y 向参考装配上限 (Max Y)")
            self.sb_limit_y.setEnabled(True)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText(t("lbl_limit_z", "Z向装配限高 (Max H)"))
            if hasattr(self, "sb_perim_outer_len") and self.sb_limit_x.value() < self.sb_perim_outer_len.value() + 1.0:
                self.sb_limit_x.setValue(max(9.00, round(self.sb_perim_outer_len.value() + 2.0, 2)))
                self.sb_limit_y.setValue(max(8.00, round(self.sb_perim_outer_wid.value() + 2.0, 2)))
        else:
            self.sb_inner_len.lbl_title.setText(t("lbl_inner_length", "线圈内长 (IL)"))
            self.sb_inner_wid.lbl_title.setText(t("lbl_inner_width", "线圈内宽 (IW)"))
            self.sb_inner_wid.setEnabled(True)
            self.sb_limit_x.lbl_title.setText(t("lbl_limit_x", "X向装配限值 (Max L)"))
            self.sb_limit_y.lbl_title.setText(t("lbl_limit_y", "Y向装配限值 (Max W)"))
            self.sb_limit_y.setEnabled(True)
            self.sb_limit_z.setEnabled(True)
            self.sb_limit_z.lbl_title.setText(t("lbl_limit_z", "Z向装配限高 (Max H)"))
            # 跑道型防呆：内长必须 >= 内宽
            if self.sb_inner_wid.value() > self.sb_inner_len.value():
                self.sb_inner_len.setValue(self.sb_inner_wid.value())
        self.run_simulation()

    def _on_wire_shape_changed(self, idx: int):
        """响应线材截面形态切换 (圆线 / 正方线 / 长方扁线)"""
        shape = self.combo_wire_shape.currentData()
        is_flat = (shape in (WireShape.SQUARE, WireShape.RECTANGULAR))
        is_square = (shape == WireShape.SQUARE)

        self.container_round_wire.setVisible(not is_flat)
        self.container_flat_wire.setVisible(is_flat)

        if is_flat:
            # 方线/扁线具有规整平直表面，工业上恒为正交同数矩阵排布 (i×j)，锁定并禁用圆线异数排布
            self.combo_mode.setCurrentIndex(1)  # WindingMode.EVEN 同数绕线
            self.combo_mode.setEnabled(False)
            self.combo_mode.setToolTip("方线与长方形扁线具备平直接触面，工艺上严格采用正交矩阵同数排布 (N=i×j)，无圆线异数交错模式")
        else:
            self.combo_mode.setEnabled(True)
            self.combo_mode.setToolTip("")

        if is_square:
            self.sb_flat_h.setVisible(False)
            self.sb_flat_w.lbl_title.setText(t("lbl_square_side", "正方边长 (a)"))
        else:
            self.sb_flat_h.setVisible(True)
            self.sb_flat_w.lbl_title.setText(t("lbl_flat_w", "宽边宽度 (W)"))
            self.sb_flat_h.lbl_title.setText(t("lbl_flat_h", "高边厚度 (H)"))

        self._on_flat_dim_changed()
        self.run_simulation()

    def _open_wire_catalog_dialog(self):
        """弹出华冶线材出厂标准数据库选型窗口"""
        from .wire_catalog_dialog import WireCatalogDialog
        curr_d = self.sb_bare_dia.value() if hasattr(self, "sb_bare_dia") else 0.080
        is_ccaw = getattr(self, "_is_current_wire_ccaw", False)
        mat_type = 2 if is_ccaw else 1

        dlg = WireCatalogDialog(current_diameter=curr_d, is_ccaw=is_ccaw, material_type=mat_type, parent=self)
        if dlg.exec():
            selected = dlg.selected_item
            if selected is not None:
                self._apply_catalog_wire(selected)

    def _open_incoming_wire_dialog(self):
        """打开线材来料实测参数输入弹窗"""
        from .incoming_wire_dialog import IncomingWireDialog
        d = self.sb_bare_dia.value() if hasattr(self, "sb_bare_dia") else 0.045
        od = self.sb_max_od.value() if hasattr(self, "sb_max_od") else 0.055
        rm = getattr(self, "_incoming_meter_res", 0.0)
        km_kg = getattr(self, "_catalog_km_kg", 0.0)
        has_sb = self.chk_self_bonding.isChecked() if hasattr(self, "chk_self_bonding") else True
        grade = self.combo_enamel_grade.currentData() if hasattr(self, "combo_enamel_grade") else EnamelGrade.SB_010

        dlg = IncomingWireDialog(
            current_bare_dia=d,
            current_max_od=od,
            current_rm=rm if rm > 0 else 10.747,
            current_km_kg=km_kg if km_kg > 0 else 70.620,
            has_self_bonding=has_sb,
            enamel_grade=grade,
            parent=self
        )
        dlg.params_applied.connect(self._apply_incoming_wire)
        dlg.exec()

    def _apply_incoming_wire(self, params):
        """应用来料实测参数到仿真"""
        self._current_catalog_item = None
        self._incoming_wire_params = params
        self._catalog_km_kg = params.km_per_kg
        self._incoming_meter_res = params.meter_resistance_ohm
        self._current_wire_density = params.density
        self._is_current_wire_ccaw = (params.density < 4.0)
        self._is_current_wire_ofc = ("无氧" in params.material_name)

        if hasattr(self, "sb_bare_dia"):
            self.sb_bare_dia.setValue(params.bare_dia)
            self.sb_bare_dia.setEnabled(False)
            self.sb_bare_dia.setToolTip(f"已锁定来料裸径: {params.bare_dia:.3f} mm")
        if hasattr(self, "sb_max_od"):
            self.sb_max_od.setValue(params.max_outer_dia)
            self.sb_max_od.setEnabled(False)
            self.sb_max_od.setToolTip(f"已锁定来料成品外径: {params.max_outer_dia:.3f} mm")
        if hasattr(self, "sb_copper_rho"):
            self.sb_copper_rho.setValue(params.resistivity)
            self.sb_copper_rho.setEnabled(False)
        if hasattr(self, "chk_self_bonding"):
            self.chk_self_bonding.blockSignals(True)
            self.chk_self_bonding.setChecked(params.has_self_bonding)
            self.chk_self_bonding.blockSignals(False)
        if hasattr(self, "combo_enamel_grade"):
            self.combo_enamel_grade.blockSignals(True)
            for i in range(self.combo_enamel_grade.count()):
                if self.combo_enamel_grade.itemData(i) == params.enamel_grade:
                    self.combo_enamel_grade.setCurrentIndex(i)
                    break
            self.combo_enamel_grade.setEnabled(False)
            self.combo_enamel_grade.blockSignals(False)

        if hasattr(self, "btn_reset_wire"):
            self.btn_reset_wire.setVisible(True)

        self.lbl_catalog_selected.setText(
            f"已锁定: 【来料实测】{params.meter_resistance_ohm:.3f}Ω/m | {params.km_per_kg:.2f}km/kg | 外径 {params.max_outer_dia:.3f}mm"
        )
        self.lbl_catalog_selected.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 700;
                color: #15803D;
                padding: 4px 8px;
                background-color: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 4px;
                margin-top: 3px;
                margin-bottom: 2px;
            }
        """)
        self.lbl_catalog_selected.setToolTip(
            f"【线材进料实测指标直接闭环】\n"
            f"实测米阻: {params.meter_resistance_ohm:.4f} Ω/m ({params.km_resistance_ohm:.1f} Ω/km)\n"
            f"线密度: {params.km_per_kg:.3f} km/kg (裸导体米重: {1000.0/params.km_per_kg:.5f} g/m)\n"
            f"公称裸径: {params.bare_dia:.3f} mm | 成品外径: {params.max_outer_dia:.3f} mm\n"
            f"材质: {params.material_name} (基准ρ={params.resistivity:.6f})\n"
            f"计算模型: 阻抗直接采用 L × {params.meter_resistance_ohm:.4f}Ω/m，导体重直接采用 L / {params.km_per_kg:.3f}km/kg"
        )
        self.status_bar.showMessage(f"已成功载入来料实测参数: {params.meter_resistance_ohm:.3f} Ω/m, {params.km_per_kg:.2f} km/kg", 3000)
        self.run_simulation()

    def _apply_catalog_wire(self, item: WireCatalogItem):
        """将选中的华冶线材出厂规格直接调入仿真引擎，并全面锁定冲突参数"""
        self._current_catalog_item = item
        self._catalog_km_kg = item.km_per_kg
        self._current_wire_density = item.density
        is_ccaw = ("铜包铝" in item.material_name)
        is_ofc = ("无氧" in item.material_name) or (abs(item.resistivity - 0.01694915) < 1e-5)
        self._is_current_wire_ccaw = is_ccaw
        self._is_current_wire_ofc = is_ofc
        self._is_current_wire_ccaw = is_ccaw

        # 1. 确保导线形状为经典圆线并锁定
        if hasattr(self, "combo_wire_shape"):
            self.combo_wire_shape.blockSignals(True)
            self.combo_wire_shape.setCurrentIndex(0) # 经典圆线
            self.combo_wire_shape.setEnabled(False)
            self.combo_wire_shape.setToolTip("华冶线规库为出厂圆线规格（如需方线/扁线请点击【✕ 自定义】）")
            self.combo_wire_shape.blockSignals(False)

        # 2. 自动填充裸径、外径与材料电阻率
        is_sb = self.chk_self_bonding.isChecked() if hasattr(self, "chk_self_bonding") else False
        eff_od = round(item.max_outer_dia + (0.006 if is_sb else 0.0), 4)

        self.sb_bare_dia.setValue(item.diameter)
        self.sb_max_od.setValue(eff_od)
        self.sb_copper_rho.setValue(item.resistivity)

        # 锁定裸径与外径，杜绝手动微调导致与出厂规格冲突
        self.sb_bare_dia.setEnabled(False)
        self.sb_bare_dia.setToolTip(f"已锁定华冶标准裸径 {item.diameter:.3f} mm")
        self.sb_max_od.setEnabled(False)
        self.sb_max_od.setToolTip(f"已锁定华冶外径 {'(1UEW-SB 含自粘胶)' if is_sb else '(1UEW 标准出厂)'} {eff_od:.3f} mm")

        # 3. 联动材料等级下拉框，智能防冲突联动 (铜线支持在纯铜与定制无氧铜之间自由比对)
        self.combo_copper_grade.blockSignals(True)
        if is_ccaw:
            self.combo_copper_grade.setCurrentIndex(3) # 15% 铜包铝
            self.combo_copper_grade.setEnabled(False)
            self.combo_copper_grade.setToolTip("已绑定华冶出厂 CCAW 材质（铝模具与铜模具不可混用）")
        elif is_ofc:
            self.combo_copper_grade.setCurrentIndex(2) # 无氧纯铜 (高纯退火态)
            self.combo_copper_grade.setEnabled(True)
            self.combo_copper_grade.setToolTip("当前为华冶定制无氧纯铜 (ρ=0.016949)；可在此快速切换比对普通纯铜 (ρ=0.017094)")
        else:
            self.combo_copper_grade.setCurrentIndex(0) # 纯铜 (华冶实测经验值)
            self.combo_copper_grade.setEnabled(True)
            self.combo_copper_grade.setToolTip("当前为华冶标准纯铜 (ρ=0.017094)；可在此快速切换比对定制无氧纯铜 (ρ=0.016949)")
        self.combo_copper_grade.blockSignals(False)
        self.sb_copper_rho.setEnabled(False)
        self.sb_copper_rho.setToolTip("已锁定出厂材质基准电阻率")

        # 4. 锁定漆膜基准等级，但保持自粘层选项可选（微特音圈常基于华冶基线加工 1UEW-SB 自粘线）
        if hasattr(self, "combo_enamel_grade"):
            self.combo_enamel_grade.blockSignals(True)
            self.combo_enamel_grade.setCurrentIndex(1) # 1 级 (单涂层 1UEW)
            self.combo_enamel_grade.setEnabled(False)
            self.combo_enamel_grade.setToolTip("华冶出厂规格表基准为 1UEW 漆膜（如需自定义漆膜等级请点击【✕ 自定义】）")
            self.combo_enamel_grade.blockSignals(False)
        if hasattr(self, "chk_self_bonding"):
            self.chk_self_bonding.setEnabled(True)
            self.chk_self_bonding.setToolTip("可根据需要切换华冶 1UEW 原厂线或 1UEW-SB 复合自粘线（勾选即叠加 0.006mm 自粘胶与 1.07g/cm³ 胶层重量）")

        # 5. 显示恢复自定义按钮与锁定微标
        if hasattr(self, "btn_reset_wire"):
            self.btn_reset_wire.setVisible(True)

        mat_short = "CCAW" if is_ccaw else ("无氧纯铜" if is_ofc else "纯铜")
        sb_tag = " 1UEW-SB" if is_sb else " 1UEW"
        info_text = f"已锁定: 【{mat_short}】 {item.diameter:.3f}mm (外径 {eff_od:.3f}mm{sb_tag} | {item.km_resistance_ohm:.1f}Ω/km | 裸铜 {item.km_per_kg:.2f}km/kg)"
        self.lbl_catalog_selected.setText(info_text)
        self.lbl_catalog_selected.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 700;
                color: #0369A1;
                padding: 4px 8px;
                background-color: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-radius: 4px;
                margin-top: 3px;
                margin-bottom: 2px;
            }
        """)
        self.lbl_catalog_selected.setToolTip(
            f"【华冶线材出厂规格 · 已全面锁定物理参数】\n"
            f"材质: {item.material_name}\n"
            f"公称裸径: {item.diameter:.3f} mm\n"
            f"基准外径: {item.max_outer_dia:.3f} mm (1UEW 标准)\n"
            f"当前外径: {eff_od:.3f} mm{sb_tag}\n"
            f"出厂KM阻值: {item.km_resistance_ohm:.1f} Ω/km\n"
            f"裸导体KM/KG: {item.km_per_kg:.3f} km/kg (裸导体米重: {1000.0/item.km_per_kg:.5f} g/m)\n"
            f"重量计算模型: 裸导体重(按华冶出厂标称KM/KG直接核算) + 固化漆膜/胶重(按华冶实测UEW 1.27/SB 1.07体积积分)\n"
            f"提示: 鼠标悬停可查看全部详细参数；点击【✕ 自定义】可随时一键解锁恢复。"
        )
        self.status_bar.showMessage(
            f"已载入华冶线材: {item.diameter:.3f}mm{sb_tag} | 阻值={item.km_resistance_ohm:.1f}Ω/km | 裸铜={item.km_per_kg:.3f}km/kg (已严谨计入漆胶重量)",
            3500
        )
        self.run_simulation()

    def _clear_catalog_wire(self):
        """解除华冶出厂库锁定，恢复自由自定义线规设计模式"""
        self._current_catalog_item = None
        self._incoming_wire_params = None
        self._incoming_meter_res = 0.0
        self._catalog_km_kg = 0.0
        self._is_current_wire_ccaw = False
        self._is_current_wire_ofc = False

        # 解锁全部参数与控件
        if hasattr(self, "combo_wire_shape"):
            self.combo_wire_shape.setEnabled(True)
            self.combo_wire_shape.setToolTip("")
        if hasattr(self, "sb_bare_dia"):
            self.sb_bare_dia.setEnabled(True)
            self.sb_bare_dia.setToolTip("")
        if hasattr(self, "sb_max_od"):
            self.sb_max_od.setEnabled(True)
            self.sb_max_od.setToolTip("")
        if hasattr(self, "combo_copper_grade"):
            self.combo_copper_grade.setEnabled(True)
            self.combo_copper_grade.setToolTip("")
        if hasattr(self, "sb_copper_rho"):
            self.sb_copper_rho.setEnabled(True)
            self.sb_copper_rho.setToolTip("")
        if hasattr(self, "combo_enamel_grade"):
            self.combo_enamel_grade.setEnabled(True)
            self.combo_enamel_grade.setToolTip("")
        if hasattr(self, "chk_self_bonding"):
            self.chk_self_bonding.setEnabled(True)
            self.chk_self_bonding.setToolTip("")

        if hasattr(self, "btn_reset_wire"):
            self.btn_reset_wire.setVisible(False)

        self.lbl_catalog_selected.setText("已选: 自定义线规")
        self.lbl_catalog_selected.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #475569;
                padding: 4px 8px;
                background-color: #F8FAFC;
                border: 1px dashed #CBD5E1;
                border-radius: 4px;
                margin-top: 3px;
                margin-bottom: 2px;
            }
        """)
        self.lbl_catalog_selected.setToolTip("当前处于自定义线规模式（所有参数已解锁）。可通过【华冶线材库】或【⚡ 来料参数】快速导入标准数据。")
        self.status_bar.showMessage("已恢复自由自定义线规设计模式（所有参数已解锁）", 3000)
        self.run_simulation()

    def _on_self_bonding_toggled(self, checked: bool):
        """响应自粘层勾选状态变动 (华冶库线材联动出厂外径，自定义线材绝不篡改外径)"""
        if getattr(self, "_current_catalog_item", None) is not None:
            item = self._current_catalog_item
            eff_od = round(item.max_outer_dia + (0.006 if checked else 0.0), 4)
            self.sb_max_od.setValue(eff_od)
            self.sb_max_od.setToolTip(f"已锁定华冶外径 {'(1UEW-SB 含自粘胶)' if checked else '(1UEW 标准出厂)'} {eff_od:.3f} mm")

            is_ccaw = getattr(self, "_is_current_wire_ccaw", False)
            is_ofc = getattr(self, "_is_current_wire_ofc", False)
            mat_short = "CCAW" if is_ccaw else ("无氧纯铜" if is_ofc else "纯铜")
            sb_tag = " 1UEW-SB" if checked else " 1UEW"
            info_text = f"已锁定: 【{mat_short}】 {item.diameter:.3f}mm (外径 {eff_od:.3f}mm{sb_tag} | {item.km_resistance_ohm:.1f}Ω/km | 裸铜 {item.km_per_kg:.2f}km/kg)"
            self.lbl_catalog_selected.setText(info_text)
            self.lbl_catalog_selected.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: 700;
                    color: #0369A1;
                    padding: 4px 8px;
                    background-color: #F0F9FF;
                    border: 1px solid #BAE6FD;
                    border-radius: 4px;
                    margin-top: 3px;
                    margin-bottom: 2px;
                }
            """)
            self.lbl_catalog_selected.setToolTip(
                f"【华冶线材出厂规格 · 已全面锁定物理参数】\n"
                f"材质: {item.material_name}\n"
                f"公称裸径: {item.diameter:.3f} mm\n"
                f"基准外径: {item.max_outer_dia:.3f} mm (1UEW 标准)\n"
                f"当前外径: {eff_od:.3f} mm{sb_tag}\n"
                f"出厂KM阻值: {item.km_resistance_ohm:.1f} Ω/km\n"
                f"裸导体KM/KG: {item.km_per_kg:.3f} km/kg (裸导体米重: {1000.0/item.km_per_kg:.5f} g/m)\n"
                f"重量计算模型: 裸导体重(按华冶出厂标称KM/KG直接核算) + 固化漆膜/胶重(按华冶实测UEW 1.27/SB 1.07体积积分)\n"
                f"提示: 鼠标悬停可查看全部详细参数；点击【✕ 自定义】可随时一键解锁恢复。"
            )
        else:
            # 自定义模式：绝不篡改用户手动输入设定的漆包外径！
            if getattr(self, "_is_syncing_wire_grade", False):
                return
            self._is_syncing_wire_grade = True
            try:
                curr_grade = self.combo_enamel_grade.currentData() if hasattr(self, "combo_enamel_grade") else None
                target_grade = curr_grade
                if checked:
                    if curr_grade == EnamelGrade.GRADE_1:
                        target_grade = EnamelGrade.SB_008
                    elif curr_grade == EnamelGrade.GRADE_2:
                        target_grade = EnamelGrade.SB_014
                else:
                    if curr_grade in (EnamelGrade.SB_010, EnamelGrade.SELF_BONDING):
                        target_grade = EnamelGrade.CUSTOM
                    elif curr_grade == EnamelGrade.SB_008:
                        target_grade = EnamelGrade.GRADE_1
                    elif curr_grade == EnamelGrade.SB_014:
                        target_grade = EnamelGrade.GRADE_2

                if target_grade is not None and target_grade != curr_grade:
                    for i in range(self.combo_enamel_grade.count()):
                        if self.combo_enamel_grade.itemData(i) == target_grade:
                            self.combo_enamel_grade.blockSignals(True)
                            self.combo_enamel_grade.setCurrentIndex(i)
                            self.combo_enamel_grade.blockSignals(False)
                            break
            finally:
                self._is_syncing_wire_grade = False

        self.run_simulation()

    def _on_enamel_grade_changed(self, idx: int):
        """漆膜等级变动联动外径预估 (仅在用户主动选择预设档位时按推荐值赋默认外径，选自定义外径则完全保留当前输入)"""
        if getattr(self, "_is_syncing_wire_grade", False):
            return
        if getattr(self, "_current_catalog_item", None) is not None:
            return  # 已锁定华冶标准出厂外径，跳过估算
        grade = self.combo_enamel_grade.currentData()
        if grade == EnamelGrade.CUSTOM:
            # 用户选择自定义：完全保留手动输入设定的外径，不作任何覆盖
            self.run_simulation()
            return

        if hasattr(self, "sb_bare_dia") and hasattr(self, "sb_max_od"):
            d = self.sb_bare_dia.value()
            inc_map = {
                EnamelGrade.SB_010: 0.010,
                EnamelGrade.SELF_BONDING: 0.010,
                EnamelGrade.SB_008: 0.008,
                EnamelGrade.SB_014: 0.014,
                EnamelGrade.GRADE_0: 0.003,
                EnamelGrade.GRADE_1: 0.008,
                EnamelGrade.GRADE_2: 0.014,
                EnamelGrade.GRADE_3: 0.022,
            }
            inc = inc_map.get(grade, 0.010)
            is_sb = grade in (EnamelGrade.SB_010, EnamelGrade.SELF_BONDING, EnamelGrade.SB_008, EnamelGrade.SB_014)

            self._is_syncing_wire_grade = True
            try:
                self.sb_max_od.setValue(round(d + inc, 4))
                if hasattr(self, "chk_self_bonding"):
                    self.chk_self_bonding.blockSignals(True)
                    self.chk_self_bonding.setChecked(is_sb)
                    self.chk_self_bonding.blockSignals(False)
            finally:
                self._is_syncing_wire_grade = False
        self.run_simulation()

    def _on_flat_dim_changed(self):
        """方线/扁线尺寸变动实时刷新面积与等效圆"""
        if not hasattr(self, "sb_flat_w") or not hasattr(self, "sb_flat_h"):
            return
        shape = self.combo_wire_shape.currentData() if hasattr(self, "combo_wire_shape") else WireShape.ROUND
        if shape == WireShape.SQUARE:
            w = self.sb_flat_w.value()
            h = w
        else:
            w = max(self.sb_flat_w.value(), self.sb_flat_h.value())
            h = min(self.sb_flat_w.value(), self.sb_flat_h.value())
        r = min(self.sb_flat_r.value(), h / 2.0)
        area = w * h - (4.0 - 3.14159265) * (r ** 2)
        d_eq = 2.0 * (area / 3.14159265) ** 0.5
        if hasattr(self, "lbl_flat_summary"):
            self.lbl_flat_summary.setText(f"📐 真实截面: {area:.4f} mm² | 等效圆径: {d_eq:.3f} mm")
        self.run_simulation()

    def _on_copper_grade_changed(self, idx: int):
        """响应导体电导率与材料等级切换 (严格华冶 5 档预设)"""
        if getattr(self, "_current_catalog_item", None) is not None:
            # 若当前为华冶铜线，支持在纯铜(0)、国标纯铜(1)与定制无氧纯铜(2)之间自由无缝比对切换
            if not getattr(self, "_is_current_wire_ccaw", False) and idx in (0, 1, 2):
                data = self.combo_copper_grade.currentData()
                if isinstance(data, tuple):
                    rho_val, density_val = data
                    self.sb_copper_rho.setValue(rho_val)
                    self._is_current_wire_ofc = (idx == 2)
                    item = self._current_catalog_item
                    is_sb = self.chk_self_bonding.isChecked() if hasattr(self, "chk_self_bonding") else False
                    eff_od = round(item.max_outer_dia + (0.006 if is_sb else 0.0), 4)
                    sb_tag = " 1UEW-SB" if is_sb else " 1UEW"
                    mat_short = "无氧纯铜" if idx == 2 else ("纯铜" if idx == 0 else "国标纯铜")
                    a_cu = 3.141592653589793 * (item.diameter / 2.0)**2
                    km_res = (1000.0 * rho_val) / a_cu if a_cu > 0 else 0.0
                    info_text = f"已锁定: 【{mat_short}】 {item.diameter:.3f}mm (外径 {eff_od:.3f}mm{sb_tag} | {km_res:.1f}Ω/km | 裸铜 {item.km_per_kg:.2f}km/kg)"
                    self.lbl_catalog_selected.setText(info_text)
                    self.lbl_catalog_selected.setStyleSheet("""
                        QLabel {
                            font-size: 11px;
                            font-weight: 700;
                            color: #0369A1;
                            padding: 4px 8px;
                            background-color: #F0F9FF;
                            border: 1px solid #BAE6FD;
                            border-radius: 4px;
                            margin-top: 3px;
                            margin-bottom: 2px;
                        }
                    """)
                    self.lbl_catalog_selected.setToolTip(
                        f"【华冶线材出厂规格 · {mat_short}】\n"
                        f"公称裸径: {item.diameter:.3f} mm\n"
                        f"当前外径: {eff_od:.3f} mm{sb_tag}\n"
                        f"当前KM阻值: {km_res:.1f} Ω/km (基准ρ={rho_val:.8f})\n"
                        f"裸导体KM/KG: {item.km_per_kg:.3f} km/kg (裸导体米重: {1000.0/item.km_per_kg:.5f} g/m)\n"
                        f"重量计算模型: 裸导体重(按华冶出厂标称KM/KG直接核算) + 固化漆膜/胶重(按华冶实测UEW 1.27/SB 1.07体积积分)\n"
                        f"提示: 鼠标悬停可查看全部详细参数；点击【✕ 自定义】可随时一键解锁恢复。"
                    )
                    self.run_simulation()
                return
            elif getattr(self, "_is_current_wire_ccaw", False) and idx == 3:
                return
            else:
                self.combo_copper_grade.blockSignals(True)
                self.combo_copper_grade.setCurrentIndex(2 if getattr(self, "_is_current_wire_ofc", False) else (3 if getattr(self, "_is_current_wire_ccaw", False) else 0))
                self.combo_copper_grade.blockSignals(False)
                self.status_bar.showMessage("华冶出厂模具系列受限：铜线与铝线/铜包铝不可直接混切，如需更换请点击【华冶线材库】重新选型。", 3500)
                return
        data = self.combo_copper_grade.currentData()
        if data is not None:
            if isinstance(data, tuple):
                rho_val, density_val = data
            elif isinstance(data, (int, float)):
                rho_val, density_val = float(data), 8.90
            else:
                rho_val, density_val = -1.0, 8.90

            if rho_val > 0:
                self.sb_copper_rho.setValue(rho_val)
                self._current_wire_density = density_val
        self.run_simulation()

    def _on_copper_rho_slider_changed(self):
        """响应用户手动滑动/输入实测电阻率"""
        if getattr(self, "_current_catalog_item", None) is not None:
            return # 已锁定华冶出厂材质电导率，跳过自定义
        curr_val = round(self.sb_copper_rho.value(), 6)
        self.combo_copper_grade.blockSignals(True)
        if abs(curr_val - 0.017094) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(0)
            self._current_wire_density = 8.90
        elif abs(curr_val - 0.017241) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(1)
            self._current_wire_density = 8.90
        elif abs(curr_val - 0.016949) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(2)
            self._current_wire_density = 8.90
        elif abs(curr_val - 0.025250) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(3)
            self._current_wire_density = 3.63
        elif abs(curr_val - 0.028260) < 1e-5:
            self.combo_copper_grade.setCurrentIndex(4)
            self._current_wire_density = 2.70
        else:
            self.combo_copper_grade.setCurrentIndex(5) # 自定义实测
        self.combo_copper_grade.blockSignals(False)
        self.run_simulation()
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
            wire_shape=self.combo_wire_shape.currentData() if hasattr(self, "combo_wire_shape") else WireShape.ROUND,
            wire_catalog_type=WireCatalogType.INCOMING_MEASURED if getattr(self, "_incoming_wire_params", None) is not None else (
                WireCatalogType.HUAYE_CCAW if getattr(self, "_is_current_wire_ccaw", False) else (
                    WireCatalogType.HUAYE_COPPER if getattr(self, "_catalog_km_kg", 0.0) > 0 else WireCatalogType.CUSTOM
                )
            ),
            enamel_grade=self.combo_enamel_grade.currentData() if hasattr(self, "combo_enamel_grade") else EnamelGrade.GRADE_2,
            has_self_bonding=self.chk_self_bonding.isChecked() if hasattr(self, "chk_self_bonding") else False,
            wire_density=getattr(self, "_current_wire_density", 8.90),
            catalog_km_kg=getattr(self, "_catalog_km_kg", 0.0),
            measured_rm=getattr(self, "_incoming_meter_res", 0.0),
            bare_dia=self.sb_bare_dia.value() if hasattr(self, "sb_bare_dia") else 0.075,
            max_od=self.sb_max_od.value() if hasattr(self, "sb_max_od") else 0.085,
            tension_factor=self.sb_tension.value() if hasattr(self, "sb_tension") else 0.99,
            copper_resistivity=self.sb_copper_rho.value() if hasattr(self, "sb_copper_rho") else 0.017094,
            flat_w=self.sb_flat_w.value() if hasattr(self, "sb_flat_w") else 0.80,
            flat_h=self.sb_flat_h.value() if hasattr(self, "sb_flat_h") else 0.35,
            flat_r=self.sb_flat_r.value() if hasattr(self, "sb_flat_r") else 0.08,
            flat_r_auto=(self.sb_flat_r.value() <= 0) if hasattr(self, "sb_flat_r") else True,
            flat_winding_dir=self.combo_flat_winding_dir.currentData() if hasattr(self, "combo_flat_winding_dir") else WindingDirection.FLATWISE,
            withstand_ground_vac=self.sb_withstand_ground.value() if hasattr(self, "sb_withstand_ground") else 3000.0,
            withstand_turn_v=self.sb_withstand_turn.value() if hasattr(self, "sb_withstand_turn") else 1400.0,
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
            is_en = i18n.is_english()
            is_circular = (self.inputs.coil_type == CoilType.CIRCULAR)
            is_oct = (self.inputs.coil_type == CoilType.OCTAGONAL)
            is_perim = (self.inputs.coil_type == CoilType.ARBITRARY_PERIMETER)

            if is_circular:
                self.card_ol.lbl_title.setText("Outer Dia (OD)" if is_en else "线圈外径 (OD)")
                self.card_ol.setValue(f"{self.outputs.outer_len:.3f}")
                self.card_ow.lbl_title.setText("Mean Dia (MD)" if is_en else "平均中径 (MD)")
                self.card_ow.setValue(f"{self.outputs.mean_dia_mm:.3f}")
            elif is_oct:
                self.card_ol.lbl_title.setText("Flat Width (OD1)" if is_en else "对边外宽 OD1")
                self.card_ol.setValue(f"{self.outputs.oct_od1:.3f}")
                self.card_ow.lbl_title.setText("Diag Width (OD2)" if is_en else "对角外宽 OD2")
                self.card_ow.setValue(f"{self.outputs.oct_od2:.3f}")
            elif is_perim:
                self.card_ol.lbl_title.setText("Ref Outer Len (L)" if is_en else "参考外长 (L)")
                self.card_ol.setValue(f"{self.outputs.outer_len:.3f}")
                self.card_ow.lbl_title.setText("Inner Perim (Cin)" if is_en else "展开内周长")
                self.card_ow.setValue(f"{self.outputs.c_inner_mm:.2f}")
            else:
                self.card_ol.lbl_title.setText(t("metric_outer_len", "外廓长度 (L)"))
                self.card_ol.setValue(f"{self.outputs.outer_len:.3f}")
                self.card_ow.lbl_title.setText(t("metric_outer_width", "外廓宽度 (W)"))
                self.card_ow.setValue(f"{self.outputs.outer_wid:.3f}")

            if self.outputs.is_mold_clamped:
                self.card_thk.lbl_title.setText("Clamped Height (H)" if is_en else "模压厚度 (H)")
                self.card_thk.setValue(f"{self.outputs.thickness_h:.3f}")
            else:
                self.card_thk.lbl_title.setText(t("metric_coil_height", "线圈厚度 (H)"))
                self.card_thk.setValue(f"{self.outputs.thickness_h:.3f}")

            # 动态更新模具压实厚度下限极限与安全提示
            if hasattr(self, "sb_mold_height") and self.outputs.h_solid_limit > 0:
                h_min = round(self.outputs.h_solid_limit, 2)
                h_safe = round(self.outputs.h_safe_min_limit, 2)
                if self.sb_mold_height.min_val != h_min:
                    self.sb_mold_height.min_val = h_min
                    self.sb_mold_height.slider.setMinimum(int(round(h_min * self.sb_mold_height.scale)))
                    self.sb_mold_height.spin.setMinimum(h_min)
                self.sb_mold_height.lbl_title.setText(
                    f"Die-Press Thk (≥{h_safe:.2f}mm)" if is_en else f"模具压实厚度 (≥{h_safe:.2f}mm)"
                )

            self.card_n.setValue(str(self.outputs.total_turns))

            # 20℃冷态电阻 (米阻展示于 Tooltip，标题极简纯粹)
            self.card_r20.lbl_title.setText(t("metric_dcr_20", "20℃直流电阻"))
            self.card_r20.setToolTip(
                f"[DC Resistance @20℃]\nCurrent R20: {self.outputs.r20:.3f} Ω\nSpecific Res: {self.outputs.rho_per_meter:.3f} Ω/m\nTotal Wire Length: {self.outputs.total_wire_len_m:.3f} m"
                if is_en else
                f"【20℃直流电阻】\n当前阻值: {self.outputs.r20:.3f} Ω\n标称米阻: {self.outputs.rho_per_meter:.3f} Ω/m\n线圈线长: {self.outputs.total_wire_len_m:.3f} m"
            )
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
            if is_en:
                self.card_weight.setToolTip(
                    f"[Coil Weight Dual-Baseline]\n"
                    f"Theoretical Nominal: {self.outputs.weight_theoretical_g:.4f} g\n"
                    f"  - Conductor Net: {self.outputs.weight_cu_g:.4f} g ({self.outputs.weight_cu_g/max(1e-5, self.outputs.weight_theoretical_g)*100:.1f}%)\n"
                    f"  - Enamel Film: {self.outputs.weight_ins_g:.4f} g ({self.outputs.weight_ins_g/max(1e-5, self.outputs.weight_theoretical_g)*100:.1f}%)\n"
                    f"Shop Floor Expected: {self.outputs.weight_actual_expected_g:.4f} g (with drawing tolerance & stretch)"
                )
            else:
                self.card_weight.setToolTip(
                    f"【线圈称重双基准明细 · 严谨计入漆膜/自粘胶重】\n"
                    f"理论公称总重: {self.outputs.weight_theoretical_g:.4f} g\n"
                    f"  - 导体裸重: {self.outputs.weight_cu_g:.4f} g ({self.outputs.weight_cu_g/max(1e-5, self.outputs.weight_theoretical_g)*100:.1f}%, 基准出厂米重)\n"
                    f"  - 绝缘/自粘胶净重: {self.outputs.weight_ins_g:.4f} g ({self.outputs.weight_ins_g/max(1e-5, self.outputs.weight_theoretical_g)*100:.1f}%, 华冶实测固化密度={self.outputs.insulation_density:.3f}g/cm³)\n"
                    f"  - 成品线真实千米米数: {self.outputs.finished_km_per_kg:.1f} km/kg (含漆膜/自粘层真实总重)\n"
                    f"车间实测预测重: {self.outputs.weight_actual_expected_g:.4f} g (考虑拉细负公差与张力拉伸)"
                )
            self.card_wire_fill.setValue(f"{self.outputs.wire_fill_factor:.2f}")
            self.card_cu_fill.setValue(f"{self.outputs.copper_fill_factor:.2f}")
            self.card_mlt.setValue(f"{self.outputs.mlt:.3f}")

            # 2. 刷新矢量画布
            self.canvas_widget.updateCoil(self.inputs, self.outputs)

            # 3. 刷新 DFM 红绿指示灯 (实时使用用户设定的卡控限值)
            self.dfm_strip.updateDFM(
                self.outputs.dfm, self.outputs.r20, self.outputs.total_turns,
                self.outputs.hi_pot_turn_passed, self.outputs.turn_safety_factor, self.outputs.turn_breakdown_voltage_v
            )

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
        self.status_bar.showMessage(
            f"✓ Restored all input parameters from [{snapshot.name}]!"
            if i18n.is_english() else
            f"✓ 已成功还原方案 [{snapshot.name}] 的全套输入参数！",
            3500
        )

    def _load_preset(self, name: str):
        """加载经典工业预设 (含匹配的模具空间限值)"""
        if getattr(self, "_initialization_done", False):
            if not self.check_authorization_or_prompt("切换工程预设"):
                if hasattr(self, "_current_preset_name") and self._current_preset_name:
                    self.combo_presets.blockSignals(True)
                    self.combo_presets.setCurrentText(self._current_preset_name)
                    self.combo_presets.blockSignals(False)
                return
            self._current_preset_name = name

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
        """保存算例工程文件 (.ansvcoil / .ansv / .json)"""
        is_en = i18n.is_english()
        if not self.check_authorization_or_prompt("Export File" if is_en else "导出工程文件"):
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        proj_name = self.get_project_name()
        clean_name = sanitize_filename_ascii(proj_name, fallback="Coil_Project")
        default_filename = f"{clean_name}_Coil_Project_{timestamp}.ansvcoil"
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Coil Project File" if is_en else "导出线圈工程文件", 
            default_filename, 
            "ANSV Coil Project (*.ansvcoil);;Legacy Case (*.ansv);;JSON File (*.json)"
            if is_en else
            "ANSV 线圈工程算例 (*.ansvcoil);;兼容算例 (*.ansv);;JSON 算例文件 (*.json)"
        )
        if not path:
            return
        data = {
            "version": "1.1.0",
            "file_type": "ANSV_COIL_PROJECT",
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
        self.status_bar.showMessage(
            f"Project case saved: {os.path.basename(path)}"
            if is_en else
            f"算例已成功原子持久化保存至: {os.path.basename(path)}",
            4000
        )

    def load_project_file(self, path: str) -> bool:
        """
        统一解析并装载工程算例文件 (.ansvcoil / .ansv / .json / .ansvschemes)
        支持界面按钮触发、启动命令行传入与 Windows 双击文件自动载入
        """
        is_en = i18n.is_english()
        if not path or not os.path.exists(path):
            return False
        try:
            # 兼容多种编码格式 (带BOM UTF-8, 纯UTF-8, GBK等)，杜绝解码崩溃
            raw_text = None
            for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
                try:
                    with open(path, "r", encoding=enc) as f:
                        raw_text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            if not raw_text:
                raise ValueError("Cannot read file content or file is empty")

            data = json.loads(raw_text)

            # 智能探测：若用户载入的是多方案比对集 (.ansvschemes 或含有 snapshots 结构)
            if data.get("file_type") == "ANSV_COIL_SCHEMES_BUNDLE" or "snapshots" in data or str(path).lower().endswith(".ansvschemes"):
                if hasattr(self, "comparison_drawer"):
                    self.comparison_drawer.import_schemes_file(path)
                    if hasattr(self.comparison_drawer, "set_expanded"):
                        self.comparison_drawer.set_expanded(True)
                    return True

            inp = data.get("inputs", {})
            if "project_name" in data and hasattr(self, "txt_project_name"):
                self.txt_project_name.setText(str(data["project_name"]))
            self._is_syncing_params = True
            try:
                # 兼容 int / str / enum 多种格式设置 coil_type
                c_type_val = parse_coil_type(inp.get("coil_type", 0))
                for i in range(self.combo_coil_type.count()):
                    if self.combo_coil_type.itemData(i) == c_type_val:
                        self.combo_coil_type.setCurrentIndex(i)
                        break

                self.sb_inner_len.setValue(float(inp.get("inner_len", 4.86)))
                self.sb_inner_wid.setValue(float(inp.get("inner_wid", 1.50)))
                self.sb_radial_layers.setValue(float(inp.get("radial_layers", 14)))
                self.sb_axial_turns.setValue(int(inp.get("axial_turns", 12)))
                self.sb_bare_dia.setValue(float(inp.get("bare_dia", 0.075)))
                self.sb_max_od.setValue(float(inp.get("max_od", 0.085)))
                self.sb_tension.setValue(float(inp.get("tension_factor", 0.99)))
                if hasattr(self, "sb_copper_rho"):
                    self.sb_copper_rho.setValue(float(inp.get("copper_resistivity", 0.016959)))
                self.sb_ambient_temp.setValue(float(inp.get("ambient_temp", 20.0)))
                self.sb_drive_current.setValue(float(inp.get("drive_current_ma", 10.0)))
                self.sb_convection_h.setValue(float(inp.get("convection_h", 25.0)))
                
                # DFM 限值恢复
                if hasattr(self, "chk_dfm_enabled"):
                    self.chk_dfm_enabled.setChecked(bool(inp.get("dfm_enabled", False)))
                self.sb_limit_x.setValue(float(inp.get("max_x_len_limit", 7.20)))
                self.sb_limit_y.setValue(float(inp.get("max_y_wid_limit", 3.82)))
                self.sb_limit_z.setValue(float(inp.get("max_z_h_limit", 1.05)))
                self.sb_limit_v.setValue(float(inp.get("max_v_term_limit", 2.80)))
                self.sb_limit_t.setValue(float(inp.get("max_temp_limit", 110.0)))

                # 异形线圈参数恢复
                if hasattr(self, "sb_oct_id1"):
                    self.sb_oct_id1.setValue(float(inp.get("oct_id1", 6.80)))
                if hasattr(self, "sb_oct_id2"):
                    self.sb_oct_id2.setValue(float(inp.get("oct_id2", 7.60)))
                if hasattr(self, "sb_oct_l1"):
                    self.sb_oct_l1.setValue(float(inp.get("oct_l1", 3.20)))
                if hasattr(self, "sb_oct_l2"):
                    self.sb_oct_l2.setValue(float(inp.get("oct_l2", 1.80)))
                if hasattr(self, "sb_oct_r1"):
                    self.sb_oct_r1.setValue(float(inp.get("oct_r1", 0.50)))
                if hasattr(self, "sb_perim_in"):
                    self.sb_perim_in.setValue(float(inp.get("perimeter_in", 22.0)))
                if hasattr(self, "sb_arb_outer_len"):
                    self.sb_arb_outer_len.setValue(float(inp.get("arbitrary_outer_len", 8.0)))
                if hasattr(self, "sb_arb_outer_wid"):
                    self.sb_arb_outer_wid.setValue(float(inp.get("arbitrary_outer_wid", 6.0)))

                mode_val = parse_winding_mode(inp.get("winding_mode", 1))
                for i in range(self.combo_mode.count()):
                    if self.combo_mode.itemData(i) == mode_val:
                        self.combo_mode.setCurrentIndex(i)
                        break
            finally:
                self._is_syncing_params = False

            # 强制同步工艺与几何防呆下限并触发求解
            c_type = self.combo_coil_type.currentData() if hasattr(self, "combo_coil_type") else CoilType.RACETRACK
            if c_type in (CoilType.RACETRACK, CoilType.CIRCULAR):
                self._on_inner_len_changed(self.sb_inner_len.value())
            self._on_bare_dia_changed(self.sb_bare_dia.value())
            self.run_simulation()
            if hasattr(self, "status_bar"):
                self.status_bar.showMessage(
                    f"Loaded coil project case: {os.path.basename(path)}"
                    if is_en else
                    f"已成功加载线圈算例: {os.path.basename(path)}",
                    4000
                )
            return True
        except Exception as e:
            if is_en:
                QMessageBox.critical(self, "Load Failed", f"Failed to parse coil project file:\n{str(e)}")
            else:
                QMessageBox.critical(self, "读取失败", f"无法解析线圈算例文件:\n{str(e)}")
            return False

    def _import_project(self):
        """导入算例工程文件"""
        is_en = i18n.is_english()
        if not self.check_authorization_or_prompt("Open Project Case" if is_en else "载入工程算例"):
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File" if is_en else "载入文件",
            "",
            "ANSV Project / Schemes (*.ansvcoil *.ansvschemes *.ansv *.json);;All Files (*.*)"
            if is_en else
            "ANSV 工程文件与方案集 (*.ansvcoil *.ansvschemes *.ansv *.json);;所有文件 (*.*)"
        )
        if not path:
            return
        self.load_project_file(path)

    def _export_report(self):
        """导出工程评审报表 (支持 Excel .xlsx 或 CSV)"""
        is_en = i18n.is_english()
        if not self.check_authorization_or_prompt("Export Engineering Report" if is_en else "导出工程评审报表"):
            return
        # 1. 弹出项目名称确认输入框，默认带出预设 Coli-Architect
        current_name = self.get_project_name()
        proj_name, ok = QInputDialog.getText(
            self, 
            "Export Engineering Report - Confirm Project Name" if is_en else "导出评审报告 - 确认项目名称", 
            "Enter project code/name (injected into filename & report header):" if is_en else "请输入工程项目名称 (将注入文件名与报表元数据):", 
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
        clean_name = sanitize_filename_ascii(proj_name, fallback="Coil_Simulation_Report")
        default_filename = f"{clean_name}_Coil_Simulation_Report_{timestamp}.xlsx"
        path, sel_filter = QFileDialog.getSaveFileName(
            self, 
            "Export Simulation Report" if is_en else "导出仿真报告", 
            default_filename, 
            "Excel Workbook (*.xlsx);;CSV Report (*.csv)"
            if is_en else
            "Excel 工作簿 (*.xlsx);;CSV 文本报表 (*.csv)"
        )
        if not path:
            return

        if path.lower().endswith(".xlsx") or "xlsx" in sel_filter.lower():
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            from ..export.report_excel import ExcelReportGenerator
            ExcelReportGenerator.generate(self.inputs, self.outputs, path, project_name=proj_name)
            if is_en:
                self.status_bar.showMessage(f"Excel engineering report exported: {os.path.basename(path)}", 4000)
                QMessageBox.information(self, "Export Successful", f"Electromagnetic coil multi-physics engineering report exported to:\n{path}")
            else:
                self.status_bar.showMessage(f"Excel 评审报告已成功导出: {os.path.basename(path)}", 4000)
                QMessageBox.information(self, "导出成功", f"线圈多物理场评审报告已导出至:\n{path}")
        else:
            self._export_csv_file(path, project_name=proj_name)

    def _export_csv_file(self, path: str, project_name: str = "Coli-Architect"):
        is_en = i18n.is_english()
        c_type = self.inputs.coil_type
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if is_en:
            if c_type == CoilType.CIRCULAR:
                c_type_name = "Circular Coil (VLRA / Speaker)"
                dim_row1 = f"Molded Outer Diameter (OD),{self.outputs.outer_len:.3f},mm"
                dim_row2 = f"Mean Winding Diameter (Dm),{self.outputs.mean_dia_mm:.3f},mm"
            elif c_type == CoilType.OCTAGONAL:
                c_type_name = "Octagonal Coil (AF / OIS VCM)"
                dim_row1 = f"Flat Outer Span (OD1),{self.outputs.oct_od1:.3f},mm"
                dim_row2 = f"Chamfer Outer Span (OD2),{self.outputs.oct_od2:.3f},mm"
            elif c_type == CoilType.ARBITRARY_PERIMETER:
                c_type_name = "Custom Perimeter Coil (CAD Solver)"
                dim_row1 = f"Inner Contour Perimeter (C_in),{self.outputs.c_inner_mm:.3f},mm"
                dim_row2 = f"Outer Contour Perimeter (C_out),{self.outputs.c_outer_mm:.3f},mm"
            else:
                c_type_name = "Racetrack Coil (VCM / LRA)"
                dim_row1 = f"Molded Outer Length (OL),{self.outputs.outer_len:.3f},mm"
                dim_row2 = f"Molded Outer Width (OW),{self.outputs.outer_wid:.3f},mm"

            lines = [
                "Coil-Architect Pro - Engineering Simulation Report",
                f"Project Name,{project_name}",
                f"Export Timestamp,{now_str}",
                "Official Platform,ansv.net (ANSV Micro-Actuator & Precision Drive Platform)",
                f"Coil Topology Type,{c_type_name}",
                f"Effective Total Turns (N),{self.outputs.total_turns},turns",
                dim_row1,
                dim_row2,
                f"Z-Axis Thickness (H),{self.outputs.thickness_h:.3f},mm",
                f"Copper Resistivity (ρ_cu),{self.inputs.copper_resistivity:.6f},Ω·mm²/m",
                f"Nominal Resistance per Meter (R/m),{self.outputs.rho_per_meter:.4f},Ω/m",
                f"20℃ Cold Resistance (R20),{self.outputs.r20:.4f},Ω",
                f"Ambient Cold Resistance (R_init),{self.outputs.r_init:.4f},Ω",
                f"Steady-State Hot Resistance (DCR_hot),{self.outputs.dcr_hot:.4f},Ω",
                f"Wheeler Air-Core Inductance (L),{self.outputs.inductance_uh:.2f},μH",
                f"Magnetomotive Force (ΣI),{self.outputs.ampere_turns:.2f},AT",
                f"Required Terminal Voltage (V_term),{self.outputs.v_term:.4f},V",
                f"Steady-State Joule Power (Power),{self.outputs.joule_power_mw:.2f},mW",
                f"Final Steady-State Temp (T_final),{self.outputs.t_final:.2f},℃",
                f"Enamel Wire Fill Factor (Wire Fill),{self.outputs.wire_fill_factor:.2f},%",
                f"Bare Copper Fill Factor (Cu Fill),{self.outputs.copper_fill_factor:.2f},%",
                f"Coil Net Weight (Weight),{self.outputs.weight_g:.4f},g",
                f"Mean Length per Turn (MLT),{self.outputs.mlt:.3f},mm",
                f"DFM Tolerance Verdict,{'ALL PASSED' if self.outputs.dfm.all_passed else 'OVER LIMIT'}"
            ]
            atomic_write_text(Path(path), "\n".join(lines), encoding="utf-8-sig")
            self.status_bar.showMessage(f"CSV report exported: {os.path.basename(path)}", 4000)
            QMessageBox.information(self, "Export Successful", f"Electromagnetic coil CSV engineering report exported to:\n{path}")
        else:
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
                f"DFM制造公差状态,{ '全部合格' if self.outputs.dfm.all_passed else '存在超差项' }"
            ]
            atomic_write_text(Path(path), "\n".join(lines), encoding="utf-8-sig")
            self.status_bar.showMessage(f"CSV 报表已成功原子持久化导出: {os.path.basename(path)}", 4000)
            QMessageBox.information(self, "导出成功", f"线圈多物理场 CSV 评审报告已导出至:\n{path}")
