"""Qt-free packet lifecycle, tracing and breakpoint state for MonkezCanva."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


MESSAGE_STATES = (
    "queued",
    "in_flight",
    "paused",
    "completed",
    "cancelled",
    "failed",
    "timed_out",
)
TERMINAL_MESSAGE_STATES = frozenset(("completed", "cancelled", "failed", "timed_out"))
BRANCH_POLICIES = ("all", "first", "round_robin")


@dataclass(frozen=True, slots=True)
class RuntimeTraceEvent:
    sequence: int
    timestamp: float
    event: str
    message_id: str
    object_id: str = ""
    detail: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "event": self.event,
            "messageId": self.message_id,
            "objectId": self.object_id,
            "detail": dict(self.detail),
        }


@dataclass(slots=True)
class MessageTicket:
    message_id: str
    entry_id: str
    payload: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    ttl: int = 64
    timeout: float | None = None
    branch_policy: str = "all"
    break_on_arrival: bool = False
    created_at: float = 0.0
    status: str = "queued"
    pending_segments: int = 0
    hop_count: int = 0
    visited: list[str] = field(default_factory=list)
    error: str = ""
    completed_at: float | None = None
    _branch_cursor: int = 0

    @property
    def done(self) -> bool:
        return self.status in TERMINAL_MESSAGE_STATES

    @property
    def elapsed(self) -> float:
        end = self.completed_at if self.completed_at is not None else time.monotonic()
        return max(0.0, end - self.created_at)

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        end = self.completed_at if self.completed_at is not None else (
            time.monotonic() if now is None else float(now)
        )
        return {
            "messageId": self.message_id,
            "entryId": self.entry_id,
            "payload": self.payload,
            "metadata": dict(self.metadata),
            "priority": self.priority,
            "ttl": self.ttl,
            "timeout": self.timeout,
            "branchPolicy": self.branch_policy,
            "breakOnArrival": self.break_on_arrival,
            "createdAt": self.created_at,
            "status": self.status,
            "pendingSegments": self.pending_segments,
            "hopCount": self.hop_count,
            "visited": list(self.visited),
            "error": self.error,
            "completedAt": self.completed_at,
            "elapsed": max(0.0, end - self.created_at),
        }


class PacketRuntime:
    """Own transient tickets and a bounded event trace without importing Qt."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_trace_events: int = 2000,
        event_sink: Callable[[RuntimeTraceEvent, MessageTicket], None] | None = None,
    ) -> None:
        self._clock = clock
        self._max_trace_events = max(10, int(max_trace_events))
        self._event_sink = event_sink
        self._tickets: dict[str, MessageTicket] = {}
        self._trace: list[RuntimeTraceEvent] = []
        self._sequence = 0
        self._paused = False
        self._breakpoints: set[str] = set()

    @property
    def paused(self) -> bool:
        return self._paused

    def create(
        self,
        message_id: str,
        entry_id: str,
        *,
        payload: Any = None,
        metadata: Mapping[str, Any] | None = None,
        priority: int = 0,
        ttl: int = 64,
        timeout: float | None = None,
        branch_policy: str = "all",
        break_on_arrival: bool = False,
    ) -> MessageTicket:
        message_id = str(message_id).strip()
        if not message_id:
            raise ValueError("Message id cannot be empty")
        if message_id in self._tickets and not self._tickets[message_id].done:
            raise ValueError(f"Message id is already in flight: {message_id}")
        policy = str(branch_policy).lower().strip().replace("-", "_")
        if policy not in BRANCH_POLICIES:
            raise ValueError(f"Unsupported packet branch policy: {branch_policy}")
        ttl = int(ttl)
        if ttl < 1:
            raise ValueError("Packet TTL must be at least one hop")
        resolved_timeout = None if timeout is None else float(timeout)
        if resolved_timeout is not None and resolved_timeout <= 0:
            raise ValueError("Packet timeout must be positive")
        ticket = MessageTicket(
            message_id=message_id,
            entry_id=str(entry_id),
            payload=payload,
            metadata=dict(metadata or {}),
            priority=int(priority),
            ttl=ttl,
            timeout=resolved_timeout,
            branch_policy=policy,
            break_on_arrival=bool(break_on_arrival),
            created_at=self._clock(),
        )
        self._tickets[message_id] = ticket
        self._record("created", ticket, ticket.entry_id, {
            "priority": ticket.priority,
            "ttl": ticket.ttl,
            "branchPolicy": ticket.branch_policy,
        })
        return ticket

    def ticket(self, message_id: str) -> MessageTicket | None:
        return self._tickets.get(str(message_id))

    def tickets(self, *, include_completed: bool = True) -> tuple[MessageTicket, ...]:
        values = self._tickets.values()
        if not include_completed:
            values = (ticket for ticket in values if not ticket.done)
        return tuple(sorted(values, key=lambda ticket: (-ticket.priority, ticket.created_at)))

    def start_segment(self, message_id: str, object_id: str) -> MessageTicket:
        ticket = self._required_active(message_id)
        object_id = str(object_id)
        if ticket.hop_count >= ticket.ttl:
            return self.fail(message_id, "Packet TTL exceeded", status="failed")
        ticket.pending_segments += 1
        ticket.hop_count += 1
        if object_id not in ticket.visited:
            ticket.visited.append(object_id)
        ticket.status = "paused" if self._paused else "in_flight"
        self._record("segment_started", ticket, object_id, {
            "pending": ticket.pending_segments,
            "hop": ticket.hop_count,
        })
        return ticket

    def arrive_segment(self, message_id: str, object_id: str) -> MessageTicket:
        ticket = self._required_active(message_id)
        ticket.pending_segments = max(0, ticket.pending_segments - 1)
        self._record("segment_arrived", ticket, str(object_id), {
            "pending": ticket.pending_segments,
        })
        return ticket

    def select_branches(
        self, message_id: str, connector_ids: Iterable[str]
    ) -> tuple[str, ...]:
        ticket = self._required_active(message_id)
        candidates = tuple(dict.fromkeys(str(value) for value in connector_ids))
        if not candidates:
            return ()
        if ticket.branch_policy == "all":
            selected = candidates
        elif ticket.branch_policy == "first":
            selected = candidates[:1]
        else:
            selected = (candidates[ticket._branch_cursor % len(candidates)],)
            ticket._branch_cursor += 1
        self._record("branches_selected", ticket, "", {
            "policy": ticket.branch_policy,
            "selected": list(selected),
            "available": len(candidates),
        })
        return selected

    def complete(self, message_id: str, object_id: str = "") -> MessageTicket:
        ticket = self._required_active(message_id)
        ticket.pending_segments = 0
        ticket.status = "completed"
        ticket.completed_at = self._clock()
        self._record("completed", ticket, str(object_id))
        return ticket

    def cancel(self, message_id: str, reason: str = "Cancelled") -> MessageTicket:
        return self.fail(message_id, reason, status="cancelled")

    def fail(
        self, message_id: str, reason: str, *, status: str = "failed"
    ) -> MessageTicket:
        if status not in ("cancelled", "failed", "timed_out"):
            raise ValueError(f"Unsupported terminal packet status: {status}")
        ticket = self._required_active(message_id)
        ticket.pending_segments = 0
        ticket.status = status
        ticket.error = str(reason)
        ticket.completed_at = self._clock()
        self._record(status, ticket, "", {"reason": ticket.error})
        return ticket

    def expire(self, now: float | None = None) -> tuple[MessageTicket, ...]:
        current = self._clock() if now is None else float(now)
        expired = []
        for ticket in tuple(self._tickets.values()):
            if (
                not ticket.done
                and ticket.timeout is not None
                and current - ticket.created_at >= ticket.timeout
            ):
                expired.append(self.fail(
                    ticket.message_id,
                    f"Packet timed out after {ticket.timeout:g}s",
                    status="timed_out",
                ))
        return tuple(expired)

    def pause(self, reason: str = "Paused") -> bool:
        if self._paused:
            return False
        self._paused = True
        for ticket in self._tickets.values():
            if not ticket.done and ticket.status == "in_flight":
                ticket.status = "paused"
                self._record("paused", ticket, "", {"reason": str(reason)})
        return True

    def resume(self) -> bool:
        if not self._paused:
            return False
        self._paused = False
        for ticket in self._tickets.values():
            if not ticket.done and ticket.status == "paused":
                ticket.status = "in_flight"
                self._record("resumed", ticket)
        return True

    def set_breakpoint(self, object_id: str, enabled: bool = True) -> bool:
        object_id = str(object_id).strip()
        if not object_id:
            raise ValueError("Breakpoint object id cannot be empty")
        before = object_id in self._breakpoints
        if enabled:
            self._breakpoints.add(object_id)
        else:
            self._breakpoints.discard(object_id)
        return before != enabled

    def breakpoints(self) -> tuple[str, ...]:
        return tuple(sorted(self._breakpoints))

    def has_breakpoint(self, object_id: str) -> bool:
        return str(object_id) in self._breakpoints

    def should_break(self, object_id: str, message_id: str) -> bool:
        ticket = self._required_active(message_id)
        return ticket.break_on_arrival or str(object_id) in self._breakpoints

    def breakpoint_hit(self, object_id: str, message_id: str) -> MessageTicket:
        ticket = self._required_active(message_id)
        self.pause(f"Breakpoint at {object_id}")
        ticket.status = "paused"
        self._record("breakpoint", ticket, str(object_id))
        return ticket

    def trace(
        self, *, message_id: str = "", event: str = "", limit: int | None = None
    ) -> tuple[RuntimeTraceEvent, ...]:
        values = self._trace
        if message_id:
            values = [item for item in values if item.message_id == str(message_id)]
        if event:
            values = [item for item in values if item.event == str(event)]
        if limit is not None:
            values = values[-max(0, int(limit)):]
        return tuple(values)

    def clear_completed(self) -> int:
        removable = [key for key, ticket in self._tickets.items() if ticket.done]
        for key in removable:
            self._tickets.pop(key, None)
        return len(removable)

    def discard(self, message_id: str) -> bool:
        ticket = self._tickets.get(str(message_id))
        if ticket is None or not ticket.done:
            return False
        self._tickets.pop(str(message_id), None)
        return True

    def clear(self) -> None:
        self._tickets.clear()
        self._trace.clear()
        self._breakpoints.clear()
        self._paused = False

    def _required_active(self, message_id: str) -> MessageTicket:
        ticket = self._tickets.get(str(message_id))
        if ticket is None:
            raise KeyError(f"Unknown message ticket: {message_id}")
        if ticket.done:
            raise RuntimeError(
                f"Message ticket {message_id} is already {ticket.status}"
            )
        return ticket

    def _record(
        self,
        event: str,
        ticket: MessageTicket,
        object_id: str = "",
        detail: Mapping[str, Any] | None = None,
    ) -> RuntimeTraceEvent:
        self._sequence += 1
        trace = RuntimeTraceEvent(
            self._sequence,
            self._clock(),
            str(event),
            ticket.message_id,
            str(object_id),
            dict(detail or {}),
        )
        self._trace.append(trace)
        if len(self._trace) > self._max_trace_events:
            del self._trace[:len(self._trace) - self._max_trace_events]
        if self._event_sink is not None:
            self._event_sink(trace, ticket)
        return trace
