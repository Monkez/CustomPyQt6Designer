"""Granular, UI-independent document change records for MonkezCanva."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time_ns
from typing import Any, Mapping
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class OperationEvent:
    """One committed change to a :class:`CanvasDocument`.

    ``origin`` is deliberately excluded from :meth:`to_dict`; it is an in-process
    routing hint (usually the view that initiated the change), not document data.
    Several events may share a revision when a reconcile operation changes more
    than one record atomically.
    """

    action: str
    target_type: str
    target_id: str = ""
    revision: int = 0
    changes: Mapping[str, Any] = field(default_factory=dict)
    previous: Mapping[str, Any] = field(default_factory=dict)
    current: Mapping[str, Any] = field(default_factory=dict)
    operation_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp_ns: int = field(default_factory=time_ns)
    origin: Any = field(default=None, compare=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operationId": self.operation_id,
            "revision": self.revision,
            "action": self.action,
            "targetType": self.target_type,
            "targetId": self.target_id,
            "changes": dict(self.changes),
            "previous": dict(self.previous),
            "current": dict(self.current),
            "timestampNs": self.timestamp_ns,
        }


def changed_fields(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    """Return new values for fields that differ between two JSON mappings."""

    missing = object()
    return {
        key: current.get(key)
        for key in previous.keys() | current.keys()
        if previous.get(key, missing) != current.get(key, missing)
    }
