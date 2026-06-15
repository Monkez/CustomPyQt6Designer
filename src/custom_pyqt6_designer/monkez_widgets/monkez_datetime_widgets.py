from __future__ import annotations

from PyQt6.QtCore import QDate, QDateTime, QPointF, QRectF, Qt, QTime, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QDateEdit,
    QDateTimeEdit,
    QHeaderView,
    QTableView,
    QTimeEdit,
    QToolButton,
)

from .theme_support import ThemeSupportMixin
from .themes import theme_color, theme_int, theme_radius


class _DateTimeStyleMixin(ThemeSupportMixin):
    def _init_datetime_style(self) -> None:
        self._init_theme_support()
        self._background_color = QColor()
        self._border_color = QColor()
        self._text_color = QColor()
        self._accent_color = QColor()
        self._radius = 8
        self._control_height = 40

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "control")
        self._border_color = theme_color(self._theme, "border")
        self._text_color = theme_color(self._theme, "text")
        self._accent_color = theme_color(self._theme, "primary")
        self._radius = theme_radius(self._theme)
        self._control_height = theme_int(self._theme, "control_height")
        self._update_style()

    def _update_style(self) -> None:
        selector = type(self).__name__
        button_width = max(28, self._control_height - 4)
        self.setMinimumHeight(self._control_height)
        base = (
            f"{selector} {{"
            f"background-color: {self._background_color.name()};"
            f"border: 1px solid {self._border_color.name()};"
            f"border-radius: {self._radius}px;"
            f"color: {self._text_color.name()};"
            "padding: 4px 8px;"
            f"padding-right: {button_width + 4}px;"
            "}"
            f"{selector}:focus {{ border: 2px solid {self._accent_color.name()}; }}"
        )
        if getattr(self, "_calendar_button", False):
            controls = (
            f"{selector}::drop-down {{"
            f"subcontrol-origin: border; subcontrol-position: top right; width: {button_width}px;"
            f"border-left: 1px solid {self._border_color.name()};"
            f"border-top-right-radius: {self._radius}px;"
            f"border-bottom-right-radius: {self._radius}px;"
            "}"
            f"{selector}::drop-down:hover {{ background-color: {theme_color(self._theme, 'control_hover').name()}; }}"
            f"{selector}::down-arrow {{ image: none; }}"
            )
        else:
            controls = (
                f"{selector}::up-button {{"
                f"subcontrol-origin: border; subcontrol-position: top right; width: {button_width}px;"
                f"border-left: 1px solid {self._border_color.name()};"
                f"border-top-right-radius: {self._radius}px;"
                "}"
                f"{selector}::down-button {{"
                f"subcontrol-origin: border; subcontrol-position: bottom right; width: {button_width}px;"
                f"border-left: 1px solid {self._border_color.name()};"
                f"border-bottom-right-radius: {self._radius}px;"
                "}"
                f"{selector}::up-button:hover, {selector}::down-button:hover {{"
                f"background-color: {theme_color(self._theme, 'control_hover').name()};"
                "}"
                f"{selector}::up-arrow, {selector}::down-arrow {{ image: none; }}"
            )
        self.setStyleSheet(base + controls)

    def _paint_calendar_icon(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self._accent_color, 2))
        size = min(16, self.height() - 12)
        x = self.width() - max(22, self._control_height // 2) - size / 2
        y = (self.height() - size) / 2
        rect = QRectF(x, y + 2, size, size - 2)
        painter.drawRoundedRect(rect, 2, 2)
        painter.drawLine(QPointF(x, y + 7), QPointF(x + size, y + 7))
        painter.drawLine(QPointF(x + 4, y), QPointF(x + 4, y + 5))
        painter.drawLine(QPointF(x + size - 4, y), QPointF(x + size - 4, y + 5))

    def _paint_step_arrows(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self._accent_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x = self.width() - max(12, self._control_height // 4)
        for y, direction in ((self.height() * 0.32, -1), (self.height() * 0.68, 1)):
            painter.drawLine(QPointF(x - 4, y - direction * 2), QPointF(x, y + direction * 2))
            painter.drawLine(QPointF(x, y + direction * 2), QPointF(x + 4, y - direction * 2))

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self._update_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self._update_style()

    def getAccentColor(self) -> QColor:
        return QColor(self._accent_color)

    def setAccentColor(self, value: QColor) -> None:
        self._accent_color = QColor(value)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._update_style()

    def getControlHeight(self) -> int:
        return self._control_height

    def setControlHeight(self, value: int) -> None:
        self._control_height = min(96, max(24, int(value)))
        self._update_style()


def _declare_datetime_properties(namespace: dict) -> None:
    namespace["themeIndex"] = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    namespace["themeHint"] = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    namespace["themeName"] = pyqtProperty(
        str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False
    )
    namespace["backgroundColor"] = pyqtProperty(
        QColor, _DateTimeStyleMixin.getBackgroundColor, _DateTimeStyleMixin.setBackgroundColor
    )
    namespace["borderColor"] = pyqtProperty(
        QColor, _DateTimeStyleMixin.getBorderColor, _DateTimeStyleMixin.setBorderColor
    )
    namespace["textColor"] = pyqtProperty(
        QColor, _DateTimeStyleMixin.getTextColor, _DateTimeStyleMixin.setTextColor
    )
    namespace["accentColor"] = pyqtProperty(
        QColor, _DateTimeStyleMixin.getAccentColor, _DateTimeStyleMixin.setAccentColor
    )
    namespace["radius"] = pyqtProperty(int, _DateTimeStyleMixin.getRadius, _DateTimeStyleMixin.setRadius)
    namespace["controlHeight"] = pyqtProperty(
        int, _DateTimeStyleMixin.getControlHeight, _DateTimeStyleMixin.setControlHeight
    )


class MonkezDateEdit(QDateEdit, _DateTimeStyleMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_datetime_style()
        self._calendar_button = True
        self.setCalendarPopup(True)
        self.setDate(QDate.currentDate())
        self.setDisplayFormat("dd/MM/yyyy")
        self.setTheme("material")

    def paintEvent(self, event) -> None:
        QDateEdit.paintEvent(self, event)
        self._paint_calendar_icon()

    _declare_datetime_properties(locals())


class MonkezTimeEdit(QTimeEdit, _DateTimeStyleMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_datetime_style()
        self.setTime(QTime.currentTime())
        self.setDisplayFormat("HH:mm:ss")
        self.setTheme("material")

    def paintEvent(self, event) -> None:
        QTimeEdit.paintEvent(self, event)
        self._paint_step_arrows()

    _declare_datetime_properties(locals())


class MonkezDateTimeEdit(QDateTimeEdit, _DateTimeStyleMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_datetime_style()
        self._calendar_button = True
        self.setCalendarPopup(True)
        self.setDateTime(QDateTime.currentDateTime())
        self.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.setTheme("material")

    def paintEvent(self, event) -> None:
        QDateTimeEdit.paintEvent(self, event)
        self._paint_calendar_icon()

    _declare_datetime_properties(locals())


class MonkezCalendarWidget(QCalendarWidget, ThemeSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._background_color = QColor()
        self._text_color = QColor()
        self._accent_color = QColor()
        self._muted_color = QColor()
        self._weekend_color = QColor()
        self._today_color = QColor()
        self._outside_month_color = QColor()
        self._radius = 8
        self.setGridVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.setNavigationBarVisible(True)
        self.setMinimumSize(340, 280)
        for object_name, text in (
            ("qt_calendar_prevmonth", "‹"),
            ("qt_calendar_nextmonth", "›"),
        ):
            button = self.findChild(QToolButton, object_name)
            if button is not None:
                button.setIcon(QIcon())
                button.setText(text)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
        view = self.findChild(QTableView, "qt_calendar_calendarview")
        if view is not None:
            view.setShowGrid(False)
            view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            view.setSelectionMode(QTableView.SelectionMode.NoSelection)
            view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._text_color = theme_color(self._theme, "text")
        self._accent_color = theme_color(self._theme, "primary")
        self._muted_color = theme_color(self._theme, "muted")
        self._weekend_color = theme_color(self._theme, "danger")
        self._today_color = theme_color(self._theme, "primary")
        self._outside_month_color = QColor(self._muted_color)
        self._outside_month_color.setAlpha(120)
        self._radius = theme_radius(self._theme)
        self._update_style()

    def _update_style(self) -> None:
        hover = theme_color(self._theme, "secondary").name()
        border = theme_color(self._theme, "border").name()
        self.setStyleSheet(
            "MonkezCalendarWidget {"
            f"background-color: {self._background_color.name()};"
            f"color: {self._text_color.name()};"
            f"border: 1px solid {border};"
            f"border-radius: {self._radius}px;"
            "}"
            "MonkezCalendarWidget QWidget#qt_calendar_navigationbar {"
            f"background-color: {theme_color(self._theme, 'surface_alt').name()};"
            f"border-top-left-radius: {self._radius}px;"
            f"border-top-right-radius: {self._radius}px;"
            f"border-bottom: 1px solid {border};"
            "padding: 8px 10px;"
            "min-height: 38px;"
            "}"
            "MonkezCalendarWidget QToolButton {"
            f"color: {self._text_color.name()};"
            "background: transparent;"
            "border: 0;"
            "padding: 7px 10px;"
            "font-weight: 650;"
            "font-size: 14px;"
            "}"
            "MonkezCalendarWidget QToolButton::menu-indicator {"
            "image: none;"
            "width: 0px;"
            "height: 0px;"
            "subcontrol-position: center;"
            "}"
            f"MonkezCalendarWidget QToolButton:hover {{ background: {hover}; border-radius: 8px; }}"
            "MonkezCalendarWidget QToolButton#qt_calendar_prevmonth,"
            "MonkezCalendarWidget QToolButton#qt_calendar_nextmonth {"
            f"color: {self._accent_color.name()};"
            "font-size: 22px;"
            "font-weight: 500;"
            "min-width: 30px;"
            "}"
            "MonkezCalendarWidget QToolButton#qt_calendar_monthbutton {"
            "padding-right: 4px;"
            "}"
            "MonkezCalendarWidget QToolButton#qt_calendar_yearbutton {"
            "padding-left: 4px;"
            "}"
            "MonkezCalendarWidget QMenu {"
            f"background: {self._background_color.name()};"
            f"color: {self._text_color.name()};"
            f"border: 1px solid {border};"
            f"border-radius: {max(6, self._radius - 2)}px;"
            "padding: 6px;"
            "}"
            "MonkezCalendarWidget QMenu::item {"
            "padding: 7px 20px;"
            "border-radius: 6px;"
            "}"
            f"MonkezCalendarWidget QMenu::item:selected {{ background: {hover}; }}"
            "MonkezCalendarWidget QTableView {"
            f"background: {self._background_color.name()};"
            "border: 0;"
            "padding: 8px;"
            "selection-background-color: transparent;"
            "outline: 0;"
            "}"
            "MonkezCalendarWidget QHeaderView {"
            f"background: {self._background_color.name()};"
            "border: 0;"
            "}"
            "MonkezCalendarWidget QHeaderView::section {"
            f"background: {self._background_color.name()};"
            f"color: {self._muted_color.name()};"
            "border: 0;"
            "padding: 7px 2px;"
            "font-size: 12px;"
            "font-weight: 600;"
            "}"
            "MonkezCalendarWidget QAbstractItemView {"
            f"background: {self._background_color.name()};"
            f"color: {self._text_color.name()};"
            "selection-background-color: transparent;"
            "outline: 0;"
            "}"
            "MonkezCalendarWidget QSpinBox {"
            f"color: {self._text_color.name()};"
            f"background: {self._background_color.name()};"
            f"border: 1px solid {border};"
            "border-radius: 6px;"
            "padding: 5px;"
            "}"
        )
        self.updateCells()

    def paintCell(self, painter: QPainter, rect, date: QDate) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cell = QRectF(rect).adjusted(4, 3, -4, -3)
        selected = date == self.selectedDate()
        today = date == QDate.currentDate()
        current_month = date.month() == self.monthShown() and date.year() == self.yearShown()
        weekend = date.dayOfWeek() in {Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday}

        if selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._accent_color)
            radius = cell.height() / 2 if self._theme == "ios" else min(9.0, cell.height() / 3)
            painter.drawRoundedRect(cell, radius, radius)
        elif today:
            painter.setPen(QPen(self._today_color, 1.5))
            painter.setBrush(theme_color(self._theme, "secondary"))
            radius = cell.height() / 2 if self._theme == "ios" else min(9.0, cell.height() / 3)
            painter.drawRoundedRect(cell, radius, radius)

        if selected:
            text_color = theme_color(self._theme, "on_primary")
        elif not current_month:
            text_color = self._outside_month_color
        elif weekend:
            text_color = self._weekend_color
        else:
            text_color = self._text_color

        font = QFont(self.font())
        font.setPointSizeF(max(9.0, font.pointSizeF()))
        font.setBold(selected or today)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(cell, Qt.AlignmentFlag.AlignCenter, str(date.day()))
        painter.restore()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._update_style()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self._update_style()

    def getAccentColor(self) -> QColor:
        return QColor(self._accent_color)

    def setAccentColor(self, value: QColor) -> None:
        self._accent_color = QColor(value)
        self._update_style()

    def getWeekendColor(self) -> QColor:
        return QColor(self._weekend_color)

    def setWeekendColor(self, value: QColor) -> None:
        self._weekend_color = QColor(value)
        self.updateCells()

    def getTodayColor(self) -> QColor:
        return QColor(self._today_color)

    def setTodayColor(self, value: QColor) -> None:
        self._today_color = QColor(value)
        self.updateCells()

    def getOutsideMonthColor(self) -> QColor:
        return QColor(self._outside_month_color)

    def setOutsideMonthColor(self, value: QColor) -> None:
        self._outside_month_color = QColor(value)
        self.updateCells()

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
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    accentColor = pyqtProperty(QColor, getAccentColor, setAccentColor)
    weekendColor = pyqtProperty(QColor, getWeekendColor, setWeekendColor)
    todayColor = pyqtProperty(QColor, getTodayColor, setTodayColor)
    outsideMonthColor = pyqtProperty(QColor, getOutsideMonthColor, setOutsideMonthColor)
    radius = pyqtProperty(int, getRadius, setRadius)
