from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt6.QtWidgets import QApplication


PLUGIN_DIR = Path(__file__).resolve().parents[1] / "src" / "custom_pyqt6_designer" / "designer_plugins"


class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        sys.path.insert(0, str(PLUGIN_DIR))

    def test_all_designer_plugins_construct(self) -> None:
        names = []
        for path in sorted(PLUGIN_DIR.glob("*_plugin.py")):
            module = importlib.import_module(path.stem)
            plugin_classes = [
                value
                for value in vars(module).values()
                if isinstance(value, type)
                and issubclass(value, QPyDesignerCustomWidgetPlugin)
                and value is not QPyDesignerCustomWidgetPlugin
            ]
            self.assertEqual(len(plugin_classes), 1, path.name)
            plugin = plugin_classes[0]()
            widget = plugin.createWidget(None)
            self.assertEqual(plugin.name(), type(widget).__name__)
            self.assertFalse(plugin.icon().isNull(), plugin.name())
            self.assertIn(plugin.name(), plugin.domXml())
            names.append(plugin.name())
            widget.deleteLater()

        self.assertEqual(len(names), 21)
        self.assertNotIn("MetricCard", names)
        self.assertNotIn("StatusBadge", names)


if __name__ == "__main__":
    unittest.main()
