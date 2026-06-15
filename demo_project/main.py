from __future__ import annotations

import sys
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

# The .ui loader resolves custom widget classes through the header declared in
# ui/main_window.ui: custom_pyqt6_designer.monkez_widgets.
from custom_pyqt6_designer import monkez_widgets  # noqa: F401


ROOT = Path(__file__).resolve().parent


class DemoWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        uic.loadUi(ROOT / "ui" / "main_window.ui", self)

        self._direction = 1
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._advance_live_value)

        self.themeSelector.currentIndexChanged.connect(self.apply_theme)
        self.valueSlider.valueChanged.connect(self.update_value)
        self.valueDial.valueChanged.connect(self.valueSlider.setValue)
        self.applyButton.clicked.connect(self.apply_profile)
        self.resetButton.clicked.connect(self.reset_demo)
        self.liveSwitch.toggled.connect(self.set_live_mode)

        self.update_value(self.valueSlider.value())
        self.apply_theme(self.themeSelector.currentIndex())

    def apply_theme(self, theme_index: int) -> None:
        for widget in self.findChildren(QWidget):
            if widget.metaObject().indexOfProperty("themeIndex") >= 0:
                widget.setProperty("themeIndex", theme_index)
        self.themeNameLabel.setText(self.themeSelector.currentText())

    def update_value(self, value: int) -> None:
        self.valueProgress.setValue(value)
        self.valueDial.blockSignals(True)
        self.valueDial.setValue(value)
        self.valueDial.blockSignals(False)
        self.valueLcd.display(value)
        self.statusLabel.setText(f"Current value: {value}%")

    def apply_profile(self) -> None:
        name = self.nameInput.text().strip() or "Anonymous"
        profile = self.profileCombo.currentText()
        target = self.targetSpin.value()
        self.valueSlider.setValue(target)
        self.statusLabel.setText(f"Applied {profile} profile for {name}, target {target}%")

    def reset_demo(self) -> None:
        self.liveSwitch.setChecked(False)
        self.nameInput.clear()
        self.profileCombo.setCurrentIndex(0)
        self.targetSpin.setValue(68)
        self.valueSlider.setValue(42)
        self.statusLabel.setText("Demo reset")

    def set_live_mode(self, enabled: bool) -> None:
        if enabled:
            self._timer.start()
            self.statusLabel.setText("Live updates enabled")
        else:
            self._timer.stop()
            self.statusLabel.setText("Live updates paused")

    def _advance_live_value(self) -> None:
        value = self.valueSlider.value() + self._direction * 2
        if value >= 100:
            value = 100
            self._direction = -1
        elif value <= 0:
            value = 0
            self._direction = 1
        self.valueSlider.setValue(value)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Monkez Runtime Demo")
    window = DemoWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
