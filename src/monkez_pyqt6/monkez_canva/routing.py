"""Qt-free routing helpers for deterministic connector geometry."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from heapq import heappop, heappush
import math


Point = tuple[float, float]
Rect = tuple[float, float, float, float]


def parallel_lane_offset(
    connector_id: str, sibling_ids: Sequence[str], spacing: float = 22.0
) -> float:
    """Return a stable, symmetric lane offset for parallel connectors."""

    ordered = tuple(dict.fromkeys(str(value) for value in sibling_ids))
    if str(connector_id) not in ordered or len(ordered) < 2:
        return 0.0
    index = ordered.index(str(connector_id))
    return (index - (len(ordered) - 1) / 2) * max(0.0, float(spacing))


def orthogonal_points(
    start: Point,
    end: Point,
    waypoints: Iterable[Point] = (),
    *,
    lane_offset: float = 0.0,
) -> tuple[Point, ...]:
    """Build an axis-aligned route through optional user reroute points."""

    anchors = [start, *(tuple((float(x), float(y)) for x, y in waypoints)), end]
    if len(anchors) == 2:
        middle_x = (start[0] + end[0]) / 2 + float(lane_offset)
        return start, (middle_x, start[1]), (middle_x, end[1]), end
    result: list[Point] = [anchors[0]]
    for target in anchors[1:]:
        previous = result[-1]
        if previous[0] != target[0] and previous[1] != target[1]:
            result.append((target[0], previous[1]))
        if target != result[-1]:
            result.append(target)
    return tuple(result)


def deduplicate_points(points: Iterable[Point]) -> tuple[Point, ...]:
    result: list[Point] = []
    for point in points:
        normalized = (float(point[0]), float(point[1]))
        if not result or normalized != result[-1]:
            result.append(normalized)
    return tuple(result)


def simplify_collinear(points: Iterable[Point]) -> tuple[Point, ...]:
    normalized = list(deduplicate_points(points))
    if len(normalized) < 3:
        return tuple(normalized)
    result = [normalized[0]]
    for index, point in enumerate(normalized[1:-1], 1):
        previous, following = result[-1], normalized[index + 1]
        if not (
            math.isclose(previous[0], point[0]) and math.isclose(point[0], following[0])
            or math.isclose(previous[1], point[1]) and math.isclose(point[1], following[1])
        ):
            result.append(point)
    result.append(normalized[-1])
    return tuple(result)


def _expanded(rect: Rect, clearance: float) -> Rect:
    x, y, width, height = (float(value) for value in rect)
    margin = max(0.0, float(clearance))
    return x - margin, y - margin, width + margin * 2, height + margin * 2


def _point_blocked(point: Point, obstacles: Sequence[Rect]) -> bool:
    x, y = point
    return any(left < x < left + width and top < y < top + height for left, top, width, height in obstacles)


def _segment_clear(first: Point, second: Point, obstacles: Sequence[Rect]) -> bool:
    if math.isclose(first[1], second[1]):
        y = first[1]
        low, high = sorted((first[0], second[0]))
        return not any(top < y < top + height and low < left + width and high > left for left, top, width, height in obstacles)
    if math.isclose(first[0], second[0]):
        x = first[0]
        low, high = sorted((first[1], second[1]))
        return not any(left < x < left + width and low < top + height and high > top for left, top, width, height in obstacles)
    return False


def obstacle_avoiding_route(
    start: Point,
    end: Point,
    obstacles: Iterable[Rect] = (),
    *,
    clearance: float = 18.0,
    bend_penalty: float = 24.0,
) -> tuple[Point, ...]:
    """Find a deterministic Manhattan path around rectangular obstacles."""

    start = float(start[0]), float(start[1])
    end = float(end[0]), float(end[1])
    expanded = tuple(_expanded(rect, clearance) for rect in obstacles)
    xs = {start[0], end[0]}
    ys = {start[1], end[1]}
    for left, top, width, height in expanded:
        xs.update((left, left + width))
        ys.update((top, top + height))
    ordered_x, ordered_y = sorted(xs), sorted(ys)
    nodes = {
        (x, y) for x in ordered_x for y in ordered_y
        if not _point_blocked((x, y), expanded)
    }
    nodes.update((start, end))
    neighbors: dict[Point, list[tuple[Point, str]]] = {node: [] for node in nodes}
    for y in ordered_y:
        row = sorted((node for node in nodes if math.isclose(node[1], y)), key=lambda point: point[0])
        for first, second in zip(row, row[1:]):
            if _segment_clear(first, second, expanded):
                neighbors[first].append((second, "h"))
                neighbors[second].append((first, "h"))
    for x in ordered_x:
        column = sorted((node for node in nodes if math.isclose(node[0], x)), key=lambda point: point[1])
        for first, second in zip(column, column[1:]):
            if _segment_clear(first, second, expanded):
                neighbors[first].append((second, "v"))
                neighbors[second].append((first, "v"))

    queue: list[tuple[float, float, Point, str, tuple[Point, ...]]] = []
    heappush(queue, (abs(end[0] - start[0]) + abs(end[1] - start[1]), 0.0, start, "", (start,)))
    best: dict[tuple[Point, str], float] = {(start, ""): 0.0}
    while queue:
        _estimate, cost, point, direction, path = heappop(queue)
        if point == end:
            return simplify_collinear(path)
        if cost > best.get((point, direction), math.inf):
            continue
        for target, next_direction in neighbors.get(point, ()):
            distance = abs(target[0] - point[0]) + abs(target[1] - point[1])
            next_cost = cost + distance + (float(bend_penalty) if direction and direction != next_direction else 0.0)
            state = target, next_direction
            if next_cost >= best.get(state, math.inf):
                continue
            best[state] = next_cost
            heuristic = abs(end[0] - target[0]) + abs(end[1] - target[1])
            heappush(queue, (next_cost + heuristic, next_cost, target, next_direction, (*path, target)))
    return orthogonal_points(start, end)


def segment_intersection(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
    *,
    endpoint_margin: float = 0.001,
) -> Point | None:
    """Return a proper intersection, excluding shared/near endpoints."""

    x1, y1 = first_start
    x2, y2 = first_end
    x3, y3 = second_start
    x4, y4 = second_end
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if math.isclose(denominator, 0.0):
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denominator
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denominator
    margin = max(0.0, float(endpoint_margin))
    if not margin < t < 1.0 - margin or not margin < u < 1.0 - margin:
        return None
    return x1 + t * (x2 - x1), y1 + t * (y2 - y1)
