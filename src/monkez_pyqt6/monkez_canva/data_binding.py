"""Qt-free declarative data-binding runtime for MonkezCanva.

Binding definitions are portable JSON. Source subscriptions and live values are
owned by the host/widget adapter and deliberately never enter the document.
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


BINDING_STATES = ("idle", "pending", "active", "stale", "error", "disabled")
BINDING_TARGET_PREFIXES = (
    "text",
    "data",
    "color",
    "background",
    "textColor",
    "flowColor",
    "opacity",
    "rotation",
    "scale",
    "x",
    "y",
    "width",
    "height",
    "highlight",
    "animation",
    "port.",
)

_MISSING = object()


def _finite_number(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _json_value(value: Any, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise TypeError(f"{label} must be finite JSON data") from error


def _normalize_target(value: Any) -> str:
    target = str(value).strip()
    if not target or not any(
        target == prefix or (prefix.endswith(".") and target.startswith(prefix))
        for prefix in BINDING_TARGET_PREFIXES
    ):
        raise ValueError(f"Unsupported data-binding target: {target!r}")
    if target.startswith("port.") and not target.removeprefix("port.").strip():
        raise ValueError("Port binding target requires a port ID")
    return target


def _path_value(value: Any, path: str, default: Any = _MISSING) -> Any:
    current = value
    if not path:
        return current
    for segment in str(path).split("."):
        if isinstance(current, Mapping):
            if segment not in current:
                if default is not _MISSING:
                    return default
                raise KeyError(f"Missing field {path!r}")
            current = current[segment]
        elif isinstance(current, (list, tuple)) and segment.lstrip("-").isdigit():
            try:
                current = current[int(segment)]
            except IndexError:
                if default is not _MISSING:
                    return default
                raise KeyError(f"Missing index {path!r}") from None
        else:
            if default is not _MISSING:
                return default
            raise KeyError(f"Cannot resolve field {path!r}")
    return current


@dataclass(frozen=True, slots=True)
class BindingSpec:
    """One portable element-target binding definition."""

    binding_id: str
    element_id: str
    target: str
    source_id: str
    transforms: tuple[Mapping[str, Any], ...] = ()
    format: str = ""
    debounce: float = 0.0
    throttle: float = 0.0
    stale_after: float = 0.0
    fallback: Any = field(default=_MISSING, repr=False)
    error_fallback: Any = field(default=_MISSING, repr=False)
    enabled: bool = True

    @classmethod
    def from_record(
        cls, element_id: str, record: Mapping[str, Any], index: int = 0
    ) -> "BindingSpec":
        raw = dict(record)
        binding_id = str(raw.get("id", f"binding-{index + 1}")).strip()
        source_id = str(raw.get("source", "")).strip()
        if not binding_id:
            raise ValueError("Data-binding ID cannot be empty")
        if not str(element_id).strip():
            raise ValueError("Data-binding element ID cannot be empty")
        if not source_id:
            raise ValueError(f"Binding {binding_id!r} requires a source")
        transforms = raw.get("transforms", ())
        if isinstance(transforms, Mapping):
            transforms = (transforms,)
        if not isinstance(transforms, (list, tuple)) or any(
            not isinstance(transform, Mapping) for transform in transforms
        ):
            raise TypeError("Binding transforms must be a list of objects")
        return cls(
            binding_id,
            str(element_id),
            _normalize_target(raw.get("target", "")),
            source_id,
            tuple(_json_value(dict(item), "Binding transform") for item in transforms),
            str(raw.get("format", "")),
            max(0.0, _finite_number(raw.get("debounce", 0.0), "debounce")),
            max(0.0, _finite_number(raw.get("throttle", 0.0), "throttle")),
            max(0.0, _finite_number(raw.get("staleAfter", 0.0), "staleAfter")),
            _MISSING if "fallback" not in raw else _json_value(raw["fallback"], "fallback"),
            _MISSING if "errorFallback" not in raw else _json_value(
                raw["errorFallback"], "errorFallback"
            ),
            bool(raw.get("enabled", True)),
        )

    def to_record(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.binding_id,
            "source": self.source_id,
            "target": self.target,
        }
        if self.transforms:
            result["transforms"] = [dict(item) for item in self.transforms]
        if self.format:
            result["format"] = self.format
        if self.debounce:
            result["debounce"] = self.debounce
        if self.throttle:
            result["throttle"] = self.throttle
        if self.stale_after:
            result["staleAfter"] = self.stale_after
        if self.fallback is not _MISSING:
            result["fallback"] = _json_value(self.fallback, "fallback")
        if self.error_fallback is not _MISSING:
            result["errorFallback"] = _json_value(
                self.error_fallback, "errorFallback"
            )
        if not self.enabled:
            result["enabled"] = False
        return result


@dataclass(frozen=True, slots=True)
class BindingUpdate:
    binding_id: str
    element_id: str
    target: str
    source_id: str
    value: Any
    source_value: Any
    timestamp: float
    state: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BindingEvent:
    sequence: int
    timestamp: float
    event: str
    binding_id: str
    element_id: str
    source_id: str
    target: str
    state: str
    value: Any = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "event": self.event,
            "bindingId": self.binding_id,
            "elementId": self.element_id,
            "sourceId": self.source_id,
            "target": self.target,
            "state": self.state,
            "value": self.value,
            "error": self.error,
        }


@dataclass(slots=True)
class _BindingRuntime:
    state: str = "idle"
    last_input: float | None = None
    last_apply: float | None = None
    value: Any = None
    source_value: Any = None
    error: str = ""
    pending: BindingUpdate | None = None
    due: float | None = None
    stale_emitted: bool = False


BindingBatchSink = Callable[[tuple[BindingUpdate, ...]], None]
BindingEventSink = Callable[[BindingEvent], None]


class DataBindingEngine:
    """Deterministic source-to-target binding evaluator.

    The engine has no timer. Hosts call :meth:`tick` with real or simulated time,
    which makes debounce, throttle and stale behavior reproducible in tests.
    """

    def __init__(
        self,
        apply_batch: BindingBatchSink | None = None,
        *,
        event_sink: BindingEventSink | None = None,
        clock: Callable[[], float] = time.monotonic,
        max_events: int = 2000,
    ) -> None:
        self._apply_batch = apply_batch
        self._event_sink = event_sink
        self._clock = clock
        self._max_events = max(10, int(max_events))
        self._specs: dict[str, BindingSpec] = {}
        self._source_bindings: dict[str, list[str]] = defaultdict(list)
        self._runtime: dict[str, _BindingRuntime] = {}
        self._events: deque[BindingEvent] = deque(maxlen=self._max_events)
        self._sequence = 0

    def register(self, spec: BindingSpec, *, replace: bool = False) -> None:
        existing = self._specs.get(spec.binding_id)
        if existing is not None and not replace:
            raise ValueError(f"Duplicate data-binding ID: {spec.binding_id}")
        if existing is not None:
            self._source_bindings[existing.source_id].remove(existing.binding_id)
        if any(
            other.element_id == spec.element_id
            and other.target == spec.target
            and other.binding_id != spec.binding_id
            for other in self._specs.values()
        ):
            raise ValueError(
                f"Element target already has a binding: {spec.element_id}.{spec.target}"
            )
        self._specs[spec.binding_id] = spec
        self._source_bindings[spec.source_id].append(spec.binding_id)
        self._runtime[spec.binding_id] = _BindingRuntime(
            state="idle" if spec.enabled else "disabled"
        )

    def replace_all(self, specs: Iterable[BindingSpec]) -> None:
        incoming = tuple(specs)
        self.clear()
        for spec in incoming:
            self.register(spec)

    def remove(self, binding_id: str) -> bool:
        key = str(binding_id)
        spec = self._specs.pop(key, None)
        if spec is None:
            return False
        self._source_bindings[spec.source_id].remove(key)
        if not self._source_bindings[spec.source_id]:
            self._source_bindings.pop(spec.source_id, None)
        self._runtime.pop(key, None)
        return True

    def clear(self) -> None:
        self._specs.clear()
        self._source_bindings.clear()
        self._runtime.clear()

    def specs(self) -> tuple[BindingSpec, ...]:
        return tuple(self._specs.values())

    def spec(self, binding_id: str) -> BindingSpec | None:
        return self._specs.get(str(binding_id))

    def state(self, binding_id: str) -> dict[str, Any]:
        key = str(binding_id)
        spec = self._specs.get(key)
        runtime = self._runtime.get(key)
        if spec is None or runtime is None:
            raise KeyError(f"Unknown data binding: {binding_id}")
        return {
            "bindingId": key,
            "elementId": spec.element_id,
            "sourceId": spec.source_id,
            "target": spec.target,
            "state": runtime.state,
            "value": runtime.value,
            "sourceValue": runtime.source_value,
            "error": runtime.error,
            "lastInput": runtime.last_input,
            "lastApply": runtime.last_apply,
            "due": runtime.due,
        }

    def states(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.state(binding_id) for binding_id in self._specs)

    def events(self, limit: int | None = None) -> tuple[BindingEvent, ...]:
        values = tuple(self._events)
        return values if limit is None else values[-max(0, int(limit)):]

    def next_due(self) -> float | None:
        due_values = [
            runtime.due
            for runtime in self._runtime.values()
            if runtime.due is not None
        ]
        stale_values = [
            runtime.last_input + spec.stale_after
            for binding_id, spec in self._specs.items()
            if spec.enabled
            and spec.stale_after > 0
            and (runtime := self._runtime[binding_id]).last_input is not None
            and not runtime.stale_emitted
        ]
        values = [value for value in (*due_values, *stale_values) if value is not None]
        return min(values) if values else None

    def feed(
        self,
        source_id: str,
        value: Any,
        *,
        timestamp: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> tuple[BindingUpdate, ...]:
        return self.feed_many(
            ((str(source_id), value, dict(metadata or {})),), timestamp=timestamp
        )

    def feed_many(
        self,
        values: Mapping[str, Any] | Iterable[tuple[str, Any] | tuple[str, Any, Mapping[str, Any]]],
        *,
        timestamp: float | None = None,
    ) -> tuple[BindingUpdate, ...]:
        now = self._time(timestamp)
        entries = values.items() if isinstance(values, Mapping) else values
        updates: list[BindingUpdate] = []
        for entry in entries:
            source_id, source_value, *rest = entry
            metadata = dict(rest[0]) if rest else {}
            for binding_id in tuple(self._source_bindings.get(str(source_id), ())):
                spec = self._specs[binding_id]
                runtime = self._runtime[binding_id]
                if not spec.enabled:
                    continue
                runtime.last_input = now
                runtime.source_value = source_value
                runtime.stale_emitted = False
                try:
                    output = apply_binding_pipeline(spec, source_value)
                    runtime.error = ""
                except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
                    runtime.error = str(error)
                    runtime.state = "error"
                    self._record("binding_error", spec, runtime, now, error=str(error))
                    if spec.error_fallback is _MISSING:
                        continue
                    output = spec.error_fallback
                update = BindingUpdate(
                    spec.binding_id,
                    spec.element_id,
                    spec.target,
                    spec.source_id,
                    output,
                    source_value,
                    now,
                    "error" if runtime.error else "active",
                    metadata,
                )
                due = now
                if spec.debounce > 0:
                    due = max(due, now + spec.debounce)
                if (
                    spec.throttle > 0
                    and runtime.last_apply is not None
                    and now < runtime.last_apply + spec.throttle
                ):
                    due = max(due, runtime.last_apply + spec.throttle)
                if due > now:
                    runtime.pending = update
                    runtime.due = due
                    runtime.state = "error" if update.state == "error" else "pending"
                    self._record("update_pending", spec, runtime, now, value=output)
                else:
                    updates.append(update)
        return self._commit(updates, now)

    def tick(self, timestamp: float | None = None) -> tuple[BindingUpdate, ...]:
        now = self._time(timestamp)
        updates: list[BindingUpdate] = []
        for binding_id, spec in self._specs.items():
            runtime = self._runtime[binding_id]
            if runtime.pending is not None and runtime.due is not None and runtime.due <= now:
                updates.append(runtime.pending)
                runtime.pending = None
                runtime.due = None
            if (
                spec.enabled
                and spec.stale_after > 0
                and runtime.last_input is not None
                and not runtime.stale_emitted
                and runtime.last_input + spec.stale_after <= now
            ):
                runtime.state = "stale"
                runtime.stale_emitted = True
                self._record("binding_stale", spec, runtime, now, value=runtime.value)
                if spec.fallback is not _MISSING:
                    updates.append(BindingUpdate(
                        spec.binding_id,
                        spec.element_id,
                        spec.target,
                        spec.source_id,
                        spec.fallback,
                        runtime.source_value,
                        now,
                        "stale",
                        {},
                    ))
        return self._commit(updates, now)

    def _commit(
        self, updates: Iterable[BindingUpdate], timestamp: float
    ) -> tuple[BindingUpdate, ...]:
        batch = tuple(updates)
        if not batch:
            return ()
        if self._apply_batch is not None:
            self._apply_batch(batch)
        for update in batch:
            spec = self._specs[update.binding_id]
            runtime = self._runtime[update.binding_id]
            runtime.value = update.value
            runtime.last_apply = timestamp
            runtime.state = update.state
            runtime.pending = None
            runtime.due = None
            self._record("value_applied", spec, runtime, timestamp, value=update.value)
        return batch

    def _record(
        self,
        event: str,
        spec: BindingSpec,
        runtime: _BindingRuntime,
        timestamp: float,
        *,
        value: Any = None,
        error: str = "",
    ) -> None:
        self._sequence += 1
        record = BindingEvent(
            self._sequence,
            timestamp,
            event,
            spec.binding_id,
            spec.element_id,
            spec.source_id,
            spec.target,
            runtime.state,
            value,
            error,
        )
        self._events.append(record)
        if self._event_sink is not None:
            self._event_sink(record)

    def _time(self, timestamp: float | None) -> float:
        return _finite_number(
            self._clock() if timestamp is None else timestamp, "binding timestamp"
        )


class _FormatValues(dict):
    def __missing__(self, key: str) -> str:
        return ""


def apply_binding_pipeline(spec: BindingSpec, source_value: Any) -> Any:
    """Apply the safe declarative transform/format pipeline."""

    value = source_value
    for transform in spec.transforms:
        operation = str(transform.get("op", "identity")).lower().strip()
        if operation in ("", "identity"):
            continue
        if operation in ("get", "pick"):
            default = transform.get("default", _MISSING)
            value = _path_value(value, str(transform.get("path", "")), default)
        elif operation == "scale":
            value = _finite_number(value, "binding value") * _finite_number(
                transform.get("value", transform.get("factor", 1)), "scale"
            )
        elif operation in ("offset", "add"):
            value = _finite_number(value, "binding value") + _finite_number(
                transform.get("value", 0), "offset"
            )
        elif operation == "clamp":
            number = _finite_number(value, "binding value")
            minimum = _finite_number(transform.get("min", number), "clamp min")
            maximum = _finite_number(transform.get("max", number), "clamp max")
            if minimum > maximum:
                raise ValueError("clamp min cannot exceed max")
            value = max(minimum, min(maximum, number))
        elif operation == "round":
            value = round(
                _finite_number(value, "binding value"),
                int(transform.get("digits", 0)),
            )
        elif operation == "map":
            mapping = transform.get("values", {})
            if not isinstance(mapping, Mapping):
                raise TypeError("map transform values must be an object")
            value = mapping.get(str(value), transform.get("default", value))
        elif operation == "coalesce":
            if value is None or value == "":
                value = transform.get("value")
        elif operation == "bool":
            value = bool(value)
        elif operation == "not":
            value = not bool(value)
        elif operation in ("str", "string"):
            value = str(value)
        elif operation == "length":
            value = len(value)
        elif operation == "json":
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            raise ValueError(f"Unsupported binding transform: {operation}")
    if spec.format:
        values = _FormatValues(value=value)
        if isinstance(source_value, Mapping):
            values.update(source_value)
        if isinstance(value, Mapping):
            values.update(value)
        try:
            value = spec.format.format_map(values)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid binding format: {error}") from error
    return value


def binding_specs_from_document(document: Mapping[str, Any]) -> tuple[BindingSpec, ...]:
    """Compile all element-local binding records in stable document order."""

    specs: list[BindingSpec] = []
    seen: set[str] = set()
    targets: set[tuple[str, str]] = set()
    for element in document.get("elements", []):
        element_id = str(element.get("id", ""))
        bindings = element.get("bindings", [])
        if not isinstance(bindings, list):
            raise TypeError(f"Element {element_id!r} bindings must be a list")
        for index, record in enumerate(bindings):
            if not isinstance(record, Mapping):
                raise TypeError(f"Element {element_id!r} binding must be an object")
            spec = BindingSpec.from_record(element_id, record, index)
            if spec.binding_id in seen:
                raise ValueError(f"Duplicate data-binding ID: {spec.binding_id}")
            target_key = (spec.element_id, spec.target)
            if target_key in targets:
                raise ValueError(
                    f"Element target already has a binding: {spec.element_id}.{spec.target}"
                )
            seen.add(spec.binding_id)
            targets.add(target_key)
            specs.append(spec)
    return tuple(specs)
