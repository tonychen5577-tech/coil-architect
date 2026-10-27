"""
Coil-Architect Pro - Linked Slider & SpinBox Widgets
高精度浮点与整型滑块-数字框双向联动控件 (含滚轮防误触与范围约束)
"""

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QSlider, QDoubleSpinBox, QSpinBox, QScrollArea
)


class NoWheelSlider(QSlider):
    """防误触工业滑块：禁止滚轮直接改变滑块数值，将滚轮平滑滚动传递给页面滚动条"""
    def wheelEvent(self, event):
        parent = self.parentWidget()
        while parent:
            if isinstance(parent, QScrollArea):
                delta = event.angleDelta().y()
                bar = parent.verticalScrollBar()
                if bar and delta != 0:
                    bar.setValue(bar.value() - delta // 2)
                event.accept()
                return
            parent = parent.parentWidget()
        event.ignore()


class ClickableDoubleSpinBox(QDoubleSpinBox):
    """优化微调箭头交互手势与光标感知的高精度浮点数字框 (双击鼠标左键全选全部数值)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(26)
        # 禁用键盘逐字即时触发，防止在用户尚未完成输入时误发信号引发级联篡改与异常
        self.setKeyboardTracking(False)
        line_edit = self.lineEdit()
        if line_edit:
            line_edit.setMouseTracking(True)
            line_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit() and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self.lineEdit().selectAll()
                QTimer.singleShot(0, self.lineEdit().selectAll)
                return True
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        # 按钮位于右侧 24px 区域
        if event.pos().x() >= self.width() - 25:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        parent = self.parentWidget()
        while parent:
            if isinstance(parent, QScrollArea):
                delta = event.angleDelta().y()
                bar = parent.verticalScrollBar()
                if bar and delta != 0:
                    bar.setValue(bar.value() - delta // 2)
                event.accept()
                return
            parent = parent.parentWidget()
        event.ignore()


class ClickableSpinBox(QSpinBox):
    """优化微调箭头交互手势与光标感知的整型数字框 (双击鼠标左键全选全部数值)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(26)
        # 禁用键盘逐字即时触发
        self.setKeyboardTracking(False)
        line_edit = self.lineEdit()
        if line_edit:
            line_edit.setMouseTracking(True)
            line_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit() and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self.lineEdit().selectAll()
                QTimer.singleShot(0, self.lineEdit().selectAll)
                return True
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        if event.pos().x() >= self.width() - 25:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        parent = self.parentWidget()
        while parent:
            if isinstance(parent, QScrollArea):
                delta = event.angleDelta().y()
                bar = parent.verticalScrollBar()
                if bar and delta != 0:
                    bar.setValue(bar.value() - delta // 2)
                event.accept()
                return
            parent = parent.parentWidget()
        event.ignore()


class FloatSliderBox(QWidget):
    """浮点数精密滑块-输入框联动组件"""
    valueChanged = pyqtSignal(float)

    def __init__(
        self, 
        title: str, 
        unit: str, 
        min_val: float, 
        max_val: float, 
        default_val: float, 
        step: float = 0.01,
        decimals: int = 3,
        parent=None
    ):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.decimals = decimals
        self.scale = 10 ** decimals

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        # 标题行：左标题 + 右单位
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet("font-size: 11px; color: #94A3B8;")
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_unit)
        layout.addLayout(header_layout)

        # 控件行：滑块 + SpinBox
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)

        self.slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(round(min_val * self.scale)), int(round(max_val * self.scale)))
        self.slider.setSingleStep(int(round(step * self.scale)))
        self.slider.setValue(int(round(default_val * self.scale)))

        self.spin = ClickableDoubleSpinBox()
        self.spin.setRange(min_val, max_val)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setValue(default_val)
        self.spin.setFixedWidth(120 if decimals >= 5 else 105)

        control_layout.addWidget(self.slider)
        control_layout.addWidget(self.spin)
        layout.addLayout(control_layout)

        # 信号联动与防循环触发
        self._block_signals = False
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.spin.valueChanged.connect(self._on_spin_changed)

    def setToolTip(self, text: str):
        """同步为滑块、数字框及标题标签注入统一的悬停工程释义"""
        super().setToolTip(text)
        self.lbl_title.setToolTip(text)
        self.lbl_unit.setToolTip(text)
        self.slider.setToolTip(text)
        self.spin.setToolTip(text)

    def setTitle(self, title: str):
        self.lbl_title.setText(str(title))

    def setUnit(self, unit: str):
        self.lbl_unit.setText(str(unit))

    def _on_slider_changed(self, int_val: int):
        if self._block_signals:
            return
        self._block_signals = True
        val = int_val / self.scale
        self.spin.setValue(val)
        self._block_signals = False
        self.valueChanged.emit(val)

    def _on_spin_changed(self, float_val: float):
        if self._block_signals:
            return
        self._block_signals = True
        self.slider.setValue(int(round(float_val * self.scale)))
        self._block_signals = False
        self.valueChanged.emit(float_val)

    def value(self) -> float:
        return self.spin.value()

    def setValue(self, val: float):
        if self._block_signals:
            return
        self._block_signals = True
        clamped_val = max(self.min_val, min(self.max_val, val))
        self.spin.setValue(clamped_val)
        self.slider.setValue(int(round(clamped_val * self.scale)))
        self._block_signals = False
        self.valueChanged.emit(clamped_val)

    def setMinimum(self, min_val: float):
        self.min_val = min_val
        self.spin.setMinimum(min_val)
        self.slider.setMinimum(int(round(min_val * self.scale)))
        if self.spin.value() < min_val:
            self.setValue(min_val)

    def setMaximum(self, max_val: float):
        self.max_val = max_val
        self.spin.setMaximum(max_val)
        self.slider.setMaximum(int(round(max_val * self.scale)))
        if self.spin.value() > max_val:
            self.setValue(max_val)

    def setRange(self, min_val: float, max_val: float):
        self.min_val = min_val
        self.max_val = max_val
        self.spin.setRange(min_val, max_val)
        self.slider.setRange(int(round(min_val * self.scale)), int(round(max_val * self.scale)))
        if self.spin.value() < min_val:
            self.setValue(min_val)
        elif self.spin.value() > max_val:
            self.setValue(max_val)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.lbl_title.setEnabled(enabled)
        self.lbl_unit.setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self.spin.setEnabled(enabled)
        if enabled:
            self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
            self.lbl_unit.setStyleSheet("font-size: 11px; color: #94A3B8;")
        else:
            self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")
            self.lbl_unit.setStyleSheet("font-size: 11px; color: #CBD5E1;")


