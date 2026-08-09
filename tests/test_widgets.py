from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSize, QSizeF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PyQt6 import uic

from monkez_pyqt6 import monkez_widgets
from monkez_pyqt6.monkez_canva import CanvasDocument, ElementDefinition
from monkez_pyqt6.monkez_widgets._painting import aligned_corner_radius, aligned_stroke_rect
from monkez_pyqt6.monkez_widgets import (
    MonkezButton,
    MonkezCanva,
    MonkezBreadcrumb,
    MonkezCalendarWidget,
    MonkezArcGauge,
    MonkezComboBox,
    MonkezDial,
    MonkezGroupBox,
    MonkezImage,
    MonkezLinearGauge,
    MonkezLCDNumber,
    MonkezLoadingIndicator,
    MonkezLoadingOverlay,
    MonkezPagination,
    MonkezRangeSlider,
    MonkezRadialGauge,
    MonkezRadioButton,
    MonkezScrollArea,
    MonkezSegmentedControl,
    MonkezStatusBadge,
    MonkezTable,
    MonkezUSBCamera,
    MonkezToast,
    MonkezFilePicker,
)


class WidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_antialiased_stroke_geometry_stays_inside_bounds(self) -> None:
        bounds = QRectF(0, 0, 20, 12)

        one_pixel = aligned_stroke_rect(bounds, 1)
        two_pixels = aligned_stroke_rect(bounds, 2)

        self.assertEqual(QRectF(0.5, 0.5, 19, 11), one_pixel)
        self.assertEqual(QRectF(1, 1, 18, 10), two_pixels)
        self.assertEqual(5.5, aligned_corner_radius(bounds, 6, 1))
        self.assertEqual(5.0, aligned_corner_radius(bounds, 99, 2))

    def test_all_widgets_construct(self) -> None:
        self.assertEqual(len(monkez_widgets.__all__), len(set(monkez_widgets.__all__)))
        for name in monkez_widgets.__all__:
            widget = getattr(monkez_widgets, name)()
            self.assertEqual(type(widget).__name__, name)
            widget.deleteLater()

    def test_themed_widgets_expose_numeric_theme_property(self) -> None:
        excluded = {"MonkezCanva", "MonkezImage", "MonkezUSBCamera"}
        for name in monkez_widgets.__all__:
            if name in excluded:
                continue
            widget = getattr(monkez_widgets, name)()
            self.assertGreaterEqual(widget.metaObject().indexOfProperty("themeIndex"), 0, name)
            widget.setProperty("themeIndex", 5)
            self.assertEqual(widget.property("themeIndex"), 5, name)
            widget.deleteLater()

    def test_fluent_api_methods_update_supported_widget_properties(self) -> None:
        button = MonkezButton()
        self.assertIs(button.setBackground("#123456"), button)
        self.assertEqual(button.activeColor, QColor("#123456"))
        button.setAccent("#654321").setForeground("#ffffff").setContentPadding(7, 3)
        self.assertEqual(button.activeColor, QColor("#654321"))
        self.assertEqual(button.textColor, QColor("#ffffff"))
        self.assertEqual(button.paddingX, 7)
        self.assertEqual(button.paddingY, 3)
        button.deleteLater()

        text_input = monkez_widgets.MonkezTextInput()
        text_input.setColors(background="#101010", text="#f8fafc", border="#334155")
        self.assertEqual(text_input.backgroundColor, QColor("#101010"))
        self.assertEqual(text_input.textColor, QColor("#f8fafc"))
        self.assertEqual(text_input.borderColor, QColor("#334155"))
        text_input.deleteLater()

        switch = monkez_widgets.MonkezSwitch()
        switch.setTrack("#222222").setThumb("#eeeeee").setAccent("#22c55e")
        self.assertEqual(switch.trackColor, QColor("#222222"))
        self.assertEqual(switch.thumbColor, QColor("#eeeeee"))
        self.assertEqual(switch.checkedColor, QColor("#22c55e"))
        switch.deleteLater()

        slider = monkez_widgets.MonkezSlider()
        slider.setTrack("#dbeafe").setAccent("#2563eb").setThumb((255, 255, 255))
        self.assertEqual(slider.grooveColor, QColor("#dbeafe"))
        self.assertEqual(slider.filledColor, QColor("#2563eb"))
        self.assertEqual(slider.handleColor, QColor(255, 255, 255))
        slider.deleteLater()

        radio = monkez_widgets.MonkezRadioButton()
        self.assertIs(radio.setBackground("#2563eb"), radio)
        self.assertEqual(radio.backgroundColor, QColor("#2563eb"))
        radio.deleteLater()

        group_box = monkez_widgets.MonkezGroupBox()
        self.assertIs(group_box.setContentPadding(15), group_box)
        self.assertEqual(group_box.contentPadding, 15)
        group_box.deleteLater()

    def test_canva_flow_api_and_json_round_trip(self) -> None:
        canvas = MonkezCanva()
        source = canvas.addNode("Input", 0, 0, element_id="source")
        target = canvas.addNode("Output", 240, 0, element_id="target")
        chart = canvas.addChart([10, 35, 22], "line", 480, 0, element_id="chart")
        connector = canvas.connectElements(source, target, connector_id="edge")
        canvas.setElementColor(source, "#ef4444")
        canvas.setElementText(target, "Result")
        canvas.setChartData(chart, [12, 42, 30])

        self.assertEqual("edge", connector)
        self.assertEqual(QColor("#ef4444"), canvas.element(source).color)
        document = canvas.toDocument()
        self.assertEqual("monkez-canva", document["format"])
        self.assertEqual(3, len(document["elements"]))
        self.assertEqual(1, len(document["connectors"]))

        restored = MonkezCanva()
        restored.loadDocument(canvas.toJson())
        self.assertEqual(["source", "target", "chart"], restored.elements())
        self.assertEqual("Result", restored.element("target").text)
        self.assertEqual([12, 42, 30], restored.element("chart").data)
        restored.deleteLater()
        canvas.deleteLater()

    def test_canva_document_model_can_drive_multiple_views(self) -> None:
        document = CanvasDocument.empty(
            {
                "width": 1600,
                "height": 1000,
                "gridVisible": True,
                "snapToGrid": True,
                "gridSize": 20,
                "gridStyle": 0,
            }
        )
        first = MonkezCanva()
        second = MonkezCanva()
        first.setDocumentModel(document)
        second.setDocumentModel(document)
        operations = []
        second.documentOperation.connect(operations.append)

        first.addNode("Shared", element_id="shared")

        self.assertEqual(1, document.revision)
        self.assertEqual(["shared"], second.elements())
        self.assertEqual("element.added", operations[-1]["action"])
        document.update_element("shared", {"text": "Updated outside Qt"})
        self.assertEqual("Updated outside Qt", first.element("shared").text)
        self.assertEqual("Updated outside Qt", second.element("shared").text)
        self.assertEqual(document.to_dict(), first.toDocument())
        self.assertEqual(document.to_dict(), second.toDocument())
        first.deleteLater()
        second.deleteLater()

    def test_canva_document_operations_preserve_item_identity_selection_and_viewport(self) -> None:
        document = CanvasDocument.from_dict(
            {
                "format": "monkez-canva",
                "version": 1,
                "scene": {"width": 1600, "height": 1000},
                "elements": [
                    {"id": "source", "type": "node", "text": "Source", "x": 0, "y": 0},
                    {"id": "target", "type": "node", "text": "Target", "x": 320, "y": 0},
                ],
                "connectors": [
                    {"id": "edge", "source": "source", "target": "target", "route": "bezier"}
                ],
            }
        )
        canvas = MonkezCanva()
        canvas.resize(900, 600)
        canvas.setDocumentModel(document)
        canvas.setEditMode(True)
        canvas.selectElements(["source", "edge"])
        source_item = canvas.element("source")
        connector_item = canvas.connector("edge")
        canvas.view().scale(1.35, 1.35)
        canvas.view().centerOn(QPointF(140, 90))
        transform = canvas.view().transform()

        document.update_element(
            "source", {"text": "Updated", "x": 45, "color": "#ef4444"}
        )

        self.assertIs(source_item, canvas.element("source"))
        self.assertTrue(source_item.isSelected())
        self.assertEqual("Updated", source_item.text)
        self.assertEqual(QColor("#ef4444"), source_item.color)
        self.assertEqual(transform, canvas.view().transform())

        document.rename_element("source", "producer")
        self.assertIs(source_item, canvas.element("producer"))
        self.assertTrue(source_item.isSelected())
        self.assertIs(connector_item, canvas.connector("edge"))
        self.assertEqual("producer", connector_item.source.element_id)

        document.update_connector("edge", {"route": "orthogonal", "color": "#0ea5e9"})
        self.assertIs(connector_item, canvas.connector("edge"))
        self.assertEqual("orthogonal", connector_item.route)
        self.assertEqual(QColor("#0ea5e9"), connector_item.color)
        self.assertEqual(transform, canvas.view().transform())
        canvas.deleteLater()

    def test_canva_command_history_is_minimal_mergeable_and_reversible(self) -> None:
        canvas = MonkezCanva()
        canvas.addNode("Initial", element_id="node")
        node_item = canvas.element("node")
        self.assertEqual(1, canvas.undoStack().count())
        self.assertTrue(canvas._quick_toolbar._undo_button.isEnabled())
        self.assertFalse(canvas._quick_toolbar._redo_button.isEnabled())

        canvas.updateElement("node", text="Typing 1")
        canvas.updateElement("node", text="Typing 2")
        canvas.updateElement("node", text="Typing 3")

        self.assertEqual(2, canvas.undoStack().count())
        command = canvas.undoStack().command(1)
        self.assertEqual(1, len(command.patches))
        self.assertEqual("elements", command.patches[0].collection)
        self.assertTrue(canvas.canUndo())
        self.assertEqual("Update Node", canvas.undoText())
        self.assertTrue(canvas.undo())
        self.assertIs(node_item, canvas.element("node"))
        self.assertEqual("Initial", canvas.element("node").text)
        self.assertTrue(canvas._quick_toolbar._redo_button.isEnabled())
        self.assertTrue(canvas.redo())
        self.assertEqual("Typing 3", canvas.element("node").text)
        canvas.deleteLater()

    def test_canva_delete_command_restores_cascade_records_atomically(self) -> None:
        canvas = MonkezCanva()
        canvas.addNode("Source", element_id="source")
        canvas.addNode("Target", element_id="target")
        canvas.connectElements("source", "target", connector_id="edge")
        canvas.documentModel().add_group(
            {"id": "pipeline", "members": ["source", "target"]}
        )
        canvas.undoStack().clear()

        self.assertTrue(canvas.removeElement("source"))
        self.assertIsNone(canvas.element("source"))
        self.assertIsNone(canvas.connector("edge"))
        self.assertEqual(("target",), canvas.documentModel().group("pipeline").members)
        command = canvas.undoStack().command(0)
        self.assertEqual(
            {("elements", "source"), ("connectors", "edge"), ("groups", "pipeline")},
            {(patch.collection, patch.record_id) for patch in command.patches},
        )

        self.assertTrue(canvas.undo())
        self.assertIsNotNone(canvas.element("source"))
        self.assertIsNotNone(canvas.connector("edge"))
        self.assertEqual(
            ("source", "target"), canvas.documentModel().group("pipeline").members
        )
        self.assertTrue(canvas.redo())
        self.assertIsNone(canvas.element("source"))
        canvas.deleteLater()

    def test_canva_command_macro_and_external_model_history_boundary(self) -> None:
        canvas = MonkezCanva()
        canvas.addNode("A", element_id="a")
        canvas.addNode("B", element_id="b")
        canvas.undoStack().clear()
        canvas.beginCommandMacro("Move pair")
        canvas.updateElement("a", x=40)
        canvas.updateElement("b", x=240)
        canvas.endCommandMacro()

        self.assertEqual(1, canvas.undoStack().count())
        self.assertEqual("Move pair", canvas.undoText())
        self.assertTrue(canvas.undo())
        self.assertEqual(0, canvas.element("a").pos().x())
        self.assertEqual(0, canvas.element("b").pos().x())
        canvas.undoStack().clear()
        canvas.documentModel().update_element("a", {"text": "External"})
        self.assertEqual(0, canvas.undoStack().count())
        self.assertEqual("External", canvas.element("a").text)
        canvas.deleteLater()

    def test_canva_graphics_origin_edit_and_multi_delete_are_commands(self) -> None:
        canvas = MonkezCanva()
        canvas.addText("Before", element_id="one")
        canvas.addText("Two", x=200, element_id="two")
        canvas.undoStack().clear()

        canvas.setElementText("one", "After")
        self.assertEqual(1, canvas.undoStack().count())
        self.assertTrue(canvas.undo())
        self.assertEqual("Before", canvas.element("one").text)
        self.assertTrue(canvas.redo())
        self.assertEqual("After", canvas.element("one").text)

        canvas.undoStack().clear()
        canvas.element("one").setPos(40, 20)
        canvas.element("one").setPos(80, 40)
        canvas.element("one").setPos(120, 60)
        self.assertEqual(1, canvas.undoStack().count())
        self.assertTrue(canvas.undo())
        self.assertEqual(QPointF(0, 0), canvas.element("one").pos())

        canvas.setEditMode(True)
        canvas.selectElements(["one", "two"])
        canvas.undoStack().clear()
        canvas.deleteSelected()
        self.assertEqual(1, canvas.undoStack().count())
        self.assertEqual("Delete 2 objects", canvas.undoText())
        self.assertEqual([], canvas.elements())
        self.assertTrue(canvas.undo())
        self.assertEqual(["one", "two"], canvas.elements())
        canvas.deleteLater()

    def test_canva_group_and_resource_apis_participate_in_command_history(self) -> None:
        canvas = MonkezCanva()
        canvas.addNode("A", element_id="a")
        canvas.addNode("B", element_id="b")
        canvas.undoStack().clear()

        group_id = canvas.addGroup(["a", "b"], "pair", label="Pair")
        resource_id = canvas.addResource(
            "image", "assets/icon.png", "icon", checksum="abc"
        )
        self.assertEqual("pair", group_id)
        self.assertEqual("icon", resource_id)
        self.assertEqual(("a", "b"), canvas.documentModel().group("pair").members)
        self.assertEqual("abc", canvas.documentModel().resource("icon").properties["checksum"])
        self.assertEqual(2, canvas.undoStack().count())

        canvas.updateGroup("pair", label="Updated pair")
        canvas.updateResource("icon", uri="assets/new.png")
        self.assertEqual("Updated pair", canvas.documentModel().group("pair").properties["label"])
        self.assertEqual("assets/new.png", canvas.documentModel().resource("icon").uri)
        self.assertTrue(canvas.undo())
        self.assertEqual("assets/icon.png", canvas.documentModel().resource("icon").uri)
        self.assertTrue(canvas.undo())
        self.assertEqual("Pair", canvas.documentModel().group("pair").properties["label"])
        self.assertTrue(canvas.removeGroup("pair"))
        self.assertTrue(canvas.undo())
        self.assertIsNotNone(canvas.documentModel().group("pair"))
        canvas.deleteLater()

    def test_canva_rename_commands_preserve_identity_through_undo_redo(self) -> None:
        canvas = MonkezCanva()
        canvas.addNode("A", element_id="a")
        canvas.addNode("B", element_id="b")
        canvas.connectElements("a", "b", connector_id="edge")
        element_item = canvas.element("a")
        connector_item = canvas.connector("edge")
        canvas.undoStack().clear()

        self.assertEqual("source", canvas.renameElement("a", "source"))
        self.assertIs(element_item, canvas.element("source"))
        self.assertEqual("signal", canvas.renameConnector("edge", "signal"))
        self.assertIs(connector_item, canvas.connector("signal"))
        self.assertTrue(canvas.undo())
        self.assertIs(connector_item, canvas.connector("edge"))
        self.assertTrue(canvas.undo())
        self.assertIs(element_item, canvas.element("a"))
        self.assertTrue(canvas.redo())
        self.assertIs(element_item, canvas.element("source"))
        canvas.deleteLater()

    def test_canva_port_resize_and_alignment_edits_are_reversible_commands(self) -> None:
        canvas = MonkezCanva()
        canvas.addNode("A", x=0, y=0, element_id="a")
        canvas.addNode("B", x=240, y=120, element_id="b")
        original_ports = canvas.nodePorts("a")
        canvas.undoStack().clear()

        canvas.setNodePorts(
            "a",
            [
                {"id": "input", "mode": "input", "side": "left"},
                {"id": "signal", "mode": "output", "side": "right"},
            ],
        )
        canvas.updateElement("a", width=260, height=140)
        self.assertEqual(1, canvas.undoStack().count())
        self.assertTrue(canvas.undo())
        self.assertEqual(180, canvas.element("a")._rect.width())
        self.assertEqual(original_ports, canvas.nodePorts("a"))

        canvas.setEditMode(True)
        canvas.selectElements(["a", "b"])
        canvas.undoStack().clear()
        self.assertTrue(canvas.alignSelected("left"))
        self.assertEqual(1, canvas.undoStack().count())
        self.assertTrue(canvas.undo())
        self.assertNotEqual(
            canvas.element("a").sceneBoundingRect().left(),
            canvas.element("b").sceneBoundingRect().left(),
        )
        canvas.deleteLater()

    def test_canva_save_marks_command_stack_clean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canvas = MonkezCanva()
            modified = []
            canvas.documentModifiedChanged.connect(modified.append)
            canvas.addText("Dirty", element_id="dirty")
            self.assertTrue(canvas.isDocumentModified())
            canvas.saveDocument(Path(directory) / "canvas.json")
            self.assertFalse(canvas.isDocumentModified())
            self.assertIn(False, modified)
            canvas.updateElement("dirty", text="Dirty again")
            self.assertTrue(canvas.isDocumentModified())
            self.assertTrue(canvas.undo())
            self.assertFalse(canvas.isDocumentModified())
            canvas.deleteLater()

    def test_canva_registry_adds_custom_items_and_missing_placeholders(self) -> None:
        canvas = MonkezCanva()
        canvas.registerElementDefinition(
            ElementDefinition("sensor", "Sensor", "Industrial", 150, 86)
        )
        sensor_id = canvas.addElement("sensor", 10, 20, element_id="pressure")

        self.assertEqual("pressure", sensor_id)
        self.assertEqual("sensor", canvas.element(sensor_id).kind)
        self.assertEqual(150, canvas.element(sensor_id)._rect.width())

        unknown = CanvasDocument.from_dict(
            {
                "format": "monkez-canva",
                "version": 1,
                "scene": {},
                "elements": [{"id": "legacy", "type": "vendor-widget", "text": "Legacy"}],
                "connectors": [],
            }
        )
        canvas.setDocumentModel(unknown)
        self.assertEqual("vendor-widget", canvas.element("legacy").kind)
        self.assertEqual("Missing components", canvas.elementRegistry().require("vendor-widget").category)
        canvas.registerElementDefinition(
            ElementDefinition(
                "vendor-widget", "Vendor widget", "Vendor", 160, 80,
                plugin_id="vendor-pack",
            )
        )
        self.assertEqual("vendor-pack", canvas.element("legacy").definition.plugin_id)
        canvas.deleteLater()

    def test_canva_registry_migrates_records_and_dispatches_extension_factories(self) -> None:
        paint_calls = []
        inspector_calls = []

        def migrate(record):
            record["value"] = record.pop("reading")
            return record

        def render(painter, item, rect, _option, _widget):
            paint_calls.append(item.custom_properties["value"])
            painter.drawRoundedRect(rect, 8, 8)

        def inspect(_canvas, item):
            inspector_calls.append(item.element_id)
            return QLabel(f"Value: {item.custom_properties['value']}")

        canvas = MonkezCanva()
        canvas.registerElementDefinition(
            ElementDefinition(
                "sensor", "Sensor", "Industrial", 150, 86,
                schema={
                    "required": ["value"],
                    "properties": {"value": {"type": "number"}},
                },
                schema_version=2,
                migrations={1: migrate},
                renderer_factory=render,
                inspector_factory=inspect,
                plugin_id="industrial-pack",
            )
        )
        document = CanvasDocument.from_dict(
            {
                "format": "monkez-canva", "version": 1, "scene": {},
                "elements": [{"id": "s1", "type": "sensor", "reading": 12}],
                "connectors": [],
            }
        )
        canvas.setDocumentModel(document)
        self.assertEqual(2, document.element("s1").properties["componentVersion"])
        self.assertEqual(12, canvas.element("s1").custom_properties["value"])
        image = QImage(200, 120, QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        canvas.element("s1").paint(painter, None)
        painter.end()
        self.assertEqual([12], paint_calls)

        canvas.setEditMode(True)
        canvas.selectElement("s1")
        self.app.processEvents()
        self.assertEqual(["s1"], inspector_calls)
        self.assertLessEqual(canvas._toolbox.height(), 760)
        self.assertFalse(canvas._toolbox._extension_inspector_host.isHidden())
        self.assertEqual(("sensor",), canvas.unregisterElementPlugin("industrial-pack"))
        self.assertIsNone(canvas.elementRegistry().definition("sensor"))
        self.assertEqual("sensor", document.element("s1").type)
        canvas.deleteLater()

    def test_canva_plugin_factory_failures_degrade_without_escaping_qt(self) -> None:
        diagnostics = []

        def broken_renderer(*_args):
            raise RuntimeError("paint exploded")

        canvas = MonkezCanva()
        canvas.diagnosticMessage.connect(diagnostics.append)
        canvas.registerElementDefinition(
            ElementDefinition(
                "broken", "Broken", "Testing", 120, 80,
                renderer_factory=broken_renderer,
                inspector_factory=lambda *_args: object(),
                plugin_id="broken-pack",
            )
        )
        canvas.addElement("broken", element_id="broken-1")
        image = QImage(160, 100, QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        canvas.element("broken-1").paint(painter, None)
        painter.end()
        canvas.setEditMode(True)
        canvas.selectElement("broken-1")
        self.app.processEvents()

        self.assertTrue(any("Renderer 'broken' failed" in message for message in diagnostics))
        self.assertTrue(any("must return QWidget" in message for message in diagnostics))
        canvas.deleteLater()

    def test_canva_advanced_connectors_lines_and_object_specific_inspector(self) -> None:
        canvas = MonkezCanva()
        source = canvas.addNode("Pump", 0, 0, element_id="pump")
        target = canvas.addNode("Tank", 360, 160, element_id="tank")
        spare = canvas.addNode("Valve", 650, 40, element_id="valve")
        line_id = canvas.addLine(
            0, 280, element_id="pipe-line", lineStyle="dash",
            lineWidth=4, arrowStart=True, arrowEnd=True, animated=True,
            animationEffect="pulse", flowDirection="reverse", flowSpacing=7,
            effectIntensity=1.4,
        )
        polyline_id = canvas.addPolyline(
            [[0, 80], [100, 10], [220, 90]], 300, 300,
            element_id="pipe-polyline", arrowEnd=True,
        )
        canvas.setEditMode(True)
        canvas.selectElements([source, target])
        connector_id = canvas.connectSelected(
            connector_id="water-flow", route="orthogonal", lineStyle="dashdot",
            lineWidth=5, arrowStart=True, arrowEnd=True, animated=True,
            animationEffect="glow", flowSpeed=2.5, flowColor="#06b6d4",
            flowDirection="reverse", flowSpacing=8, effectIntensity=1.6,
        )

        connector = canvas.connector(connector_id)
        self.assertEqual("water-flow", connector_id)
        self.assertEqual([connector_id], canvas.selectedObjectIds())
        self.assertEqual("orthogonal", connector.route)
        self.assertTrue(connector.animated)
        self.assertTrue(connector._timer.isActive())
        self.assertEqual(QColor("#06b6d4"), connector.flow_color)
        self.assertEqual("glow", connector.animation_effect)
        self.assertEqual(-1, connector.flow_direction)
        self.assertTrue(canvas.element(line_id).arrow_start)
        self.assertTrue(canvas.element(line_id)._line_timer.isActive())
        self.assertEqual("pulse", canvas.element(line_id).animation_effect)
        self.assertEqual("line", canvas.element(polyline_id).kind)
        self.assertEqual(3, len(canvas.element(polyline_id).points))

        canvas.reconnectConnector(connector_id, source, spare)
        self.assertEqual(spare, connector.target.element_id)
        canvas.selectElement(connector_id)
        toolbox = canvas._toolbox
        toolbox._sync_inspector(connector_id)
        self.assertFalse(toolbox._stroke_group.isHidden())
        self.assertTrue(toolbox._geometry_group.isHidden())
        self.assertEqual(source, toolbox._source_combo.currentData())
        self.assertEqual(spare, toolbox._target_combo.currentData())
        self.assertEqual("out", toolbox._source_port_combo.currentData())
        self.assertEqual("in", toolbox._target_port_combo.currentData())
        self.assertEqual("Glow", toolbox._effect_combo.currentText())
        self.assertEqual("Reverse", toolbox._flow_direction_combo.currentText())

        canvas.selectElement(source)
        toolbox._sync_inspector(source)
        self.assertFalse(toolbox._ports_group.isHidden())
        self.assertEqual(2, toolbox._ports_list.count())
        self.assertNotIn("Apply changes", [button.text() for button in toolbox.findChildren(QPushButton)])
        toolbox._text_edit.setText("Pump updated")
        toolbox._text_edit.textEdited.emit("Pump updated")
        QTest.qWait(240)
        self.assertEqual("Pump updated", canvas.element(source).text)
        toolbox._port_id_edit.setText("telemetry")
        toolbox._port_label_edit.setText("Telemetry")
        toolbox._port_mode_combo.setCurrentText("Output")
        toolbox._port_side_combo.setCurrentText("Bottom")
        toolbox._upsert_port()
        self.app.processEvents()
        self.assertIn("telemetry", [port["id"] for port in canvas.nodePorts(source)])

        restored = MonkezCanva()
        restored.loadDocument(canvas.toDocument())
        restored_connector = restored.connector(connector_id)
        self.assertEqual("orthogonal", restored_connector.route)
        self.assertEqual("dashdot", restored_connector.line_style)
        self.assertTrue(restored_connector.arrow_start)
        self.assertTrue(restored_connector.arrow_end)
        self.assertTrue(restored_connector.animated)
        self.assertEqual("glow", restored_connector.animation_effect)
        self.assertEqual(-1, restored_connector.flow_direction)
        self.assertEqual("pulse", restored.element(line_id).animation_effect)
        self.assertEqual(spare, restored_connector.target.element_id)
        self.assertEqual([line_id, polyline_id], [value for value in restored.elements() if "pipe" in value])

        restored.clear()
        restored.deleteLater()
        canvas.setEditMode(False)
        canvas.clear()
        canvas.deleteLater()

    def test_canva_packet_messages_and_splitter_branch_propagation(self) -> None:
        canvas = MonkezCanva()
        source = canvas.addNode("Source", 0, 0, element_id="source")
        splitter = canvas.addSplitter(220, 0, output_count=2, element_id="splitter")
        target_a = canvas.addNode("A", 440, -100, element_id="target-a")
        target_b = canvas.addNode("B", 440, 100, element_id="target-b")
        incoming = canvas.connectElements(
            source, splitter, connector_id="incoming", sourcePort="out", targetPort="in",
            animationEffect="packet", packetLoop=False, packetDuration=0.1, packetInterval=0.05,
        )
        canvas.connectElements(
            splitter, target_a, connector_id="branch-a", sourcePort="out-1", targetPort="in",
        )
        canvas.connectElements(
            splitter, target_b, connector_id="branch-b", sourcePort="out-2", targetPort="in",
        )
        sent: list[tuple[str, str]] = []
        arrived: list[tuple[str, str]] = []
        canvas.messageSent.connect(lambda edge, message: sent.append((edge, message)))
        canvas.messageArrived.connect(lambda edge, message: arrived.append((edge, message)))

        message_id = canvas.send_a_message(
            incoming, travel_time=0.1, speed=2.0, wait_to_end=True, message_id="packet-1",
        )

        self.assertEqual("packet-1", message_id)
        self.assertEqual({"incoming", "branch-a", "branch-b"}, {edge for edge, _message in sent})
        self.assertEqual(1, len(arrived))
        self.assertEqual(message_id, arrived[0][1])
        self.assertEqual(3, len(canvas.nodePorts(splitter)))
        self.assertEqual("input", canvas.nodePorts(splitter)[0]["mode"])
        self.assertFalse(canvas._message_payloads)
        canvas.updateConnector(incoming, packetLoop=True)
        self.assertTrue(canvas.connector(incoming)._timer.isActive())
        document = canvas.toDocument()
        splitter_data = next(item for item in document["elements"] if item["id"] == splitter)
        incoming_data = next(item for item in document["connectors"] if item["id"] == incoming)
        self.assertEqual("splitter", splitter_data["type"])
        self.assertEqual("packet", incoming_data["animationEffect"])
        self.assertTrue(incoming_data["packetLoop"])

        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            icon_path = project / "packet.png"
            icon = QImage(16, 16, QImage.Format.Format_ARGB32)
            icon.fill(QColor("#2563eb"))
            icon.save(str(icon_path))
            canvas.updateConnector(incoming, packetIcon=str(icon_path))
            canvas.setProjectDirectory(project)
            canvas.setPersistenceKey("packet-network")
            saved = canvas.savePersistent()
            persisted = json.loads(saved.read_text(encoding="utf-8"))
            saved_edge = next(item for item in persisted["connectors"] if item["id"] == incoming)
            self.assertFalse(Path(saved_edge["packetIcon"]).is_absolute())
            self.assertTrue((saved.parent / saved_edge["packetIcon"]).is_file())

        canvas.clear()
        canvas.deleteLater()

    def test_canva_node_ports_drag_connection_and_click_signals(self) -> None:
        window = QDialog()
        layout = QVBoxLayout(window)
        canvas = MonkezCanva()
        layout.addWidget(canvas)
        source = canvas.addNode(
            "Source", -260, 0, element_id="source-with-ports",
            ports=[
                {"id": "control", "mode": "input", "side": "left", "label": "Control"},
                {"id": "voltage", "mode": "output", "side": "right", "label": "Voltage"},
                {"id": "service", "mode": "free", "side": "bottom", "label": "Service"},
            ],
        )
        target = canvas.addNode(
            "Target", 180, 0, element_id="target-with-ports",
            ports=[
                {"id": "supply", "mode": "input", "side": "left", "label": "Supply"},
                {"id": "status", "mode": "output", "side": "right", "label": "Status"},
            ],
        )
        window.resize(900, 500)
        window.show()
        canvas.setEditMode(True)
        self.app.processEvents()

        self.assertEqual(3, len(canvas.nodePorts(source)))
        source_item = canvas.element(source)
        output_port = source_item.port("voltage")
        output_center = source_item.portLocalPosition("voltage")
        output_apex = source_item._port_marker_path(output_port, output_center).elementAt(1)
        self.assertGreater(output_apex.x, output_center.x())
        view = canvas.view()
        start = view.mapFromScene(canvas.element(source).portScenePosition("voltage"))
        end = view.mapFromScene(canvas.element(target).portScenePosition("supply"))
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(view.viewport(), end, delay=20)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
        self.app.processEvents()

        self.assertEqual(1, len(canvas.connectors()))
        connector = canvas.connector(canvas.connectors()[0])
        self.assertEqual("voltage", connector.source_port)
        self.assertEqual("supply", connector.target_port)
        self.assertEqual(source, connector.source.element_id)
        self.assertEqual(target, connector.target.element_id)

        element_clicks = []
        connector_clicks = []
        object_clicks = []
        canvas.elementClicked.connect(element_clicks.append)
        canvas.connectorClicked.connect(connector_clicks.append)
        canvas.objectClicked.connect(object_clicks.append)
        midpoint = view.mapFromScene(connector._path.pointAtPercent(0.5))
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=midpoint)
        self.app.processEvents()
        self.assertEqual([], element_clicks)
        self.assertEqual([connector.connector_id], connector_clicks)
        self.assertEqual([connector.connector_id], object_clicks)
        canvas.highlightObject(connector.connector_id)
        self.assertTrue(connector._highlight.isValid())

        reversed_id = canvas.connectPorts(source, "control", target, "status")
        reversed_connector = canvas.connector(reversed_id)
        self.assertEqual(target, reversed_connector.source.element_id)
        self.assertEqual("status", reversed_connector.source_port)
        self.assertEqual(source, reversed_connector.target.element_id)
        self.assertEqual("control", reversed_connector.target_port)
        with self.assertRaises(ValueError):
            canvas.connectPorts(source, "control", target, "supply")

        legacy_arrow = canvas.addElement("arrow", element_id="legacy-arrow")
        legacy_polyline = canvas.addElement(
            "polyline", element_id="legacy-polyline", points=[[0, 0], [40, 30], [100, 0]],
        )
        self.assertEqual("line", canvas.element(legacy_arrow).kind)
        self.assertTrue(canvas.element(legacy_arrow).arrow_end)
        self.assertEqual("line", canvas.element(legacy_polyline).kind)

        restored = MonkezCanva()
        restored.loadDocument(canvas.toDocument())
        restored_connector = restored.connector(connector.connector_id)
        self.assertEqual("voltage", restored_connector.source_port)
        self.assertEqual("supply", restored_connector.target_port)
        self.assertEqual(3, len(restored.nodePorts(source)))

        restored.clear()
        restored.deleteLater()
        canvas.setEditMode(False)
        canvas.clear()
        window.close()
        window.deleteLater()

    def test_canva_edit_mode_controls_item_interaction(self) -> None:
        canvas = MonkezCanva()
        element_id = canvas.addElement("rectangle", 10, 10)
        item = canvas.element(element_id)
        self.assertFalse(item.flags() & item.GraphicsItemFlag.ItemIsMovable)
        canvas.setEditMode(True)
        self.assertTrue(item.flags() & item.GraphicsItemFlag.ItemIsMovable)
        canvas.setEditMode(False)
        self.assertFalse(item.flags() & item.GraphicsItemFlag.ItemIsMovable)
        canvas.deleteLater()

    def test_canva_quick_toolbar_multiselect_alignment_and_right_pan(self) -> None:
        window = QDialog()
        layout = QVBoxLayout(window)
        canvas = MonkezCanva()
        layout.addWidget(canvas)
        first = canvas.addElement("rectangle", 0, 0, 100, 60, element_id="first")
        second = canvas.addElement("rectangle", 220, 100, 160, 80, element_id="second")
        third = canvas.addElement("rectangle", 480, 220, 120, 90, element_id="third")
        window.resize(900, 600)
        window.show()
        view_geometry_before = canvas.view().geometry()
        canvas.setEditMode(True)
        self.app.processEvents()

        self.assertFalse(canvas._quick_toolbar.isHidden())
        self.assertIs(canvas, canvas._quick_toolbar.parent())
        self.assertEqual(view_geometry_before, canvas.view().geometry())
        self.assertGreater(canvas._quick_toolbar.y(), 0)
        toolbar_position = canvas._quick_toolbar.pos()
        icon_buttons = canvas._quick_toolbar.findChildren(QToolButton)
        self.assertTrue(icon_buttons)
        self.assertTrue(all(not button.icon().isNull() for button in icon_buttons))
        self.assertEqual([first, second, third], canvas.selectElements([first, second, third]))
        self.assertEqual([first, second, third], canvas.selectedElementIds())
        self.assertTrue(all(button.isEnabled() for button in canvas._quick_toolbar._align_buttons))
        self.assertEqual("3 selected", canvas._toolbox._pane_header._selection_badge.text())
        self.assertFalse(canvas._toolbox._multi_select_group.isHidden())
        self.assertEqual(8, len(canvas._toolbox._arrange_buttons))
        self.assertTrue(all(not button.icon().isNull() for button in canvas._toolbox._arrange_buttons))

        canvas.element(first).setPos(0, 0)
        canvas.element(second).setPos(140, 90)
        canvas.element(third).setPos(520, 210)
        self.assertTrue(canvas.distributeSelected("horizontal"))
        horizontal_centers = [
            canvas.element(element_id).sceneBoundingRect().center().x()
            for element_id in (first, second, third)
        ]
        self.assertAlmostEqual(
            horizontal_centers[1] - horizontal_centers[0],
            horizontal_centers[2] - horizontal_centers[1],
        )

        self.assertTrue(canvas.alignSelected("left"))
        left_edges = [canvas.element(element_id).sceneBoundingRect().left() for element_id in (first, second, third)]
        self.assertAlmostEqual(left_edges[0], left_edges[1])
        self.assertAlmostEqual(left_edges[1], left_edges[2])

        canvas.selectElements([first, second, third])
        self.assertTrue(canvas.alignSelected("center"))
        centers = [canvas.element(element_id).sceneBoundingRect().center() for element_id in (first, second, third)]
        self.assertAlmostEqual(centers[0].x(), centers[1].x())
        self.assertAlmostEqual(centers[1].x(), centers[2].x())
        self.assertAlmostEqual(centers[0].y(), centers[1].y())
        self.assertAlmostEqual(centers[1].y(), centers[2].y())

        view = canvas.view()
        start = QPoint(view.viewport().width() // 2, view.viewport().height() // 2)
        before = view.horizontalScrollBar().value()
        QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=start)
        QTest.mouseMove(view.viewport(), start + QPoint(70, 0), delay=10)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=start + QPoint(70, 0))
        self.assertNotEqual(before, view.horizontalScrollBar().value())
        self.assertEqual(toolbar_position, canvas._quick_toolbar.pos())

        canvas.setEditMode(False)
        self.assertTrue(canvas._quick_toolbar.isHidden())
        window.close()
        window.deleteLater()

    def test_canva_editor_chord_toggles_edit_mode(self) -> None:
        window = QDialog()
        layout = QVBoxLayout(window)
        canvas = MonkezCanva()
        layout.addWidget(canvas)
        window.show()
        canvas.setFocus()
        self.app.processEvents()

        QTest.keyClick(canvas, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(canvas, Qt.Key.Key_E)
        self.app.processEvents()
        self.assertTrue(canvas.editMode)

        canvas.setEditMode(False)
        QTest.keyClick(canvas, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(canvas, Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertTrue(canvas.editMode)

        canvas.setEditMode(False)
        window.close()
        window.deleteLater()

    def test_canva_fit_waits_for_real_viewport_and_keeps_content_readable(self) -> None:
        window = QDialog()
        layout = QVBoxLayout(window)
        canvas = MonkezCanva()
        layout.addWidget(canvas)
        canvas.addNode("Input", -360, -50)
        canvas.addNode("Output", 450, -50)

        canvas.fitContent()
        self.assertTrue(canvas._fit_pending)
        window.resize(1180, 680)
        window.show()
        self.app.processEvents()
        self.app.processEvents()

        zoom = canvas.view().transform().m11()
        self.assertFalse(canvas._fit_pending)
        self.assertGreaterEqual(zoom, 0.2)
        self.assertGreater(zoom, 0.5)
        window.close()
        window.deleteLater()

    def test_canva_media_ids_inspector_fields_and_layers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_path = root / "photo.png"
            pixmap = QPixmap(80, 50)
            pixmap.fill(QColor("#ef4444"))
            self.assertTrue(pixmap.save(str(image_path)))
            gif_path = root / "spinner.gif"
            gif_path.write_bytes(bytes.fromhex(
                "47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b"
            ))

            canvas = MonkezCanva()
            image_id = canvas.addMedia(image_path, 10, 20, element_id="hero")
            animation_id = canvas.addMedia(gif_path, 320, 20, element_id="spinner")
            canvas.updateElement(
                image_id, x=42, y=24, width=320, height=210,
                rotation=15, opacity=0.7, z=4, text="Hero image",
            )
            renamed = canvas.renameElement(image_id, "hero-image")

            self.assertEqual("hero-image", renamed)
            self.assertIsNone(canvas.element("hero"))
            image = canvas.element(renamed)
            self.assertEqual("image", image.kind)
            self.assertFalse(image._pixmap.isNull())
            self.assertEqual(320, image._rect.width())
            self.assertEqual(15, image.rotation())
            self.assertAlmostEqual(0.7, image.opacity())
            self.assertEqual("animated_image", canvas.element(animation_id).kind)
            self.assertEqual(str(gif_path.resolve()), canvas.element(animation_id).source)

            canvas.setEditMode(True)
            toolbox = canvas._toolbox
            self.assertIsNotNone(toolbox)
            self.assertEqual(5, toolbox.findChild(QTabWidget).count())
            self.assertTrue(toolbox.windowFlags() & Qt.WindowType.FramelessWindowHint)
            self.assertNotIn("EDIT", [label.text() for label in toolbox.findChildren(QLabel)])
            toolbox.refreshLayers()
            self.assertEqual(2, toolbox._layers.count())
            canvas.setEditMode(False)
            canvas.clear()
            self.app.processEvents()
            canvas.deleteLater()

    def test_canva_session_persistent_autosave_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            persistent_path = project / "workspace.json"
            image_path = root / "source.png"
            pixmap = QPixmap(32, 24)
            pixmap.fill(QColor("#22c55e"))
            self.assertTrue(pixmap.save(str(image_path)))

            canvas = MonkezCanva()
            canvas.setProjectDirectory(project)
            canvas.setPersistenceKey("portable-test")
            self.assertEqual(project / ".monkez_canva" / "portable-test.json", canvas.persistentPath())
            canvas.persistentPath = lambda: persistent_path
            canvas.setPersistenceKey("test-workspace")
            canvas.setAutoSaveDelay(100)
            image_id = canvas.addMedia(image_path, element_id="saved-image")
            canvas.setBackgroundImage(image_path)
            canvas.setBackgroundImageMode("fill")
            canvas.setGridStyle("dots")
            canvas.saveSession()
            canvas.setElementText(image_id, "Changed")
            self.assertTrue(canvas.restoreSession())
            self.assertEqual("source.png", canvas.element(image_id).text)

            saved_path = canvas.savePersistent()
            self.assertEqual(persistent_path, saved_path)
            payload = json.loads(persistent_path.read_text(encoding="utf-8"))
            self.assertFalse(Path(payload["elements"][0]["source"]).is_absolute())
            copied_media = persistent_path.parent / payload["elements"][0]["source"]
            self.assertTrue(copied_media.is_file())
            self.assertNotEqual(image_path, copied_media)
            self.assertFalse(Path(payload["scene"]["backgroundImage"]).is_absolute())

            relocated = root / "relocated-project"
            shutil.copytree(project, relocated)
            relocated_path = relocated / "workspace.json"

            restored = MonkezCanva()
            restored.persistentPath = lambda: relocated_path
            self.assertTrue(restored.loadPersistent())
            self.assertEqual(["saved-image"], restored.elements())
            self.assertFalse(restored.element("saved-image")._pixmap.isNull())
            self.assertTrue(restored.element("saved-image").source.startswith(str(relocated)))
            self.assertEqual(1, restored.getGridStyle())
            self.assertEqual(1, restored.getBackgroundImageMode())
            self.assertFalse(restored._background_pixmap.isNull())

            auto_project = root / "auto-project"
            auto_project.mkdir()
            auto_source = MonkezCanva()
            auto_source.setProjectDirectory(auto_project)
            auto_source.setPersistenceKey("auto-workspace")
            auto_source.addNode("Portable", element_id="auto-node")
            auto_source.savePersistent()
            auto_restored = MonkezCanva()
            loaded_paths = []
            auto_restored.persistentLoaded.connect(loaded_paths.append)
            auto_restored.setProjectDirectory(auto_project)
            auto_restored.setPersistenceKey("auto-workspace")
            self.app.processEvents()
            self.assertEqual(["auto-node"], auto_restored.elements())
            self.assertTrue(loaded_paths)

            text_id = canvas.addText("First", 0, 0, element_id="history-text")
            QTest.qWait(120)
            canvas.setElementText(text_id, "Second")
            QTest.qWait(120)
            self.assertTrue(canvas.undo())
            self.assertEqual("First", canvas.element(text_id).text)
            self.assertTrue(canvas.redo())
            self.assertEqual("Second", canvas.element(text_id).text)
            restored.deleteLater()
            auto_source.deleteLater()
            auto_restored.deleteLater()
            canvas.deleteLater()

    def test_button_does_not_force_preview_geometry_to_theme_size(self) -> None:
        button = MonkezButton()
        button.setText("X")
        button.resize(24, 24)
        button.setThemeIndex(0)
        button.show()
        self.app.processEvents()

        self.assertLessEqual(button.minimumSizeHint().width(), 24)
        self.assertLessEqual(button.minimumSizeHint().height(), 24)
        self.assertLessEqual(button.minimumWidth(), 24)
        self.assertLessEqual(button.minimumHeight(), 24)
        self.assertEqual(button.paddingX, 4)
        self.assertEqual(button.paddingY, 2)
        self.assertEqual(button.size().width(), 24)
        self.assertEqual(button.size().height(), 24)
        button.close()
        button.deleteLater()

    def test_shadow_effect_is_reused_when_properties_change(self) -> None:
        for widget in (MonkezButton(), monkez_widgets.MonkezTextInput()):
            first_effect = widget.graphicsEffect()
            widget.shadowBlur = widget.shadowBlur + 1
            self.assertIs(widget.graphicsEffect(), first_effect)
            widget.shadowOffsetY = widget.shadowOffsetY + 1
            self.assertIs(widget.graphicsEffect(), first_effect)
            widget.deleteLater()

    def test_widgets_do_not_set_large_hard_minimum_sizes(self) -> None:
        allowed_explicit_minimums = {"MonkezImage", "MonkezUSBCamera"}
        for name in monkez_widgets.__all__:
            widget = getattr(monkez_widgets, name)()
            if widget.metaObject().indexOfProperty("themeIndex") >= 0:
                widget.setProperty("themeIndex", 1)

            minimum = widget.minimumSize()
            self.assertLessEqual(minimum.width(), 48, name)
            self.assertLessEqual(minimum.height(), 36, name)
            if name not in allowed_explicit_minimums:
                self.assertEqual(minimum.width(), 0, name)
                self.assertEqual(minimum.height(), 0, name)
            widget.deleteLater()

    def test_progress_bar_height_does_not_lock_widget_geometry(self) -> None:
        progress = monkez_widgets.MonkezProgressBar()
        progress.barHeight = 4

        self.assertEqual(progress.minimumHeight(), 0)
        self.assertEqual(progress.maximumHeight(), 16777215)
        self.assertNotIn("min-height", progress.styleSheet())
        self.assertNotIn("max-height", progress.styleSheet())
        progress.deleteLater()

    def test_progress_bar_height_does_not_override_text_visibility(self) -> None:
        progress = monkez_widgets.MonkezProgressBar()
        progress.setTextVisible(True)
        progress.barHeight = 8
        progress.barHeight = 28

        self.assertTrue(progress.isTextVisible())
        progress.setTextVisible(False)
        progress.barHeight = 32
        self.assertFalse(progress.isTextVisible())
        progress.deleteLater()

    def test_slider_supports_vertical_orientation(self) -> None:
        slider = monkez_widgets.MonkezSlider()
        slider.setOrientation(Qt.Orientation.Vertical)

        self.assertIn("groove:vertical", slider.styleSheet())
        self.assertIn("handle:vertical", slider.styleSheet())
        self.assertGreater(slider.sizeHint().height(), slider.sizeHint().width())
        self.assertGreater(
            slider.minimumSizeHint().height(),
            slider.minimumSizeHint().width(),
        )
        slider.deleteLater()

    def test_custom_stylesheet_colors_preserve_alpha(self) -> None:
        frame = monkez_widgets.MonkezFrame()
        frame.backgroundColor = QColor(1, 2, 3, 40)
        self.assertIn("rgba(1, 2, 3, 40)", frame.styleSheet())

        progress = monkez_widgets.MonkezProgressBar()
        progress.trackColor = QColor(4, 5, 6, 70)
        self.assertIn("rgba(4, 5, 6, 70)", progress.styleSheet())
        frame.deleteLater()
        progress.deleteLater()

    def test_checkbox_checked_and_indeterminate_states_render(self) -> None:
        checkbox = monkez_widgets.MonkezCheckBox()
        checkbox.setTristate(True)
        checkbox.resize(180, 36)
        checkbox.show()
        for state in (
            Qt.CheckState.Checked,
            Qt.CheckState.PartiallyChecked,
        ):
            checkbox.setCheckState(state)
            self.app.processEvents()
            self.assertFalse(checkbox.grab().isNull())
        checkbox.close()
        checkbox.deleteLater()

    def test_switch_renders_compact_and_right_to_left(self) -> None:
        switch = monkez_widgets.MonkezSwitch()
        switch.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        switch.showText = True
        switch.resize(44, 20)
        switch.setChecked(True)
        switch.show()
        self.app.processEvents()

        self.assertFalse(switch.grab().isNull())
        switch.close()
        switch.deleteLater()

    def test_button_hover_brightens_current_background_color(self) -> None:
        button = MonkezButton()
        active = QColor("#c00000")
        hovered = active.lighter(112)
        button.activeColor = active
        button._hovered = True
        button._update_style()

        self.assertIn(
            f"rgba({hovered.red()}, {hovered.green()}, {hovered.blue()}, {hovered.alpha()})",
            button.styleSheet(),
        )
        button.deleteLater()

    def test_button_press_darkens_current_background_color(self) -> None:
        button = MonkezButton()
        active = QColor("#c00000")
        pressed = active.darker(108)
        button.activeColor = active
        button._pressed = True
        button._update_style()

        self.assertIn(
            f"rgba({pressed.red()}, {pressed.green()}, {pressed.blue()}, {pressed.alpha()})",
            button.styleSheet(),
        )
        button.deleteLater()

    def test_outlined_button_has_hover_and_press_highlight(self) -> None:
        button = MonkezButton()
        button.buttonTypeIndex = 1
        normal_style = button.styleSheet()

        button._hovered = True
        button._update_style()
        hover_style = button.styleSheet()

        button._pressed = True
        button._update_style()
        pressed_style = button.styleSheet()

        self.assertNotEqual(hover_style, normal_style)
        self.assertNotEqual(pressed_style, hover_style)
        self.assertIn("border:", pressed_style)
        self.assertIn("background-color: rgba", pressed_style)
        button.deleteLater()

    def test_outlined_button_uses_active_and_text_designer_colors(self) -> None:
        button = MonkezButton()
        active = QColor(12, 34, 56, 210)
        text = QColor(220, 230, 240, 190)
        hover_text = QColor(250, 200, 40, 180)
        button.buttonTypeIndex = 1
        button.activeColor = active
        button.textColor = text
        button.hoverTextColor = hover_text

        normal_style = button.styleSheet()
        self.assertIn(
            f"border: 1px solid rgba({active.red()}, {active.green()}, "
            f"{active.blue()}, {active.alpha()})",
            normal_style,
        )
        self.assertIn(
            f"color: rgba({text.red()}, {text.green()}, "
            f"{text.blue()}, {text.alpha()})",
            normal_style,
        )

        button._hovered = True
        button._update_style()
        hover_style = button.styleSheet()
        self.assertIn(
            f"color: rgba({hover_text.red()}, {hover_text.green()}, "
            f"{hover_text.blue()}, {hover_text.alpha()})",
            hover_style,
        )
        button.deleteLater()

    def test_text_button_uses_text_color(self) -> None:
        button = MonkezButton()
        text = QColor(18, 52, 86, 170)
        button.buttonTypeIndex = 2
        button.textColor = text

        self.assertIn("color: rgba(18, 52, 86, 170)", button.styleSheet())
        button.deleteLater()

    def test_button_theme_uses_visible_text_for_each_button_type(self) -> None:
        button = MonkezButton()
        theme_names = ("material", "ios", "fluent", "bootstrap", "minimal", "dark")

        for theme in theme_names:
            for button_type in (1, 2):
                with self.subTest(theme=theme, button_type=button_type):
                    button.setThemeName(theme)
                    button.setButtonTypeIndex(button_type)
                    self.assertEqual(button.getTextColor(), button.getActiveColor())
                    self.assertNotEqual(button.getTextColor(), button._surface_color)

            button.setButtonTypeIndex(0)
            self.assertNotEqual(button.getTextColor(), button.getActiveColor())

        button.deleteLater()

    def test_button_type_change_preserves_explicit_text_colors(self) -> None:
        button = MonkezButton()
        text = QColor("#7c3aed")
        hover = QColor("#db2777")
        button.setTextColor(text)
        button.setHoverTextColor(hover)

        button.setButtonTypeIndex(1)
        self.assertEqual(button.getTextColor(), text)
        self.assertEqual(button.getHoverTextColor(), hover)

        button.setButtonTypeIndex(2)
        self.assertEqual(button.getTextColor(), text)
        self.assertEqual(button.getHoverTextColor(), hover)
        button.deleteLater()

    def test_image_reuses_scaled_pixmap_until_source_or_size_changes(self) -> None:
        widget = MonkezImage()
        widget.resize(320, 180)
        pixmap = QPixmap(640, 480)
        pixmap.fill(QColor("#1677d2"))
        widget.set_image(pixmap)
        widget.show()
        self.app.processEvents()

        widget._update_pixmap()
        first_key = widget._scaled_pixmap.cacheKey()
        widget._update_pixmap()
        self.assertEqual(widget._scaled_pixmap.cacheKey(), first_key)

        widget.resize(400, 220)
        self.app.processEvents()
        widget._update_pixmap()
        self.assertNotEqual(widget._scaled_pixmap.cacheKey(), first_key)
        widget.close()

    def test_image_accepts_opencv_numpy_bgr_frame_and_detaches_buffer(self) -> None:
        frame = np.zeros((2, 3, 3), dtype=np.uint8)
        frame[0, 0] = (255, 0, 0)

        widget = MonkezImage(source=frame)
        frame[0, 0] = (0, 255, 0)
        image = widget._pixmap.toImage()

        self.assertEqual(image.size().width(), 3)
        self.assertEqual(image.size().height(), 2)
        self.assertEqual(image.pixelColor(0, 0), QColor(0, 0, 255))
        self.assertEqual(widget.getImageFile(), "")
        widget.deleteLater()

    def test_image_accepts_numpy_grayscale_rgba_and_non_contiguous_frames(self) -> None:
        widget = MonkezImage()
        grayscale = np.array([[0, 127], [200, 255]], dtype=np.uint8)
        widget.setFrame(grayscale)
        self.assertEqual(widget._pixmap.toImage().pixelColor(1, 1), QColor(255, 255, 255))

        bgra = np.array([[[30, 20, 10, 255]]], dtype=np.uint8)
        widget.setFrame(bgra)
        self.assertEqual(widget._pixmap.toImage().pixelColor(0, 0), QColor(10, 20, 30))

        rgba = np.array([[[10, 20, 30, 40]]], dtype=np.uint8)
        widget.setImage(rgba, color_order="rgba")
        rendered_rgba = widget._pixmap.toImage().pixelColor(0, 0)
        self.assertEqual(rendered_rgba.alpha(), 40)
        self.assertLessEqual(abs(rendered_rgba.red() - 10), 3)
        self.assertLessEqual(abs(rendered_rgba.green() - 20), 3)
        self.assertLessEqual(abs(rendered_rgba.blue() - 30), 3)

        rgb = np.zeros((2, 4, 3), dtype=np.uint8)
        rgb[:, :, 0] = 90
        widget.set_image(rgb[:, ::2], color_order="rgb")
        self.assertEqual(widget._pixmap.width(), 2)
        self.assertEqual(widget._pixmap.toImage().pixelColor(0, 0), QColor(90, 0, 0))
        widget.deleteLater()

    def test_image_accepts_pathlib_path_directly(self) -> None:
        widget = MonkezImage()
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "source.png"
            source = QImage(4, 3, QImage.Format.Format_ARGB32)
            source.fill(QColor("#38bdf8"))
            self.assertTrue(source.save(str(path)))

            widget.set_image(path)

            self.assertEqual(widget.getImageFile(), str(path))
            self.assertEqual(widget._pixmap.size(), source.size())
            self.assertEqual(widget._pixmap.toImage().pixelColor(0, 0), QColor("#38bdf8"))
        widget.deleteLater()

    def test_image_stylesheet_targets_the_visible_container(self) -> None:
        widget = MonkezImage()
        custom_style = (
            "background-color: #123456;"
            "border: 4px solid #ef4444;"
            "border-radius: 17px;"
        )

        widget.set_image(QPixmap())
        widget.resize(120, 80)
        widget.setStyleSheet(custom_style)
        widget.show()
        self.app.processEvents()
        rendered = QImage(widget.size(), QImage.Format.Format_ARGB32)
        rendered.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rendered)
        widget.render(painter)
        painter.end()

        self.assertIs(widget.frame, widget)
        self.assertEqual(widget.layout().contentsMargins().left(), 0)
        self.assertEqual(widget.styleSheet(), custom_style)
        self.assertIn("background: transparent", widget.image_label.styleSheet())
        self.assertIn("border: none", widget.image_label.styleSheet())
        self.assertEqual(rendered.pixelColor(60, 1), QColor("#ef4444"))
        self.assertEqual(rendered.pixelColor(60, 20), QColor("#123456"))
        widget.close()

    def test_image_background_property_does_not_replace_custom_stylesheet(self) -> None:
        widget = MonkezImage()
        custom_style = "MonkezImage { border: 3px solid #22c55e; }"
        widget.setStyleSheet(custom_style)

        widget.setBackgroundColor(QColor("#020617"))

        self.assertEqual(widget.styleSheet(), custom_style)
        self.assertEqual(
            widget.palette().color(widget.backgroundRole()),
            QColor("#020617"),
        )
        widget.deleteLater()

    def test_image_background_property_overrides_inherited_parent_background(self) -> None:
        parent = QWidget()
        parent.setStyleSheet("background-color: #ffaa00;")
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = MonkezImage(parent)
        widget.setBackgroundColor(QColor("#0c0c0c"))
        widget.set_image(None)
        layout.addWidget(widget)
        parent.resize(120, 80)
        parent.show()
        self.app.processEvents()

        rendered = QImage(widget.size(), QImage.Format.Format_ARGB32)
        rendered.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rendered)
        widget.render(painter)
        painter.end()

        self.assertEqual(rendered.pixelColor(10, 10), QColor("#0c0c0c"))
        parent.close()
        parent.deleteLater()

    def test_image_scaling_does_not_lock_window_minimum_size(self) -> None:
        widget = MonkezImage()
        pixmap = QPixmap(1200, 800)
        pixmap.fill(QColor("#1976d2"))
        widget.set_image(pixmap)
        widget.resize(720, 480)
        widget.show()
        self.app.processEvents()
        widget._update_pixmap()

        self.assertGreater(widget.image_label.pixmap().width(), 300)
        self.assertLessEqual(widget.minimumSizeHint().width(), 24)
        self.assertLessEqual(widget.minimumSizeHint().height(), 24)
        self.assertLessEqual(widget.image_label.minimumSizeHint().width(), 0)
        self.assertLessEqual(widget.image_label.minimumSizeHint().height(), 0)

        widget.resize(80, 60)
        self.app.processEvents()
        widget._update_pixmap()

        self.assertEqual(widget.size().width(), 80)
        self.assertEqual(widget.size().height(), 60)
        self.assertLessEqual(widget.image_label.pixmap().width(), 80)
        widget.close()
        widget.deleteLater()

    def test_image_outer_layout_owns_geometry_before_pixmap_scaling(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = MonkezImage()
        widget._device_pixel_ratio = lambda: 1.0
        layout.addWidget(widget)

        pixmap = QPixmap(400, 100)
        pixmap.fill(QColor("#1976d2"))
        widget.set_image(pixmap)
        widget.setScaleMode(MonkezImage.ScaleMode.Fit)
        container.resize(300, 180)
        container.show()
        self.app.processEvents()
        widget._update_pixmap()

        self.assertEqual(widget.size(), container.contentsRect().size())
        self.assertEqual(widget.image_label.size(), widget.contentsRect().size())
        self.assertEqual(
            widget.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Ignored,
        )
        self.assertEqual(
            widget.sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Ignored,
        )
        self.assertEqual(widget.minimumSizeHint(), QSize(0, 0))
        self.assertEqual(
            widget.image_label.pixmap().deviceIndependentSize(),
            QSizeF(300, 75),
        )

        widget.setScaleMode(MonkezImage.ScaleMode.Fill)
        container.resize(150, 300)
        self.app.processEvents()
        widget._update_pixmap()

        self.assertEqual(widget.size(), QSize(150, 300))
        self.assertEqual(widget.image_label.size(), QSize(150, 300))
        self.assertEqual(
            widget.image_label.pixmap().deviceIndependentSize(),
            QSizeF(1200, 300),
        )
        container.close()
        container.deleteLater()

    def test_image_uses_physical_pixels_for_high_dpi_scaling(self) -> None:
        widget = MonkezImage()
        widget._device_pixel_ratio = lambda: 2.0
        pixmap = QPixmap(1200, 800)
        pixmap.fill(QColor("#1976d2"))
        widget.set_image(pixmap)
        widget.resize(300, 200)
        widget.show()
        self.app.processEvents()
        widget._update_pixmap()

        rendered = widget.image_label.pixmap()

        self.assertEqual(rendered.devicePixelRatio(), 2.0)
        self.assertGreaterEqual(rendered.width(), 550)
        self.assertLessEqual(rendered.deviceIndependentSize().width(), 300)
        self.assertLessEqual(rendered.deviceIndependentSize().height(), 200)
        widget.close()
        widget.deleteLater()

    def test_image_scale_modes_follow_the_outer_container(self) -> None:
        widget = MonkezImage()
        widget._device_pixel_ratio = lambda: 1.0
        pixmap = QPixmap(400, 200)
        pixmap.fill(QColor("#1976d2"))
        widget.set_image(pixmap)
        widget.resize(100, 100)
        widget.show()
        self.app.processEvents()

        expected_sizes = {
            MonkezImage.ScaleMode.Fit: (100, 50),
            MonkezImage.ScaleMode.Fill: (200, 100),
            MonkezImage.ScaleMode.Stretch: (100, 100),
            MonkezImage.ScaleMode.Original: (400, 200),
        }
        for mode, expected in expected_sizes.items():
            widget.setScaleMode(mode)
            widget._update_pixmap()
            rendered_size = widget.image_label.pixmap().deviceIndependentSize()
            self.assertEqual(
                (round(rendered_size.width()), round(rendered_size.height())),
                expected,
                mode.name,
            )

        widget.setScaleMode(MonkezImage.ScaleMode.Fit)
        widget.resize(160, 90)
        self.app.processEvents()
        widget._update_pixmap()
        resized = widget.image_label.pixmap().deviceIndependentSize()
        self.assertEqual((round(resized.width()), round(resized.height())), (160, 80))
        widget.close()

    def test_image_scale_mode_is_a_designer_integer_property(self) -> None:
        property_index = MonkezImage.staticMetaObject.indexOfProperty("scaleModeIndex")
        scale_property = MonkezImage.staticMetaObject.property(property_index)

        self.assertGreaterEqual(property_index, 0)
        self.assertFalse(scale_property.isEnumType())
        self.assertEqual(scale_property.typeName(), "int")
        widget = MonkezImage()
        self.assertTrue(scale_property.write(widget, 1))
        self.assertEqual(widget.getScaleMode(), MonkezImage.ScaleMode.Fill)
        widget.deleteLater()

    def test_image_scale_mode_loads_from_designer_ui(self) -> None:
        ui_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <widget class="MonkezImage" name="image">
   <property name="scaleModeIndex">
    <number>1</number>
   </property>
  </widget>
 </widget>
 <customwidgets>
  <customwidget>
   <class>MonkezImage</class>
   <extends>QWidget</extends>
   <header>monkez_pyqt6.monkez_widgets</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>
"""

        form = uic.loadUi(io.StringIO(ui_xml))

        self.assertEqual(form.image.getScaleMode(), MonkezImage.ScaleMode.Fill)
        form.deleteLater()

    def test_scroll_area_loads_designer_children_into_its_content_page(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "designer_scroll_test.ui"
        form = uic.loadUi(fixture)

        self.assertIs(form.monkezScrollArea.widget(), form.scrollAreaWidgetContents)
        self.assertIs(form.label.parentWidget(), form.scrollAreaWidgetContents)
        self.assertEqual(form.label.text(), "TextLabel")
        self.assertTrue(form.monkezScrollArea.widgetResizable())
        form.deleteLater()

    def test_scroll_area_preserves_qscrollarea_runtime_defaults(self) -> None:
        native = QScrollArea()
        widget = MonkezScrollArea()

        self.assertIsNone(widget.widget())
        self.assertEqual(widget.widgetResizable(), native.widgetResizable())
        self.assertEqual(widget.frameShape(), native.frameShape())
        self.assertEqual(widget.viewportMargins(), native.viewportMargins())

        widget.deleteLater()
        native.deleteLater()

    def test_scroll_area_automatically_tracks_content_and_shows_scrollbars(self) -> None:
        scroll = MonkezScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        child = QLabel("X", content)
        child.setGeometry(230, 150, 110, 32)
        scroll.setWidget(content)
        scroll.resize(180, 100)
        scroll.show()
        self.app.processEvents()
        scroll.refreshContentSize()
        for _ in range(5):
            self.app.processEvents()

        self.assertTrue(scroll.autoContentSize)
        self.assertGreater(scroll.horizontalScrollBar().maximum(), 0)
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        self.assertTrue(scroll.horizontalScrollBar().isVisible())
        self.assertTrue(scroll.verticalScrollBar().isVisible())

        child.setGeometry(8, 8, 80, 24)
        for _ in range(5):
            self.app.processEvents()

        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
        self.assertEqual(scroll.verticalScrollBar().maximum(), 0)
        self.assertFalse(scroll.horizontalScrollBar().isVisible())
        self.assertFalse(scroll.verticalScrollBar().isVisible())

        child.move(230, 150)
        for _ in range(5):
            self.app.processEvents()
        self.assertGreater(scroll.horizontalScrollBar().maximum(), 0)
        scroll.autoContentSize = False
        for _ in range(5):
            self.app.processEvents()
        self.assertEqual(content.minimumSize(), QSize(0, 0))
        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
        scroll.close()
        scroll.deleteLater()

    def test_scroll_area_uses_layout_minimum_for_dynamic_content(self) -> None:
        scroll = MonkezScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        for index in range(8):
            row = QLabel(f"Row {index + 1}")
            row.setMinimumHeight(28)
            layout.addWidget(row)
        scroll.setWidget(content)
        scroll.resize(220, 100)
        scroll.show()
        for _ in range(5):
            self.app.processEvents()

        self.assertGreater(content.minimumHeight(), scroll.viewport().height())
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        self.assertTrue(scroll.verticalScrollBar().isVisible())
        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
        scroll.close()
        scroll.deleteLater()

    def test_scroll_area_preserves_explicit_content_minimum(self) -> None:
        scroll = MonkezScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setMinimumSize(260, 180)
        child = QLabel("X", content)
        child.setGeometry(8, 8, 24, 24)
        scroll.setWidget(content)
        scroll.resize(180, 100)
        scroll.show()
        for _ in range(5):
            self.app.processEvents()

        self.assertEqual(content.minimumSize(), QSize(260, 180))
        self.assertGreater(scroll.horizontalScrollBar().maximum(), 0)
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        scroll.autoContentSize = False
        self.assertEqual(content.minimumSize(), QSize(260, 180))
        scroll.close()
        scroll.deleteLater()

    def test_image_does_not_lock_parent_window_after_growing(self) -> None:
        window = QWidget()
        layout = QVBoxLayout(window)
        widget = MonkezImage()
        layout.addWidget(widget)
        pixmap = QPixmap(1600, 1000)
        pixmap.fill(QColor("#38bdf8"))
        widget.set_image(pixmap)

        window.resize(900, 600)
        window.show()
        self.app.processEvents()
        widget._update_pixmap()
        large_width = widget.image_label.pixmap().width()

        window.resize(180, 120)
        self.app.processEvents()
        widget._update_pixmap()

        self.assertGreater(large_width, 500)
        self.assertLessEqual(window.layout().totalMinimumSize().width(), 48)
        self.assertLessEqual(window.layout().totalMinimumSize().height(), 48)
        self.assertLessEqual(widget.image_label.pixmap().width(), 180)
        window.close()
        widget.deleteLater()
        window.deleteLater()

    def test_camera_display_fps_and_fast_scaling(self) -> None:
        camera = MonkezUSBCamera()
        self.assertFalse(camera.smoothScaling)
        camera.displayFps = 240
        self.assertEqual(camera.displayFps, 120)
        camera.fps = 0
        self.assertEqual(camera.fps, 1)
        camera.deleteLater()

    def test_group_box_exposes_polished_header_properties(self) -> None:
        group = MonkezGroupBox()
        group.title = "Account settings"
        group.subtitle = "Manage profile and preferences"
        group.subtitleVisible = False
        group.checkable = True
        group.checked = True
        group.themeIndex = 5

        self.assertEqual(group.subtitle, "Manage profile and preferences")
        self.assertFalse(group.subtitleVisible)
        self.assertEqual(group.title, "Account settings")
        title_property = group.metaObject().property(group.metaObject().indexOfProperty("title"))
        self.assertTrue(title_property.isDesignable())
        self.assertTrue(title_property.isWritable())
        self.assertGreaterEqual(group.metaObject().indexOfProperty("title"), group.metaObject().propertyOffset())
        self.assertGreaterEqual(group.metaObject().indexOfProperty("subtitleVisible"), group.metaObject().propertyOffset())
        self.assertEqual(group.themeIndex, 5)
        self.assertGreaterEqual(group.contentsMargins().top(), group.headerHeight)
        self.assertTrue(group.checked)
        group.deleteLater()

    def test_group_box_renders_with_title_property_and_child_layout(self) -> None:
        group = MonkezGroupBox()
        group.title = "Rendered title"
        group.subtitle = "Rendered subtitle"
        group.subtitleVisible = False
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("Child content"))
        group.resize(320, 220)
        group.show()
        self.app.processEvents()

        pixmap = group.grab()

        self.assertFalse(pixmap.isNull())
        self.assertEqual(group.title, "Rendered title")
        self.assertEqual(group.subtitle, "Rendered subtitle")
        self.assertFalse(group.subtitleVisible)
        group.close()
        group.deleteLater()

    def test_group_box_does_not_apply_header_padding_twice(self) -> None:
        group = MonkezGroupBox()
        layout = QVBoxLayout(group)
        child = QLabel("Child content")
        layout.addWidget(child)
        group.resize(320, 220)
        group.show()
        self.app.processEvents()

        self.assertEqual(layout.contentsMargins().top(), 0)
        self.assertLessEqual(child.geometry().top(), group.contentsRect().top() + 1)
        self.assertLess(child.geometry().top(), group.headerHeight * 2)
        group.close()
        group.deleteLater()

    def test_group_box_auto_header_height_tracks_subtitle_and_font(self) -> None:
        group = MonkezGroupBox()
        group.subtitle = "Secondary information"
        with_subtitle = group.headerHeight
        group.subtitleVisible = False
        title_only = group.headerHeight
        font = group.font()
        font.setPointSize(font.pointSize() + 8)
        group.setFont(font)
        large_title = group.headerHeight

        self.assertLess(title_only, with_subtitle)
        self.assertGreater(large_title, title_only)
        self.assertTrue(group.autoHeaderHeight)
        group.deleteLater()

    def test_radio_dial_and_gauges_expose_distinct_styles_and_shadow(self) -> None:
        radio = MonkezRadioButton()
        dial = MonkezDial()
        gauges = (MonkezRadialGauge(), MonkezArcGauge(), MonkezLinearGauge())

        radio.radioStyle = 2
        dial.dialStyle = 2
        radio.shadowEnabled = True
        dial.shadowEnabled = True
        self.assertEqual(int(radio.radioStyle), 2)
        self.assertEqual(int(dial.dialStyle), 2)
        self.assertIsNotNone(radio.graphicsEffect())
        self.assertIsNotNone(dial.graphicsEffect())

        for gauge in gauges:
            gauge.shadowEnabled = True
            gauge.resize(gauge.sizeHint())
            gauge.show()
            self.app.processEvents()
            self.assertFalse(gauge.grab().isNull())
            self.assertIsNotNone(gauge.graphicsEffect())
            gauge.close()
            gauge.deleteLater()
        radio.deleteLater()
        dial.deleteLater()

    def test_lcd_uses_decimal_points_and_removes_commas(self) -> None:
        lcd = MonkezLCDNumber()
        lcd.resize(240, 80)
        lcd.setDigitCount(7)
        lcd.show()

        lcd.setDisplayText("1234.56")
        self.app.processEvents()
        dot_image = lcd.grab().toImage()
        lcd.setDisplayText("1,234.56")
        self.app.processEvents()
        sanitized_image = lcd.grab().toImage()

        self.assertEqual("1234.56", lcd.displayText)
        self.assertEqual(dot_image, sanitized_image)
        self.assertFalse(hasattr(lcd, "decimalSeparator"))
        self.assertFalse(hasattr(lcd, "groupSeparator"))
        self.assertFalse(hasattr(lcd, "groupingEnabled"))

        # An explicit widget stylesheet can override the resolved QLCDNumber
        # foreground without changing our cached digitColor property.
        configured_digit_color = lcd.digitColor
        resolved_digit_color = QColor("#111827")
        lcd.setStyleSheet(
            lcd.styleSheet()
            + f"MonkezLCDNumber {{ color: {resolved_digit_color.name()}; }}"
        )
        self.app.processEvents()
        palette_override_image = lcd.grab().toImage()
        rendered_colors = {
            palette_override_image.pixelColor(x, y).rgba()
            for y in range(palette_override_image.height())
            for x in range(palette_override_image.width())
        }
        self.assertIn(resolved_digit_color.rgba(), rendered_colors)
        self.assertNotIn(configured_digit_color.rgba(), rendered_colors)

        lcd.setDigitColor(QColor("#f59e0b"))
        self.app.processEvents()
        runtime_color_image = lcd.grab().toImage()
        runtime_colors = {
            runtime_color_image.pixelColor(x, y).rgba()
            for y in range(runtime_color_image.height())
            for x in range(runtime_color_image.width())
        }
        self.assertIn(QColor("#f59e0b").rgba(), runtime_colors)
        self.assertNotIn(resolved_digit_color.rgba(), runtime_colors)

        lcd.autoDigitCount = True
        self.assertEqual("12345.67", lcd.displayFormatted(12345.67, 2))
        self.assertEqual(7, lcd.digitCount())
        lcd.decimalPlaces = 1
        lcd.number = 9876.54
        self.assertEqual("9876.5", lcd.displayText)
        lcd.close()
        lcd.deleteLater()

    def test_feedback_widgets_expose_complete_runtime_states(self) -> None:
        badge = MonkezStatusBadge()
        badge.statusIndex = 3
        badge.badgeText = "Camera offline"
        self.assertEqual(3, badge.statusIndex)
        self.assertIn("Camera offline", badge.text())

        for theme_index in range(6):
            badge.themeIndex = theme_index
            badge.resize(badge.sizeHint())
            badge.show()
            self.app.processEvents()
            badge_image = badge.grab().toImage()
            self.assertEqual(0, badge_image.pixelColor(0, 0).alpha())
            self.assertGreater(badge_image.pixelColor(badge_image.width() // 2, 0).alpha(), 200)

        spinner = MonkezLoadingIndicator()
        spinner.resize(48, 48)
        spinner.speed = 45
        spinner.running = False
        self.assertFalse(spinner.running)
        self.assertFalse(spinner.grab().isNull())

        overlay = MonkezLoadingOverlay()
        overlay.message = "Connecting…"
        overlay.resize(260, 150)
        overlay.show()
        self.app.processEvents()
        self.assertEqual("Connecting…", overlay.message)
        self.assertFalse(overlay.grab().isNull())
        overlay.active = False
        self.assertFalse(overlay.isVisible())

        toast = MonkezToast()
        toast.showMessage("Saved", 0)
        self.app.processEvents()
        self.assertTrue(toast.isVisible())
        toast.dismiss()
        self.assertFalse(toast.isVisible())

        for widget in (badge, spinner, overlay, toast):
            widget.close()
            widget.deleteLater()

    def test_range_slider_clamps_values_and_supports_orientation(self) -> None:
        slider = MonkezRangeSlider()
        changes = []
        slider.valuesChanged.connect(lambda lower, upper: changes.append((lower, upper)))
        slider.setRange(-10, 110)
        slider.setValues(90, 20)
        self.assertEqual((20, 90), (slider.lowerValue, slider.upperValue))
        slider.lowerValue = 100
        self.assertEqual(90, slider.lowerValue)
        slider.upperValue = -20
        self.assertEqual(90, slider.upperValue)
        slider.orientation = Qt.Orientation.Vertical
        slider.resize(slider.sizeHint())
        slider.show()
        self.app.processEvents()
        self.assertFalse(slider.grab().isNull())
        self.assertTrue(changes)
        slider.close()
        slider.deleteLater()

    def test_segmented_breadcrumb_and_action_widgets_update_state(self) -> None:
        segmented = MonkezSegmentedControl()
        segmented.items = "Live | Result | Log"
        segmented.currentIndex = 2
        self.assertEqual("Log", segmented.currentText())

        breadcrumb = MonkezBreadcrumb()
        breadcrumb.items = "Home | Devices | Camera"
        breadcrumb.currentIndex = 1
        self.assertEqual(1, breadcrumb.currentIndex)

        button = MonkezButton()
        button.setText("Save")
        button.loadingText = "Saving"
        button.loading = True
        self.assertTrue(button.loading)
        self.assertFalse(button.isEnabled())
        button.loading = False
        self.assertEqual("Save", button.text())
        self.assertTrue(button.isEnabled())

        button.iconText = "⚙"
        button.buttonSize = 44
        button.styleIndex = 1
        self.assertEqual("⚙", button.text())
        self.assertEqual(QSize(44, 44), button.sizeHint())
        self.assertEqual(QSize(44, 44), button.size())
        button.styleIndex = 0
        self.assertEqual("Save", button.text())
        self.assertEqual(0, button.minimumWidth())
        self.assertEqual(16777215, button.maximumWidth())

        for widget in (segmented, breadcrumb, button):
            widget.close()
            widget.deleteLater()

    def test_file_picker_tracks_paths_and_validation(self) -> None:
        picker = MonkezFilePicker()
        with tempfile.NamedTemporaryFile() as handle:
            picker.path = handle.name
            self.assertTrue(picker.isValidPath())
            self.assertEqual(handle.name, picker.path)
        picker.requireExisting = False
        picker.path = "future-output.txt"
        self.assertTrue(picker.isValidPath())
        picker.clear()
        self.assertEqual("", picker.path)
        picker.deleteLater()

    def test_pagination_calculates_pages_and_responsive_ellipsis(self) -> None:
        pagination = MonkezPagination()
        changes = []
        pagination.pageChanged.connect(changes.append)
        pagination.pageSize = 25
        pagination.totalItems = 101
        self.assertEqual(5, pagination.pageCount)
        self.assertEqual(25, pagination.pageSize)

        pagination.pageCount = 20
        pagination.maximumVisiblePages = 5
        pagination.currentPage = 10
        self.assertEqual((1, None, 9, 10, 11, None, 20), pagination.visiblePages())
        pagination.nextPage()
        pagination.previousPage()
        self.assertEqual([10, 11, 10], changes[-3:])

        pagination.loopNavigation = True
        pagination.currentPage = 20
        pagination.nextPage()
        self.assertEqual(1, pagination.currentPage)
        pagination.previousPage()
        self.assertEqual(20, pagination.currentPage)
        pagination.deleteLater()

    def test_pagination_styles_render_and_keyboard_navigation_works(self) -> None:
        pagination = MonkezPagination()
        pagination.resize(520, 48)
        pagination.show()
        images = []
        for style_index in range(4):
            pagination.styleIndex = style_index
            self.app.processEvents()
            image = pagination.grab().toImage()
            self.assertFalse(image.isNull())
            images.append(image)
        self.assertGreater(len({image.cacheKey() for image in images}), 1)

        pagination.currentPage = 4
        QTest.keyClick(pagination, Qt.Key.Key_Right)
        self.assertEqual(5, pagination.currentPage)
        QTest.keyClick(pagination, Qt.Key.Key_Home)
        self.assertEqual(1, pagination.currentPage)
        QTest.keyClick(pagination, Qt.Key.Key_End)
        self.assertEqual(pagination.pageCount, pagination.currentPage)
        pagination.currentPage = 4
        pagination.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        QTest.keyClick(pagination, Qt.Key.Key_Left)
        self.assertEqual(5, pagination.currentPage)
        self.assertEqual(f"Page 5 of {pagination.pageCount}", pagination.accessibleDescription())
        pagination.close()
        pagination.deleteLater()

    def test_table_filters_sorts_paginates_and_restores_state(self) -> None:
        table = MonkezTable()
        table.setColumns(
            [
                {"key": "id", "title": "ID", "type": "number", "width": 70},
                {"key": "name", "title": "Name", "width": 180, "editable": True},
                {"key": "status", "title": "Status", "type": "badge"},
                {"key": "progress", "title": "Progress", "type": "progress"},
            ]
        )
        rows = [
            {"id": index, "name": f"Camera {index}", "status": "Online" if index % 2 else "Offline", "progress": index}
            for index in range(55)
        ]
        table.setRows(rows)
        self.assertEqual(55, table.filteredRowCount())
        self.assertEqual(20, table.visibleRowCount())
        table.setCurrentPage(3)
        self.assertEqual(15, table.visibleRowCount())
        self.assertEqual(40, table.rowData(0)["id"])

        table.setSearchText("Camera 4")
        self.assertEqual(1, table.currentPage)
        self.assertEqual(11, table.filteredRowCount())
        table.setColumnFilter("status", "online")
        self.assertEqual(5, table.filteredRowCount())
        table.setSearchText("")
        table.setColumnFilter("status", "")
        table.setSort("status")
        self.assertEqual("_TableHeader", type(table.tableView().horizontalHeader()).__name__)
        self.assertFalse(table.tableView().horizontalHeader().isSortIndicatorShown())
        table.setSort("progress", descending=True, additive=True)
        self.assertEqual(54, table.rowData(0)["progress"])

        table.setColumnVisible("progress", False)
        state = table.saveState()
        table.setColumnVisible("progress", True)
        table.setDensityIndex(2)
        table.restoreState(state)
        self.assertTrue(table.tableView().isColumnHidden(3))
        self.assertEqual(state["densityIndex"], table.densityIndex)
        table.setBackground("#f8fafc").setForeground("#0f172a").setBorder("#94a3b8").setAccent("#7c3aed")
        table.setStyleIndex(3)
        table.setBorderWidth(2)
        table.setBorderRadius(18)
        table.setControlRadius(9)
        table.setControlHeight(38)
        self.assertEqual(QColor("#f8fafc"), table.backgroundColor)
        self.assertEqual(QColor("#7c3aed"), table.accentColor)
        self.assertEqual(2, table.borderWidth)
        self.assertEqual(18, table.borderRadius)
        self.assertEqual(9, table.controlRadius)
        self.assertEqual(38, table.controlHeight)
        self.assertEqual(38, table._page_size_combo.height())
        self.assertIn("QToolButton#monkezTableColumns::menu-indicator", table.styleSheet())
        self.assertIn("border-top-left-radius: 16px", table.styleSheet())

        edits = []
        table.cellEdited.connect(lambda row, key, value: edits.append((row, key, value)))
        table.setEditable(True)
        self.assertTrue(table.sourceModel().setData(table.sourceModel().index(0, 1), "Updated camera"))
        self.assertEqual([(0, "name", "Updated camera")], edits)
        table.tableView().selectRow(0)
        self.assertIs(table.rowData(0), table.selectedRows()[0])
        with tempfile.TemporaryDirectory() as directory:
            csv_path = table.exportCsv(Path(directory) / "table.csv")
            csv_text = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("ID,Name,Status", csv_text)
            self.assertNotIn("Progress", csv_text.splitlines()[0])
        table.resize(720, 420)
        table.show()
        self.app.processEvents()
        self.assertFalse(table.grab().isNull())
        table.close()
        table.deleteLater()

    def test_table_server_mode_and_large_model_are_zero_copy(self) -> None:
        table = MonkezTable()
        table.setColumns([{"key": "id", "type": "number"}, {"key": "name"}])
        rows = [{"id": index, "name": f"Row {index}"} for index in range(50_000)]
        table.setRows(rows)
        self.assertEqual(50_000, table.sourceModel().rowCount())
        self.assertEqual(20, table.visibleRowCount())
        self.assertIs(rows[123], table.sourceModel().rowData(123))
        table.setSearchText("Row 49999")
        self.assertEqual(1, table.filteredRowCount())

        queries = []
        table.queryChanged.connect(queries.append)
        table.setServerMode(True)
        table.setRows([{"id": 1, "name": "Current page"}], total=12_345)
        table.setSearchText("remote search")
        table.setColumnFilter("name", "camera")
        table.setSort("id", descending=True)
        self.assertEqual(1, table.visibleRowCount())
        self.assertEqual(12_345, table.totalItems)
        self.assertEqual("remote search", queries[-1]["search"])
        self.assertEqual({"name": "camera"}, queries[-1]["filters"])
        self.assertEqual([{"key": "id", "descending": True}], queries[-1]["sort"])
        table.deleteLater()

    def test_radial_gauge_exposes_part_specific_color_names(self) -> None:
        gauge = MonkezRadialGauge()
        gauge.setActiveTicksColor("#22c55e")
        gauge.setInactiveTicksColor("#cbd5e1")
        gauge.setNeedleColor("#ef4444")
        gauge.setValueTextColor("#0f172a")
        gauge.setScaleTextColor("#64748b")

        self.assertEqual("#22c55e", gauge.activeTicksColor.name())
        self.assertEqual("#cbd5e1", gauge.inactiveTicksColor.name())
        self.assertEqual("#ef4444", gauge.needleColor.name())
        self.assertEqual("#0f172a", gauge.valueTextColor.name())
        self.assertEqual("#64748b", gauge.scaleTextColor.name())
        self.assertEqual(gauge.activeTicksColor, gauge.valueColor)
        self.assertEqual(gauge.inactiveTicksColor, gauge.trackColor)
        self.assertEqual(gauge.needleColor, gauge.dangerColor)
        gauge.deleteLater()

    def test_combo_popup_has_no_native_black_frame_or_shadow(self) -> None:
        combo = MonkezComboBox()
        popup = combo._popup

        self.assertTrue(popup.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(popup.windowFlags() & Qt.WindowType.NoDropShadowWindowHint)
        self.assertTrue(popup.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(popup.windowFlags() & Qt.WindowType.Popup)
        self.assertEqual(popup.contentsMargins().left(), 0)
        self.assertEqual(popup.contentsMargins().top(), 0)
        self.assertEqual(popup.contentsMargins().right(), 0)
        self.assertEqual(popup.contentsMargins().bottom(), 0)
        self.assertIs(popup.view.model(), combo.model())
        combo.deleteLater()

    def test_combo_popup_is_owned_by_dialog_window(self) -> None:
        dialog = QDialog()
        layout = QVBoxLayout(dialog)
        combo = MonkezComboBox(dialog)
        combo.addItems(["A", "B", "C"])
        layout.addWidget(combo)
        dialog.show()
        self.app.processEvents()

        combo.showPopup()
        self.app.processEvents()

        self.assertIs(combo._popup.parentWidget(), dialog)
        self.assertTrue(combo._popup.windowFlags() & Qt.WindowType.Popup)
        combo.hidePopup()
        dialog.close()
        dialog.deleteLater()

    def test_combo_can_use_compact_designer_height(self) -> None:
        combo = MonkezComboBox()
        combo.addItem("Compact item")
        combo.themeIndex = 1
        combo.setFixedHeight(24)
        combo.show()
        self.app.processEvents()

        self.assertEqual(combo.height(), 24)
        self.assertLessEqual(combo.minimumHeight(), 24)
        self.assertNotIn("min-height", combo.styleSheet())
        self.assertLessEqual(combo._popup.view.sizeHintForRow(0), 32)
        self.assertEqual(combo._popup.layout().contentsMargins().left(), 3)
        combo.close()
        combo.deleteLater()

    def test_text_input_clears_trailing_icon_hit_area(self) -> None:
        text_input = monkez_widgets.MonkezTextInput()
        text_input.trailingIcon = "clear.png"
        text_input.resize(200, 40)
        text_input.show()
        self.app.processEvents()
        self.assertFalse(text_input.trailing_rect.isNull())

        text_input.trailingIcon = ""
        self.assertTrue(text_input.trailing_icon.isNull())
        self.assertTrue(text_input.trailing_rect.isNull())
        text_input.close()
        text_input.deleteLater()

    def test_text_input_trailing_icon_emits_on_completed_click(self) -> None:
        text_input = monkez_widgets.MonkezTextInput()
        text_input.trailingIcon = "clear.png"
        text_input.resize(200, 40)
        text_input.show()
        self.app.processEvents()
        clicked = []
        text_input.trailingIconClicked.connect(lambda: clicked.append(True))
        center = text_input.trailing_rect.center()

        QTest.mousePress(text_input, Qt.MouseButton.LeftButton, pos=center)
        self.assertEqual(clicked, [])
        QTest.mouseRelease(text_input, Qt.MouseButton.LeftButton, pos=center)
        self.assertEqual(clicked, [True])

        QTest.mousePress(text_input, Qt.MouseButton.LeftButton, pos=center)
        QTest.mouseRelease(text_input, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
        self.assertEqual(clicked, [True])
        text_input.close()
        text_input.deleteLater()

    def test_combo_designer_font_applies_to_control_and_popup(self) -> None:
        combo = MonkezComboBox()
        combo.addItem("Large font item")
        font = combo.font()
        font.setFamily("Arial")
        font.setPointSize(18)
        font.setBold(True)

        combo.setFont(font)
        self.app.processEvents()

        self.assertEqual(combo.font().pointSize(), 18)
        self.assertEqual(combo.font().family(), "Arial")
        self.assertTrue(combo.font().bold())
        self.assertEqual(combo._popup.view.font(), combo.font())
        self.assertNotIn("font-size", combo.styleSheet())
        self.assertGreater(combo._popup.view.sizeHintForRow(0), 30)
        combo.deleteLater()

    def test_combo_starts_without_placeholder_items(self) -> None:
        combo = MonkezComboBox()

        self.assertEqual(combo.count(), 0)
        self.assertEqual(combo.currentIndex(), -1)
        combo.deleteLater()

    def test_empty_combo_does_not_open_blank_popup(self) -> None:
        combo = MonkezComboBox()
        combo.show()
        combo.showPopup()
        self.app.processEvents()

        self.assertFalse(combo._popup.isVisible())
        self.assertFalse(combo.is_opened)
        combo.close()
        combo.deleteLater()

    def test_stepper_and_date_button_hover_regions_do_not_cover_outer_border(self) -> None:
        for widget_cls in (
            monkez_widgets.MonkezDateEdit,
            monkez_widgets.MonkezDateTimeEdit,
            monkez_widgets.MonkezTimeEdit,
            monkez_widgets.MonkezSpinBox,
            monkez_widgets.MonkezDoubleSpinBox,
        ):
            widget = widget_cls()
            style = widget.styleSheet()

            self.assertIn("margin: 1px", style, widget_cls.__name__)
            self.assertIn("border-right: 1px solid transparent", style, widget_cls.__name__)
            self.assertIn("background-color: transparent", style, widget_cls.__name__)
            self.assertIn("border-left: 1px solid", style, widget_cls.__name__)
            self.assertNotRegex(style, r":hover \{[^}]*border", widget_cls.__name__)
            widget.deleteLater()

    def test_calendar_exposes_polished_date_colors_and_headers(self) -> None:
        calendar = MonkezCalendarWidget()
        style = calendar.styleSheet()

        self.assertEqual(
            calendar.verticalHeaderFormat(),
            calendar.VerticalHeaderFormat.NoVerticalHeader,
        )
        self.assertIn("MonkezCalendarWidget QSpinBox::up-button", style)
        self.assertIn("width: 0px", style)
        self.assertIn("selection-background-color", style)
        for property_name in ("weekendColor", "todayColor", "outsideMonthColor"):
            self.assertGreaterEqual(calendar.metaObject().indexOfProperty(property_name), 0)
        self.assertGreaterEqual(calendar.sizeHint().width(), 340)
        self.assertGreaterEqual(calendar.sizeHint().height(), 280)
        self.assertLessEqual(calendar.minimumSizeHint().width(), 120)
        self.assertLessEqual(calendar.minimumSizeHint().height(), 100)
        calendar.deleteLater()


if __name__ == "__main__":
    unittest.main()
