from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QAbstractButton

from .themes import normalize_theme, theme_color, theme_from_preset, theme_options_text, theme_radius, theme_to_preset


class MonkezSwitch(QAbstractButton):
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
        self._theme = "ios"
        self._track_color = QColor("#d1d5db")
        self._checked_color = QColor("#34c759")
        self._thumb_color = QColor("#ffffff")
        self._text_color = QColor("#111827")
        self._radius = 14
        self._thumb_margin = 3
        self._show_text = False
        self._on_text = "ON"
        self._off_text = "OFF"

        self.setCheckable(True)
        self.setChecked(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self.update)
        self.setTheme(self._theme)

    def sizeHint(self) -> QSize:
        return QSize(104 if self._show_text else 58, 34 if self._show_text else 30)

    def minimumSizeHint(self) -> QSize:
        return QSize(24, 16)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        switch_width = min(58, max(44, self.width()))
        switch_height = min(30, max(24, self.height()))
        track_rect = QRectF(0, (self.height() - switch_height) / 2, switch_width, switch_height)
        track_color = self._checked_color if self.isChecked() else self._track_color

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, self._radius, self._radius)

        thumb_diameter = switch_height - self._thumb_margin * 2
        thumb_x = (
            track_rect.right() - thumb_diameter - self._thumb_margin
            if self.isChecked()
            else track_rect.left() + self._thumb_margin
        )
        thumb_rect = QRectF(thumb_x, track_rect.top() + self._thumb_margin, thumb_diameter, thumb_diameter)
        painter.setBrush(self._thumb_color)
        painter.drawEllipse(thumb_rect)

        if self._show_text:
            text = self._on_text if self.isChecked() else self._off_text
            text_rect = QRectF(track_rect.right() + 8, 0, max(0, self.width() - track_rect.width() - 8), self.height())
            painter.setPen(self._text_color)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        painter.end()

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._checked_color = theme_color(self._theme, "primary")
        self._track_color = theme_color(self._theme, "surface_alt")
        self._text_color = theme_color(self._theme, "text")
        self._thumb_color = theme_color(self._theme, "surface")
        self._radius = theme_radius(self._theme)
        self._thumb_margin = 2 if self._theme in {"fluent", "minimal"} else 3
        self.update()
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

    def getTrackColor(self) -> QColor:
        return QColor(self._track_color)

    def setTrackColor(self, color: QColor) -> None:
        self._track_color = QColor(color)
        self.update()

    def getCheckedColor(self) -> QColor:
        return QColor(self._checked_color)

    def setCheckedColor(self, color: QColor) -> None:
        self._checked_color = QColor(color)
        self.update()

    def getThumbColor(self) -> QColor:
        return QColor(self._thumb_color)

    def setThumbColor(self, color: QColor) -> None:
        self._thumb_color = QColor(color)
        self.update()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, color: QColor) -> None:
        self._text_color = QColor(color)
        self.update()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, value)
        self.update()

    def getThumbMargin(self) -> int:
        return self._thumb_margin

    def setThumbMargin(self, value: int) -> None:
        self._thumb_margin = max(1, value)
        self.update()

    def getShowText(self) -> bool:
        return self._show_text

    def setShowText(self, value: bool) -> None:
        self._show_text = bool(value)
        self.updateGeometry()
        self.update()

    def getOnText(self) -> str:
        return self._on_text

    def setOnText(self, value: str) -> None:
        self._on_text = value or "ON"
        self.update()

    def getOffText(self) -> str:
        return self._off_text

    def setOffText(self, value: str) -> None:
        self._off_text = value or "OFF"
        self.update()

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=True, stored=False)
    themeIndexHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeOptions = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeName = pyqtProperty(str, getThemeName, setThemeName, designable=False)
    themePreset = pyqtProperty(ThemePreset, getThemePreset, setThemePreset, designable=False, notify=themePresetChanged)
    trackColor = pyqtProperty(QColor, getTrackColor, setTrackColor)
    checkedColor = pyqtProperty(QColor, getCheckedColor, setCheckedColor)
    thumbColor = pyqtProperty(QColor, getThumbColor, setThumbColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    radius = pyqtProperty(int, getRadius, setRadius)
    thumbMargin = pyqtProperty(int, getThumbMargin, setThumbMargin)
    showText = pyqtProperty(bool, getShowText, setShowText)
    onText = pyqtProperty(str, getOnText, setOnText)
    offText = pyqtProperty(str, getOffText, setOffText)
