from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    CLIPBOARD_FORMAT,
    build_selection_payload,
    decode_selection_payload,
    remap_selection_payload,
)


class CanvasClipboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = {
            "format": "monkez-canva",
            "version": 1,
            "scene": {},
            "elements": [
                {"id": "a", "type": "node", "x": 10, "y": 20},
                {"id": "b", "type": "node", "x": 100, "y": 80},
                {"id": "outside", "type": "node", "x": 500, "y": 500},
            ],
            "connectors": [
                {"id": "edge", "source": "a", "target": "b", "waypoints": [[40, 50]]},
                {"id": "parallel", "source": "a", "target": "b"},
                {"id": "external", "source": "b", "target": "outside"},
            ],
        }

    def test_build_selection_includes_only_internal_connectors(self) -> None:
        payload = build_selection_payload(self.document, ["a", "b"])
        self.assertEqual(CLIPBOARD_FORMAT, payload["format"])
        self.assertEqual(["a", "b"], [record["id"] for record in payload["elements"]])
        self.assertEqual(
            ["edge", "parallel"],
            [record["id"] for record in payload["connectors"]],
        )

    def test_selected_connector_brings_endpoint_dependencies(self) -> None:
        payload = build_selection_payload(self.document, ["edge"])
        self.assertEqual({"a", "b"}, {record["id"] for record in payload["elements"]})
        self.assertEqual(["edge"], [record["id"] for record in payload["connectors"]])

    def test_decode_rejects_dangling_edges_and_remap_offsets_graph(self) -> None:
        payload = build_selection_payload(self.document, ["a", "b"])
        elements, connectors, id_map = remap_selection_payload(
            payload, {"a-copy"}, offset=(30, 40)
        )
        self.assertEqual("a-copy-2", id_map["a"])
        self.assertEqual(40, elements[0]["x"])
        self.assertEqual(60, elements[0]["y"])
        self.assertEqual(id_map["a"], connectors[0]["source"])
        self.assertEqual(id_map["b"], connectors[0]["target"])
        self.assertEqual([[70.0, 90.0]], connectors[0]["waypoints"])

        payload["connectors"][0]["target"] = "missing"
        with self.assertRaisesRegex(ValueError, "endpoints"):
            decode_selection_payload(payload)


if __name__ == "__main__":
    unittest.main()
