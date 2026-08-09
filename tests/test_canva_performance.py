from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from monkez_pyqt6.monkez_canva import (
    CanvasDocument,
    CanvasPerformancePolicy,
    PerformanceTracker,
    adaptive_grid_step,
    estimate_transform_lod,
    normalize_performance_mode,
)
from monkez_pyqt6.monkez_widgets import MonkezCanva
from monkez_pyqt6.monkez_widgets._canva_export import export_render_state


class CanvasPerformancePolicyTests(unittest.TestCase):
    def test_transform_lod_and_mode_validation_are_deterministic(self) -> None:
        self.assertEqual(1.0, estimate_transform_lod(1, 0, 0, 1))
        self.assertEqual(0.25, estimate_transform_lod(0.25, 0, 0, 0.25))
        self.assertEqual("quality", normalize_performance_mode(" Quality "))
        with self.assertRaisesRegex(ValueError, "Unsupported canvas performance"):
            normalize_performance_mode("turbo")
        self.assertEqual(20.0, adaptive_grid_step(20, 1.0))
        self.assertEqual(20.0, adaptive_grid_step(20, 0.5))
        self.assertEqual(80.0, adaptive_grid_step(20, 0.2))

    def test_auto_policy_scales_at_100_1000_and_10000_objects(self) -> None:
        policy = CanvasPerformancePolicy()
        self.assertEqual("full", policy.resolve(1.0, 100).tier)
        self.assertEqual("compact", policy.resolve(0.5, 1_000).tier)
        self.assertEqual("overview", policy.resolve(0.3, 10_000).tier)
        self.assertEqual("full", policy.resolve(0.1, 10_000, selected=True).tier)

    def test_packets_remain_visible_when_decorative_effects_are_culled(self) -> None:
        policy = CanvasPerformancePolicy()
        decorative = policy.resolve(0.1, 10_000)
        critical = policy.resolve(0.1, 10_000, has_packets=True)
        self.assertFalse(decorative.draw_effects)
        self.assertTrue(critical.draw_effects)
        self.assertFalse(critical.draw_connector_decorations)

    def test_quality_and_speed_modes_are_explicit_overrides(self) -> None:
        quality = CanvasPerformancePolicy(mode="quality")
        speed = CanvasPerformancePolicy(mode="speed")
        self.assertEqual("full", quality.resolve(0.01, 100_000).tier)
        self.assertEqual("overview", speed.resolve(4.0, 10).tier)
        self.assertEqual("compact", speed.resolve(4.0, 10, selected=True).tier)

    def test_tracker_retains_bounded_frame_and_lod_metrics(self) -> None:
        tracker = PerformanceTracker(history_limit=8)
        for index in range(12):
            tracker.begin_frame()
            tracker.record_paint("element", "overview")
            if index % 2:
                tracker.record_paint("connector", "compact")
            tracker.finish_frame(index + 1, object_count=10_000, lod=0.2)
        snapshot = tracker.snapshot()
        self.assertEqual(12, snapshot["frameCount"])
        self.assertEqual(8, snapshot["sampleCount"])
        self.assertEqual(12.0, snapshot["maxFrameMs"])
        self.assertEqual(2, snapshot["paintedObjects"])
        self.assertEqual({"overview": 1, "compact": 1}, snapshot["tierCounts"])


class CanvasPerformanceWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_canvas_lod_metrics_and_view_controls_use_public_mode(self) -> None:
        canvas = MonkezCanva()
        canvas.resize(800, 520)
        for row in range(4):
            for column in range(5):
                canvas.addNode(
                    f"N {row}:{column}",
                    column * 150 - 300,
                    row * 100 - 150,
                )
        canvas.show()
        canvas.view().resetTransform()
        canvas.view().scale(0.2, 0.2)
        canvas.view().centerOn(0, 0)
        self.app.processEvents()
        self.assertFalse(canvas.view().viewport().grab().isNull())
        self.app.processEvents()

        stats = canvas.performanceStats()
        self.assertEqual("auto", stats["mode"])
        self.assertGreater(stats["frameCount"], 0)
        self.assertGreater(stats["paintedObjects"], 0)
        self.assertGreater(stats["tierCounts"].get("overview", 0), 0)
        self.assertEqual(
            "full",
            canvas.renderProfileForLod(
                0.1, object_count=10_000, selected=True
            )["tier"],
        )

        changes = []
        canvas.performanceModeChanged.connect(changes.append)
        canvas.setEditMode(True)
        toolbox = canvas._toolbox
        toolbox._tabs.setCurrentIndex(3)
        canvas.setPerformanceMode("speed")
        self.app.processEvents()
        self.assertEqual(["speed"], changes)
        self.assertEqual(
            "speed", toolbox._performance_mode_combo.currentData()
        )
        self.assertEqual("compact", canvas.renderProfileForLod(4, selected=True)["tier"])

        canvas.setEditMode(False)
        canvas.close()
        canvas.deleteLater()

    def test_large_document_attach_coalesces_render_notifications(self) -> None:
        canvas = MonkezCanva()
        elements = [
            {
                "id": f"node-{index}",
                "type": "node",
                "text": f"Node {index}",
                "x": float(index % 25) * 140.0,
                "y": float(index // 25) * 90.0,
            }
            for index in range(250)
        ]
        document = CanvasDocument.from_dict(
            {
                "format": "monkez-canva",
                "version": 1,
                "scene": {"width": 4_000, "height": 2_000},
                "elements": elements,
                "connectors": [],
                "groups": [],
            }
        )
        added = []
        changed = []
        canvas.elementAdded.connect(added.append)
        canvas.documentChanged.connect(lambda: changed.append(True))
        canvas.setDocumentModel(document)
        self.assertEqual(250, len(canvas.elements()))
        self.assertEqual([], added)
        self.assertEqual([True], changed)
        self.assertFalse(canvas._bulk_rendering)
        self.assertFalse(canvas._restoring)
        canvas.close()
        canvas.deleteLater()

    def test_export_transaction_forces_quality_and_restores_mode(self) -> None:
        canvas = MonkezCanva()
        canvas.addNode("Export me", 0, 0)
        canvas.setPerformanceMode("speed")
        self.assertFalse(canvas._force_quality_render)
        with export_render_state(canvas, "scene", transparent=False):
            self.assertTrue(canvas._force_quality_render)
            self.assertEqual("speed", canvas.performanceMode())
        self.assertFalse(canvas._force_quality_render)
        self.assertEqual("speed", canvas.performanceMode())
        canvas.close()
        canvas.deleteLater()


if __name__ == "__main__":
    unittest.main()
