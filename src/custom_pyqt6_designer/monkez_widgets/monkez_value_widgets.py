from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QDial, QDoubleSpinBox, QSpinBox

from .theme_support import ThemeSupportMixin
from .themes import theme_color, theme_int, theme_radius


class _SpinBoxStyleMixin(ThemeSupportMixin):
    def _init_spinbox_style(self) -> None:
        self._init_theme_support()
        self._background_color = QColor()
        self._border_color = QColor()
        self._text_color = QColor()
        self._accent_color = QColor()
        self._radius = 8
        self._control_height = 40

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "control")
        self._border_color = theme_color(self._theme, "border")
        self._text_color = theme_color(self._theme, "text")
        self._accent_color = theme_color(self._theme, "primary")
        self._radius = theme_radius(self._theme)
        self._control_height = theme_int(self._theme, "control_height")
        self._update_style()

    def _update_style(self) -> None:
        selector = type(self).__name__
        button_width = max(22, self._control_height // 2)
        self.setMinimumHeight(self._control_height)
        self.setStyleSheet(
            f"{selector} {{"
            f"background-color: {self._background_color.name()};"
            f"border: 1px solid {self._border_color.name()};"
            f"border-radius: {self._radius}px;"
            f"color: {self._text_color.name()};"
            "padding: 4px 8px;"
            f"padding-right: {button_width + 6}px;"
            "}"
            f"{selector}:focus {{ border: 2px solid {self._accent_color.name()}; }}"
            f"{selector}::up-button {{"
            f"subcontrol-origin: border; subcontrol-position: top right; width: {button_width}px;"
            f"border-left: 1px solid {self._border_color.name()};"
            f"border-top-right-radius: {self._radius}px;"
            "}"
            f"{selector}::down-button {{"
            f"subcontrol-origin: border; subcontrol-position: bottom right; width: {button_width}px;"
            f"border-left: 1px solid {self._border_color.name()};"
            f"border-bottom-right-radius: {self._radius}px;"
            "}"
            f"{selector}::up-button:hover, {selector}::down-button:hover {{"
            f"background-color: {theme_color(self._theme, 'control_hover').name()};"
            "}"
            f"{selector}::up-arrow, {selector}::down-arrow {{ image: none; }}"
        )

    def _paint_step_arrows(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self._accent_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x = self.width() - max(12, self._control_height // 4)
        offset = 4
        upper_y = self.height() * 0.32
        lower_y = self.height() * 0.68
        painter.drawLine(QPointF(x - offset, upper_y + 2), QPointF(x, upper_y - 2))
        painter.drawLine(QPointF(x, upper_y - 2), QPointF(x + offset, upper_y + 2))
        painter.drawLine(QPointF(x - offset, lower_y - 2), QPointF(x, lower_y + 2))
        painter.drawLine(QPointF(x, lower_y + 2), QPointF(x + offset, lower_y - 2))

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self._update_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self._update_style()

    def getAccentColor(self) -> QColor:
        return QColor(self._accent_color)

    def setAccentColor(self, value: QColor) -> None:
        self._accent_color = QColor(value)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._update_style()

    def getControlHeight(self) -> int:
        return self._control_height

    def setControlHeight(self, value: int) -> None:
        self._control_height = min(96, max(24, int(value)))
        self._update_style()


class MonkezSpinBox(QSpinBox, _SpinBoxStyleMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_spinbox_style()
        self.setRange(0, 100)
        self.setValue(25)
        self.setTheme("material")

    def paintEvent(self, event) -> None:
        QSpinBox.paintEvent(self, event)
        self._paint_step_arrows()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    backgroundColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getBackgroundColor, _SpinBoxStyleMixin.setBackgroundColor)
    borderColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getBorderColor, _SpinBoxStyleMixin.setBorderColor)
    textColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getTextColor, _SpinBoxStyleMixin.setTextColor)
    accentColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getAccentColor, _SpinBoxStyleMixin.setAccentColor)
    radius = pyqtProperty(int, _SpinBoxStyleMixin.getRadius, _SpinBoxStyleMixin.setRadius)
    controlHeight = pyqtProperty(int, _SpinBoxStyleMixin.getControlHeight, _SpinBoxStyleMixin.setControlHeight)


