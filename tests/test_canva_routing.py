from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    deduplicate_points,
    orthogonal_points,
    parallel_lane_offset,
)


class CanvasRoutingTests(unittest.TestCase):
    def test_parallel_lanes_are_stable_and_symmetric(self) -> None:
        siblings = ("a", "b", "c", "d")
        self.assertEqual((-30.0, -10.0, 10.0, 30.0), tuple(
            parallel_lane_offset(connector_id, siblings, 20)
            for connector_id in siblings
        ))
        self.assertEqual(0.0, parallel_lane_offset("only", ("only",), 20))

    def test_orthogonal_route_stays_axis_aligned_through_waypoints(self) -> None:
        points = orthogonal_points((0, 0), (160, 100), ((70, 40), (120, 80)))
        self.assertEqual((0, 0), points[0])
        self.assertEqual((160, 100), points[-1])
        for first, second in zip(points, points[1:]):
            self.assertTrue(first[0] == second[0] or first[1] == second[1])

    def test_route_helpers_remove_duplicates_and_offset_default_elbow(self) -> None:
        self.assertEqual(((1.0, 2.0), (3.0, 4.0)), deduplicate_points(((1, 2), (1, 2), (3, 4))))
        self.assertEqual(
            ((0, 0), (60.0, 0), (60.0, 60), (100, 60)),
            orthogonal_points((0, 0), (100, 60), lane_offset=10),
        )


if __name__ == "__main__":
    unittest.main()
