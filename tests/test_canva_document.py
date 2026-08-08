from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import CanvasDocument, ElementModel


def document_payload() -> dict:
    return {
        "format": "monkez-canva",
        "version": 1,
        "scene": {"width": 1200, "height": 800, "gridVisible": True},
        "elements": [
            {
                "id": "source",
                "type": "node",
                "text": "Source",
                "ports": [{"id": "out", "mode": "output"}],
            },
            {
                "id": "target",
                "type": "node",
                "text": "Target",
                "ports": [{"id": "in", "mode": "input"}],
            },
        ],
        "connectors": [
            {
                "id": "edge",
                "type": "connector",
                "source": "source",
                "target": "target",
                "sourcePort": "out",
                "targetPort": "in",
            }
        ],
        "application": {"name": "document-test"},
    }


class CanvasDocumentTests(unittest.TestCase):
    def test_version_one_load_is_json_safe_and_normalizes_legacy_lines(self) -> None:
        payload = document_payload()
        payload["elements"].extend(
            [
                {"id": "old-arrow", "type": "arrow", "x": 10},
                {"id": "old-polyline", "type": "polyline", "points": [[0, 0], [10, 20]]},
            ]
        )

        document = CanvasDocument.from_dict(payload)

        self.assertEqual("line", document.element("old-arrow").type)
        self.assertTrue(document.element("old-arrow").properties["arrowEnd"])
        self.assertEqual("line", document.element("old-polyline").type)
        self.assertEqual({"name": "document-test"}, document.to_dict()["application"])
        self.assertEqual("right", document.element("source").ports[0].side)
        with self.assertRaises(TypeError):
            document.element("source").properties["text"] = "mutated"
        with self.assertRaises(TypeError):
            document.element("source").properties["ports"][0]["id"] = "mutated"

    def test_reconcile_emits_granular_events_in_one_revision(self) -> None:
        document = CanvasDocument.from_dict(document_payload())
        received = []
        document.subscribe(received.append)
        updated = document_payload()
        updated["elements"][0]["text"] = "Updated Source"
        updated["elements"].append({"id": "note", "type": "text", "text": "Ready"})
        updated["connectors"] = []

        events = document.reconcile(updated, origin="unit-test")

        self.assertEqual(
            ["element.updated", "element.added", "connector.removed"],
            [event.action for event in events],
        )
        self.assertEqual({1}, {event.revision for event in events})
        self.assertEqual(1, len({event.operation_id for event in events}))
        self.assertTrue(all(event.origin == "unit-test" for event in received))
        self.assertEqual("Updated Source", document.element("source").properties["text"])

    def test_direct_operations_validate_ids_ports_and_json(self) -> None:
        document = CanvasDocument.empty()
        document.add_element(
            {"id": "source", "type": "node", "ports": [{"id": "out", "mode": "output"}]}
        )
        document.add_element(
            {"id": "target", "type": "node", "ports": [{"id": "in", "mode": "input"}]}
        )
        document.add_connector(
            {
                "id": "edge",
                "source": "source",
                "target": "target",
                "sourcePort": "out",
                "targetPort": "in",
            }
        )

        with self.assertRaisesRegex(ValueError, "Duplicate"):
            document.add_element({"id": "edge", "type": "text"})
        with self.assertRaisesRegex(ValueError, "missing source port"):
            document.update_connector("edge", {"sourcePort": "missing"})
        with self.assertRaisesRegex(TypeError, "finite JSON"):
            ElementModel.from_dict({"id": "bad", "type": "text", "metadata": {"value": object()}})
        with self.assertRaisesRegex(ValueError, "missing members"):
            document.add_group({"id": "group", "members": ["absent"]})

    def test_rename_and_remove_are_atomic_and_update_connectors(self) -> None:
        document = CanvasDocument.from_dict(document_payload())
        events = []
        document.subscribe(events.append)

        renamed = document.rename_element("source", "producer")

        self.assertEqual("producer", document.connector("edge").source)
        self.assertEqual({1}, {event.revision for event in renamed})
        self.assertEqual(1, len({event.operation_id for event in renamed}))
        removed = document.remove_element("target")
        self.assertIsNone(document.connector("edge"))
        self.assertEqual(["connector.removed", "element.removed"], [event.action for event in removed])
        self.assertEqual(2, document.revision)

    def test_groups_resources_and_duplicate_input_records_round_trip(self) -> None:
        document = CanvasDocument.from_dict(document_payload())
        document.add_group({"id": "pipeline", "members": ["source", "target"], "label": "Pipeline"})
        document.add_resource({"id": "icon", "kind": "image", "uri": "assets/icon.png", "checksum": "abc"})

        result = document.to_dict()
        self.assertEqual("pipeline", result["groups"][0]["id"])
        self.assertEqual("assets/icon.png", result["resources"][0]["uri"])

        duplicated = document_payload()
        duplicated["elements"].append(dict(duplicated["elements"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate element IDs"):
            CanvasDocument.from_dict(duplicated)


if __name__ == "__main__":
    unittest.main()
