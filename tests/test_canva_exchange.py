from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    DOCUMENT_VERSION,
    CanvasDocument,
    export_dot,
    export_mermaid,
    import_dot,
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

    def test_dot_round_trip_preserves_ids_geometry_ports_and_arrows(self) -> None:
        imported = import_dot(export_dot(sample_document()))

        self.assertEqual("MonkezCanva", imported.name)
        self.assertTrue(imported.directed)
        self.assertEqual(
            {'source "A"', "decision", "database"},
            {record["id"] for record in imported.elements},
        )
        source = next(record for record in imported.elements if record["id"] == 'source "A"')
        self.assertEqual("software_service", source["type"])
        self.assertAlmostEqual(10, source["x"])
        self.assertAlmostEqual(144, source["width"], delta=0.1)
        request = next(record for record in imported.connectors if record["id"] == "request-edge")
        self.assertEqual("out", request["sourcePort"])
        self.assertEqual("in", request["targetPort"])
        self.assertFalse(request["arrowStart"])
        self.assertTrue(request["arrowEnd"])
        save = next(record for record in imported.connectors if record["id"] == "save-edge")
        self.assertTrue(save["arrowStart"])
        self.assertTrue(save["arrowEnd"])

    def test_generic_dot_defaults_chain_ports_and_layout_are_supported(self) -> None:
        source = r'''
            // a conservative external DOT document
            digraph Pipeline {
                rankdir=TB;
                node [shape=ellipse, color="#334155", fillcolor="#eef2ff"];
                source:out -> transform:in -> sink [style=dashed, label="data"];
                transform [shape=diamond, label="Transform"];
            }
        '''
        first = import_dot(source)
        second = import_dot(source)

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual({"source", "transform", "sink"}, {record["id"] for record in first.elements})
        self.assertNotIn("rankdir", {record["id"] for record in first.elements})
        transform = next(record for record in first.elements if record["id"] == "transform")
        self.assertEqual("diamond", transform["type"])
        self.assertEqual("Transform", transform["text"])
        self.assertEqual(2, len(first.connectors))
        self.assertEqual("out", first.connectors[0]["sourcePort"])
        self.assertEqual("in", first.connectors[0]["targetPort"])
        self.assertEqual("dash", first.connectors[0]["lineStyle"])
        self.assertLess(
            next(record["y"] for record in first.elements if record["id"] == "source"),
            next(record["y"] for record in first.elements if record["id"] == "transform"),
        )

    def test_undirected_dot_has_no_arrowheads_and_unique_edge_ids(self) -> None:
        imported = import_dot('graph G { a -- b [id="a"]; a -- b [id="a"]; }')

        self.assertFalse(imported.directed)
        self.assertEqual(2, len(imported.connectors))
        self.assertEqual(2, len({record["id"] for record in imported.connectors}))
        self.assertTrue(all(not record["arrowStart"] for record in imported.connectors))
        self.assertTrue(all(not record["arrowEnd"] for record in imported.connectors))

    def test_dot_parser_rejects_unsupported_or_malformed_constructs(self) -> None:
        cases = (
            ("digraph G { subgraph cluster_a { a; } }", "subgraphs"),
            ("digraph G { a [label=<b>]; }", "HTML-like"),
            ('digraph G { a [label="unterminated]; }', "Unterminated"),
            ("not_a_graph { a; }", "graph or digraph"),
            ("digraph G { a -- b; }", "digraph edges must use '->'"),
            ("graph G { a -> b; }", "graph edges must use '--'"),
        )
        for source, message in cases:
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, message):
                import_dot(source)

    def test_dot_import_clamps_external_geometry_and_stroke_values(self) -> None:
        imported = import_dot(
            'digraph G { a [width="999999", height="999999"]; '
            'a -> b [penwidth="999999"]; }'
        )

        self.assertEqual(10_000.0, imported.elements[0]["width"])
        self.assertEqual(10_000.0, imported.elements[0]["height"])
        self.assertEqual(50.0, imported.connectors[0]["lineWidth"])


if __name__ == "__main__":
    unittest.main()
