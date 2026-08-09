"""Qt-free document health reports and stable semantic diffs for MonkezCanva."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .models import CanvasDocument
from .persistence import AssetIntegrityIssue
from .registry import ElementRegistry


DIAGNOSTIC_SEVERITIES = ("info", "warning", "error")
DIFF_ACTIONS = ("added", "removed", "modified")
_COLLECTIONS = (
    ("elements", "element"),
    ("connectors", "connector"),
    ("groups", "group"),
    ("resources", "resource"),
)
_TOP_LEVEL_KEYS = {"format", "version", "scene", *(name for name, _kind in _COLLECTIONS)}


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _document_dict(document: CanvasDocument | Mapping[str, Any]) -> dict[str, Any]:
    value = document.to_dict() if isinstance(document, CanvasDocument) else dict(document)
    return json.loads(json.dumps(_plain(value), ensure_ascii=False, allow_nan=False))


def _canonical_document(document: Mapping[str, Any]) -> dict[str, Any]:
    result = _plain(document)
    for collection, _kind in _COLLECTIONS:
        records = result.get(collection, [])
        if isinstance(records, list):
            result[collection] = sorted(
                records,
                key=lambda record: str(record.get("id", ""))
                if isinstance(record, Mapping)
                else "",
            )
    return result


def document_fingerprint(document: CanvasDocument | Mapping[str, Any]) -> str:
    """Return an order-insensitive SHA-256 fingerprint of canonical document JSON."""

    payload = _canonical_document(_document_dict(document))
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class DocumentDiagnosticIssue:
    severity: str
    code: str
    message: str
    target_type: str = "document"
    target_id: str = ""
    path: str = ""
    suggestion: str = ""

    def __post_init__(self) -> None:
        severity = str(self.severity).strip().lower()
        if severity not in DIAGNOSTIC_SEVERITIES:
            raise ValueError(f"Unsupported diagnostic severity: {severity}")
        if not str(self.code).strip():
            raise ValueError("Diagnostic issue code cannot be empty")
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "code", str(self.code).strip())
        object.__setattr__(self, "message", str(self.message).strip())
        object.__setattr__(self, "target_type", str(self.target_type).strip() or "document")
        object.__setattr__(self, "target_id", str(self.target_id).strip())
        object.__setattr__(self, "path", str(self.path).strip())
        object.__setattr__(self, "suggestion", str(self.suggestion).strip())

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "targetType": self.target_type,
            "targetId": self.target_id,
            "path": self.path,
            "suggestion": self.suggestion,
        }


@dataclass(frozen=True, slots=True)
class DocumentDiagnosticsReport:
    fingerprint: str
    issues: tuple[DocumentDiagnosticIssue, ...]
    metrics: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "fingerprint", str(self.fingerprint))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "metrics", MappingProxyType(_plain(self.metrics)))

    @property
    def severity(self) -> str:
        severities = {issue.severity for issue in self.issues}
        return "error" if "error" in severities else "warning" if "warning" in severities else "healthy"

    @property
    def counts(self) -> dict[str, int]:
        values = Counter(issue.severity for issue in self.issues)
        return {severity: values[severity] for severity in DIAGNOSTIC_SEVERITIES}

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "severity": self.severity,
            "valid": self.valid,
            "counts": self.counts,
            "metrics": _plain(self.metrics),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class DocumentChange:
    action: str
    target_type: str
    target_id: str
    fields: tuple[str, ...] = ()
    before: Any = None
    after: Any = None

    def __post_init__(self) -> None:
        action = str(self.action).strip().lower()
        if action not in DIFF_ACTIONS:
            raise ValueError(f"Unsupported document diff action: {action}")
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "target_type", str(self.target_type).strip())
        object.__setattr__(self, "target_id", str(self.target_id).strip())
        object.__setattr__(self, "fields", tuple(str(field) for field in self.fields))

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "targetType": self.target_type,
            "targetId": self.target_id,
            "fields": list(self.fields),
            "before": _plain(self.before),
            "after": _plain(self.after),
        }


@dataclass(frozen=True, slots=True)
class DocumentDiff:
    before_fingerprint: str
    after_fingerprint: str
    changes: tuple[DocumentChange, ...]

    @property
    def identical(self) -> bool:
        return not self.changes

    @property
    def counts(self) -> dict[str, int]:
        values = Counter(change.action for change in self.changes)
        return {action: values[action] for action in DIFF_ACTIONS}

    def to_dict(self) -> dict[str, Any]:
        return {
            "identical": self.identical,
            "beforeFingerprint": self.before_fingerprint,
            "afterFingerprint": self.after_fingerprint,
            "counts": self.counts,
            "changes": [change.to_dict() for change in self.changes],
        }


def _changed_paths(before: Any, after: Any, prefix: str = "") -> tuple[str, ...]:
    if before == after:
        return ()
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        paths: list[str] = []
        for key in sorted(set(before) | set(after), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                paths.append(path)
            else:
                paths.extend(_changed_paths(before[key], after[key], path))
        return tuple(paths)
    return (prefix or "$",)


def _records(document: Mapping[str, Any], collection: str) -> dict[str, Any]:
    records: dict[str, Any] = {}
    values = document.get(collection, [])
    if not isinstance(values, list):
        return records
    for index, record in enumerate(values):
        if isinstance(record, Mapping):
            records[str(record.get("id", f"#{index}"))] = _plain(record)
    return records


def diff_documents(
    before: CanvasDocument | Mapping[str, Any],
    after: CanvasDocument | Mapping[str, Any],
) -> DocumentDiff:
    """Compare two documents by stable object ID instead of array position."""

    left = _document_dict(before)
    right = _document_dict(after)
    changes: list[DocumentChange] = []
    left_scene = left.get("scene", {})
    right_scene = right.get("scene", {})
    if left_scene != right_scene:
        changes.append(
            DocumentChange(
                "modified", "scene", "scene", _changed_paths(left_scene, right_scene),
                left_scene, right_scene,
            )
        )
    for collection, target_type in _COLLECTIONS:
        left_records = _records(left, collection)
        right_records = _records(right, collection)
        for target_id in sorted(set(left_records) | set(right_records)):
            if target_id not in left_records:
                changes.append(DocumentChange("added", target_type, target_id, (), None, right_records[target_id]))
            elif target_id not in right_records:
                changes.append(DocumentChange("removed", target_type, target_id, (), left_records[target_id], None))
            elif left_records[target_id] != right_records[target_id]:
                changes.append(
                    DocumentChange(
                        "modified", target_type, target_id,
                        _changed_paths(left_records[target_id], right_records[target_id]),
                        left_records[target_id], right_records[target_id],
                    )
                )
    left_metadata = {key: value for key, value in left.items() if key not in _TOP_LEVEL_KEYS}
    right_metadata = {key: value for key, value in right.items() if key not in _TOP_LEVEL_KEYS}
    if left_metadata != right_metadata:
        changes.append(
            DocumentChange(
                "modified", "document", "metadata",
                _changed_paths(left_metadata, right_metadata), left_metadata, right_metadata,
            )
        )
    return DocumentDiff(document_fingerprint(left), document_fingerprint(right), tuple(changes))


def _graph_metrics(document: CanvasDocument) -> tuple[int, int]:
    element_ids = {element.id for element in document.elements}
    adjacency: dict[str, set[str]] = defaultdict(set)
    degrees = Counter({element_id: 0 for element_id in element_ids})
    for connector in document.connectors:
        adjacency[connector.source].add(connector.target)
        adjacency[connector.target].add(connector.source)
        degrees[connector.source] += 1
        degrees[connector.target] += 1
    components = 0
    unseen = set(element_ids)
    while unseen:
        components += 1
        queue = deque((unseen.pop(),))
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current] & unseen:
                unseen.remove(neighbor)
                queue.append(neighbor)
    return components, sum(1 for value in degrees.values() if value == 0)


def diagnose_document(
    document: CanvasDocument | Mapping[str, Any],
    *,
    registry: ElementRegistry | None = None,
    asset_issues: Iterable[AssetIntegrityIssue | str] = (),
) -> DocumentDiagnosticsReport:
    """Build a structured health report without changing or normalizing input state."""

    try:
        raw = _document_dict(document)
        fingerprint = document_fingerprint(raw)
    except (TypeError, ValueError, OverflowError) as error:
        issue = DocumentDiagnosticIssue(
            "error", "document.non-json", str(error),
            suggestion="Replace non-finite or executable values with finite JSON data."
        )
        return DocumentDiagnosticsReport("", (issue,), {"jsonBytes": 0})
    issues: list[DocumentDiagnosticIssue] = []
    try:
        model = CanvasDocument.from_dict(raw, allow_newer=True)
    except (TypeError, ValueError, KeyError) as error:
        issue = DocumentDiagnosticIssue(
            "error", "document.invalid", str(error), suggestion="Repair the reported record before loading it."
        )
        return DocumentDiagnosticsReport(
            fingerprint,
            (issue,),
            {"jsonBytes": len(json.dumps(raw, ensure_ascii=False).encode("utf-8"))},
        )

    if model.is_read_only:
        issues.append(
            DocumentDiagnosticIssue(
                "warning", "document.newer-version", model.read_only_reason,
                suggestion="Open with a newer MonkezCanva runtime before editing."
            )
        )
    component_counts = Counter(element.type for element in model.elements)
    if registry is not None:
        for element in model.elements:
            definition = registry.definition(element.type)
            if definition is None:
                issues.append(
                    DocumentDiagnosticIssue(
                        "warning", "component.missing", f"Component type {element.type!r} is not registered.",
                        "element", element.id, "type", "Install or enable the component plugin that owns this type."
                    )
                )
                continue
            try:
                definition.prepare_record(element.to_dict(), allow_newer=True)
            except (TypeError, ValueError, KeyError) as error:
                issues.append(
                    DocumentDiagnosticIssue(
                        "error", "component.invalid", str(error), "element", element.id,
                        suggestion="Correct the component properties or run its migration."
                    )
                )
            component_version = int(element.properties.get("componentVersion", 1))
            if component_version > definition.schema_version:
                issues.append(
                    DocumentDiagnosticIssue(
                        "warning", "component.newer-version",
                        f"Component requires schema {component_version}; registered schema is {definition.schema_version}.",
                        "element", element.id, "componentVersion",
                        "Install the newer component plugin before editing this element."
                    )
                )
    for element in model.elements:
        port_ids = [port.id for port in element.ports]
        duplicates = sorted(port_id for port_id, count in Counter(port_ids).items() if count > 1)
        if duplicates:
            issues.append(
                DocumentDiagnosticIssue(
                    "error", "port.duplicate-id", f"Duplicate port IDs: {', '.join(duplicates)}.",
                    "element", element.id, "ports", "Give every port on the element a unique ID."
                )
            )
    for group in model.groups:
        if not group.members:
            issues.append(
                DocumentDiagnosticIssue(
                    "info", "group.empty", "Group has no members.", "group", group.id,
                    "members", "Add members or remove the empty group."
                )
            )
    for resource in model.resources:
        if not resource.uri.strip():
            issues.append(
                DocumentDiagnosticIssue(
                    "warning", "resource.missing-uri", "Resource has no URI.",
                    "resource", resource.id, "uri", "Assign a project-relative managed asset URI."
                )
            )
    for asset_issue in asset_issues:
        if isinstance(asset_issue, AssetIntegrityIssue):
            message = asset_issue.message()
            target_id = asset_issue.path
        else:
            message = str(asset_issue)
            target_id = ""
        issues.append(
            DocumentDiagnosticIssue(
                "error", "asset.integrity", message, "asset", target_id,
                suggestion="Restore the asset or save the project again to rebuild its manifest."
            )
        )
    connected_components, isolated_elements = _graph_metrics(model)
    metrics = {
        "elements": len(model.elements),
        "connectors": len(model.connectors),
        "groups": len(model.groups),
        "resources": len(model.resources),
        "componentTypes": dict(sorted(component_counts.items())),
        "connectedComponents": connected_components,
        "isolatedElements": isolated_elements,
        "jsonBytes": len(json.dumps(raw, ensure_ascii=False).encode("utf-8")),
        "readOnly": model.is_read_only,
    }
    return DocumentDiagnosticsReport(fingerprint, tuple(issues), metrics)
