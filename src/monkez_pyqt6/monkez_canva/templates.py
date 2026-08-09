"""Qt-free reusable template manifests and project-local catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .persistence import atomic_write_json


TEMPLATE_FORMAT = "monkez-canva-template"
TEMPLATE_VERSION = 1
TEMPLATE_KINDS = ("subflow",)
MAX_TEMPLATE_BYTES = 5 * 1024 * 1024
MAX_TEMPLATE_OBJECTS = 10_000


def _copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise TypeError("Canvas template values must be finite JSON data") from error


def normalize_template_id(value: str) -> str:
    result = str(value).strip().lower().replace(" ", "-")
    if not result:
        raise ValueError("Canvas template ID cannot be empty")
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in result):
        raise ValueError(
            "Canvas template ID may contain only lowercase letters, digits, '.', '_' and '-'"
        )
    return result


def _validate_subflow(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _copy(dict(payload))
    if result.get("format") != "monkez-subflow" or result.get("version") != 1:
        raise ValueError("Canvas subflow template payload must use monkez-subflow version 1")
    collections = tuple(result.get(key) for key in ("elements", "connectors", "groups"))
    if any(not isinstance(records, list) for records in collections):
        raise TypeError("Canvas subflow elements, connectors and groups must be arrays")
    records = [record for collection in collections for record in collection]
    if len(records) > MAX_TEMPLATE_OBJECTS:
        raise ValueError("Canvas template contains too many objects")
    if any(not isinstance(record, dict) for record in records):
        raise TypeError("Canvas template records must be JSON objects")
    ids = [str(record.get("id", "")).strip() for record in records]
    if any(not object_id for object_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Canvas template object IDs must be non-empty and unique")
    known_elements = {str(record["id"]) for record in result["elements"]}
    known_groups = {str(record["id"]) for record in result["groups"]}
    for connector in result["connectors"]:
        if str(connector.get("source", "")) not in known_elements or str(
            connector.get("target", "")
        ) not in known_elements:
            raise ValueError("Canvas template connector endpoints must be included")
    for group in result["groups"]:
        if any(
            str(member) not in known_elements and str(member) not in known_groups
            for member in group.get("members", ())
        ):
            raise ValueError("Canvas template group members must be included")
    if str(result.get("root", "")) not in known_groups:
        raise ValueError("Canvas template root group must be included")
    return result


@dataclass(frozen=True, slots=True)
class CanvasTemplate:
    template_id: str
    label: str
    kind: str
    payload: Mapping[str, Any]
    description: str = ""
    tags: tuple[str, ...] = ()
    thumbnail: str = ""
    author: str = ""

    def __post_init__(self) -> None:
        template_id = normalize_template_id(self.template_id)
        kind = str(self.kind).strip().lower()
        if kind not in TEMPLATE_KINDS:
            raise ValueError(f"Unsupported canvas template kind: {kind}")
        payload = _validate_subflow(self.payload) if kind == "subflow" else _copy(self.payload)
        tags = tuple(dict.fromkeys(str(tag).strip().lower() for tag in self.tags if str(tag).strip()))
        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "label", str(self.label).strip() or template_id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "description", str(self.description).strip())
        object.__setattr__(self, "tags", tags[:32])
        object.__setattr__(self, "thumbnail", str(self.thumbnail).strip())
        object.__setattr__(self, "author", str(self.author).strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": TEMPLATE_FORMAT,
            "version": TEMPLATE_VERSION,
            "id": self.template_id,
            "label": self.label,
            "kind": self.kind,
            "description": self.description,
            "tags": list(self.tags),
            "thumbnail": self.thumbnail,
            "author": self.author,
            "payload": _copy(self.payload),
        }


def decode_canvas_template(value: bytes | str | Mapping[str, Any]) -> CanvasTemplate:
    if isinstance(value, bytes):
        if len(value) > MAX_TEMPLATE_BYTES:
            raise ValueError("Canvas template is too large")
        value = value.decode("utf-8-sig")
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_TEMPLATE_BYTES:
            raise ValueError("Canvas template is too large")
        value = json.loads(value)
    if not isinstance(value, Mapping):
        raise TypeError("Canvas template must be a JSON object")
    data = dict(value)
    if data.get("format") != TEMPLATE_FORMAT or data.get("version") != TEMPLATE_VERSION:
        raise ValueError("Unsupported MonkezCanva template format or version")
    return CanvasTemplate(
        str(data.get("id", "")),
        str(data.get("label", "")),
        str(data.get("kind", "")),
        data.get("payload", {}),
        str(data.get("description", "")),
        tuple(data.get("tags", ())),
        str(data.get("thumbnail", "")),
        str(data.get("author", "")),
    )


@dataclass(frozen=True, slots=True)
class TemplateCatalogScan:
    templates: tuple[CanvasTemplate, ...]
    errors: tuple[tuple[str, str], ...] = ()


class TemplateCatalog:
    """Portable directory catalog; malformed entries remain isolated."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory).expanduser().resolve()

    def path_for(self, template_id: str) -> Path:
        return self.directory / f"{normalize_template_id(template_id)}.monkez-template.json"

    def save(self, template: CanvasTemplate, *, replace_existing: bool = True) -> Path:
        if not isinstance(template, CanvasTemplate):
            raise TypeError("TemplateCatalog.save expects a CanvasTemplate")
        target = self.path_for(template.template_id)
        if target.exists() and not replace_existing:
            raise FileExistsError(f"Canvas template already exists: {template.template_id}")
        atomic_write_json(target, template.to_dict())
        return target

    def load(self, template_id: str) -> CanvasTemplate:
        source = self.path_for(template_id)
        return decode_canvas_template(source.read_bytes())

    def scan(self, tags: Iterable[str] = ()) -> TemplateCatalogScan:
        requested = {str(tag).strip().lower() for tag in tags if str(tag).strip()}
        templates: list[CanvasTemplate] = []
        errors: list[tuple[str, str]] = []
        if not self.directory.exists():
            return TemplateCatalogScan((), ())
        for source in sorted(self.directory.glob("*.monkez-template.json")):
            try:
                template = decode_canvas_template(source.read_bytes())
                if not requested or requested.issubset(template.tags):
                    templates.append(template)
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
                errors.append((source.name, str(error)))
        templates.sort(key=lambda template: (template.label.casefold(), template.template_id))
        return TemplateCatalogScan(tuple(templates), tuple(errors))
