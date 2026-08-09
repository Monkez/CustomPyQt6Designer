"""Qt-free opt-in component catalogs for MonkezCanva.

The records in this module are portable registry metadata only. Native painting
and Inspector widgets are attached by the Qt adapter when a pack is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .registry import ElementDefinition, ElementRegistry


DASHBOARD_PACK_ID = "monkez.dashboard"
INDUSTRIAL_PACK_ID = "monkez.industrial"
SOFTWARE_PACK_ID = "monkez.software"
COMPONENT_PACK_VERSION = "1.0"


def _port(
    port_id: str,
    mode: str,
    side: str,
    label: str = "",
    *,
    data_type: str = "any",
    unit: str = "",
    position: float | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": port_id,
        "mode": mode,
        "side": side,
        "label": label or port_id.replace("-", " ").title(),
        "dataType": data_type,
        "maxConnections": 0,
    }
    if unit:
        result["unit"] = unit
    if position is not None:
        result["position"] = position
    return result


FLOW_PORTS = (
    _port("in", "input", "left", "Input"),
    _port("out", "output", "right", "Output"),
)
DATA_PORTS = (
    _port("in", "input", "left", "Request", data_type="dict"),
    _port("out", "output", "right", "Response", data_type="dict"),
)


_BASE_SCHEMA = {
    "value": {"type": "number", "title": "Value"},
    "minimum": {"type": "number", "title": "Minimum"},
    "maximum": {"type": "number", "title": "Maximum"},
    "unit": {"type": "string", "title": "Unit"},
    "status": {"type": "string", "title": "Status"},
    "active": {"type": "boolean", "title": "Active"},
}


def _definition(
    type_id: str,
    label: str,
    category: str,
    visual: str,
    plugin_id: str,
    *,
    size: tuple[float, float] = (180, 100),
    color: str = "#2563eb",
    background: str = "#ffffff",
    defaults: Mapping[str, Any] | None = None,
    properties: Mapping[str, Any] | None = None,
    ports: Iterable[Mapping[str, Any]] = (),
    capabilities: Iterable[str] = (),
) -> ElementDefinition:
    port_records = [dict(port) for port in ports]
    values: dict[str, Any] = {
        "text": label,
        "color": color,
        "background": background,
        "textColor": "#172033",
        "packVisual": visual,
        **dict(defaults or {}),
    }
    if port_records:
        values["ports"] = port_records
    schema_properties = {
        "packVisual": {"type": "string", "title": "Visual"},
        **dict(properties or {}),
    }
    if port_records:
        schema_properties["ports"] = {"type": "array"}
    resolved_capabilities = {
        "content",
        "geometry",
        "appearance",
        "component-pack",
        *capabilities,
    }
    if port_records:
        resolved_capabilities.add("ports")
    return ElementDefinition(
        type_id,
        label,
        category,
        size[0],
        size[1],
        icon=visual,
        defaults=values,
        schema={"properties": schema_properties},
        plugin_id=plugin_id,
        plugin_version=COMPONENT_PACK_VERSION,
        capabilities=frozenset(resolved_capabilities),
    )


def _dashboard_definitions() -> tuple[ElementDefinition, ...]:
    category = "Dashboard Pack"
    common_range = {
        "value": _BASE_SCHEMA["value"],
        "minimum": _BASE_SCHEMA["minimum"],
        "maximum": _BASE_SCHEMA["maximum"],
        "unit": _BASE_SCHEMA["unit"],
    }
    chart = {"data": {"type": "array", "title": "Data"}}
    specs = (
        (
            "dash_kpi_card",
            "KPI card",
            "kpi",
            (210, 112),
            {"value": 72.4, "unit": "%", "subtitle": "This month", "trend": 8.2},
            {
                **common_range,
                "subtitle": {"type": "string", "title": "Subtitle"},
                "trend": {"type": "number", "title": "Trend %"},
            },
            (),
        ),
        (
            "dash_sparkline",
            "Sparkline",
            "sparkline",
            (220, 100),
            {"data": [18, 24, 21, 35, 31, 44, 48], "showArea": True},
            {**chart, "showArea": {"type": "boolean", "title": "Fill area"}},
            ("chart",),
        ),
        (
            "dash_gauge",
            "Gauge",
            "gauge",
            (190, 150),
            {"value": 64, "minimum": 0, "maximum": 100, "unit": "%"},
            common_range,
            (),
        ),
        (
            "dash_progress_ring",
            "Progress ring",
            "progress_ring",
            (150, 150),
            {"value": 78, "minimum": 0, "maximum": 100, "unit": "%"},
            common_range,
            (),
        ),
        (
            "dash_pie",
            "Pie chart",
            "pie",
            (190, 160),
            {"data": [42, 28, 18, 12], "labels": ["A", "B", "C", "D"]},
            {**chart, "labels": {"type": "array", "title": "Labels"}},
            ("chart",),
        ),
        (
            "dash_donut",
            "Donut chart",
            "donut",
            (190, 160),
            {"data": [52, 27, 21], "labels": ["Online", "Idle", "Offline"]},
            {**chart, "labels": {"type": "array", "title": "Labels"}},
            ("chart",),
        ),
        (
            "dash_scatter",
            "Scatter plot",
            "scatter",
            (230, 150),
            {"data": [[1, 3], [2, 5], [3, 4], [4, 8], [5, 7]]},
            chart,
            ("chart",),
        ),
        ("dash_area", "Area chart", "area", (230, 150), {"data": [12, 20, 17, 29, 24, 38]}, chart, ("chart",)),
        ("dash_histogram", "Histogram", "histogram", (230, 150), {"data": [3, 7, 12, 18, 14, 9, 4]}, chart, ("chart",)),
        (
            "dash_heatmap",
            "Heatmap",
            "heatmap",
            (220, 150),
            {"data": [1, 3, 6, 8, 5, 2, 4, 7, 9, 6, 3, 8], "columns": 4},
            {**chart, "columns": {"type": "integer", "minimum": 1, "maximum": 24, "title": "Columns"}},
            ("chart",),
        ),
        (
            "dash_timeline",
            "Timeline",
            "timeline",
            (250, 130),
            {"data": ["08:00 Start", "10:15 Review", "13:30 Deploy"]},
            chart,
            ("chart",),
        ),
        (
            "dash_event_log",
            "Event log",
            "event_log",
            (270, 160),
            {"data": ["INFO Service ready", "WARN High latency", "OK Recovered"], "maxRows": 8},
            {**chart, "maxRows": {"type": "integer", "minimum": 1, "maximum": 100, "title": "Visible rows"}},
            ("chart",),
        ),
        (
            "dash_data_table",
            "Data table",
            "data_table",
            (290, 170),
            {"columns": ["Name", "Value", "State"], "data": [["Pump A", "72%", "Run"], ["Valve B", "40%", "Idle"]]},
            {**chart, "columns": {"type": "array", "title": "Columns"}},
            ("chart",),
        ),
        (
            "dash_status_light",
            "Status light",
            "status_light",
            (170, 90),
            {"status": "online", "active": True},
            {
                "status": {"type": "string", "enum": ["online", "warning", "error", "offline"], "title": "Status"},
                "active": _BASE_SCHEMA["active"],
            },
            (),
        ),
        (
            "dash_alarm_banner",
            "Alarm banner",
            "alarm_banner",
            (300, 86),
            {"message": "Pressure above threshold", "severity": "warning", "acknowledged": False},
            {
                "message": {"type": "string", "title": "Message"},
                "severity": {"type": "string", "enum": ["info", "warning", "critical"], "title": "Severity"},
                "acknowledged": {"type": "boolean", "title": "Acknowledged"},
            },
            (),
        ),
    )
    return tuple(
        _definition(
            type_id,
            label,
            category,
            visual,
            DASHBOARD_PACK_ID,
            size=size,
            color="#ff685b",
            background="#fffdfb",
            defaults=defaults,
            properties=properties,
            capabilities=capabilities,
        )
        for type_id, label, visual, size, defaults, properties, capabilities in specs
    )


def _industrial_definitions() -> tuple[ElementDefinition, ...]:
    category = "Industrial Pack"
    range_fields = {
        "value": _BASE_SCHEMA["value"],
        "minimum": _BASE_SCHEMA["minimum"],
        "maximum": _BASE_SCHEMA["maximum"],
        "unit": _BASE_SCHEMA["unit"],
    }
    fluid_ports = (
        _port("in", "input", "left", "Inlet", data_type="fluid"),
        _port("out", "output", "right", "Outlet", data_type="fluid"),
    )
    power_ports = (
        _port("power", "input", "left", "Power", data_type="number", unit="V"),
        _port("state", "output", "right", "State", data_type="dict"),
    )
    specs = (
        (
            "ind_tank",
            "Tank",
            "tank",
            (150, 210),
            {"value": 68, "minimum": 0, "maximum": 100, "unit": "%", "capacity": 5000},
            {**range_fields, "capacity": {"type": "number", "minimum": 0, "title": "Capacity"}},
            fluid_ports,
        ),
        (
            "ind_pump",
            "Pump",
            "pump",
            (165, 120),
            {"active": True, "speed": 72, "direction": "forward"},
            {
                "active": _BASE_SCHEMA["active"],
                "speed": {"type": "number", "minimum": 0, "maximum": 100, "title": "Speed %"},
                "direction": {"type": "string", "enum": ["forward", "reverse"], "title": "Direction"},
            },
            fluid_ports,
        ),
        (
            "ind_valve",
            "Valve",
            "valve",
            (150, 105),
            {"active": True, "position": 60, "normallyOpen": False},
            {
                "active": _BASE_SCHEMA["active"],
                "position": {"type": "number", "minimum": 0, "maximum": 100, "title": "Position %"},
                "normallyOpen": {"type": "boolean", "title": "Normally open"},
            },
            fluid_ports,
        ),
        (
            "ind_motor",
            "Motor",
            "motor",
            (150, 125),
            {"active": True, "speed": 1450, "unit": "rpm"},
            {
                "active": _BASE_SCHEMA["active"],
                "speed": {"type": "number", "minimum": 0, "title": "Speed"},
                "unit": _BASE_SCHEMA["unit"],
            },
            power_ports,
        ),
        (
            "ind_fan",
            "Fan",
            "fan",
            (150, 125),
            {"active": True, "speed": 65},
            {
                "active": _BASE_SCHEMA["active"],
                "speed": {"type": "number", "minimum": 0, "maximum": 100, "title": "Speed %"},
            },
            power_ports,
        ),
        (
            "ind_pipe",
            "Pipe",
            "pipe",
            (230, 72),
            {"active": True, "value": 24, "unit": "L/min", "direction": "forward"},
            {
                "active": _BASE_SCHEMA["active"],
                "value": _BASE_SCHEMA["value"],
                "unit": _BASE_SCHEMA["unit"],
                "direction": {"type": "string", "enum": ["forward", "reverse"], "title": "Direction"},
            },
            fluid_ports,
        ),
        (
            "ind_sensor",
            "Sensor",
            "sensor",
            (170, 105),
            {"value": 24.8, "minimum": -20, "maximum": 120, "unit": "°C", "status": "normal"},
            {
                **range_fields,
                "status": {"type": "string", "enum": ["normal", "warning", "alarm", "offline"], "title": "Status"},
            },
            (_port("signal", "output", "right", "Signal", data_type="number"),),
        ),
        (
            "ind_plc",
            "PLC",
            "plc",
            (190, 150),
            {"status": "run", "active": True, "program": "MAIN"},
            {
                "status": {"type": "string", "enum": ["run", "stop", "fault", "offline"], "title": "Mode"},
                "active": _BASE_SCHEMA["active"],
                "program": {"type": "string", "title": "Program"},
            },
            (
                _port("di", "input", "left", "DI", data_type="boolean", position=0.3),
                _port("ai", "input", "left", "AI", data_type="number", position=0.7),
                _port("do", "output", "right", "DO", data_type="boolean", position=0.3),
                _port("ao", "output", "right", "AO", data_type="number", position=0.7),
            ),
        ),
        (
            "ind_circuit_breaker",
            "Circuit breaker",
            "breaker",
            (165, 110),
            {"closed": True, "tripped": False, "rating": 32, "unit": "A"},
            {
                "closed": {"type": "boolean", "title": "Closed"},
                "tripped": {"type": "boolean", "title": "Tripped"},
                "rating": {"type": "number", "minimum": 0, "title": "Rating"},
                "unit": _BASE_SCHEMA["unit"],
            },
            power_ports,
        ),
        (
            "ind_battery",
            "Battery",
            "battery",
            (155, 115),
            {"value": 82, "minimum": 0, "maximum": 100, "unit": "%", "voltage": 24},
            {**range_fields, "voltage": {"type": "number", "minimum": 0, "title": "Voltage"}},
            power_ports,
        ),
        (
            "ind_transformer",
            "Transformer",
            "transformer",
            (175, 125),
            {"active": True, "ratio": 4.0, "primaryVoltage": 400, "secondaryVoltage": 100},
            {
                "active": _BASE_SCHEMA["active"],
                "ratio": {"type": "number", "minimum": 0.01, "title": "Ratio"},
                "primaryVoltage": {"type": "number", "minimum": 0, "title": "Primary V"},
                "secondaryVoltage": {"type": "number", "minimum": 0, "title": "Secondary V"},
            },
            (
                _port("primary", "input", "left", "Primary", data_type="number", unit="V"),
                _port("secondary", "output", "right", "Secondary", data_type="number", unit="V"),
            ),
        ),
        (
            "ind_conveyor",
            "Conveyor",
            "conveyor",
            (260, 115),
            {"active": True, "speed": 1.2, "unit": "m/s", "load": 56},
            {
                "active": _BASE_SCHEMA["active"],
                "speed": {"type": "number", "minimum": 0, "title": "Speed"},
                "unit": _BASE_SCHEMA["unit"],
                "load": {"type": "number", "minimum": 0, "maximum": 100, "title": "Load %"},
            },
            FLOW_PORTS,
        ),
    )
    return tuple(
        _definition(
            type_id,
            label,
            category,
            visual,
            INDUSTRIAL_PACK_ID,
            size=size,
            color="#0f9f8f",
            background="#f8fffd",
            defaults=defaults,
            properties=properties,
            ports=ports,
            capabilities=("industrial",),
        )
        for type_id, label, visual, size, defaults, properties, ports in specs
    )


def _software_definitions() -> tuple[ElementDefinition, ...]:
    category = "Software & Flowchart Pack"
    common_fields = {
        "technology": {"type": "string", "title": "Technology"},
        "status": {"type": "string", "enum": ["online", "warning", "error", "offline"], "title": "Status"},
    }
    specs = (
        ("soft_database", "Database", "database", (180, 125), {"technology": "SQL", "status": "online"}, DATA_PORTS),
        ("soft_server", "Server", "server", (180, 125), {"technology": "Linux", "status": "online"}, DATA_PORTS),
        ("soft_cloud", "Cloud", "cloud", (190, 120), {"technology": "Cloud", "status": "online"}, DATA_PORTS),
        ("soft_api", "API", "api", (180, 110), {"technology": "REST", "status": "online"}, DATA_PORTS),
        (
            "soft_queue",
            "Queue",
            "queue",
            (190, 115),
            {"technology": "FIFO", "status": "online", "depth": 12},
            DATA_PORTS,
        ),
        (
            "soft_topic",
            "Topic",
            "topic",
            (190, 115),
            {"technology": "Pub/Sub", "status": "online", "subscribers": 3},
            DATA_PORTS,
        ),
        (
            "soft_cache",
            "Cache",
            "cache",
            (180, 115),
            {"technology": "Memory", "status": "online", "hitRate": 94},
            DATA_PORTS,
        ),
        ("soft_file", "File", "file", (145, 125), {"technology": "JSON", "status": "online"}, FLOW_PORTS),
        ("soft_service", "Service", "service", (190, 120), {"technology": "Python", "status": "online"}, DATA_PORTS),
        ("soft_container", "Container", "container", (190, 120), {"technology": "OCI", "status": "online"}, DATA_PORTS),
        ("soft_process", "Process", "process", (180, 100), {"technology": "", "status": "online"}, FLOW_PORTS),
        (
            "soft_decision",
            "Decision",
            "decision",
            (170, 135),
            {},
            (
                _port("in", "input", "left", "Input"),
                _port("yes", "output", "right", "Yes", data_type="boolean", position=0.3),
                _port("no", "output", "right", "No", data_type="boolean", position=0.7),
            ),
        ),
        ("soft_document", "Document", "document", (150, 130), {"technology": "", "status": "online"}, FLOW_PORTS),
        ("soft_terminator", "Terminator", "terminator", (180, 80), {}, FLOW_PORTS),
        ("soft_annotation", "Annotation", "annotation", (210, 105), {}, ()),
        ("soft_sticky_note", "Sticky note", "sticky_note", (190, 150), {}, ()),
    )
    extended = {
        **common_fields,
        "depth": {"type": "integer", "minimum": 0, "title": "Queue depth"},
        "subscribers": {"type": "integer", "minimum": 0, "title": "Subscribers"},
        "hitRate": {"type": "number", "minimum": 0, "maximum": 100, "title": "Hit rate %"},
    }
    return tuple(
        _definition(
            type_id,
            label,
            category,
            visual,
            SOFTWARE_PACK_ID,
            size=size,
            color="#596579" if visual not in ("sticky_note", "decision") else "#e7a53b",
            background="#ffffff" if visual != "sticky_note" else "#fff8c9",
            defaults=defaults,
            properties={name: rule for name, rule in extended.items() if name in defaults},
            ports=ports,
            capabilities=("software",),
        )
        for type_id, label, visual, size, defaults, ports in specs
    )


@dataclass(frozen=True, slots=True)
class ComponentPack:
    pack_id: str
    label: str
    version: str
    definitions: tuple[ElementDefinition, ...]

    def __post_init__(self) -> None:
        pack_id = str(self.pack_id).strip().lower()
        label = str(self.label).strip()
        version = str(self.version).strip()
        definitions = tuple(self.definitions)
        object.__setattr__(self, "pack_id", pack_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "definitions", definitions)
        if not pack_id or not label or not version:
            raise ValueError("Component pack ID, label and version cannot be empty")
        if not definitions:
            raise ValueError(f"Component pack {pack_id!r} cannot be empty")
        ids = tuple(definition.type_id for definition in definitions)
        if len(ids) != len(set(ids)):
            raise ValueError(f"Component pack {self.pack_id!r} has duplicate type IDs")
        if any(definition.plugin_id != pack_id for definition in definitions):
            raise ValueError(f"Component pack {pack_id!r} has inconsistent ownership")


COMPONENT_PACKS = (
    ComponentPack(DASHBOARD_PACK_ID, "Dashboard", COMPONENT_PACK_VERSION, _dashboard_definitions()),
    ComponentPack(INDUSTRIAL_PACK_ID, "Industrial", COMPONENT_PACK_VERSION, _industrial_definitions()),
    ComponentPack(SOFTWARE_PACK_ID, "Software & Flowchart", COMPONENT_PACK_VERSION, _software_definitions()),
)
_PACKS_BY_ID = {pack.pack_id: pack for pack in COMPONENT_PACKS}
_PACK_ALIASES = {
    "dashboard": DASHBOARD_PACK_ID,
    "dash": DASHBOARD_PACK_ID,
    "industrial": INDUSTRIAL_PACK_ID,
    "industry": INDUSTRIAL_PACK_ID,
    "software": SOFTWARE_PACK_ID,
    "flowchart": SOFTWARE_PACK_ID,
    "software-flowchart": SOFTWARE_PACK_ID,
}


def component_packs() -> tuple[ComponentPack, ...]:
    return COMPONENT_PACKS


def component_pack(pack_id: str) -> ComponentPack:
    key = str(pack_id).strip().lower().replace("_", "-")
    key = _PACK_ALIASES.get(key, key)
    try:
        return _PACKS_BY_ID[key]
    except KeyError as error:
        raise KeyError(f"Unknown MonkezCanva component pack: {pack_id}") from error


def register_component_pack(
    registry: ElementRegistry,
    pack_id: str,
    *,
    replace_existing: bool = False,
    definitions: Iterable[ElementDefinition] | None = None,
) -> tuple[str, ...]:
    pack = component_pack(pack_id)
    records = tuple(definitions) if definitions is not None else pack.definitions
    for definition in records:
        if definition.plugin_id != pack.pack_id:
            raise ValueError(f"Component {definition.type_id!r} is not owned by {pack.pack_id!r}")
    if not replace_existing:
        conflicts = [
            definition.type_id
            for definition in records
            if registry.definition(definition.type_id) is not None
        ]
        if conflicts:
            raise ValueError(f"Duplicate MonkezCanva element type: {conflicts[0]}")
    registered = []
    for definition in records:
        registry.register(definition, replace_existing=replace_existing)
        registered.append(definition.type_id)
    return tuple(registered)


__all__ = [
    "COMPONENT_PACKS",
    "COMPONENT_PACK_VERSION",
    "DASHBOARD_PACK_ID",
    "INDUSTRIAL_PACK_ID",
    "SOFTWARE_PACK_ID",
    "ComponentPack",
    "component_pack",
    "component_packs",
    "register_component_pack",
]
