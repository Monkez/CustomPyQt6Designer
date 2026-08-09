"""Deterministic, Qt-free graph layout strategies for MonkezCanva."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable, Mapping


LAYOUT_STRATEGIES = ("layered", "tree", "radial", "force")
LAYOUT_DIRECTIONS = ("right", "left", "down", "up")


@dataclass(frozen=True, slots=True)
class LayoutNode:
    id: str
    x: float = 0.0
    y: float = 0.0
    width: float = 120.0
    height: float = 72.0
    locked: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "LayoutNode":
        node_id = str(value.get("id", "")).strip()
        if not node_id:
            raise ValueError("Auto-layout nodes require a non-empty ID")
        return cls(
            node_id,
            float(value.get("x", 0.0)),
            float(value.get("y", 0.0)),
            max(1.0, float(value.get("width", 120.0))),
            max(1.0, float(value.get("height", 72.0))),
            bool(value.get("locked", False)),
        )


@dataclass(frozen=True, slots=True)
class LayoutEdge:
    source: str
    target: str
    weight: float = 1.0

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "LayoutEdge":
        source = str(value.get("source", "")).strip()
        target = str(value.get("target", "")).strip()
        if not source or not target:
            raise ValueError("Auto-layout edges require source and target IDs")
        return cls(source, target, max(0.01, float(value.get("weight", 1.0))))


@dataclass(frozen=True, slots=True)
class LayoutOptions:
    strategy: str = "layered"
    direction: str = "right"
    node_spacing: float = 48.0
    layer_spacing: float = 120.0
    component_spacing: float = 160.0
    iterations: int = 180
    start_angle: float = -90.0
    preserve_center: bool = True

    def normalized(self) -> "LayoutOptions":
        strategy = str(self.strategy).lower().strip().replace("_", "-")
        strategy = {"hierarchy": "layered", "hierarchical": "layered"}.get(
            strategy, strategy
        )
        if strategy not in LAYOUT_STRATEGIES:
            raise ValueError(f"Unsupported MonkezCanva layout strategy: {strategy}")
        direction = str(self.direction).lower().strip().replace("_", "-")
        direction = {
            "left-to-right": "right", "lr": "right", "horizontal": "right",
            "right-to-left": "left", "rl": "left",
            "top-to-bottom": "down", "tb": "down", "vertical": "down",
            "bottom-to-top": "up", "bt": "up",
        }.get(direction, direction)
        if direction not in LAYOUT_DIRECTIONS:
            raise ValueError(f"Unsupported MonkezCanva layout direction: {direction}")
        return LayoutOptions(
            strategy,
            direction,
            max(4.0, min(1000.0, float(self.node_spacing))),
            max(8.0, min(2000.0, float(self.layer_spacing))),
            max(8.0, min(4000.0, float(self.component_spacing))),
            max(1, min(2000, int(self.iterations))),
            float(self.start_angle),
            bool(self.preserve_center),
        )


@dataclass(frozen=True, slots=True)
class LayoutResult:
    positions: Mapping[str, tuple[float, float]]
    strategy: str
    direction: str
    component_count: int
    layer_count: int
    moved_count: int
    bounds: tuple[float, float, float, float]


def _normalize_nodes(
    values: Iterable[LayoutNode | Mapping[str, object]],
) -> dict[str, LayoutNode]:
    nodes: dict[str, LayoutNode] = {}
    for value in values:
        node = value if isinstance(value, LayoutNode) else LayoutNode.from_mapping(value)
        if node.id in nodes:
            raise ValueError(f"Duplicate auto-layout node ID: {node.id}")
        nodes[node.id] = node
    return nodes


def _normalize_edges(
    values: Iterable[LayoutEdge | Mapping[str, object]], node_ids: set[str]
) -> tuple[LayoutEdge, ...]:
    result: list[LayoutEdge] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        edge = value if isinstance(value, LayoutEdge) else LayoutEdge.from_mapping(value)
        if edge.source not in node_ids or edge.target not in node_ids:
            continue
        key = (edge.source, edge.target)
        if key not in seen:
            seen.add(key)
            result.append(edge)
    return tuple(result)


def _adjacency(
    node_ids: Iterable[str], edges: Iterable[LayoutEdge]
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    outgoing = {node_id: [] for node_id in node_ids}
    incoming = {node_id: [] for node_id in node_ids}
    undirected = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if edge.target not in outgoing[edge.source]:
            outgoing[edge.source].append(edge.target)
        if edge.source not in incoming[edge.target]:
            incoming[edge.target].append(edge.source)
        if edge.target != edge.source:
            if edge.target not in undirected[edge.source]:
                undirected[edge.source].append(edge.target)
            if edge.source not in undirected[edge.target]:
                undirected[edge.target].append(edge.source)
    return outgoing, incoming, undirected


def _components(node_ids: Iterable[str], undirected: Mapping[str, list[str]]) -> list[list[str]]:
    order = list(node_ids)
    remaining = set(order)
    result: list[list[str]] = []
    for start in order:
        if start not in remaining:
            continue
        remaining.remove(start)
        component: list[str] = []
        queue = deque([start])
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in undirected[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        result.append(component)
    return result


def _strongly_connected_components(
    node_ids: list[str], outgoing: Mapping[str, list[str]]
) -> list[list[str]]:
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []

    def visit(node_id: str) -> None:
        nonlocal index
        indexes[node_id] = lowlinks[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)
        for neighbor in outgoing[node_id]:
            if neighbor not in indexes:
                visit(neighbor)
                lowlinks[node_id] = min(lowlinks[node_id], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node_id] = min(lowlinks[node_id], indexes[neighbor])
        if lowlinks[node_id] != indexes[node_id]:
            return
        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node_id:
                break
        component.reverse()
        result.append(component)

    for node_id in node_ids:
        if node_id not in indexes:
            visit(node_id)
    return result


def _layer_ranks(
    node_ids: list[str], outgoing: Mapping[str, list[str]]
) -> dict[str, int]:
    components = _strongly_connected_components(node_ids, outgoing)
    component_of = {
        node_id: index for index, members in enumerate(components) for node_id in members
    }
    component_out: dict[int, set[int]] = {index: set() for index in range(len(components))}
    indegree = {index: 0 for index in range(len(components))}
    for source in node_ids:
        source_component = component_of[source]
        for target in outgoing[source]:
            target_component = component_of[target]
            if source_component != target_component and target_component not in component_out[source_component]:
                component_out[source_component].add(target_component)
                indegree[target_component] += 1
    queue = deque(index for index in range(len(components)) if indegree[index] == 0)
    ranks = {index: 0 for index in range(len(components))}
    while queue:
        current = queue.popleft()
        for target in sorted(component_out[current]):
            ranks[target] = max(ranks[target], ranks[current] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return {node_id: ranks[component_of[node_id]] for node_id in node_ids}


def _barycentric_order(
    layers: dict[int, list[str]],
    outgoing: Mapping[str, list[str]],
    incoming: Mapping[str, list[str]],
) -> None:
    if len(layers) < 2:
        return
    def indexes() -> dict[str, int]:
        return {
            node_id: position
            for rank in sorted(layers)
            for position, node_id in enumerate(layers[rank])
        }
    for _ in range(4):
        current_indexes = indexes()
        for rank in sorted(layers)[1:]:
            original = {node_id: position for position, node_id in enumerate(layers[rank])}
            layers[rank].sort(
                key=lambda node_id: (
                    sum(current_indexes[parent] for parent in incoming[node_id])
                    / max(1, len(incoming[node_id])),
                    original[node_id],
                )
            )
        current_indexes = indexes()
        for rank in reversed(sorted(layers)[:-1]):
            original = {node_id: position for position, node_id in enumerate(layers[rank])}
            layers[rank].sort(
                key=lambda node_id: (
                    sum(current_indexes[child] for child in outgoing[node_id])
                    / max(1, len(outgoing[node_id])),
                    original[node_id],
                )
            )


def _oriented_size(node: LayoutNode, direction: str) -> tuple[float, float]:
    return (node.width, node.height) if direction in ("right", "left") else (
        node.height, node.width
    )


def _from_oriented_center(
    primary: float, secondary: float, node: LayoutNode, direction: str
) -> tuple[float, float]:
    if direction == "right":
        center_x, center_y = primary, secondary
    elif direction == "left":
        center_x, center_y = -primary, secondary
    elif direction == "down":
        center_x, center_y = secondary, primary
    else:
        center_x, center_y = secondary, -primary
    return center_x - node.width / 2.0, center_y - node.height / 2.0


def _primary_centers(
    layers: Mapping[int, list[str]], nodes: Mapping[str, LayoutNode], options: LayoutOptions
) -> dict[int, float]:
    centers: dict[int, float] = {}
    cursor = 0.0
    for rank in sorted(layers):
        extent = max(_oriented_size(nodes[node_id], options.direction)[0] for node_id in layers[rank])
        centers[rank] = cursor + extent / 2.0
        cursor += extent + options.layer_spacing
    return centers


def _layered_component(
    node_ids: list[str],
    nodes: Mapping[str, LayoutNode],
    outgoing: Mapping[str, list[str]],
    incoming: Mapping[str, list[str]],
    options: LayoutOptions,
) -> tuple[dict[str, tuple[float, float]], int]:
    ranks = _layer_ranks(node_ids, outgoing)
    layers: dict[int, list[str]] = defaultdict(list)
    for node_id in node_ids:
        layers[ranks[node_id]].append(node_id)
    _barycentric_order(layers, outgoing, incoming)
    primary_centers = _primary_centers(layers, nodes, options)
    positions: dict[str, tuple[float, float]] = {}
    layer_extents: dict[int, float] = {}
    for rank, members in layers.items():
        extent = sum(_oriented_size(nodes[node_id], options.direction)[1] for node_id in members)
        extent += options.node_spacing * max(0, len(members) - 1)
        layer_extents[rank] = extent
    maximum_extent = max(layer_extents.values(), default=0.0)
    for rank, members in layers.items():
        cursor = (maximum_extent - layer_extents[rank]) / 2.0
        for node_id in members:
            node = nodes[node_id]
            secondary_size = _oriented_size(node, options.direction)[1]
            secondary = cursor + secondary_size / 2.0
            positions[node_id] = _from_oriented_center(
                primary_centers[rank], secondary, node, options.direction
            )
            cursor += secondary_size + options.node_spacing
    return positions, len(layers)


def _tree_component(
    node_ids: list[str],
    nodes: Mapping[str, LayoutNode],
    outgoing: Mapping[str, list[str]],
    incoming: Mapping[str, list[str]],
    options: LayoutOptions,
) -> tuple[dict[str, tuple[float, float]], int]:
    roots = [node_id for node_id in node_ids if not [p for p in incoming[node_id] if p in node_ids]]
    if not roots:
        roots = [node_ids[0]]
    parent: dict[str, str] = {}
    depth: dict[str, int] = {}
    children: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    queue = deque((root, 0) for root in roots)
    visited: set[str] = set()
    while queue:
        current, current_depth = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        depth[current] = current_depth
        for child in outgoing[current]:
            if child in node_ids and child not in visited and child not in parent:
                parent[child] = current
                children[current].append(child)
                queue.append((child, current_depth + 1))
    for node_id in node_ids:
        if node_id not in visited:
            roots.append(node_id)
            queue = deque([(node_id, 0)])
            while queue:
                current, current_depth = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                depth[current] = current_depth
                for child in outgoing[current]:
                    if child in node_ids and child not in visited and child not in parent:
                        parent[child] = current
                        children[current].append(child)
                        queue.append((child, current_depth + 1))

    subtree_extent: dict[str, float] = {}

    def measure(node_id: str) -> float:
        own = _oriented_size(nodes[node_id], options.direction)[1]
        child_extents = [measure(child) for child in children[node_id]]
        children_total = sum(child_extents) + options.node_spacing * max(0, len(child_extents) - 1)
        subtree_extent[node_id] = max(own, children_total)
        return subtree_extent[node_id]

    for root in roots:
        measure(root)
    secondary_centers: dict[str, float] = {}

    def place(node_id: str, start: float) -> None:
        members = children[node_id]
        if not members:
            secondary_centers[node_id] = start + subtree_extent[node_id] / 2.0
            return
        children_total = sum(subtree_extent[child] for child in members)
        children_total += options.node_spacing * max(0, len(members) - 1)
        cursor = start + (subtree_extent[node_id] - children_total) / 2.0
        for child in members:
            place(child, cursor)
            cursor += subtree_extent[child] + options.node_spacing
        secondary_centers[node_id] = (
            secondary_centers[members[0]] + secondary_centers[members[-1]]
        ) / 2.0

    root_cursor = 0.0
    for root in roots:
        place(root, root_cursor)
        root_cursor += subtree_extent[root] + options.component_spacing
    layers: dict[int, list[str]] = defaultdict(list)
    for node_id, rank in depth.items():
        layers[rank].append(node_id)
    primary_centers = _primary_centers(layers, nodes, options)
    return {
        node_id: _from_oriented_center(
            primary_centers[depth[node_id]], secondary_centers[node_id], nodes[node_id], options.direction
        )
        for node_id in node_ids
    }, len(layers)


def _radial_component(
    node_ids: list[str],
    nodes: Mapping[str, LayoutNode],
    undirected: Mapping[str, list[str]],
    outgoing: Mapping[str, list[str]],
    incoming: Mapping[str, list[str]],
    options: LayoutOptions,
) -> tuple[dict[str, tuple[float, float]], int]:
    roots = [node_id for node_id in node_ids if not incoming[node_id]]
    root = max(
        roots or node_ids,
        key=lambda node_id: (len(outgoing[node_id]), len(undirected[node_id]), -node_ids.index(node_id)),
    )
    distance = {root: 0}
    queue = deque([root])
    while queue:
        current = queue.popleft()
        for neighbor in undirected[current]:
            if neighbor in node_ids and neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    rings: dict[int, list[str]] = defaultdict(list)
    for node_id in node_ids:
        rings[distance.get(node_id, max(distance.values(), default=0) + 1)].append(node_id)
    positions: dict[str, tuple[float, float]] = {}
    positions[root] = (-nodes[root].width / 2.0, -nodes[root].height / 2.0)
    radius = 0.0
    start = math.radians(options.start_angle)
    for ring in sorted(rank for rank in rings if rank > 0):
        members = rings[ring]
        maximum = max(max(nodes[node_id].width, nodes[node_id].height) for node_id in members)
        circumference_radius = (
            sum(max(nodes[node_id].width, nodes[node_id].height) for node_id in members)
            + options.node_spacing * len(members)
        ) / (2.0 * math.pi)
        radius = max(radius + maximum + options.layer_spacing, circumference_radius)
        for index, node_id in enumerate(members):
            angle = start + 2.0 * math.pi * index / len(members)
            center_x = math.cos(angle) * radius
            center_y = math.sin(angle) * radius
            node = nodes[node_id]
            positions[node_id] = (center_x - node.width / 2.0, center_y - node.height / 2.0)
    return positions, len(rings)


def _force_component(
    node_ids: list[str],
    nodes: Mapping[str, LayoutNode],
    edges: Iterable[LayoutEdge],
    options: LayoutOptions,
) -> tuple[dict[str, tuple[float, float]], int]:
    count = len(node_ids)
    if count == 1:
        node = nodes[node_ids[0]]
        return {node.id: (node.x, node.y)}, 1
    centers = {
        node_id: [nodes[node_id].x + nodes[node_id].width / 2.0,
                  nodes[node_id].y + nodes[node_id].height / 2.0]
        for node_id in node_ids
    }
    unique_centers = {(round(value[0], 6), round(value[1], 6)) for value in centers.values()}
    if len(unique_centers) < max(2, count // 2):
        radius = max(100.0, count * (options.node_spacing + 30.0) / (2.0 * math.pi))
        for index, node_id in enumerate(node_ids):
            angle = 2.0 * math.pi * index / count
            centers[node_id] = [math.cos(angle) * radius, math.sin(angle) * radius]
    component_edges = [edge for edge in edges if edge.source in centers and edge.target in centers]
    area = max(40000.0, count * (options.layer_spacing + 80.0) ** 2)
    ideal = math.sqrt(area / count)
    temperature = ideal
    for iteration in range(options.iterations):
        displacement = {node_id: [0.0, 0.0] for node_id in node_ids}
        for index, first in enumerate(node_ids):
            for second in node_ids[index + 1:]:
                dx = centers[first][0] - centers[second][0]
                dy = centers[first][1] - centers[second][1]
                distance = max(0.01, math.hypot(dx, dy))
                force = ideal * ideal / distance
                fx, fy = dx / distance * force, dy / distance * force
                displacement[first][0] += fx
                displacement[first][1] += fy
                displacement[second][0] -= fx
                displacement[second][1] -= fy
        for edge in component_edges:
            dx = centers[edge.source][0] - centers[edge.target][0]
            dy = centers[edge.source][1] - centers[edge.target][1]
            distance = max(0.01, math.hypot(dx, dy))
            force = distance * distance / ideal * edge.weight
            fx, fy = dx / distance * force, dy / distance * force
            displacement[edge.source][0] -= fx
            displacement[edge.source][1] -= fy
            displacement[edge.target][0] += fx
            displacement[edge.target][1] += fy
        for node_id in node_ids:
            if nodes[node_id].locked:
                continue
            dx, dy = displacement[node_id]
            magnitude = max(0.01, math.hypot(dx, dy))
            centers[node_id][0] += dx / magnitude * min(magnitude, temperature)
            centers[node_id][1] += dy / magnitude * min(magnitude, temperature)
            centers[node_id][0] *= 0.995
            centers[node_id][1] *= 0.995
        temperature = ideal * max(0.01, 1.0 - (iteration + 1) / options.iterations)

    for _ in range(12):
        changed = False
        for index, first in enumerate(node_ids):
            for second in node_ids[index + 1:]:
                first_node, second_node = nodes[first], nodes[second]
                dx = centers[second][0] - centers[first][0]
                dy = centers[second][1] - centers[first][1]
                overlap_x = (first_node.width + second_node.width) / 2 + options.node_spacing - abs(dx)
                overlap_y = (first_node.height + second_node.height) / 2 + options.node_spacing - abs(dy)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                changed = True
                if overlap_x < overlap_y:
                    amount = overlap_x / 2.0
                    sign = 1.0 if dx >= 0 else -1.0
                    if not first_node.locked:
                        centers[first][0] -= sign * amount
                    if not second_node.locked:
                        centers[second][0] += sign * amount
                else:
                    amount = overlap_y / 2.0
                    sign = 1.0 if dy >= 0 else -1.0
                    if not first_node.locked:
                        centers[first][1] -= sign * amount
                    if not second_node.locked:
                        centers[second][1] += sign * amount
        if not changed:
            break
    return {
        node_id: (
            centers[node_id][0] - nodes[node_id].width / 2.0,
            centers[node_id][1] - nodes[node_id].height / 2.0,
        )
        for node_id in node_ids
    }, 1


def _bounds(
    positions: Mapping[str, tuple[float, float]], nodes: Mapping[str, LayoutNode]
) -> tuple[float, float, float, float]:
    if not positions:
        return (0.0, 0.0, 0.0, 0.0)
    left = min(positions[node_id][0] for node_id in positions)
    top = min(positions[node_id][1] for node_id in positions)
    right = max(positions[node_id][0] + nodes[node_id].width for node_id in positions)
    bottom = max(positions[node_id][1] + nodes[node_id].height for node_id in positions)
    return left, top, right - left, bottom - top


def _translate(
    positions: dict[str, tuple[float, float]], dx: float, dy: float
) -> dict[str, tuple[float, float]]:
    return {node_id: (x + dx, y + dy) for node_id, (x, y) in positions.items()}


def layout_graph(
    node_values: Iterable[LayoutNode | Mapping[str, object]],
    edge_values: Iterable[LayoutEdge | Mapping[str, object]] = (),
    *,
    options: LayoutOptions | None = None,
    strategy: str | None = None,
    direction: str | None = None,
    node_spacing: float | None = None,
    layer_spacing: float | None = None,
    component_spacing: float | None = None,
    iterations: int | None = None,
    preserve_center: bool | None = None,
) -> LayoutResult:
    """Lay out a graph and return deterministic top-left positions.

    Explicit keyword values override ``options``. Locked nodes are never moved;
    when a component has locked nodes its generated layout is anchored to their
    average displacement. Otherwise the complete result preserves its old center.
    """

    base = options or LayoutOptions()
    configured = LayoutOptions(
        base.strategy if strategy is None else strategy,
        base.direction if direction is None else direction,
        base.node_spacing if node_spacing is None else node_spacing,
        base.layer_spacing if layer_spacing is None else layer_spacing,
        base.component_spacing if component_spacing is None else component_spacing,
        base.iterations if iterations is None else iterations,
        base.start_angle,
        base.preserve_center if preserve_center is None else preserve_center,
    ).normalized()
    nodes = _normalize_nodes(node_values)
    if not nodes:
        return LayoutResult({}, configured.strategy, configured.direction, 0, 0, 0, (0, 0, 0, 0))
    edges = _normalize_edges(edge_values, set(nodes))
    outgoing, incoming, undirected = _adjacency(nodes, edges)
    components = _components(nodes, undirected)
    result: dict[str, tuple[float, float]] = {}
    pack_cursor = 0.0
    maximum_layers = 0
    for component in components:
        component_edges = [
            edge for edge in edges if edge.source in component and edge.target in component
        ]
        if configured.strategy == "layered":
            positions, layers = _layered_component(
                component, nodes, outgoing, incoming, configured
            )
        elif configured.strategy == "tree":
            positions, layers = _tree_component(
                component, nodes, outgoing, incoming, configured
            )
        elif configured.strategy == "radial":
            positions, layers = _radial_component(
                component, nodes, undirected, outgoing, incoming, configured
            )
        else:
            positions, layers = _force_component(
                component, nodes, component_edges, configured
            )
        maximum_layers = max(maximum_layers, layers)
        locked = [node_id for node_id in component if nodes[node_id].locked]
        if locked:
            dx = sum(nodes[node_id].x - positions[node_id][0] for node_id in locked) / len(locked)
            dy = sum(nodes[node_id].y - positions[node_id][1] for node_id in locked) / len(locked)
            positions = _translate(positions, dx, dy)
            locked_bounds = _bounds(positions, nodes)
            pack_cursor = max(
                pack_cursor,
                locked_bounds[0] + locked_bounds[2] + configured.component_spacing,
            )
        else:
            component_bounds = _bounds(positions, nodes)
            positions = _translate(
                positions,
                pack_cursor - component_bounds[0],
                -component_bounds[1],
            )
            packed_bounds = _bounds(positions, nodes)
            pack_cursor = packed_bounds[0] + packed_bounds[2] + configured.component_spacing
        for node_id in component:
            result[node_id] = (
                (nodes[node_id].x, nodes[node_id].y)
                if nodes[node_id].locked else positions[node_id]
            )
    if configured.preserve_center and not any(node.locked for node in nodes.values()):
        old_bounds = _bounds({node_id: (node.x, node.y) for node_id, node in nodes.items()}, nodes)
        new_bounds = _bounds(result, nodes)
        result = _translate(
            result,
            old_bounds[0] + old_bounds[2] / 2.0 - new_bounds[0] - new_bounds[2] / 2.0,
            old_bounds[1] + old_bounds[3] / 2.0 - new_bounds[1] - new_bounds[3] / 2.0,
        )
    moved = sum(
        1
        for node_id, position in result.items()
        if not math.isclose(position[0], nodes[node_id].x, abs_tol=1e-6)
        or not math.isclose(position[1], nodes[node_id].y, abs_tol=1e-6)
    )
    return LayoutResult(
        dict(result), configured.strategy, configured.direction,
        len(components), maximum_layers, moved, _bounds(result, nodes),
    )
