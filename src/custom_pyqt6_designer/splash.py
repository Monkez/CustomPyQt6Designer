from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable

from PyQt6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QLabel, QProgressBar, QWidget

from .monkez_widgets import MonkezSplashScreen


@dataclass(slots=True)
class SplashConfig:
    app_name: str = "Monkez Application"
    app_version: str = "Version 1.0"
    initial_status: str = "Starting..."
    background_image: str = ""
    background_color: str = "#0f172a"
    text_color: str = "#f8fafc"
    accent_color: str = "#38bdf8"
    image_mode: int = 0
    size: tuple[int, int] | None = None
    initial_progress: int = 0
    minimum_visible_ms: int = 450
    fade_in_ms: int = 180
    fade_out_ms: int = 220
    progress_animation_ms: int = 220
    always_on_top: bool = True
    transparent_background: bool = True
    animation_enabled: bool = True
    show_progress: bool = True
    show_spinner: bool = True
    center_on_screen: bool = True
    process_events_on_update: bool = False


class SplashController(QObject):
    """Coordinates splash UI updates and transition to the main window."""

    progressChanged = pyqtSignal(int, str)
    statusChanged = pyqtSignal(str)
    shown = pyqtSignal()
    finished = pyqtSignal()

    _progress_requested = pyqtSignal(int, str)
    _status_requested = pyqtSignal(str)

    def __init__(
        self,
        widget: QWidget,
        config: SplashConfig | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.widget = widget
        self.config = config or SplashConfig()
        self._shown_at = 0.0
        self._finishing = False
        self._fade_animation: QPropertyAnimation | None = None
        self._named_progress_animation = QVariantAnimation(self)
        self._named_progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._named_progress_animation.valueChanged.connect(
            lambda value: self._set_named_progress(int(round(float(value))))
        )
        self._progress = max(0, min(100, int(self.config.initial_progress)))

        self._progress_requested.connect(self._apply_progress)
        self._status_requested.connect(self._apply_status)
        self._configure_widget()

    @classmethod
    def create(
        cls,
        config: SplashConfig | None = None,
        parent: QObject | None = None,
    ) -> "SplashController":
        cls._require_application()
        return cls(MonkezSplashScreen(), config=config, parent=parent)

    @classmethod
    def from_ui(
        cls,
        ui_file: str | Path,
        config: SplashConfig | None = None,
        parent: QObject | None = None,
    ) -> "SplashController":
        cls._require_application()
        from PyQt6 import uic

        widget = uic.loadUi(str(Path(ui_file)))
        if not isinstance(widget, QWidget):
            raise TypeError("Splash UI root must be a QWidget or MonkezSplashScreen.")
        return cls(widget, config=config, parent=parent)

    @property
    def progress(self) -> int:
        return self._progress

    def _configure_widget(self) -> None:
        config = self.config
        if isinstance(self.widget, MonkezSplashScreen):
            self.widget.set_runtime_window_mode(config.always_on_top)
            self.widget.setAppName(config.app_name)
            self.widget.setAppVersion(config.app_version)
            self.widget.setStatusText(config.initial_status)
            self.widget.setBackgroundImage(config.background_image)
            self.widget.setBackgroundColor(QColor(config.background_color))
            self.widget.setTextColor(QColor(config.text_color))
            self.widget.setAccentColor(QColor(config.accent_color))
            self.widget.setImageMode(config.image_mode)
            self.widget.setTransparentBackground(config.transparent_background)
            self.widget.setAnimationEnabled(config.animation_enabled)
            self.widget.setShowProgress(config.show_progress)
            self.widget.setShowSpinner(config.show_spinner)
            if self._has_custom_content():
                self.widget.setDefaultContentVisible(False)
            self.widget.setProgress(config.initial_progress)
        else:
            flags = self.widget.windowFlags()
            from PyQt6.QtCore import Qt

            flags |= Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
            if config.always_on_top:
                flags |= Qt.WindowType.WindowStaysOnTopHint
            self.widget.setWindowFlags(flags)
            self.widget.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground,
                config.transparent_background,
            )

        self._set_named_text("splashAppNameLabel", config.app_name)
        self._set_named_text("splashVersionLabel", config.app_version)
        self._set_named_text("splashStatusLabel", config.initial_status)
        self._set_named_progress(config.initial_progress)
        if config.size is not None:
            self.widget.resize(max(1, int(config.size[0])), max(1, int(config.size[1])))

    @staticmethod
    def _require_application() -> None:
        if QApplication.instance() is None:
            raise RuntimeError("Create QApplication before creating the splash screen.")

    def _has_custom_content(self) -> bool:
        return any(
            self.widget.findChild(QWidget, name) is not None
            for name in (
                "splashAppNameLabel",
                "splashVersionLabel",
                "splashStatusLabel",
                "splashProgressBar",
            )
        )

    def _set_named_text(self, object_name: str, text: str) -> None:
        label = self.widget.findChild(QLabel, object_name)
        if label is not None:
            label.setText(text)

    def _set_named_progress(self, value: int) -> None:
        progress = self.widget.findChild(QProgressBar, "splashProgressBar")
        if progress is not None:
            progress.setValue(value)

    def show(self) -> "SplashController":
        if self.config.center_on_screen:
            self.center()
        if self.config.animation_enabled and self.config.fade_in_ms > 0:
            self.widget.setWindowOpacity(0.0)
        self.widget.show()
        self.widget.raise_()
        self._shown_at = perf_counter()
        self._start_fade(0.0, 1.0, self.config.fade_in_ms)
        self._flush_events()
        self.shown.emit()
        return self

    def center(self) -> None:
        screen = self.widget.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        target = QPoint(
            area.x() + (area.width() - self.widget.width()) // 2,
            area.y() + (area.height() - self.widget.height()) // 2,
        )
        self.widget.move(target)

    def set_progress(self, value: int, status: str = "") -> "SplashController":
        self._progress_requested.emit(int(value), str(status))
        return self

    def update(self, progress: int | None = None, status: str = "") -> "SplashController":
        if progress is None:
            self.set_status(status)
        else:
            self.set_progress(progress, status)
        return self

    def advance(self, amount: int = 1, status: str = "") -> "SplashController":
        return self.set_progress(self._progress + int(amount), status)

    def set_stage(
        self,
        index: int,
        total: int,
        status: str = "",
    ) -> "SplashController":
        denominator = max(1, int(total))
        return self.set_progress(round(max(0, int(index)) * 100 / denominator), status)

    def set_status(self, status: str) -> "SplashController":
        self._status_requested.emit(str(status))
        return self

    @pyqtSlot(int, str)
    def _apply_progress(self, value: int, status: str) -> None:
        self._progress = max(0, min(100, int(value)))
        if isinstance(self.widget, MonkezSplashScreen):
            self.widget.setProgress(self._progress)
            if status:
                self.widget.setStatusText(status)
        named_progress = self.widget.findChild(QProgressBar, "splashProgressBar")
        if (
            named_progress is not None
            and self.config.animation_enabled
            and self.widget.isVisible()
        ):
            self._named_progress_animation.stop()
            self._named_progress_animation.setDuration(
                max(0, int(self.config.progress_animation_ms))
            )
            self._named_progress_animation.setStartValue(named_progress.value())
            self._named_progress_animation.setEndValue(self._progress)
            self._named_progress_animation.start()
        else:
            self._set_named_progress(self._progress)
        if status:
            self._set_named_text("splashStatusLabel", status)
            self.statusChanged.emit(status)
        self.progressChanged.emit(self._progress, status)
        self._flush_events_if_requested()

    @pyqtSlot(str)
    def _apply_status(self, status: str) -> None:
        if isinstance(self.widget, MonkezSplashScreen):
            self.widget.setStatusText(status)
        self._set_named_text("splashStatusLabel", status)
        self.statusChanged.emit(status)
        self._flush_events_if_requested()

    def run_steps(
        self,
        steps: Iterable[tuple[str, Callable[[], object]]],
    ) -> None:
        planned = list(steps)
        total = len(planned)
        for index, (status, callback) in enumerate(planned, start=1):
            self.set_stage(index - 1, total, status)
            self._flush_events()
            callback()
        self.set_progress(100, "Ready")

    def finish(
        self,
        main_window: QWidget | None = None,
        show_main_window: bool = True,
    ) -> None:
        if self._finishing:
            return
        self._finishing = True
        elapsed_ms = int((perf_counter() - self._shown_at) * 1000) if self._shown_at else 0
        delay = max(0, int(self.config.minimum_visible_ms) - elapsed_ms)
        QTimer.singleShot(delay, lambda: self._begin_finish(main_window, show_main_window))

    def close(self) -> None:
        self.finish(None, False)

    def _begin_finish(
        self,
        main_window: QWidget | None,
        show_main_window: bool,
    ) -> None:
        if main_window is not None and show_main_window:
            main_window.show()
            main_window.raise_()
        duration = self.config.fade_out_ms if self.config.animation_enabled else 0
        if duration <= 0:
            self._complete_finish()
            return
        animation = self._start_fade(self.widget.windowOpacity(), 0.0, duration)
        animation.finished.connect(self._complete_finish)

    def _complete_finish(self) -> None:
        self.widget.close()
        self.finished.emit()

    def _start_fade(
        self,
        start: float,
        end: float,
        duration_ms: int,
    ) -> QPropertyAnimation:
        if self._fade_animation is not None:
            self._fade_animation.stop()
        animation = QPropertyAnimation(self.widget, b"windowOpacity", self)
        animation.setDuration(max(0, int(duration_ms)))
        animation.setStartValue(float(start))
        animation.setEndValue(float(end))
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation = animation
        animation.start()
        return animation

    def _flush_events_if_requested(self) -> None:
        if self.config.process_events_on_update:
            self._flush_events()

    @staticmethod
    def _flush_events() -> None:
        app = QApplication.instance()
        if app is not None:
            app.processEvents()


def show_splash(
    *,
    app_name: str = "Monkez Application",
    app_version: str = "Version 1.0",
    background_image: str = "",
    status: str = "Starting...",
    ui_file: str | Path | None = None,
    **config_overrides,
) -> SplashController:
    """Create and immediately show a splash controller with minimal boilerplate."""

    config = SplashConfig(
        app_name=app_name,
        app_version=app_version,
        background_image=background_image,
        initial_status=status,
        **config_overrides,
    )
    controller = (
        SplashController.from_ui(ui_file, config)
        if ui_file is not None
        else SplashController.create(config)
    )
    return controller.show()
