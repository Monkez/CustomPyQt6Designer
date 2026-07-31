from __future__ import annotations

from enum import Enum
from os import PathLike, fsdecode, fspath

from PyQt6.QtCore import QEvent, QRectF, QSize, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QImage, QPainter, QPalette, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from .assets import image_path


class _ScalableImageLabel(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._display_pixmap = QPixmap()
        self._display_text = ""

    def sizeHint(self) -> QSize:
        return QSize(120, 100)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)

    def setPixmap(self, pixmap: QPixmap) -> None:
        self._display_pixmap = QPixmap(pixmap)
        self._display_text = ""
        self.update()

    def pixmap(self) -> QPixmap:
        return QPixmap(self._display_pixmap)

    def setText(self, text: str) -> None:
        self._display_text = text
        if text:
            self._display_pixmap = QPixmap()
        self.update()

    def text(self) -> str:
        return self._display_text

    def clear(self) -> None:
        self._display_pixmap = QPixmap()
        self._display_text = ""
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        if not self._display_pixmap.isNull():
            pixmap_size = self._display_pixmap.deviceIndependentSize()
            target = QRectF(
                (self.width() - pixmap_size.width()) / 2,
                (self.height() - pixmap_size.height()) / 2,
                pixmap_size.width(),
                pixmap_size.height(),
            )
            source = QRectF(0, 0, self._display_pixmap.width(), self._display_pixmap.height())
            painter.drawPixmap(target, self._display_pixmap, source)
            return
        if self._display_text:
            painter.setPen(self.palette().color(self.foregroundRole()))
            painter.drawText(self.rect(), self.alignment(), self._display_text)


