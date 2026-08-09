from __future__ import annotations

import math
import unittest

from monkez_pyqt6.monkez_canva import LayoutOptions, layout_graph


def nodes(*ids: str) -> list[dict]:
    return [
        {"id": node_id, "x": index * 15, "y": index * 9, "width": 100, "height": 60}
        for index, node_id in enumerate(ids)
    ]


class AutoLayoutTests(unittest.TestCase):
    def test_layered_layout_handles_cycles_and_is_deterministic(self) -> None:
        graph_nodes = nodes("source", "a", "b", "sink")
        edges = [
            {"source": "source", "target": "a"},
            {"source": "a", "target": "b"},
            {"source": "b", "target": "a"},
            {"source": "b", "target": "sink"},
        ]

        first = layout_graph(graph_nodes, edges, strategy="layered", preserve_center=False)
        second = layout_graph(graph_nodes, edges, strategy="layered", preserve_center=False)

        self.assertEqual(first.positions, second.positions)
        self.assertEqual(3, first.layer_count)
        self.assertLess(first.positions["source"][0], first.positions["a"][0])
        self.assertEqual(first.positions["a"][0], first.positions["b"][0])
        self.assertLess(first.positions["b"][0], first.positions["sink"][0])

    def test_layered_direction_and_component_packing(self) -> None:
        result = layout_graph(
            nodes("a", "b", "c", "d"),
            [{"source": "a", "target": "b"}, {"source": "c", "target": "d"}],
            strategy="layered",
            direction="down",
            component_spacing=200,
            preserve_center=False,
        )

        self.assertEqual(2, result.component_count)
        self.assertLess(result.positions["a"][1], result.positions["b"][1])
        first_right = max(result.positions[key][0] + 100 for key in ("a", "b"))
        second_left = min(result.positions[key][0] for key in ("c", "d"))
        self.assertGreaterEqual(second_left - first_right, 200)

    def test_tree_centers_parent_over_children(self) -> None:
        result = layout_graph(
            nodes("root", "left", "right", "leaf"),
            [
                {"source": "root", "target": "left"},
                {"source": "root", "target": "right"},
                {"source": "left", "target": "leaf"},
            ],
            strategy="tree",
            preserve_center=False,
        )

        root_center = result.positions["root"][1] + 30
        child_center = (
            result.positions["left"][1] + result.positions["right"][1] + 60
        ) / 2
        self.assertAlmostEqual(root_center, child_center)
        self.assertLess(result.positions["root"][0], result.positions["left"][0])
        self.assertLess(result.positions["left"][0], result.positions["leaf"][0])

    def test_radial_uses_graph_distance_rings(self) -> None:
        result = layout_graph(
            nodes("root", "a", "b", "leaf"),
            [
                {"source": "root", "target": "a"},
                {"source": "root", "target": "b"},
                {"source": "a", "target": "leaf"},
            ],
            strategy="radial",
            preserve_center=False,
        )
        center = (
            result.positions["root"][0] + 50,
            result.positions["root"][1] + 30,
        )
        distance_a = math.hypot(
            result.positions["a"][0] + 50 - center[0],
            result.positions["a"][1] + 30 - center[1],
        )
        distance_leaf = math.hypot(
            result.positions["leaf"][0] + 50 - center[0],
            result.positions["leaf"][1] + 30 - center[1],
        )
        self.assertEqual(3, result.layer_count)
        self.assertGreater(distance_leaf, distance_a)

    def test_force_is_deterministic_separates_nodes_and_preserves_lock(self) -> None:
        graph_nodes = nodes("locked", "a", "b", "c")
        graph_nodes[0].update({"x": 420, "y": 180, "locked": True})
        edges = [
            {"source": "locked", "target": "a"},
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "locked"},
        ]
        options = LayoutOptions(strategy="force", iterations=80, node_spacing=20)

        first = layout_graph(graph_nodes, edges, options=options)
        second = layout_graph(graph_nodes, edges, options=options)

        self.assertEqual(first.positions, second.positions)
        self.assertEqual((420, 180), first.positions["locked"])
        centers = [
            (first.positions[node_id][0] + 50, first.positions[node_id][1] + 30)
            for node_id in ("locked", "a", "b", "c")
        ]
        self.assertTrue(
            all(
                math.hypot(x1 - x2, y1 - y2) > 20
                for index, (x1, y1) in enumerate(centers)
                for x2, y2 in centers[index + 1:]
            )
        )

    def test_preserve_center_keeps_unlocked_graph_center(self) -> None:
        graph_nodes = nodes("a", "b", "c")
        old_left = min(node["x"] for node in graph_nodes)
        old_right = max(node["x"] + node["width"] for node in graph_nodes)
        old_top = min(node["y"] for node in graph_nodes)
        old_bottom = max(node["y"] + node["height"] for node in graph_nodes)
        result = layout_graph(
            graph_nodes,
            [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
            strategy="tree",
        )
        left, top, width, height = result.bounds
        self.assertAlmostEqual((old_left + old_right) / 2, left + width / 2)
        self.assertAlmostEqual((old_top + old_bottom) / 2, top + height / 2)


if __name__ == "__main__":
    unittest.main()
