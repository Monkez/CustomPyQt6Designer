from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow

from monkez_pyqt6.splash import SplashConfig, SplashController


ROOT = Path(__file__).resolve().parent


def main() -> int:
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_window.setWindowTitle("Splash demo")
    main_window.setCentralWidget(QLabel("Application is ready"))
    main_window.resize(720, 480)

    splash = SplashController.from_ui(
        ROOT / "splash_screen.ui",
        SplashConfig(
            app_name="Monkez Studio",
            app_version="Version 0.4",
            initial_status="Preparing startup...",
            minimum_visible_ms=900,
        ),
    ).show()

    stages = (
        (12, "Reading configuration..."),
        (34, "Loading plugins..."),
        (58, "Connecting services..."),
        (82, "Building workspace..."),
        (100, "Ready"),
    )

    def next_stage(index: int = 0) -> None:
        progress, status = stages[index]
        splash.set_progress(progress, status)
        if index + 1 < len(stages):
            QTimer.singleShot(220, lambda: next_stage(index + 1))
        else:
            QTimer.singleShot(250, lambda: splash.finish(main_window))

    QTimer.singleShot(80, next_stage)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
