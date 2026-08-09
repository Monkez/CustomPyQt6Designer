from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    deduplicate_points,
    obstacle_avoiding_route,
    orthogonal_points,
    parallel_lane_offset,
    segment_intersection,
    simplify_collinear,
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

    def test_obstacle_route_is_axis_aligned_and_avoids_expanded_rectangle(self) -> None:
        points = obstacle_avoiding_route(
            (0, 50),
            (300, 50),
            ((120, 0, 60, 100),),
            clearance=10,
        )
        self.assertEqual((0.0, 50.0), points[0])
        self.assertEqual((300.0, 50.0), points[-1])
        self.assertTrue(any(point[1] in (-10.0, 110.0) for point in points))
        for first, second in zip(points, points[1:]):
            self.assertTrue(first[0] == second[0] or first[1] == second[1])
            if first[1] == second[1]:
                self.assertFalse(-10.0 < first[1] < 110.0 and min(first[0], second[0]) < 190.0 and max(first[0], second[0]) > 110.0)
            else:
                self.assertFalse(110.0 < first[0] < 190.0 and min(first[1], second[1]) < 110.0 and max(first[1], second[1]) > -10.0)

    def test_obstacle_route_without_obstacles_is_simple_and_deterministic(self) -> None:
        expected = ((0.0, 20.0), (0.0, 80.0), (90.0, 80.0))
        self.assertEqual(expected, obstacle_avoiding_route((0, 20), (90, 80)))
        self.assertEqual(
            ((0.0, 0.0), (40.0, 0.0), (40.0, 30.0)),
            simplify_collinear(((0, 0), (20, 0), (40, 0), (40, 30))),
        )

    def test_segment_intersection_excludes_endpoints_and_parallel_lines(self) -> None:
        self.assertEqual(
            (50.0, 50.0),
            segment_intersection((0, 50), (100, 50), (50, 0), (50, 100)),
        )
        self.assertIsNone(segment_intersection((0, 0), (100, 0), (100, 0), (100, 50)))
        self.assertIsNone(segment_intersection((0, 0), (100, 0), (0, 10), (100, 10)))


if __name__ == "__main__":
    unittest.main()