class MonkezImage(QWidget):
    class ScaleMode(Enum):
        Fit = 0
        Fill = 1
        Stretch = 2
        Original = 3

    Fit = ScaleMode.Fit
    Fill = ScaleMode.Fill
    Stretch = ScaleMode.Stretch
    Original = ScaleMode.Original

    def __init__(
        self,
        parent=None,
        background_color=(255, 255, 255),
        image_file: str | PathLike[str] = "",
        source: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._background_color = QColor(*background_color)
        self._image_file = ""
        self._pixmap = QPixmap()
        self._pixmap_update_pending = False
        self._scaled_cache_key: tuple[int, int, int, int, int, bool, int] | None = None
        self._scaled_pixmap = QPixmap()
        self._scale_mode = self.ScaleMode.Fit
        self._smooth_scaling = True
        self._resize_update_delay_ms = 16

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = _ScalableImageLabel(self)
        self.image_label.setObjectName("monkezImageContent")
        self.image_label.setStyleSheet(
            "background: transparent;"
            "border: none;"
            "border-radius: 0;"
        )
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(0, 0)
        self.image_label.setMaximumSize(16777215, 16777215)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.image_label)

        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        if source is None:
            self.setImageFile(image_file)
        else:
            self.set_image(source)
        self._update_style()
        self._schedule_pixmap_update()

    def sizeHint(self) -> QSize:
        return QSize(180, 120)

    @property
    def frame(self) -> QWidget:
        """Compatibility alias for the visible outer image container."""
        return self

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_pixmap_update(self._resize_update_delay_ms)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._schedule_pixmap_update()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() in {
            QEvent.Type.Polish,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        }:
            self._schedule_pixmap_update()
        return handled

    def set_image(self, image: object, color_order: str = "bgr") -> None:
        """Display a Qt image, NumPy frame, or local image path.

        NumPy frames default to OpenCV's BGR/BGRA channel order. Pass
        ``color_order="rgb"`` or ``"rgba"`` for RGB sources such as PIL.
        """
        if image is None:
            self._image_file = ""
            self._set_source_pixmap(QPixmap())
            return
        if isinstance(image, QPixmap):
            self._image_file = ""
            pixmap = QPixmap(image)
        elif isinstance(image, QImage):
            self._image_file = ""
            pixmap = QPixmap.fromImage(image)
        elif isinstance(image, (str, bytes, PathLike)):
            self.setImageFile(image)
            return
        else:
            self._image_file = ""
            pixmap = QPixmap.fromImage(self._qimage_from_numpy(image, color_order))
        self._set_source_pixmap(pixmap)

    def setImage(self, image: object, color_order: str = "bgr") -> None:
        """Qt-style alias for :meth:`set_image`."""
        self.set_image(image, color_order)

    def setFrame(self, frame: object, color_order: str = "bgr") -> None:
        """Display a NumPy video frame, using OpenCV channel order by default."""
        self.set_image(frame, color_order)

    @staticmethod
    def _qimage_from_numpy(frame: object, color_order: str) -> QImage:
        try:
            import numpy as np
        except ModuleNotFoundError as error:
            raise TypeError(
                "NumPy must be installed before MonkezImage can display ndarray frames."
            ) from error

        if not isinstance(frame, np.ndarray):
            raise TypeError(
                "MonkezImage accepts QPixmap, QImage, numpy.ndarray, "
                "str, pathlib.Path, or None."
            )
        if frame.size == 0:
            return QImage()
        if frame.dtype != np.uint8:
            raise TypeError(
                f"NumPy frame dtype must be uint8, received {frame.dtype}."
            )

        if frame.ndim == 2:
            height, width = frame.shape
            contiguous = np.ascontiguousarray(frame)
            image_format = QImage.Format.Format_Grayscale8
        elif frame.ndim == 3 and frame.shape[2] == 1:
            height, width, _ = frame.shape
            contiguous = np.ascontiguousarray(frame[:, :, 0])
            image_format = QImage.Format.Format_Grayscale8
        elif frame.ndim == 3 and frame.shape[2] in {3, 4}:
            height, width, channels = frame.shape
            contiguous = np.ascontiguousarray(frame)
            normalized_order = color_order.strip().lower()
            if channels == 3:
                formats = {
                    "bgr": QImage.Format.Format_BGR888,
                    "rgb": QImage.Format.Format_RGB888,
                }
            else:
                formats = {
                    "bgra": QImage.Format.Format_RGBA8888,
                    "bgr": QImage.Format.Format_RGBA8888,
                    "rgba": QImage.Format.Format_RGBA8888,
                    "rgb": QImage.Format.Format_RGBA8888,
                }
            try:
                image_format = formats[normalized_order]
            except KeyError as error:
                allowed = "BGR or RGB" if channels == 3 else "BGRA or RGBA"
                raise ValueError(
                    f"color_order must be {allowed} for a {channels}-channel frame."
                ) from error
        else:
            raise ValueError(
                "NumPy frame shape must be HxW, HxWx1, HxWx3, or HxWx4; "
                f"received {frame.shape}."
            )

        qimage = QImage(
            contiguous.data,
            width,
            height,
            contiguous.strides[0],
            image_format,
        )
        if frame.ndim == 3 and frame.shape[2] == 4:
            normalized_order = color_order.strip().lower()
            if normalized_order in {"bgr", "bgra"}:
                qimage = qimage.rgbSwapped()
        return qimage.copy()

    def _set_source_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = QPixmap(pixmap)
        self._invalidate_scaled_cache()
        self._schedule_pixmap_update()

    def _update_style(self) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, self._background_color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.update()
        self._schedule_pixmap_update()

    def _schedule_pixmap_update(self, delay_ms: int = 0) -> None:
        if self._pixmap_update_pending:
            return
        self._pixmap_update_pending = True
        QTimer.singleShot(max(0, delay_ms), self._flush_pixmap_update)

    def _flush_pixmap_update(self) -> None:
        self._pixmap_update_pending = False
        self._update_pixmap()

    def _update_pixmap(self) -> None:
        if self._pixmap.isNull():
            self.image_label.clear()
            self.image_label.setText("No image loaded")
            self._invalidate_scaled_cache()
            return
        size = self._target_pixmap_size()
        if size.width() <= 0 or size.height() <= 0:
            return

        device_pixel_ratio = self._device_pixel_ratio()
        physical_size = QSize(
            max(1, round(size.width() * device_pixel_ratio)),
            max(1, round(size.height() * device_pixel_ratio)),
        )
        cache_key = (
            self._pixmap.cacheKey(),
            size.width(),
            size.height(),
            physical_size.width(),
            physical_size.height(),
            self._smooth_scaling,
            self._scale_mode.value,
        )
        if self._scaled_cache_key != cache_key:
            if self._scale_mode is self.ScaleMode.Original:
                self._scaled_pixmap = QPixmap(self._pixmap)
            else:
                transform = (
                    Qt.TransformationMode.SmoothTransformation
                    if self._smooth_scaling
                    else Qt.TransformationMode.FastTransformation
                )
                aspect_mode = {
                    self.ScaleMode.Fit: Qt.AspectRatioMode.KeepAspectRatio,
                    self.ScaleMode.Fill: Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    self.ScaleMode.Stretch: Qt.AspectRatioMode.IgnoreAspectRatio,
                }[self._scale_mode]
                self._scaled_pixmap = self._pixmap.scaled(
                    physical_size,
                    aspect_mode,
                    transform,
                )
                self._scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
            self._scaled_cache_key = cache_key

        self.image_label.setText("")
        self.image_label.setPixmap(self._scaled_pixmap)

    def _invalidate_scaled_cache(self) -> None:
        self._scaled_cache_key = None
        self._scaled_pixmap = QPixmap()

    def _target_pixmap_size(self) -> QSize:
        size = self.image_label.size()
        if size.width() > 0 and size.height() > 0:
            return size

        size = self.frame.contentsRect().size()
        if size.width() > 0 and size.height() > 0:
            return size

        size = self.contentsRect().size()
        if size.width() > 4 and size.height() > 4:
            return QSize(size.width() - 4, size.height() - 4)

        return QSize()

    def _device_pixel_ratio(self) -> float:
        window = self.window().windowHandle() if self.window() is not None else None
        if window is not None and window.screen() is not None:
            return max(1.0, float(window.screen().devicePixelRatio()))
        return max(1.0, float(self.image_label.devicePixelRatioF()))

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, color: QColor) -> None:
        self._background_color = QColor(color)
        self._update_style()

    def getImageFile(self) -> str:
        return self._image_file

    def setImageFile(self, path: str | bytes | PathLike[str]) -> None:
        normalized_path = fsdecode(fspath(path)) if path else ""
        self._image_file = normalized_path or image_path("MonkezPlaceHolderImage.jpg")
        self._set_source_pixmap(QPixmap(self._image_file))

    def getScaleMode(self) -> ScaleMode:
        return self._scale_mode

    def setScaleMode(self, value: ScaleMode | int | str) -> None:
        if isinstance(value, self.ScaleMode):
            mode = value
        elif isinstance(value, str):
            normalized = value.strip().lower()
            mode = {
                "fit": self.ScaleMode.Fit,
                "contain": self.ScaleMode.Fit,
                "fill": self.ScaleMode.Fill,
                "cover": self.ScaleMode.Fill,
                "stretch": self.ScaleMode.Stretch,
                "original": self.ScaleMode.Original,
                "center": self.ScaleMode.Original,
            }.get(normalized, self.ScaleMode.Fit)
        else:
            try:
                mode = self.ScaleMode(int(value))
            except (TypeError, ValueError):
                mode = self.ScaleMode.Fit
        if self._scale_mode is mode:
            return
        self._scale_mode = mode
        self._invalidate_scaled_cache()
        self._schedule_pixmap_update()

    def getScaleModeIndex(self) -> int:
        return self._scale_mode.value

    def setScaleModeIndex(self, value: int) -> None:
        self.setScaleMode(value)

    def getScaleModeHint(self) -> str:
        return "0 Fit | 1 Fill | 2 Stretch | 3 Original"

    def setScaleModeHint(self, value: str) -> None:
        return None

    def getSmoothScaling(self) -> bool:
        return self._smooth_scaling

    def setSmoothScaling(self, value: bool) -> None:
        value = bool(value)
        if self._smooth_scaling == value:
            return
        self._smooth_scaling = value
        self._invalidate_scaled_cache()
        self._schedule_pixmap_update()

    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    imageFile = pyqtProperty(str, getImageFile, setImageFile)
    scaleModeIndex = pyqtProperty(int, getScaleModeIndex, setScaleModeIndex)
    scaleModeHint = pyqtProperty(str, getScaleModeHint, setScaleModeHint, stored=False)
    smoothScaling = pyqtProperty(bool, getSmoothScaling, setSmoothScaling)
