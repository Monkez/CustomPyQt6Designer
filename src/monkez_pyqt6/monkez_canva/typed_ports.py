"""Qt-free typed-port normalization and connection compatibility rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


PORT_MODES = ("input", "output", "free")
PORT_SIDES = ("left", "right", "top", "bottom")
_TYPE_ALIASES = {
    "*": "any",
    "object": "any",
    "integer": "int",
    "double": "float",
    "number": "float",
    "boolean": "bool",
    "string": "str",
    "dictionary": "dict",
    "mapping": "dict",
    "array": "list",
}
_STANDARD_KEYS = {
    "id", "mode", "side", "label", "position", "dataType", "unit",
    "required", "defaultValue", "maxConnections", "acceptedTypes",
    "acceptedUnits", "convertsTo", "tooltip",
}


def normalize_data_type(value: Any) -> str:
    result = str(value or "any").strip().lower().replace(" ", "_")
    return _TYPE_ALIASES.get(result, result or "any")


def infer_data_type(value: Any) -> str:
    """Return the portable type name used by runtime port diagnostics."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, Mapping):
        return "dict"
    if isinstance(value, (list, tuple)):
        return "list"
    return normalize_data_type(type(value).__name__)


def _unique_strings(values: Any, *, types: bool = False) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [part.strip() for part in values.split(",")]
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise TypeError("Typed port compatibility lists must be arrays or comma-separated strings")
    result: list[str] = []
    for value in values:
        normalized = normalize_data_type(value) if types else str(value).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def normalize_port_record(raw: Mapping[str, Any], index: int = 0) -> dict[str, Any]:
    """Normalize a JSON-safe port record while preserving extension fields."""

    data = dict(raw)
    port_id = str(data.get("id", f"port-{index + 1}")).strip()
    if not port_id:
        raise ValueError("MonkezCanva port ID cannot be empty")
    mode = str(data.get("mode", "free")).lower().strip()
    mode = {"in": "input", "out": "output", "io": "free", "bidirectional": "free"}.get(mode, mode)
    if mode not in PORT_MODES:
        raise ValueError(f"Unsupported MonkezCanva port mode: {mode}")
    default_side = "left" if mode == "input" else "right" if mode == "output" else "bottom"
    side = str(data.get("side", default_side)).lower().strip()
    if side not in PORT_SIDES:
        raise ValueError(f"Unsupported MonkezCanva port side: {side}")
    position_value = data.get("position")
    max_connections = int(data.get("maxConnections", 0))
    if max_connections < 0:
        raise ValueError("Port maxConnections must be zero (unlimited) or positive")
    result: dict[str, Any] = {
        "id": port_id,
        "mode": mode,
        "side": side,
        "label": str(data.get("label", port_id)),
        "dataType": normalize_data_type(data.get("dataType", "any")),
        "unit": str(data.get("unit", "")).strip(),
        "required": bool(data.get("required", False)),
        "maxConnections": max_connections,
        "acceptedTypes": _unique_strings(data.get("acceptedTypes"), types=True),
        "acceptedUnits": _unique_strings(data.get("acceptedUnits")),
        "convertsTo": _unique_strings(data.get("convertsTo"), types=True),
        "tooltip": str(data.get("tooltip", "")),
    }
    if position_value is not None:
        result["position"] = max(0.0, min(1.0, float(position_value)))
    if "defaultValue" in data:
        default_value = data["defaultValue"]
        actual_type = infer_data_type(default_value)
        expected_type = result["dataType"]
        if (
            default_value is not None
            and expected_type != "any"
            and actual_type != expected_type
            and not (expected_type == "float" and actual_type == "int")
        ):
            raise TypeError(
                f"Port {port_id!r} default value type {actual_type!r} "
                f"does not match {expected_type!r}"
            )
        result["defaultValue"] = default_value
    result.update({key: value for key, value in data.items() if key not in _STANDARD_KEYS})
    return result


