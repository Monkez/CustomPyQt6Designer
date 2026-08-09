"""Optional protocol adapter implementations for MonkezCanva.

The core package never imports protocol clients.  Applications provide a
transport object (or install an optional extra) and these adapters translate
its callbacks into :class:`DataAdapterRegistry` events.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .data_adapters import DataAdapterContext, DataAdapterManifest


class ProtocolAdapter:
    """Small transport-neutral adapter used by all protocol packages."""

    protocol = "custom"

    def __init__(self, adapter_id: str, *, transport: Any = None, channels: Mapping[str, Any] | None = None) -> None:
        self.manifest = DataAdapterManifest(
            adapter_id, self.protocol, display_name=adapter_id,
            capabilities=("read", "subscribe", "write", "history"),
        )
        self.transport = transport
        self.channels = dict(channels or {})
        self._context: DataAdapterContext | None = None

    def start(self, context: DataAdapterContext) -> None:
        self._context = context
        if self.transport is not None and callable(getattr(self.transport, "start", None)):
            self.transport.start(self._on_value)

    def stop(self) -> None:
        if self.transport is not None and callable(getattr(self.transport, "stop", None)):
            self.transport.stop()
        self._context = None

    def subscribe(self, channel: str) -> None:
        if self.transport is not None and callable(getattr(self.transport, "subscribe", None)):
            self.transport.subscribe(channel, self._on_value)

    def write(self, channel: str, value: Any, metadata: Mapping[str, Any] | None = None) -> Any:
        if self.transport is None or not callable(getattr(self.transport, "write", None)):
            self.channels[channel] = value
            return value
        return self.transport.write(channel, value, dict(metadata or {}))

    def read(self, channel: str) -> Any:
        if self.transport is not None and callable(getattr(self.transport, "read", None)):
            return self.transport.read(channel)
        return self.channels.get(channel)

    def _on_value(self, channel: str, value: Any, metadata: Mapping[str, Any] | None = None) -> None:
        if self._context is not None:
            self._context.publish(channel, value, metadata=metadata)


class MQTTAdapter(ProtocolAdapter):
    protocol = "mqtt"


class WebSocketAdapter(ProtocolAdapter):
    protocol = "websocket"


class OPCUAAdapter(ProtocolAdapter):
    protocol = "opcua"


class ModbusAdapter(ProtocolAdapter):
    protocol = "modbus"


PROTOCOL_ADAPTERS = {
    "mqtt": MQTTAdapter,
    "websocket": WebSocketAdapter,
    "opcua": OPCUAAdapter,
    "modbus": ModbusAdapter,
}


def create_protocol_adapter(protocol: str, adapter_id: str, **kwargs: Any) -> ProtocolAdapter:
    try:
        adapter_type = PROTOCOL_ADAPTERS[str(protocol).strip().lower()]
    except KeyError as error:
        raise ValueError(f"Unsupported protocol adapter: {protocol!r}") from error
    return adapter_type(adapter_id, **kwargs)


def available_protocols() -> tuple[str, ...]:
    return tuple(PROTOCOL_ADAPTERS)
