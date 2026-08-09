"""Qt-free group, swimlane and reusable-subflow helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


Rect = tuple[float, float, float, float]
GROUP_KINDS = ("frame", "swimlane", "subflow")


def normalize_group_kind(value: Any) -> str:
    kind = str(value or "frame").strip().lower()
    if kind not in GROUP_KINDS:
        raise ValueError(f"Unsupported MonkezCanva group kind: {kind}")
    return kind


def group_bounds(
    rectangles: Iterable[Rect],
    *,
    padding: float = 28.0,
    header: float = 38.0,
    minimum_size: tuple[float, float] = (180.0, 110.0),
) -> Rect:
    """Return a padded group rectangle around scene-space member rectangles."""

    values = [tuple(float(value) for value in rectangle) for rectangle in rectangles]
    pad = max(0.0, float(padding))
    title_height = max(0.0, float(header))
    minimum_width, minimum_height = (max(1.0, float(value)) for value in minimum_size)
    if not values:
        return 0.0, 0.0, minimum_width, minimum_height
    left = min(rectangle[0] for rectangle in values)
    top = min(rectangle[1] for rectangle in values)
    right = max(rectangle[0] + rectangle[2] for rectangle in values)
    bottom = max(rectangle[1] + rectangle[3] for rectangle in values)
    x = left - pad
    y = top - pad - title_height
    return (
        x,
        y,
        max(minimum_width, right - left + pad * 2),
        max(minimum_height, bottom - top + pad * 2 + title_height),
    )


def descendant_element_ids(
    group_id: str,
    groups: Mapping[str, Mapping[str, Any]],
    element_ids: Iterable[str],
) -> tuple[str, ...]:
    """Flatten nested groups to stable, unique element IDs."""

    known_elements = {str(value) for value in element_ids}
    result: list[str] = []
    seen_elements: set[str] = set()
    visiting: set[str] = set()

    def visit(current_id: str) -> None:
        if current_id in visiting:
            raise ValueError(f"Group cycle detected at {current_id!r}")
        record = groups.get(current_id)
        if record is None:
            return
        visiting.add(current_id)
        try:
            for raw_member in record.get("members", ()):
                member = str(raw_member)
                if member in known_elements and member not in seen_elements:
                    seen_elements.add(member)
                    result.append(member)
                elif member in groups:
                    visit(member)
        finally:
            visiting.remove(current_id)

    visit(str(group_id))
    return tuple(result)


def validate_group_graph(
    groups: Mapping[str, Mapping[str, Any]], element_ids: Iterable[str]
) -> None:
    """Validate membership references and reject direct or indirect cycles."""

    known_elements = {str(value) for value in element_ids}
    known_groups = {str(value) for value in groups}
    for group_id, record in groups.items():
        normalize_group_kind(record.get("kind", "frame"))
        missing = [
            str(member)
            for member in record.get("members", ())
            if str(member) not in known_elements and str(member) not in known_groups
        ]
        if missing:
            raise ValueError(f"Group {group_id!r} contains missing members: {missing}")
        descendant_element_ids(str(group_id), groups, known_elements)
