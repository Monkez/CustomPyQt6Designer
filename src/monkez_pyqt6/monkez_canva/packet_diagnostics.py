"""Portable replay fixtures and bounded per-link packet diagnostics."""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict, deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


PACKET_REPLAY_FORMAT = "monkez-canva-packet-replay"
PACKET_REPLAY_VERSION = 1
MAX_REPLAY_BYTES = 1024 * 1024
MAX_REPLAY_EVENTS = 10_000
REPLAY_BRANCH_POLICIES = ("all", "first", "round_robin")
REPLAY_TERMINAL_STATES = ("completed", "cancelled", "failed", "timed_out")


def _json_value(value: Any, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise TypeError(f"{label} must be finite JSON data") from error


def _finite(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class PacketReplayComparison:
    matched: bool
    expected_status: str
    actual_status: str
    expected_route: tuple[str, ...]
    actual_route: tuple[str, ...]
    mismatches: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "expectedStatus": self.expected_status,
            "actualStatus": self.actual_status,
            "expectedRoute": list(self.expected_route),
            "actualRoute": list(self.actual_route),
            "mismatches": list(self.mismatches),
        }


@dataclass(frozen=True, slots=True)
class PacketReplayFixture:
    """One JSON-safe packet input plus its expected deterministic outcome."""

    fixture_id: str
    entry_id: str
    payload: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    priority: int = 0
    ttl: int = 64
    timeout: float | None = None
    branch_policy: str = "all"
    break_on_arrival: bool = False
    expected_status: str = "completed"
    expected_route: tuple[str, ...] = ()
    expected_events: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        fixture_id = str(self.fixture_id).strip()
        entry_id = str(self.entry_id).strip()
        if not fixture_id:
            raise ValueError("Replay fixture ID cannot be empty")
        if not entry_id:
            raise ValueError("Replay entry ID cannot be empty")
        ttl = int(self.ttl)
        if ttl < 1:
            raise ValueError("Replay TTL must be at least one hop")
        timeout = None if self.timeout is None else _finite(
            self.timeout, "Replay timeout"
        )
        if timeout is not None and timeout <= 0:
            raise ValueError("Replay timeout must be positive")
        if len(self.expected_events) > MAX_REPLAY_EVENTS:
            raise ValueError("Replay fixture contains too many events")
        branch_policy = str(self.branch_policy).strip().lower().replace("-", "_")
        if branch_policy not in REPLAY_BRANCH_POLICIES:
            raise ValueError(f"Unsupported replay branch policy: {self.branch_policy}")
        expected_status = str(self.expected_status).strip().lower()
        if expected_status not in REPLAY_TERMINAL_STATES:
            raise ValueError(f"Unsupported replay terminal state: {self.expected_status}")
        object.__setattr__(self, "fixture_id", fixture_id)
        object.__setattr__(self, "entry_id", entry_id)
        object.__setattr__(self, "payload", _json_value(self.payload, "Replay payload"))
        object.__setattr__(
            self, "metadata", _json_value(dict(self.metadata), "Replay metadata")
        )
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "ttl", ttl)
        object.__setattr__(self, "timeout", timeout)
        object.__setattr__(self, "branch_policy", branch_policy)
        object.__setattr__(self, "break_on_arrival", bool(self.break_on_arrival))
        object.__setattr__(self, "expected_status", expected_status)
        object.__setattr__(
            self, "expected_route", tuple(str(item) for item in self.expected_route)
        )
        object.__setattr__(
            self,
            "expected_events",
            tuple(
                _json_value(dict(event), "Replay event")
                for event in self.expected_events
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": PACKET_REPLAY_FORMAT,
            "version": PACKET_REPLAY_VERSION,
            "fixtureId": self.fixture_id,
            "entryId": self.entry_id,
            "payload": _json_value(self.payload, "Replay payload"),
            "metadata": _json_value(dict(self.metadata), "Replay metadata"),
            "options": {
                "priority": self.priority,
                "ttl": self.ttl,
                "timeout": self.timeout,
                "branchPolicy": self.branch_policy,
                "breakOnArrival": self.break_on_arrival,
            },
            "expected": {
                "status": self.expected_status,
                "route": list(self.expected_route),
                "events": [dict(event) for event in self.expected_events],
            },
        }

    @classmethod
    def from_dict(cls, record: Mapping[str, Any]) -> "PacketReplayFixture":
        raw = dict(record)
        if raw.get("format") != PACKET_REPLAY_FORMAT:
            raise ValueError("Unsupported packet replay format")
        if int(raw.get("version", 0)) != PACKET_REPLAY_VERSION:
            raise ValueError(f"Unsupported packet replay version: {raw.get('version')}")
        options = raw.get("options", {})
        expected = raw.get("expected", {})
        if not isinstance(options, Mapping) or not isinstance(expected, Mapping):
            raise TypeError("Replay options and expected result must be objects")
        events = expected.get("events", ())
        if not isinstance(events, (list, tuple)) or any(
            not isinstance(event, Mapping) for event in events
        ):
            raise TypeError("Replay expected events must be a list of objects")
        route = expected.get("route", ())
        if not isinstance(route, (list, tuple)):
            raise TypeError("Replay expected route must be a list")
        return cls(
            str(raw.get("fixtureId", "")),
            str(raw.get("entryId", "")),
            raw.get("payload"),
            dict(raw.get("metadata", {})),
            int(options.get("priority", 0)),
            int(options.get("ttl", 64)),
            None if options.get("timeout") is None else float(options["timeout"]),
            str(options.get("branchPolicy", "all")),
            bool(options.get("breakOnArrival", False)),
            str(expected.get("status", "completed")),
            tuple(str(item) for item in route),
            tuple(_json_value(dict(event), "Replay event") for event in events),
        )

    def compare(
        self,
        *,
        status: str,
        route: Iterable[str],
        events: Iterable[Mapping[str, Any]] = (),
    ) -> PacketReplayComparison:
        actual_route = tuple(str(item) for item in route)
        mismatches: list[str] = []
        if str(status) != self.expected_status:
            mismatches.append(
                f"status: expected {self.expected_status}, got {status}"
            )
        if actual_route != self.expected_route:
            mismatches.append(
                f"route: expected {list(self.expected_route)}, got {list(actual_route)}"
            )
        expected_signatures = tuple(
            (str(event.get("event", "")), str(event.get("objectId", "")))
            for event in self.expected_events
        )
        actual_signatures = tuple(
            (str(event.get("event", "")), str(event.get("objectId", "")))
            for event in events
        )
        if expected_signatures and expected_signatures != actual_signatures:
            mismatches.append("event sequence diverged")
        return PacketReplayComparison(
            not mismatches,
            self.expected_status,
            str(status),
            self.expected_route,
            actual_route,
            tuple(mismatches),
        )


def build_packet_replay_fixture(
    ticket: Mapping[str, Any],
    events: Iterable[Mapping[str, Any]],
    *,
    fixture_id: str = "",
) -> PacketReplayFixture:
    snapshot = dict(ticket)
    created_at = _finite(snapshot.get("createdAt", 0.0), "Ticket createdAt")
    normalized_events = []
    for event in events:
        raw = dict(event)
        normalized_events.append({
            "offset": round(max(0.0, _finite(raw.get("timestamp", created_at), "Event timestamp") - created_at), 6),
            "event": str(raw.get("event", "")),
            "objectId": str(raw.get("objectId", "")),
            "detail": _json_value(dict(raw.get("detail", {})), "Replay event detail"),
        })
    metadata = {
        str(key): value for key, value in dict(snapshot.get("metadata", {})).items()
        if not str(key).startswith("_monkezReplay")
    }
    return PacketReplayFixture(
        fixture_id or f"replay-{snapshot.get('messageId', 'packet')}",
        str(snapshot.get("entryId", "")),
        snapshot.get("payload"),
        metadata,
        int(snapshot.get("priority", 0)),
        int(snapshot.get("ttl", 64)),
        snapshot.get("timeout"),
        str(snapshot.get("branchPolicy", "all")),
        bool(snapshot.get("breakOnArrival", False)),
        str(snapshot.get("status", "completed")),
        tuple(str(item) for item in snapshot.get("visited", ())),
        tuple(normalized_events),
    )


def encode_packet_replay(fixture: PacketReplayFixture) -> bytes:
    payload = json.dumps(
        fixture.to_dict(), ensure_ascii=False, allow_nan=False,
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > MAX_REPLAY_BYTES:
        raise ValueError("Packet replay fixture is too large")
    return payload


def decode_packet_replay(data: bytes | str | Mapping[str, Any]) -> PacketReplayFixture:
    if isinstance(data, Mapping):
        record = dict(data)
        try:
            serialized = json.dumps(
                record, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise TypeError("Packet replay fixture must be finite JSON data") from error
        if len(serialized) > MAX_REPLAY_BYTES:
            raise ValueError("Packet replay fixture is too large")
    else:
        payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        if len(payload) > MAX_REPLAY_BYTES:
            raise ValueError("Packet replay fixture is too large")
        try:
            record = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Invalid packet replay JSON") from error
    if not isinstance(record, Mapping):
        raise TypeError("Packet replay root must be an object")
    return PacketReplayFixture.from_dict(record)


@dataclass(slots=True)
class _LinkState:
    started: int = 0
    arrived: int = 0
    failed: int = 0
    timed_out: int = 0
    cancelled: int = 0
    first_event: float | None = None
    last_event: float | None = None
    pending: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    latencies: deque[float] = field(default_factory=deque)
    arrivals: deque[float] = field(default_factory=deque)


class PacketLinkMetricsTracker:
    """Pairs segment events and retains bounded latency/throughput samples."""

    def __init__(self, *, max_samples: int = 512) -> None:
        self._max_samples = max(10, int(max_samples))
        self._links: dict[str, _LinkState] = {}

    def observe(
        self,
        event: str,
        message_id: str,
        object_id: str,
        timestamp: float,
    ) -> None:
        event = str(event)
        message_id = str(message_id)
        object_id = str(object_id)
        now = _finite(timestamp, "Metric timestamp")
        if event == "segment_started" and object_id:
            state = self._state(object_id)
            state.started += 1
            state.pending[message_id].append(now)
            self._touch(state, now)
        elif event == "segment_arrived" and object_id:
            state = self._state(object_id)
            starts = state.pending.get(message_id)
            if starts:
                started = starts.popleft()
                if not starts:
                    state.pending.pop(message_id, None)
                self._append(state.latencies, max(0.0, now - started))
            state.arrived += 1
            self._append(state.arrivals, now)
            self._touch(state, now)
        elif event in ("completed", "failed", "timed_out", "cancelled"):
            for state in self._links.values():
                starts = state.pending.pop(message_id, ())
                count = len(starts)
                if not count:
                    continue
                if event == "completed":
                    pass
                elif event == "timed_out":
                    state.timed_out += count
                elif event == "cancelled":
                    state.cancelled += count
                else:
                    state.failed += count
                self._touch(state, now)

    def snapshots(
        self,
        *,
        object_id: str = "",
        now: float | None = None,
        window: float = 60.0,
    ) -> tuple[dict[str, Any], ...]:
        current = _finite(
            now if now is not None else max(
                (state.last_event or 0.0 for state in self._links.values()),
                default=0.0,
            ),
            "Metric time",
        )
        window = max(0.001, _finite(window, "Metric window"))
        links = (
            ((str(object_id), self._links[str(object_id)]),)
            if object_id and str(object_id) in self._links
            else () if object_id else tuple(sorted(self._links.items()))
        )
        return tuple(self._snapshot(key, state, current, window) for key, state in links)

    def reset(self, object_id: str = "") -> int:
        if object_id:
            return int(self._links.pop(str(object_id), None) is not None)
        count = len(self._links)
        self._links.clear()
        return count

    def _state(self, object_id: str) -> _LinkState:
        state = self._links.get(object_id)
        if state is None:
            state = _LinkState(
                latencies=deque(maxlen=self._max_samples),
                arrivals=deque(maxlen=self._max_samples),
            )
            self._links[object_id] = state
        return state

    @staticmethod
    def _touch(state: _LinkState, timestamp: float) -> None:
        state.first_event = timestamp if state.first_event is None else state.first_event
        state.last_event = timestamp

    def _append(self, values: deque[float], value: float) -> None:
        values.append(value)

    @staticmethod
    def _percentile(values: tuple[float, ...], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, math.ceil(percentile * len(ordered)) - 1))
        return ordered[index]

    def _snapshot(
        self, object_id: str, state: _LinkState, now: float, window: float
    ) -> dict[str, Any]:
        latencies = tuple(state.latencies)
        recent = sum(1 for timestamp in state.arrivals if timestamp >= now - window)
        dropped = state.failed + state.timed_out + state.cancelled
        return {
            "objectId": object_id,
            "started": state.started,
            "arrived": state.arrived,
            "inFlight": sum(len(starts) for starts in state.pending.values()),
            "failed": state.failed,
            "timedOut": state.timed_out,
            "cancelled": state.cancelled,
            "dropped": dropped,
            "deliveryRate": state.arrived / state.started if state.started else 0.0,
            "throughputPerSecond": recent / window,
            "sampleWindow": window,
            "latencySamples": len(latencies),
            "latencyMs": {
                "average": statistics.fmean(latencies) * 1000 if latencies else 0.0,
                "minimum": min(latencies) * 1000 if latencies else 0.0,
                "maximum": max(latencies) * 1000 if latencies else 0.0,
                "p50": self._percentile(latencies, 0.50) * 1000,
                "p95": self._percentile(latencies, 0.95) * 1000,
            },
            "firstEvent": state.first_event,
            "lastEvent": state.last_event,
        }
