from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from .theme_support import ThemeSupportMixin
from .themes import color_to_css, theme_color, theme_radius


STATUS_NAMES = ("info", "success", "warning", "error", "neutral")
STATUS_OPTIONS = "0 Info | 1 Success | 2 Warning | 3 Error | 4 Neutral"


class MonkezStatusBadge(QLabel, ThemeSupportMixin):
    """Compact semantic status label with an optional leading dot."""

    themeChanged = pyqtSignal(str)
    statusChanged = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._status_index = 1
        self._dot_visible = True
        self._radius = 10
        self._padding_x = 10
        self._padding_y = 4
        self._foreground_color = QColor()
        self._background_color = QColor()
        self._accent_color = QColor()
        self._base_text = "Online"
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self.text()) + self._padding_x * 2, metrics.height() + self._padding_y * 2)

    def _apply_theme(self) -> None:
        role = ("primary", "success", "warning", "danger", "muted")[self._status_index]
        self._accent_color = theme_color(self._theme, role)
        self._foreground_color = QColor(self._accent_color).darker(145)
        if self._theme == "dark":
            self._foreground_color = QColor(self._accent_color).lighter(125)
        self._background_color = QColor(self._accent_color)
        self._background_color.setAlpha(32 if self._theme != "dark" else 45)
        self._radius = max(6, theme_radius(self._theme) + 2)
        self._refresh()

    def _refresh(self) -> None:
        prefix = "● " if self._dot_visible else ""
        super().setText(prefix + self._base_text)
        self.setStyleSheet(
            "MonkezStatusBadge {"
            f"color: {color_to_css(self._foreground_color)};"
            f"background-color: {color_to_css(self._background_color)};"
            f"border: 1px solid {color_to_css(self._accent_color)};"
            f"border-radius: {self._radius}px;"
            f"padding: {self._padding_y}px {self._padding_x}px;"
            "font-weight: 600;"
            "}"
        )
        self.updateGeometry()

    def setText(self, text: str) -> None:
        self._base_text = str(text)
        self._refresh()

    def baseText(self) -> str:
        return self._base_text

    def setBaseText(self, text: str) -> None:
        self.setText(text)

    def getStatusIndex(self) -> int:
        return self._status_index

    def setStatusIndex(self, value: int) -> None:
        index = max(0, min(len(STATUS_NAMES) - 1, int(value)))
        if index == self._status_index:
            return
        self._status_index = index
        self._apply_theme()
        self.statusChanged.emit(index)

    def getStatusHint(self) -> str:
        return STATUS_OPTIONS

    def setStatusHint(self, value: str) -> None:
        return None

    def getDotVisible(self) -> bool:
        return self._dot_visible

    def setDotVisible(self, value: bool) -> None:
        self._dot_visible = bool(value)
        self._refresh()

    def getAccentColor(self) -> QColor:
        return QColor(self._accent_color)

    def setAccentColor(self, color: QColor) -> None:
        self._accent_color = QColor(color)
        self._refresh()

    def getTextColor(self) -> QColor:
        return QColor(self._foreground_color)

    def setTextColor(self, color: QColor) -> None:
        self._foreground_color = QColor(color)
        self._refresh()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, color: QColor) -> None:
        self._background_color = QColor(color)
        self._refresh()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._refresh()

    statusIndex = pyqtProperty(int, getStatusIndex, setStatusIndex, notify=statusChanged)
    statusHint = pyqtProperty(str, getStatusHint, setStatusHint, stored=False)
    dotVisible = pyqtProperty(bool, getDotVisible, setDotVisible)
    badgeText = pyqtProperty(str, baseText, setBaseText)
    accentColor = pyqtProperty(QColor, getAccentColor, setAccentColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    radius = pyqtProperty(int, getRadius, setRadius)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)


