from __future__ import annotations

from PyQt6.QtCore import QEvent, QSize, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

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
            x = (self.width() - self._display_pixmap.width()) // 2
            y = (self.height() - self._display_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._display_pixmap)
            return
        if self._display_text:
            painter.setPen(self.palette().color(self.foregroundRole()))
            painter.drawText(self.rect(), self.alignment(), self._display_text)


class MonkezImage(QWidget):
    def __init__(self, parent=None, background_color=(255, 255, 255), image_file: str = "") -> None:
        super().__init__(parent)
        self._background_color = QColor(*background_color)
        self._image_file = image_file or image_path("MonkezPlaceHolderImage.jpg")
        self._pixmap = QPixmap()
        self._pixmap_update_pending = False
        self._scaled_cache_key: tuple[int, int, int, bool] | None = None
        self._scaled_pixmap = QPixmap()
        self._smooth_scaling = True
        self._resize_update_delay_ms = 16

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.frame = QFrame(self)
        layout.addWidget(self.frame)

        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = _ScalableImageLabel(self.frame)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(0, 0)
        self.image_label.setMaximumSize(16777215, 16777215)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        frame_layout.addWidget(self.image_label)

        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setImageFile(self._image_file)
        self._update_style()
        self._schedule_pixmap_update()

    def sizeHint(self) -> QSize:
        return QSize(180, 120)

    def minimumSizeHint(self) -> QSize:
        return QSize(24, 24)

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

    def set_image(self, image) -> None:
        if isinstance(image, QPixmap):
            self._pixmap = image
        elif isinstance(image, QImage):
            self._pixmap = QPixmap.fromImage(image)
        elif isinstance(image, str):
            self._pixmap = QPixmap(image)
        else:
            self._pixmap = QPixmap()
        self._invalidate_scaled_cache()
        self._schedule_pixmap_update()

    def _update_style(self) -> None:
        self.frame.setStyleSheet(
            "QFrame {"
            f"background-color: {self._background_color.name()};"
            "border-radius: 5px;"
            "}"
        )
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

        cache_key = (self._pixmap.cacheKey(), size.width(), size.height(), self._smooth_scaling)
        if self._scaled_cache_key != cache_key:
            transform = (
                Qt.TransformationMode.SmoothTransformation
                if self._smooth_scaling
                else Qt.TransformationMode.FastTransformation
            )
            self._scaled_pixmap = self._pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, transform)
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

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, color: QColor) -> None:
        self._background_color = QColor(color)
        self._update_style()

    def getImageFile(self) -> str:
        return self._image_file

    def setImageFile(self, path: str) -> None:
        self._image_file = path or image_path("MonkezPlaceHolderImage.jpg")
        self._pixmap = QPixmap(self._image_file)
        self._invalidate_scaled_cache()
        self._schedule_pixmap_update()

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
    smoothScaling = pyqtProperty(bool, getSmoothScaling, setSmoothScaling)
