"""Qt-free graph exchange helpers for MonkezCanva documents.

The exporters intentionally target a conservative subset of DOT and Mermaid so
the output remains readable, deterministic and safe to embed in documentation.
They never mutate the source document and can be used in headless tooling.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .auto_layout import LayoutEdge, LayoutNode, LayoutOptions, layout_graph
from .models import CanvasDocument


GRAPH_DIRECTIONS = ("TB", "TD", "BT", "LR", "RL")
EXPORT_PAGE_SIZES = ("A3", "A4", "A5", "LETTER", "LEGAL")
EXPORT_PAGE_ORIENTATIONS = ("portrait", "landscape")
MAX_DOT_BYTES = 5 * 1024 * 1024
MAX_DOT_OBJECTS = 10_000


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


@dataclass(frozen=True, slots=True)
class DotImportResult:
    """Validated portable records produced by the constrained DOT parser."""

    name: str
    directed: bool
    elements: tuple[Mapping[str, Any], ...]
    connectors: tuple[Mapping[str, Any], ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "directed": self.directed,
            "elements": [dict(record) for record in self.elements],
            "connectors": [dict(record) for record in self.connectors],
            "warnings": list(self.warnings),
        }


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


@dataclass(frozen=True, slots=True)
class _DotToken:
    kind: str
    value: str
    offset: int


def _dot_tokens(value: bytes | str) -> tuple[_DotToken, ...]:
    if isinstance(value, bytes):
        if len(value) > MAX_DOT_BYTES:
            raise ValueError("DOT input is too large")
        text = value.decode("utf-8-sig")
    else:
        text = str(value)
        if len(text.encode("utf-8")) > MAX_DOT_BYTES:
            raise ValueError("DOT input is too large")
        text = text.removeprefix("\ufeff")
    result: list[_DotToken] = []
    index = 0
    punctuation = "{}[];,=:\n"
    while index < len(text):
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if character == "#":
            index = text.find("\n", index)
            if index < 0:
                break
            continue
        if text.startswith("//", index):
            index = text.find("\n", index + 2)
            if index < 0:
                break
            continue
        if text.startswith("/*", index):
            closing = text.find("*/", index + 2)
            if closing < 0:
                raise ValueError(f"Unterminated DOT comment at offset {index}")
            index = closing + 2
            continue
        if text.startswith("->", index) or text.startswith("--", index):
            result.append(_DotToken("edge", text[index : index + 2], index))
            index += 2
            continue
        if character in punctuation:
            if character != "\n":
                result.append(_DotToken(character, character, index))
            index += 1
            continue
        if character == '"':
            start = index
            index += 1
            decoded: list[str] = []
            while index < len(text) and text[index] != '"':
                if text[index] == "\\":
                    index += 1
                    if index >= len(text):
                        raise ValueError(f"Unterminated DOT string at offset {start}")
                    escaped = text[index]
                    decoded.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                else:
                    decoded.append(text[index])
                index += 1
            if index >= len(text):
                raise ValueError(f"Unterminated DOT string at offset {start}")
            result.append(_DotToken("id", "".join(decoded), start))
            index += 1
            continue
        if character == "<":
            raise ValueError(
                f"HTML-like DOT labels are not supported at offset {index}"
            )
        start = index
        while index < len(text):
            if text[index].isspace() or text[index] in punctuation + '"<':
                break
            if text.startswith("->", index) or text.startswith("--", index):
                break
            index += 1
        if index == start:
            raise ValueError(f"Unsupported DOT token at offset {index}: {text[index]!r}")
        result.append(_DotToken("id", text[start:index], start))
        if len(result) > MAX_DOT_OBJECTS * 32:
            raise ValueError("DOT input contains too many tokens")
    result.append(_DotToken("eof", "", len(text)))
    return tuple(result)


class _DotParser:
    def __init__(self, tokens: tuple[_DotToken, ...]) -> None:
        self.tokens = tokens
        self.index = 0
        self.directed = True
        self.name = "Imported DOT"
        self.graph_attributes: dict[str, str] = {}
        self.node_defaults: dict[str, str] = {}
        self.edge_defaults: dict[str, str] = {}
        self.nodes: OrderedDict[str, dict[str, str]] = OrderedDict()
        self.edges: list[tuple[tuple[str, str], tuple[str, str], dict[str, str], str]] = []

    @property
    def current(self) -> _DotToken:
        return self.tokens[self.index]

    def _advance(self) -> _DotToken:
        token = self.current
        self.index += 1
        return token

    def _accept(self, kind: str, value: str = "") -> _DotToken | None:
        token = self.current
        if token.kind != kind or value and token.value.casefold() != value.casefold():
            return None
        self.index += 1
        return token

    def _require(self, kind: str, value: str = "") -> _DotToken:
        token = self._accept(kind, value)
        if token is None:
            expectation = value or kind
            raise ValueError(
                f"Expected {expectation!r} at DOT offset {self.current.offset}, "
                f"found {self.current.value or self.current.kind!r}"
            )
        return token

    def _identifier(self) -> str:
        return self._require("id").value

    def _attributes(self) -> dict[str, str]:
        result: dict[str, str] = {}
        while self._accept("[") is not None:
            while self._accept("]") is None:
                if self.current.kind == "eof":
                    raise ValueError("Unterminated DOT attribute list")
                key = self._identifier().strip().lower()
                value = "true"
                if self._accept("=") is not None:
                    value = self._identifier()
                if key:
                    result[key] = value
                self._accept(",")
                self._accept(";")
        return result

    def _endpoint(self) -> tuple[str, str]:
        node_id = self._identifier().strip()
        if not node_id:
            raise ValueError("DOT node IDs cannot be empty")
        port_id = ""
        if self._accept(":") is not None:
            port_id = self._identifier().strip()
            if self._accept(":") is not None:
                self._identifier()  # compass point, deliberately ignored
        self.nodes.setdefault(node_id, dict(self.node_defaults))
        return node_id, port_id

    def parse(self) -> None:
        if self.current.kind == "id" and self.current.value.casefold() == "strict":
            self._advance()
        graph_kind = self._identifier().casefold()
        if graph_kind not in {"graph", "digraph"}:
            raise ValueError("DOT input must start with graph or digraph")
        self.directed = graph_kind == "digraph"
        if self.current.kind == "id":
            self.name = self._identifier().strip() or self.name
        self._require("{")
        statements = 0
        while self._accept("}") is None:
            if self.current.kind == "eof":
                raise ValueError("Unterminated DOT graph")
            if self._accept(";") is not None or self._accept(",") is not None:
                continue
            statements += 1
            if statements > MAX_DOT_OBJECTS * 4:
                raise ValueError("DOT input contains too many statements")
            if self.current.kind == "id" and self.current.value.casefold() == "subgraph":
                raise ValueError(
                    f"DOT subgraphs are not supported at offset {self.current.offset}"
                )
            if self.current.kind == "id" and self.current.value.casefold() in {
                "graph",
                "node",
                "edge",
            }:
                target = self._identifier().casefold()
                attributes = self._attributes()
                if not attributes:
                    raise ValueError(f"DOT {target} defaults require an attribute list")
                if target == "graph":
                    self.graph_attributes.update(attributes)
                elif target == "node":
                    self.node_defaults.update(attributes)
                else:
                    self.edge_defaults.update(attributes)
                self._accept(";")
                continue
            first = self._endpoint()
            if self._accept("=") is not None:
                self.nodes.pop(first[0], None)
                self.graph_attributes[first[0].lower()] = self._identifier()
                self._accept(";")
                continue
            edge_token = self._accept("edge")
            if edge_token is not None:
                endpoints = [first, self._endpoint()]
                operators = [edge_token.value]
                while (edge_token := self._accept("edge")) is not None:
                    operators.append(edge_token.value)
                    endpoints.append(self._endpoint())
                attributes = {**self.edge_defaults, **self._attributes()}
                for index, operator in enumerate(operators):
                    self.edges.append(
                        (endpoints[index], endpoints[index + 1], dict(attributes), operator)
                    )
            else:
                self.nodes[first[0]].update(self._attributes())
            self._accept(";")
        self._accept(";")
        self._require("eof")
        if len(self.nodes) + len(self.edges) > MAX_DOT_OBJECTS:
            raise ValueError("DOT input contains too many graph objects")


def _dot_float(
    value: Any,
    default: float,
    *,
    minimum: float = -1e9,
    maximum: float = 1e9,
) -> float:
    try:
        return max(minimum, min(maximum, float(str(value).rstrip("!"))))
    except (TypeError, ValueError):
        return default


def _dot_position(value: str) -> tuple[float, float] | None:
    parts = str(value).rstrip("!").split(",")
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), -float(parts[1])
    except ValueError:
        return None


def _dot_element_type(attributes: Mapping[str, str]) -> str:
    declared = str(attributes.get("monkez_type", "")).strip().lower()
    if declared and declared != "connector":
        return declared
    shape = str(attributes.get("shape", "box")).lower()
    return {
        "diamond": "diamond",
        "ellipse": "ellipse",
        "circle": "ellipse",
        "oval": "ellipse",
        "plaintext": "text",
        "none": "text",
    }.get(shape, "rectangle")


def import_dot(value: bytes | str) -> DotImportResult:
    """Parse a safe DOT subset into portable MonkezCanva element records.

    Supported input covers ordinary node/edge statements, chained edges,
    quoted IDs, graph/node/edge defaults, endpoint ports and the attributes
    emitted by :func:`export_dot`. HTML labels, subgraphs and executable or
    external Graphviz features are deliberately rejected.
    """

    parser = _DotParser(_dot_tokens(value))
    parser.parse()
    warnings: list[str] = []
    edge_records: list[dict[str, Any]] = []
    occupied_ids = set(parser.nodes)
    edge_counter = 0

    def allocate_edge_id(requested: str) -> str:
        nonlocal edge_counter
        base = requested.strip()
        if not base:
            edge_counter += 1
            base = f"edge-{edge_counter}"
        candidate = base
        suffix = 2
        while candidate in occupied_ids:
            candidate = f"{base}-{suffix}"
            suffix += 1
        occupied_ids.add(candidate)
        return candidate

    for source, target, attributes, operator in parser.edges:
        expected_operator = "->" if parser.directed else "--"
        if operator != expected_operator:
            graph_kind = "digraph" if parser.directed else "graph"
            raise ValueError(
                f"DOT {graph_kind} edges must use {expected_operator!r}, "
                f"found {operator!r}"
            )
        direction = str(attributes.get("dir", "forward" if parser.directed else "none")).lower()
        arrow_start = direction in {"back", "both"}
        arrow_end = direction in {"forward", "both"}
        record: dict[str, Any] = {
            "id": allocate_edge_id(str(attributes.get("id", ""))),
            "type": "connector",
            "source": source[0],
            "target": target[0],
            "sourcePort": str(attributes.get("monkez_source_port", source[1])),
            "targetPort": str(attributes.get("monkez_target_port", target[1])),
            "arrowStart": arrow_start,
            "arrowEnd": arrow_end,
            "metadata": {"dotAttributes": dict(attributes), "dotOperator": operator},
        }
        if attributes.get("label"):
            record["label"] = attributes["label"]
        if attributes.get("color"):
            record["color"] = attributes["color"]
        if attributes.get("penwidth"):
            record["lineWidth"] = _dot_float(
                attributes["penwidth"], 2.0, minimum=0.5, maximum=50.0
            )
        style = str(attributes.get("style", "")).lower()
        if "dashed" in style:
            record["lineStyle"] = "dash"
        elif "dotted" in style:
            record["lineStyle"] = "dot"
        edge_records.append(record)

    element_records: list[dict[str, Any]] = []
    positioned: set[str] = set()
    for node_id, attributes in parser.nodes.items():
        width = _dot_float(
            attributes.get("width"),
            120.0 / 72.0,
            minimum=24.0 / 72.0,
            maximum=10_000.0 / 72.0,
        ) * 72.0
        height = _dot_float(
            attributes.get("height"),
            72.0 / 72.0,
            minimum=24.0 / 72.0,
            maximum=10_000.0 / 72.0,
        ) * 72.0
        position = _dot_position(str(attributes.get("pos", "")))
        record: dict[str, Any] = {
            "id": node_id,
            "type": _dot_element_type(attributes),
            "x": position[0] if position else 0.0,
            "y": position[1] if position else 0.0,
            "width": width,
            "height": height,
            "text": str(attributes.get("label", node_id)),
            "metadata": {"dotAttributes": dict(attributes)},
        }
        if position is not None:
            positioned.add(node_id)
        if attributes.get("color"):
            record["color"] = attributes["color"]
        if attributes.get("fillcolor") and attributes.get("fillcolor") != "#ffffff":
            record["background"] = attributes["fillcolor"]
        if attributes.get("fontcolor"):
            record["textColor"] = attributes["fontcolor"]
        element_records.append(record)

    if element_records and len(positioned) != len(element_records):
        direction = {
            "LR": "right",
            "RL": "left",
            "TB": "down",
            "BT": "up",
        }.get(str(parser.graph_attributes.get("rankdir", "LR")).upper(), "right")
        layout = layout_graph(
            [
                LayoutNode(
                    str(record["id"]),
                    float(record["x"]),
                    float(record["y"]),
                    float(record["width"]),
                    float(record["height"]),
                    str(record["id"]) in positioned,
                )
                for record in element_records
            ],
            [LayoutEdge(str(record["source"]), str(record["target"])) for record in edge_records],
            options=LayoutOptions(direction=direction, preserve_center=False),
        )
        for record in element_records:
            if str(record["id"]) not in positioned:
                record["x"], record["y"] = layout.positions[str(record["id"])]
        if positioned:
            warnings.append("Missing DOT positions were filled with deterministic layout")

    return DotImportResult(
        parser.name,
        parser.directed,
        tuple(element_records),
        tuple(edge_records),
        tuple(warnings),
    )
