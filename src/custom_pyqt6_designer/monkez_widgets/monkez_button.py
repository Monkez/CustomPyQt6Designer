from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QSize, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

from .themes import (
    normalize_theme,
    theme_color,
    theme_from_preset,
    theme_int,
    theme_options_text,
    theme_radius,
    theme_to_preset,
)


BUTTON_TYPE_NAMES = ("filled", "outlined", "text")
BUTTON_TYPE_OPTIONS_TEXT = "0 Filled | 1 Outlined | 2 Text"


class MonkezButton(QPushButton):
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
        self._radius = 15
        self._button_type = "filled"
        self._active = True
        self._active_color = QColor(0, 170, 0, 255)
        self._surface_color = QColor("#ffffff")
        self._border_color = QColor("#1976d2")
        self._deactive_color = QColor(170, 0, 0, 255)
        self._text_color = QColor("white")
        self._hover_text_color = QColor(255, 255, 0)
        self._padding_x = 4
        self._padding_y = 2
        self._shadow_enabled = True
        self._shadow_blur = 10
        self._shadow_offset_x = 1
        self._shadow_offset_y = 1
        self._shadow_color = QColor(0, 0, 0, 100)
        self._hovered = False
        self._pressed = False

        self.setText("Monkez Button")
        self.setMinimumSize(0, 0)
        self.setMouseTracking(True)
        self.setTheme(self._theme)
        self._apply_shadow()
        self._update_style()

    def sizeHint(self) -> QSize:
        return QSize(130, 40)

    def minimumSizeHint(self) -> QSize:
        return QSize(24, 24)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._pressed = True
        self._update_style()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._pressed = False
        self._update_style()
        super().mouseReleaseEvent(event)

    def _apply_shadow(self) -> None:
        if self._shadow_enabled:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(self._shadow_blur)
            shadow.setOffset(self._shadow_offset_x, self._shadow_offset_y)
            shadow.setColor(self._shadow_color)
            self.setGraphicsEffect(shadow)
        else:
            self.setGraphicsEffect(None)

    def _hover_background(self, color: QColor) -> QColor:
        hovered = QColor(color).lighter(112)
        hovered.setAlpha(color.alpha())
        return hovered

    def _pressed_background(self, color: QColor) -> QColor:
        pressed = QColor(color).darker(108)
        pressed.setAlpha(color.alpha())
        return pressed

    def _tinted_surface(self, tint: QColor, alpha: int) -> QColor:
        color = QColor(tint)
        color.setAlpha(max(0, min(255, alpha)))
        return color

    def _blend(self, base: QColor, tint: QColor, amount: float) -> QColor:
        amount = max(0.0, min(1.0, amount))
        mixed = QColor(
            round(base.red() * (1.0 - amount) + tint.red() * amount),
            round(base.green() * (1.0 - amount) + tint.green() * amount),
            round(base.blue() * (1.0 - amount) + tint.blue() * amount),
            base.alpha(),
        )
        return mixed

    def _rgba(self, color: QColor) -> str:
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"

    def _update_style(self) -> None:
        bg_color = QColor(self._active_color if self._active else self._deactive_color)
        hover_color = self._hover_background(bg_color)
        pressed_color = self._pressed_background(bg_color)
        bg = pressed_color if self._pressed else hover_color if self._hovered else bg_color
        text_color = self._hover_text_color if self._hovered or self._pressed else self._text_color
        border_color = self._border_color if self._active else self._deactive_color
        padding_y = self._padding_y
        padding_x = self._padding_x

        if self._button_type == "outlined":
            outline_bg = QColor(self._surface_color)
            if self._pressed:
                outline_bg = self._blend(self._surface_color, border_color, 0.16)
            elif self._hovered:
                outline_bg = self._blend(self._surface_color, border_color, 0.09)
            border = self._pressed_background(border_color) if self._pressed else border_color
            self.setStyleSheet(
                "QPushButton {"
                f"border-radius: {self._radius}px;"
                f"background-color: {self._rgba(outline_bg)};"
                f"color: {border.name()};"
                f"border: {max(1, theme_int(self._theme, 'border_width'))}px solid {border.name()};"
                f"padding: {padding_y}px {padding_x}px;"
                "}"
            )
        elif self._button_type == "text":
            text_bg = QColor(0, 0, 0, 0)
            if self._pressed:
                text_bg = self._tinted_surface(border_color, 30)
            elif self._hovered:
                text_bg = self._tinted_surface(border_color, 18)
            self.setStyleSheet(
                "QPushButton {"
                f"border-radius: {self._radius}px;"
                f"background-color: {self._rgba(text_bg)};"
                f"color: {border_color.name()};"
                "border: none;"
                f"padding: {padding_y}px {padding_x}px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                f"border-radius: {self._radius}px;"
                f"background-color: {self._rgba(bg)};"
                f"color: {text_color.name()};"
                "border: none;"
                f"padding: {padding_y}px {padding_x}px;"
                "}"
            )

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, value)
        self._update_style()

    def getButtonType(self) -> str:
        return self._button_type

    def setButtonType(self, value: str) -> None:
        value = (value or "filled").strip().lower()
        if value.isdigit():
            self.setButtonTypeIndex(int(value))
            return
        if value not in BUTTON_TYPE_NAMES:
            value = "filled"
        self._button_type = value
        self._update_style()

    def getButtonTypeIndex(self) -> int:
        return BUTTON_TYPE_NAMES.index(self._button_type)

    def setButtonTypeIndex(self, value: int) -> None:
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = 0
        if not 0 <= index < len(BUTTON_TYPE_NAMES):
            index = 0
        self.setButtonType(BUTTON_TYPE_NAMES[index])

    def getButtonTypeOptions(self) -> str:
        return BUTTON_TYPE_OPTIONS_TEXT

    def setButtonTypeOptions(self, value: str) -> None:
        return None

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._active_color = theme_color(self._theme, "primary")
        self._surface_color = theme_color(self._theme, "surface")
        self._border_color = theme_color(self._theme, "border_focus")
        self._deactive_color = theme_color(self._theme, "danger")
        self._text_color = theme_color(self._theme, "on_primary")
        self._hover_text_color = theme_color(self._theme, "on_primary")
        self._radius = theme_radius(self._theme)
        self._shadow_color = theme_color(self._theme, "shadow")
        self._shadow_blur = 18 if self._theme in {"ios", "material"} else 8
        self._shadow_offset_y = 4 if self._theme in {"ios", "material"} else 1
        self._apply_shadow()
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

    def getActive(self) -> bool:
        return self._active

    def setActive(self, value: bool) -> None:
        self._active = bool(value)
        self._update_style()

    def getActiveColor(self) -> QColor:
        return QColor(self._active_color)

    def setActiveColor(self, color: QColor) -> None:
        self._active_color = QColor(color)
        self._update_style()

    def getDeactiveColor(self) -> QColor:
        return QColor(self._deactive_color)

    def setDeactiveColor(self, color: QColor) -> None:
        self._deactive_color = QColor(color)
        self._update_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, color: QColor) -> None:
        self._text_color = QColor(color)
        self._update_style()

    def getHoverTextColor(self) -> QColor:
        return QColor(self._hover_text_color)

    def setHoverTextColor(self, color: QColor) -> None:
        self._hover_text_color = QColor(color)
        self._update_style()

    def getPaddingX(self) -> int:
        return self._padding_x

    def setPaddingX(self, value: int) -> None:
        self._padding_x = max(0, int(value))
        self._update_style()

    def getPaddingY(self) -> int:
        return self._padding_y

    def setPaddingY(self, value: int) -> None:
        self._padding_y = max(0, int(value))
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
    buttonTypeIndex = pyqtProperty(int, getButtonTypeIndex, setButtonTypeIndex)
    buttonTypeHint = pyqtProperty(str, getButtonTypeOptions, setButtonTypeOptions, designable=True, stored=False)
    buttonTypeIndexHint = pyqtProperty(str, getButtonTypeOptions, setButtonTypeOptions, designable=False, stored=False)
    buttonTypeOptions = pyqtProperty(str, getButtonTypeOptions, setButtonTypeOptions, designable=False, stored=False)
    buttonType = pyqtProperty(str, getButtonType, setButtonType, designable=False)
    active = pyqtProperty(bool, getActive, setActive)
    activeColor = pyqtProperty(QColor, getActiveColor, setActiveColor)
    deactiveColor = pyqtProperty(QColor, getDeactiveColor, setDeactiveColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    hoverTextColor = pyqtProperty(QColor, getHoverTextColor, setHoverTextColor)
    paddingX = pyqtProperty(int, getPaddingX, setPaddingX)
    paddingY = pyqtProperty(int, getPaddingY, setPaddingY)
    shadowEnabled = pyqtProperty(bool, getShadowEnabled, setShadowEnabled)
    shadowBlur = pyqtProperty(int, getShadowBlur, setShadowBlur)
    shadowOffsetX = pyqtProperty(int, getShadowOffsetX, setShadowOffsetX)
    shadowOffsetY = pyqtProperty(int, getShadowOffsetY, setShadowOffsetY)
    shadowColor = pyqtProperty(QColor, getShadowColor, setShadowColor)
