"""Deterministic, Qt-free snapping primitives for MonkezCanva editors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


SNAP_TARGETS_KEY = "snapTargets"
SNAP_DISTANCE_KEY = "snapDistance"
SMART_GUIDES_KEY = "smartGuidesVisible"
SNAP_TARGETS = ("grid", "edges", "centers", "ports")


@dataclass(frozen=True, slots=True)
class SnapRect:
    x: float
    y: float
    width: float
    height: float

    @property
    def horizontal(self) -> tuple[float, float, float]:
        return self.x, self.x + self.width / 2, self.x + self.width

    @property
    def vertical(self) -> tuple[float, float, float]:
        return self.y, self.y + self.height / 2, self.y + self.height


@dataclass(frozen=True, slots=True)
class SnapGuide:
    axis: str
    value: float
    target: str


@dataclass(frozen=True, slots=True)
class SnapResult:
    x: float
    y: float
    guides: tuple[SnapGuide, ...] = ()


def normalize_snap_targets(values: Iterable[str] | None) -> tuple[str, ...]:
    requested = {str(value).strip().lower() for value in (values or ())}
    return tuple(target for target in SNAP_TARGETS if target in requested)


def _best_axis_snap(
    moving: Sequence[float], candidates: Sequence[tuple[float, str]], threshold: float
) -> tuple[float, float, str] | None:
    matches = (
        (abs(target - source), target - source, target, kind)
        for source in moving
        for target, kind in candidates
        if abs(target - source) <= threshold
    )
    best = min(matches, default=None, key=lambda value: (value[0], value[3], value[2]))
    return None if best is None else (best[1], best[2], best[3])


def snap_rect(
    moving: SnapRect,
    candidates: Iterable[SnapRect] = (),
    *,
    targets: Iterable[str] = SNAP_TARGETS,
    grid_size: float = 20.0,
    threshold: float = 8.0,
    moving_ports: Iterable[tuple[float, float]] = (),
    candidate_ports: Iterable[tuple[float, float]] = (),
) -> SnapResult:
    """Snap a rectangle by the nearest eligible target on each axis."""

    enabled = normalize_snap_targets(targets)
    threshold = max(0.0, float(threshold))
    x_candidates: list[tuple[float, str]] = []
    y_candidates: list[tuple[float, str]] = []
    for candidate in candidates:
        if "edges" in enabled:
            x_candidates.extend((value, "edge") for value in (candidate.horizontal[0], candidate.horizontal[2]))
            y_candidates.extend((value, "edge") for value in (candidate.vertical[0], candidate.vertical[2]))
        if "centers" in enabled:
            x_candidates.append((candidate.horizontal[1], "center"))
            y_candidates.append((candidate.vertical[1], "center"))

    moving_x: list[float] = []
    moving_y: list[float] = []
    if "edges" in enabled:
        moving_x.extend((moving.horizontal[0], moving.horizontal[2]))
        moving_y.extend((moving.vertical[0], moving.vertical[2]))
    if "centers" in enabled:
        moving_x.append(moving.horizontal[1])
        moving_y.append(moving.vertical[1])
    if "ports" in enabled:
        ports = tuple(candidate_ports)
        x_candidates.extend((x, "port") for x, _y in ports)
        y_candidates.extend((y, "port") for _x, y in ports)
        own_ports = tuple(moving_ports)
        moving_x.extend(x for x, _y in own_ports)
        moving_y.extend(y for _x, y in own_ports)

    x_match = _best_axis_snap(moving_x, x_candidates, threshold) if moving_x else None
    y_match = _best_axis_snap(moving_y, y_candidates, threshold) if moving_y else None
    guides: list[SnapGuide] = []
    x, y = moving.x, moving.y
    if x_match is not None:
        x += x_match[0]
        guides.append(SnapGuide("vertical", x_match[1], x_match[2]))
    elif "grid" in enabled and grid_size > 0:
        grid_x = round(x / grid_size) * grid_size
        if abs(grid_x - x) <= threshold:
            x = grid_x
    if y_match is not None:
        y += y_match[0]
        guides.append(SnapGuide("horizontal", y_match[1], y_match[2]))
    elif "grid" in enabled and grid_size > 0:
        grid_y = round(y / grid_size) * grid_size
        if abs(grid_y - y) <= threshold:
            y = grid_y
    return SnapResult(x, y, tuple(guides))
