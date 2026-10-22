"""
Coil-Architect Pro - DFM Status Indicator Widget
DFM 结构空间与电气安全卡控芯片条 (交通灯红绿状态联动 · 中英双语自适应)
"""

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from ...core.models import DFMCheckResult
from src.core.i18n import i18n, t


class DFMChip(QFrame):
    """单个 DFM 监测状态芯片"""

    def __init__(self, name: str, default_limit: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.limit_str = default_limit
        self.setObjectName("DFMChip")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self.setFixedHeight(28)

        self.setStyleSheet("""
            #DFMChip {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
            #DFMChip QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        # 状态指示圆点 / 图标 (固定宽度，左侧严格对齐，绝不占据额外宽度挤压文字)
        self.dot = QLabel("●")
        self.dot.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.dot.setFixedWidth(14)
        self.dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dot.setStyleSheet("color: #059669; font-size: 11px; background: transparent; border: none;")

        # 文字描述 (设为 Preferred 尺寸策略，紧随图标左对齐展开，杜绝前部空白与末尾截断)
        self.lbl_text = QLabel(f"{name}: {default_limit}")
        self.lbl_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_text.setStyleSheet("font-size: 10px; font-weight: 600; color: #334155; background: transparent; border: none;")

        layout.addWidget(self.dot)
        layout.addWidget(self.lbl_text)
        layout.addStretch()  # 弹性空间置于最右侧，确保左侧图文紧凑左对齐

    def setStatus(self, passed: bool, curr_val: float, limit_val: float, unit: str, enabled: bool = True):
        is_en = i18n.is_english()
        val_str = f"{curr_val:.3f}" if unit == "mm" else f"{curr_val:.2f}"
        if not enabled:
            self.dot.setText("○")
            self.dot.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent; border: none;")
            self.setStyleSheet("""
                #DFMChip {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                }
                #DFMChip QLabel {
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            if is_en:
                self.lbl_text.setText(f"{self.name}: {val_str}{unit} (Ref {limit_val:.2f})")
                self.setToolTip(f"[{self.name}]\nCurrent: {curr_val:.3f} {unit}\nReference Limit: {limit_val:.2f} {unit}\nStatus: Free Design Mode (DFM Limits Off)")
            else:
                self.lbl_text.setText(f"{self.name}: {val_str}{unit} (参考{limit_val:.2f})")
                self.setToolTip(f"【{self.name}】\n当前值: {curr_val:.3f} {unit}\n参考空间: {limit_val:.2f} {unit}\n状态: 自由设计模式 (DFM 卡限未开启)")
            self.lbl_text.setStyleSheet("font-size: 10px; font-weight: 500; color: #64748B; background: transparent; border: none;")
        elif passed:
            self.dot.setText("●")
            self.dot.setStyleSheet("color: #059669; font-size: 11px; background: transparent; border: none;")
            self.setStyleSheet("""
                #DFMChip {
                    background-color: #F0FDF4;
                    border: 1px solid #BBF7D0;
                    border-radius: 6px;
                }
                #DFMChip QLabel {
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            self.lbl_text.setText(f"{self.name}: {val_str}{unit} (≤{limit_val:.2f})")
            self.lbl_text.setStyleSheet("font-size: 10px; font-weight: 600; color: #166534; background: transparent; border: none;")
            if is_en:
                self.setToolTip(f"[{self.name}]\nCurrent: {curr_val:.3f} {unit}\nMax Limit: {limit_val:.2f} {unit}\nMargin: {limit_val - curr_val:+.3f} {unit}\nStatus: Passed ✓")
            else:
                self.setToolTip(f"【{self.name}】\n当前值: {curr_val:.3f} {unit}\n装配上限: {limit_val:.2f} {unit}\n余量: {limit_val - curr_val:+.3f} {unit}\n状态: 合格通过 ✓")
        else:
            self.dot.setText("✖")
            self.dot.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: bold; background: transparent; border: none;")
            self.setStyleSheet("""
                #DFMChip {
                    background-color: #FEF2F2;
                    border: 1px solid #FECACA;
                    border-radius: 6px;
                }
                #DFMChip QLabel {
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            if is_en:
                self.lbl_text.setText(f"{self.name} Over: {val_str}{unit} (Max {limit_val:.2f})")
                self.setToolTip(f"[{self.name}]\nCurrent: {curr_val:.3f} {unit}\nMax Limit: {limit_val:.2f} {unit}\nExceeded by: {curr_val - limit_val:+.3f} {unit}\nStatus: 🚨 Limit Exceeded! Adjust parameters.")
            else:
                self.lbl_text.setText(f"{self.name}超标: {val_str}{unit} (限{limit_val:.2f})")
                self.setToolTip(f"【{self.name}】\n当前值: {curr_val:.3f} {unit}\n卡控上限: {limit_val:.2f} {unit}\n超标量: {curr_val - limit_val:+.3f} {unit}\n状态: 🚨 严重超差，请调校参数！")
            self.lbl_text.setStyleSheet("font-size: 10px; font-weight: 700; color: #991B1B; background: transparent; border: none;")

    def setAdaptiveStatus(self, curr_val: float, recommend_envelope: float, unit: str):
        """Z-LRA 专用：自适应免卡控状态展示 (提示线圈占位与线圈距磁轭 0.58mm 推荐总净空)"""
        is_en = i18n.is_english()
        val_str = f"{curr_val:.3f}" if unit == "mm" else f"{curr_val:.2f}"
        self.dot.setText("●")
        self.dot.setStyleSheet("color: #0284C7; font-size: 11px; background: transparent; border: none;")
        self.setStyleSheet("""
            #DFMChip {
                background-color: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-radius: 6px;
            }
            #DFMChip QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        if is_en:
            self.lbl_text.setText(f"{self.name}: {val_str}{unit} (Rec ≥{recommend_envelope:.2f})")
            self.setToolTip(f"[{self.name}]\nCoil Thickness: {curr_val:.3f} {unit}\nRecommended Clearance: ≥{recommend_envelope:.2f} {unit} (incl. 0.58mm yoke gap)\nStatus: Adaptive Mode")
        else:
            self.lbl_text.setText(f"{self.name}: {val_str}{unit} (推荐≥{recommend_envelope:.2f})")
            self.setToolTip(f"【{self.name}】\n当前线圈厚度: {curr_val:.3f} {unit}\n推荐总净空: ≥{recommend_envelope:.2f} {unit} (含距磁轭 0.58mm)\n状态: 自适应免卡控模式")
        self.lbl_text.setStyleSheet("font-size: 10px; font-weight: 600; color: #0369A1; background: transparent; border: none;")

    def minimumSizeHint(self) -> QSize:
        return QSize(60, 26)


class DFMStatusStrip(QFrame):
    """装配空间与安全卡控整体横条"""

    settingsClicked = pyqtSignal()

    def minimumSizeHint(self) -> QSize:
        return QSize(350, 60)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DFMStatusStrip")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self.setMinimumHeight(66)
        self.setStyleSheet("""
            QFrame#DFMStatusStrip {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)

        # 顶行：标题、设置按钮与全局汇总状态
        header_layout = QHBoxLayout()
        self.title_lbl = QLabel("🛡 结构装配与 DFM 制造公差")
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #0284C7;")
        header_layout.addWidget(self.title_lbl)

        self.btn_cfg = QPushButton("⚙ 公差与限值设置")
        self.btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cfg.setToolTip("点击快速定位至左侧 DFM 装配公差与安全限值配置区")
        self.btn_cfg.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                color: #0284C7;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                border-color: #0284C7;
            }
        """)
        self.btn_cfg.clicked.connect(self.settingsClicked.emit)
        header_layout.addWidget(self.btn_cfg)

        header_layout.addSpacing(16)

        self.summary_lbl = QLabel("✔ 求解完成 | DFM 尺寸与公差全部合格")
        self.summary_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.summary_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #059669;")
        header_layout.addWidget(self.summary_lbl)

        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # 芯片行 (名称简洁无冗余括号，紧凑左对齐)
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        self.chip_x = DFMChip("X向", "≤7.20mm")
        self.chip_y = DFMChip("Y向", "≤3.82mm")
        self.chip_z = DFMChip("Z向", "≤1.05mm")
        self.chip_v = DFMChip("端压", "≤2.80V")
        self.chip_t = DFMChip("耐温", "≤155℃")

        chips_layout.addWidget(self.chip_x)
        chips_layout.addWidget(self.chip_y)
        chips_layout.addWidget(self.chip_z)
        chips_layout.addWidget(self.chip_v)
        chips_layout.addWidget(self.chip_t)

        main_layout.addLayout(chips_layout)

    def retranslate_ui(self):
        """动态多语言刷新"""
        if hasattr(self, "title_lbl"):
            self.title_lbl.setText(t("dfm_section_title", "🛡 结构装配与 DFM 制造公差"))
        if hasattr(self, "btn_cfg"):
            self.btn_cfg.setText(t("btn_dfm_settings", "⚙ 公差与限值设置"))
            self.btn_cfg.setToolTip(t("btn_dfm_settings_tip", "点击快速定位至左侧 DFM 装配公差与安全限值配置区"))
        if hasattr(self, "chip_x"):
            self.chip_x.name = t("dfm_chip_x", "X向")
            self.chip_y.name = t("dfm_chip_y", "Y向")
            self.chip_z.name = t("dfm_chip_z", "Z向")
            self.chip_v.name = t("dfm_chip_v", "端压")
            self.chip_t.name = t("dfm_chip_t", "耐温")
        if hasattr(self, "_last_dfm_data"):
            d, r, trn = self._last_dfm_data
            self.updateDFM(d, r, trn)

    def updateDFM(self, dfm: DFMCheckResult, r20: float, turns: int):
        self._last_dfm_data = (dfm, r20, turns)
        is_en = i18n.is_english()
        if hasattr(self, "chip_x"):
            self.chip_x.name = t("dfm_chip_x", "X向")
            self.chip_y.name = t("dfm_chip_y", "Y向")
            self.chip_z.name = t("dfm_chip_z", "Z向")
            self.chip_v.name = t("dfm_chip_v", "端压")
            self.chip_t.name = t("dfm_chip_t", "耐温")
        is_enabled = getattr(dfm, "enabled", False)
        self.chip_x.setStatus(dfm.x_passed, dfm.x_val, dfm.x_limit, "mm", enabled=is_enabled)
        self.chip_y.setStatus(dfm.y_passed, dfm.y_val, dfm.y_limit, "mm", enabled=is_enabled)

        # Z 向自适应状态分流
        if getattr(dfm, "z_adaptive", False):
            self.chip_z.setAdaptiveStatus(dfm.z_val, dfm.z_limit, "mm")
        else:
            self.chip_z.setStatus(dfm.z_passed, dfm.z_val, dfm.z_limit, "mm", enabled=is_enabled)

        self.chip_v.setStatus(dfm.voltage_passed, dfm.voltage_val, dfm.voltage_limit, "V", enabled=is_enabled)
        self.chip_t.setStatus(dfm.temp_passed, dfm.temp_val, dfm.temp_limit, "°C" if is_en else "℃", enabled=is_enabled)

        if not is_enabled:
            if is_en:
                self.summary_lbl.setText(f"✔ Solved | R20 = {r20:.3f} Ω | Turns = {turns} T | Free Parameter Mode (DFM Limits Off)")
            else:
                self.summary_lbl.setText(f"✔ 求解完成 | R20 = {r20:.3f} Ω | 匝数 = {turns} 匝 | 自由参数模式 (DFM限值未开启)")
            self.summary_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #0284C7;")
        elif dfm.all_passed:
            self.summary_lbl.setText(t("dfm_all_passed", "✔ 求解完成 | R20 = {r20:.3f} Ω | 匝数 = {turns} 匝 | DFM 尺寸与公差全部合格", r20=r20, turns=turns))
            self.summary_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #059669;")
        else:
            self.summary_lbl.setText(t("dfm_warning", "⚠ 警告：存在尺寸干涉或超出设计限值，请调整参数！"))
            self.summary_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #DC2626;")
