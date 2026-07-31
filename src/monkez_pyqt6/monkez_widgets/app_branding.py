from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication


ENV_APP_ICON = "MONKEZ_DESIGNER_ICON"
_branding_scheduled = False


def apply_designer_branding() -> None:
    global _branding_scheduled
    if _branding_scheduled:
        return

    app = QApplication.instance()
    icon_path = Path(os.environ.get(ENV_APP_ICON, ""))
    if app is None or not icon_path.is_file():
        return

    icon = QIcon(str(icon_path))
    if icon.isNull():
        return

    _branding_scheduled = True
    app.setWindowIcon(icon)

    def apply_to_windows() -> None:
        for window in app.topLevelWidgets():
            window.setWindowIcon(icon)

    apply_to_windows()
    for delay in (0, 250, 1000):
        QTimer.singleShot(delay, apply_to_windows)
