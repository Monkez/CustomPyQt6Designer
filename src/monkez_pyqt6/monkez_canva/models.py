"""Qt-free canonical document models used by MonkezCanva."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4
from weakref import WeakMethod

from .operations import OperationEvent, changed_fields


DOCUMENT_FORMAT = "monkez-canva"
DOCUMENT_VERSION = 1
_KNOWN_TOP_LEVEL = {"format", "version", "scene", "elements", "connectors", "groups", "resources"}
_PORT_MODES = {"input", "output", "free"}
_PORT_SIDES = {"left", "right", "top", "bottom"}


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    return value


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _json_copy(value: Any) -> Any:
    """Validate and detach a JSON value, rejecting NaN and executable objects."""

    try:
        return json.loads(json.dumps(_plain_json(value), ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise TypeError("MonkezCanva document values must be finite JSON data") from error


def _frozen_mapping(value: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return _freeze_json(_json_copy(dict(value or {})))


def _required_id(value: Any, label: str = "object") -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"MonkezCanva {label} ID cannot be empty")
    return result


@dataclass(frozen=True, slots=True)
class PortModel:
    id: str
    mode: str = "free"
    side: str = "bottom"
    label: str = ""
    position: float | None = None
    properties: Mapping[str, Any] = field(default_factory=_frozen_mapping)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PortModel":
        raw = _json_copy(dict(data))
        port_id = _required_id(raw.pop("id", ""), "port")
        mode = str(raw.pop("mode", "free")).lower().strip()
        mode = {"in": "input", "out": "output", "io": "free", "bidirectional": "free"}.get(mode, mode)
        if mode not in _PORT_MODES:
            raise ValueError(f"Unsupported MonkezCanva port mode: {mode}")
        default_side = "left" if mode == "input" else "right" if mode == "output" else "bottom"
        side = str(raw.pop("side", default_side)).lower().strip()
        if side not in _PORT_SIDES:
            raise ValueError(f"Unsupported MonkezCanva port side: {side}")
        label = str(raw.pop("label", port_id))
        position_value = raw.pop("position", None)
        position = None if position_value is None else max(0.0, min(1.0, float(position_value)))
        return cls(port_id, mode, side, label, position, _frozen_mapping(raw))

    def to_dict(self) -> dict[str, Any]:
        result = {"id": self.id, "mode": self.mode, "side": self.side, "label": self.label}
        if self.position is not None:
            result["position"] = self.position
        result.update(_json_copy(self.properties))
        return result


@dataclass(frozen=True, slots=True)
class SceneModel:
    properties: Mapping[str, Any] = field(default_factory=_frozen_mapping)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> "SceneModel":
        return cls(_frozen_mapping(data))

    def to_dict(self) -> dict[str, Any]:
        return _json_copy(self.properties)


@dataclass(frozen=True, slots=True)
class ElementModel:
    id: str
    type: str
    properties: Mapping[str, Any] = field(default_factory=_frozen_mapping)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ElementModel":
        raw = _json_copy(dict(data))
        element_id = _required_id(raw.pop("id", ""), "element")
        element_type = str(raw.pop("type", "")).lower().strip()
        if not element_type:
            raise ValueError(f"Element {element_id!r} has no type")
        if element_type == "arrow":
            element_type = "line"
            raw.setdefault("arrowEnd", True)
        elif element_type == "polyline":
            element_type = "line"
        if "ports" in raw:
            ports = [PortModel.from_dict(port) for port in raw["ports"]]
            ids = [port.id for port in ports]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Element {element_id!r} contains duplicate port IDs")
            raw["ports"] = [port.to_dict() for port in ports]
        return cls(element_id, element_type, _frozen_mapping(raw))

    @property
    def ports(self) -> tuple[PortModel, ...]:
        return tuple(PortModel.from_dict(port) for port in self.properties.get("ports", []))

    def to_dict(self) -> dict[str, Any]:
        result = {"id": self.id, "type": self.type}
        result.update(_json_copy(self.properties))
        return result


@dataclass(frozen=True, slots=True)
class ConnectorModel:
    id: str
    source: str
    target: str
    source_port: str = ""
    target_port: str = ""
    properties: Mapping[str, Any] = field(default_factory=_frozen_mapping)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ConnectorModel":
        raw = _json_copy(dict(data))
        connector_id = _required_id(raw.pop("id", ""), "connector")
        connector_type = str(raw.pop("type", "connector")).lower().strip()
        if connector_type != "connector":
            raise ValueError(f"Object {connector_id!r} is not a connector")
        source = _required_id(raw.pop("source", ""), "connector source")
        target = _required_id(raw.pop("target", ""), "connector target")
        source_port = str(raw.pop("sourcePort", ""))
        target_port = str(raw.pop("targetPort", ""))
        return cls(connector_id, source, target, source_port, target_port, _frozen_mapping(raw))

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "type": "connector",
            "source": self.source,
            "target": self.target,
            "sourcePort": self.source_port,
            "targetPort": self.target_port,
        }
        result.update(_json_copy(self.properties))
        return result


@dataclass(frozen=True, slots=True)
class GroupModel:
    id: str
    members: tuple[str, ...] = ()
    properties: Mapping[str, Any] = field(default_factory=_frozen_mapping)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GroupModel":
        raw = _json_copy(dict(data))
        group_id = _required_id(raw.pop("id", ""), "group")
        members = tuple(_required_id(member, "group member") for member in raw.pop("members", []))
        if len(members) != len(set(members)):
            raise ValueError(f"Group {group_id!r} contains duplicate members")
        return cls(group_id, members, _frozen_mapping(raw))

    def to_dict(self) -> dict[str, Any]:
        result = {"id": self.id, "members": list(self.members)}
        result.update(_json_copy(self.properties))
        return result


@dataclass(frozen=True, slots=True)
class ResourceModel:
    id: str
    kind: str
    uri: str
    properties: Mapping[str, Any] = field(default_factory=_frozen_mapping)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResourceModel":
        raw = _json_copy(dict(data))
        resource_id = _required_id(raw.pop("id", ""), "resource")
        kind = str(raw.pop("kind", "asset")).strip() or "asset"
        uri = str(raw.pop("uri", ""))
        return cls(resource_id, kind, uri, _frozen_mapping(raw))

    def to_dict(self) -> dict[str, Any]:
        result = {"id": self.id, "kind": self.kind, "uri": self.uri}
        result.update(_json_copy(self.properties))
        return result


DocumentListener = Callable[[OperationEvent], None]


class CanvasDocument:
    """Canonical, serializable MonkezCanva state with granular operations."""

    def __init__(
        self,
        *,
        scene: SceneModel | None = None,
        elements: Iterable[ElementModel] = (),
        connectors: Iterable[ConnectorModel] = (),
        groups: Iterable[GroupModel] = (),
        resources: Iterable[ResourceModel] = (),
        version: int = DOCUMENT_VERSION,
        extensions: Mapping[str, Any] | None = None,
    ) -> None:
        if int(version) != DOCUMENT_VERSION:
            raise ValueError(f"Unsupported MonkezCanva document version: {version}")
        element_items = tuple(elements)
        connector_items = tuple(connectors)
        group_items = tuple(groups)
        resource_items = tuple(resources)
        self._scene = scene or SceneModel()
        self._elements = {model.id: model for model in element_items}
        self._connectors = {model.id: model for model in connector_items}
        self._groups = {model.id: model for model in group_items}
        self._resources = {model.id: model for model in resource_items}
        if len(self._elements) != len(element_items):
            raise ValueError("MonkezCanva document contains duplicate element IDs")
        if len(self._connectors) != len(connector_items):
            raise ValueError("MonkezCanva document contains duplicate connector IDs")
        if len(self._groups) != len(group_items):
            raise ValueError("MonkezCanva document contains duplicate group IDs")
        if len(self._resources) != len(resource_items):
            raise ValueError("MonkezCanva document contains duplicate resource IDs")
        self._extensions = _frozen_mapping(extensions)
        self._revision = 0
        self._listeners: dict[str, DocumentListener | WeakMethod] = {}
        self._validate()

    @classmethod
    def empty(cls, scene: Mapping[str, Any] | None = None) -> "CanvasDocument":
        return cls(scene=SceneModel.from_dict(scene))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CanvasDocument":
        raw = _json_copy(dict(data))
        if raw.get("format") != DOCUMENT_FORMAT:
            raise ValueError("Unsupported MonkezCanva document format")
        version = int(raw.get("version", DOCUMENT_VERSION))
        extensions = {key: value for key, value in raw.items() if key not in _KNOWN_TOP_LEVEL}
        return cls(
            scene=SceneModel.from_dict(raw.get("scene", {})),
            elements=(ElementModel.from_dict(item) for item in raw.get("elements", [])),
            connectors=(ConnectorModel.from_dict(item) for item in raw.get("connectors", [])),
            groups=(GroupModel.from_dict(item) for item in raw.get("groups", [])),
            resources=(ResourceModel.from_dict(item) for item in raw.get("resources", [])),
            version=version,
            extensions=extensions,
        )

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def scene(self) -> SceneModel:
        return self._scene

    @property
    def elements(self) -> tuple[ElementModel, ...]:
        return tuple(self._elements.values())

    @property
    def connectors(self) -> tuple[ConnectorModel, ...]:
        return tuple(self._connectors.values())

    @property
    def groups(self) -> tuple[GroupModel, ...]:
        return tuple(self._groups.values())

    @property
    def resources(self) -> tuple[ResourceModel, ...]:
        return tuple(self._resources.values())

    def element(self, element_id: str) -> ElementModel | None:
        return self._elements.get(str(element_id))

    def connector(self, connector_id: str) -> ConnectorModel | None:
        return self._connectors.get(str(connector_id))

    def group(self, group_id: str) -> GroupModel | None:
        return self._groups.get(str(group_id))

    def resource(self, resource_id: str) -> ResourceModel | None:
        return self._resources.get(str(resource_id))

    def subscribe(self, listener: DocumentListener) -> str:
        token = uuid4().hex
        try:
            stored: DocumentListener | WeakMethod = WeakMethod(listener) if getattr(listener, "__self__", None) else listener
        except TypeError:
            stored = listener
        self._listeners[token] = stored
        return token

    def unsubscribe(self, token: str) -> None:
        self._listeners.pop(str(token), None)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "format": DOCUMENT_FORMAT,
            "version": DOCUMENT_VERSION,
            "scene": self._scene.to_dict(),
            "elements": [item.to_dict() for item in self._elements.values()],
            "connectors": [item.to_dict() for item in self._connectors.values()],
        }
        if self._groups:
            result["groups"] = [item.to_dict() for item in self._groups.values()]
        if self._resources:
            result["resources"] = [item.to_dict() for item in self._resources.values()]
        result.update(_json_copy(self._extensions))
        return result

    def reconcile(self, data: Mapping[str, Any], *, origin: Any = None) -> tuple[OperationEvent, ...]:
        """Atomically replace state and report the smallest record-level changes."""

        candidate = CanvasDocument.from_dict(data)
        events: list[tuple[str, str, str, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
        previous_scene = self._scene.to_dict()
        current_scene = candidate._scene.to_dict()
        if previous_scene != current_scene:
            events.append(("scene.updated", "scene", "scene", changed_fields(previous_scene, current_scene), previous_scene, current_scene))
        self._collect_record_changes(events, "element", self._elements, candidate._elements)
        self._collect_record_changes(events, "connector", self._connectors, candidate._connectors)
        self._collect_record_changes(events, "group", self._groups, candidate._groups)
        self._collect_record_changes(events, "resource", self._resources, candidate._resources)
        previous_extensions = dict(self._extensions)
        current_extensions = dict(candidate._extensions)
        if previous_extensions != current_extensions:
            events.append(("document.metadata.updated", "document", "", changed_fields(previous_extensions, current_extensions), previous_extensions, current_extensions))
        if not events:
            return ()
        self._scene = candidate._scene
        self._elements = candidate._elements
        self._connectors = candidate._connectors
        self._groups = candidate._groups
        self._resources = candidate._resources
        self._extensions = candidate._extensions
        self._revision += 1
        operation_id = uuid4().hex
        committed = tuple(
            OperationEvent(action, target_type, target_id, self._revision, changes, previous, current, operation_id, origin=origin)
            for action, target_type, target_id, changes, previous, current in events
        )
        self._emit(committed)
        return committed

    def add_element(self, element: ElementModel | Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        model = element if isinstance(element, ElementModel) else ElementModel.from_dict(element)
        self._ensure_available_id(model.id)
        self._elements[model.id] = model
        return self._commit("element.added", "element", model.id, current=model.to_dict(), origin=origin)

    def update_element(self, element_id: str, changes: Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        key = str(element_id)
        previous = self._required_element(key).to_dict()
        updated = dict(previous)
        updated.update(_json_copy(dict(changes)))
        updated["id"] = key
        model = ElementModel.from_dict(updated)
        self._elements[key] = model
        return self._commit(
            "element.updated", "element", key, changed_fields(previous, model.to_dict()), previous, model.to_dict(), origin
        )

    def remove_element(self, element_id: str, *, origin: Any = None) -> tuple[OperationEvent, ...]:
        key = str(element_id)
        previous = self._required_element(key).to_dict()
        attached = [item for item in self._connectors.values() if key in (item.source, item.target)]
        changed_groups: list[tuple[GroupModel, GroupModel]] = []
        self._elements.pop(key)
        for connector in attached:
            self._connectors.pop(connector.id)
        for group_id, group in tuple(self._groups.items()):
            if key not in group.members:
                continue
            data = group.to_dict()
            data["members"] = [member for member in group.members if member != key]
            updated = GroupModel.from_dict(data)
            self._groups[group_id] = updated
            changed_groups.append((group, updated))
        self._revision += 1
        operation_id = uuid4().hex
        events = [
            OperationEvent("connector.removed", "connector", item.id, self._revision, previous=item.to_dict(), operation_id=operation_id, origin=origin)
            for item in attached
        ]
        events.extend(
            OperationEvent(
                "group.updated", "group", current.id, self._revision,
                changed_fields(old.to_dict(), current.to_dict()), old.to_dict(), current.to_dict(),
                operation_id, origin=origin,
            )
            for old, current in changed_groups
        )
        events.append(OperationEvent("element.removed", "element", key, self._revision, previous=previous, operation_id=operation_id, origin=origin))
        committed = tuple(events)
        self._emit(committed)
        return committed

    def add_connector(self, connector: ConnectorModel | Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        model = connector if isinstance(connector, ConnectorModel) else ConnectorModel.from_dict(connector)
        self._ensure_available_id(model.id)
        self._validate_connector(model)
        self._connectors[model.id] = model
        return self._commit("connector.added", "connector", model.id, current=model.to_dict(), origin=origin)

    def update_connector(self, connector_id: str, changes: Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        key = str(connector_id)
        previous_model = self._connectors.get(key)
        if previous_model is None:
            raise KeyError(f"Unknown MonkezCanva connector: {key}")
        previous = previous_model.to_dict()
        updated = dict(previous)
        updated.update(_json_copy(dict(changes)))
        updated["id"] = key
        model = ConnectorModel.from_dict(updated)
        self._validate_connector(model)
        self._connectors[key] = model
        return self._commit(
            "connector.updated", "connector", key,
            changed_fields(previous, model.to_dict()), previous, model.to_dict(), origin,
        )

    def remove_connector(self, connector_id: str, *, origin: Any = None) -> OperationEvent:
        key = str(connector_id)
        model = self._connectors.pop(key, None)
        if model is None:
            raise KeyError(f"Unknown MonkezCanva connector: {key}")
        return self._commit("connector.removed", "connector", key, previous=model.to_dict(), origin=origin)

    def rename_connector(self, connector_id: str, new_id: str, *, origin: Any = None) -> OperationEvent | None:
        old_id = str(connector_id)
        requested = _required_id(new_id, "connector")
        model = self._connectors.get(old_id)
        if model is None:
            raise KeyError(f"Unknown MonkezCanva connector: {old_id}")
        if requested == old_id:
            return None
        self._ensure_available_id(requested)
        data = model.to_dict()
        data["id"] = requested
        renamed = ConnectorModel.from_dict(data)
        ordered: dict[str, ConnectorModel] = {}
        for key, entry in self._connectors.items():
            ordered[requested if key == old_id else key] = renamed if key == old_id else entry
        self._connectors = ordered
        return self._commit(
            "connector.renamed", "connector", requested, {"id": requested},
            model.to_dict(), renamed.to_dict(), origin,
        )

    def rename_element(self, element_id: str, new_id: str, *, origin: Any = None) -> tuple[OperationEvent, ...]:
        old_id = str(element_id)
        requested = _required_id(new_id, "element")
        model = self._required_element(old_id)
        if requested == old_id:
            return ()
        self._ensure_available_id(requested)
        renamed_data = model.to_dict()
        renamed_data["id"] = requested
        renamed = ElementModel.from_dict(renamed_data)
        elements = dict(self._elements)
        ordered: dict[str, ElementModel] = {}
        for key, entry in elements.items():
            ordered[requested if key == old_id else key] = renamed if key == old_id else entry
        self._elements = ordered
        changed_connectors: list[tuple[ConnectorModel, ConnectorModel]] = []
        for key, connector in tuple(self._connectors.items()):
            if old_id not in (connector.source, connector.target):
                continue
            data = connector.to_dict()
            if data["source"] == old_id:
                data["source"] = requested
            if data["target"] == old_id:
                data["target"] = requested
            updated = ConnectorModel.from_dict(data)
            self._connectors[key] = updated
            changed_connectors.append((connector, updated))
        changed_groups: list[tuple[GroupModel, GroupModel]] = []
        for key, group in tuple(self._groups.items()):
            if old_id in group.members:
                data = group.to_dict()
                data["members"] = [requested if member == old_id else member for member in group.members]
                updated = GroupModel.from_dict(data)
                self._groups[key] = updated
                changed_groups.append((group, updated))
        self._revision += 1
        operation_id = uuid4().hex
        events = [
            OperationEvent(
                "element.renamed", "element", requested, self._revision,
                {"id": requested}, model.to_dict(), renamed.to_dict(), operation_id, origin=origin,
            )
        ]
        events.extend(
            OperationEvent(
                "connector.updated", "connector", current.id, self._revision,
                changed_fields(previous.to_dict(), current.to_dict()), previous.to_dict(), current.to_dict(),
                operation_id, origin=origin,
            )
            for previous, current in changed_connectors
        )
        events.extend(
            OperationEvent(
                "group.updated", "group", current.id, self._revision,
                changed_fields(previous.to_dict(), current.to_dict()), previous.to_dict(), current.to_dict(),
                operation_id, origin=origin,
            )
            for previous, current in changed_groups
        )
        committed = tuple(events)
        self._emit(committed)
        return committed

    def add_group(self, group: GroupModel | Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        model = group if isinstance(group, GroupModel) else GroupModel.from_dict(group)
        self._ensure_available_id(model.id)
        missing = [member for member in model.members if member not in self._elements and member not in self._groups]
        if missing:
            raise ValueError(f"Group {model.id!r} contains missing members: {missing}")
        self._groups[model.id] = model
        return self._commit("group.added", "group", model.id, current=model.to_dict(), origin=origin)

    def update_group(self, group_id: str, changes: Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        key = str(group_id)
        previous_model = self._groups.get(key)
        if previous_model is None:
            raise KeyError(f"Unknown MonkezCanva group: {key}")
        previous = previous_model.to_dict()
        current = dict(previous)
        current.update(_json_copy(dict(changes)))
        current["id"] = key
        model = GroupModel.from_dict(current)
        missing = [member for member in model.members if member not in self._elements and member not in self._groups]
        if missing:
            raise ValueError(f"Group {model.id!r} contains missing members: {missing}")
        self._groups[key] = model
        return self._commit(
            "group.updated", "group", key, changed_fields(previous, model.to_dict()),
            previous, model.to_dict(), origin,
        )

    def remove_group(self, group_id: str, *, origin: Any = None) -> OperationEvent:
        key = str(group_id)
        model = self._groups.pop(key, None)
        if model is None:
            raise KeyError(f"Unknown MonkezCanva group: {key}")
        changed_parents: list[tuple[GroupModel, GroupModel]] = []
        for parent_id, parent in tuple(self._groups.items()):
            if key not in parent.members:
                continue
            data = parent.to_dict()
            data["members"] = [member for member in parent.members if member != key]
            updated = GroupModel.from_dict(data)
            self._groups[parent_id] = updated
            changed_parents.append((parent, updated))
        self._revision += 1
        operation_id = uuid4().hex
        events = [
            OperationEvent(
                "group.updated", "group", current.id, self._revision,
                changed_fields(previous.to_dict(), current.to_dict()), previous.to_dict(), current.to_dict(),
                operation_id, origin=origin,
            )
            for previous, current in changed_parents
        ]
        removed = OperationEvent(
            "group.removed", "group", key, self._revision, previous=model.to_dict(),
            operation_id=operation_id, origin=origin,
        )
        events.append(removed)
        self._emit(events)
        return removed

    def add_resource(self, resource: ResourceModel | Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        model = resource if isinstance(resource, ResourceModel) else ResourceModel.from_dict(resource)
        if model.id in self._resources:
            raise ValueError(f"Duplicate MonkezCanva resource id: {model.id}")
        self._resources[model.id] = model
        return self._commit("resource.added", "resource", model.id, current=model.to_dict(), origin=origin)

    def update_resource(self, resource_id: str, changes: Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        key = str(resource_id)
        previous_model = self._resources.get(key)
        if previous_model is None:
            raise KeyError(f"Unknown MonkezCanva resource: {key}")
        previous = previous_model.to_dict()
        current = dict(previous)
        current.update(_json_copy(dict(changes)))
        current["id"] = key
        model = ResourceModel.from_dict(current)
        self._resources[key] = model
        return self._commit(
            "resource.updated", "resource", key, changed_fields(previous, model.to_dict()),
            previous, model.to_dict(), origin,
        )

    def remove_resource(self, resource_id: str, *, origin: Any = None) -> OperationEvent:
        key = str(resource_id)
        model = self._resources.pop(key, None)
        if model is None:
            raise KeyError(f"Unknown MonkezCanva resource: {key}")
        return self._commit("resource.removed", "resource", key, previous=model.to_dict(), origin=origin)

    def update_scene(self, changes: Mapping[str, Any], *, origin: Any = None) -> OperationEvent:
        previous = self._scene.to_dict()
        current = dict(previous)
        current.update(_json_copy(dict(changes)))
        self._scene = SceneModel.from_dict(current)
        return self._commit("scene.updated", "scene", "scene", changed_fields(previous, current), previous, current, origin)

    @staticmethod
    def _collect_record_changes(events, target_type: str, previous: Mapping[str, Any], current: Mapping[str, Any]) -> None:
        for target_id, model in previous.items():
            if target_id not in current:
                old = model.to_dict()
                events.append((f"{target_type}.removed", target_type, target_id, {}, old, {}))
        for target_id, model in current.items():
            new = model.to_dict()
            if target_id not in previous:
                events.append((f"{target_type}.added", target_type, target_id, new, {}, new))
            else:
                old = previous[target_id].to_dict()
                if old != new:
                    events.append((f"{target_type}.updated", target_type, target_id, changed_fields(old, new), old, new))

    def _commit(
        self,
        action: str,
        target_type: str,
        target_id: str,
        changes: Mapping[str, Any] | None = None,
        previous: Mapping[str, Any] | None = None,
        current: Mapping[str, Any] | None = None,
        origin: Any = None,
    ) -> OperationEvent:
        self._revision += 1
        event = OperationEvent(
            action, target_type, target_id, self._revision,
            _json_copy(changes or {}), _json_copy(previous or {}), _json_copy(current or {}), origin=origin,
        )
        self._emit((event,))
        return event

    def _emit(self, events: Iterable[OperationEvent]) -> None:
        listeners: list[DocumentListener] = []
        for token, stored in tuple(self._listeners.items()):
            listener = stored() if isinstance(stored, WeakMethod) else stored
            if listener is None:
                self._listeners.pop(token, None)
            else:
                listeners.append(listener)
        for event in events:
            for listener in listeners:
                listener(event)

    def _ensure_available_id(self, object_id: str) -> None:
        if object_id in self._elements or object_id in self._connectors or object_id in self._groups:
            raise ValueError(f"Duplicate MonkezCanva object id: {object_id}")

    def _required_element(self, element_id: str) -> ElementModel:
        model = self._elements.get(element_id)
        if model is None:
            raise KeyError(f"Unknown MonkezCanva element: {element_id}")
        return model

    def _validate_connector(self, connector: ConnectorModel) -> None:
        source = self._elements.get(connector.source)
        target = self._elements.get(connector.target)
        if source is None or target is None:
            raise ValueError(f"Connector {connector.id!r} refers to missing endpoints")
        source_ports = {port.id for port in source.ports}
        target_ports = {port.id for port in target.ports}
        if connector.source_port and connector.source_port not in source_ports:
            raise ValueError(f"Connector {connector.id!r} refers to missing source port {connector.source_port!r}")
        if connector.target_port and connector.target_port not in target_ports:
            raise ValueError(f"Connector {connector.id!r} refers to missing target port {connector.target_port!r}")

    def _validate(self) -> None:
        ids = [*self._elements, *self._connectors, *self._groups]
        if len(ids) != len(set(ids)):
            raise ValueError("MonkezCanva object IDs must be globally unique")
        for connector in self._connectors.values():
            self._validate_connector(connector)
        known = set(self._elements) | set(self._groups)
        for group in self._groups.values():
            missing = [member for member in group.members if member not in known]
            if missing:
                raise ValueError(f"Group {group.id!r} contains missing members: {missing}")
