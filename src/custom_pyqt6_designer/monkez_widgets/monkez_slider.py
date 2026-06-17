from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QSize, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QSlider

from .themes import normalize_theme, theme_color, theme_from_preset, theme_options_text, theme_radius, theme_to_preset


class MonkezSlider(QSlider):
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
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._theme = "material"
        self._groove_color = QColor("#d1d5db")
        self._filled_color = QColor("#1976d2")
        self._handle_color = QColor("#ffffff")
        self._groove_height = 6
        self._handle_size = 20
        self._radius = 6

        self.setRange(0, 100)
        self.setValue(35)
        self.setTheme(self._theme)

    def sizeHint(self) -> QSize:
        return QSize(180, max(28, self._handle_size + 10))

    def minimumSizeHint(self) -> QSize:
        return QSize(32, 12)

    def _update_style(self) -> None:
        radius = max(1, self._radius)
        self.setStyleSheet(
            "QSlider::groove:horizontal {"
            f"height: {self._groove_height}px;"
            f"border-radius: {radius}px;"
            f"background-color: {self._groove_color.name()};"
            "}"
            "QSlider::sub-page:horizontal {"
            f"height: {self._groove_height}px;"
            f"border-radius: {radius}px;"
            f"background-color: {self._filled_color.name()};"
            "}"
            "QSlider::handle:horizontal {"
            f"width: {self._handle_size}px;"
            f"height: {self._handle_size}px;"
            f"margin: {-max(1, (self._handle_size - self._groove_height) // 2)}px 0;"
            f"border-radius: {self._handle_size // 2}px;"
            f"background-color: {self._handle_color.name()};"
            f"border: 2px solid {self._filled_color.name()};"
            "}"
            "QSlider::handle:horizontal:hover {"
            f"background-color: {theme_color(self._theme, 'secondary').name()};"
            "}"
        )

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._groove_color = theme_color(self._theme, "surface_alt")
        self._filled_color = theme_color(self._theme, "primary")
        self._handle_color = theme_color(self._theme, "surface")
        self._radius = theme_radius(self._theme)
        self._groove_height = 8 if self._theme in {"ios", "bootstrap"} else 6
        self._handle_size = 24 if self._theme == "ios" else 20
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

    def getGrooveColor(self) -> QColor:
        return QColor(self._groove_color)

    def setGrooveColor(self, color: QColor) -> None:
        self._groove_color = QColor(color)
        self._update_style()

    def getFilledColor(self) -> QColor:
        return QColor(self._filled_color)

    def setFilledColor(self, color: QColor) -> None:
        self._filled_color = QColor(color)
        self._update_style()

    def getHandleColor(self) -> QColor:
        return QColor(self._handle_color)

    def setHandleColor(self, color: QColor) -> None:
        self._handle_color = QColor(color)
        self._update_style()

    def getGrooveHeight(self) -> int:
        return self._groove_height

    def setGrooveHeight(self, value: int) -> None:
        self._groove_height = max(2, value)
        self._update_style()

    def getHandleSize(self) -> int:
        return self._handle_size

    def setHandleSize(self, value: int) -> None:
        self._handle_size = max(8, value)
        self._update_style()

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=True, stored=False)
    themeIndexHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeOptions = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeName = pyqtProperty(str, getThemeName, setThemeName, designable=False)
    themePreset = pyqtProperty(ThemePreset, getThemePreset, setThemePreset, designable=False, notify=themePresetChanged)
    grooveColor = pyqtProperty(QColor, getGrooveColor, setGrooveColor)
    filledColor = pyqtProperty(QColor, getFilledColor, setFilledColor)
    handleColor = pyqtProperty(QColor, getHandleColor, setHandleColor)
    grooveHeight = pyqtProperty(int, getGrooveHeight, setGrooveHeight)
    handleSize = pyqtProperty(int, getHandleSize, setHandleSize)
