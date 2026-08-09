"""Qt-free render policy and metrics for large MonkezCanva scenes."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Any


PERFORMANCE_MODES = ("auto", "quality", "speed")
RENDER_TIERS = ("overview", "compact", "full")


def normalize_performance_mode(value: object) -> str:
    mode = str(value).strip().lower()
    if mode not in PERFORMANCE_MODES:
        raise ValueError(
            f"Unsupported canvas performance mode: {value!r}; "
            f"expected one of {', '.join(PERFORMANCE_MODES)}"
        )
    return mode


def estimate_transform_lod(
    m11: float, m12: float, m21: float, m22: float
) -> float:
    """Return a rotation/shear-safe scale estimate for a 2D transform."""

    determinant = float(m11) * float(m22) - float(m12) * float(m21)
    if not math.isfinite(determinant):
        return 1.0
    return max(0.0, math.sqrt(abs(determinant)))


def adaptive_grid_step(
    grid_size: float,
    lod: float,
    *,
    minimum_screen_spacing: float = 10.0,
    maximum_multiplier: int = 64,
) -> float:
    """Increase only the painted grid step while preserving document snap size."""

    base = max(1.0, float(grid_size))
    scale = max(0.0001, float(lod))
    target = max(2.0, float(minimum_screen_spacing))
    limit = max(1, int(maximum_multiplier))
    multiplier = 1
    while multiplier < limit and base * scale * multiplier < target:
        multiplier *= 2
    return base * min(multiplier, limit)


@dataclass(frozen=True, slots=True)
class RenderProfile:
    """Features allowed for one item at the current zoom and scene pressure."""

    tier: str
    draw_text: bool
    draw_ports: bool
    draw_details: bool
    draw_effects: bool
    smooth_media: bool
    draw_connector_labels: bool
    draw_connector_decorations: bool

    def to_dict(self) -> dict[str, bool | str]:
        return {
            "tier": self.tier,
            "drawText": self.draw_text,
            "drawPorts": self.draw_ports,
            "drawDetails": self.draw_details,
            "drawEffects": self.draw_effects,
            "smoothMedia": self.smooth_media,
            "drawConnectorLabels": self.draw_connector_labels,
            "drawConnectorDecorations": self.draw_connector_decorations,
        }


@dataclass(frozen=True, slots=True)
class CanvasPerformancePolicy:
    """Deterministic LOD thresholds shared by Qt and headless benchmarks."""

    mode: str = "auto"
    overview_lod: float = 0.24
    compact_lod: float = 0.58
    large_scene_objects: int = 1_000
    huge_scene_objects: int = 10_000

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", normalize_performance_mode(self.mode))
        if not 0.01 <= float(self.overview_lod) < float(self.compact_lod):
            raise ValueError("LOD thresholds must satisfy 0.01 <= overview < compact")
        if int(self.large_scene_objects) < 100:
            raise ValueError("large_scene_objects must be at least 100")
        if int(self.huge_scene_objects) <= int(self.large_scene_objects):
            raise ValueError("huge_scene_objects must exceed large_scene_objects")

    def with_mode(self, mode: object) -> "CanvasPerformancePolicy":
        return CanvasPerformancePolicy(
            normalize_performance_mode(mode),
            self.overview_lod,
            self.compact_lod,
            self.large_scene_objects,
            self.huge_scene_objects,
        )

    def resolve(
        self,
        lod: float,
        object_count: int,
        *,
        selected: bool = False,
        has_packets: bool = False,
    ) -> RenderProfile:
        lod = max(0.0, float(lod))
        count = max(0, int(object_count))
        if self.mode == "quality" or (selected and self.mode != "speed"):
            tier = "full"
        elif self.mode == "speed":
            tier = "compact" if selected else "overview"
        else:
            pressure = (
                0.16
                if count >= self.huge_scene_objects
                else 0.08
                if count >= self.large_scene_objects
                else 0.0
            )
            if lod < self.overview_lod + pressure:
                tier = "overview"
            elif lod < self.compact_lod + pressure:
                tier = "compact"
            else:
                tier = "full"
        if tier == "full":
            return RenderProfile(tier, True, True, True, True, True, True, True)
        if tier == "compact":
            return RenderProfile(
                tier, True, False, False, bool(has_packets), False, False, False
            )
        return RenderProfile(
            tier, False, False, False, bool(has_packets), False, False, False
        )


class PerformanceTracker:
    """Bounded frame metrics with no Qt dependency and no document mutation."""

    def __init__(self, history_limit: int = 120) -> None:
        self._durations: deque[float] = deque(maxlen=max(8, int(history_limit)))
        self._frame_count = 0
        self._paint_counts: dict[str, int] = {}
        self._tier_counts: dict[str, int] = {}
        self._last_paint_counts: dict[str, int] = {}
        self._last_tier_counts: dict[str, int] = {}
        self._last_object_count = 0
        self._last_lod = 1.0

    def begin_frame(self) -> None:
        self._paint_counts = {}
        self._tier_counts = {}

    def record_paint(self, kind: str, tier: str) -> None:
        key = str(kind).strip().lower() or "object"
        normalized_tier = str(tier).strip().lower()
        if normalized_tier not in RENDER_TIERS:
            raise ValueError(f"Unsupported render tier: {tier!r}")
        self._paint_counts[key] = self._paint_counts.get(key, 0) + 1
        self._tier_counts[normalized_tier] = (
            self._tier_counts.get(normalized_tier, 0) + 1
        )

    def finish_frame(
        self, duration_ms: float, *, object_count: int, lod: float
    ) -> dict[str, Any]:
        duration = max(0.0, float(duration_ms))
        self._durations.append(duration)
        self._frame_count += 1
        self._last_paint_counts = dict(self._paint_counts)
        self._last_tier_counts = dict(self._tier_counts)
        self._last_object_count = max(0, int(object_count))
        self._last_lod = max(0.0, float(lod))
        return self.snapshot()

    def reset(self) -> None:
        self._durations.clear()
        self._frame_count = 0
        self._paint_counts = {}
        self._tier_counts = {}
        self._last_paint_counts = {}
        self._last_tier_counts = {}
        self._last_object_count = 0
        self._last_lod = 1.0

    def snapshot(self) -> dict[str, Any]:
        durations = tuple(self._durations)
        ordered = sorted(durations)
        p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
        return {
            "frameCount": self._frame_count,
            "sampleCount": len(durations),
            "lastFrameMs": round(durations[-1], 4) if durations else 0.0,
            "averageFrameMs": (
                round(sum(durations) / len(durations), 4) if durations else 0.0
            ),
            "p95FrameMs": round(ordered[p95_index], 4) if ordered else 0.0,
            "maxFrameMs": round(max(durations), 4) if durations else 0.0,
            "objectCount": self._last_object_count,
            "lod": round(self._last_lod, 4),
            "paintedObjects": sum(self._last_paint_counts.values()),
            "paintCounts": dict(self._last_paint_counts),
            "tierCounts": dict(self._last_tier_counts),
        }
