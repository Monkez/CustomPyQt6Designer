from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QPointF, QSize, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton

from .themes import (
    color_to_css,
    normalize_theme,
    theme_color,
    theme_from_preset,
    theme_int,
    theme_options_text,
    theme_radius,
    theme_to_preset,
)


class MonkezCheckBox(QCheckBox):
    @pyqtEnum
    class ThemePreset(IntEnum):
        Material = 0
        IOS = 1
        Fluent = 2
        Bootstrap = 3
        Minimal = 4
        Dark = 5

    Material = ThemePreset.Material
    IOS = ThemePreset.IOS
    Fluent = ThemePreset.Fluent
    Bootstrap = ThemePreset.Bootstrap
    Minimal = ThemePreset.Minimal
    Dark = ThemePreset.Dark
    themePresetChanged = pyqtSignal(ThemePreset)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._theme = "material"
        self._box_color = QColor("#ffffff")
        self._checked_color = QColor("#1976d2")
        self._border_color = QColor("#90a4ae")
        self._text_color = QColor("#1f2937")
        self._radius = 4
        self._indicator_size = 18

        self.setText("Monkez CheckBox")
        self.setTheme(self._theme)

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self.text()) + self._indicator_size + 18, max(30, metrics.height() + 10))

    def minimumSizeHint(self) -> QSize:
        return QSize(18, 18)

    def _update_style(self) -> None:
        hover = color_to_css(theme_color(self._theme, "secondary"))
        self.setStyleSheet(
            "QCheckBox {"
            f"color: {color_to_css(self._text_color)};"
            f"font-size: {theme_int(self._theme, 'font_size')}px;"
            "spacing: 8px;"
            "}"
            "QCheckBox::indicator {"
            f"width: {self._indicator_size}px;"
            f"height: {self._indicator_size}px;"
            f"border-radius: {self._radius}px;"
            f"border: {max(1, theme_int(self._theme, 'border_width'))}px solid {color_to_css(self._border_color)};"
            f"background-color: {color_to_css(self._box_color)};"
            "}"
            "QCheckBox::indicator:hover {"
            f"background-color: {hover};"
            f"border-color: {color_to_css(self._checked_color)};"
            "}"
            "QCheckBox::indicator:checked {"
            f"background-color: {color_to_css(self._checked_color)};"
            f"border-color: {color_to_css(self._checked_color)};"
            "image: none;"
            "}"
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        state = self.checkState()
        if state == Qt.CheckState.Unchecked:
            return
        option = QStyleOptionButton()
        self.initStyleOption(option)
        rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            option,
            self,
        )
        if rect.isEmpty():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(
            QPen(
                theme_color(self._theme, "on_primary"),
                max(2.0, rect.width() / 8),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        if state == Qt.CheckState.PartiallyChecked:
            y = rect.center().y()
            painter.drawLine(
                QPointF(rect.left() + rect.width() * 0.25, y),
                QPointF(rect.right() - rect.width() * 0.25, y),
            )
        else:
            painter.drawLine(
                QPointF(rect.left() + rect.width() * 0.22, rect.center().y()),
                QPointF(rect.left() + rect.width() * 0.43, rect.bottom() - rect.height() * 0.24),
            )
            painter.drawLine(
                QPointF(rect.left() + rect.width() * 0.43, rect.bottom() - rect.height() * 0.24),
                QPointF(rect.right() - rect.width() * 0.17, rect.top() + rect.height() * 0.22),
            )

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._box_color = theme_color(self._theme, "control")
        self._checked_color = theme_color(self._theme, "primary")
        self._border_color = theme_color(self._theme, "border")
        self._text_color = theme_color(self._theme, "text")
        self._radius = max(3, theme_radius(self._theme) // 2)
        self._indicator_size = 20 if self._theme == "ios" else 18
        self._update_style()
        if previous != self._theme:
            self.themePresetChanged.emit(self.getThemePreset())

    def getThemePreset(self):
        return self.ThemePreset(theme_to_preset(self._theme))

    def setThemePreset(self, value) -> None:
        self.setTheme(theme_from_preset(value))

    def getThemeName(self) -> str:
        return self.getTheme()

    def setThemeName(self, value: str) -> None:
        self.setTheme(value)

    def getThemeIndex(self) -> int:
        return theme_to_preset(self._theme)

    def setThemeIndex(self, value: int) -> None:
        self.setTheme(theme_from_preset(value))

    def getThemeOptions(self) -> str:
        return theme_options_text()

    def setThemeOptions(self, value: str) -> None:
        return None

    def getBoxColor(self) -> QColor:
        return QColor(self._box_color)

    def setBoxColor(self, color: QColor) -> None:
        self._box_color = QColor(color)
        self._update_style()

    def getCheckedColor(self) -> QColor:
        return QColor(self._checked_color)

    def setCheckedColor(self, color: QColor) -> None:
        self._checked_color = QColor(color)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, color: QColor) -> None:
        self._border_color = QColor(color)
        self._update_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, color: QColor) -> None:
        self._text_color = QColor(color)
        self._update_style()

    def getIndicatorSize(self) -> int:
        return self._indicator_size

    def setIndicatorSize(self, value: int) -> None:
        self._indicator_size = max(10, value)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, value)
        self._update_style()

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=True, stored=False)
    themeIndexHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeOptions = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeName = pyqtProperty(str, getThemeName, setThemeName, designable=False)
    themePreset = pyqtProperty(ThemePreset, getThemePreset, setThemePreset, designable=False, notify=themePresetChanged)
    boxColor = pyqtProperty(QColor, getBoxColor, setBoxColor)
    checkedColor = pyqtProperty(QColor, getCheckedColor, setCheckedColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    indicatorSize = pyqtProperty(int, getIndicatorSize, setIndicatorSize)
    radius = pyqtProperty(int, getRadius, setRadius)
