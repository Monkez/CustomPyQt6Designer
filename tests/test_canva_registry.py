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


if __name__ == "__main__":
    unittest.main()