class IntSliderBox(QWidget):
    """整型精密滑块-输入框联动组件 (用于层数与匝数)"""
    valueChanged = pyqtSignal(int)

    def __init__(
        self, 
        title: str, 
        unit: str, 
        min_val: int, 
        max_val: int, 
        default_val: int, 
        parent=None
    ):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        # 标题行
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet("font-size: 11px; color: #94A3B8;")
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_unit)
        layout.addLayout(header_layout)

        # 控制行
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)

        self.slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)

        self.spin = ClickableSpinBox()
        self.spin.setRange(min_val, max_val)
        self.spin.setValue(default_val)
        self.spin.setFixedWidth(98)

        control_layout.addWidget(self.slider)
        control_layout.addWidget(self.spin)
        layout.addLayout(control_layout)

        self._block_signals = False
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.spin.valueChanged.connect(self._on_spin_changed)

    def setToolTip(self, text: str):
        """同步为整型滑块、数字框及标题标签注入统一的悬停工程释义"""
        super().setToolTip(text)
        self.lbl_title.setToolTip(text)
        self.lbl_unit.setToolTip(text)
        self.slider.setToolTip(text)
        self.spin.setToolTip(text)

    def setTitle(self, title: str):
        self.lbl_title.setText(str(title))

    def setUnit(self, unit: str):
        self.lbl_unit.setText(str(unit))

    def _on_slider_changed(self, val: int):
        if self._block_signals:
            return
        self._block_signals = True
        self.spin.setValue(val)
        self._block_signals = False
        self.valueChanged.emit(val)

    def _on_spin_changed(self, val: int):
        if self._block_signals:
            return
        self._block_signals = True
        self.slider.setValue(val)
        self._block_signals = False
        self.valueChanged.emit(val)

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, val: int):
        if self._block_signals:
            return
        self._block_signals = True
        clamped_val = max(self.min_val, min(self.max_val, val))
        self.spin.setValue(clamped_val)
        self.slider.setValue(clamped_val)
        self._block_signals = False
        self.valueChanged.emit(clamped_val)

    def setMinimum(self, min_val: int):
        self.min_val = min_val
        self.spin.setMinimum(min_val)
        self.slider.setMinimum(min_val)
        if self.spin.value() < min_val:
            self.setValue(min_val)

    def setMaximum(self, max_val: int):
        self.max_val = max_val
        self.spin.setMaximum(max_val)
        self.slider.setMaximum(max_val)
        if self.spin.value() > max_val:
            self.setValue(max_val)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.lbl_title.setEnabled(enabled)
        self.lbl_unit.setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self.spin.setEnabled(enabled)
        if enabled:
            self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
            self.lbl_unit.setStyleSheet("font-size: 11px; color: #94A3B8;")
        else:
            self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")
            self.lbl_unit.setStyleSheet("font-size: 11px; color: #CBD5E1;")
