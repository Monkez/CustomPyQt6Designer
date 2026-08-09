"""Deterministic, Qt-free workflow graph compiler and execution kernel."""

from __future__ import annotations

import heapq
import operator
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


WORKFLOW_COMPONENT_TYPES = (
    "wf_source", "wf_sink", "wf_input", "wf_output", "wf_error_handler",
    "wf_junction", "wf_reroute", "wf_merge", "wf_splitter", "wf_switch",
    "wf_router", "wf_multiplexer", "wf_demultiplexer", "wf_bus",
    "wf_timer", "wf_delay", "wf_queue", "wf_buffer", "wf_throttle",
    "wf_debounce", "wf_retry", "wf_rate_limiter",
    "wf_gate", "wf_compare", "wf_filter", "wf_transform", "wf_map",
    "wf_counter", "wf_state_machine",
)
WORKFLOW_TERMINAL_STATES = frozenset(("completed", "failed", "cancelled"))


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _field(value: Any, path: str, default: Any = None) -> Any:
    current = value
    for part in str(path).split(".") if path else ():
        if isinstance(current, Mapping):
            current = current.get(part, default)
        elif isinstance(current, (list, tuple)) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else default
        else:
            return default
    return current


@dataclass(frozen=True, slots=True)
class WorkflowNode:
    id: str
    type_id: str
    ports: tuple[str, ...] = ()
    config: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowConnector:
    id: str
    source: str
    target: str
    source_port: str = "out"
    target_port: str = "in"
    config: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowGraph:
    nodes: Mapping[str, WorkflowNode]
    connectors: tuple[WorkflowConnector, ...]

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        *,
        supported_types: Iterable[str] = WORKFLOW_COMPONENT_TYPES,
    ) -> "WorkflowGraph":
        supported = frozenset(str(value) for value in supported_types)
        nodes: dict[str, WorkflowNode] = {}
        for raw in document.get("elements", ()):
            type_id = str(raw.get("type", ""))
            if type_id not in supported:
                continue
            node_id = str(raw.get("id", "")).strip()
            if not node_id:
                raise ValueError("Workflow element id cannot be empty")
            ports = tuple(str(port.get("id", "")) for port in raw.get("ports", ()))
            config = raw.get("workflow", {})
            if not isinstance(config, Mapping):
                raise TypeError(f"Workflow config for {node_id!r} must be an object")
            nodes[node_id] = WorkflowNode(node_id, type_id, ports, dict(config))
        connectors = []
        for raw in document.get("connectors", ()):
            source = str(raw.get("source", ""))
            target = str(raw.get("target", ""))
            if source not in nodes or target not in nodes:
                continue
            connector_id = str(raw.get("id", "")).strip()
            if not connector_id:
                raise ValueError("Workflow connector id cannot be empty")
            source_port = str(raw.get("sourcePort", "out") or "out")
            target_port = str(raw.get("targetPort", "in") or "in")
            if nodes[source].ports and source_port not in nodes[source].ports:
                raise ValueError(
                    f"Workflow connector {connector_id!r} has unknown source port {source_port!r}"
                )
            if nodes[target].ports and target_port not in nodes[target].ports:
                raise ValueError(
                    f"Workflow connector {connector_id!r} has unknown target port {target_port!r}"
                )
            config = raw.get("workflow", {})
            connectors.append(WorkflowConnector(
                connector_id, source, target, source_port, target_port,
                dict(config) if isinstance(config, Mapping) else {},
            ))
        graph = cls(nodes, tuple(connectors))
        graph.validate()
        return graph

    def validate(self) -> None:
        if len(self.nodes) != len(set(self.nodes)):
            raise ValueError("Workflow contains duplicate node IDs")
        connector_ids = [connector.id for connector in self.connectors]
        if len(connector_ids) != len(set(connector_ids)):
            raise ValueError("Workflow contains duplicate connector IDs")
        for connector in self.connectors:
            if connector.source not in self.nodes or connector.target not in self.nodes:
                raise ValueError(f"Workflow connector {connector.id!r} has a missing endpoint")

    def outgoing(self, node_id: str, port: str = "out") -> tuple[WorkflowConnector, ...]:
        return tuple(
            connector for connector in self.connectors
            if connector.source == node_id
            and (port == "*" or connector.source_port in (port, ""))
        )


