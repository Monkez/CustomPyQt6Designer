"""Public component metadata registry for MonkezCanva."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping


RecordMigration = Callable[[dict[str, Any]], Mapping[str, Any]]
RendererFactory = Callable[..., Any]
InspectorFactory = Callable[..., Any]

_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "array": (list, tuple),
    "object": (dict,),
    "null": (type(None),),
}


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    return value


def _json_copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(_plain_json(value), ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise TypeError("Element registry values must be finite JSON data") from error


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _validate_schema_value(name: str, value: Any, rule: Mapping[str, Any]) -> None:
    expected = rule.get("type")
    if expected:
        accepted = _JSON_TYPES.get(str(expected))
        if accepted is None:
            raise ValueError(f"Unsupported schema type {expected!r} for {name!r}")
        valid = isinstance(value, accepted)
        if expected in ("number", "integer") and isinstance(value, bool):
            valid = False
        if not valid:
            raise TypeError(f"Property {name!r} must be {expected}")
    if "enum" in rule and value not in rule["enum"]:
        raise ValueError(f"Property {name!r} must be one of {list(rule['enum'])!r}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in rule and value < rule["minimum"]:
            raise ValueError(f"Property {name!r} must be >= {rule['minimum']}")
        if "maximum" in rule and value > rule["maximum"]:
            raise ValueError(f"Property {name!r} must be <= {rule['maximum']}")


def _validate_schema_definition(type_id: str, schema: Mapping[str, Any]) -> None:
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        raise TypeError(f"Element {type_id!r} schema properties must be a mapping")
    required = schema.get("required", ())
    if not isinstance(required, (list, tuple)) or any(not isinstance(key, str) for key in required):
        raise TypeError(f"Element {type_id!r} schema required must be a string list")
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        raise TypeError(f"Element {type_id!r} additionalProperties must be boolean")
    for name, rule in properties.items():
        if not isinstance(rule, Mapping):
            raise TypeError(f"Schema rule for {name!r} must be a mapping")
        expected = rule.get("type")
        if expected is not None and str(expected) not in _JSON_TYPES:
            raise ValueError(f"Unsupported schema type {expected!r} for {name!r}")
        if "enum" in rule and not isinstance(rule["enum"], (list, tuple)):
            raise TypeError(f"Schema enum for {name!r} must be a list")
        for bound in ("minimum", "maximum"):
            if bound in rule and (
                not isinstance(rule[bound], (int, float)) or isinstance(rule[bound], bool)
            ):
                raise TypeError(f"Schema {bound} for {name!r} must be numeric")


@dataclass(frozen=True, slots=True)
class ElementDefinition:
    """Declarative metadata shared by documents, palettes and future plugins."""

    type_id: str
    label: str
    category: str
    default_width: float
    default_height: float
    icon: str = ""
    defaults: Mapping[str, Any] = field(default_factory=dict)
    media_picker: bool = False
    schema: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    migrations: Mapping[int, RecordMigration] = field(default_factory=dict, repr=False)
    renderer_factory: RendererFactory | None = field(default=None, compare=False, repr=False)
    inspector_factory: InspectorFactory | None = field(default=None, compare=False, repr=False)
    plugin_id: str = "builtin"
    plugin_version: str = ""
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        type_id = str(self.type_id).strip().lower()
        if not type_id:
            raise ValueError("MonkezCanva element type ID cannot be empty")
        if float(self.default_width) <= 0 or float(self.default_height) <= 0:
            raise ValueError(f"Element {type_id!r} must have a positive default size")
        if int(self.schema_version) < 1:
            raise ValueError(f"Element {type_id!r} schema version must be >= 1")
        object.__setattr__(self, "type_id", type_id)
        object.__setattr__(self, "label", str(self.label).strip() or type_id.replace("_", " ").title())
        object.__setattr__(self, "category", str(self.category).strip() or "Custom")
        object.__setattr__(self, "icon", str(self.icon).strip() or type_id)
        object.__setattr__(self, "defaults", _freeze_json(_json_copy(dict(self.defaults))))
        object.__setattr__(self, "schema", _freeze_json(_json_copy(dict(self.schema))))
        object.__setattr__(self, "schema_version", int(self.schema_version))
        object.__setattr__(self, "migrations", MappingProxyType(dict(self.migrations)))
        object.__setattr__(self, "plugin_id", str(self.plugin_id).strip() or "application")
        object.__setattr__(self, "plugin_version", str(self.plugin_version).strip())
        object.__setattr__(self, "capabilities", frozenset(str(item) for item in self.capabilities))
        _validate_schema_definition(type_id, self.schema)
        invalid_migrations = [version for version, callback in self.migrations.items() if not isinstance(version, int) or not callable(callback)]
        if invalid_migrations:
            raise TypeError(f"Element {type_id!r} migrations must map integer versions to callables")
        missing_steps = [version for version in range(1, self.schema_version) if version not in self.migrations]
        if missing_steps:
            raise ValueError(f"Element {type_id!r} has missing migrations: {missing_steps}")

    @property
    def default_size(self) -> tuple[float, float]:
        return float(self.default_width), float(self.default_height)

    def prepare_record(
        self, record: Mapping[str, Any], *, allow_newer: bool = False
    ) -> dict[str, Any]:
        """Migrate, default and validate one JSON element record."""
        result = _json_copy(dict(record))
        if str(result.get("type", self.type_id)).lower() != self.type_id:
            raise ValueError(f"Record type does not match definition {self.type_id!r}")
        version = int(result.get("componentVersion", 1))
        if version > self.schema_version:
            if allow_newer:
                return result
            raise ValueError(
                f"Element {self.type_id!r} requires newer schema {version}; supported {self.schema_version}"
            )
        while version < self.schema_version:
            migrated = self.migrations[version](dict(result))
            result = _json_copy(dict(migrated))
            version += 1
            result["componentVersion"] = version
            result["type"] = self.type_id
        for key, value in self.defaults.items():
            result.setdefault(key, _json_copy(value))
        required = tuple(self.schema.get("required", ()))
        missing = [key for key in required if key not in result]
        if missing:
            raise ValueError(f"Element {self.type_id!r} is missing required properties: {missing}")
        properties = self.schema.get("properties", {})
        if not isinstance(properties, Mapping):
            raise TypeError(f"Element {self.type_id!r} schema properties must be a mapping")
        for key, rule in properties.items():
            if key in result:
                if not isinstance(rule, Mapping):
                    raise TypeError(f"Schema rule for {key!r} must be a mapping")
                _validate_schema_value(str(key), result[key], rule)
        if self.schema.get("additionalProperties") is False:
            core = {"id", "type", "componentVersion", "x", "y", "width", "height"}
            unknown = set(result) - core - set(properties)
            if unknown:
                raise ValueError(f"Element {self.type_id!r} has unknown properties: {sorted(unknown)}")
        return result


class ElementRegistry:
    """Ordered, cloneable registry with explicit duplicate handling."""

    def __init__(self, definitions: Iterable[ElementDefinition] = ()) -> None:
        self._definitions: dict[str, ElementDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: ElementDefinition, *, replace_existing: bool = False) -> None:
        if not isinstance(definition, ElementDefinition):
            raise TypeError("ElementRegistry.register expects an ElementDefinition")
        if definition.type_id in self._definitions and not replace_existing:
            raise ValueError(f"Duplicate MonkezCanva element type: {definition.type_id}")
        self._definitions[definition.type_id] = definition

    def unregister(self, type_id: str) -> ElementDefinition:
        key = str(type_id).strip().lower()
        try:
            return self._definitions.pop(key)
        except KeyError as error:
            raise KeyError(f"Unknown MonkezCanva element type: {key}") from error

    def definition(self, type_id: str) -> ElementDefinition | None:
        return self._definitions.get(str(type_id).strip().lower())

    def require(self, type_id: str) -> ElementDefinition:
        definition = self.definition(type_id)
        if definition is None:
            raise KeyError(f"Unknown MonkezCanva element type: {type_id}")
        return definition

    def definitions(self) -> tuple[ElementDefinition, ...]:
        return tuple(self._definitions.values())

    def categories(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.category for item in self._definitions.values()))

    def in_category(self, category: str) -> tuple[ElementDefinition, ...]:
        return tuple(item for item in self._definitions.values() if item.category == category)

    def owned_by(self, plugin_id: str) -> tuple[ElementDefinition, ...]:
        owner = str(plugin_id).strip()
        return tuple(item for item in self._definitions.values() if item.plugin_id == owner)

    def unregister_owner(self, plugin_id: str) -> tuple[ElementDefinition, ...]:
        removed = self.owned_by(plugin_id)
        for definition in removed:
            self._definitions.pop(definition.type_id, None)
        return removed

    def prepare_record(
        self, record: Mapping[str, Any], *, allow_newer: bool = False
    ) -> dict[str, Any]:
        type_id = str(record.get("type", "")).strip().lower()
        return self.require(type_id).prepare_record(record, allow_newer=allow_newer)

    def clone(self) -> "ElementRegistry":
        return ElementRegistry(replace(item) for item in self._definitions.values())


_COMMON_PROPERTIES = {
    "x": {"type": "number"},
    "y": {"type": "number"},
    "width": {"type": "number", "minimum": 24},
    "height": {"type": "number", "minimum": 24},
    "text": {"type": "string"},
    "color": {"type": "string"},
    "background": {"type": "string"},
    "textColor": {"type": "string"},
    "metadata": {"type": "object"},
    "opacity": {"type": "number", "minimum": 0, "maximum": 1},
    "rotation": {"type": "number"},
    "z": {"type": "number"},
}
_SIGNAL_PROPERTIES = {
    "lineWidth": {"type": "number", "minimum": 0.5},
    "lineStyle": {"type": "string", "enum": ["solid", "dash", "dot", "dashdot"]},
    "arrowStart": {"type": "boolean"},
    "arrowEnd": {"type": "boolean"},
    "animated": {"type": "boolean"},
    "animationEffect": {
        "type": "string", "enum": ["flow", "pulse", "glow", "particles", "packet"],
    },
    "flowSpeed": {"type": "number", "minimum": 0.1},
    "flowDirection": {"type": "string", "enum": ["forward", "reverse"]},
    "flowSpacing": {"type": "number", "minimum": 1},
    "effectIntensity": {"type": "number", "minimum": 0.2, "maximum": 4},
    "packetLoop": {"type": "boolean"},
    "packetDuration": {"type": "number", "minimum": 0.1},
    "packetInterval": {"type": "number", "minimum": 0.05},
    "packetIcon": {"type": "string"},
    "points": {"type": "array"},
}


def _element_schema(extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"properties": {**_COMMON_PROPERTIES, **dict(extra or {})}}


_STANDARD = frozenset({"content", "geometry", "appearance"})
BUILTIN_ELEMENT_DEFINITIONS = (
    ElementDefinition("text", "Text", "Shapes", 160, 48, schema=_element_schema(), capabilities=_STANDARD),
    ElementDefinition("rectangle", "Rectangle", "Shapes", 140, 80, schema=_element_schema(), capabilities=_STANDARD),
    ElementDefinition("ellipse", "Ellipse", "Shapes", 120, 80, schema=_element_schema(), capabilities=_STANDARD),
    ElementDefinition("button", "Button", "Shapes", 120, 42, schema=_element_schema(), capabilities=_STANDARD),
    ElementDefinition("diamond", "Diamond", "Shapes", 120, 100, schema=_element_schema(), capabilities=_STANDARD),
    ElementDefinition("triangle", "Triangle", "Shapes", 120, 100, schema=_element_schema(), capabilities=_STANDARD),
    ElementDefinition(
        "node", "Node", "Diagram & data", 180, 96,
        schema=_element_schema({"ports": {"type": "array"}}),
        capabilities=_STANDARD | {"ports"},
    ),
    ElementDefinition(
        "splitter", "Splitter", "Diagram & data", 72, 72,
        schema=_element_schema({"ports": {"type": "array"}}),
        capabilities=frozenset({"geometry", "appearance", "ports"}),
    ),
    ElementDefinition(
        "line", "Line / arrow", "Diagram & data", 220, 40,
        schema=_element_schema(_SIGNAL_PROPERTIES),
        capabilities=frozenset({"geometry", "appearance", "signal"}),
    ),
    ElementDefinition(
        "bar_chart", "Bar chart", "Diagram & data", 260, 160,
        schema=_element_schema({"data": {"type": "array"}}),
        capabilities=_STANDARD | {"chart"},
    ),
    ElementDefinition(
        "line_chart", "Line chart", "Diagram & data", 260, 160,
        schema=_element_schema({"data": {"type": "array"}}),
        capabilities=_STANDARD | {"chart"},
    ),
    ElementDefinition(
        "image", "Image", "Media", 280, 180,
        media_picker=True, schema=_element_schema({"source": {"type": "string"}}),
        capabilities=frozenset({"geometry", "appearance", "media"}),
    ),
    ElementDefinition(
        "animated_image", "Animated GIF", "Media", 280, 180, icon="gif",
        media_picker=True, schema=_element_schema({"source": {"type": "string"}}),
        capabilities=frozenset({"geometry", "appearance", "media"}),
    ),
)


def create_default_element_registry() -> ElementRegistry:
    return ElementRegistry(BUILTIN_ELEMENT_DEFINITIONS)
