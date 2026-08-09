from __future__ import annotations

import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from monkez_pyqt6.monkez_canva import (
    DataAdapterManifest,
    DataAdapterRegistry,
)
from monkez_pyqt6.monkez_widgets import MonkezCanva


class MemoryAdapter:
    manifest = DataAdapterManifest(
        "memory",
        "memory",
        display_name="In-memory telemetry",
        capabilities=("read", "subscribe", "write", "history"),
    )

    def __init__(self) -> None:
        self.context = None
        self.subscriptions: list[str] = []
        self.writes: list[tuple[str, object, dict]] = []
        self.stopped = False

    def start(self, context) -> None:
        self.context = context

    def stop(self) -> None:
        self.stopped = True

    def subscribe(self, channel: str) -> None:
        self.subscriptions.append(channel)

    def unsubscribe(self, channel: str) -> None:
        self.subscriptions.remove(channel)

    def write(self, channel: str, value, metadata: dict):
        record = (channel, value, metadata)
        self.writes.append(record)
        return record

    def read(self, channel: str):
        for written_channel, value, _metadata in reversed(self.writes):
            if written_channel == channel:
                return value
        return None


class DataAdapterRegistryTests(unittest.TestCase):
    def test_lifecycle_subscription_history_health_and_write(self) -> None:
        clock = [10.0]
        events = []
        adapter = MemoryAdapter()
        registry = DataAdapterRegistry(
            event_sink=events.append, clock=lambda: clock[0], history_limit=2
        )

        self.assertEqual("memory", registry.register(adapter, start=True))
        self.assertEqual("connected", registry.health("memory")["state"])
        received = []
        token = registry.subscribe("memory", "temperature", received.append)
        self.assertEqual(["temperature"], adapter.subscriptions)

        for value in (21, 22, 23):
            clock[0] += 1
            adapter.context.publish("temperature", value, metadata={"quality": "good"})

        self.assertEqual([21, 22, 23], [event.value for event in received])
        self.assertEqual([22, 23], [event.value for event in registry.history(
            "memory", "temperature"
        )])
        self.assertEqual(
            ("setpoint", 24, {"actor": "test"}),
            registry.write("memory", "setpoint", 24, metadata={"actor": "test"}),
        )
        self.assertEqual(24, registry.read("memory", "setpoint"))
        health = registry.health("memory")
        self.assertEqual(4, health["received"])
        self.assertEqual(1, health["written"])
        self.assertTrue(registry.unsubscribe(token))
        self.assertFalse(adapter.subscriptions)
        self.assertTrue(registry.unregister("memory"))
        self.assertTrue(adapter.stopped)
        self.assertEqual("unregistered", events[-1].event)

    def test_validation_duplicate_and_capability_guards(self) -> None:
        registry = DataAdapterRegistry()
        adapter = MemoryAdapter()
        registry.register(adapter, start=True)
        with self.assertRaises(ValueError):
            registry.register(adapter)

        class ReadOnlyAdapter:
            manifest = DataAdapterManifest("readonly", "custom")

            def start(self, _context) -> None:
                pass

        registry.register(ReadOnlyAdapter())
        with self.assertRaises(PermissionError):
            registry.write("readonly", "value", 1)
        with self.assertRaises(TypeError):
            adapter.context.publish("bad", float("nan"))

    def test_adapter_and_channel_ids_do_not_collide_at_colon_boundaries(self) -> None:
        left = MemoryAdapter()
        left.manifest = DataAdapterManifest("a:b", "memory")
        right = MemoryAdapter()
        right.manifest = DataAdapterManifest("a", "memory")
        registry = DataAdapterRegistry()
        registry.register(left, start=True)
        registry.register(right, start=True)
        left_values = []
        right_values = []
        registry.subscribe("a:b", "c", left_values.append)
        registry.subscribe("a", "b:c", right_values.append)

        left.context.publish("c", "left")
        right.context.publish("b:c", "right")

        self.assertEqual(["left"], [event.value for event in left_values])
        self.assertEqual(["right"], [event.value for event in right_values])


class CanvasDataAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_adapter_channel_drives_binding_without_dirtying_document(self) -> None:
        canvas = MonkezCanva()
        adapter = MemoryAdapter()
        label = canvas.addText("Waiting", element_id="telemetry-label")
        canvas.addDataBinding(label, "text", "plant.temperature")
        document_before_runtime = canvas.toDocument()
        dirty_before_runtime = canvas.isDocumentModified()

        canvas.registerDataAdapter(adapter)
        canvas.bindAdapterSource(
            "plant.temperature", "memory", "temperature"
        )
        adapter.context.publish("temperature", 26.5)

        self.assertEqual("26.5", canvas.element(label).text)
        self.assertEqual(document_before_runtime, canvas.toDocument())
        self.assertEqual(dirty_before_runtime, canvas.isDocumentModified())
        self.assertEqual(1, canvas.dataAdapterHealth("memory")["received"])
        self.assertEqual(26.5, canvas.dataAdapterHistory(
            "memory", "temperature", 1
        )[0]["value"])
        canvas.close()
        self.assertTrue(adapter.stopped)

    def test_worker_thread_publication_is_queued_to_gui_thread(self) -> None:
        canvas = MonkezCanva()
        adapter = MemoryAdapter()
        label = canvas.addText("Waiting", element_id="worker-label")
        canvas.addDataBinding(label, "text", "worker.value")
        canvas.registerDataAdapter(adapter)
        canvas.bindAdapterSource("worker.value", "memory", "value")

        worker = threading.Thread(
            target=lambda: adapter.context.publish("value", "from worker")
        )
        worker.start()
        worker.join(timeout=2)
        deadline = time.monotonic() + 2
        while canvas.element(label).text != "from worker" and time.monotonic() < deadline:
            self.app.processEvents()

        self.assertEqual("from worker", canvas.element(label).text)
        canvas.close()


if __name__ == "__main__":
    unittest.main()
