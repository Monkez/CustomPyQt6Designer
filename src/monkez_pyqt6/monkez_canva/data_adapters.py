"""Qt-free runtime contract for external MonkezCanva data adapters.

Protocol clients (MQTT, WebSocket, OPC-UA, Modbus, and similar packages) stay
optional.  They implement a tiny lifecycle contract and publish values through
the context supplied by :class:`DataAdapterRegistry`.
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import RLock
from typing import Any


ADAPTER_STATES = (
    "stopped", "connecting", "connected", "degraded", "error", "disconnected"
)
ADAPTER_CAPABILITIES = ("read", "subscribe", "write", "history")


def _identifier(value: Any, label: str) -> str:
    result = str(value).strip()
    if not result or any(character.isspace() for character in result):
        raise ValueError(f"{label} must be a non-empty identifier without spaces")
    return result


def _json_value(value: Any, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise TypeError(f"{label} must be finite JSON data") from error


@dataclass(frozen=True, slots=True)
class DataAdapterManifest:
    """Portable adapter identity and capabilities; never contains credentials."""

    adapter_id: str
    protocol: str
    version: str = "1.0"
    display_name: str = ""
    capabilities: tuple[str, ...] = ("read", "subscribe")
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", _identifier(self.adapter_id, "Adapter ID"))
        object.__setattr__(self, "protocol", _identifier(self.protocol, "Protocol"))
        normalized = tuple(dict.fromkeys(str(item).strip().lower() for item in self.capabilities))
        unknown = set(normalized).difference(ADAPTER_CAPABILITIES)
        if unknown:
            raise ValueError(f"Unsupported adapter capabilities: {sorted(unknown)}")
        object.__setattr__(self, "capabilities", normalized)
        object.__setattr__(self, "metadata", _json_value(dict(self.metadata), "Adapter metadata"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapterId": self.adapter_id,
            "protocol": self.protocol,
            "version": str(self.version),
            "displayName": self.display_name or self.adapter_id,
            "capabilities": list(self.capabilities),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class DataAdapterEvent:
    sequence: int
    timestamp: float
    adapter_id: str
    event: str
    channel: str = ""
    value: Any = None
    message: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def source_id(self) -> str:
        return f"{self.adapter_id}:{self.channel}" if self.channel else self.adapter_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "adapterId": self.adapter_id,
            "sourceId": self.source_id,
            "event": self.event,
            "channel": self.channel,
            "value": self.value,
            "message": self.message,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class _AdapterRuntime:
    adapter: Any
    manifest: DataAdapterManifest
    state: str = "stopped"
    message: str = ""
    started_at: float | None = None
    last_event: float | None = None
    received: int = 0
    written: int = 0
    errors: int = 0
    reconnects: int = 0


class DataAdapterContext:
    """Capability handed to an adapter during ``start``."""

    def __init__(self, registry: "DataAdapterRegistry", adapter_id: str) -> None:
        self._registry = registry
        self.adapter_id = adapter_id

    def publish(self, channel: str, value: Any, *, metadata: Mapping[str, Any] | None = None) -> None:
        self._registry.publish(self.adapter_id, channel, value, metadata=metadata)

    def set_state(self, state: str, message: str = "") -> None:
        self._registry.set_state(self.adapter_id, state, message)

    def report_error(self, message: str, *, channel: str = "") -> None:
        self._registry.report_error(self.adapter_id, message, channel=channel)


class DataAdapterRegistry:
    """Lifecycle, health, subscriptions, write-back, trace and bounded history."""

    def __init__(
        self,
        *,
        event_sink: Callable[[DataAdapterEvent], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
        history_limit: int = 256,
        trace_limit: int = 2000,
    ) -> None:
        self._event_sink = event_sink
        self._clock = clock
        self._history_limit = max(1, int(history_limit))
        self._trace: deque[DataAdapterEvent] = deque(maxlen=max(10, int(trace_limit)))
        self._runtimes: dict[str, _AdapterRuntime] = {}
        self._history: dict[tuple[str, str], deque[DataAdapterEvent]] = {}
        self._subscribers: dict[
            tuple[str, str], dict[int, Callable[[DataAdapterEvent], None]]
        ] = defaultdict(dict)
        self._next_token = 0
        self._sequence = 0
        self._lock = RLock()

    def register(self, adapter: Any, *, start: bool = False) -> str:
        raw_manifest = getattr(adapter, "manifest", None)
        raw_manifest = raw_manifest() if callable(raw_manifest) else raw_manifest
        if isinstance(raw_manifest, Mapping):
            raw_manifest = DataAdapterManifest(
                raw_manifest.get("adapterId", raw_manifest.get("adapter_id", "")),
                raw_manifest.get("protocol", "custom"),
                raw_manifest.get("version", "1.0"),
                raw_manifest.get("displayName", raw_manifest.get("display_name", "")),
                tuple(raw_manifest.get("capabilities", ("read", "subscribe"))),
                raw_manifest.get("metadata", {}),
            )
        if not isinstance(raw_manifest, DataAdapterManifest):
            raise TypeError("Adapter must expose a DataAdapterManifest as 'manifest'")
        with self._lock:
            if raw_manifest.adapter_id in self._runtimes:
                raise ValueError(f"Duplicate data adapter ID: {raw_manifest.adapter_id}")
            self._runtimes[raw_manifest.adapter_id] = _AdapterRuntime(adapter, raw_manifest)
        self._record(raw_manifest.adapter_id, "registered")
        if start:
            self.start(raw_manifest.adapter_id)
        return raw_manifest.adapter_id

    def unregister(self, adapter_id: str, *, stop: bool = True) -> bool:
        key = str(adapter_id)
        with self._lock:
            if key not in self._runtimes:
                return False
        if stop:
            self.stop(key)
        with self._lock:
            self._runtimes.pop(key, None)
            for route in tuple(self._subscribers):
                if route[0] == key:
                    self._subscribers.pop(route, None)
        self._record(key, "unregistered")
        return True

    def start(self, adapter_id: str) -> None:
        runtime = self._required(adapter_id)
        with self._lock:
            if runtime.state in ("connecting", "connected", "degraded"):
                return
            if runtime.started_at is not None:
                runtime.reconnects += 1
        self.set_state(adapter_id, "connecting")
        try:
            result = runtime.adapter.start(DataAdapterContext(self, runtime.manifest.adapter_id))
            if result is not False and runtime.state == "connecting":
                self.set_state(adapter_id, "connected")
            with self._lock:
                runtime.started_at = self._now()
        except Exception as error:
            self.report_error(adapter_id, str(error))
            raise

    def stop(self, adapter_id: str) -> None:
        runtime = self._required(adapter_id)
        with self._lock:
            if runtime.state == "stopped":
                return
        try:
            stop = getattr(runtime.adapter, "stop", None)
            if callable(stop):
                stop()
        finally:
            self.set_state(adapter_id, "stopped")

    def stop_all(self) -> None:
        with self._lock:
            adapter_ids = tuple(self._runtimes)
        for adapter_id in adapter_ids:
            try:
                self.stop(adapter_id)
            except Exception as error:
                self.report_error(adapter_id, str(error))

    def subscribe(self, adapter_id: str, channel: str, callback: Callable[[DataAdapterEvent], None]) -> int:
        runtime = self._required(adapter_id)
        if not callable(callback):
            raise TypeError("Subscriber must be callable")
        channel_key = _identifier(channel, "Adapter channel")
        route = (runtime.manifest.adapter_id, channel_key)
        with self._lock:
            first = not self._subscribers[route]
            self._next_token += 1
            token = self._next_token
            self._subscribers[route][token] = callback
        if first:
            subscribe = getattr(runtime.adapter, "subscribe", None)
            if callable(subscribe):
                try:
                    subscribe(channel_key)
                except Exception:
                    with self._lock:
                        self._subscribers[route].pop(token, None)
                        if not self._subscribers[route]:
                            self._subscribers.pop(route, None)
                    raise
        return token

    def unsubscribe(self, token: int) -> bool:
        adapter = None
        channel = ""
        with self._lock:
            for route, subscribers in tuple(self._subscribers.items()):
                if token not in subscribers:
                    continue
                subscribers.pop(token)
                if not subscribers:
                    self._subscribers.pop(route, None)
                    adapter_id, channel = route
                    runtime = self._runtimes.get(adapter_id)
                    adapter = runtime.adapter if runtime else None
                break
            else:
                return False
        unsubscribe = getattr(adapter, "unsubscribe", None)
        if callable(unsubscribe):
            unsubscribe(channel)
        return True

    def publish(self, adapter_id: str, channel: str, value: Any, *, metadata: Mapping[str, Any] | None = None) -> DataAdapterEvent:
        runtime = self._required(adapter_id)
        channel_key = _identifier(channel, "Adapter channel")
        safe_value = _json_value(value, "Adapter value")
        with self._lock:
            runtime.received += 1
            runtime.last_event = self._now()
        event = self._record(adapter_id, "value", channel_key, safe_value, metadata=metadata)
        route = (runtime.manifest.adapter_id, channel_key)
        with self._lock:
            history = self._history.setdefault(route, deque(maxlen=self._history_limit))
            history.append(event)
            callbacks = tuple(self._subscribers.get(route, {}).values())
        for callback in callbacks:
            try:
                callback(event)
            except Exception as error:
                self.report_error(adapter_id, f"Subscriber failed: {error}", channel=channel_key)
        return event

    def write(self, adapter_id: str, channel: str, value: Any, *, metadata: Mapping[str, Any] | None = None) -> Any:
        runtime = self._required(adapter_id)
        if "write" not in runtime.manifest.capabilities:
            raise PermissionError(f"Adapter {adapter_id!r} does not support write-back")
        writer = getattr(runtime.adapter, "write", None)
        if not callable(writer):
            raise TypeError(f"Adapter {adapter_id!r} declares write but has no write()")
        safe_value = _json_value(value, "Adapter write value")
        try:
            result = writer(_identifier(channel, "Adapter channel"), safe_value, dict(metadata or {}))
            with self._lock:
                runtime.written += 1
            self._record(adapter_id, "write", str(channel), safe_value, metadata=metadata)
            return result
        except Exception as error:
            self.report_error(adapter_id, f"Write failed: {error}", channel=str(channel))
            raise

    def read(self, adapter_id: str, channel: str) -> Any:
        """Read one channel and publish the result through the normal value path."""

        runtime = self._required(adapter_id)
        if "read" not in runtime.manifest.capabilities:
            raise PermissionError(f"Adapter {adapter_id!r} does not support reads")
        reader = getattr(runtime.adapter, "read", None)
        if not callable(reader):
            raise TypeError(f"Adapter {adapter_id!r} declares read but has no read()")
        channel_key = _identifier(channel, "Adapter channel")
        try:
            value = reader(channel_key)
            return self.publish(
                adapter_id, channel_key, value, metadata={"origin": "read"}
            ).value
        except Exception as error:
            self.report_error(adapter_id, f"Read failed: {error}", channel=channel_key)
            raise

    def set_state(self, adapter_id: str, state: str, message: str = "") -> None:
        runtime = self._required(adapter_id)
        normalized = str(state).lower().strip()
        if normalized not in ADAPTER_STATES:
            raise ValueError(f"Unsupported adapter state: {state}")
        with self._lock:
            runtime.state = normalized
            runtime.message = str(message)
        self._record(adapter_id, "state", message=runtime.message, metadata={"state": normalized})

    def report_error(self, adapter_id: str, message: str, *, channel: str = "") -> None:
        runtime = self._required(adapter_id)
        with self._lock:
            runtime.state = "error"
            runtime.message = str(message)
            runtime.errors += 1
        self._record(adapter_id, "error", channel, message=str(message))

    def manifests(self) -> tuple[DataAdapterManifest, ...]:
        with self._lock:
            return tuple(runtime.manifest for runtime in self._runtimes.values())

    def health(self, adapter_id: str | None = None) -> tuple[dict[str, Any], ...] | dict[str, Any]:
        def snapshot(runtime: _AdapterRuntime) -> dict[str, Any]:
            return {
                **runtime.manifest.to_dict(), "state": runtime.state,
                "message": runtime.message, "startedAt": runtime.started_at,
                "lastEvent": runtime.last_event, "received": runtime.received,
                "written": runtime.written, "errors": runtime.errors,
                "reconnects": runtime.reconnects,
            }
        with self._lock:
            if adapter_id is not None:
                return snapshot(self._required(adapter_id))
            return tuple(snapshot(runtime) for runtime in self._runtimes.values())

    def history(self, adapter_id: str, channel: str, limit: int | None = None) -> tuple[DataAdapterEvent, ...]:
        with self._lock:
            values = tuple(self._history.get((str(adapter_id), str(channel)), ()))
        return values if limit is None else values[-max(0, int(limit)):]

    def trace(self, limit: int | None = None) -> tuple[DataAdapterEvent, ...]:
        with self._lock:
            values = tuple(self._trace)
        return values if limit is None else values[-max(0, int(limit)):]

    def _required(self, adapter_id: str) -> _AdapterRuntime:
        with self._lock:
            runtime = self._runtimes.get(str(adapter_id))
        if runtime is None:
            raise KeyError(f"Unknown data adapter: {adapter_id}")
        return runtime

    def _now(self) -> float:
        result = float(self._clock())
        if not math.isfinite(result):
            raise ValueError("Adapter clock must be finite")
        return result

    def _record(self, adapter_id: str, event: str, channel: str = "", value: Any = None, message: str = "", metadata: Mapping[str, Any] | None = None) -> DataAdapterEvent:
        with self._lock:
            self._sequence += 1
            record = DataAdapterEvent(
                self._sequence, self._now(), str(adapter_id), str(event), str(channel),
                value, str(message), _json_value(dict(metadata or {}), "Adapter event metadata"),
            )
            self._trace.append(record)
        if self._event_sink is not None:
            self._event_sink(record)
        return record
