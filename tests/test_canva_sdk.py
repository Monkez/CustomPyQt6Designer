from __future__ import annotations

import os
import importlib.util
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QDoubleSpinBox, QLabel

from monkez_pyqt6.monkez_canva import (
    COMPONENT_SDK_VERSION,
    CanvasDocument,
    ComponentPlugin,
    ElementDefinition,
    ElementRegistry,
    component_plugin,
    install_component_plugin,
    uninstall_component_plugin,
)
from monkez_pyqt6.monkez_widgets import MonkezCanva


def definition(
    type_id: str,
    plugin_id: str = "com.example.telemetry",
    **options,
) -> ElementDefinition:
    return ElementDefinition(
        type_id,
        type_id.replace("_", " ").title(),
        "SDK tests",
        160,
        90,
        plugin_id=plugin_id,
        **options,
    )


class ComponentSdkCoreTests(unittest.TestCase):
    def test_manifest_normalizes_metadata_and_validates_ownership(self) -> None:
        plugin = component_plugin(
            "COM.EXAMPLE.Telemetry",
            "Telemetry",
            "1.2.0",
            [definition("sensor")],
            metadata={"vendor": "Example"},
        )

        self.assertEqual("com.example.telemetry", plugin.plugin_id)
        self.assertEqual(("sensor",), plugin.type_ids)
        self.assertEqual("Example", plugin.metadata["vendor"])
        self.assertEqual(1, COMPONENT_SDK_VERSION)
        with self.assertRaises(TypeError):
            plugin.metadata["vendor"] = "Changed"

        with self.assertRaisesRegex(ValueError, "owned"):
            ComponentPlugin(
                "com.example.other", "Other", "1.0", (definition("wrong"),)
            )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            component_plugin(
                "com.example.telemetry",
                "Duplicate",
                "1.0",
                (definition("same"), definition("same")),
            )
        with self.assertRaisesRegex(ValueError, "requires SDK"):
            component_plugin(
                "com.example.telemetry",
                "Future",
                "1.0",
                (definition("future"),),
                minimum_sdk=COMPONENT_SDK_VERSION + 1,
            )

    def test_registry_install_is_atomic_idempotent_and_placeholder_safe(self) -> None:
        registry = ElementRegistry(
            (
                definition("foreign", "com.example.foreign"),
                definition("missing", "__missing__"),
            )
        )
        conflicting = component_plugin(
            "com.example.telemetry",
            "Telemetry",
            "1.0",
            (definition("sensor"), definition("foreign")),
        )

        with self.assertRaisesRegex(ValueError, "conflicts"):
            install_component_plugin(registry, conflicting)
        self.assertIsNone(registry.definition("sensor"))
        self.assertEqual("com.example.foreign", registry.require("foreign").plugin_id)

        plugin = component_plugin(
            "com.example.telemetry",
            "Telemetry",
            "1.0",
            (definition("sensor"), definition("missing")),
        )
        self.assertEqual(("sensor", "missing"), install_component_plugin(registry, plugin))
        self.assertEqual(("sensor", "missing"), install_component_plugin(registry, plugin))
        self.assertEqual("com.example.telemetry", registry.require("missing").plugin_id)
        self.assertEqual(("sensor", "missing"), uninstall_component_plugin(registry, plugin))
        self.assertIsNone(registry.definition("sensor"))


class ComponentSdkCanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_canvas_plugin_restores_placeholder_factories_and_emits_lifecycle(self) -> None:
        renderer_calls: list[str] = []

        def renderer(_painter, item, _rect, _option, _widget) -> None:
            renderer_calls.append(item.element_id)

        plugin = component_plugin(
            "com.example.telemetry",
            "Telemetry",
            "1.0",
            (
                definition(
                    "telemetry_sensor",
                    defaults={"value": 0.0},
                    schema={"properties": {"value": {"type": "number"}}},
                    renderer_factory=renderer,
                    inspector_factory=lambda _canvas, item: QLabel(item.element_id),
                    capabilities={"geometry", "appearance", "ports"},
                ),
            ),
        )
        canvas = MonkezCanva()
        lifecycle: list[tuple[str, bool]] = []
        canvas.componentPluginChanged.connect(
            lambda plugin_id, enabled: lifecycle.append((plugin_id, enabled))
        )
        canvas.setDocumentModel(
            CanvasDocument.from_dict(
                {
                    "format": "monkez-canva",
                    "version": 1,
                    "scene": {},
                    "elements": [
                        {
                            "id": "temperature",
                            "type": "telemetry_sensor",
                            "value": 42.5,
                        }
                    ],
                    "connectors": [],
                }
            )
        )
        original_item = canvas.element("temperature")
        self.assertEqual("__missing__", original_item.definition.plugin_id)

        self.assertEqual(("telemetry_sensor",), canvas.registerElementPlugin(plugin))
        self.assertIs(original_item, canvas.element("temperature"))
        self.assertIs(renderer, canvas.element("temperature").definition.renderer_factory)
        self.assertEqual(42.5, canvas.element("temperature").custom_properties["value"])
        self.assertEqual(
            [("com.example.telemetry", True)], lifecycle
        )

        canvas.setEditMode(True)
        canvas.selectElement("temperature")
        self.app.processEvents()
        self.assertFalse(canvas._toolbox._extension_inspector_host.isHidden())
        self.assertEqual(
            ("telemetry_sensor",),
            canvas.unregisterElementPlugin("com.example.telemetry"),
        )
        self.assertEqual(
            [("com.example.telemetry", True), ("com.example.telemetry", False)],
            lifecycle,
        )
        self.assertEqual("telemetry_sensor", canvas.documentModel().element("temperature").type)
        canvas.close()
        canvas.deleteLater()

    def test_canvas_rejects_invalid_existing_plugin_record_before_registry_change(self) -> None:
        canvas = MonkezCanva()
        canvas.setDocumentModel(
            CanvasDocument.from_dict(
                {
                    "format": "monkez-canva",
                    "version": 1,
                    "scene": {},
                    "elements": [
                        {"id": "sensor", "type": "strict_sensor", "value": "bad"}
                    ],
                    "connectors": [],
                }
            )
        )
        plugin = component_plugin(
            "com.example.telemetry",
            "Telemetry",
            "1.0",
            (
                definition(
                    "strict_sensor",
                    schema={"properties": {"value": {"type": "number"}}},
                ),
            ),
        )

        with self.assertRaisesRegex(TypeError, "must be number"):
            canvas.registerElementPlugin(plugin)
        self.assertEqual("__missing__", canvas.elementRegistry().require("strict_sensor").plugin_id)
        canvas.close()
        canvas.deleteLater()

    def test_repository_example_plugin_renders_and_inspector_auto_applies(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "canva_component_plugin.py"
        spec = importlib.util.spec_from_file_location("monkez_canva_sdk_example", source)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        canvas = MonkezCanva()
        diagnostics: list[str] = []
        canvas.diagnosticMessage.connect(diagnostics.append)
        canvas.registerElementPlugin(module.PLUGIN)
        element_id = canvas.addElement(
            "telemetry_sensor", element_id="temperature", value=36.8
        )
        image = QImage(240, 150, QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        canvas.element(element_id).paint(painter, None)
        painter.end()
        self.assertFalse(any("failed" in message.lower() for message in diagnostics))

        canvas.setEditMode(True)
        canvas.selectElement(element_id)
        self.app.processEvents()
        editor = canvas._toolbox._extension_inspector_host.findChild(QDoubleSpinBox)
        self.assertIsNotNone(editor)
        canvas.undoStack().clear()
        editor.setValue(41.25)
        self.app.processEvents()
        self.assertEqual(41.25, canvas.documentModel().element(element_id).properties["value"])
        self.assertEqual(1, canvas.undoStack().count())
        self.assertTrue(canvas.undo())
        self.assertEqual(36.8, canvas.documentModel().element(element_id).properties["value"])
        canvas.close()
        canvas.deleteLater()


if __name__ == "__main__":
    unittest.main()
