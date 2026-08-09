from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    CanvasDocument,
    evaluate_directed_ports,
    evaluate_port_pair,
    infer_data_type,
    normalize_port_record,
    validate_port_value,
)


class TypedPortContractTests(unittest.TestCase):
    def test_normalization_aliases_defaults_and_extensions(self) -> None:
        port = normalize_port_record(
            {
                "id": "temperature",
                "mode": "in",
                "dataType": "Number",
                "unit": " °C ",
                "acceptedTypes": "integer, float, integer",
                "maxConnections": 1,
                "vendorRole": "telemetry",
            }
        )

        self.assertEqual("input", port["mode"])
        self.assertEqual("left", port["side"])
        self.assertEqual("float", port["dataType"])
        self.assertEqual("°C", port["unit"])
        self.assertEqual(["int", "float"], port["acceptedTypes"])
        self.assertEqual("telemetry", port["vendorRole"])
        self.assertFalse(port["required"])
        with self.assertRaisesRegex(TypeError, "default value type"):
            normalize_port_record(
                {"id": "bad-default", "dataType": "bool", "defaultValue": "yes"}
            )

    def test_direction_type_unit_conversion_and_cardinality(self) -> None:
        output = {
            "id": "voltage",
            "mode": "output",
            "dataType": "float",
            "unit": "V",
            "maxConnections": 2,
            "convertsTo": ["str"],
        }
        input_port = {
            "id": "reading",
            "mode": "input",
            "dataType": "str",
            "unit": "mV",
            "acceptedUnits": ["V"],
        }

        result = evaluate_port_pair(input_port, output)
        self.assertTrue(result.compatible)
        self.assertFalse(result.source_is_first)
        self.assertTrue(result.conversion)
        self.assertIn("conversion", result.reason)

        full = evaluate_directed_ports(output, input_port, source_connections=2)
        self.assertFalse(full.compatible)
        self.assertIn("2-connection limit", full.reason)

        incompatible = evaluate_directed_ports(
            {**output, "convertsTo": []}, {**input_port, "acceptedUnits": []}
        )
        self.assertFalse(incompatible.compatible)
        self.assertIn("Type", incompatible.reason)

    def test_runtime_value_validation_is_transient_and_predictable(self) -> None:
        required = {"id": "count", "mode": "input", "dataType": "float", "required": True}
        self.assertEqual("bool", infer_data_type(True))
        self.assertEqual("int", infer_data_type(4))
        self.assertTrue(validate_port_value(required, 4).valid)
        self.assertFalse(validate_port_value(required, None).valid)
        self.assertFalse(validate_port_value(required, "4").valid)
        self.assertTrue(validate_port_value({**required, "defaultValue": 0}, None).valid)

    def test_document_enforces_typed_ports_and_rolls_back_invalid_edits(self) -> None:
        document = CanvasDocument.empty()
        document.add_element(
            {
                "id": "source",
                "type": "node",
                "ports": [{
                    "id": "out", "mode": "output", "dataType": "float",
                    "unit": "V", "maxConnections": 1,
                }],
            }
        )
        document.add_element(
            {
                "id": "target",
                "type": "node",
                "ports": [{
                    "id": "in", "mode": "input", "dataType": "float", "unit": "V",
                }],
            }
        )
        document.add_connector(
            {
                "id": "edge", "source": "source", "target": "target",
                "sourcePort": "out", "targetPort": "in",
            }
        )
        document.update_connector("edge", {"label": "still valid"})

        with self.assertRaisesRegex(ValueError, "connection limit"):
            document.add_connector(
                {
                    "id": "second", "source": "source", "target": "target",
                    "sourcePort": "out", "targetPort": "in",
                }
            )
        with self.assertRaisesRegex(ValueError, "Type"):
            document.update_element(
                "target",
                {"ports": [{"id": "in", "mode": "input", "dataType": "str"}]},
            )
        self.assertEqual("float", document.element("target").ports[0].properties["dataType"])


if __name__ == "__main__":
    unittest.main()
