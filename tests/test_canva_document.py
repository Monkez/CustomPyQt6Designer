from __future__ import annotations

import json
import unittest
from importlib.resources import files

from monkez_pyqt6.monkez_canva import (
    DOCUMENT_JSON_SCHEMA,
    CanvasDocument,
    ElementModel,
    migrate_document,
)


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
    def test_public_schema_and_newer_document_read_only_contract(self) -> None:
        payload = document_payload()
        payload["version"] = 7
        payload["futureMetadata"] = {"preserved": True}

        with self.assertRaisesRegex(ValueError, "newer than supported"):
            CanvasDocument.from_dict(payload)
        document = CanvasDocument.from_dict(payload, allow_newer=True)

        self.assertTrue(document.is_read_only)
        self.assertEqual(7, document.source_version)
        self.assertEqual(7, document.to_dict()["version"])
        self.assertEqual({"preserved": True}, document.to_dict()["futureMetadata"])
        with self.assertRaises(PermissionError):
            document.add_element({"id": "blocked", "type": "text"})
        with self.assertRaises(PermissionError):
            document.reconcile(document.to_dict())
        self.assertEqual("object", DOCUMENT_JSON_SCHEMA["type"])
        self.assertTrue(migrate_document(payload, allow_newer=True).read_only)
        packaged_schema = json.loads(
            files("monkez_pyqt6.monkez_canva")
            .joinpath("schemas/monkez-canva-document-v1.schema.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(DOCUMENT_JSON_SCHEMA, packaged_schema)

    def test_declarative_bindings_are_portable_and_structurally_validated(self) -> None:
        payload = document_payload()
        payload["elements"][0]["bindings"] = [
            {
                "id": "source-label",
                "source": "telemetry.status",
                "target": "text",
                "transforms": [{"op": "get", "path": "label"}],
                "format": "State: {value}",
                "debounce": 0.05,
                "staleAfter": 5,
                "fallback": "Offline",
            }
        ]

        document = CanvasDocument.from_dict(payload)

        self.assertEqual(
            payload["elements"][0]["bindings"],
            document.to_dict()["elements"][0]["bindings"],
        )
        binding_schema = DOCUMENT_JSON_SCHEMA["$defs"]["binding"]
        self.assertEqual(["id", "source", "target"], binding_schema["required"])
        self.assertEqual(
            "#/$defs/binding",
            DOCUMENT_JSON_SCHEMA["properties"]["elements"]["items"]
            ["properties"]["bindings"]["items"]["$ref"],
        )

        duplicate = document_payload()
        duplicate["elements"][0]["bindings"] = [
            {"id": "duplicate", "source": "a", "target": "text"},
            {"id": "duplicate", "source": "b", "target": "color"},
        ]
        with self.assertRaisesRegex(ValueError, "Duplicate data-binding ID"):
            CanvasDocument.from_dict(duplicate)

        invalid = document_payload()
        invalid["elements"][0]["bindings"] = [
            {"id": "bad", "source": "telemetry", "target": "unsupported"}
        ]
        with self.assertRaisesRegex(ValueError, "Unsupported data-binding target"):
            CanvasDocument.from_dict(invalid)

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
        document.add_group({"id": "pipeline", "members": ["source", "target"]})
        events = []
        document.subscribe(events.append)

        renamed = document.rename_element("source", "producer")

        self.assertEqual("producer", document.connector("edge").source)
        self.assertEqual(("producer", "target"), document.group("pipeline").members)
        self.assertEqual({2}, {event.revision for event in renamed})
        self.assertEqual(1, len({event.operation_id for event in renamed}))
        removed = document.remove_element("target")
        self.assertIsNone(document.connector("edge"))
        self.assertEqual(("producer",), document.group("pipeline").members)
        self.assertEqual(
            ["connector.removed", "group.updated", "element.removed"],
            [event.action for event in removed],
        )
        self.assertEqual(3, document.revision)

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

    def test_connector_group_and_resource_lifecycle_operations(self) -> None:
        document = CanvasDocument.from_dict(document_payload())
        document.add_group({"id": "pipeline", "members": ["source", "target"]})
        document.add_resource({"id": "icon", "kind": "image", "uri": "old.png"})

        connector_event = document.rename_connector("edge", "signal")
        group_event = document.update_group("pipeline", {"label": "Main pipeline"})
        resource_event = document.update_resource("icon", {"uri": "assets/icon.png"})

        self.assertEqual("connector.renamed", connector_event.action)
        self.assertIsNone(document.connector("edge"))
        self.assertEqual("source", document.connector("signal").source)
        self.assertEqual("Main pipeline", document.group("pipeline").properties["label"])
        self.assertEqual("assets/icon.png", document.resource("icon").uri)
        self.assertEqual("group.updated", group_event.action)
        self.assertEqual("resource.updated", resource_event.action)
        self.assertEqual("group.removed", document.remove_group("pipeline").action)
        self.assertEqual("resource.removed", document.remove_resource("icon").action)


if __name__ == "__main__":
    unittest.main()
