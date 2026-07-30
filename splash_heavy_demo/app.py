from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from time import perf_counter

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from custom_pyqt6_designer.splash import SplashConfig, SplashController


APP_NAME = "Monkez Heavy Startup Demo"
VERIFY_FLAG = "--verify"


def resource_path(name: str) -> Path:
    """Resolve assets both from source and a PyInstaller one-folder build."""

    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / name
    return Path(__file__).resolve().parents[1] / name


class HeavyStartupWorker(QThread):
    """Runs deliberately expensive initialization without blocking Qt's UI thread."""

    progress = pyqtSignal(int, str)
    ready = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, workload_scale: float = 1.0, parent=None) -> None:
        super().__init__(parent)
        self.workload_scale = max(0.001, float(workload_scale))

    def run(self) -> None:
        started_at = perf_counter()
        try:
            self.progress.emit(4, "Reading a large configuration...")
            record_count = max(200, int(16_000 * self.workload_scale))
            configuration = json.dumps(
                [
                    {
                        "id": index,
                        "enabled": index % 3 != 0,
                        "route": f"/workspace/module/{index % 127}",
                    }
                    for index in range(record_count)
                ]
            )
            parsed_configuration = json.loads(configuration)
            self._paced_delay(0.9)

            self.progress.emit(22, "Loading and validating 48 MB of assets...")
            payload_size = max(1_048_576, int(48 * 1_048_576 * self.workload_scale))
            payload = bytearray((index * 31 + 17) & 0xFF for index in range(payload_size))
            digest = hashlib.sha256(payload).hexdigest()
            del payload
            self._paced_delay(1.3)

            self.progress.emit(48, "Building the application search index...")
            item_count = max(2_000, int(320_000 * self.workload_scale))
            search_index = sorted(
                ((index * 2_654_435_761) & 0xFFFFFFFF, index)
                for index in range(item_count)
            )
            index_checksum = sum(
                value for value, _ in search_index[:: max(1, item_count // 500)]
            )
            self._paced_delay(1.2)

            self.progress.emit(72, "Warming the calculation engine...")
            iterations = max(20_000, int(2_400_000 * self.workload_scale))
            accumulator = 0.0
            for index in range(1, iterations + 1):
                accumulator += math.sin(index * 0.0007) * math.cos(index * 0.0003)
            self._paced_delay(1.2)

            self.progress.emit(91, "Connecting services and restoring workspace...")
            workspace_count = sum(1 for item in parsed_configuration if item["enabled"])
            self._paced_delay(0.8)

            elapsed = perf_counter() - started_at
            self.progress.emit(100, "Startup complete")
            self.ready.emit(
                {
                    "elapsed_seconds": elapsed,
                    "config_records": len(parsed_configuration),
                    "asset_megabytes": payload_size / 1_048_576,
                    "asset_digest": digest[:12],
                    "index_items": len(search_index),
                    "index_checksum": index_checksum,
                    "workspace_items": workspace_count,
                    "engine_result": accumulator,
                }
            )
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")

    def _paced_delay(self, seconds: float) -> None:
        remaining_ms = max(0, int(seconds * 1000 * self.workload_scale))
        while remaining_ms > 0 and not self.isInterruptionRequested():
            step = min(remaining_ms, 50)
            self.msleep(step)
            remaining_ms -= step


class MetricCard(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(5)
        caption = QLabel(title)
        caption.setObjectName("metricCaption")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("metricValue")
        layout.addWidget(caption)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class DemoWindow(QMainWindow):
    def __init__(self, verification_mode: bool = False) -> None:
        super().__init__()
        self.verification_mode = verification_mode
        self.max_frame_gap_ms = 0.0
        self._last_heartbeat = perf_counter()
        self._worker: HeavyStartupWorker | None = None
        self._splash: SplashController | None = None
        self._verification_failed = False

        self.setWindowTitle(APP_NAME)
        self.resize(920, 610)
        self.setMinimumSize(760, 500)
        self._build_ui()
        self._apply_style()

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(16)
        self._heartbeat_timer.timeout.connect(self._record_heartbeat)
        self._heartbeat_timer.start()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(38, 32, 38, 34)
        layout.setSpacing(22)

        eyebrow = QLabel("BACKGROUND LOADING DEMONSTRATION")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("The interface stayed responsive")
        title.setObjectName("title")
        subtitle = QLabel(
            "Initialization ran on a worker thread while the splash screen "
            "animated and received live progress updates."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        self.time_card = MetricCard("STARTUP LOAD")
        self.data_card = MetricCard("PROCESSED DATA")
        self.frame_card = MetricCard("MAX UI GAP")
        metrics.addWidget(self.time_card)
        metrics.addWidget(self.data_card)
        metrics.addWidget(self.frame_card)

        log_frame = QFrame()
        log_frame.setObjectName("logFrame")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(20, 17, 20, 17)
        log_title = QLabel("Startup activity")
        log_title.setObjectName("logTitle")
        self.activity_label = QLabel("Waiting for startup...")
        self.activity_label.setObjectName("activity")
        self.activity_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.activity_label.setWordWrap(True)
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.activity_label, 1)

        footer = QHBoxLayout()
        self.result_label = QLabel("Ready")
        self.result_label.setObjectName("result")
        self.run_again_button = QPushButton("Run heavy startup again")
        self.run_again_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_again_button.clicked.connect(self.start_loading)
        footer.addWidget(self.result_label, 1)
        footer.addWidget(self.run_again_button)

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(metrics)
        layout.addWidget(log_frame, 1)
        layout.addLayout(footer)
        self.setCentralWidget(root)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #08111f;
                color: #e7eef8;
                font-family: "Segoe UI";
            }
            QLabel#eyebrow {
                color: #38bdf8;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#title {
                font-size: 32px;
                font-weight: 700;
            }
            QLabel#subtitle {
                color: #91a4bc;
                font-size: 15px;
            }
            QFrame#metricCard, QFrame#logFrame {
                background: #101c2e;
                border: 1px solid #1e324d;
                border-radius: 14px;
            }
            QLabel#metricCaption {
                color: #7890ac;
                font-size: 10px;
                font-weight: 700;
            }
            QLabel#metricValue {
                color: #f6f9fd;
                font-size: 23px;
                font-weight: 700;
            }
            QLabel#logTitle {
                color: #dbe8f7;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#activity, QLabel#result {
                color: #91a4bc;
                font-size: 13px;
            }
            QPushButton {
                background: #0ea5e9;
                color: white;
                border: none;
                border-radius: 9px;
                padding: 11px 20px;
                font-weight: 700;
            }
            QPushButton:hover { background: #38bdf8; }
            QPushButton:pressed { background: #0284c7; }
            QPushButton:disabled { background: #334155; color: #94a3b8; }
            """
        )

    def start_loading(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self.max_frame_gap_ms = 0.0
        self._last_heartbeat = perf_counter()
        self.activity_label.setText("")
        self.result_label.setText("Heavy initialization is running")
        self.run_again_button.setEnabled(False)

        self._splash = SplashController.create(
            SplashConfig(
                app_name=APP_NAME,
                app_version="64-bit portable demo",
                initial_status="Starting background worker...",
                background_image=str(resource_path("logo.png")),
                background_color="#08111f",
                text_color="#f8fafc",
                accent_color="#38bdf8",
                image_mode=1,
                size=(720, 430),
                minimum_visible_ms=700,
                fade_in_ms=120,
                fade_out_ms=180,
            )
        ).show()

        scale = 0.015 if self.verification_mode else 1.0
        self._worker = HeavyStartupWorker(scale, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.ready.connect(self._on_ready)
        self._worker.failed.connect(self._on_failure)
        self._worker.start(QThread.Priority.NormalPriority)

    def _on_progress(self, progress: int, status: str) -> None:
        if self._splash is not None:
            self._splash.set_progress(progress, status)
        current = self.activity_label.text()
        entry = f"{progress:>3}%  {status}"
        self.activity_label.setText(entry if not current else f"{current}\n{entry}")

    def _on_ready(self, result: dict) -> None:
        self.time_card.set_value(f"{result['elapsed_seconds']:.2f} s")
        self.data_card.set_value(f"{result['asset_megabytes']:.0f} MB")
        self.frame_card.set_value(f"{self.max_frame_gap_ms:.1f} ms")
        self.result_label.setText(
            f"Index: {result['index_items']:,} items  •  "
            f"Asset SHA-256: {result['asset_digest']}"
        )
        self.run_again_button.setEnabled(True)
        if self._splash is not None:
            self._splash.finish(self)
        if self.verification_mode:
            QTimer.singleShot(250, QApplication.instance().quit)

    def _on_failure(self, message: str) -> None:
        self._verification_failed = True
        self.activity_label.setText(f"Startup failed:\n{message}")
        self.result_label.setText("Initialization failed")
        self.run_again_button.setEnabled(True)
        if self._splash is not None:
            self._splash.finish(self)
        if self.verification_mode:
            QTimer.singleShot(250, QApplication.instance().quit)

    def _record_heartbeat(self) -> None:
        now = perf_counter()
        gap_ms = (now - self._last_heartbeat) * 1000
        self._last_heartbeat = now
        self.max_frame_gap_ms = max(self.max_frame_gap_ms, gap_ms)


def main() -> int:
    verification_mode = VERIFY_FLAG in sys.argv
    app = QApplication([argument for argument in sys.argv if argument != VERIFY_FLAG])
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))

    window = DemoWindow(verification_mode)
    QTimer.singleShot(0, window.start_loading)
    exit_code = app.exec()
    return 2 if window._verification_failed else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
