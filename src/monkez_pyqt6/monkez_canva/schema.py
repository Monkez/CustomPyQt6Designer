"""Versioned JSON contract for portable MonkezCanva documents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping


DOCUMENT_FORMAT = "monkez-canva"
DOCUMENT_VERSION = 1

DocumentMigration = Callable[[dict[str, Any]], Mapping[str, Any]]


DOCUMENT_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://monkez.dev/schemas/monkez-canva/document-v1.json",
    "title": "MonkezCanva document",
    "type": "object",
    "$defs": {
        "port": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "mode": {"enum": ["input", "output", "free"]},
                "side": {"enum": ["left", "right", "top", "bottom"]},
                "label": {"type": "string"},
                "position": {"type": "number", "minimum": 0, "maximum": 1},
                "dataType": {"type": "string", "minLength": 1},
                "unit": {"type": "string"},
                "required": {"type": "boolean"},
                "defaultValue": {},
                "maxConnections": {"type": "integer", "minimum": 0},
                "acceptedTypes": {"type": "array", "items": {"type": "string"}},
                "acceptedUnits": {"type": "array", "items": {"type": "string"}},
                "convertsTo": {"type": "array", "items": {"type": "string"}},
                "tooltip": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    "required": ["format", "version", "scene", "elements", "connectors"],
    "properties": {
        "format": {"const": DOCUMENT_FORMAT},
        "version": {"type": "integer", "minimum": 1},
        "scene": {"type": "object"},
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "type": {"type": "string", "minLength": 1},
                    "componentVersion": {"type": "integer", "minimum": 1},
                    "ports": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/port"},
                    },
                },
                "additionalProperties": True,
            },
        },
        "connectors": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "source", "target"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "type": {"const": "connector"},
                    "source": {"type": "string", "minLength": 1},
                    "target": {"type": "string", "minLength": 1},
                },
                "additionalProperties": True,
            },
        },
        "groups": {"type": "array", "items": {"type": "object"}},
        "resources": {"type": "array", "items": {"type": "object"}},
        "assetManifest": {"type": "object"},
    },
    "additionalProperties": True,
}


DOCUMENT_MIGRATIONS: dict[int, DocumentMigration] = {}


@dataclass(frozen=True, slots=True)
class DocumentMigrationResult:
    payload: dict[str, Any]
    source_version: int
    migrated: bool = False
    read_only: bool = False


def _copy_json(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise TypeError("MonkezCanva document values must be finite JSON data") from error


def validate_document_shape(data: Mapping[str, Any]) -> None:
    """Validate the stable structural subset represented by the public schema."""

    if not isinstance(data, Mapping):
        raise TypeError("MonkezCanva document must be a JSON object")
    if data.get("format") != DOCUMENT_FORMAT:
        raise ValueError("Unsupported MonkezCanva document format")
    version = data.get("version", DOCUMENT_VERSION)
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("MonkezCanva document version must be a positive integer")
    if not isinstance(data.get("scene", {}), Mapping):
        raise TypeError("MonkezCanva scene must be a JSON object")
    for collection in ("elements", "connectors", "groups", "resources"):
        records = data.get(collection, [])
        if not isinstance(records, list):
            raise TypeError(f"MonkezCanva {collection} must be a JSON array")
        if any(not isinstance(record, Mapping) for record in records):
            raise TypeError(f"MonkezCanva {collection} entries must be JSON objects")
    for entry in data.get("elements", []):
        if not str(entry.get("id", "")).strip() or not str(entry.get("type", "")).strip():
            raise ValueError("MonkezCanva elements require non-empty id and type")
        component_version = entry.get("componentVersion", 1)
        if isinstance(component_version, bool) or not isinstance(component_version, int) or component_version < 1:
            raise ValueError("MonkezCanva componentVersion must be a positive integer")
    for entry in data.get("connectors", []):
        if any(not str(entry.get(key, "")).strip() for key in ("id", "source", "target")):
            raise ValueError("MonkezCanva connectors require id, source and target")


def migrate_document(
    data: Mapping[str, Any], *, allow_newer: bool = False
) -> DocumentMigrationResult:
    """Validate and migrate a document without importing Qt.

    A newer document is returned structurally intact only when ``allow_newer``
    is requested. Callers must then enforce read-only behavior.
    """

    payload = _copy_json(dict(data))
    validate_document_shape(payload)
    source_version = int(payload.get("version", DOCUMENT_VERSION))
    if source_version > DOCUMENT_VERSION:
        if not allow_newer:
            raise ValueError(
                f"MonkezCanva document version {source_version} is newer than supported {DOCUMENT_VERSION}"
            )
        return DocumentMigrationResult(payload, source_version, read_only=True)
    migrated = False
    version = source_version
    while version < DOCUMENT_VERSION:
        migration = DOCUMENT_MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(f"No MonkezCanva document migration from version {version}")
        payload = _copy_json(dict(migration(payload)))
        version += 1
        payload["format"] = DOCUMENT_FORMAT
        payload["version"] = version
        validate_document_shape(payload)
        migrated = True
    return DocumentMigrationResult(payload, source_version, migrated=migrated)