@dataclass(frozen=True, slots=True)
class WorkflowEmission:
    port: str
    payload: Any
    delay: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowNodeResult:
    emissions: tuple[WorkflowEmission, ...] = ()
    output: Any = None


@dataclass(frozen=True, slots=True)
class WorkflowTraceEvent:
    sequence: int
    timestamp: float
    event: str
    token_id: str = ""
    node_id: str = ""
    connector_id: str = ""
    detail: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "event": self.event,
            "tokenId": self.token_id,
            "nodeId": self.node_id,
            "connectorId": self.connector_id,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    state: str
    steps: int
    logical_time: float
    outputs: Mapping[str, tuple[Any, ...]]
    errors: tuple[Mapping[str, Any], ...]
    node_states: Mapping[str, str]


@dataclass(slots=True)
class WorkflowContext:
    executor: "WorkflowExecutor"
    node: WorkflowNode
    token_id: str
    input_port: str
    metadata: dict[str, Any]
    memory: dict[str, Any]
    attempt: int


@dataclass(order=True, slots=True)
class _WorkItem:
    due: float
    negative_priority: int
    order: int
    token_id: str = field(compare=False)
    node_id: str = field(compare=False)
    input_port: str = field(compare=False)
    payload: Any = field(compare=False)
    metadata: dict[str, Any] = field(compare=False)
    attempt: int = field(compare=False, default=0)
    connector_id: str = field(compare=False, default="")
    generation: int = field(compare=False, default=0)


WorkflowHandler = Callable[[WorkflowContext, Any], Any]


