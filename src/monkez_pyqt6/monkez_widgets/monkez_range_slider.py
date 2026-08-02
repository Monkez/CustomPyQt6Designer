from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .theme_support import ThemeSupportMixin
from .themes import theme_color


class MonkezRangeSlider(QWidget, ThemeSupportMixin):
    """Accessible two-handle integer range slider."""

    themeChanged = pyqtSignal(str)
    lowerValueChanged = pyqtSignal(int)
    upperValueChanged = pyqtSignal(int)
    rangeChanged = pyqtSignal(int, int)
    valuesChanged = pyqtSignal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._minimum = 0
        self._maximum = 100
        self._lower_value = 25
        self._upper_value = 75
        self._single_step = 1
        self._orientation = Qt.Orientation.Horizontal
        self._groove_height = 6
        self._handle_size = 18
        self._groove_color = QColor()
        self._range_color = QColor()
        self._handle_color = QColor()
        self._border_color = QColor()
        self._active_handle = 0
        self._dragging = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Range slider")
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        return QSize(220, max(32, self._handle_size + 10)) if self._orientation == Qt.Orientation.Horizontal else QSize(max(32, self._handle_size + 10), 220)

    def minimumSizeHint(self) -> QSize:
        return QSize(70, 24) if self._orientation == Qt.Orientation.Horizontal else QSize(24, 70)

    def _apply_theme(self) -> None:
        self._groove_color = theme_color(self._theme, "border")
        self._range_color = theme_color(self._theme, "primary")
        self._handle_color = theme_color(self._theme, "surface")
        self._border_color = theme_color(self._theme, "primary")
        self.update()

    def _span(self) -> int:
        return max(1, self._maximum - self._minimum)

    def _track_rect(self) -> QRectF:
        margin = self._handle_size / 2 + 2
        if self._orientation == Qt.Orientation.Horizontal:
            return QRectF(margin, (self.height() - self._groove_height) / 2, max(1, self.width() - margin * 2), self._groove_height)
        return QRectF((self.width() - self._groove_height) / 2, margin, self._groove_height, max(1, self.height() - margin * 2))

    def _position_for_value(self, value: int) -> QPointF:
        ratio = (value - self._minimum) / self._span()
        track = self._track_rect()
        if self._orientation == Qt.Orientation.Horizontal:
            if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
                ratio = 1.0 - ratio
            return QPointF(track.left() + track.width() * ratio, track.center().y())
        return QPointF(track.center().x(), track.bottom() - track.height() * ratio)

    def _value_for_position(self, position: QPointF) -> int:
        track = self._track_rect()
        if self._orientation == Qt.Orientation.Horizontal:
            ratio = (position.x() - track.left()) / max(1.0, track.width())
            if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
                ratio = 1.0 - ratio
        else:
            ratio = (track.bottom() - position.y()) / max(1.0, track.height())
        raw = self._minimum + max(0.0, min(1.0, ratio)) * self._span()
        stepped = self._minimum + round((raw - self._minimum) / self._single_step) * self._single_step
        return max(self._minimum, min(self._maximum, int(stepped)))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = self._track_rect()
        radius = self._groove_height / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._groove_color)
        painter.drawRoundedRect(track, radius, radius)
        lower = self._position_for_value(self._lower_value)
        upper = self._position_for_value(self._upper_value)
        if self._orientation == Qt.Orientation.Horizontal:
            selected = QRectF(min(lower.x(), upper.x()), track.top(), abs(upper.x() - lower.x()), track.height())
        else:
            selected = QRectF(track.left(), min(lower.y(), upper.y()), track.width(), abs(upper.y() - lower.y()))
        painter.setBrush(self._range_color)
        painter.drawRoundedRect(selected, radius, radius)
        for index, center in ((1, lower), (2, upper)):
            painter.setPen(QPen(self._range_color if index == self._active_handle else self._border_color, 2))
            painter.setBrush(self._handle_color)
            painter.drawEllipse(center, self._handle_size / 2, self._handle_size / 2)

    def _nearest_handle(self, position: QPointF) -> int:
        lower = self._position_for_value(self._lower_value)
        upper = self._position_for_value(self._upper_value)
        dl = (position.x() - lower.x()) ** 2 + (position.y() - lower.y()) ** 2
        du = (position.x() - upper.x()) ** 2 + (position.y() - upper.y()) ** 2
        return 1 if dl <= du else 2

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._active_handle = self._nearest_handle(event.position())
            self._dragging = True
            self._move_active(event.position())
            self.setFocus()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._move_active(event.position())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _move_active(self, position: QPointF) -> None:
        value = self._value_for_position(position)
        if self._active_handle == 1:
            self.setLowerValue(min(value, self._upper_value))
        else:
            self.setUpperValue(max(value, self._lower_value))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Tab:
            self._active_handle = 2 if self._active_handle == 1 else 1
            self.update()
            event.accept()
            return
        delta = 0
        if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Up):
            delta = self._single_step
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Down):
            delta = -self._single_step
        if delta:
            if self._active_handle != 2:
                self._active_handle = 1
                self.setLowerValue(self._lower_value + delta)
            else:
                self.setUpperValue(self._upper_value + delta)
            event.accept()
            return
        super().keyPressEvent(event)

    def getMinimum(self) -> int:
        return self._minimum

    def setMinimum(self, value: int) -> None:
        self.setRange(int(value), self._maximum)

    def getMaximum(self) -> int:
        return self._maximum

    def setMaximum(self, value: int) -> None:
        self.setRange(self._minimum, int(value))

    def setRange(self, minimum: int, maximum: int) -> None:
        minimum, maximum = sorted((int(minimum), int(maximum)))
        changed = (minimum, maximum) != (self._minimum, self._maximum)
        self._minimum, self._maximum = minimum, maximum
        self._lower_value = max(minimum, min(self._lower_value, maximum))
        self._upper_value = max(self._lower_value, min(self._upper_value, maximum))
        if changed:
            self.rangeChanged.emit(minimum, maximum)
        self.update()

    def getLowerValue(self) -> int:
        return self._lower_value

    def setLowerValue(self, value: int) -> None:
        value = max(self._minimum, min(int(value), self._upper_value))
        if value == self._lower_value:
            return
        self._lower_value = value
        self.lowerValueChanged.emit(value)
        self.valuesChanged.emit(self._lower_value, self._upper_value)
        self.update()

    def getUpperValue(self) -> int:
        return self._upper_value

    def setUpperValue(self, value: int) -> None:
        value = min(self._maximum, max(int(value), self._lower_value))
        if value == self._upper_value:
            return
        self._upper_value = value
        self.upperValueChanged.emit(value)
        self.valuesChanged.emit(self._lower_value, self._upper_value)
        self.update()

    def setValues(self, lower: int, upper: int) -> None:
        lower, upper = sorted((int(lower), int(upper)))
        lower = max(self._minimum, min(lower, self._maximum))
        upper = max(lower, min(upper, self._maximum))
        lower_changed = lower != self._lower_value
        upper_changed = upper != self._upper_value
        self._lower_value, self._upper_value = lower, upper
        if lower_changed:
            self.lowerValueChanged.emit(lower)
        if upper_changed:
            self.upperValueChanged.emit(upper)
        if lower_changed or upper_changed:
            self.valuesChanged.emit(lower, upper)
        self.update()

    def getSingleStep(self) -> int:
        return self._single_step

    def setSingleStep(self, value: int) -> None:
        self._single_step = max(1, int(value))

    def getOrientation(self) -> Qt.Orientation:
        return self._orientation

    def setOrientation(self, value: Qt.Orientation) -> None:
        self._orientation = Qt.Orientation(value)
        if self._orientation == Qt.Orientation.Horizontal:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.updateGeometry()
        self.update()

    def getGrooveHeight(self) -> int:
        return self._groove_height

    def setGrooveHeight(self, value: int) -> None:
        self._groove_height = max(2, min(30, int(value)))
        self.update()

    def getHandleSize(self) -> int:
        return self._handle_size

    def setHandleSize(self, value: int) -> None:
        self._handle_size = max(8, min(60, int(value)))
        self.updateGeometry()
        self.update()

    def getGrooveColor(self) -> QColor:
        return QColor(self._groove_color)

    def setGrooveColor(self, value: QColor) -> None:
        self._groove_color = QColor(value)
        self.update()

    def getFilledColor(self) -> QColor:
        return QColor(self._range_color)

    def setFilledColor(self, value: QColor) -> None:
        self._range_color = QColor(value)
        self.update()

    def getHandleColor(self) -> QColor:
        return QColor(self._handle_color)

    def setHandleColor(self, value: QColor) -> None:
        self._handle_color = QColor(value)
        self.update()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self.update()

    minimum = pyqtProperty(int, getMinimum, setMinimum)
    maximum = pyqtProperty(int, getMaximum, setMaximum)
    lowerValue = pyqtProperty(int, getLowerValue, setLowerValue, notify=lowerValueChanged)
    upperValue = pyqtProperty(int, getUpperValue, setUpperValue, notify=upperValueChanged)
    singleStep = pyqtProperty(int, getSingleStep, setSingleStep)
    orientation = pyqtProperty(Qt.Orientation, getOrientation, setOrientation)
    grooveHeight = pyqtProperty(int, getGrooveHeight, setGrooveHeight)
    handleSize = pyqtProperty(int, getHandleSize, setHandleSize)
    grooveColor = pyqtProperty(QColor, getGrooveColor, setGrooveColor)
    filledColor = pyqtProperty(QColor, getFilledColor, setFilledColor)
    handleColor = pyqtProperty(QColor, getHandleColor, setHandleColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
