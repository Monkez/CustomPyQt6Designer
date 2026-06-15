from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QProgressBar

from .themes import (
    normalize_theme,
    theme_color,
    theme_from_preset,
    theme_int,
    theme_options_text,
    theme_radius,
    theme_to_preset,
)


class MonkezProgressBar(QProgressBar):
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
        self._bar_color = QColor("#1976d2")
        self._track_color = QColor("#eef5fd")
        self._text_color = QColor("#1f2937")
        self._radius = 8
        self._bar_height = 28

        self.setRange(0, 100)
        self.setValue(62)
        self.setTextVisible(True)
        self.setMinimumSize(180, 4)
        self.resize(180, self._bar_height)
        self.setTheme(self._theme)

    def _update_style(self) -> None:
        radius = min(self._radius, max(1, self._bar_height // 2))
        border_width = 0 if self._bar_height <= 8 else max(1, theme_int(self._theme, "border_width"))
        font_size = min(theme_int(self._theme, "font_size"), max(1, self._bar_height - 6))
        self.setStyleSheet(
            "QProgressBar {"
            f"border: {border_width}px solid {theme_color(self._theme, 'border').name()};"
            f"border-radius: {radius}px;"
            f"background-color: {self._track_color.name()};"
            f"color: {self._text_color.name()};"
            f"font-size: {font_size}px;"
            f"min-height: {self._bar_height}px;"
            f"max-height: {self._bar_height}px;"
            "text-align: center;"
            "}"
            "QProgressBar::chunk {"
            f"border-radius: {max(0, radius - border_width)}px;"
            f"background-color: {self._bar_color.name()};"
            "}"
        )

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._bar_color = theme_color(self._theme, "primary")
        self._track_color = theme_color(self._theme, "surface_alt")
        self._text_color = theme_color(self._theme, "text")
        self._radius = theme_radius(self._theme)
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

    def getBarColor(self) -> QColor:
        return QColor(self._bar_color)

    def setBarColor(self, color: QColor) -> None:
        self._bar_color = QColor(color)
        self._update_style()

    def getTrackColor(self) -> QColor:
        return QColor(self._track_color)

    def setTrackColor(self, color: QColor) -> None:
        self._track_color = QColor(color)
        self._update_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, color: QColor) -> None:
        self._text_color = QColor(color)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, value)
        self._update_style()

    def getBarHeight(self) -> int:
        return self._bar_height

    def setBarHeight(self, value: int) -> None:
        try:
            height = int(value)
        except (TypeError, ValueError):
            height = 28
        self._bar_height = max(2, height)
        self.setMinimumHeight(self._bar_height)
        self.setMaximumHeight(self._bar_height)
        self.resize(max(self.width(), 1), self._bar_height)
        if self._bar_height <= 14:
            self.setTextVisible(False)
        self._update_style()

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=True, stored=False)
    themeIndexHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeOptions = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeName = pyqtProperty(str, getThemeName, setThemeName, designable=False)
    themePreset = pyqtProperty(ThemePreset, getThemePreset, setThemePreset, designable=False, notify=themePresetChanged)
    barColor = pyqtProperty(QColor, getBarColor, setBarColor)
    trackColor = pyqtProperty(QColor, getTrackColor, setTrackColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    radius = pyqtProperty(int, getRadius, setRadius)
    barHeight = pyqtProperty(int, getBarHeight, setBarHeight)
