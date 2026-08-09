"""Qt-free graph exchange helpers for MonkezCanva documents.

The exporters intentionally target a conservative subset of DOT and Mermaid so
the output remains readable, deterministic and safe to embed in documentation.
They never mutate the source document and can be used in headless tooling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .models import CanvasDocument


GRAPH_DIRECTIONS = ("TB", "TD", "BT", "LR", "RL")
EXPORT_PAGE_SIZES = ("A3", "A4", "A5", "LETTER", "LEGAL")
EXPORT_PAGE_ORIENTATIONS = ("portrait", "landscape")


@dataclass(frozen=True, slots=True)
class CanvasPageConfig:
    """Portable page settings shared by PDF export and printing."""

    size: str = "A4"
    orientation: str = "landscape"
    margin_left_mm: float = 12.0
    margin_top_mm: float = 12.0
    margin_right_mm: float = 12.0
    margin_bottom_mm: float = 12.0
    resolution: int = 144

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_page_config(
    value: CanvasPageConfig | Mapping[str, Any] | None,
) -> CanvasPageConfig:
    if isinstance(value, CanvasPageConfig):
        return value
    raw = dict(value or {})
    size = str(raw.get("size", "A4")).upper().strip()
    if size not in EXPORT_PAGE_SIZES:
        raise ValueError(f"Unsupported export page size: {size}")
    orientation = str(raw.get("orientation", "landscape")).lower().strip()
    if orientation not in EXPORT_PAGE_ORIENTATIONS:
        raise ValueError(f"Unsupported export page orientation: {orientation}")

    def margin(name: str) -> float:
        return max(0.0, min(100.0, float(raw.get(name, 12.0))))

    return CanvasPageConfig(
        size=size,
        orientation=orientation,
        margin_left_mm=margin("margin_left_mm"),
        margin_top_mm=margin("margin_top_mm"),
        margin_right_mm=margin("margin_right_mm"),
        margin_bottom_mm=margin("margin_bottom_mm"),
        resolution=max(72, min(1200, int(raw.get("resolution", 144)))),
    )


@dataclass(frozen=True, slots=True)
class GraphSelection:
    """Resolved records for an entire document or an object-ID subset."""

    elements: tuple[Mapping[str, Any], ...]
    connectors: tuple[Mapping[str, Any], ...]
    object_ids: frozenset[str]


def _plain_document(document: CanvasDocument | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(document, CanvasDocument):
        return document.to_dict()
    return CanvasDocument.from_dict(document).to_dict()


def select_graph(
    document: CanvasDocument | Mapping[str, Any],
    object_ids: Iterable[str] | None = None,
) -> GraphSelection:
    """Resolve graph records, including connectors internal to a node selection."""

    data = _plain_document(document)
    elements = tuple(data.get("elements", ()))
    connectors = tuple(data.get("connectors", ()))
    groups = {str(item["id"]): item for item in data.get("groups", ())}
    element_ids = {str(item["id"]) for item in elements}
    connector_ids = {str(item["id"]) for item in connectors}
    known_ids = element_ids | connector_ids | set(groups)
    visited: set[str] = set()
    if object_ids is None:
        requested = known_ids
        selected_elements = element_ids
        selected_connectors = connector_ids
    else:
        requested = {str(value).strip() for value in object_ids if str(value).strip()}
        missing = sorted(requested - known_ids)
        if missing:
            raise KeyError(f"Unknown MonkezCanva export object IDs: {missing}")
        selected_elements = requested & element_ids
        pending = list(requested & set(groups))
        while pending:
            group_id = pending.pop()
            if group_id in visited:
                continue
            visited.add(group_id)
            for member in groups[group_id].get("members", ()):
                member_id = str(member)
                if member_id in element_ids:
                    selected_elements.add(member_id)
                elif member_id in groups:
                    pending.append(member_id)
        selected_connectors = requested & connector_ids
        selected_connectors.update(
            str(item["id"])
            for item in connectors
            if str(item.get("source", "")) in selected_elements and str(item.get("target", "")) in selected_elements
        )
    return GraphSelection(
        tuple(item for item in elements if str(item["id"]) in selected_elements),
        tuple(item for item in connectors if str(item["id"]) in selected_connectors),
        frozenset(requested | selected_elements | selected_connectors | visited),
    )


def _label(record: Mapping[str, Any]) -> str:
    for key in ("text", "label", "title", "name"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    return str(record.get("id", "Object"))


def _dot_quote(value: Any) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    text = text.replace("\r", "").replace("\n", "\\n")
    return f'"{text}"'


def _dot_shape(type_id: str) -> str:
    key = str(type_id).lower()
    if "decision" in key or key in {"diamond"}:
        return "diamond"
    if "database" in key:
        return "cylinder"
    if "terminator" in key or key in {"ellipse"}:
        return "ellipse"
    if "annotation" in key or "note" in key:
        return "note"
    return "box"


def export_dot(
    document: CanvasDocument | Mapping[str, Any],
    object_ids: Iterable[str] | None = None,
    *,
    graph_name: str = "MonkezCanva",
    include_positions: bool = True,
) -> str:
    """Export a deterministic directed graph in a portable DOT subset."""

    selection = select_graph(document, object_ids)
    lines = [f"digraph {_dot_quote(graph_name)} {{", "  graph [overlap=false, splines=true];"]
    lines.append('  node [fontname="Arial", style="rounded,filled", fillcolor="#ffffff"];')
    lines.append('  edge [fontname="Arial"];')
    for element in selection.elements:
        attributes = {
            "label": _label(element),
            "shape": _dot_shape(str(element.get("type", ""))),
            "monkez_type": str(element.get("type", "")),
        }
        if include_positions:
            x = float(element.get("x", 0.0))
            y = float(element.get("y", 0.0))
            attributes["pos"] = f"{x:g},{-y:g}!"
            attributes["width"] = f"{max(1.0, float(element.get('width', 120.0))) / 72.0:.4g}"
            attributes["height"] = f"{max(1.0, float(element.get('height', 72.0))) / 72.0:.4g}"
            attributes["fixedsize"] = "true"
        rendered = ", ".join(f"{key}={_dot_quote(value)}" for key, value in attributes.items())
        lines.append(f"  {_dot_quote(element['id'])} [{rendered}];")
    exported_ids = {str(item["id"]) for item in selection.elements}
    for connector in selection.connectors:
        source = str(connector.get("source", ""))
        target = str(connector.get("target", ""))
        if source not in exported_ids or target not in exported_ids:
            continue
        attributes: dict[str, str] = {
            "id": str(connector["id"]),
            "monkez_type": "connector",
        }
        label = _label(connector)
        if label != str(connector["id"]):
            attributes["label"] = label
        if connector.get("sourcePort"):
            attributes["monkez_source_port"] = str(connector["sourcePort"])
        if connector.get("targetPort"):
            attributes["monkez_target_port"] = str(connector["targetPort"])
        arrow_start = bool(connector.get("arrowStart", False))
        arrow_end = bool(connector.get("arrowEnd", True))
        attributes["dir"] = (
            "both" if arrow_start and arrow_end else "back" if arrow_start else "forward" if arrow_end else "none"
        )
        rendered = ", ".join(f"{key}={_dot_quote(value)}" for key, value in attributes.items())
        lines.append(f"  {_dot_quote(source)} -> {_dot_quote(target)} [{rendered}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _mermaid_text(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\r", "")
        .replace("\n", "<br/>")
    )


def _mermaid_node(alias: str, record: Mapping[str, Any]) -> str:
    label = _mermaid_text(_label(record))
    key = str(record.get("type", "")).lower()
    if "decision" in key or key == "diamond":
        return f'{alias}{{"{label}"}}'
    if "database" in key:
        return f'{alias}[("{label}")]'
    if "terminator" in key or key == "ellipse":
        return f'{alias}(["{label}"])'
    if "annotation" in key or "note" in key:
        return f'{alias}[>"{label}"]'
    return f'{alias}["{label}"]'


def export_mermaid(
    document: CanvasDocument | Mapping[str, Any],
    object_ids: Iterable[str] | None = None,
    *,
    direction: str = "LR",
) -> str:
    """Export a conservative Mermaid flowchart with stable ID comments."""

    normalized_direction = str(direction).upper().strip()
    if normalized_direction not in GRAPH_DIRECTIONS:
        raise ValueError(f"Unsupported Mermaid graph direction: {direction}")
    selection = select_graph(document, object_ids)
    aliases = {str(item["id"]): f"n{index}" for index, item in enumerate(selection.elements)}
    lines = [f"flowchart {normalized_direction}"]
    for element in selection.elements:
        element_id = str(element["id"])
        lines.append(f"  {_mermaid_node(aliases[element_id], element)}")
        lines.append(f"  %% {aliases[element_id]} = {element_id}")
    for connector in selection.connectors:
        source = str(connector.get("source", ""))
        target = str(connector.get("target", ""))
        if source not in aliases or target not in aliases:
            continue
        arrow_start = bool(connector.get("arrowStart", False))
        arrow_end = bool(connector.get("arrowEnd", True))
        operator = "<-->" if arrow_start and arrow_end else "<--" if arrow_start else "-->" if arrow_end else "---"
        label = _label(connector)
        label_part = "" if label == str(connector["id"]) else f'|"{_mermaid_text(label)}"|'
        lines.append(f"  {aliases[source]} {operator}{label_part} {aliases[target]}")
    return "\n".join(lines) + "\n"
