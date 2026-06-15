from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "demo_project"
sys.path.insert(0, str(DEMO_ROOT))

from main import DemoWindow


class DemoProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_ui_loads_and_runtime_connections_work(self) -> None:
        window = DemoWindow()
        self.assertEqual(window.profileGroup.subtitle, "Configure values and apply them at runtime")

        window.nameInput.setText("Monkez")
        window.targetSpin.setValue(73)
        window.applyButton.click()

        self.assertEqual(window.valueProgress.value(), 73)
        self.assertIn("Monkez", window.statusLabel.text())

        window.themeSelector.setCurrentIndex(5)
        self.assertEqual(window.profileGroup.themeIndex, 5)
        self.assertEqual(window.valueDial.themeIndex, 5)
        window.close()


if __name__ == "__main__":
    unittest.main()
