from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget

from .theme_support import ThemeSupportMixin
from .themes import color_to_css, theme_color, theme_radius


class MonkezSegmentedControl(QWidget, ThemeSupportMixin):
    """Mutually-exclusive text segments with keyboard-friendly buttons."""

    themeChanged = pyqtSignal(str)
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._items = ["Camera", "Result", "History"]
        self._current_index = 0
        self._radius = 8
        self._background_color = QColor()
        self._text_color = QColor()
        self._active_color = QColor()
        self._active_text_color = QColor()
        self._border_color = QColor()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.setCurrentIndex)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setTheme("material")
        self._rebuild()

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        width = sum(max(72, metrics.horizontalAdvance(item) + 28) for item in self._items)
        return QSize(width, 40)

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._text_color = theme_color(self._theme, "text")
        self._active_color = theme_color(self._theme, "primary")
        self._active_text_color = theme_color(self._theme, "on_primary")
        self._border_color = theme_color(self._theme, "border")
        self._radius = theme_radius(self._theme)
        self._refresh_style()

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self._group.removeButton(widget)
                widget.deleteLater()
        for index, text in enumerate(self._items):
            button = QPushButton(text, self)
            if len(self._items) == 1:
                button.setObjectName("segmentOnly")
            elif index == 0:
                button.setObjectName("segmentFirst")
            elif index == len(self._items) - 1:
                button.setObjectName("segmentLast")
            else:
                button.setObjectName("segmentMiddle")
            button.setCheckable(True)
            button.setChecked(index == self._current_index)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._group.addButton(button, index)
            self._layout.addWidget(button)
        self._refresh_style()
        self.updateGeometry()

    def _refresh_style(self) -> None:
        self.setStyleSheet(
            "MonkezSegmentedControl { background: transparent; }"
            "MonkezSegmentedControl QPushButton {"
            f"background: {color_to_css(self._background_color)};"
            f"color: {color_to_css(self._text_color)};"
            f"border: 1px solid {color_to_css(self._border_color)};"
            "border-right-width: 0px; padding: 8px 14px; min-height: 20px;"
            "}"
            "MonkezSegmentedControl QPushButton#segmentFirst {"
            f"border-top-left-radius: {self._radius}px; border-bottom-left-radius: {self._radius}px;"
            "}"
            "MonkezSegmentedControl QPushButton#segmentLast {"
            f"border-top-right-radius: {self._radius}px; border-bottom-right-radius: {self._radius}px;"
            "border-right-width: 1px;"
            "}"
            "MonkezSegmentedControl QPushButton#segmentOnly {"
            f"border-radius: {self._radius}px; border-right-width: 1px;"
            "}"
            "MonkezSegmentedControl QPushButton:checked {"
            f"background: {color_to_css(self._active_color)};"
            f"color: {color_to_css(self._active_text_color)};"
            f"border-color: {color_to_css(self._active_color)};"
            "font-weight: 600;"
            "}"
        )

    def getItems(self) -> str:
        return " | ".join(self._items)

    def setItems(self, value: str) -> None:
        items = [part.strip() for part in str(value).split("|") if part.strip()]
        if not items:
            items = ["Item"]
        self._items = items
        self._current_index = min(self._current_index, len(items) - 1)
        self._rebuild()

    def getCurrentIndex(self) -> int:
        return self._current_index

    def setCurrentIndex(self, value: int) -> None:
        index = max(0, min(len(self._items) - 1, int(value)))
        if index == self._current_index:
            button = self._group.button(index)
            if button is not None:
                button.setChecked(True)
            return
        self._current_index = index
        button = self._group.button(index)
        if button is not None:
            button.setChecked(True)
        self.currentIndexChanged.emit(index)

    def currentText(self) -> str:
        return self._items[self._current_index]

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._refresh_style()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._refresh_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self._refresh_style()

    def getActiveColor(self) -> QColor:
        return QColor(self._active_color)

    def setActiveColor(self, value: QColor) -> None:
        self._active_color = QColor(value)
        self._refresh_style()

    def getActiveTextColor(self) -> QColor:
        return QColor(self._active_text_color)

    def setActiveTextColor(self, value: QColor) -> None:
        self._active_text_color = QColor(value)
        self._refresh_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self._refresh_style()

    items = pyqtProperty(str, getItems, setItems)
    currentIndex = pyqtProperty(int, getCurrentIndex, setCurrentIndex, notify=currentIndexChanged)
    radius = pyqtProperty(int, getRadius, setRadius)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    activeColor = pyqtProperty(QColor, getActiveColor, setActiveColor)
    activeTextColor = pyqtProperty(QColor, getActiveTextColor, setActiveTextColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)


