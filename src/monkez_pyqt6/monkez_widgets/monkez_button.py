from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QSize, QTimer, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

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


BUTTON_TYPE_NAMES = ("filled", "outlined", "text")
BUTTON_TYPE_OPTIONS_TEXT = "0 Filled | 1 Outlined | 2 Text"
BUTTON_STYLE_NAMES = ("standard", "icon")
BUTTON_STYLE_OPTIONS_TEXT = "0 Standard | 1 Icon only"


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
    loadingChanged = pyqtSignal(bool)
    iconTextChanged = pyqtSignal(str)

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
        self._text_color_uses_theme = True
        self._hover_text_color_uses_theme = True
        self._padding_x = 4
        self._padding_y = 2
        self._shadow_enabled = True
        self._shadow_blur = 10
        self._shadow_offset_x = 1
        self._shadow_offset_y = 1
        self._shadow_color = QColor(0, 0, 0, 100)
        self._hovered = False
        self._pressed = False
        self._style = "standard"
        self._icon_text = "⋯"
        self._button_size = 40
        self._loading = False
        self._loading_text = "Loading"
        self._idle_text = "Monkez Button"
        self._loading_dot_count = 0
        self._disable_while_loading = True
        self._enabled_before_loading = True
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(350)
        self._loading_timer.timeout.connect(self._advance_loading)

        self.setText("Monkez Button")
        self.setMinimumSize(0, 0)
        self.setMouseTracking(True)
        self.setTheme(self._theme)
        self._apply_shadow()
        self._update_style()

    def sizeHint(self) -> QSize:
        if self._style == "icon":
            return QSize(self._button_size, self._button_size)
        return QSize(130, 40)

    def minimumSizeHint(self) -> QSize:
        return QSize(24, 24)

    def setText(self, text: str) -> None:
        self._idle_text = str(text)
        if not self._loading and self._style == "standard":
            super().setText(self._idle_text)

    def _display_idle_content(self) -> None:
        text = self._icon_text if self._style == "icon" else self._idle_text
        super().setText(text)

    def _advance_loading(self) -> None:
        self._loading_dot_count = self._loading_dot_count % 3 + 1
        dots = "." * self._loading_dot_count
        super().setText(dots if self._style == "icon" else self._loading_text + dots)

    def getStyle(self) -> str:
        return self._style

    def setStyle(self, value: str) -> None:
        value = (value or "standard").strip().lower()
        if value.isdigit():
            self.setStyleIndex(int(value))
            return
        if value not in BUTTON_STYLE_NAMES:
            value = "standard"
        if value == self._style:
            return
        self._style = value
        if value == "icon":
            self.setMinimumSize(self._button_size, self._button_size)
            self.setMaximumSize(self._button_size, self._button_size)
            self.setAccessibleName(self.toolTip() or self._icon_text)
        else:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
        if not self._loading:
            self._display_idle_content()
        self.updateGeometry()

    def getStyleIndex(self) -> int:
        return BUTTON_STYLE_NAMES.index(self._style)

    def setStyleIndex(self, value: int) -> None:
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = 0
        if not 0 <= index < len(BUTTON_STYLE_NAMES):
            index = 0
        self.setStyle(BUTTON_STYLE_NAMES[index])

    def getStyleOptions(self) -> str:
        return BUTTON_STYLE_OPTIONS_TEXT

    def setStyleOptions(self, value: str) -> None:
        return None

    def getIconText(self) -> str:
        return self._icon_text

    def setIconText(self, value: str) -> None:
        value = str(value)
        if value == self._icon_text:
            return
        self._icon_text = value
        if self._style == "icon" and not self._loading:
            super().setText(value)
        self.setAccessibleName(self.toolTip() or value)
        self.iconTextChanged.emit(value)

    def getButtonSize(self) -> int:
        return self._button_size

    def setButtonSize(self, value: int) -> None:
        self._button_size = max(24, min(128, int(value)))
        if self._style == "icon":
            self.setMinimumSize(self._button_size, self._button_size)
            self.setMaximumSize(self._button_size, self._button_size)
        self.updateGeometry()

    def getLoading(self) -> bool:
        return self._loading

    def setLoading(self, value: bool) -> None:
        loading = bool(value)
        if loading == self._loading:
            return
        self._loading = loading
        self._loading_dot_count = 0
        if loading:
            self._enabled_before_loading = self.isEnabled()
            if self._disable_while_loading:
                self.setEnabled(False)
            self._loading_timer.start()
            self._advance_loading()
        else:
            self._loading_timer.stop()
            if self._disable_while_loading:
                self.setEnabled(self._enabled_before_loading)
            self._display_idle_content()
        self.loadingChanged.emit(loading)

    def getLoadingText(self) -> str:
        return self._loading_text

    def setLoadingText(self, value: str) -> None:
        self._loading_text = str(value)
        if self._loading:
            self._loading_dot_count = 0
            self._advance_loading()

    def getDisableWhileLoading(self) -> bool:
        return self._disable_while_loading

    def setDisableWhileLoading(self, value: bool) -> None:
        disable = bool(value)
        if disable == self._disable_while_loading:
            return
        self._disable_while_loading = disable
        if self._loading:
            self.setEnabled(False if disable else self._enabled_before_loading)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self._pressed = self.isDown() and event.button() == Qt.MouseButton.LeftButton
        self._update_style()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self._pressed = self.isDown()
        self._update_style()

    def keyPressEvent(self, event) -> None:
        super().keyPressEvent(event)
        pressed = self.isDown()
        if pressed != self._pressed:
            self._pressed = pressed
            self._update_style()

    def keyReleaseEvent(self, event) -> None:
        super().keyReleaseEvent(event)
        pressed = self.isDown()
        if pressed != self._pressed:
            self._pressed = pressed
            self._update_style()

    def _apply_shadow(self) -> None:
        if not self._shadow_enabled:
            self.setGraphicsEffect(None)
            return
        shadow = self.graphicsEffect()
        if not isinstance(shadow, QGraphicsDropShadowEffect):
            shadow = QGraphicsDropShadowEffect(self)
            self.setGraphicsEffect(shadow)
        shadow.setBlurRadius(self._shadow_blur)
        shadow.setOffset(self._shadow_offset_x, self._shadow_offset_y)
        shadow.setColor(self._shadow_color)

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

    def _theme_button_text_color(self) -> QColor:
        role = "on_primary" if self._button_type == "filled" else "primary"
        return theme_color(self._theme, role)

    def _refresh_theme_text_colors(self) -> None:
        default = self._theme_button_text_color()
        if self._text_color_uses_theme:
            self._text_color = QColor(default)
        if self._hover_text_color_uses_theme:
            self._hover_text_color = QColor(default)

    def _resolved_text_colors(self) -> tuple[QColor, QColor]:
        normal = QColor(self._text_color)
        hover = QColor(self._hover_text_color)
        if not self._active and self._button_type != "filled":
            if self._text_color_uses_theme:
                normal = QColor(self._deactive_color)
            if self._hover_text_color_uses_theme:
                hover = QColor(self._deactive_color)
        return normal, hover

    def _update_style(self) -> None:
        bg_color = QColor(self._active_color if self._active else self._deactive_color)
        hover_color = self._hover_background(bg_color)
        pressed_color = self._pressed_background(bg_color)
        bg = pressed_color if self._pressed else hover_color if self._hovered else bg_color
        normal_text_color, hover_text_color = self._resolved_text_colors()
        text_color = hover_text_color if self._hovered or self._pressed else normal_text_color
        accent_color = QColor(self._active_color if self._active else self._deactive_color)
        text_button_color = QColor(text_color)
        padding_y = self._padding_y
        padding_x = self._padding_x
        disabled_bg = self._blend(self._surface_color, QColor("#9ca3af"), 0.20)
        disabled_text = QColor("#6b7280")
        disabled_border = QColor("#d1d5db")

        if self._button_type == "outlined":
            outline_bg = QColor(self._surface_color)
            if self._pressed:
                outline_bg = self._blend(self._surface_color, accent_color, 0.16)
            elif self._hovered:
                outline_bg = self._blend(self._surface_color, accent_color, 0.09)
            border = self._pressed_background(accent_color) if self._pressed else accent_color
            self.setStyleSheet(
                "QPushButton {"
                f"border-radius: {self._radius}px;"
                f"background-color: {self._rgba(outline_bg)};"
                f"color: {self._rgba(text_color)};"
                f"border: {max(1, theme_int(self._theme, 'border_width'))}px solid {self._rgba(border)};"
                f"padding: {padding_y}px {padding_x}px;"
                "}"
                "QPushButton:disabled {"
                f"background-color: {self._rgba(disabled_bg)};"
                f"color: {color_to_css(disabled_text)};"
                f"border: {max(1, theme_int(self._theme, 'border_width'))}px solid {color_to_css(disabled_border)};"
                "}"
            )
        elif self._button_type == "text":
            text_bg = QColor(0, 0, 0, 0)
            if self._pressed:
                text_bg = self._tinted_surface(text_button_color, 30)
            elif self._hovered:
                text_bg = self._tinted_surface(text_button_color, 18)
            self.setStyleSheet(
                "QPushButton {"
                f"border-radius: {self._radius}px;"
                f"background-color: {self._rgba(text_bg)};"
                f"color: {color_to_css(text_button_color)};"
                "border: none;"
                f"padding: {padding_y}px {padding_x}px;"
                "}"
                "QPushButton:disabled {"
                "background-color: transparent;"
                f"color: {color_to_css(disabled_text)};"
                "border: none;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                f"border-radius: {self._radius}px;"
                f"background-color: {self._rgba(bg)};"
                f"color: {color_to_css(text_color)};"
                "border: none;"
                f"padding: {padding_y}px {padding_x}px;"
                "}"
                "QPushButton:disabled {"
                f"background-color: {self._rgba(disabled_bg)};"
                f"color: {color_to_css(disabled_text)};"
                "border: none;"
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
        self._refresh_theme_text_colors()
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
        self._text_color_uses_theme = True
        self._hover_text_color_uses_theme = True
        self._refresh_theme_text_colors()
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
        self._text_color_uses_theme = False
        self._update_style()

    def getHoverTextColor(self) -> QColor:
        return QColor(self._hover_text_color)

    def setHoverTextColor(self, color: QColor) -> None:
        self._hover_text_color = QColor(color)
        self._hover_text_color_uses_theme = False
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
    styleIndex = pyqtProperty(int, getStyleIndex, setStyleIndex)
    styleHint = pyqtProperty(str, getStyleOptions, setStyleOptions, designable=True, stored=False)
    styleIndexHint = pyqtProperty(str, getStyleOptions, setStyleOptions, designable=False, stored=False)
    styleOptions = pyqtProperty(str, getStyleOptions, setStyleOptions, designable=False, stored=False)
    buttonStyle = pyqtProperty(str, getStyle, setStyle, designable=False)
    iconText = pyqtProperty(str, getIconText, setIconText, notify=iconTextChanged)
    buttonSize = pyqtProperty(int, getButtonSize, setButtonSize)
    loading = pyqtProperty(bool, getLoading, setLoading, notify=loadingChanged)
    loadingText = pyqtProperty(str, getLoadingText, setLoadingText)
    disableWhileLoading = pyqtProperty(bool, getDisableWhileLoading, setDisableWhileLoading)
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
