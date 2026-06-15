from __future__ import annotations

import time

from PyQt6.QtCore import QThread, QTimer, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from .assets import image_path
from .monkez_image import MonkezImage


BACKENDS = {
    "auto": 0,
    "any": 0,
    "dshow": 700,
    "msmf": 1400,
    "v4l2": 200,
    "avfoundation": 1200,
    "gstreamer": 1800,
    "ffmpeg": 1900,
}

BACKEND_HINT_TEXT = "auto | dshow | msmf | v4l2 | avfoundation | gstreamer | ffmpeg"
CAMERA_SOURCE_HINT_TEXT = "0/1/2 | path | rtsp/http URL"
RESOLUTION_HINT_TEXT = "0=default | 640x480 | 1280x720 | 1920x1080"
FOURCC_HINT_TEXT = "empty=default | MJPG | YUY2 | H264 | XVID"


class CameraCaptureThread(QThread):
    frameReady = pyqtSignal(QImage)
    statusChanged = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)

    def __init__(self, config: dict, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._running = False

    def stop(self) -> None:
        self._running = False
        self.requestInterruption()

    def run(self) -> None:
        try:
            import cv2
        except Exception as exc:
            self.errorOccurred.emit(f"OpenCV is not available: {exc}")
            return

        self._running = True
        while self._should_run():
            cap = self._open_capture(cv2)
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                self.errorOccurred.emit("Camera open failed")
                if not self.config["reconnect"]:
                    break
                if not self._interruptible_sleep(self.config["reconnect_interval_ms"]):
                    break
                continue

            self.statusChanged.emit("Camera connected")
            frame_interval = 1.0 / max(1, self.config["display_fps"])
            next_emit = 0.0

            try:
                while self._should_run():
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        self.errorOccurred.emit("Camera frame read failed")
                        break

                    now = time.monotonic()
                    if now < next_emit:
                        continue
                    next_emit = max(next_emit + frame_interval, now)

                    if self.config["mirror"]:
                        frame = cv2.flip(frame, 1)

                    height, width, channels = frame.shape
                    image = QImage(
                        frame.data,
                        width,
                        height,
                        frame.strides[0],
                        QImage.Format.Format_BGR888,
                    ).copy()
                    self.frameReady.emit(image)
            finally:
                cap.release()
            self.statusChanged.emit("Camera disconnected")

            if not self._should_run() or not self.config["reconnect"]:
                break
            if not self._interruptible_sleep(self.config["reconnect_interval_ms"]):
                break

        self._running = False

    def _should_run(self) -> bool:
        return self._running and not self.isInterruptionRequested()

    def _interruptible_sleep(self, duration_ms: int) -> bool:
        remaining = max(0, duration_ms)
        while remaining > 0 and self._should_run():
            step = min(50, remaining)
            self.msleep(step)
            remaining -= step
        return self._should_run()

    def _open_capture(self, cv2):
        source = self.config["camera_name"] or self.config["camera_source"]
        if not source:
            source = str(self.config["camera_index"])

        capture_source = int(source) if str(source).strip().isdigit() else source
        backend = BACKENDS.get(self.config["backend"], 0)
        cap = cv2.VideoCapture(capture_source, backend) if backend else cv2.VideoCapture(capture_source)

        width = self.config["resolution_width"]
        height = self.config["resolution_height"]
        fps = self.config["fps"]
        fourcc = self.config["fourcc"].strip()
        buffer_size = self.config["buffer_size"]

        if width > 0:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height > 0:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps > 0:
            cap.set(cv2.CAP_PROP_FPS, fps)
        if buffer_size > 0:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
        if fourcc:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc[:4].ljust(4)))

        return cap


