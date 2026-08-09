"""Opt-in registry pack for executable MonkezCanva workflow nodes."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .registry import ElementDefinition, ElementRegistry
from .workflow import WORKFLOW_COMPONENT_TYPES


WORKFLOW_PLUGIN_ID = "monkez.workflow"
WORKFLOW_PLUGIN_VERSION = "1.0"


def _port(
    port_id: str,
    mode: str,
    side: str,
    label: str = "",
    *,
    data_type: str = "any",
    position: float | None = None,
) -> dict[str, Any]:
    result = {
        "id": port_id,
        "mode": mode,
        "side": side,
        "label": label or port_id.replace("-", " ").title(),
        "dataType": data_type,
        "maxConnections": 0,
    }
    if position is not None:
        result["position"] = position
    return result


IN_OUT = (
    _port("in", "input", "left", "Input"),
    _port("out", "output", "right", "Output"),
)
SOURCE_PORTS = (_port("out", "output", "right", "Output"),)
SINK_PORTS = (_port("in", "input", "left", "Input"),)
TRUE_FALSE = (
    _port("in", "input", "left", "Input"),
    _port("true", "output", "right", "True", position=0.32),
    _port("false", "output", "right", "False", position=0.72),
    _port("error", "output", "bottom", "Error"),
)
FILTER_PORTS = (
    _port("in", "input", "left", "Input"),
    _port("out", "output", "right", "Accepted", position=0.32),
    _port("rejected", "output", "right", "Rejected", position=0.72),
    _port("error", "output", "bottom", "Error"),
)
FAN_OUT = (
    _port("in", "input", "left", "Input"),
    *tuple(
        _port(f"out-{index}", "output", "right", f"Output {index}", position=index / 5)
        for index in range(1, 5)
    ),
    _port("default", "output", "bottom", "Default"),
)
FAN_IN = (
    *tuple(
        _port(f"in-{index}", "input", "left", f"Input {index}", position=index / 5)
        for index in range(1, 5)
    ),
    _port("out", "output", "right", "Output"),
)


_SPECS = (
    ("wf_source", "Source", "Workflow · Boundaries", SOURCE_PORTS, {}, "#0f9f8f"),
    ("wf_sink", "Sink", "Workflow · Boundaries", SINK_PORTS, {}, "#0f9f8f"),
    ("wf_input", "Input interface", "Workflow · Boundaries", SOURCE_PORTS, {}, "#0f9f8f"),
    ("wf_output", "Output interface", "Workflow · Boundaries", SINK_PORTS, {}, "#0f9f8f"),
    ("wf_error_handler", "Error handler", "Workflow · Boundaries", (
        _port("error", "input", "left", "Error"),
        _port("out", "output", "right", "Recovered"),
    ), {}, "#dc2626"),
    ("wf_junction", "Junction", "Workflow · Routing", IN_OUT, {}, "#2563eb"),
    ("wf_reroute", "Reroute", "Workflow · Routing", IN_OUT, {}, "#2563eb"),
    ("wf_merge", "Merge", "Workflow · Routing", FAN_IN, {}, "#2563eb"),
    ("wf_splitter", "Splitter", "Workflow · Routing", FAN_OUT, {}, "#2563eb"),
    ("wf_switch", "Switch", "Workflow · Routing", TRUE_FALSE, {
        "field": "enabled", "operator": "truthy", "value": True,
    }, "#2563eb"),
    ("wf_router", "Router", "Workflow · Routing", FAN_OUT, {
        "field": "route", "routes": {}, "defaultPort": "default",
    }, "#2563eb"),
    ("wf_multiplexer", "Multiplexer", "Workflow · Routing", FAN_IN, {}, "#2563eb"),
    ("wf_demultiplexer", "Demultiplexer", "Workflow · Routing", FAN_OUT, {
        "channelField": "channel", "valueField": "value",
    }, "#2563eb"),
    ("wf_bus", "Bus", "Workflow · Routing", IN_OUT, {}, "#2563eb"),
    ("wf_timer", "Timer", "Workflow · Timing", IN_OUT, {
        "interval": 1.0, "initialDelay": 1.0, "maxOccurrences": None,
        "catchUp": "latest", "maxBurst": 1000,
    }, "#7c3aed"),
    ("wf_delay", "Delay", "Workflow · Timing", IN_OUT, {"seconds": 1.0}, "#7c3aed"),
    ("wf_queue", "Queue", "Workflow · Timing", IN_OUT, {
        "capacity": 100, "overflow": "drop_oldest",
    }, "#7c3aed"),
    ("wf_buffer", "Buffer", "Workflow · Timing", IN_OUT, {"size": 10}, "#7c3aed"),
    ("wf_throttle", "Throttle", "Workflow · Timing", IN_OUT, {"interval": 1.0}, "#7c3aed"),
    ("wf_debounce", "Debounce", "Workflow · Timing", IN_OUT, {"interval": 0.25}, "#7c3aed"),
    ("wf_retry", "Retry", "Workflow · Timing", (
        *IN_OUT, _port("error", "output", "bottom", "Error"),
    ), {"retries": 3, "retryDelay": 0.25}, "#7c3aed"),
    ("wf_rate_limiter", "Rate limiter", "Workflow · Timing", IN_OUT, {"interval": 1.0}, "#7c3aed"),
    ("wf_gate", "Gate", "Workflow · Logic", FILTER_PORTS, {
        "field": "enabled", "operator": "truthy", "value": True,
    }, "#ea580c"),
    ("wf_compare", "Compare", "Workflow · Logic", TRUE_FALSE, {
        "field": "value", "operator": "equals", "value": True,
    }, "#ea580c"),
    ("wf_filter", "Filter", "Workflow · Logic", FILTER_PORTS, {
        "field": "value", "operator": "truthy", "value": True,
    }, "#ea580c"),
    ("wf_transform", "Transform", "Workflow · Logic", IN_OUT, {
        "operation": "identity",
    }, "#ea580c"),
    ("wf_map", "Map", "Workflow · Logic", IN_OUT, {
        "operation": "identity",
    }, "#ea580c"),
    ("wf_counter", "Counter", "Workflow · Logic", IN_OUT, {
        "field": "count", "step": 1,
    }, "#ea580c"),
    ("wf_state_machine", "State machine", "Workflow · Logic", (
        _port("in", "input", "left", "Event"),
        _port("out", "output", "right", "Unchanged", position=0.3),
        _port("changed", "output", "right", "Changed", position=0.7),
        _port("error", "output", "bottom", "Error"),
    ), {"initial": "idle", "eventField": "event", "stateField": "state", "transitions": {}}, "#ea580c"),
)


def workflow_component_definitions() -> tuple[ElementDefinition, ...]:
    definitions = []
    for type_id, label, category, ports, workflow, color in _SPECS:
        definitions.append(ElementDefinition(
            type_id,
            label,
            category,
            188,
            96,
            icon="node",
            defaults={
                "text": label,
                "color": color,
                "background": "#ffffff",
                "ports": list(ports),
                "workflow": dict(workflow),
            },
            schema={"properties": {
                "ports": {"type": "array"},
                "workflow": {"type": "object"},
            }},
            plugin_id=WORKFLOW_PLUGIN_ID,
            plugin_version=WORKFLOW_PLUGIN_VERSION,
            capabilities=frozenset({
                "content", "geometry", "appearance", "ports", "workflow",
            }),
        ))
    if tuple(definition.type_id for definition in definitions) != WORKFLOW_COMPONENT_TYPES:
        raise RuntimeError("Workflow component definition order is inconsistent")
    return tuple(definitions)


WORKFLOW_COMPONENT_DEFINITIONS = workflow_component_definitions()


def register_workflow_components(
    registry: ElementRegistry,
    *,
    replace_existing: bool = False,
    definitions: Iterable[ElementDefinition] = WORKFLOW_COMPONENT_DEFINITIONS,
) -> tuple[str, ...]:
    registered = []
    for definition in definitions:
        registry.register(definition, replace_existing=replace_existing)
        registered.append(definition.type_id)
    return tuple(registered)
