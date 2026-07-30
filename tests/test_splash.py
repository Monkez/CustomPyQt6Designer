from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication, QLabel, QProgressBar

from custom_pyqt6_designer.monkez_widgets import MonkezSplashScreen
from custom_pyqt6_designer.splash import SplashConfig, SplashController


ROOT = Path(__file__).resolve().parents[1]


class SplashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_widget_properties_and_transparent_png(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "transparent.png"
            image = QImage(16, 16, QImage.Format.Format_ARGB32)
            image.fill(QColor(255, 0, 0, 80))
            self.assertTrue(image.save(str(image_path)))

            splash = MonkezSplashScreen()
            splash.setAnimationEnabled(False)
            splash.setAppName("Fast App")
            splash.setAppVersion("Version 4.0")
            splash.setStatusText("Loading...")
            splash.setProgress(42)
            splash.setBackgroundImage(str(image_path))

            self.assertEqual(splash.appName, "Fast App")
            self.assertEqual(splash.appVersion, "Version 4.0")
            self.assertEqual(splash.statusText, "Loading...")
            self.assertEqual(splash.progress, 42)
            self.assertFalse(splash._background_pixmap.isNull())
            self.assertTrue(splash._background_pixmap.hasAlphaChannel())
            splash.deleteLater()

    def test_controller_updates_default_and_named_designer_content(self) -> None:
        widget = MonkezSplashScreen()
        app_label = QLabel(widget)
        app_label.setObjectName("splashAppNameLabel")
        version_label = QLabel(widget)
        version_label.setObjectName("splashVersionLabel")
        status_label = QLabel(widget)
        status_label.setObjectName("splashStatusLabel")
        progress_bar = QProgressBar(widget)
        progress_bar.setObjectName("splashProgressBar")

        controller = SplashController(
            widget,
            SplashConfig(
                app_name="Designer App",
                app_version="Version 0.4",
                initial_status="Preparing",
                animation_enabled=False,
                minimum_visible_ms=0,
            ),
        )
        controller.set_progress(65, "Loading workspace")

        self.assertFalse(widget.defaultContentVisible)
        self.assertEqual(app_label.text(), "Designer App")
        self.assertEqual(version_label.text(), "Version 0.4")
        self.assertEqual(status_label.text(), "Loading workspace")
        self.assertEqual(progress_bar.value(), 65)
        self.assertEqual(widget.progress, 65)
        widget.deleteLater()

    def test_progress_updates_are_safe_from_worker_thread(self) -> None:
        controller = SplashController.create(
            SplashConfig(animation_enabled=False, minimum_visible_ms=0)
        ).show()

        worker = threading.Thread(
            target=lambda: controller.set_progress(73, "Worker ready"),
            daemon=True,
        )
        worker.start()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())

        deadline = time.monotonic() + 2
        while controller.progress != 73 and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)

        self.assertEqual(controller.progress, 73)
        self.assertEqual(controller.widget.statusText, "Worker ready")
        controller.widget.close()
        controller.widget.deleteLater()

    def test_designer_ui_template_loads_and_receives_progress(self) -> None:
        controller = SplashController.from_ui(
            ROOT / "examples" / "splash_screen.ui",
            SplashConfig(
                app_name="UI Template",
                app_version="Version 9",
                animation_enabled=False,
                minimum_visible_ms=0,
            ),
        )
        controller.set_progress(88, "Almost ready")

        self.assertIsInstance(controller.widget, MonkezSplashScreen)
        self.assertEqual(
            controller.widget.findChild(QLabel, "splashAppNameLabel").text(),
            "UI Template",
        )
        self.assertEqual(
            controller.widget.findChild(QLabel, "splashStatusLabel").text(),
            "Almost ready",
        )
        self.assertEqual(
            controller.widget.findChild(QProgressBar, "splashProgressBar").value(),
            88,
        )
        controller.widget.deleteLater()

    def test_fast_import_path_does_not_load_unrelated_widgets(self) -> None:
        script = (
            "import sys,time;"
            "t=time.perf_counter();"
            "from custom_pyqt6_designer.splash import show_splash;"
            "elapsed=(time.perf_counter()-t)*1000;"
            "blocked=['custom_pyqt6_designer.gallery_app',"
            "'custom_pyqt6_designer.monkez_widgets.monkez_usb_camera','cv2'];"
            "print(round(elapsed,2));"
            "print(any(name in sys.modules for name in blocked))"
        )
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        lines = result.stdout.strip().splitlines()
        self.assertLess(float(lines[-2]), 1500.0)
        self.assertEqual(lines[-1], "False")


if __name__ == "__main__":
    unittest.main()
