from __future__ import annotations

from PyQt6.QtCore import QDate, QDateTime, QPointF, QRectF, Qt, QTime, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen
from PyQt6.QtWidgets import QCalendarWidget, QDateEdit, QDateTimeEdit, QTimeEdit, QToolButton

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
        self._radius = 8
        self.setGridVisible(False)
        self.setMinimumSize(300, 220)
        for object_name, text in (
            ("qt_calendar_prevmonth", "<"),
            ("qt_calendar_nextmonth", ">"),
        ):
            button = self.findChild(QToolButton, object_name)
            if button is not None:
                button.setIcon(QIcon())
                button.setText(text)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._text_color = theme_color(self._theme, "text")
        self._accent_color = theme_color(self._theme, "primary")
        self._muted_color = theme_color(self._theme, "muted")
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
            "padding: 5px;"
            "}"
            "MonkezCalendarWidget QToolButton {"
            f"color: {self._text_color.name()};"
            "background: transparent;"
            "border: 0;"
            "padding: 6px;"
            "font-weight: 600;"
            "}"
            f"MonkezCalendarWidget QToolButton:hover {{ background: {hover}; border-radius: 5px; }}"
            "MonkezCalendarWidget QMenu {"
            f"background: {self._background_color.name()}; color: {self._text_color.name()};"
            "}"
            "MonkezCalendarWidget QAbstractItemView {"
            f"background: {self._background_color.name()};"
            f"color: {self._text_color.name()};"
            f"selection-background-color: {self._accent_color.name()};"
            f"selection-color: {theme_color(self._theme, 'on_primary').name()};"
            "outline: 0;"
            "}"
            f"MonkezCalendarWidget QSpinBox {{ color: {self._text_color.name()}; background: transparent; }}"
        )

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
    radius = pyqtProperty(int, getRadius, setRadius)
