from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from monkez_pyqt6.monkez_widgets import MonkezCanva
from monkez_pyqt6.monkez_widgets.monkez_canva import _CanvasCommandPalette


class CanvasGraphicExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.canvas = MonkezCanva()
        self.canvas.resize(800, 500)
        self.first = self.canvas.addElement(
            "rectangle",
            x=20,
            y=30,
            width=140,
            height=80,
            text="First",
            color="#f97316",
        )
        self.second = self.canvas.addElement(
            "ellipse",
            x=520,
            y=260,
            width=120,
            height=90,
            text="Second",
            color="#2563eb",
        )
        self.connector = self.canvas.connectElements(
            self.first, self.second, connector_id="first-to-second", label="next"
        )
        self.app.processEvents()

    def tearDown(self) -> None:
        self.canvas.setEditMode(False)
        self.canvas.close()
        self.canvas.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_png_svg_pdf_and_transparent_selection_export(self) -> None:
        completed: list[tuple[str, str, str]] = []
        document_before = self.canvas.toJson(indent=None)
        revision_before = self.canvas.documentModel().revision
        modified_before = self.canvas.isDocumentModified()
        self.canvas.exportCompleted.connect(
            lambda path, format_name, scope: completed.append((path, format_name, scope))
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            png = self.canvas.exportScene(root / "scene.png", scale=1.25)
            svg = self.canvas.exportScene(root / "scene.svg")
            pdf = self.canvas.exportScene(root / "scene.pdf")

            self.canvas.setEditMode(True)
            self.canvas.selectElement(self.first)
            selection = self.canvas.exportSelection(root / "selection.png", transparent=True, padding=18)

            image = QImage(str(png))
            selection_image = QImage(str(selection))
            self.assertFalse(image.isNull())
            self.assertFalse(selection_image.isNull())
            self.assertLess(selection_image.width(), image.width())
            self.assertLess(selection_image.height(), image.height())
            self.assertEqual(0, selection_image.pixelColor(0, 0).alpha())
            self.assertIn(b"<svg", svg.read_bytes()[:500])
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
            self.assertGreater(pdf.stat().st_size, 500)

        self.assertEqual(
            [("png", "scene"), ("svg", "scene"), ("pdf", "scene"), ("png", "selection")],
            [(format_name, scope) for _path, format_name, scope in completed],
        )
        self.assertTrue(self.canvas.element(self.first).isSelected())
        self.assertTrue(self.canvas.element(self.second).isVisible())
        self.assertEqual(document_before, self.canvas.toJson(indent=None))
        self.assertEqual(revision_before, self.canvas.documentModel().revision)
        self.assertEqual(modified_before, self.canvas.isDocumentModified())

    def test_graph_exports_page_configuration_and_command_discovery(self) -> None:
        self.canvas.setObjectName("Export sample")
        self.canvas.setExportPageConfiguration(
            {
                "size": "Letter",
                "orientation": "portrait",
                "margin_left_mm": 8,
                "resolution": 180,
            }
        )
        config = self.canvas.exportPageConfiguration()
        self.assertEqual("LETTER", config["size"])
        self.assertEqual("portrait", config["orientation"])
        self.assertEqual(180, config["resolution"])
        with self.assertRaisesRegex(ValueError, "page size"):
            self.canvas.setExportPageConfiguration({"size": "Poster"})

        with tempfile.TemporaryDirectory() as directory:
            dot = self.canvas.exportDot(Path(directory) / "graph.dot")
            mermaid = self.canvas.exportMermaid(Path(directory) / "graph.mmd", direction="TB")
            self.assertIn('digraph "Export sample"', dot.read_text(encoding="utf-8"))
            self.assertIn('"first-to-second"', dot.read_text(encoding="utf-8"))
            self.assertTrue(mermaid.read_text(encoding="utf-8").startswith("flowchart TB"))

        self.canvas.setEditMode(True)
        palette = _CanvasCommandPalette(self.canvas)
        command_ids = {command[0] for command in palette._commands()}
        palette.deleteLater()
        self.assertTrue(
            {
                "export:scene",
                "export:selection",
                "export:dot",
                "export:mermaid",
                "print:preview",
                "print:page-setup",
            }.issubset(command_ids)
        )
        blank_menu = self.canvas.createContextMenu("")
        self.assertIn("Export", [action.text() for action in blank_menu.actions()])

    def test_selection_export_requires_selection(self) -> None:
        self.canvas._scene.clearSelection()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Select at least one"):
                self.canvas.exportSelection(Path(directory) / "empty.png")


if __name__ == "__main__":
    unittest.main()