class MonkezLoadingIndicator(QWidget, ThemeSupportMixin):
    """Lightweight timer-driven spinner with no external dependencies."""

    themeChanged = pyqtSignal(str)
    runningChanged = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._running = True
        self._line_count = 12
        self._line_width = 3
        self._speed = 70
        self._angle = 0
        self._color = QColor()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Loading")
        self.setTheme("material")
        self._timer.start(self._speed)

    def sizeHint(self) -> QSize:
        return QSize(32, 32)

    def minimumSizeHint(self) -> QSize:
        return QSize(16, 16)

    def _apply_theme(self) -> None:
        self._color = theme_color(self._theme, "primary")
        self.update()

    def _advance(self) -> None:
        self._angle = (self._angle + 1) % max(1, self._line_count)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        radius = max(2.0, min(self.width(), self.height()) * 0.36)
        inner = radius * 0.52
        for index in range(self._line_count):
            alpha_step = (index - self._angle) % self._line_count
            color = QColor(self._color)
            color.setAlpha(max(32, 255 - alpha_step * (210 // max(1, self._line_count - 1))))
            painter.setPen(QPen(color, self._line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.save()
            painter.translate(center)
            painter.rotate(index * 360.0 / self._line_count)
            painter.drawLine(0, -round(inner), 0, -round(radius))
            painter.restore()

    def getRunning(self) -> bool:
        return self._running

    def setRunning(self, value: bool) -> None:
        running = bool(value)
        if running == self._running:
            return
        self._running = running
        if running:
            self._timer.start(self._speed)
        else:
            self._timer.stop()
        self.runningChanged.emit(running)
        self.update()

    def getColor(self) -> QColor:
        return QColor(self._color)

    def setColor(self, value: QColor) -> None:
        self._color = QColor(value)
        self.update()

    def setAccentColor(self, value: QColor) -> None:
        self.setColor(value)

    def getLineCount(self) -> int:
        return self._line_count

    def setLineCount(self, value: int) -> None:
        self._line_count = max(6, min(24, int(value)))
        self.update()

    def getLineWidth(self) -> int:
        return self._line_width

    def setLineWidth(self, value: int) -> None:
        self._line_width = max(1, min(12, int(value)))
        self.update()

    def getSpeed(self) -> int:
        return self._speed

    def setSpeed(self, value: int) -> None:
        self._speed = max(16, min(1000, int(value)))
        if self._running:
            self._timer.start(self._speed)

    running = pyqtProperty(bool, getRunning, setRunning, notify=runningChanged)
    spinnerColor = pyqtProperty(QColor, getColor, setColor)
    lineCount = pyqtProperty(int, getLineCount, setLineCount)
    lineWidth = pyqtProperty(int, getLineWidth, setLineWidth)
    speed = pyqtProperty(int, getSpeed, setSpeed)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)


class MonkezLoadingOverlay(QFrame, ThemeSupportMixin):
    """Drop-in loading surface that can cover a parent or standalone region."""

    themeChanged = pyqtSignal(str)
    activeChanged = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._active = True
        self._message = "Loading…"
        self._background_color = QColor()
        self._text_color = QColor()
        self._radius = 10
        self._indicator = MonkezLoadingIndicator(self)
        self._label = QLabel(self._message, self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addStretch()
        layout.addWidget(self._indicator, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        return QSize(220, 140)

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface_alt")
        self._background_color.setAlpha(235)
        self._text_color = theme_color(self._theme, "text")
        self._radius = theme_radius(self._theme)
        self._indicator.setTheme(self._theme)
        self._refresh()

    def _refresh(self) -> None:
        self.setStyleSheet(
            "MonkezLoadingOverlay {"
            f"background-color: {color_to_css(self._background_color)};"
            f"border-radius: {self._radius}px;"
            "}"
            "MonkezLoadingOverlay QLabel {"
            f"color: {color_to_css(self._text_color)};"
            "background: transparent; font-weight: 600;"
            "}"
        )
        self._label.setText(self._message)

    def getActive(self) -> bool:
        return self._active

    def setActive(self, value: bool) -> None:
        active = bool(value)
        if active == self._active:
            return
        self._active = active
        self._indicator.setRunning(active)
        self.setVisible(active)
        self.activeChanged.emit(active)

    def getMessage(self) -> str:
        return self._message

    def setMessage(self, value: str) -> None:
        self._message = str(value)
        self._refresh()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._refresh()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self._refresh()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._refresh()

    active = pyqtProperty(bool, getActive, setActive, notify=activeChanged)
    message = pyqtProperty(str, getMessage, setMessage)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    radius = pyqtProperty(int, getRadius, setRadius)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)


class MonkezToast(QFrame, ThemeSupportMixin):
    """Runtime toast notification; use showMessage() to position and dismiss it."""

    themeChanged = pyqtSignal(str)
    dismissed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._duration = 3000
        self._message = "Saved successfully"
        self._status_index = 1
        self._radius = 10
        self._background_color = QColor()
        self._text_color = QColor()
        self._accent_color = QColor()
        self._accent = QFrame(self)
        self._accent.setFixedWidth(4)
        self._label = QLabel(self._message, self)
        self._label.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 14, 0)
        layout.setSpacing(12)
        layout.addWidget(self._accent)
        layout.addWidget(self._label, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        return QSize(300, 58)

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._text_color = theme_color(self._theme, "text")
        role = ("primary", "success", "warning", "danger", "muted")[self._status_index]
        self._accent_color = theme_color(self._theme, role)
        self._radius = theme_radius(self._theme)
        self._refresh()

    def _refresh(self) -> None:
        self.setStyleSheet(
            "MonkezToast {"
            f"background-color: {color_to_css(self._background_color)};"
            f"border: 1px solid {color_to_css(theme_color(self._theme, 'border'))};"
            f"border-radius: {self._radius}px;"
            "}"
            "MonkezToast QLabel {"
            f"color: {color_to_css(self._text_color)}; background: transparent;"
            "}"
        )
        self._accent.setStyleSheet(f"background: {color_to_css(self._accent_color)};")
        self._label.setText(self._message)

    def showMessage(self, message: str | None = None, duration: int | None = None) -> None:
        if message is not None:
            self.setMessage(message)
        self.adjustSize()
        if self.parentWidget() is not None:
            parent = self.parentWidget()
            x = max(12, parent.width() - self.width() - 20)
            y = max(12, parent.height() - self.height() - 20)
            self.move(x, y)
        self.show()
        self.raise_()
        timeout = self._duration if duration is None else max(0, int(duration))
        if timeout:
            self._timer.start(timeout)

    def dismiss(self) -> None:
        self._timer.stop()
        self.hide()
        self.dismissed.emit()

    def getMessage(self) -> str:
        return self._message

    def setMessage(self, value: str) -> None:
        self._message = str(value)
        self._refresh()

    def getDuration(self) -> int:
        return self._duration

    def setDuration(self, value: int) -> None:
        self._duration = max(0, int(value))

    def getStatusIndex(self) -> int:
        return self._status_index

    def setStatusIndex(self, value: int) -> None:
        self._status_index = max(0, min(len(STATUS_NAMES) - 1, int(value)))
        self._apply_theme()

    message = pyqtProperty(str, getMessage, setMessage)
    duration = pyqtProperty(int, getDuration, setDuration)
    statusIndex = pyqtProperty(int, getStatusIndex, setStatusIndex)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName)