class MonkezBreadcrumb(QWidget, ThemeSupportMixin):
    """Clickable breadcrumb path with a compact paint-only implementation."""

    themeChanged = pyqtSignal(str)
    activated = pyqtSignal(int, str)
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._items = ["Home", "Cameras", "Camera 01"]
        self._separator = "/"
        self._current_index = 2
        self._spacing = 8
        self._text_color = QColor()
        self._current_color = QColor()
        self._separator_color = QColor()
        self._hover_color = QColor()
        self._hover_index = -1
        self._item_rects: list[QRectF] = []
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        width = sum(metrics.horizontalAdvance(item) for item in self._items)
        width += max(0, len(self._items) - 1) * (metrics.horizontalAdvance(self._separator) + self._spacing * 2)
        return QSize(max(140, width + 12), max(34, metrics.height() + 12))

    def _apply_theme(self) -> None:
        self._text_color = theme_color(self._theme, "muted")
        self._current_color = theme_color(self._theme, "text")
        self._separator_color = theme_color(self._theme, "border")
        self._hover_color = theme_color(self._theme, "primary")
        self.update()

    def _layout_items(self) -> tuple[list[QRectF], list[QRectF]]:
        metrics = self.fontMetrics()
        y = (self.height() - metrics.height()) / 2
        x = 6.0
        items: list[QRectF] = []
        separators: list[QRectF] = []
        for index, item in enumerate(self._items):
            width = metrics.horizontalAdvance(item) + 4
            items.append(QRectF(x, y, width, metrics.height()))
            x += width
            if index < len(self._items) - 1:
                sep_width = metrics.horizontalAdvance(self._separator) + self._spacing * 2
                separators.append(QRectF(x, y, sep_width, metrics.height()))
                x += sep_width
        return items, separators

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._item_rects, separators = self._layout_items()
        for index, rect in enumerate(self._item_rects):
            font = painter.font()
            font.setBold(index == self._current_index)
            painter.setFont(font)
            if index == self._hover_index:
                painter.setPen(self._hover_color)
            elif index == self._current_index:
                painter.setPen(self._current_color)
            else:
                painter.setPen(self._text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._items[index])
            if index < len(separators):
                painter.setPen(QPen(self._separator_color, 1))
                painter.drawText(separators[index], Qt.AlignmentFlag.AlignCenter, self._separator)

    def _item_at(self, position) -> int:
        self._item_rects, _ = self._layout_items()
        for index, rect in enumerate(self._item_rects):
            if rect.adjusted(-3, -4, 3, 4).contains(position):
                return index
        return -1

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        index = self._item_at(event.position())
        if index != self._hover_index:
            self._hover_index = index
            self.setCursor(Qt.CursorShape.PointingHandCursor if index >= 0 else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_index = -1
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._item_at(event.position())
            if index >= 0:
                self.setCurrentIndex(index)
                self.activated.emit(index, self._items[index])
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def getItems(self) -> str:
        return " | ".join(self._items)

    def setItems(self, value: str) -> None:
        items = [part.strip() for part in str(value).split("|") if part.strip()]
        self._items = items or ["Home"]
        self._current_index = min(self._current_index, len(self._items) - 1)
        self.updateGeometry()
        self.update()

    def getSeparator(self) -> str:
        return self._separator

    def setSeparator(self, value: str) -> None:
        self._separator = str(value) or "/"
        self.updateGeometry()
        self.update()

    def getCurrentIndex(self) -> int:
        return self._current_index

    def setCurrentIndex(self, value: int) -> None:
        index = max(0, min(len(self._items) - 1, int(value)))
        if index == self._current_index:
            return
        self._current_index = index
        self.currentIndexChanged.emit(index)
        self.update()

    def getSpacing(self) -> int:
        return self._spacing

    def setSpacing(self, value: int) -> None:
        self._spacing = max(0, min(40, int(value)))
        self.updateGeometry()
        self.update()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self.update()

    def getCurrentColor(self) -> QColor:
        return QColor(self._current_color)

    def setCurrentColor(self, value: QColor) -> None:
        self._current_color = QColor(value)
        self.update()

    def getSeparatorColor(self) -> QColor:
        return QColor(self._separator_color)

    def setSeparatorColor(self, value: QColor) -> None:
        self._separator_color = QColor(value)
        self.update()

    def getHoverColor(self) -> QColor:
        return QColor(self._hover_color)

    def setHoverColor(self, value: QColor) -> None:
        self._hover_color = QColor(value)
        self.update()

    items = pyqtProperty(str, getItems, setItems)
    separator = pyqtProperty(str, getSeparator, setSeparator)
    currentIndex = pyqtProperty(int, getCurrentIndex, setCurrentIndex, notify=currentIndexChanged)
    spacing = pyqtProperty(int, getSpacing, setSpacing)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    currentColor = pyqtProperty(QColor, getCurrentColor, setCurrentColor)
    separatorColor = pyqtProperty(QColor, getSeparatorColor, setSeparatorColor)
    hoverColor = pyqtProperty(QColor, getHoverColor, setHoverColor)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