class WorkflowExecutor:
    """Execute one compiled graph with deterministic logical-time scheduling."""

    def __init__(
        self,
        graph: WorkflowGraph,
        *,
        clock: Callable[[], float] = time.monotonic,
        event_sink: Callable[[WorkflowTraceEvent], None] | None = None,
        max_steps: int = 100_000,
    ) -> None:
        graph.validate()
        self.graph = graph
        self._clock = clock
        self._event_sink = event_sink
        self.max_steps = max(1, int(max_steps))
        self._queue: list[_WorkItem] = []
        self._order = 0
        self._sequence = 0
        self._logical_time = float(clock())
        self._state = "idle"
        self._paused = False
        self._handlers_by_type: dict[str, WorkflowHandler] = {}
        self._handlers_by_node: dict[str, WorkflowHandler] = {}
        self._memory: dict[str, dict[str, Any]] = defaultdict(dict)
        self._node_states: dict[str, str] = {node_id: "idle" for node_id in graph.nodes}
        self._outputs: dict[str, list[Any]] = defaultdict(list)
        self._errors: list[dict[str, Any]] = []
        self._trace: list[WorkflowTraceEvent] = []
        self._steps = 0

    @property
    def state(self) -> str:
        return self._state

    @property
    def logical_time(self) -> float:
        return self._logical_time

    def register_handler(
        self, key: str, handler: WorkflowHandler, *, node: bool = False
    ) -> None:
        if not callable(handler):
            raise TypeError("Workflow handler must be callable")
        target = self._handlers_by_node if node else self._handlers_by_type
        target[str(key)] = handler

    def enqueue(
        self,
        node_id: str,
        payload: Any = None,
        *,
        input_port: str = "in",
        metadata: Mapping[str, Any] | None = None,
        priority: int = 0,
        delay: float = 0.0,
        token_id: str | None = None,
        connector_id: str = "",
        attempt: int = 0,
        generation: int = 0,
    ) -> str:
        if node_id not in self.graph.nodes:
            raise KeyError(f"Unknown workflow node: {node_id}")
        node = self.graph.nodes[node_id]
        if node.type_id == "wf_debounce" and generation == 0:
            memory = self._memory[node_id]
            generation = int(memory.get("generation", 0)) + 1
            memory["generation"] = generation
            delay += max(
                0.0, float(node.config.get("interval", node.config.get("seconds", 0.25)))
            )
        token_id = str(token_id or uuid.uuid4().hex[:12])
        self._order += 1
        heapq.heappush(self._queue, _WorkItem(
            self._logical_time + max(0.0, float(delay)),
            -int(priority), self._order, token_id, str(node_id), str(input_port),
            payload, dict(metadata or {}), int(attempt), str(connector_id), int(generation),
        ))
        self._state = "paused" if self._paused else "running"
        self._record("token_queued", token_id, node_id, connector_id, {
            "inputPort": input_port, "delay": max(0.0, float(delay)),
            "priority": int(priority),
        })
        return token_id

    def start(
        self,
        source_id: str,
        payload: Any = None,
        *,
        metadata: Mapping[str, Any] | None = None,
        priority: int = 0,
        token_id: str | None = None,
    ) -> str:
        return self.enqueue(
            source_id, payload, input_port="trigger", metadata=metadata,
            priority=priority, token_id=token_id,
        )

    def pause(self) -> bool:
        if self._paused:
            return False
        self._paused = True
        self._state = "paused"
        self._record("runtime_paused")
        return True

    def resume(self) -> bool:
        if not self._paused:
            return False
        self._paused = False
        self._state = "running" if self._queue else "completed"
        self._record("runtime_resumed")
        return True

    def cancel(self) -> bool:
        if self._state in WORKFLOW_TERMINAL_STATES:
            return False
        self._queue.clear()
        self._state = "cancelled"
        for node_id, state in tuple(self._node_states.items()):
            if state in ("queued", "running"):
                self._node_states[node_id] = "cancelled"
        self._record("runtime_cancelled")
        return True

    def step(self, *, auto_advance: bool = False) -> bool:
        if self._paused or self._state in WORKFLOW_TERMINAL_STATES or not self._queue:
            return False
        item = self._queue[0]
        if item.due > self._logical_time:
            if not auto_advance:
                return False
            self._logical_time = item.due
        heapq.heappop(self._queue)
        self._steps += 1
        if self._steps > self.max_steps:
            self._state = "failed"
            raise RuntimeError(
                f"Workflow exceeded max_steps={self.max_steps}; possible infinite cycle"
            )
        node = self.graph.nodes[item.node_id]
        if node.type_id == "wf_debounce":
            latest = int(self._memory[node.id].get("generation", 0))
            if item.generation and item.generation != latest:
                self._record("token_debounced", item.token_id, node.id, item.connector_id)
                return True
        self._node_states[node.id] = "running"
        self._record("node_started", item.token_id, node.id, item.connector_id, {
            "inputPort": item.input_port, "attempt": item.attempt,
        })
        context = WorkflowContext(
            self, node, item.token_id, item.input_port, dict(item.metadata),
            self._memory[node.id], item.attempt,
        )
        try:
            handler = self._handlers_by_node.get(node.id) or self._handlers_by_type.get(node.type_id)
            raw_result = handler(context, item.payload) if handler else self._execute_builtin(context, item.payload)
            result = self._normalize_result(raw_result)
        except Exception as error:
            self._handle_error(item, node, error)
            return True
        self._node_states[node.id] = "completed"
        self._record("node_completed", item.token_id, node.id, detail={
            "emissions": len(result.emissions),
        })
        if result.output is not None:
            self._outputs[node.id].append(result.output)
        for emission in result.emissions:
            self._route(item, node, emission)
        if not self._queue:
            self._state = "completed" if not self._errors else "failed"
            self._record("runtime_completed" if not self._errors else "runtime_failed")
        return True

    def run_until_idle(self, *, auto_advance: bool = True) -> WorkflowRunResult:
        while self._queue and not self._paused:
            if not self.step(auto_advance=auto_advance):
                break
        return self.result()

    def advance(self, seconds: float) -> WorkflowRunResult:
        self._logical_time += max(0.0, float(seconds))
        return self.run_until_idle(auto_advance=False)

    def result(self) -> WorkflowRunResult:
        return WorkflowRunResult(
            self._state,
            self._steps,
            self._logical_time,
            {key: tuple(values) for key, values in self._outputs.items()},
            tuple(dict(error) for error in self._errors),
            dict(self._node_states),
        )

    def trace(self, limit: int | None = None) -> tuple[WorkflowTraceEvent, ...]:
        values = self._trace if limit is None else self._trace[-max(0, int(limit)):]
        return tuple(values)

    def node_state(self, node_id: str) -> str:
        if node_id not in self._node_states:
            raise KeyError(f"Unknown workflow node: {node_id}")
        return self._node_states[node_id]

    def _route(
        self, item: _WorkItem, node: WorkflowNode, emission: WorkflowEmission
    ) -> None:
        connectors = self.graph.outgoing(node.id, emission.port)
        if not connectors:
            self._outputs[node.id].append(emission.payload)
            self._record("output_unconnected", item.token_id, node.id, detail={
                "port": emission.port,
            })
            return
        for connector in connectors:
            metadata = dict(item.metadata)
            metadata.update(dict(emission.metadata))
            priority = int(metadata.get("priority", -item.negative_priority))
            self._record("connector_emitted", item.token_id, node.id, connector.id, {
                "sourcePort": connector.source_port,
                "targetPort": connector.target_port,
                "delay": emission.delay,
                "payload": emission.payload,
                "metadata": metadata,
            })
            self.enqueue(
                connector.target,
                emission.payload,
                input_port=connector.target_port,
                metadata=metadata,
                priority=priority,
                delay=emission.delay + float(connector.config.get("delay", 0.0)),
                token_id=item.token_id,
                connector_id=connector.id,
            )

    def _handle_error(self, item: _WorkItem, node: WorkflowNode, error: Exception) -> None:
        retries = max(0, int(node.config.get("retries", 0)))
        if item.attempt < retries:
            delay = max(0.0, float(node.config.get("retryDelay", 0.0)))
            self._record("node_retry", item.token_id, node.id, detail={
                "attempt": item.attempt + 1, "error": str(error), "delay": delay,
            })
            self.enqueue(
                node.id, item.payload, input_port=item.input_port,
                metadata=item.metadata, priority=-item.negative_priority,
                delay=delay, token_id=item.token_id,
                connector_id=item.connector_id, attempt=item.attempt + 1,
            )
            return
        failure = {
            "tokenId": item.token_id, "nodeId": node.id,
            "error": str(error), "type": type(error).__name__,
        }
        self._errors.append(failure)
        self._node_states[node.id] = "failed"
        self._record("node_failed", item.token_id, node.id, item.connector_id, failure)
        error_edges = self.graph.outgoing(node.id, "error")
        for connector in error_edges:
            self.enqueue(
                connector.target, failure, input_port=connector.target_port,
                metadata=item.metadata, priority=-item.negative_priority,
                token_id=item.token_id, connector_id=connector.id,
            )
        if not error_edges and not self._queue:
            self._state = "failed"

    def _execute_builtin(self, context: WorkflowContext, payload: Any) -> WorkflowNodeResult:
        node = context.node
        config = node.config
        kind = node.type_id
        passthrough = {
            "wf_source", "wf_input", "wf_junction", "wf_reroute", "wf_merge",
            "wf_bus", "wf_queue", "wf_buffer", "wf_retry", "wf_timer",
        }
        if kind in ("wf_sink", "wf_output", "wf_error_handler"):
            return WorkflowNodeResult(output=payload)
        if kind in passthrough:
            return WorkflowNodeResult((WorkflowEmission("out", payload),))
        if kind == "wf_splitter":
            return WorkflowNodeResult((WorkflowEmission("*", payload),))
        if kind in ("wf_switch", "wf_compare"):
            matched = self._compare(payload, config)
            return WorkflowNodeResult((WorkflowEmission("true" if matched else "false", payload),))
        if kind in ("wf_filter", "wf_gate"):
            matched = self._compare(payload, config)
            port = "out" if matched else "rejected"
            return WorkflowNodeResult((WorkflowEmission(port, payload),))
        if kind == "wf_router":
            key = str(_field(payload, str(config.get("field", "route")), config.get("default", "default")))
            routes = config.get("routes", {})
            port = str(routes.get(key, config.get("defaultPort", "default"))) if isinstance(routes, Mapping) else key
            return WorkflowNodeResult((WorkflowEmission(port, payload),))
        if kind == "wf_multiplexer":
            return WorkflowNodeResult((WorkflowEmission("out", {
                "channel": context.input_port, "value": payload,
            }),))
        if kind == "wf_demultiplexer":
            channel = str(_field(payload, str(config.get("channelField", "channel")), "default"))
            value = _field(payload, str(config.get("valueField", "value")), payload)
            return WorkflowNodeResult((WorkflowEmission(channel, value),))
        if kind in ("wf_delay", "wf_debounce"):
            delay = 0.0 if kind == "wf_debounce" else max(
                0.0, float(config.get("seconds", config.get("interval", 0.1)))
            )
            return WorkflowNodeResult((WorkflowEmission("out", payload, delay),))
        if kind in ("wf_throttle", "wf_rate_limiter"):
            interval = max(0.0, float(config.get("interval", 1.0)))
            last = float(context.memory.get("lastEmit", float("-inf")))
            if self._logical_time - last < interval:
                self._record("token_throttled", context.token_id, node.id)
                return WorkflowNodeResult()
            context.memory["lastEmit"] = self._logical_time
            return WorkflowNodeResult((WorkflowEmission("out", payload),))
        if kind in ("wf_transform", "wf_map"):
            return WorkflowNodeResult((WorkflowEmission(
                "out", self._transform(payload, config),
            ),))
        if kind == "wf_counter":
            context.memory["count"] = int(context.memory.get("count", 0)) + int(config.get("step", 1))
            field_name = str(config.get("field", "count"))
            result = dict(payload) if isinstance(payload, Mapping) else {"value": payload}
            result[field_name] = context.memory["count"]
            return WorkflowNodeResult((WorkflowEmission("out", result),))
        if kind == "wf_state_machine":
            current = str(context.memory.get("state", config.get("initial", "idle")))
            event = str(_field(payload, str(config.get("eventField", "event")), ""))
            transitions = config.get("transitions", {})
            target = current
            if isinstance(transitions, Mapping):
                state_transitions = transitions.get(current, {})
                if isinstance(state_transitions, Mapping):
                    target = str(state_transitions.get(event, current))
            context.memory["state"] = target
            result = dict(payload) if isinstance(payload, Mapping) else {"value": payload}
            result[str(config.get("stateField", "state"))] = target
            port = "changed" if target != current else "out"
            return WorkflowNodeResult((WorkflowEmission(port, result),))
        raise ValueError(f"No built-in workflow handler for {kind!r}")

    @staticmethod
    def _compare(payload: Any, config: Mapping[str, Any]) -> bool:
        actual = _field(payload, str(config.get("field", "")), payload)
        expected = config.get("value", True)
        operation = str(config.get("operator", "equals")).lower()
        operations = {
            "equals": operator.eq, "eq": operator.eq,
            "not_equals": operator.ne, "ne": operator.ne,
            "gt": operator.gt, "gte": operator.ge,
            "lt": operator.lt, "lte": operator.le,
            "contains": lambda left, right: right in left,
            "truthy": lambda left, _right: bool(left),
            "falsy": lambda left, _right: not bool(left),
        }
        callback = operations.get(operation)
        if callback is None:
            raise ValueError(f"Unsupported workflow comparison operator: {operation}")
        return bool(callback(actual, expected))

    @staticmethod
    def _transform(payload: Any, config: Mapping[str, Any]) -> Any:
        operation = str(config.get("operation", "identity")).lower()
        if operation == "identity":
            return payload
        if operation == "get":
            return _field(payload, str(config.get("field", "")), config.get("default"))
        if operation in ("set", "rename"):
            if not isinstance(payload, Mapping):
                raise TypeError(f"Workflow {operation} requires a mapping payload")
            result = dict(payload)
            if operation == "set":
                result[str(config.get("field", "value"))] = config.get("value")
            else:
                source = str(config.get("field", ""))
                target = str(config.get("target", source))
                if source in result:
                    result[target] = result.pop(source)
            return result
        if operation in ("scale", "offset"):
            value = float(_field(payload, str(config.get("field", "")), payload))
            return value * float(config.get("value", 1.0)) if operation == "scale" else value + float(config.get("value", 0.0))
        if operation == "format":
            return str(config.get("template", "{value}")).format(value=payload)
        raise ValueError(f"Unsupported workflow transform operation: {operation}")

    @staticmethod
    def _normalize_result(value: Any) -> WorkflowNodeResult:
        if isinstance(value, WorkflowNodeResult):
            return value
        if isinstance(value, WorkflowEmission):
            return WorkflowNodeResult((value,))
        if value is None:
            return WorkflowNodeResult()
        return WorkflowNodeResult((WorkflowEmission("out", value),))

    def _record(
        self,
        event: str,
        token_id: str = "",
        node_id: str = "",
        connector_id: str = "",
        detail: Mapping[str, Any] | None = None,
    ) -> WorkflowTraceEvent:
        self._sequence += 1
        trace = WorkflowTraceEvent(
            self._sequence, self._logical_time, str(event), str(token_id),
            str(node_id), str(connector_id), dict(detail or {}),
        )
        self._trace.append(trace)
        if self._event_sink is not None:
            self._event_sink(trace)
        return trace
