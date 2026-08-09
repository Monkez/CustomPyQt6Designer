"""Qt-free clipboard contract for copying MonkezCanva graph selections."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


CLIPBOARD_FORMAT = "monkez-canva-selection"
CLIPBOARD_VERSION = 1
CANVAS_CLIPBOARD_MIME_TYPE = "application/x-monkez-canva-selection+json"
MAX_CLIPBOARD_BYTES = 5 * 1024 * 1024
MAX_CLIPBOARD_OBJECTS = 10_000


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def build_selection_payload(
    document: Mapping[str, Any], selected_ids: list[str] | tuple[str, ...]
) -> dict[str, Any]:
    """Build a portable subgraph, including dependencies of selected edges."""

    requested = {str(object_id) for object_id in selected_ids}
    elements = {
        str(record["id"]): record for record in document.get("elements", [])
    }
    connectors = {
        str(record["id"]): record for record in document.get("connectors", [])
    }
    selected_element_ids = requested.intersection(elements)
    selected_connector_ids = requested.intersection(connectors)
    element_ids = set(selected_element_ids)
    for connector_id in selected_connector_ids:
        connector = connectors[connector_id]
        element_ids.update((str(connector["source"]), str(connector["target"])))
    copied_connectors = [
        record
        for record in connectors.values()
        if str(record["id"]) in selected_connector_ids
        or (
            str(record["source"]) in selected_element_ids
            and str(record["target"]) in selected_element_ids
        )
    ]
    return {
        "format": CLIPBOARD_FORMAT,
        "version": CLIPBOARD_VERSION,
        "elements": [_copy(elements[element_id]) for element_id in elements if element_id in element_ids],
        "connectors": [_copy(record) for record in copied_connectors],
    }


def decode_selection_payload(value: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    """Parse and strictly validate an untrusted clipboard subgraph."""

    if isinstance(value, bytes):
        if len(value) > MAX_CLIPBOARD_BYTES:
            raise ValueError("MonkezCanva clipboard payload is too large")
        value = value.decode("utf-8")
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_CLIPBOARD_BYTES:
            raise ValueError("MonkezCanva clipboard payload is too large")
        value = json.loads(value)
    if not isinstance(value, Mapping):
        raise TypeError("MonkezCanva clipboard payload must be a JSON object")
    payload = _copy(dict(value))
    if payload.get("format") != CLIPBOARD_FORMAT:
        raise ValueError("Unsupported MonkezCanva clipboard format")
    if payload.get("version") != CLIPBOARD_VERSION:
        raise ValueError("Unsupported MonkezCanva clipboard version")
    elements = payload.get("elements")
    connectors = payload.get("connectors")
    if not isinstance(elements, list) or not isinstance(connectors, list):
        raise TypeError("MonkezCanva clipboard elements/connectors must be arrays")
    if len(elements) + len(connectors) > MAX_CLIPBOARD_OBJECTS:
        raise ValueError("MonkezCanva clipboard contains too many objects")
    if any(not isinstance(record, dict) for record in (*elements, *connectors)):
        raise TypeError("MonkezCanva clipboard records must be JSON objects")
    element_ids = [str(record.get("id", "")).strip() for record in elements]
    connector_ids = [str(record.get("id", "")).strip() for record in connectors]
    all_ids = [*element_ids, *connector_ids]
    if any(not object_id for object_id in all_ids):
        raise ValueError("MonkezCanva clipboard object IDs cannot be empty")
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("MonkezCanva clipboard object IDs must be unique")
    known_elements = set(element_ids)
    for record in connectors:
        if not str(record.get("source", "")) or not str(record.get("target", "")):
            raise ValueError("MonkezCanva clipboard connectors require endpoints")
        if str(record["source"]) not in known_elements or str(record["target"]) not in known_elements:
            raise ValueError("MonkezCanva clipboard connector endpoints must be included")
    return payload


def remap_selection_payload(
    value: bytes | str | Mapping[str, Any],
    occupied_ids: set[str] | tuple[str, ...] | list[str],
    *,
    offset: tuple[float, float] = (30.0, 30.0),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Return offset records with collision-free IDs and remapped endpoints."""

    payload = decode_selection_payload(value)
    occupied = {str(object_id) for object_id in occupied_ids}
    id_map: dict[str, str] = {}

    def allocate(source_id: str) -> str:
        base = f"{source_id}-copy"
        candidate = base
        suffix = 2
        while candidate in occupied:
            candidate = f"{base}-{suffix}"
            suffix += 1
        occupied.add(candidate)
        id_map[source_id] = candidate
        return candidate

    dx, dy = float(offset[0]), float(offset[1])
    elements: list[dict[str, Any]] = []
    for source in payload["elements"]:
        record = _copy(source)
        source_id = str(record["id"])
        record["id"] = allocate(source_id)
        record["x"] = float(record.get("x", 0.0)) + dx
        record["y"] = float(record.get("y", 0.0)) + dy
        elements.append(record)
    connectors: list[dict[str, Any]] = []
    for source in payload["connectors"]:
        record = _copy(source)
        source_id = str(record["id"])
        record["id"] = allocate(source_id)
        record["source"] = id_map[str(record["source"])]
        record["target"] = id_map[str(record["target"])]
        record["waypoints"] = [
            [float(point[0]) + dx, float(point[1]) + dy]
            for point in record.get("waypoints", [])
        ]
        connectors.append(record)
    return elements, connectors, id_map
