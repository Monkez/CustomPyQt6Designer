from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QRect, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QLineEdit

from .assets import icon_path
from .themes import (
    normalize_theme,
    theme_color,
    theme_from_preset,
    theme_int,
    theme_options_text,
    theme_radius,
    theme_to_preset,
)


class MonkezTextInput(QLineEdit):
    trailingIconClicked = pyqtSignal()

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
        self._radius = 10
        self._background_color = QColor(255, 255, 255, 255)
        self._text_color = QColor("black")
        self._border_color = QColor("#d1d5db")
        self._padding = 5
        self._shadow_enabled = True
        self._shadow_blur = 10
        self._shadow_offset_x = 2
        self._shadow_offset_y = 2
        self._shadow_color = QColor(0, 0, 0, 100)
        self._leading_icon_name = ""
        self._leading_icon_size = 16
        self._trailing_icon_name = ""
        self._trailing_icon_size = 20
        self.leading_icon = QPixmap()
        self.trailing_icon = QPixmap()
        self.trailing_hovered = False
        self.trailing_rect = QRect()

        self.setPlaceholderText("Monkez input text...")
        self.setMinimumSize(200, 30)
        self.setTheme(self._theme)
        self._update_style()

    def mousePressEvent(self, event) -> None:
        if not self.trailing_rect.isNull() and self.trailing_rect.contains(event.pos()):
            self.trailingIconClicked.emit()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self.trailing_rect.isNull() and self.trailing_rect.contains(event.pos()):
            if not self.trailing_hovered:
                self.trailing_hovered = True
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                self.update()
        elif self.trailing_hovered:
            self.trailing_hovered = False
            self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self.trailing_hovered:
            self.trailing_hovered = False
            self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        if not self.leading_icon.isNull():
            y = (self.height() - self._leading_icon_size) // 2
            painter.drawPixmap(self._leading_icon_size // 2, y, self.leading_icon)
        if not self.trailing_icon.isNull():
            y = (self.height() - self._trailing_icon_size) // 2
            x = self.width() - self._trailing_icon_size - 10
            self.trailing_rect = QRect(x, y, self._trailing_icon_size, self._trailing_icon_size)
            if self.trailing_hovered:
                scaled_icon = self.trailing_icon.scaled(
                    self._trailing_icon_size + 4,
                    self._trailing_icon_size + 4,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(x - 2, y - 2, scaled_icon)
            else:
                painter.drawPixmap(x, y, self.trailing_icon)
        painter.end()

    def _load_icon(self, name: str, size: int) -> QPixmap:
        if not name:
            return QPixmap()
        pixmap = QPixmap(icon_path(name))
        if pixmap.isNull():
            return QPixmap()
        return pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _apply_shadow(self) -> None:
        if self._shadow_enabled:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(self._shadow_blur)
            shadow.setOffset(self._shadow_offset_x, self._shadow_offset_y)
            shadow.setColor(self._shadow_color)
            self.setGraphicsEffect(shadow)
        else:
            self.setGraphicsEffect(None)

    def _update_style(self) -> None:
        padding_left = self._padding + (self._leading_icon_size + 8 if self._leading_icon_name else 0)
        padding_right = self._padding + (self._trailing_icon_size + 15 if self._trailing_icon_name else 0)
        self.setStyleSheet(
            "QLineEdit {"
            f"border: {max(1, theme_int(self._theme, 'border_width'))}px solid {self._border_color.name()};"
            f"border-radius: {self._radius}px;"
            f"background-color: {self._background_color.name()};"
            f"color: {self._text_color.name()};"
            f"padding: {self._padding}px;"
            f"padding-left: {padding_left}px;"
            f"padding-right: {padding_right}px;"
            f"font-size: {theme_int(self._theme, 'font_size')}px;"
            "selection-background-color: "
            f"{theme_color(self._theme, 'primary').name()};"
            "}"
            "QLineEdit:focus {"
            f"border-color: {theme_color(self._theme, 'border_focus').name()};"
            "}"
        )
        self._apply_shadow()
        self.update()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, value)
        self._update_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, color: QColor) -> None:
        self._text_color = QColor(color)
        self._update_style()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, color: QColor) -> None:
        self._background_color = QColor(color)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, color: QColor) -> None:
        self._border_color = QColor(color)
        self._update_style()

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._background_color = theme_color(self._theme, "control")
        self._text_color = theme_color(self._theme, "text")
        self._border_color = theme_color(self._theme, "border")
        self._radius = theme_radius(self._theme)
        self._shadow_color = theme_color(self._theme, "shadow")
        self._shadow_blur = 14 if self._theme in {"ios", "material"} else 6
        self._shadow_offset_x = 0
        self._shadow_offset_y = 3 if self._theme in {"ios", "material"} else 1
        self.setMinimumHeight(theme_int(self._theme, "control_height"))
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

    def getPadding(self) -> int:
        return self._padding

    def setPadding(self, padding: int) -> None:
        self._padding = max(0, padding)
        self._update_style()

    def getLeadingIcon(self) -> str:
        return self._leading_icon_name

    def setLeadingIcon(self, name: str) -> None:
        self._leading_icon_name = name or ""
        self.leading_icon = self._load_icon(self._leading_icon_name, self._leading_icon_size)
        self._update_style()

    def getLeadingIconSize(self) -> int:
        return self._leading_icon_size

    def setLeadingIconSize(self, size: int) -> None:
        self._leading_icon_size = max(1, size)
        self.leading_icon = self._load_icon(self._leading_icon_name, self._leading_icon_size)
        self._update_style()

    def getTrailingIcon(self) -> str:
        return self._trailing_icon_name

    def setTrailingIcon(self, name: str) -> None:
        self._trailing_icon_name = name or ""
        self.trailing_icon = self._load_icon(self._trailing_icon_name, self._trailing_icon_size)
        self._update_style()

    def getTrailingIconSize(self) -> int:
        return self._trailing_icon_size

    def setTrailingIconSize(self, size: int) -> None:
        self._trailing_icon_size = max(1, size)
        self.trailing_icon = self._load_icon(self._trailing_icon_name, self._trailing_icon_size)
        self._update_style()

    def getShadowEnabled(self) -> bool:
        return self._shadow_enabled

    def setShadowEnabled(self, enabled: bool) -> None:
        self._shadow_enabled = bool(enabled)
        self._apply_shadow()

    def getShadowBlur(self) -> int:
        return self._shadow_blur

    def setShadowBlur(self, value: int) -> None:
        self._shadow_blur = max(0, value)
        self._apply_shadow()

    def getShadowOffsetX(self) -> int:
        return self._shadow_offset_x

    def setShadowOffsetX(self, value: int) -> None:
        self._shadow_offset_x = value
        self._apply_shadow()

    def getShadowOffsetY(self) -> int:
        return self._shadow_offset_y

    def setShadowOffsetY(self, value: int) -> None:
        self._shadow_offset_y = value
        self._apply_shadow()

    def getShadowColor(self) -> QColor:
        return QColor(self._shadow_color)

    def setShadowColor(self, color: QColor) -> None:
        self._shadow_color = QColor(color)
        self._apply_shadow()

    radius = pyqtProperty(int, getRadius, setRadius)
    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=True, stored=False)
    themeIndexHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeOptions = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeName = pyqtProperty(str, getThemeName, setThemeName, designable=False)
    themePreset = pyqtProperty(ThemePreset, getThemePreset, setThemePreset, designable=False, notify=themePresetChanged)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    padding = pyqtProperty(int, getPadding, setPadding)
    leadingIcon = pyqtProperty(str, getLeadingIcon, setLeadingIcon)
    leadingIconSize = pyqtProperty(int, getLeadingIconSize, setLeadingIconSize)
    trailingIcon = pyqtProperty(str, getTrailingIcon, setTrailingIcon)
    trailingIconSize = pyqtProperty(int, getTrailingIconSize, setTrailingIconSize)
    shadowEnabled = pyqtProperty(bool, getShadowEnabled, setShadowEnabled)
    shadowBlur = pyqtProperty(int, getShadowBlur, setShadowBlur)
    shadowOffsetX = pyqtProperty(int, getShadowOffsetX, setShadowOffsetX)
    shadowOffsetY = pyqtProperty(int, getShadowOffsetY, setShadowOffsetY)
    shadowColor = pyqtProperty(QColor, getShadowColor, setShadowColor)
