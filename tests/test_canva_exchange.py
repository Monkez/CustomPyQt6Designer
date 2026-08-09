from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    DOCUMENT_VERSION,
    CanvasDocument,
    export_dot,
    export_mermaid,
    select_graph,
)


def sample_document() -> CanvasDocument:
    return CanvasDocument.from_dict(
        {
            "format": "monkez-canva",
            "version": DOCUMENT_VERSION,
            "scene": {},
            "elements": [
                {
                    "id": 'source "A"',
                    "type": "software_service",
                    "text": "Receive\nrequest",
                    "x": 10,
                    "y": 20,
                    "width": 144,
                    "height": 72,
                    "ports": [{"id": "out", "mode": "output", "side": "right"}],
                },
                {
                    "id": "decision",
                    "type": "software_decision",
                    "text": "Valid?",
                    "x": 240,
                    "y": 20,
                    "width": 100,
                    "height": 100,
                    "ports": [
                        {"id": "in", "mode": "input", "side": "left"},
                        {"id": "out", "mode": "output", "side": "right"},
                    ],
                },
                {
                    "id": "database",
                    "type": "software_database",
                    "text": "Orders",
                    "x": 440,
                    "y": 20,
                    "width": 120,
                    "height": 90,
                    "ports": [{"id": "in", "mode": "input", "side": "left"}],
                },
            ],
            "connectors": [
                {
                    "id": "request-edge",
                    "type": "connector",
                    "source": 'source "A"',
                    "target": "decision",
                    "label": "validate",
                    "sourcePort": "out",
                    "targetPort": "in",
                    "arrowEnd": True,
                },
                {
                    "id": "save-edge",
                    "type": "connector",
                    "source": "decision",
                    "target": "database",
                    "sourcePort": "out",
                    "targetPort": "in",
                    "arrowStart": True,
                    "arrowEnd": True,
                },
            ],
            "groups": [
                {
                    "id": "inner",
                    "kind": "frame",
                    "members": ["decision"],
                },
                {
                    "id": "outer",
                    "kind": "subflow",
                    "members": ['source "A"', "inner"],
                },
            ],
        }
    )


class CanvasExchangeTests(unittest.TestCase):
    def test_selection_expands_nested_groups_and_internal_connectors(self) -> None:
        selected = select_graph(sample_document(), ["outer"])

        self.assertEqual({'source "A"', "decision"}, {item["id"] for item in selected.elements})
        self.assertEqual({"request-edge"}, {item["id"] for item in selected.connectors})
        self.assertTrue({"outer", "inner"}.issubset(selected.object_ids))

    def test_dot_export_is_deterministic_escaped_and_positioned(self) -> None:
        first = export_dot(sample_document(), graph_name='Flow "demo"')
        second = export_dot(sample_document(), graph_name='Flow "demo"')

        self.assertEqual(first, second)
        self.assertIn('digraph "Flow \\"demo\\""', first)
        self.assertIn('"source \\"A\\""', first)
        self.assertIn('label="Receive\\nrequest"', first)
        self.assertIn('shape="diamond"', first)
        self.assertIn('shape="cylinder"', first)
        self.assertIn('dir="both"', first)
        self.assertIn('pos="10,-20!"', first)

    def test_mermaid_export_uses_safe_aliases_shapes_labels_and_direction(self) -> None:
        output = export_mermaid(sample_document(), direction="TB")

        self.assertTrue(output.startswith("flowchart TB\n"))
        self.assertIn('n0["Receive<br/>request"]', output)
        self.assertIn('n1{"Valid?"}', output)
        self.assertIn('n2[("Orders")]', output)
        self.assertIn('n0 -->|"validate"| n1', output)
        self.assertIn("n1 <--> n2", output)
        self.assertIn('%% n0 = source "A"', output)
        with self.assertRaisesRegex(ValueError, "direction"):
            export_mermaid(sample_document(), direction="diagonal")

    def test_unknown_scope_id_is_actionable(self) -> None:
        with self.assertRaisesRegex(KeyError, "missing"):
            select_graph(sample_document(), ["missing"])


if __name__ == "__main__":
    unittest.main()
