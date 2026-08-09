from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from monkez_pyqt6.monkez_canva import (
    AssetIntegrityIssue,
    create_default_element_registry,
    diagnose_document,
    diff_documents,
    document_fingerprint,
)
from monkez_pyqt6.monkez_widgets import MonkezCanva


def sample_document() -> dict:
    return {
        "format": "monkez-canva",
        "version": 1,
        "scene": {"width": 1200, "height": 800, "gridVisible": True},
        "elements": [
            {
                "id": "source",
                "type": "node",
                "x": 20,
                "y": 40,
                "width": 180,
                "height": 96,
                "text": "Source",
                "ports": [{"id": "out", "mode": "output", "side": "right"}],
            },
            {
                "id": "sink",
                "type": "node",
                "x": 320,
                "y": 40,
                "width": 180,
                "height": 96,
                "text": "Sink",
                "ports": [{"id": "in", "mode": "input", "side": "left"}],
            },
        ],
        "connectors": [
            {
                "id": "edge",
                "type": "connector",
                "source": "source",
                "target": "sink",
                "sourcePort": "out",
                "targetPort": "in",
                "label": "payload",
            }
        ],
    }


class CanvasDocumentDiagnosticsTests(unittest.TestCase):
    def test_healthy_report_has_stable_metrics_and_fingerprint(self) -> None:
        document = sample_document()
        report = diagnose_document(document, registry=create_default_element_registry())

        self.assertTrue(report.valid)
        self.assertEqual("healthy", report.severity)
        self.assertEqual(2, report.metrics["elements"])
        self.assertEqual(1, report.metrics["connectedComponents"])
        self.assertEqual(0, report.metrics["isolatedElements"])
        self.assertEqual(document_fingerprint(document), report.fingerprint)
        self.assertEqual(report.fingerprint, report.to_dict()["fingerprint"])

    def test_report_combines_component_group_resource_and_asset_health(self) -> None:
        document = sample_document()
        document["elements"].append(
            {
                "id": "plugin-object",
                "type": "vendor.sensor",
                "x": 40,
                "y": 240,
                "width": 160,
                "height": 80,
            }
        )
        document["groups"] = [{"id": "empty", "members": []}]
        document["resources"] = [{"id": "photo", "kind": "image", "uri": ""}]
        report = diagnose_document(
            document,
            registry=create_default_element_registry(),
            asset_issues=(AssetIntegrityIssue("assets/photo.png", "file is missing"),),
        )

        self.assertFalse(report.valid)
        self.assertEqual("error", report.severity)
        codes = {issue.code for issue in report.issues}
        self.assertEqual(
            {"component.missing", "group.empty", "resource.missing-uri", "asset.integrity"},
            codes,
        )
        self.assertEqual(2, report.metrics["connectedComponents"])
        self.assertEqual(1, report.metrics["isolatedElements"])

    def test_invalid_document_returns_bounded_error_report(self) -> None:
        document = sample_document()
        document["connectors"][0]["target"] = "absent"

        report = diagnose_document(document)

        self.assertFalse(report.valid)
        self.assertEqual("document.invalid", report.issues[0].code)
        self.assertIn("missing endpoints", report.issues[0].message)
        self.assertGreater(report.metrics["jsonBytes"], 0)

        document = sample_document()
        document["scene"]["zoom"] = float("nan")
        non_json = diagnose_document(document)
        self.assertEqual("document.non-json", non_json.issues[0].code)
        self.assertEqual("", non_json.fingerprint)

    def test_semantic_diff_is_id_based_and_reports_nested_fields(self) -> None:
        before = sample_document()
        reordered = copy.deepcopy(before)
        reordered["elements"].reverse()
        self.assertTrue(diff_documents(before, reordered).identical)
        self.assertEqual(document_fingerprint(before), document_fingerprint(reordered))

        after = copy.deepcopy(before)
        after["scene"]["gridVisible"] = False
        after["elements"][0]["x"] = 88
        after["elements"][0]["ports"][0]["label"] = "Events"
        after["connectors"] = []
        after["groups"] = [{"id": "pipeline", "members": ["source", "sink"]}]
        after["review"] = {"approved": True}

        result = diff_documents(before, after)
        self.assertFalse(result.identical)
        self.assertEqual({"added": 1, "removed": 1, "modified": 3}, result.counts)
        changes = {(change.target_type, change.target_id): change for change in result.changes}
        self.assertEqual(("gridVisible",), changes[("scene", "scene")].fields)
        self.assertEqual(
            ("ports", "x"), changes[("element", "source")].fields
        )
        self.assertEqual("removed", changes[("connector", "edge")].action)
        self.assertEqual("added", changes[("group", "pipeline")].action)
        self.assertEqual(("review",), changes[("document", "metadata")].fields)


class CanvasDiagnosticsWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_canvas_report_tracks_clean_baseline_and_exports_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canvas = MonkezCanva()
            canvas.setProjectDirectory(directory)
            diagnostics = []
            diffs = []
            canvas.documentDiagnosticsReady.connect(diagnostics.append)
            canvas.documentDiffReady.connect(diffs.append)
            canvas.addNode("Source", 20, 30, element_id="source")

            self.assertEqual(1, canvas.documentDiff().counts["added"])
            report = canvas.diagnoseDocument(verify_assets=False)
            self.assertTrue(report.valid)
            self.assertEqual(1, report.metrics["elements"])
            self.assertTrue(diagnostics)
            self.assertTrue(diffs)

            canvas.saveDocument(Path(directory) / "canvas.json")
            self.assertTrue(canvas.documentDiff().identical)
            canvas.updateElement("source", text="Updated source")
            current_diff = canvas.documentDiff()
            self.assertEqual(1, current_diff.counts["modified"])
            self.assertEqual(("text",), current_diff.changes[0].fields)

            target = canvas.exportDocumentReport(Path(directory) / "health.json")
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual("monkez-canva-report", payload["format"])
            self.assertEqual(1, payload["diff"]["counts"]["modified"])
            canvas.close()
            canvas.deleteLater()

    def test_document_health_ui_and_discovery_are_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canvas = MonkezCanva()
            canvas.resize(900, 600)
            canvas.setProjectDirectory(directory)
            canvas.addNode("Processor", 40, 50, element_id="processor")
            canvas.setEditMode(True)
            canvas.showDocumentDiagnostics()
            self.app.processEvents()
            dialog = canvas._document_report

            self.assertTrue(dialog.isVisible())
            self.assertEqual("1", dialog._metric_labels["elements"].text())
            self.assertEqual(2, dialog._tabs.count())
            self.assertEqual("Healthy", dialog._status.text())
            self.assertEqual(1, dialog._diff.counts["added"])
            self.assertEqual(len(dialog._diff.changes), dialog._changes.count())
            labels = {action.text() for action in canvas.createContextMenu().actions()}
            self.assertIn("Document health...", labels)

            canvas.showCommandPalette("document health")
            self.app.processEvents()
            command_ids = {
                str(
                    canvas._command_palette._list.item(index).data(
                        Qt.ItemDataRole.UserRole
                    )
                )
                for index in range(canvas._command_palette._list.count())
            }
            self.assertIn("document:health", command_ids)
            canvas.close()
            canvas.deleteLater()


if __name__ == "__main__":
    unittest.main()
