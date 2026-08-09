from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import SnapRect, normalize_snap_targets, snap_rect


class CanvasSnappingTests(unittest.TestCase):
    def test_normalizes_targets_in_stable_priority_order(self) -> None:
        self.assertEqual(
            ("grid", "centers", "ports"),
            normalize_snap_targets(("PORTS", "grid", "centers", "ports", "unknown")),
        )

    def test_snaps_nearest_edges_and_returns_guides(self) -> None:
        result = snap_rect(
            SnapRect(96, 34, 40, 30),
            (SnapRect(140, 60, 50, 40),),
            targets=("edges",),
            threshold=6,
        )
        self.assertEqual((100, 30), (result.x, result.y))
        self.assertEqual({"vertical", "horizontal"}, {guide.axis for guide in result.guides})

    def test_centers_take_effect_without_edge_target(self) -> None:
        result = snap_rect(
            SnapRect(52, 51, 40, 20),
            (SnapRect(0, 0, 140, 120),),
            targets=("centers",),
            threshold=3,
        )
        self.assertEqual((50, 50), (result.x, result.y))
        self.assertTrue(all(guide.target == "center" for guide in result.guides))

    def test_grid_respects_threshold_and_port_alignment(self) -> None:
        near = snap_rect(SnapRect(38, 61, 20, 20), targets=("grid",), grid_size=20, threshold=3)
        far = snap_rect(SnapRect(34, 66, 20, 20), targets=("grid",), grid_size=20, threshold=3)
        ports = snap_rect(
            SnapRect(10, 10, 20, 20), targets=("ports",), threshold=5,
            moving_ports=((29, 20),), candidate_ports=((32, 18),),
        )
        self.assertEqual((40, 60), (near.x, near.y))
        self.assertEqual((34, 66), (far.x, far.y))
        self.assertEqual((13, 8), (ports.x, ports.y))


if __name__ == "__main__":
    unittest.main()