class MonkezDoubleSpinBox(QDoubleSpinBox, _SpinBoxStyleMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_spinbox_style()
        self.setRange(0.0, 100.0)
        self.setDecimals(2)
        self.setValue(25.5)
        self.setTheme("material")

    def paintEvent(self, event) -> None:
        QDoubleSpinBox.paintEvent(self, event)
        self._paint_step_arrows()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    backgroundColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getBackgroundColor, _SpinBoxStyleMixin.setBackgroundColor)
    borderColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getBorderColor, _SpinBoxStyleMixin.setBorderColor)
    textColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getTextColor, _SpinBoxStyleMixin.setTextColor)
    accentColor = pyqtProperty(QColor, _SpinBoxStyleMixin.getAccentColor, _SpinBoxStyleMixin.setAccentColor)
    radius = pyqtProperty(int, _SpinBoxStyleMixin.getRadius, _SpinBoxStyleMixin.setRadius)
    controlHeight = pyqtProperty(int, _SpinBoxStyleMixin.getControlHeight, _SpinBoxStyleMixin.setControlHeight)


class MonkezDial(QDial, ThemeSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._track_color = QColor()
        self._value_color = QColor()
        self._handle_color = QColor()
        self._text_color = QColor()
        self._track_width = 8
        self._handle_size = 12
        self._show_value = True
        self.setRange(0, 100)
        self.setValue(35)
        self.setNotchesVisible(False)
        self.setMinimumSize(96, 96)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._track_color = theme_color(self._theme, "surface_alt")
        self._value_color = theme_color(self._theme, "primary")
        self._handle_color = theme_color(self._theme, "surface")
        self._text_color = theme_color(self._theme, "text")
        self._track_width = 9 if self._theme == "ios" else 8
        self._update_style()

    def _update_style(self) -> None:
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        margin = max(self._handle_size, self._track_width) / 2 + 6
        rect = QRectF(
            (self.width() - side) / 2 + margin,
            (self.height() - side) / 2 + margin,
            side - margin * 2,
            side - margin * 2,
        )
        if rect.width() <= 0:
            return

        denominator = max(1, self.maximum() - self.minimum())
        ratio = (self.value() - self.minimum()) / denominator
        start_angle = 225 * 16
        total_span = -270 * 16

        pen = QPen(self._track_color, self._track_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, start_angle, total_span)

        pen.setColor(self._value_color)
        painter.setPen(pen)
        painter.drawArc(rect, start_angle, int(total_span * ratio))

        angle = math.radians(135 + ratio * 270)
        center = rect.center()
        radius = rect.width() / 2
        handle = QPointF(center.x() + radius * math.cos(angle), center.y() + radius * math.sin(angle))
        painter.setPen(QPen(self._value_color, 2))
        painter.setBrush(self._handle_color)
        painter.drawEllipse(handle, self._handle_size / 2, self._handle_size / 2)

        if self._show_value:
            painter.setPen(self._text_color)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(max(8, min(14, side // 9)))
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self.value()))

    def getTrackColor(self) -> QColor:
        return QColor(self._track_color)

    def setTrackColor(self, value: QColor) -> None:
        self._track_color = QColor(value)
        self.update()

    def getValueColor(self) -> QColor:
        return QColor(self._value_color)

    def setValueColor(self, value: QColor) -> None:
        self._value_color = QColor(value)
        self.update()

    def getHandleColor(self) -> QColor:
        return QColor(self._handle_color)

    def setHandleColor(self, value: QColor) -> None:
        self._handle_color = QColor(value)
        self.update()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self.update()

    def getTrackWidth(self) -> int:
        return self._track_width

    def setTrackWidth(self, value: int) -> None:
        self._track_width = min(24, max(2, int(value)))
        self.update()

    def getHandleSize(self) -> int:
        return self._handle_size

    def setHandleSize(self, value: int) -> None:
        self._handle_size = min(32, max(4, int(value)))
        self.update()

    def getShowValue(self) -> bool:
        return self._show_value

    def setShowValue(self, value: bool) -> None:
        self._show_value = bool(value)
        self.update()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    trackColor = pyqtProperty(QColor, getTrackColor, setTrackColor)
    valueColor = pyqtProperty(QColor, getValueColor, setValueColor)
    handleColor = pyqtProperty(QColor, getHandleColor, setHandleColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    trackWidth = pyqtProperty(int, getTrackWidth, setTrackWidth)
    handleSize = pyqtProperty(int, getHandleSize, setHandleSize)
    showValue = pyqtProperty(bool, getShowValue, setShowValue)
