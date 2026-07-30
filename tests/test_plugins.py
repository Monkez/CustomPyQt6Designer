from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtDesigner import QExtensionManager, QPyDesignerCustomWidgetPlugin
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
            if plugin.name() == "MonkezSplashScreen":
                self.assertEqual(plugin.domXml(), "")
                self.assertTrue(plugin.isContainer())
            else:
                self.assertIn(plugin.name(), plugin.domXml())
            names.append(plugin.name())
            widget.deleteLater()

        self.assertEqual(len(names), 25)
        self.assertNotIn("MetricCard", names)
        self.assertNotIn("StatusBadge", names)

    def test_theme_task_menu_exposes_all_runtime_themes(self) -> None:
        theme_task_menu = importlib.import_module("theme_task_menu")
        self.assertEqual(
            [entry[0] for entry in theme_task_menu.THEME_LABELS],
            ["Material", "iOS", "Fluent", "Bootstrap", "Minimal", "Dark"],
        )
        self.assertEqual(
            [entry[3] for entry in theme_task_menu.THEME_LABELS],
            list(range(6)),
        )
        image = importlib.import_module(
            "custom_pyqt6_designer.monkez_widgets"
        ).MonkezImage()
        menu = theme_task_menu.MonkezThemeTaskMenu(image)
        self.assertEqual(
            [action.text() for action in menu.taskActions() if action.text().startswith("Image Scale:")],
            [
                "Image Scale: Fit",
                "Image Scale: Fill",
                "Image Scale: Stretch",
                "Image Scale: Original",
            ],
        )
        image.deleteLater()

    def test_image_plugin_registers_its_designer_task_menu(self) -> None:
        image_plugin = importlib.import_module("monkez_image_plugin")
        theme_task_menu = importlib.import_module("theme_task_menu")
        manager = QExtensionManager()

        class DesignerCore:
            def extensionManager(self):
                return manager

        plugin = image_plugin.MonkezImagePlugin()
        plugin.initialize(DesignerCore())
        image = plugin.createWidget(None)
        menu = manager.extension(image, theme_task_menu.TASK_MENU_IID)

        self.assertIsNotNone(menu)
        self.assertEqual(
            [action.text() for action in menu.taskActions() if action.text().startswith("Image Scale:")],
            [
                "Image Scale: Fit",
                "Image Scale: Fill",
                "Image Scale: Stretch",
                "Image Scale: Original",
            ],
        )
        image.deleteLater()

    def test_plugins_are_arranged_in_logical_palette_groups(self) -> None:
        expected_groups = {
            "Monkez 01 Controls",
            "Monkez 02 Inputs",
            "Monkez 03 Value Editors",
            "Monkez 04 Display",
            "Monkez 05 Gauges",
            "Monkez 06 Containers",
            "Monkez 07 Media",
        }
        groups = set()
        for path in sorted(PLUGIN_DIR.glob("*_plugin.py")):
            module = importlib.import_module(path.stem)
            plugin_class = next(
                value
                for value in vars(module).values()
                if isinstance(value, type)
                and issubclass(value, QPyDesignerCustomWidgetPlugin)
                and value is not QPyDesignerCustomWidgetPlugin
            )
            groups.add(plugin_class().group())

        self.assertEqual(groups, expected_groups)

    def test_scroll_area_exposes_its_content_page_to_designer(self) -> None:
        scroll_plugin = importlib.import_module("monkez_scroll_area_plugin")
        container_support = importlib.import_module("scroll_area_container")
        manager = QExtensionManager()

        class DesignerCore:
            def extensionManager(self):
                return manager

        plugin = scroll_plugin.MonkezScrollAreaPlugin()
        plugin.initialize(DesignerCore())
        widget = plugin.createWidget(None)
        extension = manager.extension(widget, container_support.CONTAINER_IID)

        self.assertIsNotNone(extension)
        self.assertEqual(extension.count(), 1)
        self.assertEqual(extension.currentIndex(), 0)
        self.assertIs(extension.widget(0), widget.widget())
        self.assertFalse(extension.canAddWidget())
        self.assertFalse(extension.canRemove(0))
        widget.deleteLater()


if __name__ == "__main__":
    unittest.main()
