"""Qt-free routing helpers for deterministic connector geometry."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


Point = tuple[float, float]


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
