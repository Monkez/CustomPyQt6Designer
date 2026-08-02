from __future__ import annotations

from PyQt6.QtCore import QSize, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QFrame, QLCDNumber

from .theme_support import ThemeSupportMixin
from .themes import color_to_css, theme_color, theme_radius


class MonkezLCDNumber(QLCDNumber, ThemeSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._background_color = QColor()
        self._digit_color = QColor()
        self._border_color = QColor()
        self._radius = 8
        self._display_text = ""
        self._auto_digit_count = False
        self._number = 123.45
        self._decimal_places = 2
        self.setDigitCount(6)
        self.setSmallDecimalPoint(True)
        self.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.display(123.45)
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        return QSize(160, 64)

    def minimumSizeHint(self) -> QSize:
        return QSize(40, 24)

    def display(self, value) -> None:
        """Display numeric text using QLCDNumber's native decimal point only."""
        # Commas are deliberately unsupported. Silently remove them so older
        # Designer forms continue loading without rendering a blank/invalid
        # LCD character or reviving custom punctuation.
        text = str(value).replace(",", "")
        if isinstance(value, (int, float)):
            self._number = float(value)
        self._display_text = text
        if self._auto_digit_count:
            visible_digits = sum(character != "." for character in text)
            self.setDigitCount(max(1, visible_digits))
        super().display(text)
        self.update()

    def getDisplayText(self) -> str:
        return self._display_text

    def setDisplayText(self, value: str) -> None:
        self.display(value)

    def getAutoDigitCount(self) -> bool:
        return self._auto_digit_count

    def setAutoDigitCount(self, value: bool) -> None:
        self._auto_digit_count = bool(value)
        if self._display_text:
            self.display(self._display_text)

    def displayFormatted(
        self,
        value: int | float,
        decimals: int = 2,
    ) -> str:
        """Format and display a number with the native decimal point."""
        decimals = max(0, int(decimals))
        self._number = float(value)
        formatted = f"{self._number:.{decimals}f}"
        self.display(formatted)
        return formatted

    def getNumber(self) -> float:
        return self._number

    def setNumber(self, value: float) -> None:
        self._number = float(value)
        self.displayFormatted(self._number, self._decimal_places)

    def getDecimalPlaces(self) -> int:
        return self._decimal_places

    def setDecimalPlaces(self, value: int) -> None:
        self._decimal_places = min(12, max(0, int(value)))
        self.setNumber(self._number)

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
            f"background-color: {color_to_css(self._background_color)};"
            f"color: {color_to_css(self._digit_color)};"
            f"border: 1px solid {color_to_css(self._border_color)};"
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
    displayText = pyqtProperty(str, getDisplayText, setDisplayText)
    autoDigitCount = pyqtProperty(bool, getAutoDigitCount, setAutoDigitCount)
    number = pyqtProperty(float, getNumber, setNumber)
    decimalPlaces = pyqtProperty(int, getDecimalPlaces, setDecimalPlaces)