@dataclass(frozen=True, slots=True)
class PortSpec:
    id: str
    mode: str
    data_type: str = "any"
    unit: str = ""
    required: bool = False
    max_connections: int = 0
    accepted_types: tuple[str, ...] = ()
    accepted_units: tuple[str, ...] = ()
    converts_to: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "PortSpec":
        record = normalize_port_record(raw)
        return cls(
            record["id"],
            record["mode"],
            record["dataType"],
            record["unit"],
            record["required"],
            record["maxConnections"],
            tuple(record["acceptedTypes"]),
            tuple(record["acceptedUnits"]),
            tuple(record["convertsTo"]),
        )


@dataclass(frozen=True, slots=True)
class PortCompatibility:
    compatible: bool
    reason: str
    source_is_first: bool = True
    conversion: bool = False


@dataclass(frozen=True, slots=True)
class PortValueValidation:
    valid: bool
    reason: str
    actual_type: str


def validate_port_value(port: Mapping[str, Any], value: Any) -> PortValueValidation:
    """Validate a transient runtime value without importing or persisting Qt state."""

    spec = PortSpec.from_mapping(port)
    actual = infer_data_type(value)
    if value is None:
        if spec.required and "defaultValue" not in port:
            return PortValueValidation(False, f"Required port {spec.id!r} has no value", actual)
        return PortValueValidation(True, "Optional/default value is available", actual)
    expected = spec.data_type
    if expected == "any" or actual == expected:
        return PortValueValidation(True, "Runtime value matches the port type", actual)
    if expected == "float" and actual == "int":
        return PortValueValidation(True, "Integer value is losslessly accepted as float", actual)
    return PortValueValidation(
        False, f"Runtime value type {actual!r} does not match {expected!r}", actual
    )


def _directed_compatibility(
    source: PortSpec,
    target: PortSpec,
    source_connections: int,
    target_connections: int,
) -> PortCompatibility:
    if source.mode == "input":
        return PortCompatibility(False, "A connection cannot start from an input port")
    if target.mode == "output":
        return PortCompatibility(False, "A connection cannot end at an output port")
    if source.max_connections and source_connections >= source.max_connections:
        return PortCompatibility(
            False, f"Source port {source.id!r} reached its {source.max_connections}-connection limit"
        )
    if target.max_connections and target_connections >= target.max_connections:
        return PortCompatibility(
            False, f"Target port {target.id!r} reached its {target.max_connections}-connection limit"
        )

    source_type, target_type = source.data_type, target.data_type
    conversion = False
    if source_type != "any" and target_type != "any" and source_type != target_type:
        conversion = (
            source_type in target.accepted_types or target_type in source.converts_to
        )
        if not conversion:
            return PortCompatibility(
                False,
                f"Type {source_type!r} is not compatible with {target_type!r}",
            )
    if source.unit and target.unit and source.unit != target.unit:
        if source.unit not in target.accepted_units:
            return PortCompatibility(
                False,
                f"Unit {source.unit!r} is not compatible with {target.unit!r}",
            )
        conversion = True
    reason = "Compatible through declared conversion" if conversion else "Ports are compatible"
    return PortCompatibility(True, reason, conversion=conversion)


def evaluate_port_pair(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    *,
    first_connections: int = 0,
    second_connections: int = 0,
) -> PortCompatibility:
    """Orient two ports and evaluate mode, cardinality, type and unit rules."""

    first_spec = PortSpec.from_mapping(first)
    second_spec = PortSpec.from_mapping(second)
    if first_spec.mode == "input" or second_spec.mode == "output":
        reverse = _directed_compatibility(
            second_spec, first_spec, second_connections, first_connections
        )
        return PortCompatibility(
            reverse.compatible, reverse.reason, source_is_first=False,
            conversion=reverse.conversion,
        )
    return _directed_compatibility(
        first_spec, second_spec, first_connections, second_connections
    )


def evaluate_directed_ports(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    source_connections: int = 0,
    target_connections: int = 0,
) -> PortCompatibility:
    return _directed_compatibility(
        PortSpec.from_mapping(source),
        PortSpec.from_mapping(target),
        source_connections,
        target_connections,
    )
