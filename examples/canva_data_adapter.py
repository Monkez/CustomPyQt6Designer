"""Minimal external data-adapter example for MonkezCanva.

Real MQTT/WebSocket/OPC-UA/Modbus packages can keep their own dependencies and
worker threads.  Only this small lifecycle surface is required by the canvas.
"""

from __future__ import annotations

from typing import Any

from monkez_pyqt6.monkez_canva import DataAdapterManifest


class SimulatedTelemetryAdapter:
    manifest = DataAdapterManifest(
        "demo-telemetry",
        "simulation",
        display_name="Demo telemetry",
        capabilities=("read", "subscribe", "write", "history"),
        metadata={"vendor": "Monkez", "transport": "in-process"},
    )

    def __init__(self) -> None:
        self._context = None
        self._channels: set[str] = set()
        self._values: dict[str, Any] = {}

    def start(self, context) -> None:
        self._context = context
        context.set_state("connected", "Simulator ready")

    def stop(self) -> None:
        self._channels.clear()
        self._context = None

    def subscribe(self, channel: str) -> None:
        self._channels.add(channel)

    def unsubscribe(self, channel: str) -> None:
        self._channels.discard(channel)

    def write(self, channel: str, value: Any, metadata: dict[str, Any]) -> Any:
        self._values[channel] = value
        self.publish(channel, value, metadata={**metadata, "writeBack": True})
        return value

    def read(self, channel: str) -> Any:
        return self._values.get(channel)

    def publish(
        self,
        channel: str,
        value: Any,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._context is None:
            raise RuntimeError("Adapter is not started")
        self._values[channel] = value
        self._context.publish(channel, value, metadata=metadata)


def attach_simulated_telemetry(canvas):
    """Attach the demo and return it so the host can publish sample values."""

    adapter = SimulatedTelemetryAdapter()
    canvas.registerDataAdapter(adapter)
    canvas.bindAdapterSource(
        "plant.temperature", "demo-telemetry", "temperature"
    )
    return adapter
