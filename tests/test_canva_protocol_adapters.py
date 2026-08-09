import unittest

from monkez_pyqt6.monkez_canva import (
    HistorianPolicy,
    MQTTAdapter,
    DataAdapterRegistry,
    create_protocol_adapter,
)
from monkez_pyqt6.monkez_canva.data_binding import BindingSpec, DataBindingEngine


class ProtocolAdapterTests(unittest.TestCase):
    def test_optional_protocol_adapter_publishes_and_writes(self):
        adapter = create_protocol_adapter("mqtt", "broker", channels={"temp": 21})
        registry = DataAdapterRegistry()
        registry.register(adapter, start=True)
        seen = []
        registry.subscribe("broker", "temp", lambda event: seen.append(event.value))
        adapter._on_value("temp", 22)
        self.assertEqual([22], seen)
        self.assertEqual(23, registry.write("broker", "temp", 23))
        self.assertEqual(("mqtt",), (adapter.manifest.protocol,))

    def test_historian_policy_aggregates(self):
        registry = DataAdapterRegistry(clock=lambda: 10.0)
        registry.register(MQTTAdapter("broker"))
        registry.set_historian_policy("broker", "temp", HistorianPolicy(aggregation="avg"))
        for value in (10, 20, 30):
            registry.publish("broker", "temp", value)
        self.assertEqual(20.0, registry.history("broker", "temp")[0].value)


class WriteBackBindingTests(unittest.TestCase):
    def test_write_back_requires_opt_in_and_uses_transform(self):
        spec = BindingSpec.from_record("node", {
            "id": "b", "source": "mqtt:temp", "target": "text",
            "writeBack": True, "writeTransforms": [{"op": "scale", "value": 2}],
        })
        engine = DataBindingEngine()
        engine.register(spec)
        writes = []
        engine.write_back("b", 4, lambda source, value, metadata: writes.append((source, value)))
        self.assertEqual([("mqtt:temp", 8)], writes)
