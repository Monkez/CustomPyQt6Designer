from __future__ import annotations

import math
from dataclasses import dataclass

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .theme_support import ThemeSupportMixin
from .themes import theme_color, theme_radius


@dataclass(frozen=True)
class _PageButton:
    kind: str
    text: str
    target: int | None
    rect: QRectF
    enabled: bool = True
    active: bool = False


class MonkezPagination(QWidget, ThemeSupportMixin):
    """Theme-aware page navigation with responsive ellipsis and four styles."""

    pageChanged = pyqtSignal(int)
    pageCountChanged = pyqtSignal(int)
    totalItemsChanged = pyqtSignal(int)
    pageSizeChanged = pyqtSignal(int)
    themeChanged = pyqtSignal(str)

    STYLE_NAMES = ("Rounded", "Pill", "Minimal", "Compact")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._current_page = 4
        self._page_count = 12
        self._total_items = 0
        self._page_size = 20
        self._maximum_visible_pages = 5
        self._style_index = 0
        self._show_first_last = False
        self._show_prev_next = True
        self._loop_navigation = False
        self._wheel_navigation = False
        self._button_size = 36
        self._spacing = 6
        self._radius = 8
        self._previous_text = "‹"
        self._next_text = "›"
        self._background_color = QColor()
        self._text_color = QColor()
        self._active_color = QColor()
        self._active_text_color = QColor()
        self._hover_color = QColor()
        self._disabled_color = QColor()
        self._border_color = QColor()
        self._hover_index = -1
        self._buttons: list[_PageButton] = []
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Pagination")
        self.setTheme("material")
        self._update_accessibility()

    def sizeHint(self) -> QSize:
        widths = self._button_widths()
        spacing = self._effective_spacing()
        return QSize(max(120, round(sum(widths) + max(0, len(widths) - 1) * spacing)), self._button_size)

    def minimumSizeHint(self) -> QSize:
        return QSize(min(180, self.sizeHint().width()), self._button_size)

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._text_color = theme_color(self._theme, "text")
        self._active_color = theme_color(self._theme, "primary")
        self._active_text_color = theme_color(self._theme, "on_primary")
        self._hover_color = theme_color(self._theme, "surface_alt")
        self._disabled_color = theme_color(self._theme, "muted")
        self._border_color = theme_color(self._theme, "border")
        self._radius = theme_radius(self._theme)
        self.updateGeometry()
        self.update()

    def _page_tokens(self) -> list[int | None]:
        count = self._page_count
        visible = self._maximum_visible_pages
        if count <= visible:
            return list(range(1, count + 1))

        inner_count = max(1, visible - 2)
        start = self._current_page - inner_count // 2
        start = max(2, min(start, count - inner_count))
        end = min(count - 1, start + inner_count - 1)
        tokens: list[int | None] = [1]
        if start > 2:
            tokens.append(None)
        tokens.extend(range(start, end + 1))
        if end < count - 1:
            tokens.append(None)
        tokens.append(count)
        return tokens

    def visiblePages(self) -> tuple[int | None, ...]:
        return tuple(self._page_tokens())

    def _button_specs(self) -> list[tuple[str, str, int | None, bool, bool]]:
        specs: list[tuple[str, str, int | None, bool, bool]] = []
        at_first = self._current_page <= 1
        at_last = self._current_page >= self._page_count
        if self._show_first_last:
            specs.append(("first", "«", 1, self._loop_navigation or not at_first, False))
        if self._show_prev_next:
            previous = self._page_count if at_first and self._loop_navigation else self._current_page - 1
            specs.append(("previous", self._previous_text, previous, self._loop_navigation or not at_first, False))

        if self._style_index == 3:
            specs.append(("info", f"{self._current_page} / {self._page_count}", None, False, False))
        else:
            for token in self._page_tokens():
                if token is None:
                    specs.append(("ellipsis", "…", None, False, False))
                else:
                    specs.append(("page", str(token), token, True, token == self._current_page))

        if self._show_prev_next:
            following = 1 if at_last and self._loop_navigation else self._current_page + 1
            specs.append(("next", self._next_text, following, self._loop_navigation or not at_last, False))
        if self._show_first_last:
            specs.append(("last", "»", self._page_count, self._loop_navigation or not at_last, False))
        return specs

    def _button_widths(self) -> list[float]:
        metrics = self.fontMetrics()
        widths: list[float] = []
        for kind, text, _target, _enabled, _active in self._button_specs():
            if kind == "info":
                widths.append(max(self._button_size * 2.2, metrics.horizontalAdvance(text) + 24))
            elif kind == "ellipsis":
                widths.append(max(20, self._button_size * 0.65))
            else:
                widths.append(float(self._button_size))
        return widths

    def _effective_spacing(self) -> int:
        return 0 if self._style_index in (1, 3) else self._spacing

    def _layout_buttons(self) -> list[_PageButton]:
        specs = self._button_specs()
        if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            specs.reverse()
        widths = self._button_widths()
        spacing = self._effective_spacing()
        total_width = sum(widths) + max(0, len(widths) - 1) * spacing
        x = max(0.0, (self.width() - total_width) / 2)
        y = max(0.0, (self.height() - self._button_size) / 2)
        buttons: list[_PageButton] = []
        for spec, width in zip(specs, widths):
            kind, text, target, enabled, active = spec
            buttons.append(_PageButton(kind, text, target, QRectF(x, y, width, self._button_size), enabled, active))
            x += width + spacing
        return buttons

    def paintEvent(self, event) -> None:
        self._buttons = self._layout_buttons()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.55)

        if self._style_index in (1, 3) and self._buttons:
            group_rect = self._buttons[0].rect.united(self._buttons[-1].rect)
            painter.setPen(QPen(self._border_color, 1))
            painter.setBrush(self._background_color)
            painter.drawRoundedRect(group_rect, self._radius, self._radius)

        for index, button in enumerate(self._buttons):
            hovered = index == self._hover_index and button.enabled
            self._draw_button(painter, button, hovered)

        if self.hasFocus():
            focus_rect = self.rect().adjusted(1, 1, -1, -1)
            pen = QPen(self._active_color, 1, Qt.PenStyle.DotLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(focus_rect), self._radius, self._radius)

    def _draw_button(self, painter: QPainter, button: _PageButton, hovered: bool) -> None:
        rect = button.rect.adjusted(0.5, 0.5, -0.5, -0.5)
        font = QFont(self.font())
        font.setBold(button.active)
        painter.setFont(font)

        if self._style_index == 0:
            painter.setPen(QPen(self._active_color if button.active else self._border_color, 1))
            painter.setBrush(self._active_color if button.active else (self._hover_color if hovered else self._background_color))
            if button.kind != "ellipsis":
                painter.drawRoundedRect(rect, self._radius, self._radius)
        elif self._style_index in (1, 3):
            painter.setPen(Qt.PenStyle.NoPen)
            if button.active:
                painter.setBrush(self._active_color)
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), max(2, self._radius - 2), max(2, self._radius - 2))
            elif hovered:
                painter.setBrush(self._hover_color)
                painter.drawRect(rect)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            if hovered:
                painter.setBrush(self._hover_color)
                painter.drawRoundedRect(rect, self._radius, self._radius)
            if button.active:
                painter.setBrush(self._active_color)
                painter.drawRoundedRect(QRectF(rect.left() + 7, rect.bottom() - 3, rect.width() - 14, 3), 1.5, 1.5)

        text_color = self._text_color
        if not button.enabled and button.kind not in ("ellipsis", "info"):
            text_color = self._disabled_color
        elif button.active:
            text_color = self._active_text_color if self._style_index != 2 else self._active_color
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, button.text)

    def _button_at(self, position) -> int:
        self._buttons = self._layout_buttons()
        for index, button in enumerate(self._buttons):
            if button.rect.contains(position):
                return index
        return -1

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        hover_index = self._button_at(event.position())
        if hover_index >= 0 and not self._buttons[hover_index].enabled:
            hover_index = -1
        if hover_index != self._hover_index:
            self._hover_index = hover_index
            self.setCursor(Qt.CursorShape.PointingHandCursor if hover_index >= 0 else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_index = -1
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._button_at(event.position())
            if index >= 0:
                button = self._buttons[index]
                if button.enabled and button.target is not None:
                    self.setCurrentPage(button.target)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self.nextPage() if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.previousPage()
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self.previousPage() if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.nextPage()
        elif event.key() == Qt.Key.Key_Home:
            self.firstPage()
        elif event.key() == Qt.Key.Key_End:
            self.lastPage()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def wheelEvent(self, event) -> None:
        if not self._wheel_navigation:
            super().wheelEvent(event)
            return
        if event.angleDelta().y() > 0:
            self.previousPage()
        elif event.angleDelta().y() < 0:
            self.nextPage()
        event.accept()

    def nextPage(self) -> None:
        if self._current_page < self._page_count:
            self.setCurrentPage(self._current_page + 1)
        elif self._loop_navigation:
            self.setCurrentPage(1)

    def previousPage(self) -> None:
        if self._current_page > 1:
            self.setCurrentPage(self._current_page - 1)
        elif self._loop_navigation:
            self.setCurrentPage(self._page_count)

    def firstPage(self) -> None:
        self.setCurrentPage(1)

    def lastPage(self) -> None:
        self.setCurrentPage(self._page_count)

    def getCurrentPage(self) -> int:
        return self._current_page

    def setCurrentPage(self, value: int) -> None:
        page = min(self._page_count, max(1, int(value)))
        if page == self._current_page:
            return
        self._current_page = page
        self._update_accessibility()
        self.updateGeometry()
        self.update()
        self.pageChanged.emit(page)

    def getPageCount(self) -> int:
        return self._page_count

    def setPageCount(self, value: int) -> None:
        had_total = self._total_items != 0
        self._set_page_count(value, clear_total=True)
        if had_total:
            self.totalItemsChanged.emit(0)

    def _set_page_count(self, value: int, *, clear_total: bool) -> None:
        count = max(1, int(value))
        if clear_total:
            self._total_items = 0
        changed = count != self._page_count
        self._page_count = count
        old_page = self._current_page
        self._current_page = min(self._current_page, count)
        self._update_accessibility()
        self.updateGeometry()
        self.update()
        if changed:
            self.pageCountChanged.emit(count)
        if self._current_page != old_page:
            self.pageChanged.emit(self._current_page)

    def getTotalItems(self) -> int:
        return self._total_items

    def setTotalItems(self, value: int) -> None:
        total = max(0, int(value))
        if total == self._total_items:
            return
        self._total_items = total
        self._set_page_count(max(1, math.ceil(total / self._page_size)), clear_total=False)
        self.totalItemsChanged.emit(total)

    def _update_accessibility(self) -> None:
        self.setAccessibleDescription(f"Page {self._current_page} of {self._page_count}")

    def getPageSize(self) -> int:
        return self._page_size

    def setPageSize(self, value: int) -> None:
        size = max(1, int(value))
        if size == self._page_size:
            return
        self._page_size = size
        if self._total_items:
            self._set_page_count(math.ceil(self._total_items / size), clear_total=False)
        self.pageSizeChanged.emit(size)

    def getMaximumVisiblePages(self) -> int:
        return self._maximum_visible_pages

    def setMaximumVisiblePages(self, value: int) -> None:
        self._maximum_visible_pages = min(15, max(3, int(value)))
        self.updateGeometry()
        self.update()

    def getStyleIndex(self) -> int:
        return self._style_index

    def setStyleIndex(self, value: int) -> None:
        self._style_index = min(len(self.STYLE_NAMES) - 1, max(0, int(value)))
        self.updateGeometry()
        self.update()

    def getStyleHint(self) -> str:
        return " | ".join(f"{index} {name}" for index, name in enumerate(self.STYLE_NAMES))

    def setStyleHint(self, value: str) -> None:
        return None

    def _bool_accessors(name: str):
        def getter(self):
            return bool(getattr(self, name))

        def setter(self, value):
            setattr(self, name, bool(value))
            self.updateGeometry()
            self.update()

        return getter, setter

    getShowFirstLast, setShowFirstLast = _bool_accessors("_show_first_last")
    getShowPrevNext, setShowPrevNext = _bool_accessors("_show_prev_next")
    getLoopNavigation, setLoopNavigation = _bool_accessors("_loop_navigation")
    getWheelNavigation, setWheelNavigation = _bool_accessors("_wheel_navigation")

    def _int_accessors(name: str, minimum: int, maximum: int):
        def getter(self):
            return int(getattr(self, name))

        def setter(self, value):
            setattr(self, name, min(maximum, max(minimum, int(value))))
            self.updateGeometry()
            self.update()

        return getter, setter

    getButtonSize, setButtonSize = _int_accessors("_button_size", 24, 64)
    getSpacing, setSpacing = _int_accessors("_spacing", 0, 24)
    getRadius, setRadius = _int_accessors("_radius", 0, 32)

    def getPreviousText(self) -> str:
        return self._previous_text

    def setPreviousText(self, value: str) -> None:
        self._previous_text = str(value) or "‹"
        self.updateGeometry()
        self.update()

    def getNextText(self) -> str:
        return self._next_text

    def setNextText(self, value: str) -> None:
        self._next_text = str(value) or "›"
        self.updateGeometry()
        self.update()

    def _color_accessors(name: str):
        def getter(self):
            return QColor(getattr(self, name))

        def setter(self, value):
            setattr(self, name, QColor(value))
            self.update()

        return getter, setter

    getBackgroundColor, setBackgroundColor = _color_accessors("_background_color")
    getTextColor, setTextColor = _color_accessors("_text_color")
    getActiveColor, setActiveColor = _color_accessors("_active_color")
    getActiveTextColor, setActiveTextColor = _color_accessors("_active_text_color")
    getHoverColor, setHoverColor = _color_accessors("_hover_color")
    getDisabledColor, setDisabledColor = _color_accessors("_disabled_color")
    getBorderColor, setBorderColor = _color_accessors("_border_color")

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    currentPage = pyqtProperty(int, getCurrentPage, setCurrentPage, notify=pageChanged)
    pageCount = pyqtProperty(int, getPageCount, setPageCount, notify=pageCountChanged)
    totalItems = pyqtProperty(int, getTotalItems, setTotalItems, notify=totalItemsChanged)
    pageSize = pyqtProperty(int, getPageSize, setPageSize, notify=pageSizeChanged)
    maximumVisiblePages = pyqtProperty(int, getMaximumVisiblePages, setMaximumVisiblePages)
    styleIndex = pyqtProperty(int, getStyleIndex, setStyleIndex)
    styleHint = pyqtProperty(str, getStyleHint, setStyleHint, stored=False)
    showFirstLast = pyqtProperty(bool, getShowFirstLast, setShowFirstLast)
    showPrevNext = pyqtProperty(bool, getShowPrevNext, setShowPrevNext)
    loopNavigation = pyqtProperty(bool, getLoopNavigation, setLoopNavigation)
    wheelNavigation = pyqtProperty(bool, getWheelNavigation, setWheelNavigation)
    buttonSize = pyqtProperty(int, getButtonSize, setButtonSize)
    spacing = pyqtProperty(int, getSpacing, setSpacing)
    radius = pyqtProperty(int, getRadius, setRadius)
    previousText = pyqtProperty(str, getPreviousText, setPreviousText)
    nextText = pyqtProperty(str, getNextText, setNextText)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    activeColor = pyqtProperty(QColor, getActiveColor, setActiveColor)
    activeTextColor = pyqtProperty(QColor, getActiveTextColor, setActiveTextColor)
    hoverColor = pyqtProperty(QColor, getHoverColor, setHoverColor)
    disabledColor = pyqtProperty(QColor, getDisabledColor, setDisabledColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
