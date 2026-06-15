from __future__ import annotations

from PyQt6.QtCore import pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QFrame, QLCDNumber

from .theme_support import ThemeSupportMixin
from .themes import theme_color, theme_radius


class MonkezLCDNumber(QLCDNumber, ThemeSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._background_color = QColor()
        self._digit_color = QColor()
        self._border_color = QColor()
        self._radius = 8
        self.setDigitCount(6)
        self.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.display(123.45)
        self.setMinimumSize(160, 64)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface_alt")
        self._digit_color = theme_color(self._theme, "primary")
        self._border_color = theme_color(self._theme, "border")
        self._radius = theme_radius(self._theme)
        self._update_style()

    def _update_style(self) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, self._digit_color)
        palette.setColor(QPalette.ColorRole.Light, self._digit_color)
        palette.setColor(QPalette.ColorRole.Dark, self._digit_color.darker(160))
        self.setPalette(palette)
        self.setStyleSheet(
            "MonkezLCDNumber {"
            f"background-color: {self._background_color.name()};"
            f"border: 1px solid {self._border_color.name()};"
            f"border-radius: {self._radius}px;"
            "padding: 8px;"
            "}"
        )

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._update_style()

    def getDigitColor(self) -> QColor:
        return QColor(self._digit_color)

    def setDigitColor(self, value: QColor) -> None:
        self._digit_color = QColor(value)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._update_style()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    digitColor = pyqtProperty(QColor, getDigitColor, setDigitColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    radius = pyqtProperty(int, getRadius, setRadius)
