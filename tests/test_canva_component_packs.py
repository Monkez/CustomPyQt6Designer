from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    COMPONENT_PACKS,
    DASHBOARD_PACK_ID,
    INDUSTRIAL_PACK_ID,
    SOFTWARE_PACK_ID,
    ElementRegistry,
    component_pack,
    component_packs,
    create_default_element_registry,
    register_component_pack,
)


class ComponentPackTests(unittest.TestCase):
    def test_catalog_is_complete_stable_and_opt_in(self) -> None:
        packs = component_packs()

        self.assertIs(COMPONENT_PACKS, packs)
        self.assertEqual(
            (DASHBOARD_PACK_ID, INDUSTRIAL_PACK_ID, SOFTWARE_PACK_ID),
            tuple(pack.pack_id for pack in packs),
        )
        self.assertEqual((15, 12, 16), tuple(len(pack.definitions) for pack in packs))
        all_definitions = tuple(
            definition for pack in packs for definition in pack.definitions
        )
        self.assertEqual(43, len(all_definitions))
        self.assertEqual(43, len({definition.type_id for definition in all_definitions}))
        self.assertEqual(
            {"dash_kpi_card", "dash_alarm_banner"},
            {
                component_pack("dashboard").definitions[0].type_id,
                component_pack("dash").definitions[-1].type_id,
            },
        )
        default_ids = {
            definition.type_id
            for definition in create_default_element_registry().definitions()
        }
        self.assertFalse(default_ids.intersection(
            definition.type_id for definition in all_definitions
        ))

    def test_definitions_have_portable_defaults_schema_and_typed_ports(self) -> None:
        tank = next(
            definition for definition in component_pack("industrial").definitions
            if definition.type_id == "ind_tank"
        )
        prepared = tank.prepare_record({"id": "tank-a", "type": "ind_tank"})

        self.assertEqual("tank", prepared["packVisual"])
        self.assertEqual("fluid", prepared["ports"][0]["dataType"])
        self.assertIn("component-pack", tank.capabilities)
        self.assertIn("ports", tank.capabilities)
        self.assertEqual(68, prepared["value"])
        plc = next(
            definition for definition in component_pack("industrial").definitions
            if definition.type_id == "ind_plc"
        )
        with self.assertRaisesRegex(ValueError, "one of"):
            plc.prepare_record({"id": "plc-b", "type": "ind_plc", "status": "invalid"})

        gauge = next(
            definition for definition in component_pack("dashboard").definitions
            if definition.type_id == "dash_gauge"
        )
        self.assertIn("value", gauge.schema["properties"])
        self.assertEqual("monkez.dashboard", gauge.plugin_id)

        decision = next(
            definition for definition in component_pack("flowchart").definitions
            if definition.type_id == "soft_decision"
        )
        self.assertEqual(
            ("in", "yes", "no"),
            tuple(port["id"] for port in decision.defaults["ports"]),
        )

    def test_registration_is_owned_ordered_and_strict(self) -> None:
        registry = ElementRegistry()
        registered = register_component_pack(registry, "software")

        self.assertEqual(16, len(registered))
        self.assertEqual(
            registered,
            tuple(
                definition.type_id
                for definition in registry.owned_by(SOFTWARE_PACK_ID)
            ),
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            register_component_pack(registry, "software")
        partial = ElementRegistry([component_pack("dashboard").definitions[-1]])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            register_component_pack(partial, "dashboard")
        self.assertEqual(1, len(partial.definitions()))
        removed = registry.unregister_owner(SOFTWARE_PACK_ID)
        self.assertEqual(16, len(removed))
        self.assertFalse(registry.definitions())
        with self.assertRaisesRegex(KeyError, "Unknown"):
            component_pack("unknown")


if __name__ == "__main__":
    unittest.main()
