from __future__ import annotations

from enum import IntEnum

from PyQt6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSize, Qt, pyqtEnum, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QKeyEvent, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QComboBox, QFrame, QListView, QStyle, QStyledItemDelegate, QVBoxLayout

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
    def __init__(self, combo, parent=None) -> None:
        super().__init__(parent)
        self._combo = combo

    def paint(self, painter, option, index) -> None:
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        text = index.data(Qt.ItemDataRole.DisplayRole)
        combo = self._combo
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

    def sizeHint(self, option, index) -> QSize:
        hint = super().sizeHint(option, index)
        return QSize(hint.width(), max(40, hint.height()))


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



class MonkezComboPopup(QFrame):
    def __init__(self, combo) -> None:
        flags = (
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        super().__init__(combo.window(), flags)
        self._combo = combo
        self.setObjectName("monkezComboPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setAutoFillBackground(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._event_filter_installed = False

        self.view = MonkezComboListView(combo, self)
        self.view.setModel(combo.model())
        self.view.setRootIndex(combo.rootModelIndex())
        self.view.setModelColumn(combo.modelColumn())
        self.view.setItemDelegate(MonkezComboItemDelegate(combo, self.view))
        self.view.clicked.connect(self._activate_index)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        layout.addWidget(self.view)

    def sync_and_show(self) -> None:
        combo = self._combo
        owner = combo.window()
        if owner is not None and self.parentWidget() is not owner:
            self.setParent(owner, self.windowFlags())
        self.view.setModel(combo.model())
        self.view.setRootIndex(combo.rootModelIndex())
        self.view.setModelColumn(combo.modelColumn())

        current = combo.model().index(combo.currentIndex(), combo.modelColumn(), combo.rootModelIndex())
        if current.isValid():
            self.view.setCurrentIndex(current)
            self.view.scrollTo(current, QListView.ScrollHint.EnsureVisible)

        row_count = combo.model().rowCount(combo.rootModelIndex())
        visible_rows = max(1, min(combo.maxVisibleItems(), row_count))
        self.view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            if row_count <= combo.maxVisibleItems()
            else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        row_height = self.view.sizeHintForRow(0) if row_count else 40
        content_height = visible_rows * max(40, row_height) + max(0, visible_rows - 1) * self.view.spacing()
        popup_height = content_height + 24
        popup_width = max(combo.width(), self.view.sizeHintForColumn(combo.modelColumn()) + 48)

        global_position = combo.mapToGlobal(QPoint(0, combo.height() + 4))
        screen = combo.screen()
        if screen is not None:
            available = screen.availableGeometry()
            popup_width = min(popup_width, available.width())
            popup_height = min(popup_height, available.height())
            if global_position.y() + popup_height > available.bottom():
                global_position.setY(combo.mapToGlobal(QPoint(0, -popup_height - 4)).y())
            global_position.setX(min(max(global_position.x(), available.left()), available.right() - popup_width + 1))

        self.resize(popup_width, popup_height)
        self.move(global_position)
        app = QApplication.instance()
        if app is not None and not self._event_filter_installed:
            app.installEventFilter(self)
            self._event_filter_installed = True
        self.show()
        self.raise_()
        self.view.setFocus(Qt.FocusReason.PopupFocusReason)
        self.update()

    def dismiss(self) -> None:
        if not self.isVisible():
            return
        self.hide()

    def hideEvent(self, event) -> None:
        app = QApplication.instance()
        if app is not None and self._event_filter_installed:
            app.removeEventFilter(self)
            self._event_filter_installed = False
        self._combo._popup_hidden()
        super().hideEvent(event)

    def _activate_index(self, index) -> None:
        if index.isValid():
            self._combo.setCurrentIndex(index.row())
            self._combo.activated.emit(index.row())
        self.dismiss()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress and self.isVisible():
            global_position = event.globalPosition().toPoint()
            popup_rect = QRect(self.mapToGlobal(QPoint()), self.size())
            combo_rect = QRect(self._combo.mapToGlobal(QPoint()), self._combo.size())
            if not popup_rect.contains(global_position) and not combo_rect.contains(global_position):
                self.dismiss()
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._activate_index(self.view.currentIndex())
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        border_width = max(1, theme_int(self._combo._theme, "border_width"))
        inset = border_width / 2
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        radius = float(getattr(self._combo, "_border_radius", 8))
        background = self._combo._background_color
        border = theme_color(self._combo._theme, "border_focus")

        painter.setPen(QPen(border, border_width))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()


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

        self._popup = MonkezComboPopup(self)
        self.destroyed.connect(self._popup.deleteLater)
        self.addItems(["Option 1", "Option 2", "Option 3"])
        self.setMinimumSize(150, 36)
        self.setTheme(self._theme)
        self._update_style()

    def showPopup(self) -> None:
        if self._popup.isVisible():
            self._popup.dismiss()
            return
        self.is_opened = True
        self._update_style()
        self._popup.sync_and_show()

    def hidePopup(self) -> None:
        self._popup.dismiss()

    def _popup_hidden(self) -> None:
        self.is_opened = False
        self._update_style()

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
        self._popup.view.setStyleSheet(
            "QListView {"
            "border: none;"
            "background-color: transparent;"
            f"color: {self._text_color.name()};"
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
            "QScrollBar:vertical {"
            "background: transparent;"
            "border: 0;"
            "width: 8px;"
            "margin: 4px 1px;"
            "}"
            "QScrollBar::handle:vertical {"
            f"background: {theme_color(self._theme, 'muted').name()};"
            "border-radius: 4px;"
            "min-height: 24px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        )
        self._popup.update()
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
