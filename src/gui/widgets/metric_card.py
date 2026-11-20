"""
Coil-Architect Pro - Metric Card Widget
孪生总线高对比度 KPI 指标卡片
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy


class MetricCard(QFrame):
    """单项 KPI 数字指标卡 (防布局挤压 + 纯白高质感工程释义 ToolTip)"""

    def __init__(
        self, 
        title: str, 
        unit: str = "", 
        accent_color: str = "#0F172A",
        bg_color: str = "#FFFFFF",
        border_color: str = "#E2E8F0",
        tooltip: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.accent_color = accent_color
        self.bg_color = bg_color
        self.border_color = border_color
        self.unit = unit
        
        self.setObjectName("MetricCard")
        self.setMinimumHeight(58)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        # 标题 (锁定宽度伸缩策略为 Ignored，彻底禁止长文本挤压父级 Splitter 分割栏)
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("metricCardTitle")
        self.lbl_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_title.setMinimumWidth(0)
        layout.addWidget(self.lbl_title)

        # 数值与单位行
        val_layout = QHBoxLayout()
        val_layout.setSpacing(4)
        val_layout.setContentsMargins(0, 0, 0, 0)
        val_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_val = QLabel("--")
        self.lbl_val.setObjectName("metricCardVal")
        self.lbl_val.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.lbl_val.setMinimumWidth(30)

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setObjectName("metricCardUnit")

        val_layout.addWidget(self.lbl_val)
        val_layout.addWidget(self.lbl_unit)
        val_layout.addStretch()

        layout.addLayout(val_layout)

        self.is_dark = False
        self._default_accent_color = accent_color
        self._update_style()

        if tooltip:
            self.setToolTip(tooltip)

    def set_dark_mode(self, is_dark: bool):
        """动态切换深/浅色模式 (对齐 ansv.net 纯正深色卡片)"""
        self.is_dark = is_dark
        if is_dark:
            self.bg_color = "#13131E"
            self.border_color = "#262638"
        else:
            self.bg_color = "#FFFFFF"
            self.border_color = "#E2E8F0"
        self._update_style()

    def _update_style(self):
        """统一在卡片容器级注入严格作用域 QSS，杜绝子标签无选择器内联样式污染 QTipLabel 导致黑底与字号突变"""
        is_dark = getattr(self, "is_dark", False)
        title_color = "#8888A8" if is_dark else "#64748B"
        unit_color = "#8888A8" if is_dark else "#475569"
        hover_bg = "#1A1A28" if is_dark else "#F8FAFC"
        hover_border = "#38BDF8" if is_dark else "#0284C7"
        
        # 优化深色模式下的默认深色强调色对比度
        val_color = getattr(self, "accent_color", "#0F172A")
        if is_dark:
            if val_color in ["#0F172A", "#1E293B", "#334155"]:
                val_color = "#E8E8F0"
            elif val_color == "#D97706":  # 琥珀黄明亮化
                val_color = "#F59E0B"
            elif val_color == "#DC2626":  # 珊瑚红明亮化
                val_color = "#EF4444"
            elif val_color == "#7C3AED":  # 紫色明亮化 (对齐 ansv.net 极光紫)
                val_color = "#A78BFA"
        else:
            val_color = getattr(self, "_default_accent_color", val_color)

        tooltip_bg = "#1A1A28" if is_dark else "#FFFFFF"
        tooltip_text = "#E8E8F0" if is_dark else "#0F172A"
        tooltip_border = "#7C6AF7" if is_dark else "#0284C7"

        self.setStyleSheet(f"""
            QFrame#MetricCard {{
                background-color: {self.bg_color};
                border: 1px solid {self.border_color};
                border-radius: 8px;
            }}
            QFrame#MetricCard:hover {{
                border: 1px solid {hover_border};
                background-color: {hover_bg};
            }}
            QLabel#metricCardTitle {{
                font-size: 11px;
                font-weight: 600;
                color: {title_color};
                background: transparent;
                border: none;
                padding: 0px;
            }}
            QLabel#metricCardVal {{
                font-size: 18px;
                font-weight: 700;
                color: {val_color};
                font-family: 'Consolas', 'Courier New', monospace;
                background: transparent;
                border: none;
                padding: 0px;
            }}
            QLabel#metricCardUnit {{
                font-size: 12px;
                font-weight: 600;
                color: {unit_color};
                background: transparent;
                border: none;
                padding: 0px;
            }}
            QToolTip {{
                background-color: {tooltip_bg};
                color: {tooltip_text};
                border: 1px solid {tooltip_border};
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 11px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }}
        """)

    def setToolTip(self, text: str):
        """为卡片底板注入悬停工程释义 (子控件不设独立 ToolTip，统一冒泡由卡片纯白底座渲染，彻底杜绝黑底与字号突变)"""
        super().setToolTip(text)
        self.lbl_title.setToolTip("")
        self.lbl_val.setToolTip("")
        self.lbl_unit.setToolTip("")

    def setTitle(self, title: str):
        self.lbl_title.setText(str(title))

    def setUnit(self, unit: str):
        self.unit = str(unit)
        self.lbl_unit.setText(str(unit))

    def setValue(self, value_text: str):
        self.lbl_val.setText(str(value_text))

    def setAccentColor(self, color: str):
        self.accent_color = color
        self._update_style()

