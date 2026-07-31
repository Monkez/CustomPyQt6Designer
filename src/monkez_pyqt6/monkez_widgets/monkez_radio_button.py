from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QRadioButton

from .shadow_support import ShadowSupportMixin
from .themes import normalize_theme, theme_color, theme_from_preset, theme_int, theme_options_text, theme_to_preset


class MonkezRadioButton(QRadioButton, ShadowSupportMixin):
    @pyqtEnum
    class ThemePreset(IntEnum):
        Material = 0
        IOS = 1
        Fluent = 2
        Bootstrap = 3
        Minimal = 4
        Dark = 5

    @pyqtEnum
    class RadioStyle(IntEnum):
        Classic = 0
        Card = 1
        Pill = 2

    themePresetChanged = pyqtSignal(ThemePreset)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_shadow_support()
        self._theme = "material"
        self._radio_style = self.RadioStyle.Classic
        self._indicator_color = QColor()
        self._checked_color = QColor()
        self._border_color = QColor()
        self._text_color = QColor()
        self._hover_color = QColor()
        self._indicator_size = 18
        self._content_padding = 10
        self.setText("Monkez Radio")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        width = metrics.horizontalAdvance(self.text()) + self._indicator_size + 34
        height = max(34, metrics.height() + 18)
        if self._radio_style != self.RadioStyle.Classic:
            width += 18
            height = max(height, 44)
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        return QSize(18, 18)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        hovered = self.underMouse()
        checked = self.isChecked()
        enabled_opacity = 1.0 if self.isEnabled() else 0.48
        painter.setOpacity(enabled_opacity)

        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self._radio_style in (self.RadioStyle.Card, self.RadioStyle.Pill):
            radius = bounds.height() / 2 if self._radio_style == self.RadioStyle.Pill else 9
            background = self._hover_color if hovered or checked else self._indicator_color
            border = self._checked_color if checked else self._border_color
            painter.setPen(QPen(border, 1.5 if checked else 1))
            painter.setBrush(background)
            painter.drawRoundedRect(bounds, radius, radius)

        left = self._content_padding if self._radio_style != self.RadioStyle.Classic else 2
        indicator = QRectF(
            left,
            (self.height() - self._indicator_size) / 2,
            self._indicator_size,
            self._indicator_size,
        )
        painter.setPen(QPen(self._checked_color if checked or hovered else self._border_color, 2))
        painter.setBrush(self._indicator_color)
        painter.drawEllipse(indicator)
        if checked:
            dot = indicator.adjusted(self._indicator_size * 0.27, self._indicator_size * 0.27,
                                     -self._indicator_size * 0.27, -self._indicator_size * 0.27)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._checked_color)
            painter.drawEllipse(dot)

        text_rect = QRectF(indicator.right() + 10, 0, self.width() - indicator.right() - 16, self.height())
        font = QFont(self.font())
        font.setWeight(QFont.Weight.DemiBold if checked and self._radio_style != self.RadioStyle.Classic else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(self._text_color)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

        if self.hasFocus():
            focus = bounds.adjusted(2, 2, -2, -2)
            painter.setPen(QPen(self._checked_color, 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(focus, 7, 7)

    def _update_style(self) -> None:
        self.setStyleSheet("MonkezRadioButton { background: transparent; }")
        self.updateGeometry()
        self.update()

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._indicator_color = theme_color(self._theme, "control")
        self._checked_color = theme_color(self._theme, "primary")
        self._border_color = theme_color(self._theme, "border")
        self._text_color = theme_color(self._theme, "text")
        self._hover_color = theme_color(self._theme, "secondary")
        self._indicator_size = 20 if self._theme == "ios" else 18
        self._update_style()
        if previous != self._theme:
            self.themePresetChanged.emit(self.ThemePreset(theme_to_preset(self._theme)))

    def getThemeIndex(self) -> int:
        return theme_to_preset(self._theme)

    def setThemeIndex(self, value: int) -> None:
        self.setTheme(theme_from_preset(value))

    def getThemeOptions(self) -> str:
        return theme_options_text()

    def setThemeOptions(self, value: str) -> None:
        return None

    def getRadioStyle(self):
        return int(self._radio_style)

    def setRadioStyle(self, value) -> None:
        try:
            self._radio_style = self.RadioStyle(int(value))
        except (TypeError, ValueError):
            self._radio_style = self.RadioStyle.Classic
        self._update_style()

    def getRadioStyleHint(self) -> str:
        return "0 Classic | 1 Card | 2 Pill"

    def setRadioStyleHint(self, value: str) -> None:
        return None

    def _color_property(name: str):
        def getter(self):
            return QColor(getattr(self, name))

        def setter(self, value):
            setattr(self, name, QColor(value))
            self.update()

        return getter, setter

    def getBackgroundColor(self) -> QColor:
        return QColor(self._indicator_color)

    def setBackgroundColor(self, value: QColor) -> None:
        color = QColor(value)
        self._indicator_color = color
        self._hover_color = color.lighter(108)
        self.update()

    getCheckedColor, setCheckedColor = _color_property("_checked_color")
    getBorderColor, setBorderColor = _color_property("_border_color")
    getTextColor, setTextColor = _color_property("_text_color")

    def getIndicatorSize(self) -> int:
        return self._indicator_size

    def setIndicatorSize(self, value: int) -> None:
        self._indicator_size = min(36, max(10, int(value)))
        self._update_style()

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, stored=False)
    radioStyle = pyqtProperty(int, getRadioStyle, setRadioStyle)
    radioStyleHint = pyqtProperty(str, getRadioStyleHint, setRadioStyleHint, stored=False)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    checkedColor = pyqtProperty(QColor, getCheckedColor, setCheckedColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    indicatorSize = pyqtProperty(int, getIndicatorSize, setIndicatorSize)
    shadowEnabled = pyqtProperty(bool, ShadowSupportMixin.getShadowEnabled, ShadowSupportMixin.setShadowEnabled)
    shadowBlur = pyqtProperty(int, ShadowSupportMixin.getShadowBlur, ShadowSupportMixin.setShadowBlur)
    shadowOffsetX = pyqtProperty(int, ShadowSupportMixin.getShadowOffsetX, ShadowSupportMixin.setShadowOffsetX)
    shadowOffsetY = pyqtProperty(int, ShadowSupportMixin.getShadowOffsetY, ShadowSupportMixin.setShadowOffsetY)
    shadowColor = pyqtProperty(QColor, ShadowSupportMixin.getShadowColor, ShadowSupportMixin.setShadowColor)
