from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

from monkez_pyqt6 import UiLoaderMixin, load_ui, load_ui_into
from monkez_pyqt6.monkez_widgets import MonkezButton


MAIN_WINDOW_UI = """\
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <widget class="QWidget" name="centralwidget">
   <widget class="MonkezButton" name="actionButton"/>
  </widget>
 </widget>
 <customwidgets>
  <customwidget>
   <class>MonkezButton</class>
   <extends>QPushButton</extends>
   <header>{header}</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>
"""

CHILD_UI = """\
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>ChildPanel</class>
 <widget class="QWidget" name="ChildPanel">
  <widget class="QWidget" name="innerWidget"/>
 </widget>
 <resources/>
 <connections/>
</ui>
"""


class MixinWindow(UiLoaderMixin, QMainWindow):
    pass


class UiLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _write_ui(self, directory: str, name: str, contents: str) -> Path:
        path = Path(directory) / name
        path.write_text(contents, encoding="utf-8")
        return path

    def test_load_ui_creates_top_level_widget_with_monkez_classes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_ui(
                directory,
                "main.ui",
                MAIN_WINDOW_UI.format(header="monkez_pyqt6.monkez_widgets"),
            )
            window = load_ui(path)

        self.assertIsInstance(window, QMainWindow)
        self.assertIsInstance(window.actionButton, MonkezButton)
        window.deleteLater()

    def test_load_ui_into_returns_the_existing_instance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_ui(
                directory,
                "main.ui",
                MAIN_WINDOW_UI.format(header="monkez_pyqt6.monkez_widgets"),
            )
            window = MixinWindow()
            loaded = window.load_ui(path)

        self.assertIs(loaded, window)
        self.assertIsInstance(window.actionButton, MonkezButton)
        window.deleteLater()

    def test_load_ui_can_parent_a_reusable_child_form(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_ui(directory, "child.ui", CHILD_UI)
            parent = QWidget()
            child = load_ui(path, parent=parent)

        self.assertIs(child.parentWidget(), parent)
        self.assertIsInstance(child.innerWidget, QWidget)
        parent.deleteLater()

    def test_load_ui_into_function_accepts_main_windows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_ui(
                directory,
                "main.ui",
                MAIN_WINDOW_UI.format(header="monkez_pyqt6.monkez_widgets"),
            )
            window = QMainWindow()
            loaded = load_ui_into(window, path)

        self.assertIs(loaded, window)
        window.deleteLater()

    def test_legacy_custom_widget_header_remains_loadable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_ui(
                directory,
                "legacy.ui",
                MAIN_WINDOW_UI.format(
                    header="custom_pyqt6_designer.monkez_widgets"
                ),
            )
            window = load_ui(path)

        self.assertIsInstance(window.actionButton, MonkezButton)
        window.deleteLater()

    def test_missing_ui_has_an_actionable_error(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "UI file was not found"):
            load_ui("missing-form.ui")

    def test_parent_and_existing_instance_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(ValueError, "parent cannot be used"):
            load_ui("unused.ui", QWidget(), parent=QWidget())


if __name__ == "__main__":
    unittest.main()
