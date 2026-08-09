from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from monkez_pyqt6.monkez_canva import (
    TEMPLATE_FORMAT,
    CanvasTemplate,
    TemplateCatalog,
    decode_canvas_template,
)
from monkez_pyqt6.monkez_widgets import MonkezCanva


def subflow_payload() -> dict:
    return {
        "format": "monkez-subflow",
        "version": 1,
        "root": "pipeline",
        "elements": [
            {"id": "source", "type": "node", "x": 20, "y": 50, "text": "Source"},
            {"id": "sink", "type": "node", "x": 260, "y": 50, "text": "Sink"},
        ],
        "connectors": [
            {"id": "edge", "source": "source", "target": "sink"}
        ],
        "groups": [
            {"id": "pipeline", "kind": "subflow", "members": ["source", "sink"]}
        ],
    }


class CanvasTemplateCoreTests(unittest.TestCase):
    def test_manifest_round_trip_normalizes_metadata(self) -> None:
        template = CanvasTemplate(
            " Order Pipeline ",
            "Order pipeline",
            "subflow",
            subflow_payload(),
            "Reusable order path",
            ("API", "orders", "api"),
            "assets/order.png",
            "Platform team",
        )
        decoded = decode_canvas_template(json.dumps(template.to_dict()))

        self.assertEqual(TEMPLATE_FORMAT, decoded.to_dict()["format"])
        self.assertEqual("order-pipeline", decoded.template_id)
        self.assertEqual(("api", "orders"), decoded.tags)
        self.assertEqual(template.to_dict(), decoded.to_dict())

    def test_catalog_is_deterministic_and_isolates_malformed_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog = TemplateCatalog(directory)
            second = CanvasTemplate(
                "second", "Zulu", "subflow", subflow_payload(), tags=("flow",)
            )
            first = CanvasTemplate(
                "first", "Alpha", "subflow", subflow_payload(), tags=("flow", "api")
            )
            catalog.save(second)
            catalog.save(first)
            (Path(directory) / "broken.monkez-template.json").write_text(
                "{broken", encoding="utf-8"
            )

            scan = catalog.scan()
            self.assertEqual(("first", "second"), tuple(item.template_id for item in scan.templates))
            self.assertEqual("broken.monkez-template.json", scan.errors[0][0])
            self.assertEqual(("first",), tuple(item.template_id for item in catalog.scan(("api",)).templates))
            with self.assertRaises(FileExistsError):
                catalog.save(first, replace_existing=False)

    def test_manifest_rejects_missing_dependencies(self) -> None:
        payload = subflow_payload()
        payload["connectors"][0]["target"] = "missing"
        with self.assertRaisesRegex(ValueError, "endpoints"):
            CanvasTemplate("bad", "Bad", "subflow", payload)


class CanvasTemplateWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_project_catalog_save_list_instantiate_and_undo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canvas = MonkezCanva()
            canvas.setProjectDirectory(directory)
            source = canvas.addNode("Source", 10, 40, element_id="source")
            sink = canvas.addNode("Sink", 260, 40, element_id="sink")
            canvas.connectElements(source, sink, connector_id="edge")
            group = canvas.addSubflow((source, sink), "pipeline", label="Pipeline")
            saved: list[tuple[str, str]] = []
            instantiated: list[tuple[str, str]] = []
            canvas.projectTemplateSaved.connect(
                lambda template_id, path: saved.append((template_id, path))
            )
            canvas.projectTemplateInstantiated.connect(
                lambda template_id, group_id: instantiated.append((template_id, group_id))
            )

            target = canvas.saveGroupAsProjectTemplate(
                group,
                "pipeline-template",
                description="Reusable pipeline",
                tags=("flow", "demo"),
                author="Monkez",
            )
            self.assertTrue(target.is_file())
            self.assertIn(".monkez_canva", target.parts)
            self.assertEqual("pipeline-template", saved[0][0])
            listing = canvas.projectTemplates("flow")
            self.assertEqual("Pipeline", listing[0]["label"])
            self.assertEqual(2, listing[0]["elements"])

            canvas.undoStack().clear()
            imported = canvas.instantiateProjectTemplate("pipeline-template", 600, 200)
            self.assertNotEqual(group, imported)
            self.assertEqual(("pipeline-template", imported), instantiated[0])
            self.assertEqual(4, len(canvas.elements()))
            self.assertEqual(1, canvas.undoStack().count())
            self.assertTrue(canvas.undo())
            self.assertEqual(2, len(canvas.elements()))
            canvas.close()
            canvas.deleteLater()


if __name__ == "__main__":
    unittest.main()
