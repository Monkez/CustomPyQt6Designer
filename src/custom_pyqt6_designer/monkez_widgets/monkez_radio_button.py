from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QRadioButton

from .themes import normalize_theme, theme_color, theme_from_preset, theme_int, theme_options_text, theme_to_preset


class MonkezRadioButton(QRadioButton):
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
        self._indicator_color = QColor("#ffffff")
        self._checked_color = QColor("#1976d2")
        self._border_color = QColor("#90a4ae")
        self._text_color = QColor("#1f2937")
        self._indicator_size = 18

        self.setText("Monkez Radio")
        self.setMinimumHeight(30)
        self.setTheme(self._theme)

    def _update_style(self) -> None:
        dot_size = max(6, self._indicator_size // 2)
        self.setStyleSheet(
            "QRadioButton {"
            f"color: {self._text_color.name()};"
            f"font-size: {theme_int(self._theme, 'font_size')}px;"
            "spacing: 8px;"
            "}"
            "QRadioButton::indicator {"
            f"width: {self._indicator_size}px;"
            f"height: {self._indicator_size}px;"
            f"border-radius: {self._indicator_size // 2}px;"
            f"border: {max(1, theme_int(self._theme, 'border_width'))}px solid {self._border_color.name()};"
            f"background-color: {self._indicator_color.name()};"
            "}"
            "QRadioButton::indicator:hover {"
            f"border-color: {self._checked_color.name()};"
            f"background-color: {theme_color(self._theme, 'secondary').name()};"
            "}"
            "QRadioButton::indicator:checked {"
            f"border: {max(4, (self._indicator_size - dot_size) // 2)}px solid {self._checked_color.name()};"
            f"background-color: {self._indicator_color.name()};"
            "}"
        )

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._indicator_color = theme_color(self._theme, "control")
        self._checked_color = theme_color(self._theme, "primary")
        self._border_color = theme_color(self._theme, "border")
        self._text_color = theme_color(self._theme, "text")
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

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=True, stored=False)
    themeIndexHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeOptions = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeName = pyqtProperty(str, getThemeName, setThemeName, designable=False)
    themePreset = pyqtProperty(ThemePreset, getThemePreset, setThemePreset, designable=False, notify=themePresetChanged)
    checkedColor = pyqtProperty(QColor, getCheckedColor, setCheckedColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    indicatorSize = pyqtProperty(int, getIndicatorSize, setIndicatorSize)
