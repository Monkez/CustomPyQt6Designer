from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

from .theme_support import ThemeSupportMixin
from .themes import theme_color, theme_radius


class MonkezSplashScreen(QWidget, ThemeSupportMixin):
    """Designer-ready splash surface with a lightweight painted fallback UI."""

    progressChanged = pyqtSignal(int)
    statusChanged = pyqtSignal(str)
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._app_name = "Monkez Application"
        self._app_version = "Version 1.0"
        self._status_text = "Starting..."
        self._progress = 0
        self._display_progress = 0.0
        self._show_progress = True
        self._show_spinner = True
        self._default_content_visible = True
        self._background_image = ""
        self._background_pixmap = QPixmap()
        self._image_mode = 0
        self._transparent_background = True
        self._animation_enabled = True
        self._animation_duration = 220
        self._spinner_interval = 16
        self._spinner_angle = 0.0
        self._content_padding = 36
        self._radius = 22
        self._background_color = QColor("#0f172a")
        self._text_color = QColor("#f8fafc")
        self._secondary_text_color = QColor("#94a3b8")
        self._accent_color = QColor("#38bdf8")
        self._track_color = QColor(255, 255, 255, 42)

        self._progress_animation = QVariantAnimation(self)
        self._progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_animation.valueChanged.connect(self._set_display_progress)

        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._advance_spinner)

        self.setObjectName("monkezSplashScreen")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self._init_theme_support()

    def sizeHint(self) -> QSize:
        return QSize(680, 400)

    def minimumSizeHint(self) -> QSize:
        return QSize(240, 140)

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._text_color = theme_color(self._theme, "text")
        self._secondary_text_color = theme_color(self._theme, "muted")
        self._accent_color = theme_color(self._theme, "primary")
        self._track_color = QColor(self._secondary_text_color)
        self._track_color.setAlpha(55)
        self._radius = max(12, theme_radius(self._theme) + 10)
        self.update()

    def set_runtime_window_mode(self, always_on_top: bool = True) -> None:
        flags = Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, self._transparent_background)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )

        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(bounds, self._radius, self._radius)
        painter.setClipPath(clip)
        painter.fillPath(clip, self._background_color)
        self._draw_background_image(painter, bounds)

        if self._default_content_visible:
            self._draw_default_content(painter, bounds)

    def _draw_background_image(self, painter: QPainter, bounds: QRectF) -> None:
        if self._background_pixmap.isNull():
            return
        source = QRectF(self._background_pixmap.rect())
        target = QRectF(bounds)
        if self._image_mode != 2:
            source_ratio = source.width() / max(1.0, source.height())
            target_ratio = target.width() / max(1.0, target.height())
            contain = self._image_mode == 1
            if (source_ratio > target_ratio) == contain:
                height = target.width() / source_ratio
                target.setTop(target.center().y() - height / 2)
                target.setHeight(height)
            else:
                width = target.height() * source_ratio
                target.setLeft(target.center().x() - width / 2)
                target.setWidth(width)
            if not contain:
                target = bounds
                if source_ratio > target_ratio:
                    crop_width = source.height() * target_ratio
                    source.setLeft(source.center().x() - crop_width / 2)
                    source.setWidth(crop_width)
                else:
                    crop_height = source.width() / target_ratio
                    source.setTop(source.center().y() - crop_height / 2)
                    source.setHeight(crop_height)
        painter.drawPixmap(target, self._background_pixmap, source)

    def _draw_default_content(self, painter: QPainter, bounds: QRectF) -> None:
        pad = float(self._content_padding)
        content = bounds.adjusted(pad, pad, -pad, -pad)

        title_font = QFont("Segoe UI")
        title_font.setPointSize(max(18, title_font.pointSize() + 10))
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(self._text_color)
        title_rect = QRectF(content.left(), content.top(), content.width() - 70, 54)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._app_name)

        version_font = QFont("Segoe UI")
        version_font.setPointSize(max(9, version_font.pointSize() - 1))
        painter.setFont(version_font)
        painter.setPen(self._secondary_text_color)
        version_rect = QRectF(content.left(), title_rect.bottom() + 2, content.width(), 26)
        painter.drawText(version_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._app_version)

        bottom = content.bottom()
        if self._show_progress:
            self._draw_progress(painter, QRectF(content.left(), bottom - 12, content.width(), 8))
            bottom -= 28

        status_font = QFont("Segoe UI")
        status_font.setPointSize(max(9, status_font.pointSize()))
        painter.setFont(status_font)
        painter.setPen(self._text_color)
        status_rect = QRectF(content.left(), bottom - 30, content.width() - 42, 28)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._status_text)

        if self._show_spinner:
            self._draw_spinner(painter, QPointF(content.right() - 14, bottom - 16), 11)

    def _draw_progress(self, painter: QPainter, rect: QRectF) -> None:
        track = QPainterPath()
        track.addRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        painter.fillPath(track, self._track_color)

        ratio = max(0.0, min(1.0, self._display_progress / 100.0))
        if ratio <= 0:
            return
        value_rect = QRectF(rect)
        value_rect.setWidth(max(rect.height(), rect.width() * ratio))
        value_path = QPainterPath()
        value_path.addRoundedRect(value_rect, rect.height() / 2, rect.height() / 2)
        painter.fillPath(value_path, self._accent_color)

    def _draw_spinner(self, painter: QPainter, center: QPointF, radius: float) -> None:
        painter.save()
        painter.translate(center)
        painter.rotate(self._spinner_angle)
        pen = QPen(self._accent_color, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(-radius, -radius, radius * 2, radius * 2), 30 * 16, 250 * 16)
        painter.restore()

    def _advance_spinner(self) -> None:
        self._spinner_angle = (self._spinner_angle + 6.0) % 360.0
        self.update()

    def _sync_spinner_timer(self) -> None:
        should_run = self.isVisible() and self._show_spinner and self._animation_enabled
        if should_run:
            self._spinner_timer.start(max(8, self._spinner_interval))
        else:
            self._spinner_timer.stop()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_spinner_timer()

    def hideEvent(self, event) -> None:
        self._spinner_timer.stop()
        super().hideEvent(event)

    def _set_display_progress(self, value) -> None:
        self._display_progress = float(value)
        self.update()

    def getAppName(self) -> str:
        return self._app_name

    def setAppName(self, value: str) -> None:
        self._app_name = str(value)
        self.update()

    def getAppVersion(self) -> str:
        return self._app_version

    def setAppVersion(self, value: str) -> None:
        self._app_version = str(value)
        self.update()

    def getStatusText(self) -> str:
        return self._status_text

    def setStatusText(self, value: str) -> None:
        text = str(value)
        if text == self._status_text:
            return
        self._status_text = text
        self.statusChanged.emit(text)
        self.update()

    def getProgress(self) -> int:
        return self._progress

    def setProgress(self, value: int) -> None:
        progress = max(0, min(100, int(value)))
        if progress == self._progress and self._display_progress == float(progress):
            return
        self._progress = progress
        if self._animation_enabled and self.isVisible():
            self._progress_animation.stop()
            self._progress_animation.setDuration(max(0, self._animation_duration))
            self._progress_animation.setStartValue(self._display_progress)
            self._progress_animation.setEndValue(float(progress))
            self._progress_animation.start()
        else:
            self._set_display_progress(progress)
        self.progressChanged.emit(progress)

    def getShowProgress(self) -> bool:
        return self._show_progress

    def setShowProgress(self, value: bool) -> None:
        self._show_progress = bool(value)
        self.update()

    def getShowSpinner(self) -> bool:
        return self._show_spinner

    def setShowSpinner(self, value: bool) -> None:
        self._show_spinner = bool(value)
        self._sync_spinner_timer()
        self.update()

    def getDefaultContentVisible(self) -> bool:
        return self._default_content_visible

    def setDefaultContentVisible(self, value: bool) -> None:
        self._default_content_visible = bool(value)
        self.update()

    def getBackgroundImage(self) -> str:
        return self._background_image

    def setBackgroundImage(self, value: str) -> None:
        path = str(value or "")
        self._background_image = path
        self._background_pixmap = QPixmap(path) if path else QPixmap()
        self.update()

    def getImageMode(self) -> int:
        return self._image_mode

    def setImageMode(self, value: int) -> None:
        self._image_mode = max(0, min(2, int(value)))
        self.update()

    def getTransparentBackground(self) -> bool:
        return self._transparent_background

    def setTransparentBackground(self, value: bool) -> None:
        self._transparent_background = bool(value)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, self._transparent_background)
        self.update()

    def getAnimationEnabled(self) -> bool:
        return self._animation_enabled

    def setAnimationEnabled(self, value: bool) -> None:
        self._animation_enabled = bool(value)
        self._sync_spinner_timer()

    def getAnimationDuration(self) -> int:
        return self._animation_duration

    def setAnimationDuration(self, value: int) -> None:
        self._animation_duration = max(0, min(2000, int(value)))

    def getSpinnerInterval(self) -> int:
        return self._spinner_interval

    def setSpinnerInterval(self, value: int) -> None:
        self._spinner_interval = max(8, min(1000, int(value)))
        self._sync_spinner_timer()

    def getContentPadding(self) -> int:
        return self._content_padding

    def setContentPadding(self, value: int) -> None:
        self._content_padding = max(0, min(160, int(value)))
        self.update()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, min(160, int(value)))
        self.update()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self.update()

    def getTextColor(self) -> QColor:
        return QColor(self._text_color)

    def setTextColor(self, value: QColor) -> None:
        self._text_color = QColor(value)
        self.update()

    def getSecondaryTextColor(self) -> QColor:
        return QColor(self._secondary_text_color)

    def setSecondaryTextColor(self, value: QColor) -> None:
        self._secondary_text_color = QColor(value)
        self.update()

    def getAccentColor(self) -> QColor:
        return QColor(self._accent_color)

    def setAccentColor(self, value: QColor) -> None:
        self._accent_color = QColor(value)
        self.update()

    def getTrackColor(self) -> QColor:
        return QColor(self._track_color)

    def setTrackColor(self, value: QColor) -> None:
        self._track_color = QColor(value)
        self.update()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(
        str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False
    )
    appName = pyqtProperty(str, getAppName, setAppName)
    appVersion = pyqtProperty(str, getAppVersion, setAppVersion)
    statusText = pyqtProperty(str, getStatusText, setStatusText)
    progress = pyqtProperty(int, getProgress, setProgress)
    showProgress = pyqtProperty(bool, getShowProgress, setShowProgress)
    showSpinner = pyqtProperty(bool, getShowSpinner, setShowSpinner)
    defaultContentVisible = pyqtProperty(
        bool, getDefaultContentVisible, setDefaultContentVisible
    )
    backgroundImage = pyqtProperty(str, getBackgroundImage, setBackgroundImage)
    imageMode = pyqtProperty(int, getImageMode, setImageMode)
    transparentBackground = pyqtProperty(
        bool, getTransparentBackground, setTransparentBackground
    )
    animationEnabled = pyqtProperty(bool, getAnimationEnabled, setAnimationEnabled)
    animationDuration = pyqtProperty(int, getAnimationDuration, setAnimationDuration)
    spinnerInterval = pyqtProperty(int, getSpinnerInterval, setSpinnerInterval)
    contentPadding = pyqtProperty(int, getContentPadding, setContentPadding)
    radius = pyqtProperty(int, getRadius, setRadius)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    secondaryTextColor = pyqtProperty(
        QColor, getSecondaryTextColor, setSecondaryTextColor
    )
    accentColor = pyqtProperty(QColor, getAccentColor, setAccentColor)
    trackColor = pyqtProperty(QColor, getTrackColor, setTrackColor)
