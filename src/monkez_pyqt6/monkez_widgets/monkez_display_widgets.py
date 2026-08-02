from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPalette
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
        self._decimal_separator = "."
        self._group_separator = ","
        self._grouping_enabled = False
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
        """Display text while preserving both decimal dots and comma separators."""
        text = str(value)
        if isinstance(value, (int, float)):
            self._number = float(value)
        self._display_text = text
        if self._auto_digit_count:
            visible_digits = sum(character not in ".," for character in text)
            self.setDigitCount(max(1, visible_digits))
        super().display(text.replace(",", "."))
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
        decimal_separator: str = ".",
        group_separator: str = ",",
    ) -> str:
        """Format and display a numeric value with configurable separators."""
        decimals = max(0, int(decimals))
        if decimal_separator not in (".", ","):
            raise ValueError("decimal_separator must be '.' or ','")
        if group_separator not in ("", ".", ","):
            raise ValueError("group_separator must be empty, '.' or ','")
        if group_separator == decimal_separator and group_separator:
            raise ValueError("group_separator and decimal_separator must differ")

        self._number = float(value)
        formatted = f"{self._number:,.{decimals}f}"
        marker = "\u202f"
        formatted = formatted.replace(",", marker).replace(".", decimal_separator)
        formatted = formatted.replace(marker, group_separator)
        self.display(formatted)
        return formatted

    def getNumber(self) -> float:
        return self._number

    def setNumber(self, value: float) -> None:
        self._number = float(value)
        group_separator = self._group_separator if self._grouping_enabled else ""
        self.displayFormatted(
            self._number,
            self._decimal_places,
            self._decimal_separator,
            group_separator,
        )

    def getDecimalPlaces(self) -> int:
        return self._decimal_places

    def setDecimalPlaces(self, value: int) -> None:
        self._decimal_places = min(12, max(0, int(value)))
        self.setNumber(self._number)

    def getDecimalSeparator(self) -> str:
        return self._decimal_separator

    def setDecimalSeparator(self, value: str) -> None:
        value = str(value)
        if value not in (".", ","):
            return
        self._decimal_separator = value
        if self._group_separator == value:
            self._group_separator = "," if value == "." else "."
        self.setNumber(self._number)

    def getGroupSeparator(self) -> str:
        return self._group_separator

    def setGroupSeparator(self, value: str) -> None:
        value = str(value)
        if value not in ("", ".", ",") or value == self._decimal_separator:
            return
        self._group_separator = value
        self.setNumber(self._number)

    def getGroupingEnabled(self) -> bool:
        return self._grouping_enabled

    def setGroupingEnabled(self, value: bool) -> None:
        self._grouping_enabled = bool(value)
        self.setNumber(self._number)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if "," not in self._display_text or self.digitCount() <= 0:
            return

        content = QRectF(self.rect()).adjusted(9, 9, -9, -9)
        if content.width() <= 0 or content.height() <= 0:
            return
        slot_width = content.width() / self.digitCount()
        character_slots = sum(character not in ".," for character in self._display_text)
        leading_slots = max(0, self.digitCount() - character_slots)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._digit_color)
        occupied_slots = 0
        for character in self._display_text:
            if character == "," and occupied_slots:
                x = content.left() + (leading_slots + occupied_slots) * slot_width - slot_width * 0.08
                mark_size = max(2.5, min(slot_width * 0.08, content.height() * 0.04))
                y = content.bottom() - content.height() * 0.17
                painter.drawEllipse(QPointF(x, y), mark_size * 0.48, mark_size * 0.48)
                tail = QPainterPath(QPointF(x + mark_size * 0.22, y + mark_size * 0.2))
                tail.cubicTo(
                    QPointF(x + mark_size * 0.5, y + mark_size * 0.85),
                    QPointF(x - mark_size * 0.05, y + mark_size * 1.5),
                    QPointF(x - mark_size * 0.75, y + mark_size * 1.95),
                )
                tail.lineTo(QPointF(x - mark_size * 0.15, y + mark_size * 0.75))
                tail.closeSubpath()
                painter.drawPath(tail)
            elif character not in ".,":
                occupied_slots += 1

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
    decimalSeparator = pyqtProperty(str, getDecimalSeparator, setDecimalSeparator)
    groupSeparator = pyqtProperty(str, getGroupSeparator, setGroupSeparator)
    groupingEnabled = pyqtProperty(bool, getGroupingEnabled, setGroupingEnabled)
