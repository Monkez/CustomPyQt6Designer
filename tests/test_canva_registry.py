from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    ElementDefinition,
    ElementRegistry,
    create_default_element_registry,
)


class ElementRegistryTests(unittest.TestCase):
    def test_builtin_registry_is_ordered_cloneable_and_category_driven(self) -> None:
        registry = create_default_element_registry()

        self.assertEqual((160.0, 48.0), registry.require("text").default_size)
        self.assertEqual(("Shapes", "Diagram & data", "Media"), registry.categories())
        clone = registry.clone()
        clone.unregister("text")
        self.assertIsNotNone(registry.definition("text"))
        self.assertIsNone(clone.definition("text"))

    def test_custom_definition_and_duplicate_policy(self) -> None:
        registry = ElementRegistry()
        definition = ElementDefinition(
            "sensor", "Sensor", "Industrial", 144, 88, defaults={"unit": "bar"}
        )
        registry.register(definition)

        self.assertEqual((definition,), registry.in_category("Industrial"))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            registry.register(definition)
        registry.register(
            ElementDefinition("sensor", "Pressure sensor", "Industrial", 160, 90),
            replace_existing=True,
        )
        self.assertEqual("Pressure sensor", registry.require("sensor").label)

    def test_schema_defaults_migrations_and_plugin_ownership(self) -> None:
        def migrate_v1(record):
            record["value"] = record.pop("reading")
            return record

        definition = ElementDefinition(
            "sensor",
            "Sensor",
            "Industrial",
            144,
            88,
            defaults={"unit": "bar"},
            schema={
                "required": ["value"],
                "properties": {
                    "value": {"type": "number", "minimum": 0, "maximum": 100},
                    "unit": {"type": "string", "enum": ["bar", "psi"]},
                },
            },
            schema_version=2,
            migrations={1: migrate_v1},
            plugin_id="industrial-pack",
            plugin_version="1.4.0",
        )
        registry = ElementRegistry([definition])

        migrated = registry.prepare_record(
            {"id": "pressure", "type": "sensor", "reading": 42}
        )
        self.assertEqual(2, migrated["componentVersion"])
        self.assertEqual(42, migrated["value"])
        self.assertEqual("bar", migrated["unit"])
        self.assertEqual((definition,), registry.owned_by("industrial-pack"))
        self.assertEqual((definition,), registry.unregister_owner("industrial-pack"))
        with self.assertRaises(TypeError):
            definition.schema["properties"]["value"]["minimum"] = -10
        with self.assertRaisesRegex(ValueError, ">= 0"):
            definition.prepare_record(
                {"id": "bad", "type": "sensor", "componentVersion": 2, "value": -1}
            )

    def test_schema_requires_contiguous_migration_chain(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing migrations"):
            ElementDefinition(
                "future", "Future", "Custom", 100, 100, schema_version=3,
                migrations={1: lambda record: record},
            )
        with self.assertRaisesRegex(ValueError, "Unsupported schema type"):
            ElementDefinition(
                "bad-schema", "Bad", "Custom", 100, 100,
                schema={"properties": {"value": {"type": "callable"}}},
            )


if __name__ == "__main__":
    unittest.main()
