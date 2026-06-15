from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QComboBox, QFrame, QListView, QStyle, QStyledItemDelegate

from .themes import (
    normalize_theme,
    theme_color,
    theme_from_preset,
    theme_int,
    theme_options_text,
    theme_radius,
    theme_to_preset,
)


class MonkezComboItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        text = index.data(Qt.ItemDataRole.DisplayRole)
        combo = self.parent()
        hover_background = getattr(combo, "_hover_background_color", QColor("#ebf3fd"))
        text_color = getattr(combo, "_text_color", QColor("#2c3e50"))
        hover_text_color = getattr(combo, "_hover_text_color", QColor("#3498db"))

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect.adjusted(6, 2, -6, -2), hover_background)
            resolved_text_color = hover_text_color
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect.adjusted(6, 2, -6, -2), hover_background)
            resolved_text_color = hover_text_color
        else:
            resolved_text_color = text_color

        if icon and not icon.isNull():
            icon_size = 24
            icon_rect = QRect(
                option.rect.x() + 12,
                option.rect.y() + (option.rect.height() - icon_size) // 2,
                icon_size,
                icon_size,
            )
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)
            text_x = icon_rect.right() + 12
        else:
            text_x = option.rect.x() + 12

        text_rect = QRect(text_x, option.rect.y(), option.rect.right() - text_x - 12, option.rect.height())
        painter.setPen(resolved_text_color)
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, str(text))


class MonkezComboListView(QListView):
    def __init__(self, combo, parent=None) -> None:
        super().__init__(parent)
        self._combo = combo
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.viewport().rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = float(getattr(self._combo, "_border_radius", 8))
        background = getattr(self._combo, "_background_color", QColor("white"))
        border = theme_color(getattr(self._combo, "_theme", "material"), "border_focus")
        border_width = max(1, theme_int(getattr(self._combo, "_theme", "material"), "border_width"))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(QPen(border, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()
        super().paintEvent(event)


class MonkezComboBox(QComboBox):
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
        self.is_opened = False
        self._theme = "material"
        self._border_color = QColor("#5b8dae")
        self._background_color = QColor("white")
        self._hover_background_color = QColor("#f8f9fa")
        self._text_color = QColor("#2c3e50")
        self._hover_text_color = QColor("#3498db")
        self._border_radius = 8

        view = MonkezComboListView(self, self)
        self.setView(view)
        self.setItemDelegate(MonkezComboItemDelegate(self))
        self.addItems(["Option 1", "Option 2", "Option 3"])
        self.setMinimumSize(150, 36)
        self.setTheme(self._theme)
        self._update_style()

    def showPopup(self) -> None:
        self.is_opened = True
        self._update_style()
        super().showPopup()
        popup = self.view().window()
        popup.setAutoFillBackground(False)
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def hidePopup(self) -> None:
        self.is_opened = False
        self._update_style()
        super().hidePopup()

    def _update_style(self) -> None:
        self.setStyleSheet(
            "QComboBox {"
            f"border: {max(1, theme_int(self._theme, 'border_width'))}px solid {self._border_color.name()};"
            f"border-radius: {self._border_radius}px;"
            "padding: 7px 12px;"
            "padding-right: 40px;"
            f"background-color: {self._background_color.name()};"
            f"color: {self._text_color.name()};"
            f"min-height: {max(20, theme_int(self._theme, 'control_height') - 18)}px;"
            f"font-size: {theme_int(self._theme, 'font_size')}px;"
            "}"
            "QComboBox:hover {"
            f"background-color: {self._hover_background_color.name()};"
            f"border-color: {theme_color(self._theme, 'border_focus').name()};"
            f"color: {self._text_color.name()};"
            "}"
            "QComboBox::drop-down {"
            "subcontrol-origin: padding;"
            "subcontrol-position: top right;"
            "width: 38px;"
            "border-left: 0px;"
            "background-color: transparent;"
            "}"
            "QComboBox::drop-down:hover, QComboBox::drop-down:on {"
            "background-color: transparent;"
            "}"
            "QComboBox::down-arrow { width: 0px; height: 0px; border: none; background: none; }"
        )
        self.view().setStyleSheet(
            "QListView {"
            "border: none;"
            "background-color: transparent;"
            f"color: {self._text_color.name()};"
            "padding: 8px 0px;"
            "outline: 0;"
            "}"
            "QListView::item {"
            "min-height: 30px;"
            "padding: 4px 12px;"
            f"border-radius: {max(3, self._border_radius - 3)}px;"
            "margin: 0px 6px;"
            "}"
            "QListView::item:hover,"
            "QListView::item:selected {"
            f"background-color: {self._hover_background_color.name()};"
            f"color: {self._hover_text_color.name()};"
            "}"
        )
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._paint_chevron()

    def _paint_chevron(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        arrow_rect = QRectF(self.width() - 36, 0, 24, self.height())
        center = arrow_rect.center()
        half_width = 5.5
        half_height = 3.5

        if self.is_opened:
            points = (
                QPointF(center.x() - half_width, center.y() + half_height / 2),
                QPointF(center.x(), center.y() - half_height),
                QPointF(center.x() + half_width, center.y() + half_height / 2),
            )
        else:
            points = (
                QPointF(center.x() - half_width, center.y() - half_height / 2),
                QPointF(center.x(), center.y() + half_height),
                QPointF(center.x() + half_width, center.y() - half_height / 2),
            )

        path = QPainterPath(points[0])
        path.lineTo(points[1])
        path.lineTo(points[2])

        color = theme_color(self._theme, "primary") if self.is_opened else QColor(self._text_color)
        pen = QPen(color, 2.1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.end()

    def addItemWithIcon(self, icon_path: str, text: str, data=None) -> None:
        self.addItem(QIcon(icon_path), text, data)

    def addItemWithPixmap(self, pixmap: QPixmap, text: str, data=None) -> None:
        self.addItem(QIcon(pixmap), text, data)

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, color: QColor) -> None:
        self._border_color = QColor(color)
        self._update_style()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, color: QColor) -> None:
        self._background_color = QColor(color)
        self._update_style()

    def getHoverBackgroundColor(self) -> QColor:
        return QColor(self._hover_background_color)

    def setHoverBackgroundColor(self, color: QColor) -> None:
        self._hover_background_color = QColor(color)
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

    def getBorderRadius(self) -> int:
        return self._border_radius

    def setBorderRadius(self, radius: int) -> None:
        self._border_radius = max(0, radius)
        self._update_style()

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        previous = self._theme
        self._theme = normalize_theme(value)
        self._border_color = theme_color(self._theme, "border")
        self._background_color = theme_color(self._theme, "control")
        self._hover_background_color = theme_color(self._theme, "secondary")
        self._text_color = theme_color(self._theme, "text")
        self._hover_text_color = theme_color(self._theme, "primary")
        self._border_radius = theme_radius(self._theme)
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

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=True, stored=False)
    themeIndexHint = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeOptions = pyqtProperty(str, getThemeOptions, setThemeOptions, designable=False, stored=False)
    themeName = pyqtProperty(str, getThemeName, setThemeName, designable=False)
    themePreset = pyqtProperty(ThemePreset, getThemePreset, setThemePreset, designable=False, notify=themePresetChanged)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    hoverBackgroundColor = pyqtProperty(QColor, getHoverBackgroundColor, setHoverBackgroundColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    hoverTextColor = pyqtProperty(QColor, getHoverTextColor, setHoverTextColor)
    borderRadius = pyqtProperty(int, getBorderRadius, setBorderRadius)
