from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    BindingSpec,
    DataBindingEngine,
    apply_binding_pipeline,
    binding_specs_from_document,
)


class DataBindingKernelTests(unittest.TestCase):
    def test_spec_round_trip_and_safe_transform_pipeline(self) -> None:
        record = {
            "id": "temperature-label",
            "source": "sensor.temperature",
            "target": "text",
            "transforms": [
                {"op": "get", "path": "measurement.value"},
                {"op": "scale", "value": 1.8},
                {"op": "offset", "value": 32},
                {"op": "clamp", "min": -40, "max": 212},
                {"op": "round", "digits": 1},
            ],
            "format": "{value} °F",
            "debounce": 0.1,
            "throttle": 0.5,
            "staleAfter": 5,
            "fallback": "No signal",
            "errorFallback": "Invalid",
        }
        spec = BindingSpec.from_record("temperature", record)
        self.assertEqual(record, spec.to_record())
        self.assertEqual(
            "77.0 °F",
            apply_binding_pipeline(spec, {"measurement": {"value": 25}}),
        )

    def test_batch_feed_updates_multiple_targets_once(self) -> None:
        batches = []
        events = []
        engine = DataBindingEngine(batches.append, event_sink=events.append, clock=lambda: 10)
        engine.register(BindingSpec.from_record("label", {
            "id": "label-text", "source": "telemetry", "target": "text",
            "transforms": {"op": "get", "path": "name"},
        }))
        engine.register(BindingSpec.from_record("chart", {
            "id": "chart-data", "source": "telemetry", "target": "data",
            "transforms": {"op": "get", "path": "samples"},
        }))

        updates = engine.feed("telemetry", {"name": "Pump A", "samples": [1, 2, 3]})

        self.assertEqual(2, len(updates))
        self.assertEqual(1, len(batches))
        self.assertEqual("Pump A", batches[0][0].value)
        self.assertEqual([1, 2, 3], batches[0][1].value)
        self.assertEqual("active", engine.state("label-text")["state"])
        self.assertEqual(2, len([event for event in events if event.event == "value_applied"]))

    def test_debounce_throttle_stale_and_error_fallback_are_deterministic(self) -> None:
        now = [0.0]
        batches = []
        engine = DataBindingEngine(batches.append, clock=lambda: now[0])
        engine.register(BindingSpec.from_record("value", {
            "id": "bound", "source": "source", "target": "text",
            "transforms": {"op": "scale", "value": 2},
            "debounce": 0.2, "throttle": 1.0, "staleAfter": 2.0,
            "fallback": "stale", "errorFallback": "invalid",
        }))

        self.assertFalse(engine.feed("source", 2))
        now[0] = 0.1
        self.assertFalse(engine.feed("source", 3))
        now[0] = 0.29
        self.assertFalse(engine.tick())
        now[0] = 0.31
        self.assertEqual(6.0, engine.tick()[0].value)

        now[0] = 0.4
        engine.feed("source", 4)
        self.assertAlmostEqual(1.31, engine.state("bound")["due"])
        now[0] = 1.31
        self.assertEqual(8.0, engine.tick()[0].value)

        now[0] = 1.4
        engine.feed("source", "bad")
        self.assertEqual("error", engine.state("bound")["state"])
        now[0] = 2.31
        fallback = engine.tick()
        self.assertEqual("invalid", fallback[0].value)
        self.assertEqual("error", engine.state("bound")["state"])

        now[0] = 3.4
        stale = engine.tick()
        self.assertEqual("stale", stale[-1].value)
        self.assertEqual("stale", engine.state("bound")["state"])
        self.assertIn("binding_stale", [event.event for event in engine.events()])

    def test_document_compilation_validates_ids_targets_and_json(self) -> None:
        document = {
            "elements": [
                {"id": "a", "type": "text", "bindings": [
                    {"id": "one", "source": "s", "target": "text"},
                ]},
                {"id": "b", "type": "node", "bindings": [
                    {"id": "two", "source": "s", "target": "port.in"},
                ]},
            ]
        }
        specs = binding_specs_from_document(document)
        self.assertEqual(("one", "two"), tuple(spec.binding_id for spec in specs))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            binding_specs_from_document({"elements": [
                {"id": "a", "bindings": [
                    {"id": "same", "source": "x", "target": "text"},
                ]},
                {"id": "b", "bindings": [
                    {"id": "same", "source": "y", "target": "text"},
                ]},
            ]})
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            BindingSpec.from_record("a", {
                "id": "bad", "source": "x", "target": "__dict__",
            })

    def test_one_thousand_batched_source_values_keep_latest_state(self) -> None:
        batches = []
        engine = DataBindingEngine(batches.append, clock=lambda: 0)
        engine.register(BindingSpec.from_record("counter", {
            "id": "counter-text", "source": "counter", "target": "text",
            "format": "Value {value}",
        }))
        for value in range(1000):
            engine.feed("counter", value)
        self.assertEqual("Value 999", engine.state("counter-text")["value"])
        self.assertEqual(1000, len(batches))
        self.assertEqual(1000, len(engine.events()))


if __name__ == "__main__":
    unittest.main()