class MonkezUSBCamera(MonkezImage):
    statusChanged = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None, background_color=(31, 31, 31)) -> None:
        super().__init__(parent, background_color, image_path("CameraOffline.png"))
        self._backend = "auto"
        self._camera_index = 0
        self._camera_source = "0"
        self._camera_name = ""
        self._resolution_width = 1280
        self._resolution_height = 720
        self._fps = 30
        self._display_fps = 30
        self._fourcc = "MJPG"
        self._buffer_size = 1
        self._mirror = False
        self._auto_start = False
        self._preview_auto_start = False
        self._stop_on_hide = True
        self._reconnect = True
        self._reconnect_interval_ms = 1000
        self._status = "Camera offline"
        self._capture_thread: CameraCaptureThread | None = None
        self.setSmoothScaling(False)
        self.image_label.setText("Camera offline")
        self.destroyed.connect(self._stop_camera_from_destroyed)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._auto_start and not self._is_designer_form_editor_widget():
            self.startCamera()
        elif self._preview_auto_start and self._is_running_in_designer():
            QTimer.singleShot(250, self._start_camera_if_preview_widget)

    def hideEvent(self, event) -> None:
        if self._stop_on_hide:
            self.stopCamera()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        self.stopCamera()
        super().closeEvent(event)

    def __del__(self) -> None:
        try:
            self.stopCamera()
        except Exception:
            pass

    def startCamera(self) -> None:
        if self._capture_thread is not None and self._capture_thread.isRunning():
            return

        config = {
            "backend": self._backend,
            "camera_index": self._camera_index,
            "camera_source": self._camera_source,
            "camera_name": self._camera_name,
            "resolution_width": self._resolution_width,
            "resolution_height": self._resolution_height,
            "fps": self._fps,
            "display_fps": self._display_fps,
            "fourcc": self._fourcc,
            "buffer_size": self._buffer_size,
            "mirror": self._mirror,
            "reconnect": self._reconnect,
            "reconnect_interval_ms": self._reconnect_interval_ms,
        }
        thread = CameraCaptureThread(config, self)
        self._capture_thread = thread
        thread.frameReady.connect(self._on_frame)
        thread.statusChanged.connect(self._set_status)
        thread.errorOccurred.connect(self._on_error)
        thread.finished.connect(lambda current=thread: self._on_capture_finished(current))
        thread.start()

    def stopCamera(self) -> None:
        if self._capture_thread is None:
            return
        thread = self._capture_thread
        thread.stop()
        if not thread.wait(2500):
            self._set_status("Camera is still stopping")
            return
        self._capture_thread = None
        thread.deleteLater()
        self._set_status("Camera stopped")

    def restartCamera(self) -> None:
        self.stopCamera()
        self.startCamera()

    def isRunning(self) -> bool:
        return self._capture_thread is not None and self._capture_thread.isRunning()

    def _on_capture_finished(self, thread: CameraCaptureThread) -> None:
        if self._capture_thread is thread:
            self._capture_thread = None
        thread.deleteLater()

    def _stop_camera_from_destroyed(self, *args) -> None:
        self.stopCamera()

    def _on_frame(self, image: QImage) -> None:
        self.set_image(image)

    def _on_error(self, message: str) -> None:
        self.errorOccurred.emit(message)
        self._set_status(message)
        if self._pixmap.isNull():
            self.setImageFile(image_path("CameraOffline.png"))

    def _set_status(self, message: str) -> None:
        self._status = message
        self.statusChanged.emit(message)
        if not self.isRunning():
            self.image_label.setText(message)

    def _start_camera_if_preview_widget(self) -> None:
        if not self._preview_auto_start or self.isRunning():
            return
        if self._is_designer_form_editor_widget():
            return
        if not self.isVisible():
            return
        self.startCamera()

    def _is_running_in_designer(self) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        app_name = (app.applicationName() or "").lower()
        return "designer" in app_name

    def _is_designer_form_editor_widget(self) -> bool:
        try:
            from PyQt6.QtDesigner import QDesignerFormWindowInterface
        except Exception:
            return False
        return QDesignerFormWindowInterface.findFormWindow(self) is not None

    def getBackend(self) -> str:
        return self._backend

    def setBackend(self, value: str) -> None:
        value = (value or "auto").strip().lower()
        self._backend = value if value in BACKENDS else "auto"

    def getBackendHint(self) -> str:
        return BACKEND_HINT_TEXT

    def setBackendHint(self, value: str) -> None:
        return None

    def getCameraIndex(self) -> int:
        return self._camera_index

    def setCameraIndex(self, value: int) -> None:
        self._camera_index = max(0, value)
        self._camera_source = str(self._camera_index)

    def getCameraSource(self) -> str:
        return self._camera_source

    def setCameraSource(self, value: str) -> None:
        self._camera_source = value or "0"
        if self._camera_source.strip().isdigit():
            self._camera_index = int(self._camera_source)

    def getCameraSourceHint(self) -> str:
        return CAMERA_SOURCE_HINT_TEXT

    def setCameraSourceHint(self, value: str) -> None:
        return None

    def getCameraName(self) -> str:
        return self._camera_name

    def setCameraName(self, value: str) -> None:
        self._camera_name = value or ""

    def getResolutionWidth(self) -> int:
        return self._resolution_width

    def setResolutionWidth(self, value: int) -> None:
        self._resolution_width = max(0, value)

    def getResolutionHeight(self) -> int:
        return self._resolution_height

    def setResolutionHeight(self, value: int) -> None:
        self._resolution_height = max(0, value)

    def getResolutionHint(self) -> str:
        return RESOLUTION_HINT_TEXT

    def setResolutionHint(self, value: str) -> None:
        return None

    def getFps(self) -> int:
        return self._fps

    def setFps(self, value: int) -> None:
        self._fps = min(240, max(1, value))

    def getDisplayFps(self) -> int:
        return self._display_fps

    def setDisplayFps(self, value: int) -> None:
        self._display_fps = min(120, max(1, value))

    def getFourcc(self) -> str:
        return self._fourcc

    def setFourcc(self, value: str) -> None:
        self._fourcc = (value or "")[:4]

    def getFourccHint(self) -> str:
        return FOURCC_HINT_TEXT

    def setFourccHint(self, value: str) -> None:
        return None

    def getBufferSize(self) -> int:
        return self._buffer_size

    def setBufferSize(self, value: int) -> None:
        self._buffer_size = max(0, value)

    def getMirror(self) -> bool:
        return self._mirror

    def setMirror(self, value: bool) -> None:
        self._mirror = bool(value)

    def getAutoStart(self) -> bool:
        return self._auto_start

    def setAutoStart(self, value: bool) -> None:
        self._auto_start = bool(value)

    def getPreviewAutoStart(self) -> bool:
        return self._preview_auto_start

    def setPreviewAutoStart(self, value: bool) -> None:
        self._preview_auto_start = bool(value)

    def getReconnect(self) -> bool:
        return self._reconnect

    def setReconnect(self, value: bool) -> None:
        self._reconnect = bool(value)

    def getReconnectIntervalMs(self) -> int:
        return self._reconnect_interval_ms

    def setReconnectIntervalMs(self, value: int) -> None:
        self._reconnect_interval_ms = max(100, value)

    def getStopOnHide(self) -> bool:
        return self._stop_on_hide

    def setStopOnHide(self, value: bool) -> None:
        self._stop_on_hide = bool(value)

    def getStatus(self) -> str:
        return self._status

    backend = pyqtProperty(str, getBackend, setBackend)
    backendHint = pyqtProperty(str, getBackendHint, setBackendHint, designable=True, stored=False)
    cameraIndex = pyqtProperty(int, getCameraIndex, setCameraIndex)
    cameraSource = pyqtProperty(str, getCameraSource, setCameraSource)
    cameraSourceHint = pyqtProperty(str, getCameraSourceHint, setCameraSourceHint, designable=True, stored=False)
    cameraName = pyqtProperty(str, getCameraName, setCameraName)
    resolutionWidth = pyqtProperty(int, getResolutionWidth, setResolutionWidth)
    resolutionHeight = pyqtProperty(int, getResolutionHeight, setResolutionHeight)
    resolutionHint = pyqtProperty(str, getResolutionHint, setResolutionHint, designable=True, stored=False)
    fps = pyqtProperty(int, getFps, setFps)
    displayFps = pyqtProperty(int, getDisplayFps, setDisplayFps)
    fourcc = pyqtProperty(str, getFourcc, setFourcc)
    fourccHint = pyqtProperty(str, getFourccHint, setFourccHint, designable=True, stored=False)
    bufferSize = pyqtProperty(int, getBufferSize, setBufferSize)
    mirror = pyqtProperty(bool, getMirror, setMirror)
    autoStart = pyqtProperty(bool, getAutoStart, setAutoStart)
    previewAutoStart = pyqtProperty(bool, getPreviewAutoStart, setPreviewAutoStart)
    stopOnHide = pyqtProperty(bool, getStopOnHide, setStopOnHide)
    reconnect = pyqtProperty(bool, getReconnect, setReconnect)
    reconnectIntervalMs = pyqtProperty(int, getReconnectIntervalMs, setReconnectIntervalMs)
    status = pyqtProperty(str, getStatus)
