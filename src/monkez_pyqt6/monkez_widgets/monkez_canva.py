"""Interactive canvas, chart and flow-diagram editor for Monkez applications."""

from __future__ import annotations

import json
import math
import os
import sys
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import (
    QByteArray,
    QEvent,
    QMimeData,
    QSignalBlocker,
    QStandardPaths,
    QEventLoop,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QMovie,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPixmap,
    QShortcut,
    QUndoStack,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from monkez_pyqt6.monkez_canva import (
    ASSET_MANIFEST_KEY,
    CanvasDocument,
    ElementDefinition,
    ElementRegistry,
    LayoutEdge,
    LayoutNode,
    LayoutOptions,
    LayoutResult,
    OperationEvent,
    PortCompatibility,
    PALETTE_FAVORITES_KEY,
    PALETTE_RECENT_KEY,
    PaletteEntry,
    CANVAS_CLIPBOARD_MIME_TYPE,
    atomic_write_json,
    backup_path,
    build_asset_manifest,
    build_selection_payload,
    create_default_element_registry,
    load_json_with_recovery,
    layout_graph,
    normalize_component_ids,
    record_recent_component,
    search_palette,
    decode_selection_payload,
    remap_selection_payload,
    verify_asset_manifest,
    SMART_GUIDES_KEY,
    SNAP_DISTANCE_KEY,
    SNAP_TARGETS,
    SNAP_TARGETS_KEY,
    SnapRect,
    normalize_snap_targets,
    snap_rect,
    deduplicate_points,
    descendant_element_ids,
    group_bounds,
    normalize_group_kind,
    orthogonal_points,
    obstacle_avoiding_route,
    evaluate_directed_ports,
    evaluate_port_pair,
    normalize_port_record,
    validate_port_value,
    parallel_lane_offset,
    segment_intersection,
)
from monkez_pyqt6.monkez_canva.persistence import copy_asset_atomically
from monkez_pyqt6.monkez_widgets._canva_commands import (
    CanvasDocumentCommand,
    CanvasRenameCommand,
    patches_from_documents,
)
from monkez_pyqt6.monkez_widgets._canva_animation import (
    CanvasAnimationScheduler,
    ScheduledPropertyAnimation,
)
from monkez_pyqt6.monkez_widgets._canva_minimap import CanvasMinimap


_GRID_STYLES = ("lines", "dots", "cross")
_BACKGROUND_IMAGE_MODES = ("fit", "fill", "scale")
_LINE_EFFECTS = ("flow", "pulse", "glow", "particles", "packet")
_PORT_KINDS = ("node", "splitter")
_VIEWPORT_BOOKMARKS_KEY = "viewportBookmarks"
_MINIMAP_VISIBLE_KEY = "minimapVisible"
_ELEMENT_STANDARD_PROPERTIES = {
    "id", "type", "x", "y", "width", "height", "text", "color", "background",
    "textColor", "data", "metadata", "source", "lineWidth", "lineStyle",
    "arrowStart", "arrowEnd", "animated", "animationEffect", "flowColor",
    "flowSpeed", "flowDirection", "flowSpacing", "effectIntensity", "packetLoop",
    "packetDuration", "packetInterval", "packetIcon", "points", "ports", "opacity",
    "rotation", "z", "locked", "hidden",
}
_GROUP_STANDARD_PROPERTIES = {
    "id", "members", "kind", "label", "text", "x", "y", "width", "height",
    "color", "background", "headerColor", "padding", "collapsed", "lanes",
    "orientation", "opacity", "rotation", "z", "locked", "hidden",
}


def _normalize_node_ports(raw_ports: Any) -> list[dict[str, Any]]:
    """Return a stable, JSON-safe port schema for a node."""
    if raw_ports is None:
        raw_ports = (
            {"id": "in", "mode": "input", "side": "left", "label": "Input"},
            {"id": "out", "mode": "output", "side": "right", "label": "Output"},
        )
    if not isinstance(raw_ports, (list, tuple)):
        raise TypeError("Node ports must be a list of dictionaries")
    ports: list[dict[str, Any]] = []
    used: set[str] = set()
    for index, raw in enumerate(raw_ports):
        if not isinstance(raw, dict):
            raise TypeError("Each node port must be a dictionary")
        port = normalize_port_record(raw, index)
        port_id = port["id"]
        if not port_id or port_id in used:
            raise ValueError(f"Node port ID must be unique and non-empty: {port_id!r}")
        used.add(port_id)
        ports.append(port)
    return ports


def _splitter_ports(output_count: int = 3) -> list[dict[str, Any]]:
    output_count = max(2, min(12, int(output_count)))
    ports = [{"id": "in", "mode": "input", "side": "left", "label": "In", "position": 0.5}]
    ports.extend(
        {
            "id": f"out-{index + 1}", "mode": "output", "side": "right",
            "label": str(index + 1), "position": (index + 1) / (output_count + 1),
        }
        for index in range(output_count)
    )
    return ports


def _color(value: Any, fallback: str = "#2563eb") -> QColor:
    result = QColor(value)
    return result if result.isValid() else QColor(fallback)


def _paint_path_effect(
    painter: QPainter,
    path: QPainterPath,
    effect: str,
    color: QColor,
    width: float,
    phase: float,
    spacing: float,
    intensity: float,
) -> None:
    """Paint one animated overlay shared by standalone lines and connectors."""
    painter.save()
    effect = effect if effect in _LINE_EFFECTS else "flow"
    width = max(1.0, float(width))
    spacing = max(1.0, float(spacing))
    intensity = max(0.2, min(4.0, float(intensity)))
    if effect == "packet":
        painter.restore()
        return
    if effect == "pulse":
        pulse = (math.sin(phase * 0.16) + 1.0) / 2.0
        pulse_color = QColor(color)
        pulse_color.setAlphaF(min(1.0, 0.35 + pulse * 0.55))
        pen = QPen(pulse_color, width * (0.75 + pulse * 0.75 * intensity))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
    elif effect == "glow":
        for multiplier, alpha in ((4.0, 28), (2.5, 55), (1.35, 115)):
            glow = QColor(color)
            glow.setAlpha(min(220, int(alpha * intensity)))
            pen = QPen(glow, width * multiplier * intensity)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)
        core = QPen(color, max(1.0, width * 0.65))
        core.setDashPattern([1.0, spacing])
        core.setDashOffset(phase)
        core.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(core)
        painter.drawPath(path)
    elif effect == "particles":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        count = max(3, min(24, int(5 + intensity * 3)))
        radius = max(1.8, width * (0.55 + intensity * 0.16))
        offset = (phase * 0.012) % 1.0
        for index in range(count):
            progress = (index / count + offset) % 1.0
            painter.drawEllipse(path.pointAtPercent(progress), radius, radius)
    else:
        pen = QPen(color, max(1.5, width * 0.7 * intensity))
        pen.setDashPattern([2.0, spacing])
        pen.setDashOffset(phase)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)
    painter.restore()


def _packet_pixmap(icon: Any, size: int = 20) -> QPixmap:
    if isinstance(icon, QPixmap):
        return icon.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    if isinstance(icon, QIcon):
        return icon.pixmap(size, size)
    if icon:
        pixmap = QPixmap(str(icon))
        if not pixmap.isNull():
            return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return QPixmap()


def _paint_packets(painter: QPainter, path: QPainterPath, packets: list[dict[str, Any]]) -> None:
    """Render in-flight message packets; an envelope is used without a custom icon."""
    now = time.monotonic()
    for packet in packets:
        progress = max(0.0, min(1.0, (now - packet["started"]) / packet["duration"]))
        point = path.pointAtPercent(progress)
        pixmap = packet.get("pixmap")
        if not isinstance(pixmap, QPixmap):
            pixmap = QPixmap()
        painter.save()
        painter.translate(point)
        painter.setPen(QPen(QColor("#ffffff"), 1.4))
        painter.setBrush(QColor("#2563eb"))
        painter.drawEllipse(QRectF(-14, -14, 28, 28))
        if not pixmap.isNull():
            painter.drawPixmap(-10, -10, pixmap)
        else:
            painter.setPen(QPen(QColor("#ffffff"), 1.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(-8, -6, 16, 12), 2, 2)
            painter.drawLine(QPointF(-8, -5), QPointF(0, 1))
            painter.drawLine(QPointF(8, -5), QPointF(0, 1))
        painter.restore()


def _canvas_icon(name: str, color: str = "#475569") -> QIcon:
    """Create small dependency-free vector icons with one coherent stroke style."""
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "save":
        painter.drawRoundedRect(QRectF(3, 2.5, 14, 15), 2, 2)
        painter.drawRect(QRectF(6, 2.5, 7, 5))
        painter.drawRoundedRect(QRectF(6, 11, 8, 6.5), 1, 1)
    elif name == "add":
        painter.drawLine(QPointF(10, 3), QPointF(10, 17))
        painter.drawLine(QPointF(3, 10), QPointF(17, 10))
    elif name == "lock":
        painter.drawRoundedRect(QRectF(4, 8, 12, 9), 2, 2)
        painter.drawArc(QRectF(6, 2.5, 8, 11), 0, 180 * 16)
    elif name in ("eye", "eye_off"):
        eye = QPainterPath(QPointF(2, 10))
        eye.cubicTo(6, 4, 14, 4, 18, 10)
        eye.cubicTo(14, 16, 6, 16, 2, 10)
        painter.drawPath(eye)
        painter.drawEllipse(QRectF(8, 8, 4, 4))
        if name == "eye_off":
            painter.drawLine(QPointF(3, 3), QPointF(17, 17))
    elif name == "focus":
        painter.drawEllipse(QRectF(6, 6, 8, 8))
        for start, end in (
            ((3, 7), (3, 3)), ((3, 3), (7, 3)), ((13, 3), (17, 3)),
            ((17, 3), (17, 7)), ((3, 13), (3, 17)), ((3, 17), (7, 17)),
            ((13, 17), (17, 17)), ((17, 17), (17, 13)),
        ):
            painter.drawLine(QPointF(*start), QPointF(*end))
        painter.drawEllipse(QRectF(9, 11, 2, 2))
    elif name in ("zoom_in", "zoom_out"):
        painter.drawEllipse(QRectF(3, 3, 10, 10))
        painter.drawLine(QPointF(12, 12), QPointF(17, 17))
        painter.drawLine(QPointF(6, 8), QPointF(10, 8))
        if name == "zoom_in":
            painter.drawLine(QPointF(8, 6), QPointF(8, 10))
    elif name == "actual_size":
        font = QFont(painter.font())
        font.setPixelSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(1, 4, 18, 12), Qt.AlignmentFlag.AlignCenter, "1:1")
    elif name == "fit":
        for x1, y1, x2, y2, x3, y3 in (
            (3, 7, 3, 3, 7, 3), (13, 3, 17, 3, 17, 7),
            (3, 13, 3, 17, 7, 17), (13, 17, 17, 17, 17, 13),
        ):
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            painter.drawLine(QPointF(x2, y2), QPointF(x3, y3))
    elif name.startswith("align_"):
        edge = name.removeprefix("align_")
        if edge == "center":
            painter.drawLine(QPointF(10, 2), QPointF(10, 18))
            painter.drawLine(QPointF(2, 10), QPointF(18, 10))
            painter.drawRect(QRectF(5, 6, 10, 8))
        elif edge in ("left", "right", "hcenter"):
            anchor = 3 if edge == "left" else 17 if edge == "right" else 10
            painter.drawLine(QPointF(anchor, 2), QPointF(anchor, 18))
            offsets = ((4, 9), (7, 13), (5, 11))
            for row, (start, end) in enumerate(offsets):
                y = 4 + row * 5
                if edge == "left":
                    painter.drawLine(QPointF(anchor, y), QPointF(end, y))
                elif edge == "right":
                    painter.drawLine(QPointF(start, y), QPointF(anchor, y))
                else:
                    width = end - start
                    painter.drawLine(QPointF(anchor - width / 2, y), QPointF(anchor + width / 2, y))
        else:
            anchor = 3 if edge == "top" else 17 if edge == "bottom" else 10
            painter.drawLine(QPointF(2, anchor), QPointF(18, anchor))
            offsets = ((4, 9), (7, 13), (5, 11))
            for column, (start, end) in enumerate(offsets):
                x = 4 + column * 5
                if edge == "top":
                    painter.drawLine(QPointF(x, anchor), QPointF(x, end))
                elif edge == "bottom":
                    painter.drawLine(QPointF(x, start), QPointF(x, anchor))
                else:
                    height = end - start
                    painter.drawLine(QPointF(x, anchor - height / 2), QPointF(x, anchor + height / 2))
    elif name.startswith("distribute_"):
        direction = name.removeprefix("distribute_")
        if direction == "horizontal":
            painter.drawLine(QPointF(3, 3), QPointF(3, 17))
            painter.drawLine(QPointF(17, 3), QPointF(17, 17))
            for x in (6, 10, 14):
                painter.drawRoundedRect(QRectF(x - 1, 7, 2, 6), 0.5, 0.5)
        else:
            painter.drawLine(QPointF(3, 3), QPointF(17, 3))
            painter.drawLine(QPointF(3, 17), QPointF(17, 17))
            for y in (6, 10, 14):
                painter.drawRoundedRect(QRectF(7, y - 1, 6, 2), 0.5, 0.5)
    elif name in ("rectangle", "button"):
        painter.drawRoundedRect(QRectF(3, 5, 14, 10), 2.5 if name == "button" else 1, 2.5 if name == "button" else 1)
    elif name == "ellipse":
        painter.drawEllipse(QRectF(3, 5, 14, 10))
    elif name in ("diamond", "triangle", "arrow"):
        if name == "diamond":
            path = QPainterPath(QPointF(10, 2.5))
            path.lineTo(17, 10)
            path.lineTo(10, 17.5)
            path.lineTo(3, 10)
        elif name == "triangle":
            path = QPainterPath(QPointF(10, 3))
            path.lineTo(17, 16)
            path.lineTo(3, 16)
        else:
            path = QPainterPath(QPointF(2, 7))
            path.lineTo(12, 7)
            path.lineTo(12, 3)
            path.lineTo(18, 10)
            path.lineTo(12, 17)
            path.lineTo(12, 13)
            path.lineTo(2, 13)
        path.closeSubpath()
        painter.drawPath(path)
    elif name in ("line", "polyline", "connector"):
        path = QPainterPath(QPointF(2, 15 if name == "polyline" else 10))
        if name == "polyline":
            path.lineTo(7, 5)
            path.lineTo(12, 14)
        elif name == "connector":
            path.cubicTo(7, 2, 13, 18, 18, 10)
        else:
            path.lineTo(18, 10)
        if name == "polyline":
            path.lineTo(18, 5)
        painter.drawPath(path)
    elif name == "text":
        painter.drawLine(QPointF(4, 4), QPointF(16, 4))
        painter.drawLine(QPointF(10, 4), QPointF(10, 17))
        painter.drawLine(QPointF(7, 17), QPointF(13, 17))
    elif name in ("bar_chart", "line_chart"):
        painter.drawLine(QPointF(3, 3), QPointF(3, 17))
        painter.drawLine(QPointF(3, 17), QPointF(18, 17))
        if name == "bar_chart":
            painter.drawRect(QRectF(6, 10, 2.5, 7))
            painter.drawRect(QRectF(11, 6, 2.5, 11))
            painter.drawRect(QRectF(16, 8, 2, 9))
        else:
            path = QPainterPath(QPointF(5, 14))
            path.lineTo(9, 8)
            path.lineTo(13, 11)
            path.lineTo(17, 5)
            painter.drawPath(path)
    elif name == "node":
        painter.drawRoundedRect(QRectF(4, 5, 12, 10), 2, 2)
        painter.drawEllipse(QRectF(1.5, 8.5, 3, 3))
        painter.drawEllipse(QRectF(15.5, 8.5, 3, 3))
    elif name == "splitter":
        painter.drawEllipse(QRectF(3, 3, 14, 14))
        painter.drawLine(QPointF(3, 10), QPointF(9, 10))
        painter.drawLine(QPointF(9, 10), QPointF(16, 6))
        painter.drawLine(QPointF(9, 10), QPointF(16, 14))
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(7.5, 8.5, 3, 3))
    elif name == "send":
        painter.drawRoundedRect(QRectF(2, 5, 16, 11), 2, 2)
        painter.drawLine(QPointF(2, 6), QPointF(10, 12))
        painter.drawLine(QPointF(18, 6), QPointF(10, 12))
    elif name in ("image", "gif"):
        painter.drawRoundedRect(QRectF(3, 4, 14, 12), 2, 2)
        painter.drawEllipse(QRectF(11.5, 6, 2.5, 2.5))
        path = QPainterPath(QPointF(5, 14))
        path.lineTo(8.5, 10)
        path.lineTo(11, 12.5)
        path.lineTo(14, 9.5)
        path.lineTo(17, 13)
        painter.drawPath(path)
        if name == "gif":
            painter.setBrush(QColor(color))
            play = QPainterPath(QPointF(8, 7))
            play.lineTo(8, 13)
            play.lineTo(13, 10)
            play.closeSubpath()
            painter.drawPath(play)
    elif name == "delete":
        painter.drawLine(QPointF(5, 6), QPointF(15, 6))
        painter.drawLine(QPointF(8, 3.5), QPointF(12, 3.5))
        painter.drawRoundedRect(QRectF(6, 6, 8, 11), 1, 1)
        painter.drawLine(QPointF(9, 9), QPointF(9, 14))
        painter.drawLine(QPointF(11.5, 9), QPointF(11.5, 14))
    elif name == "duplicate":
        painter.drawRoundedRect(QRectF(6, 3, 11, 11), 1, 1)
        painter.drawRoundedRect(QRectF(3, 6, 11, 11), 1, 1)
    elif name in ("undo", "redo"):
        if name == "undo":
            painter.drawLine(QPointF(8, 5), QPointF(4, 9))
            painter.drawLine(QPointF(4, 9), QPointF(8, 13))
            path = QPainterPath(QPointF(4, 9))
            path.cubicTo(15, 5, 17, 10, 15, 15)
        else:
            painter.drawLine(QPointF(12, 5), QPointF(16, 9))
            painter.drawLine(QPointF(16, 9), QPointF(12, 13))
            path = QPainterPath(QPointF(16, 9))
            path.cubicTo(5, 5, 3, 10, 5, 15)
        painter.drawPath(path)
    elif name == "folder":
        painter.drawRoundedRect(QRectF(2.5, 6, 15, 10), 2, 2)
        painter.drawLine(QPointF(3, 6), QPointF(7, 6))
        painter.drawLine(QPointF(7, 6), QPointF(8.5, 4))
        painter.drawLine(QPointF(8.5, 4), QPointF(13, 4))
    elif name == "check":
        painter.drawLine(QPointF(4, 10), QPointF(8, 14))
        painter.drawLine(QPointF(8, 14), QPointF(16, 5))
    elif name == "refresh":
        path = QPainterPath(QPointF(15, 7))
        path.cubicTo(11, 2, 4, 5, 4, 10)
        path.cubicTo(4, 16, 12, 18, 16, 13)
        painter.drawPath(path)
        painter.drawLine(QPointF(15, 7), QPointF(11, 7))
        painter.drawLine(QPointF(15, 7), QPointF(15, 3))
    elif name in ("front", "back"):
        painter.drawRect(QRectF(6, 4, 10, 10))
        painter.drawRect(QRectF(3, 7, 10, 10))
        painter.drawLine(QPointF(14, 16), QPointF(17, 13 if name == "front" else 17))
    elif name == "color":
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(4, 4, 12, 12))
    elif name == "pan":
        painter.drawLine(QPointF(10, 2), QPointF(10, 18))
        painter.drawLine(QPointF(2, 10), QPointF(18, 10))
        painter.drawLine(QPointF(10, 2), QPointF(7.5, 5))
        painter.drawLine(QPointF(10, 2), QPointF(12.5, 5))
        painter.drawLine(QPointF(18, 10), QPointF(15, 7.5))
        painter.drawLine(QPointF(18, 10), QPointF(15, 12.5))
    elif name.startswith("arrow_"):
        direction = name.removeprefix("arrow_")
        if direction in ("left", "right"):
            start, end = (16, 4) if direction == "left" else (4, 16)
            painter.drawLine(QPointF(start, 10), QPointF(end, 10))
            tip = end
            wing = 4 if direction == "left" else -4
            painter.drawLine(QPointF(tip, 10), QPointF(tip + wing, 6))
            painter.drawLine(QPointF(tip, 10), QPointF(tip + wing, 14))
        else:
            start, end = (16, 4) if direction == "up" else (4, 16)
            painter.drawLine(QPointF(10, start), QPointF(10, end))
            tip = end
            wing = 4 if direction == "up" else -4
            painter.drawLine(QPointF(10, tip), QPointF(6, tip + wing))
            painter.drawLine(QPointF(10, tip), QPointF(14, tip + wing))
    elif name == "close":
        painter.drawLine(QPointF(5, 5), QPointF(15, 15))
        painter.drawLine(QPointF(15, 5), QPointF(5, 15))
    elif name == "grid":
        for x in (4, 10, 16):
            painter.drawLine(QPointF(x, 3), QPointF(x, 17))
        for y in (4, 10, 16):
            painter.drawLine(QPointF(3, y), QPointF(17, y))
    elif name == "search":
        painter.drawEllipse(QRectF(3, 3, 10, 10))
        painter.drawLine(QPointF(12, 12), QPointF(17, 17))
    elif name in ("star", "star_filled"):
        path = QPainterPath(QPointF(10, 2.5))
        for index in range(1, 10):
            angle = -math.pi / 2 + index * math.pi / 5
            radius = 7.2 if index % 2 == 0 else 3.2
            path.lineTo(QPointF(10 + math.cos(angle) * radius, 10 + math.sin(angle) * radius))
        path.closeSubpath()
        if name == "star_filled":
            painter.setBrush(QColor(color))
        painter.drawPath(path)
    elif name == "command":
        painter.drawRoundedRect(QRectF(3, 3, 14, 14), 4, 4)
        painter.drawLine(QPointF(7, 7), QPointF(10, 10))
        painter.drawLine(QPointF(10, 10), QPointF(7, 13))
        painter.drawLine(QPointF(11.5, 13), QPointF(14, 13))
    elif name == "background":
        painter.drawRoundedRect(QRectF(2.5, 3.5, 15, 13), 2, 2)
        painter.drawEllipse(QRectF(12, 6, 2.5, 2.5))
        painter.drawLine(QPointF(4, 14), QPointF(8, 9))
        painter.drawLine(QPointF(8, 9), QPointF(11, 12))
        painter.drawLine(QPointF(11, 12), QPointF(14, 10))
        painter.drawLine(QPointF(14, 10), QPointF(17, 14))

    painter.end()
    return QIcon(pixmap)


class _CanvasScene(QGraphicsScene):
    def __init__(self, canvas: "MonkezCanva") -> None:
        super().__init__(canvas)
        self.canvas = canvas
        self._smart_guides: tuple[Any, ...] = ()

    def setSmartGuides(self, guides) -> None:
        normalized = tuple(guides) if self.canvas._smart_guides_visible else ()
        if normalized != self._smart_guides:
            self._smart_guides = normalized
            self.invalidate(self.sceneRect(), QGraphicsScene.SceneLayer.ForegroundLayer)

    def clearSmartGuides(self) -> None:
        self.setSmartGuides(())

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        if not self._smart_guides:
            return
        painter.save()
        pen = QPen(QColor("#ff6b5f"), 0, Qt.PenStyle.DashLine)
        pen.setDashPattern((5, 4))
        painter.setPen(pen)
        for guide in self._smart_guides:
            if guide.axis == "vertical":
                painter.drawLine(QPointF(guide.value, rect.top()), QPointF(guide.value, rect.bottom()))
            else:
                painter.drawLine(QPointF(rect.left(), guide.value), QPointF(rect.right(), guide.value))
        painter.restore()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, self.canvas.backgroundColor)
        pixmap = self.canvas._background_pixmap
        if not pixmap.isNull():
            scene_rect = self.sceneRect()
            source = QRectF(pixmap.rect())
            if self.canvas._background_image_mode == 2:
                target = scene_rect
            else:
                x_scale = scene_rect.width() / max(1, pixmap.width())
                y_scale = scene_rect.height() / max(1, pixmap.height())
                factor = min(x_scale, y_scale) if self.canvas._background_image_mode == 0 else max(x_scale, y_scale)
                width = pixmap.width() * factor
                height = pixmap.height() * factor
                target = QRectF(
                    scene_rect.center().x() - width / 2,
                    scene_rect.center().y() - height / 2,
                    width,
                    height,
                )
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(target, pixmap, source)
            painter.restore()
        if not self.canvas.gridVisible:
            return
        size = self.canvas.gridSize
        left = math.floor(rect.left() / size) * size
        top = math.floor(rect.top() / size) * size
        minor = QColor(self.canvas.gridColor)
        pen = QPen(minor, 0)
        if self.canvas._grid_style in (1, 2):
            pen.setWidthF(1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        if self.canvas._grid_style == 1:
            x = left
            while x <= rect.right():
                y = top
                while y <= rect.bottom():
                    painter.drawPoint(QPointF(x, y))
                    y += size
                x += size
            return
        if self.canvas._grid_style == 2:
            arm = min(3.0, size * 0.18)
            x = left
            while x <= rect.right():
                y = top
                while y <= rect.bottom():
                    painter.drawLine(QPointF(x - arm, y), QPointF(x + arm, y))
                    painter.drawLine(QPointF(x, y - arm), QPointF(x, y + arm))
                    y += size
                x += size
            return
        x = left
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += size
        y = top
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += size


class _CanvasElement(QGraphicsObject):
    changed = pyqtSignal(str)
    packetArrived = pyqtSignal(str, str)

    def __init__(
        self,
        canvas: "MonkezCanva",
        element_id: str,
        kind: str,
        width: float,
        height: float,
        options: dict[str, Any] | None = None,
        definition: ElementDefinition | None = None,
    ) -> None:
        super().__init__()
        options = dict(options or {})
        self.canvas = canvas
        self.element_id = element_id
        self.kind = kind
        self.definition = definition
        self._rect = QRectF(0, 0, max(24.0, width), max(24.0, height))
        self.text = str(options.get("text", kind.replace("_", " ").title()))
        self.color = _color(options.get("color", "#2563eb"))
        self.background = _color(options.get("background", "#ffffff"), "#ffffff")
        self.text_color = _color(options.get("textColor", "#0f172a"), "#0f172a")
        self.data = list(options.get("data", [32, 68, 46, 82, 58]))
        self.metadata = dict(options.get("metadata", {}))
        self.locked = bool(options.get("locked", False))
        self.hidden = bool(options.get("hidden", False))
        self.custom_properties = {
            key: value for key, value in options.items()
            if key not in _ELEMENT_STANDARD_PROPERTIES
        }
        self._renderer_error = ""
        self.source = str(options.get("source", ""))
        self.line_width = max(0.5, float(options.get("lineWidth", 2.2)))
        self.line_style = str(options.get("lineStyle", "solid")).lower()
        self.arrow_start = bool(options.get("arrowStart", False))
        self.arrow_end = bool(options.get("arrowEnd", False))
        self.animated = bool(options.get("animated", False))
        self.animation_effect = str(options.get("animationEffect", "flow")).lower()
        self.flow_color = _color(options.get("flowColor", "#38bdf8"), "#38bdf8")
        self.flow_speed = max(0.1, float(options.get("flowSpeed", 1.0)))
        self.flow_direction = -1 if str(options.get("flowDirection", "forward")).lower() == "reverse" else 1
        self.flow_spacing = max(1.0, float(options.get("flowSpacing", 5.0)))
        self.effect_intensity = max(0.2, min(4.0, float(options.get("effectIntensity", 1.0))))
        self.packet_loop = bool(options.get("packetLoop", False))
        self.packet_duration = max(0.1, float(options.get("packetDuration", 1.5)))
        self.packet_interval = max(0.05, float(options.get("packetInterval", 0.7)))
        self.packet_icon = str(options.get("packetIcon", ""))
        self._packets: list[dict[str, Any]] = []
        self._last_packet_at = 0.0
        raw_points = options.get("points", [])
        self.points = [QPointF(float(point[0]), float(point[1])) for point in raw_points]
        self.supports_ports = kind in _PORT_KINDS or bool(
            definition is not None and "ports" in definition.capabilities
        )
        self.ports = _normalize_node_ports(options.get("ports")) if self.supports_ports else []
        self._pixmap = QPixmap()
        self._movie: QMovie | None = None
        self._highlight = QColor()
        self._port_feedback: dict[str, tuple[str, str]] = {}
        self._resizing = False
        self._resize_origin = QPointF()
        self._line_phase = 0.0
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setOpacity(max(0.0, min(1.0, float(options.get("opacity", 1.0)))))
        self.setRotation(float(options.get("rotation", 0.0)))
        self.setZValue(float(options.get("z", 0.0)))
        self._load_media()
        self._sync_line_animation()

    def _load_media(self) -> None:
        self.releaseMedia()
        self._pixmap = QPixmap()
        if not self.source:
            return
        if self.kind == "animated_image":
            movie = QMovie(self.source)
            if movie.isValid():
                movie.frameChanged.connect(self.update)
                movie.start()
                self._movie = movie
        elif self.kind == "image":
            self._pixmap = QPixmap(self.source)

    def releaseMedia(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.setFileName("")
            self._movie.deleteLater()
            self._movie = None
        self._pixmap = QPixmap()

    def release(self) -> None:
        self.canvas._animation_scheduler.unregister(self)
        self.releaseMedia()

    def setSource(self, source: str) -> None:
        self.source = str(source)
        self._load_media()
        self.update()
        self.changed.emit(self.element_id)

    def boundingRect(self) -> QRectF:
        margin = 11 if self.supports_ports else 5
        return self._rect.adjusted(-margin, -margin, margin, margin)

    def port(self, port_id: str) -> dict[str, Any] | None:
        return next((port for port in self.ports if port["id"] == str(port_id)), None)

    def portLocalPosition(self, port_id: str | None, endpoint: str = "source") -> QPointF:
        port = self.port(port_id) if port_id else None
        if port is None:
            return QPointF(self._rect.right(), self._rect.center().y()) if endpoint == "source" else QPointF(
                self._rect.left(), self._rect.center().y()
            )
        side = port["side"]
        siblings = [candidate for candidate in self.ports if candidate["side"] == side]
        index = siblings.index(port)
        ratio = float(port.get("position", (index + 1) / (len(siblings) + 1)))
        if side == "left":
            body_top = self._rect.top() + min(38.0, self._rect.height() * 0.4)
            body_height = max(12.0, self._rect.bottom() - body_top - 6.0)
            return QPointF(self._rect.left(), body_top + body_height * ratio)
        if side == "right":
            body_top = self._rect.top() + min(38.0, self._rect.height() * 0.4)
            body_height = max(12.0, self._rect.bottom() - body_top - 6.0)
            return QPointF(self._rect.right(), body_top + body_height * ratio)
        if side == "top":
            return QPointF(self._rect.left() + self._rect.width() * ratio, self._rect.top())
        return QPointF(self._rect.left() + self._rect.width() * ratio, self._rect.bottom())

    def portScenePosition(self, port_id: str | None, endpoint: str = "source") -> QPointF:
        return self.mapToScene(self.portLocalPosition(port_id, endpoint))

    def portAt(self, scene_position: QPointF, radius: float = 11.0) -> dict[str, Any] | None:
        if not self.supports_ports:
            return None
        local = self.mapFromScene(scene_position)
        for port in self.ports:
            if (local - self.portLocalPosition(port["id"])).manhattanLength() <= radius:
                return port
        return None

    def setEditable(self, enabled: bool) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, enabled)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, enabled)
        if not enabled:
            self.setSelected(False)
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self._rect.adjusted(2, 2, -2, -2)
        outline = self._highlight if self._highlight.isValid() else self.color
        painter.setPen(QPen(outline, 2.0))
        painter.setBrush(self.background)

        if self.definition is not None and self.definition.renderer_factory is not None:
            try:
                self.definition.renderer_factory(painter, self, rect, option, widget)
                self._renderer_error = ""
            except Exception as error:  # plugin boundary: paint must never escape into Qt
                message = f"Renderer {self.kind!r} failed: {error}"
                if message != self._renderer_error and self.scene() is not None:
                    self.scene().canvas.diagnosticMessage.emit(message)
                self._renderer_error = message
                painter.setPen(QPen(QColor("#dc2626"), 2.0))
                painter.setBrush(QColor("#fef2f2"))
                painter.drawRoundedRect(rect, 8, 8)
                painter.setPen(QColor("#991b1b"))
                painter.drawText(
                    rect.adjusted(8, 8, -8, -8),
                    Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                    f"Renderer error\n{self.kind}",
                )
            return

        if self.kind in ("image", "animated_image"):
            self._paint_media(painter, rect)
        elif self.kind == "line":
            self._paint_line(painter, rect)
        elif self.kind == "diamond":
            path = QPainterPath(rect.topLeft() + QPointF(rect.width() / 2, 0))
            path.lineTo(rect.center() + QPointF(rect.width() / 2, 0))
            path.lineTo(rect.bottomLeft() + QPointF(rect.width() / 2, 0))
            path.lineTo(rect.center() - QPointF(rect.width() / 2, 0))
            path.closeSubpath()
            painter.drawPath(path)
            self._paint_centered_text(painter, rect)
        elif self.kind == "triangle":
            path = QPainterPath(rect.topLeft() + QPointF(rect.width() / 2, 0))
            path.lineTo(rect.bottomRight())
            path.lineTo(rect.bottomLeft())
            path.closeSubpath()
            painter.drawPath(path)
            self._paint_centered_text(painter, rect.adjusted(12, 24, -12, -6))
        elif self.kind == "ellipse":
            painter.drawEllipse(rect)
            self._paint_centered_text(painter, rect.adjusted(10, 6, -10, -6))
        elif self.kind in ("bar_chart", "line_chart"):
            painter.drawRoundedRect(rect, 10, 10)
            self._paint_chart(painter, rect)
        elif self.kind == "node":
            painter.drawRoundedRect(rect, 12, 12)
            header = QRectF(rect.left(), rect.top(), rect.width(), 32)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.color)
            painter.drawRoundedRect(header, 10, 10)
            painter.fillRect(QRectF(header.left(), header.bottom() - 10, header.width(), 10), self.color)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(header.adjusted(12, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter, self.text)
            self._paint_ports(painter)
        elif self.kind == "splitter":
            painter.setBrush(QColor("#eff6ff"))
            painter.setPen(QPen(self.color, 2.2))
            painter.drawEllipse(rect)
            center = rect.center()
            painter.drawLine(QPointF(rect.left() + 10, center.y()), center)
            painter.drawLine(center, QPointF(rect.right() - 10, rect.top() + 17))
            painter.drawLine(center, QPointF(rect.right() - 10, rect.bottom() - 17))
            painter.setBrush(self.color)
            painter.drawEllipse(center, 4, 4)
            self._paint_ports(painter)
        else:
            radius = 10 if self.kind in ("button", "rectangle") else 4
            painter.drawRoundedRect(rect, radius, radius)
            painter.setPen(self.text_color)
            font = QFont(painter.font())
            font.setBold(self.kind == "button")
            font.setPointSize(12 if self.kind == "text" else 10)
            painter.setFont(font)
            painter.drawText(rect.adjusted(10, 6, -10, -6), Qt.AlignmentFlag.AlignCenter, self.text)

        if self.isSelected():
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(QPen(QColor("#2563eb"), 1.5))
            for point in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
                painter.drawRect(QRectF(point.x() - 4, point.y() - 4, 8, 8))

    def _paint_centered_text(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(self.text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.text)

    def _paint_ports(self, painter: QPainter) -> None:
        colors = {"input": QColor("#f59e0b"), "output": QColor("#0ea5e9"), "free": QColor("#22c55e")}
        painter.setFont(QFont(painter.font().family(), 7))
        for port in self.ports:
            point = self.portLocalPosition(port["id"])
            mode = port["mode"]
            color = colors[mode]
            feedback = self._port_feedback.get(port["id"])
            if feedback is not None:
                feedback_color = {
                    "origin": QColor("#2563eb"),
                    "compatible": QColor("#10b981"),
                    "conversion": QColor("#8b5cf6"),
                    "incompatible": QColor("#ef4444"),
                }.get(feedback[0], QColor("#64748b"))
                halo = QColor(feedback_color)
                halo.setAlpha(45)
                painter.setPen(QPen(feedback_color, 2.0))
                painter.setBrush(halo)
                painter.drawEllipse(point, 10.0, 10.0)
            painter.setPen(QPen(QColor("#ffffff"), 1.8))
            painter.setBrush(color)
            if mode in ("input", "output"):
                painter.drawPath(self._port_marker_path(port, point))
            else:
                path = QPainterPath(QPointF(point.x(), point.y() - 7))
                path.lineTo(QPointF(point.x() + 7, point.y()))
                path.lineTo(QPointF(point.x(), point.y() + 7))
                path.lineTo(QPointF(point.x() - 7, point.y()))
                path.closeSubpath()
                painter.drawPath(path)

            runtime_key = (self.element_id, port["id"])
            if runtime_key in self.canvas._port_runtime_values:
                painter.setPen(QPen(QColor("#ffffff"), 1.0))
                painter.setBrush(QColor("#0f9f8f"))
                painter.drawEllipse(point, 2.7, 2.7)

            label = port.get("label", "")
            if not label:
                continue
            painter.setPen(self.text_color)
            side = port["side"]
            if side == "left":
                label_rect = QRectF(point.x() + 9, point.y() - 8, 72, 16)
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            elif side == "right":
                label_rect = QRectF(point.x() - 81, point.y() - 8, 72, 16)
                alignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            elif side == "top":
                label_rect = QRectF(point.x() - 36, point.y() + 7, 72, 16)
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            else:
                label_rect = QRectF(point.x() - 36, point.y() - 23, 72, 16)
                alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
            painter.drawText(label_rect, alignment, label)
            data_type = str(port.get("dataType", "any"))
            if data_type != "any" and (self.isSelected() or feedback is not None):
                painter.setPen(QColor("#64748b"))
                type_rect = QRectF(label_rect)
                type_rect.translate(0, 10 if side in ("left", "right", "top") else -10)
                painter.drawText(type_rect, alignment, data_type)

    def setPortFeedback(self, feedback: dict[str, tuple[str, str]]) -> None:
        if feedback != self._port_feedback:
            self._port_feedback = dict(feedback)
            self.update()

    def clearPortFeedback(self) -> None:
        self.setPortFeedback({})

    @staticmethod
    def _port_triangle_path(point: QPointF, side: str) -> QPainterPath:
        if side == "right":
            vertices = (
                point + QPointF(6, -6), point + QPointF(-6, 0), point + QPointF(6, 6),
            )
        elif side == "top":
            vertices = (
                point + QPointF(-6, -6), point + QPointF(0, 6), point + QPointF(6, -6),
            )
        elif side == "bottom":
            vertices = (
                point + QPointF(-6, 6), point + QPointF(0, -6), point + QPointF(6, 6),
            )
        else:
            vertices = (
                point + QPointF(-6, -6), point + QPointF(6, 0), point + QPointF(-6, 6),
            )
        path = QPainterPath(vertices[0])
        path.lineTo(vertices[1])
        path.lineTo(vertices[2])
        path.closeSubpath()
        return path

    def _port_marker_path(self, port: dict[str, Any], point: QPointF | None = None) -> QPainterPath:
        point = point if point is not None else self.portLocalPosition(port["id"])
        side = port["side"]
        if port["mode"] == "output":
            side = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}[side]
        return self._port_triangle_path(point, side)

    def _paint_media(self, painter: QPainter, rect: QRectF) -> None:
        pixmap = self._movie.currentPixmap() if self._movie is not None else self._pixmap
        painter.drawRoundedRect(rect, 8, 8)
        if pixmap.isNull():
            painter.setPen(self.text_color)
            painter.drawText(rect.adjusted(10, 10, -10, -10), Qt.AlignmentFlag.AlignCenter, "Drop image / GIF")
            return
        scaled = pixmap.scaled(
            rect.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        target = QRectF(
            rect.center().x() - scaled.width() / 2,
            rect.center().y() - scaled.height() / 2,
            scaled.width(),
            scaled.height(),
        )
        painter.drawPixmap(target, scaled, QRectF(scaled.rect()))

    def _paint_line(self, painter: QPainter, rect: QRectF) -> None:
        points = self.points
        if not points:
            points = [QPointF(rect.left(), rect.center().y()), QPointF(rect.right(), rect.center().y())]
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        pen = QPen(self._highlight if self._highlight.isValid() else self.color, self.line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        styles = {
            "dash": Qt.PenStyle.DashLine,
            "dot": Qt.PenStyle.DotLine,
            "dashdot": Qt.PenStyle.DashDotLine,
        }
        pen.setStyle(styles.get(self.line_style, Qt.PenStyle.SolidLine))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        if self.animated:
            _paint_path_effect(
                painter, path, self.animation_effect, self.flow_color,
                self.line_width, self._line_phase, self.flow_spacing,
                self.effect_intensity,
            )
        if self._packets:
            _paint_packets(painter, path, self._packets)
        if self.arrow_start and len(points) > 1:
            self._paint_line_arrow(painter, points[0], points[1])
        if self.arrow_end and len(points) > 1:
            self._paint_line_arrow(painter, points[-1], points[-2])

    def _animation_active(self) -> bool:
        return self.kind == "line" and (
            self.animated
            or bool(self._packets)
            or (self.animation_effect == "packet" and self.packet_loop)
        )

    def _animation_has_packets(self) -> bool:
        return bool(self._packets)

    def _animation_tick(
        self,
        now: float,
        delta: float,
        *,
        advance_visuals: bool,
        allow_loop: bool,
        repaint: bool,
    ) -> None:
        if advance_visuals and self.animated:
            self._line_phase -= (
                self.flow_speed * self.flow_direction * max(0.0, delta / 0.04)
            )
        self._advance_packets(now, allow_loop=allow_loop)
        if repaint:
            self.update(self.boundingRect())

    def sendPacket(self, message_id: str, icon: Any = None, duration: float | None = None) -> None:
        resolved_icon = self.packet_icon if icon is None else icon
        self._packets.append({
            "id": message_id,
            "pixmap": _packet_pixmap(resolved_icon),
            "duration": max(0.1, float(duration or self.packet_duration)),
            "started": time.monotonic(),
        })
        self.canvas._animation_scheduler.register(self)

    def _advance_packets(self, now: float, *, allow_loop: bool = True) -> None:
        if (
            allow_loop
            and self.kind == "line"
            and self.animation_effect == "packet"
            and self.packet_loop
        ):
            if now - self._last_packet_at >= self.packet_interval:
                self._last_packet_at = now
                self.sendPacket(uuid.uuid4().hex[:10])
        arrived = [packet for packet in self._packets if now - packet["started"] >= packet["duration"]]
        arrived_ids = {id(packet) for packet in arrived}
        self._packets = [packet for packet in self._packets if id(packet) not in arrived_ids]
        for packet in arrived:
            self.packetArrived.emit(self.element_id, packet["id"])

    def _sync_line_animation(self) -> None:
        if self._animation_active():
            self.canvas._animation_scheduler.register(self)
        else:
            self.canvas._animation_scheduler.unregister(self)
        self.update()

    def _paint_line_arrow(self, painter: QPainter, tip: QPointF, near: QPointF) -> None:
        angle = math.atan2(tip.y() - near.y(), tip.x() - near.x())
        length = max(8.0, self.line_width * 4.0)
        left = QPointF(
            tip.x() - length * math.cos(angle - math.pi / 6),
            tip.y() - length * math.sin(angle - math.pi / 6),
        )
        right = QPointF(
            tip.x() - length * math.cos(angle + math.pi / 6),
            tip.y() - length * math.sin(angle + math.pi / 6),
        )
        arrow = QPainterPath(tip)
        arrow.lineTo(left)
        arrow.lineTo(right)
        arrow.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawPath(arrow)

    def _paint_chart(self, painter: QPainter, rect: QRectF) -> None:
        values = [float(value) for value in self.data if isinstance(value, (int, float))]
        if not values:
            return
        plot = rect.adjusted(22, 34, -16, -20)
        maximum = max(max(values), 1.0)
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        painter.drawLine(plot.bottomLeft(), plot.topLeft())
        painter.setPen(self.text_color)
        painter.drawText(QRectF(rect.left() + 12, rect.top() + 6, rect.width() - 24, 22), self.text)
        if self.kind == "bar_chart":
            slot = plot.width() / len(values)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.color)
            for index, value in enumerate(values):
                height = plot.height() * max(0.0, value) / maximum
                bar = QRectF(plot.left() + index * slot + slot * 0.18, plot.bottom() - height, slot * 0.64, height)
                painter.drawRoundedRect(bar, 3, 3)
        else:
            path = QPainterPath()
            step = plot.width() / max(1, len(values) - 1)
            points = [
                QPointF(plot.left() + index * step, plot.bottom() - plot.height() * max(0.0, value) / maximum)
                for index, value in enumerate(values)
            ]
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            painter.setPen(QPen(self.color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            painter.setBrush(self.color)
            for point in points:
                painter.drawEllipse(point, 4, 4)

    def mousePressEvent(self, event) -> None:
        if self.isSelected() and (event.pos() - self._rect.bottomRight()).manhattanLength() <= 14:
            self._resizing = True
            self._resize_origin = event.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing:
            point = event.pos()
            self.prepareGeometryChange()
            self._rect.setWidth(max(36.0, point.x()))
            self._rect.setHeight(max(28.0, point.y()))
            self.update()
            self.changed.emit(self.element_id)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._resizing = False
        super().mouseReleaseEvent(event)
        self.canvas._scene.clearSmartGuides()
        self.changed.emit(self.element_id)

    def hoverMoveEvent(self, event) -> None:
        port = self.portAt(self.mapToScene(event.pos())) if self.supports_ports else None
        if port is None:
            self.setToolTip("")
        else:
            lines = [
                f"{port.get('label', port['id'])} ({port['id']})",
                f"{port['mode']} · {port.get('dataType', 'any')}",
            ]
            if port.get("unit"):
                lines[-1] += f" · {port['unit']}"
            if port.get("maxConnections"):
                lines.append(f"Maximum connections: {port['maxConnections']}")
            if port.get("tooltip"):
                lines.append(str(port["tooltip"]))
            state = self.canvas.portRuntimeState(self.element_id, port["id"])
            if state["source"] != "unset":
                lines.append(
                    f"Runtime ({state['source']}): {state['value']!r} · {state['actualType']}"
                )
            feedback = self._port_feedback.get(port["id"])
            if feedback is not None:
                lines.append(feedback[1])
            self.setToolTip("\n".join(lines))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setToolTip("")
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            canvas = self.scene().canvas
            if canvas.editMode and not canvas._restoring:
                value = canvas._snap_item_position(self, value)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.changed.emit(self.element_id)
        return super().itemChange(change, value)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.element_id,
            "type": self.kind,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "width": self._rect.width(),
            "height": self._rect.height(),
            "text": self.text,
            "color": self.color.name(QColor.NameFormat.HexArgb),
            "background": self.background.name(QColor.NameFormat.HexArgb),
            "textColor": self.text_color.name(QColor.NameFormat.HexArgb),
            "data": list(self.data),
            "metadata": dict(self.metadata),
            "source": self.source,
            "lineWidth": self.line_width,
            "lineStyle": self.line_style,
            "arrowStart": self.arrow_start,
            "arrowEnd": self.arrow_end,
            "animated": self.animated,
            "animationEffect": self.animation_effect,
            "flowColor": self.flow_color.name(QColor.NameFormat.HexArgb),
            "flowSpeed": self.flow_speed,
            "flowDirection": "reverse" if self.flow_direction < 0 else "forward",
            "flowSpacing": self.flow_spacing,
            "effectIntensity": self.effect_intensity,
            "packetLoop": self.packet_loop,
            "packetDuration": self.packet_duration,
            "packetInterval": self.packet_interval,
            "packetIcon": self.packet_icon,
            "points": [[point.x(), point.y()] for point in self.points],
            "ports": [dict(port) for port in self.ports],
            "opacity": self.opacity(),
            "rotation": self.rotation(),
            "z": self.zValue(),
            "locked": self.locked,
            "hidden": self.hidden,
        }
        result.update(self.custom_properties)
        return result


class _CanvasGroup(QGraphicsObject):
    """Selectable document-backed frame for nested groups and subflows."""

    changed = pyqtSignal(str)

    def __init__(self, canvas: "MonkezCanva", record: dict[str, Any]) -> None:
        super().__init__()
        self.canvas = canvas
        self.group_id = str(record["id"])
        self.element_id = self.group_id
        self.kind = normalize_group_kind(record.get("kind", "frame"))
        self.members = tuple(str(member) for member in record.get("members", ()))
        self.text = str(record.get("label", record.get("text", "Group")))
        self.color = _color(record.get("color", "#64748b"), "#64748b")
        self.background = _color(record.get("background", "#f8fafc"), "#f8fafc")
        self.header_color = _color(record.get("headerColor", self.color), "#64748b")
        self.collapsed = bool(record.get("collapsed", False))
        self.locked = bool(record.get("locked", False))
        self.hidden = bool(record.get("hidden", False))
        self.padding = max(0.0, min(120.0, float(record.get("padding", 28.0))))
        self.lanes = tuple(str(value) for value in record.get("lanes", ()))
        self.orientation = (
            "vertical" if str(record.get("orientation", "horizontal")).lower() == "vertical"
            else "horizontal"
        )
        self.custom_properties = {
            key: value for key, value in record.items()
            if key not in _GROUP_STANDARD_PROPERTIES
        }
        self._highlight = QColor()
        self._rect = QRectF(
            0,
            0,
            max(120.0, float(record.get("width", 320.0))),
            max(54.0, float(record.get("height", 220.0))),
        )
        self._drag_start: QPointF | None = None
        self._last_drag_position = QPointF()
        self.setPos(float(record.get("x", 0.0)), float(record.get("y", 0.0)))
        self.setZValue(float(record.get("z", -20.0)))
        self.setOpacity(max(0.0, min(1.0, float(record.get("opacity", 1.0)))))
        self.setRotation(float(record.get("rotation", 0.0)))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setEditable(canvas.editMode and not canvas.isReadOnly())

    @property
    def display_height(self) -> float:
        return 46.0 if self.collapsed else self._rect.height()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._rect.width(), self.display_height).adjusted(-3, -3, 3, 3)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self._rect.width(), self.display_height), 13, 13)
        return path

    def setEditable(self, editable: bool) -> None:
        movable = bool(editable) and not self.locked
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, bool(editable))
        self.setCursor(Qt.CursorShape.SizeAllCursor if movable else Qt.CursorShape.ArrowCursor)

    def paint(self, painter: QPainter, _option, _widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self._rect.width(), self.display_height)
        surface = QColor(self.background)
        surface.setAlpha(226 if self.kind == "subflow" else 178)
        border = (
            QColor(self._highlight)
            if self._highlight.isValid()
            else QColor("#2563eb") if self.isSelected() else QColor(self.color)
        )
        pen = QPen(border, 2.2 if self.isSelected() else 1.4)
        if self.kind == "frame":
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(surface)
        painter.drawRoundedRect(rect, 13, 13)

        header_height = min(42.0, rect.height())
        header = QPainterPath()
        header.addRoundedRect(QRectF(0, 0, rect.width(), header_height), 13, 13)
        header.addRect(QRectF(0, header_height / 2, rect.width(), header_height / 2))
        header_fill = QColor(self.header_color)
        header_fill.setAlpha(34 if self.kind == "frame" else 52)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(header_fill)
        painter.drawPath(header)

        painter.setPen(QColor("#27323a"))
        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        prefix = "◇  " if self.kind == "subflow" else "▦  " if self.kind == "swimlane" else ""
        painter.drawText(
            QRectF(14, 0, max(20.0, rect.width() - 58), header_height),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            f"{prefix}{self.text}",
        )
        painter.setPen(QPen(QColor("#64748b"), 1.7))
        center = QPointF(rect.right() - 22, header_height / 2)
        if self.collapsed:
            painter.drawLine(center + QPointF(-4, -2), center + QPointF(0, 2))
            painter.drawLine(center + QPointF(0, 2), center + QPointF(4, -2))
        else:
            painter.drawLine(center + QPointF(-4, 2), center + QPointF(0, -2))
            painter.drawLine(center + QPointF(0, -2), center + QPointF(4, 2))

        if self.kind == "swimlane" and not self.collapsed and self.lanes:
            painter.setPen(QPen(QColor(self.color), 1, Qt.PenStyle.DashLine))
            count = len(self.lanes)
            for index, label in enumerate(self.lanes):
                if self.orientation == "vertical":
                    lane_width = rect.width() / count
                    lane_rect = QRectF(index * lane_width, header_height, lane_width, rect.height() - header_height)
                    if index:
                        painter.drawLine(lane_rect.topLeft(), lane_rect.bottomLeft())
                else:
                    lane_height = (rect.height() - header_height) / count
                    lane_rect = QRectF(0, header_height + index * lane_height, rect.width(), lane_height)
                    if index:
                        painter.drawLine(lane_rect.topLeft(), lane_rect.topRight())
                painter.setPen(QColor("#64748b"))
                painter.drawText(lane_rect.adjusted(8, 5, -8, -5), Qt.AlignmentFlag.AlignTop, label)
                painter.setPen(QPen(QColor(self.color), 1, Qt.PenStyle.DashLine))

        if self.kind == "subflow" and not self.collapsed:
            painter.setPen(QPen(QColor(self.color), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(6, 6, -6, -6), 9, 9)

    def mouseDoubleClickEvent(self, event) -> None:
        if not self.locked and self.canvas.editMode:
            self.canvas.setGroupCollapsed(self.group_id, not self.collapsed)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.locked:
            self._drag_start = QPointF(self.pos())
            self._last_drag_position = QPointF(self.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        start = self._drag_start
        self._drag_start = None
        super().mouseReleaseEvent(event)
        if start is not None:
            delta = self.pos() - start
            if not math.isclose(delta.x(), 0.0) or not math.isclose(delta.y(), 0.0):
                self.canvas._commit_group_move(self.group_id, delta)

    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
            and self._drag_start is not None
            and not self.canvas._restoring
        ):
            current = QPointF(value)
            delta = current - self._last_drag_position
            self._last_drag_position = current
            self.canvas._preview_group_move(self.group_id, delta)
        return super().itemChange(change, value)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.group_id,
            "members": list(self.members),
            "kind": self.kind,
            "label": self.text,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "width": self._rect.width(),
            "height": self._rect.height(),
            "color": self.color.name(QColor.NameFormat.HexArgb),
            "background": self.background.name(QColor.NameFormat.HexArgb),
            "headerColor": self.header_color.name(QColor.NameFormat.HexArgb),
            "padding": self.padding,
            "collapsed": self.collapsed,
            "lanes": list(self.lanes),
            "orientation": self.orientation,
            "opacity": self.opacity(),
            "rotation": self.rotation(),
            "z": self.zValue(),
            "locked": self.locked,
            "hidden": self.hidden,
        }
        result.update(self.custom_properties)
        return result


def _rounded_polyline_path(points: list[QPointF], radius: float) -> QPainterPath:
    points = [QPointF(x, y) for x, y in deduplicate_points((point.x(), point.y()) for point in points)]
    path = QPainterPath(points[0])
    if len(points) < 3 or radius <= 0:
        for point in points[1:]:
            path.lineTo(point)
        return path
    for index in range(1, len(points) - 1):
        previous, corner, following = points[index - 1], points[index], points[index + 1]
        incoming = corner - previous
        outgoing = following - corner
        incoming_length = math.hypot(incoming.x(), incoming.y())
        outgoing_length = math.hypot(outgoing.x(), outgoing.y())
        if incoming_length <= 0.001 or outgoing_length <= 0.001:
            path.lineTo(corner)
            continue
        distance = min(float(radius), incoming_length / 2, outgoing_length / 2)
        before = corner - incoming * (distance / incoming_length)
        after = corner + outgoing * (distance / outgoing_length)
        path.lineTo(before)
        path.quadTo(corner, after)
    path.lineTo(points[-1])
    return path


class _CanvasWaypointHandle(QGraphicsObject):
    def __init__(self, connector: "_CanvasConnector", index: int) -> None:
        super().__init__(connector)
        self.connector = connector
        self.index = index
        self.setZValue(1000)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Drag reroute point · double-click to remove")

    def boundingRect(self) -> QRectF:
        return QRectF(-7, -7, 14, 14)

    def paint(self, painter: QPainter, _option, _widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ef6a5b"), 2))
        painter.setBrush(QColor("#fffdfb"))
        painter.drawEllipse(QRectF(-5, -5, 10, 10))

    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
            and not self.connector._syncing_handles
            and self.index < len(self.connector.waypoints)
        ):
            self.connector.waypoints[self.index] = QPointF(value)
            self.connector.updatePath()
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.connector.canvas.updateConnector(
            self.connector.connector_id,
            waypoints=[[point.x(), point.y()] for point in self.connector.waypoints],
        )

    def mouseDoubleClickEvent(self, event) -> None:
        self.connector.canvas.removeConnectorWaypoint(self.connector.connector_id, self.index)
        event.accept()


class _CanvasConnector(QGraphicsObject):
    """Selectable, serializable signal path between two node-like elements."""

    changed = pyqtSignal(str)
    packetArrived = pyqtSignal(str, str)

    def __init__(
        self,
        canvas: "MonkezCanva",
        connector_id: str,
        source: _CanvasElement,
        target: _CanvasElement,
        options: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        options = dict(options or {})
        self.canvas = canvas
        self.connector_id = connector_id
        self.element_id = connector_id
        self.kind = "connector"
        self.source = source
        self.target = target
        self.source_port = str(options.get("sourcePort", ""))
        self.target_port = str(options.get("targetPort", ""))
        self.color = _color(options.get("color", "#64748b"), "#64748b")
        self.flow_color = _color(options.get("flowColor", "#38bdf8"), "#38bdf8")
        self.route = str(options.get("route", "bezier")).lower()
        self.line_style = str(options.get("lineStyle", "solid")).lower()
        self.line_width = max(0.5, float(options.get("lineWidth", 2.2)))
        self.arrow_start = bool(options.get("arrowStart", False))
        self.arrow_end = bool(options.get("arrowEnd", True))
        self.animated = bool(options.get("animated", False))
        self.animation_effect = str(options.get("animationEffect", "flow")).lower()
        self.flow_speed = max(0.1, float(options.get("flowSpeed", 1.0)))
        self.flow_direction = -1 if str(options.get("flowDirection", "forward")).lower() == "reverse" else 1
        self.flow_spacing = max(1.0, float(options.get("flowSpacing", 5.0)))
        self.effect_intensity = max(0.2, min(4.0, float(options.get("effectIntensity", 1.0))))
        self.packet_loop = bool(options.get("packetLoop", False))
        self.packet_duration = max(0.1, float(options.get("packetDuration", 1.5)))
        self.packet_interval = max(0.05, float(options.get("packetInterval", 0.7)))
        self.packet_icon = str(options.get("packetIcon", ""))
        self._packets: list[dict[str, Any]] = []
        self._last_packet_at = 0.0
        self.waypoints = [QPointF(float(point[0]), float(point[1])) for point in options.get("waypoints", [])]
        self.corner_radius = max(0.0, min(80.0, float(options.get("cornerRadius", 14.0))))
        self.label = str(options.get("label", ""))
        self.label_position = max(0.0, min(1.0, float(options.get("labelPosition", 0.5))))
        self.parallel_spacing = max(0.0, min(120.0, float(options.get("parallelSpacing", 22.0))))
        self.obstacle_clearance = max(0.0, min(160.0, float(options.get("obstacleClearance", 20.0))))
        self.bridge_crossings = bool(options.get("bridgeCrossings", True))
        self.bridge_size = max(3.0, min(30.0, float(options.get("bridgeSize", 7.0))))
        self.bus_style = str(options.get("busStyle", "none")).lower()
        self.bus_width = max(2.0, min(80.0, float(options.get("busWidth", 10.0))))
        self.bus_id = str(options.get("busId", ""))
        self.metadata = dict(options.get("metadata", {}))
        self.locked = bool(options.get("locked", False))
        self.hidden = bool(options.get("hidden", False))
        self._highlight = QColor()
        self._path = QPainterPath()
        self._flow_phase = 0.0
        self._waypoint_handles: list[_CanvasWaypointHandle] = []
        self._syncing_handles = False
        self._handles_editable = False
        self._bridge_cache_revision = -1
        self._bridge_cache: list[tuple[QPointF, float]] = []
        self.setZValue(float(options.get("z", -1)))
        self.setOpacity(max(0.0, min(1.0, float(options.get("opacity", 1.0)))))
        source.changed.connect(self.updatePath)
        target.changed.connect(self.updatePath)
        self.setEditable(canvas.editMode and not canvas.isReadOnly())
        self.updatePath()
        self._sync_animation()

    def boundingRect(self) -> QRectF:
        margin = max(28.0 if self.label else 12.0, self.line_width + 9.0)
        return self._path.boundingRect().adjusted(-margin, -margin, margin, margin)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(max(12.0, self.line_width + 8.0))
        return stroker.createStroke(self._path)

    def setEditable(self, enabled: bool) -> None:
        self._handles_editable = bool(enabled)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, enabled)
        if not enabled:
            self.setSelected(False)
        self._sync_waypoint_handles()

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._sync_waypoint_handles()
        return result

    def _lane_offset(self) -> float:
        siblings = [
            connector_id
            for connector_id, connector in self.canvas._connectors.items()
            if {connector.source.element_id, connector.target.element_id}
            == {self.source.element_id, self.target.element_id}
        ]
        if self.connector_id not in siblings:
            siblings.append(self.connector_id)
        return parallel_lane_offset(self.connector_id, siblings, self.parallel_spacing)

    def updatePath(self, *_args) -> None:
        self.prepareGeometryChange()
        start = self.source.portScenePosition(self.source_port, "source")
        end = self.target.portScenePosition(self.target_port, "target")
        path = QPainterPath(start)
        lane = self._lane_offset()
        if self.source is self.target:
            bounds = self.source.sceneBoundingRect()
            reach = 54.0 + abs(lane)
            side = 1.0 if lane >= 0 else -1.0
            path.cubicTo(
                QPointF(bounds.right() + reach, start.y() - reach * 0.2),
                QPointF(bounds.center().x() + side * reach * 0.35, bounds.top() - reach),
                end,
            )
        elif self.route == "auto":
            obstacles = [
                (
                    bounds.x(), bounds.y(), bounds.width(), bounds.height()
                )
                for element_id, item in self.canvas._elements.items()
                if item.isVisible()
                and element_id not in (self.source.element_id, self.target.element_id)
                for bounds in (item.sceneBoundingRect(),)
            ]
            anchors = [start, *self.waypoints, end]
            routed: list[QPointF] = []
            for first, second in zip(anchors, anchors[1:]):
                segment = obstacle_avoiding_route(
                    (first.x(), first.y()), (second.x(), second.y()), obstacles,
                    clearance=self.obstacle_clearance,
                )
                routed.extend(QPointF(x, y) for x, y in segment[1 if routed else 0:])
            path = _rounded_polyline_path(routed, self.corner_radius)
        elif self.route in ("orthogonal", "elbow"):
            route_points = orthogonal_points(
                (start.x(), start.y()), (end.x(), end.y()),
                ((point.x(), point.y()) for point in self.waypoints),
                lane_offset=lane,
            )
            path = _rounded_polyline_path(
                [QPointF(x, y) for x, y in route_points], self.corner_radius
            )
        elif self.waypoints:
            path = _rounded_polyline_path(
                [start, *self.waypoints, end], self.corner_radius
            )
        elif self.route in ("straight", "polyline"):
            if math.isclose(lane, 0.0):
                path.lineTo(end)
            else:
                dx, dy = end.x() - start.x(), end.y() - start.y()
                length = max(1.0, math.hypot(dx, dy))
                midpoint = (start + end) / 2 + QPointF(-dy / length * lane, dx / length * lane)
                path.quadTo(midpoint, end)
        else:
            delta = max(50.0, abs(end.x() - start.x()) * 0.5)
            direction = 1 if end.x() >= start.x() else -1
            dx, dy = end.x() - start.x(), end.y() - start.y()
            length = max(1.0, math.hypot(dx, dy))
            offset = QPointF(-dy / length * lane, dx / length * lane)
            path.cubicTo(
                QPointF(start.x() + delta * direction, start.y()) + offset,
                QPointF(end.x() - delta * direction, end.y()) + offset,
                end,
            )
        self._path = path
        self.canvas._routing_revision += 1
        self._sync_waypoint_handles()
        self.update()

    def _sync_waypoint_handles(self) -> None:
        if not hasattr(self, "_waypoint_handles"):
            return
        while len(self._waypoint_handles) > len(self.waypoints):
            handle = self._waypoint_handles.pop()
            handle.setParentItem(None)
            if handle.scene() is not None:
                handle.scene().removeItem(handle)
            handle.deleteLater()
        while len(self._waypoint_handles) < len(self.waypoints):
            self._waypoint_handles.append(
                _CanvasWaypointHandle(self, len(self._waypoint_handles))
            )
        visible = self._handles_editable and self.isSelected() and not self.locked
        self._syncing_handles = True
        try:
            for index, (handle, point) in enumerate(zip(self._waypoint_handles, self.waypoints)):
                handle.index = index
                handle.setPos(point)
                handle.setVisible(visible)
        finally:
            self._syncing_handles = False

    def mouseDoubleClickEvent(self, event) -> None:
        if self._handles_editable and not self.locked:
            self.canvas.addConnectorWaypoint(self.connector_id, event.scenePos())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def paint(self, painter: QPainter, _option, _widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isSelected():
            painter.setPen(QPen(QColor(37, 99, 235, 80), self.line_width + 7, Qt.PenStyle.SolidLine))
            painter.drawPath(self._path)
        pen = QPen(self._highlight if self._highlight.isValid() else self.color, self.line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if self.line_style == "dash":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif self.line_style == "dot":
            pen.setStyle(Qt.PenStyle.DotLine)
        elif self.line_style == "dashdot":
            pen.setStyle(Qt.PenStyle.DashDotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.bus_style in ("trunk", "double"):
            bus_pen = QPen(pen)
            bus_pen.setStyle(Qt.PenStyle.SolidLine)
            bus_pen.setWidthF(max(self.line_width, self.bus_width))
            painter.setPen(bus_pen)
            painter.drawPath(self._path)
            if self.bus_style == "double":
                inner = QPen(self.canvas.backgroundColor, max(1.0, self.bus_width - self.line_width * 2.2))
                inner.setCapStyle(Qt.PenCapStyle.RoundCap)
                inner.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(inner)
                painter.drawPath(self._path)
            else:
                painter.setPen(pen)
                painter.drawPath(self._path)
        else:
            painter.drawPath(self._path)
        if self.animated:
            _paint_path_effect(
                painter, self._path, self.animation_effect, self.flow_color,
                self.line_width, self._flow_phase, self.flow_spacing,
                self.effect_intensity,
            )
        if self.bridge_crossings:
            self._paint_crossing_bridges(painter, pen)
        if self._packets:
            _paint_packets(painter, self._path, self._packets)
        if self.arrow_start:
            self._paint_arrow(painter, 0.0)
        if self.arrow_end:
            self._paint_arrow(painter, 1.0)
        if self.label:
            point = self._path.pointAtPercent(self.label_position)
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(self.label).adjusted(-7, -4, 7, 4)
            text_rect.moveCenter(point.toPoint())
            painter.setPen(QPen(QColor("#d8d4cf"), 1))
            painter.setBrush(QColor(255, 254, 252, 242))
            painter.drawRoundedRect(QRectF(text_rect), 6, 6)
            painter.setPen(QColor("#334155"))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.label)

    def _paint_crossing_bridges(self, painter: QPainter, pen: QPen) -> None:
        for point, angle in self._crossing_bridges():
            radius = self.bridge_size
            painter.save()
            painter.translate(point)
            painter.rotate(math.degrees(angle))
            gap = QPen(self.canvas.backgroundColor, max(self.line_width + 5.0, radius * 0.9))
            gap.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(gap)
            painter.drawLine(QPointF(-radius, 0), QPointF(radius, 0))
            bridge_pen = QPen(pen)
            bridge_pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(bridge_pen)
            bridge = QPainterPath(QPointF(-radius, 0))
            bridge.cubicTo(
                QPointF(-radius * 0.45, -radius),
                QPointF(radius * 0.45, -radius),
                QPointF(radius, 0),
            )
            painter.drawPath(bridge)
            painter.restore()

    def _crossing_bridges(self) -> list[tuple[QPointF, float]]:
        if self._bridge_cache_revision == self.canvas._routing_revision:
            return self._bridge_cache
        ordered = sorted(
            self.canvas._connectors.values(),
            key=lambda connector: (connector.zValue(), list(self.canvas._connectors).index(connector.connector_id)),
        )
        position = ordered.index(self) if self in ordered else 0
        current_segments = self._path_segments()
        bridges: list[tuple[QPointF, float]] = []
        for other in ordered[:position]:
            if not other.isVisible() or {self.source.element_id, self.target.element_id} & {other.source.element_id, other.target.element_id}:
                continue
            for first_start, first_end in current_segments:
                for second_start, second_end in other._path_segments():
                    crossing = segment_intersection(
                        (first_start.x(), first_start.y()), (first_end.x(), first_end.y()),
                        (second_start.x(), second_start.y()), (second_end.x(), second_end.y()),
                        endpoint_margin=0.02,
                    )
                    if crossing is not None:
                        angle = math.atan2(first_end.y() - first_start.y(), first_end.x() - first_start.x())
                        bridges.append((QPointF(*crossing), angle))
                        if len(bridges) >= 32:
                            break
                if len(bridges) >= 32:
                    break
        self._bridge_cache = bridges
        self._bridge_cache_revision = self.canvas._routing_revision
        return bridges

    def _path_segments(self) -> list[tuple[QPointF, QPointF]]:
        segments: list[tuple[QPointF, QPointF]] = []
        for polygon in self._path.toSubpathPolygons():
            segments.extend((QPointF(first), QPointF(second)) for first, second in zip(polygon, polygon[1:]))
        return segments

    def _paint_arrow(self, painter: QPainter, position: float) -> None:
        point = self._path.pointAtPercent(position)
        near = self._path.pointAtPercent(0.025 if position == 0.0 else 0.975)
        dx = point.x() - near.x()
        dy = point.y() - near.y()
        angle = math.atan2(dy, dx)
        length = max(8.0, self.line_width * 4.0)
        left = QPointF(
            point.x() - length * math.cos(angle - math.pi / 6),
            point.y() - length * math.sin(angle - math.pi / 6),
        )
        right = QPointF(
            point.x() - length * math.cos(angle + math.pi / 6),
            point.y() - length * math.sin(angle + math.pi / 6),
        )
        arrow = QPainterPath(point)
        arrow.lineTo(left)
        arrow.lineTo(right)
        arrow.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(
            self._highlight
            if self._highlight.isValid()
            else self.flow_color if self.animated else self.color
        )
        painter.drawPath(arrow)

    def _animation_active(self) -> bool:
        return self.animated or bool(self._packets) or (
            self.animation_effect == "packet" and self.packet_loop
        )

    def _animation_has_packets(self) -> bool:
        return bool(self._packets)

    def _animation_tick(
        self,
        now: float,
        delta: float,
        *,
        advance_visuals: bool,
        allow_loop: bool,
        repaint: bool,
    ) -> None:
        if advance_visuals and self.animated:
            self._flow_phase -= (
                self.flow_speed * self.flow_direction * max(0.0, delta / 0.04)
            )
        self._advance_packets(now, allow_loop=allow_loop)
        if repaint:
            self.update(self.boundingRect())

    def sendPacket(self, message_id: str, icon: Any = None, duration: float | None = None) -> None:
        resolved_icon = self.packet_icon if icon is None else icon
        self._packets.append({
            "id": message_id,
            "pixmap": _packet_pixmap(resolved_icon),
            "duration": max(0.1, float(duration or self.packet_duration)),
            "started": time.monotonic(),
        })
        self.canvas._animation_scheduler.register(self)

    def _advance_packets(self, now: float, *, allow_loop: bool = True) -> None:
        if allow_loop and self.animation_effect == "packet" and self.packet_loop:
            if now - self._last_packet_at >= self.packet_interval:
                self._last_packet_at = now
                message_id = uuid.uuid4().hex[:10]
                self.canvas._message_payloads[message_id] = {
                    "icon": self.packet_icon,
                    "duration": self.packet_duration,
                    "pending": 1,
                    "visited": {self.connector_id},
                }
                self.sendPacket(message_id)
                self.canvas.messageSent.emit(self.connector_id, message_id)
        arrived = [packet for packet in self._packets if now - packet["started"] >= packet["duration"]]
        arrived_ids = {id(packet) for packet in arrived}
        self._packets = [packet for packet in self._packets if id(packet) not in arrived_ids]
        for packet in arrived:
            self.packetArrived.emit(self.connector_id, packet["id"])

    def _sync_animation(self) -> None:
        if self._animation_active():
            self.canvas._animation_scheduler.register(self)
        else:
            self.canvas._animation_scheduler.unregister(self)
        self.update()

    def release(self) -> None:
        self.canvas._animation_scheduler.unregister(self)
        self._waypoint_handles.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.connector_id,
            "type": "connector",
            "source": self.source.element_id,
            "target": self.target.element_id,
            "sourcePort": self.source_port,
            "targetPort": self.target_port,
            "color": self.color.name(QColor.NameFormat.HexArgb),
            "flowColor": self.flow_color.name(QColor.NameFormat.HexArgb),
            "route": self.route,
            "lineStyle": self.line_style,
            "lineWidth": self.line_width,
            "arrowStart": self.arrow_start,
            "arrowEnd": self.arrow_end,
            "animated": self.animated,
            "animationEffect": self.animation_effect,
            "flowSpeed": self.flow_speed,
            "flowDirection": "reverse" if self.flow_direction < 0 else "forward",
            "flowSpacing": self.flow_spacing,
            "effectIntensity": self.effect_intensity,
            "packetLoop": self.packet_loop,
            "packetDuration": self.packet_duration,
            "packetInterval": self.packet_interval,
            "packetIcon": self.packet_icon,
            "waypoints": [[point.x(), point.y()] for point in self.waypoints],
            "cornerRadius": self.corner_radius,
            "label": self.label,
            "labelPosition": self.label_position,
            "parallelSpacing": self.parallel_spacing,
            "obstacleClearance": self.obstacle_clearance,
            "bridgeCrossings": self.bridge_crossings,
            "bridgeSize": self.bridge_size,
            "busStyle": self.bus_style,
            "busWidth": self.bus_width,
            "busId": self.bus_id,
            "metadata": dict(self.metadata),
            "opacity": self.opacity(),
            "z": self.zValue(),
            "locked": self.locked,
            "hidden": self.hidden,
        }


class _CanvasPaneHeader(QFrame):
    """Custom title bar that keeps the compact editor pane draggable."""

    def __init__(self, dialog: QDialog, canvas: "MonkezCanva") -> None:
        super().__init__(dialog)
        self._drag_offset = None
        self.setObjectName("canvasPaneHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 3, 2, 8)
        layout.setSpacing(11)
        brand = QLabel()
        brand.setObjectName("canvasPaneBrand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setFixedSize(38, 38)
        brand.setPixmap(_canvas_icon("node", "#ffffff").pixmap(20, 20))
        layout.addWidget(brand)
        title = QLabel("MonkezCanva")
        title.setObjectName("canvasPaneTitle")
        layout.addWidget(title)
        layout.addStretch(1)
        self._selection_badge = QLabel()
        self._selection_badge.setObjectName("canvasSelectionBadge")
        self._selection_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._selection_badge)
        commands = QToolButton()
        commands.setObjectName("canvasPaneCommand")
        commands.setIcon(_canvas_icon("command"))
        commands.setIconSize(QSize(17, 17))
        commands.setToolTip("Open command palette (Ctrl+K)")
        commands.clicked.connect(lambda _checked=False: canvas.showCommandPalette())
        layout.addWidget(commands)
        close = QToolButton()
        close.setObjectName("canvasPaneClose")
        close.setIcon(_canvas_icon("close"))
        close.setIconSize(QSize(16, 16))
        close.setToolTip("Close edit mode (Ctrl+D, E)")
        close.clicked.connect(lambda _checked=False: canvas.setEditMode(False))
        layout.addWidget(close)
        canvas.selectionSetChanged.connect(self.setSelectionCount)
        self.setSelectionCount(canvas.selectedObjectIds())

    def setSelectionCount(self, object_ids: list[str]) -> None:
        count = len(object_ids)
        self._selection_badge.setText(
            "No selection" if count == 0 else "1 selected" if count == 1 else f"{count} selected"
        )
        self._selection_badge.setProperty("hasSelection", count > 0)
        self._selection_badge.style().unpolish(self._selection_badge)
        self._selection_badge.style().polish(self._selection_badge)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class _CanvasNumberField(QDoubleSpinBox):
    """Spinbox that renders a real mixed-value state until the user edits it."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mixed_value = False

    def setMixedValue(self, mixed: bool, fallback: float | None = None) -> None:
        if fallback is not None:
            self.setValue(float(fallback))
        self._mixed_value = bool(mixed)
        self.setProperty("mixedValue", self._mixed_value)
        self.style().unpolish(self)
        self.style().polish(self)
        self.lineEdit().setText(
            "Mixed" if self._mixed_value else super().textFromValue(self.value())
        )
        self.update()

    def hasMixedValue(self) -> bool:
        return self._mixed_value

    def textFromValue(self, value: float) -> str:
        if getattr(self, "_mixed_value", False):
            return "Mixed"
        return super().textFromValue(value)

    def stepBy(self, steps: int) -> None:
        if self._mixed_value:
            self.setMixedValue(False)
        super().stepBy(steps)

    def keyPressEvent(self, event) -> None:
        if self._mixed_value and (
            event.text() or event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
        ):
            self.setMixedValue(False)
            self.lineEdit().clear()
        super().keyPressEvent(event)


class _CanvasPaletteTile(QFrame):
    """One compact registry-driven component entry with a favorite action."""

    def __init__(
        self,
        definition: ElementDefinition,
        favorite: bool,
        add_callback: Callable[[], None],
        favorite_callback: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.definition = definition
        self.setObjectName("canvasPaletteTile")
        self.setProperty("componentType", definition.type_id)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 4, 4)
        layout.setSpacing(1)
        add = QToolButton()
        add.setObjectName("canvasPaletteAdd")
        add.setText(definition.label)
        add.setIcon(_canvas_icon(definition.icon))
        add.setIconSize(QSize(18, 18))
        add.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        add.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        add.setToolTip(f"Add {definition.label}\n{definition.category} · {definition.type_id}")
        add.clicked.connect(lambda _checked=False: add_callback())
        layout.addWidget(add, 1)
        star = QToolButton()
        star.setObjectName("canvasPaletteFavorite")
        star.setIcon(_canvas_icon("star_filled" if favorite else "star", "#f59e0b"))
        star.setIconSize(QSize(15, 15))
        star.setFixedSize(28, 28)
        star.setToolTip("Remove from favorites" if favorite else "Add to favorites")
        star.clicked.connect(lambda _checked=False: favorite_callback())
        layout.addWidget(star)


class _CanvasCardGroup(QGroupBox):
    """A platform-stable inspector card with its title inside the frame.

    Native ``QGroupBox`` painting differs noticeably between Windows styles and
    can cut the top border around the title.  The pane uses an inset title, so
    painting the card ourselves keeps the approved visual language consistent
    at every DPI while retaining QGroupBox semantics and accessibility.
    """

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        card = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor("#e5e1dc"), 1.0))
        painter.setBrush(QColor("#fffefd"))
        painter.drawRoundedRect(card, 13.0, 13.0)
        if self.title():
            font = QFont(self.font())
            font.setPixelSize(11)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor("#303941"))
            painter.drawText(
                QRectF(14.0, 10.0, max(0.0, self.width() - 28.0), 18.0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.title(),
            )


class _CanvasCommandPalette(QDialog):
    """Keyboard-first, context-aware command launcher for one canvas."""

    def __init__(self, canvas: "MonkezCanva") -> None:
        super().__init__(canvas.window())
        self.canvas = canvas
        self._command_lookup: dict[str, Callable[[], Any]] = {}
        self.setObjectName("canvasCommandPalette")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(520, 430)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        panel = QFrame()
        panel.setObjectName("canvasCommandPanel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(31, 36, 41, 80))
        panel.setGraphicsEffect(shadow)
        root.addWidget(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 15, 16, 13)
        layout.setSpacing(9)
        title_row = QHBoxLayout()
        title = QLabel("Command palette")
        title.setObjectName("canvasCommandTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        shortcut = QLabel("Ctrl K")
        shortcut.setObjectName("canvasCommandShortcut")
        title_row.addWidget(shortcut)
        layout.addLayout(title_row)
        self._search = QLineEdit()
        self._search.setObjectName("canvasCommandSearch")
        self._search.setPlaceholderText("Search actions or components…")
        self._search.addAction(_canvas_icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self._search.textChanged.connect(self._refresh)
        self._search.returnPressed.connect(self._activate_current)
        self._search.installEventFilter(self)
        layout.addWidget(self._search)
        self._list = QListWidget()
        self._list.setObjectName("canvasCommandList")
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.itemDoubleClicked.connect(lambda _item: self._activate_current())
        layout.addWidget(self._list, 1)
        hint = QLabel("↑ ↓ navigate   ·   Enter run   ·   Esc close")
        hint.setObjectName("canvasCommandHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        self.setStyleSheet("""
        QFrame#canvasCommandPanel {
            background: #fcfbf9; border: 1px solid #d8d5d0; border-radius: 18px;
        }
        QLabel#canvasCommandTitle { color: #303941; font-size: 16px; font-weight: 700; }
        QLabel#canvasCommandShortcut {
            color: #7a7f84; background: #f1efec; border: 1px solid #e2ded8;
            border-radius: 7px; padding: 4px 8px; font-size: 9px; font-weight: 650;
        }
        QLineEdit#canvasCommandSearch {
            color: #303941; background: #fffefd; border: 1px solid #d7d3ce;
            border-radius: 11px; padding: 8px 10px; min-height: 28px;
            selection-background-color: #ffd8d2;
        }
        QLineEdit#canvasCommandSearch:focus { border-color: #ff8c80; }
        QListWidget#canvasCommandList {
            color: #394249; background: transparent; border: none; outline: none;
        }
        QListWidget#canvasCommandList::item {
            border-radius: 9px; padding: 9px 10px; margin: 1px 0;
        }
        QListWidget#canvasCommandList::item:selected { color: #df5145; background: #fff0ed; }
        QListWidget#canvasCommandList::item:hover:!selected { background: #f4f1ed; }
        QListWidget#canvasCommandList::item:disabled { color: #b5b1ac; }
        QLabel#canvasCommandHint { color: #96928d; font-size: 9px; }
        """)

    def showPalette(self, query: str = "") -> None:
        self._search.setText(str(query))
        self._refresh()
        owner = self.canvas.window()
        center = owner.frameGeometry().center()
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        self.show()
        self.raise_()
        self.activateWindow()
        self._search.setFocus()
        self._search.selectAll()

    def eventFilter(self, watched, event) -> bool:
        if watched is self._search and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Down:
                self._list.setCurrentRow(min(self._list.count() - 1, self._list.currentRow() + 1))
                return True
            if event.key() == Qt.Key.Key_Up:
                self._list.setCurrentRow(max(0, self._list.currentRow() - 1))
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.close()
                return True
        return super().eventFilter(watched, event)

    def _commands(self) -> list[tuple[str, str, str, str, str, bool, Callable[[], Any]]]:
        canvas = self.canvas
        writable = not canvas.isReadOnly()
        selected = canvas.selectedObjectIds()
        selected_elements = canvas.selectedElementIds()
        clipboard_objects = bool(selected) and all(
            object_id not in canvas._groups for object_id in selected
        )
        clipboard = QApplication.clipboard().mimeData()
        can_paste = bool(clipboard and clipboard.hasFormat(CANVAS_CLIPBOARD_MIME_TYPE))
        commands: list[tuple[str, str, str, str, str, bool, Callable[[], Any]]] = []
        for definition in canvas.elementRegistry().definitions():
            commands.append((
                f"add:{definition.type_id}", f"Add {definition.label}",
                definition.category, "component add", definition.icon, writable,
                lambda kind=definition.type_id: canvas.addPaletteElement(kind),
            ))
        commands.extend((
            ("edit:copy", "Copy selection", "Edit", "clipboard", "duplicate", clipboard_objects, canvas.copySelection),
            ("edit:cut", "Cut selection", "Edit", "clipboard", "delete", writable and clipboard_objects, canvas.cutSelection),
            ("edit:paste", "Paste", "Edit", "clipboard", "duplicate", writable and can_paste, canvas.pasteSelection),
            ("edit:duplicate", "Duplicate selection", "Edit", "copy", "duplicate", writable and clipboard_objects, canvas.duplicateSelection),
            ("edit:delete", "Delete selection", "Edit", "remove", "delete", writable and bool(selected), canvas.deleteSelected),
            ("edit:select-all", "Select all elements", "Edit", "selection", "rectangle", bool(canvas.elements()), canvas.selectAllElements),
            ("history:undo", f"Undo {canvas.undoText()}".strip(), "History", "revert", "undo", writable and canvas.canUndo(), canvas.undo),
            ("history:redo", f"Redo {canvas.redoText()}".strip(), "History", "repeat", "redo", writable and canvas.canRedo(), canvas.redo),
            ("view:fit", "Fit all content", "View", "zoom", "fit", True, canvas.fitContent),
            ("view:zoom-selection", "Zoom to selection", "View", "focus", "align_center", bool(selected), canvas.zoomToSelection),
            ("view:grid", "Toggle grid", "View", "background", "grid", writable, lambda: canvas.setGridVisible(not canvas.gridVisible)),
            ("view:minimap", "Toggle minimap", "View", "overview navigator", "focus", writable, lambda: canvas.setMinimapVisible(not canvas.minimapVisible())),
            ("save:project", "Save project workspace", "Save", "persistent durable", "save", writable, canvas.savePersistent),
            ("group:import", "Import reusable subflow", "Group", "template json", "folder", writable, canvas.importSubflowFromDialog),
        ))
        if selected:
            all_locked = all(canvas.objectState(object_id)["locked"] for object_id in selected)
            commands.extend((
                ("object:lock", "Unlock selection" if all_locked else "Lock selection", "Object", "protect movement", "lock", writable, lambda: canvas.lockSelected(not all_locked)),
                ("object:hide", "Hide selection", "Object", "visibility", "eye_off", writable, canvas.hideSelected),
                ("object:isolate", "Isolate selection", "Object", "focus visibility", "focus", True, canvas.isolateSelection),
            ))
        if len(selected_elements) >= 2:
            commands.extend((
                ("group:frame", "Create frame from selection", "Group", "container", "front", writable, lambda: canvas.groupSelected(kind="frame")),
                ("group:swimlane", "Create swimlane from selection", "Group", "container lanes", "grid", writable, lambda: canvas.groupSelected(kind="swimlane")),
                ("group:subflow", "Create reusable subflow", "Group", "container workflow", "node", writable, lambda: canvas.groupSelected(kind="subflow")),
            ))
        if len(selected) == 1 and selected[0] in canvas._groups:
            group_id = selected[0]
            group = canvas._groups[group_id]
            commands.extend((
                ("group:collapse", "Expand group" if group.collapsed else "Collapse group", "Group", "contents visibility", "focus", writable, lambda: canvas.setGroupCollapsed(group_id, not group.collapsed)),
                ("group:fit", "Fit group to contents", "Group", "resize bounds", "fit", writable and not group.collapsed, lambda: canvas.fitGroupToContents(group_id)),
                ("group:remove", "Ungroup selection", "Group", "remove container", "delete", writable, lambda: canvas.removeGroup(group_id)),
            ))
        if canvas.isolatedObjectIds():
            commands.append(("object:clear-isolate", "Clear isolation", "Object", "visibility", "eye", True, canvas.clearIsolation))
        if len(selected) == 1 and selected[0] in canvas._connectors:
            connector_id = selected[0]
            commands.extend((
                ("connector:auto-route", "Route around obstacles", "Connector", "routing obstacle automatic", "focus", writable, lambda: canvas.autoRouteConnector(connector_id)),
                ("connector:add-waypoint", "Add reroute point", "Connector", "routing waypoint", "add", writable, lambda: canvas.addConnectorWaypoint(connector_id)),
                ("connector:clear-waypoints", "Clear reroute points", "Connector", "routing waypoint", "delete", writable and bool(canvas.connector(connector_id).waypoints), lambda: canvas.clearConnectorWaypoints(connector_id)),
            ))
        for alignment in ("left", "hcenter", "right", "top", "vcenter", "bottom"):
            commands.append((
                f"arrange:{alignment}", f"Align {alignment}", "Arrange", "selection",
                f"align_{alignment}", writable and len(selected_elements) >= 2,
                lambda value=alignment: canvas.alignSelected(value),
            ))
        for mode, label in (("width", "Match width"), ("height", "Match height"), ("both", "Match size")):
            commands.append((
                f"arrange:match-{mode}", label, "Arrange", "selection equal size",
                "rectangle", writable and len(selected_elements) >= 2,
                lambda value=mode: canvas.matchSelectedSize(value),
            ))
        layoutable = len(canvas._auto_layout_scope_ids("auto")) >= 2
        for strategy, label in (
            ("layered", "Layered layout"),
            ("tree", "Tree layout"),
            ("radial", "Radial layout"),
            ("force", "Force-directed layout"),
        ):
            commands.append((
                f"layout:{strategy}", label, "Layout",
                "graph arrange hierarchy network auto layout", "node",
                writable and layoutable,
                lambda value=strategy: canvas.autoLayout(value),
            ))
        return commands

    def _refresh(self, _text: str = "") -> None:
        query_words = tuple(word for word in self._search.text().casefold().split() if word)
        self._list.clear()
        self._command_lookup.clear()
        ranked = []
        for index, command in enumerate(self._commands()):
            command_id, label, category, keywords, _icon, _enabled, _callback = command
            searchable = f"{label} {category} {keywords} {command_id}".casefold()
            if any(word not in searchable for word in query_words):
                continue
            query = " ".join(query_words)
            score = 0 if query and label.casefold().startswith(query) else 1 if query_words else 2
            ranked.append((score, index, command))
        ranked.sort(key=lambda value: (value[0], value[1]))
        for _score, _index, command in ranked:
            command_id, label, category, _keywords, icon, enabled, callback = command
            item = QListWidgetItem(_canvas_icon(icon), f"{label}    · {category}")
            item.setData(Qt.ItemDataRole.UserRole, command_id)
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self._list.addItem(item)
            self._command_lookup[command_id] = callback
        if self._list.count():
            self._list.setCurrentRow(0)

    def _activate_current(self) -> None:
        item = self._list.currentItem()
        if item is None or not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return
        callback = self._command_lookup.get(str(item.data(Qt.ItemDataRole.UserRole)))
        if callback is not None:
            self.close()
            callback()


class _CanvasEditorToolbox(QDialog):
    """Floating multi-tab editor for elements, layers, viewport and persistence."""

    def __init__(self, canvas: "MonkezCanva") -> None:
        super().__init__(canvas.window())
        self.canvas = canvas
        self._syncing_layers = False
        self._syncing_inspector = False
        self._syncing_port_editor = False
        self._pending_inspector_fields: set[str] = set()
        self._inspector_apply_timer = QTimer(self)
        self._inspector_apply_timer.setSingleShot(True)
        self._inspector_apply_timer.timeout.connect(self._apply_inspector)
        self.setWindowTitle("MonkezCanva Editor")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(410, 620)
        self.resize(438, 720)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        panel = QFrame()
        panel.setObjectName("canvasEditorPanel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(43, 40, 36, 62))
        panel.setGraphicsEffect(shadow)
        root.addWidget(panel)
        content = QVBoxLayout(panel)
        content.setContentsMargins(16, 13, 16, 12)
        content.setSpacing(9)
        self._pane_header = _CanvasPaneHeader(self, canvas)
        content.addWidget(self._pane_header)
        self._tabs = QTabWidget()
        self._tabs.setObjectName("canvasEditorTabs")
        self._tabs.setDocumentMode(True)
        self._tabs.setIconSize(QSize(16, 16))
        self._tabs.tabBar().setObjectName("canvasEditorTabBar")
        self._tabs.tabBar().setExpanding(True)
        self._tabs.tabBar().setUsesScrollButtons(False)
        self._tabs.addTab(self._elements_tab(), _canvas_icon("rectangle"), "Add")
        self._tabs.addTab(self._inspector_tab(), _canvas_icon("color"), "Inspect")
        self._tabs.addTab(self._layers_tab(), _canvas_icon("front"), "Layers")
        self._tabs.addTab(self._view_tab(), _canvas_icon("grid"), "View")
        self._tabs.addTab(self._save_tab(), _canvas_icon("save"), "Save")
        content.addWidget(self._tabs, 1)
        footer = QFrame()
        footer.setObjectName("canvasPaneFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(8, 7, 8, 2)
        footer_layout.addStretch(1)
        self._footer_icon = QLabel()
        self._footer_icon.setPixmap(_canvas_icon("check", "#0f9f8f").pixmap(19, 19))
        footer_layout.addWidget(self._footer_icon)
        self._footer_status = QLabel("Saved")
        self._footer_status.setObjectName("canvasFooterStatus")
        footer_layout.addWidget(self._footer_status)
        footer_layout.addStretch(1)
        footer.setToolTip("Ctrl+D, E: close editor  •  Del: remove  •  Ctrl+wheel: zoom")
        content.addWidget(footer)
        self.setStyleSheet(self._pane_stylesheet())
        canvas.elementAdded.connect(lambda _element_id: self.refreshLayers())
        canvas.elementRemoved.connect(lambda _element_id: self.refreshLayers())
        canvas.connectorAdded.connect(lambda _connector_id: self.refreshLayers())
        canvas.connectorRemoved.connect(lambda _connector_id: self.refreshLayers())
        canvas.groupAdded.connect(lambda _group_id: self.refreshLayers())
        canvas.groupRemoved.connect(lambda _group_id: self.refreshLayers())
        canvas.selectionChanged.connect(self._sync_inspector)
        canvas.selectionSetChanged.connect(lambda _element_ids: self.refreshLayers())
        canvas.autoSaved.connect(self._show_save_status)
        canvas.documentModifiedChanged.connect(self._sync_modified_status)
        canvas.readOnlyChanged.connect(self._sync_read_only_status)
        canvas.documentChanged.connect(self._sync_view_controls)
        canvas.portRuntimeValueChanged.connect(
            lambda _element_id, _port_id, _value: self._sync_inspector(
                canvas.selectedElementId()
            )
        )
        self._sync_inspector(canvas.selectedElementId())
        self.refreshLayers()
        self._sync_modified_status(canvas.isDocumentModified())
        self._sync_read_only_status(canvas.isReadOnly(), canvas.readOnlyReason())

    @staticmethod
    def _pane_stylesheet() -> str:
        icon_root = Path(__file__).resolve().parent / "monkez_assets" / "icons"
        stylesheet = """
        QFrame#canvasEditorPanel {
            background: #fcfbf9;
            border: 1px solid #d8d5d0;
            border-radius: 20px;
        }
        QFrame#canvasPaneHeader { border: none; border-bottom: 1px solid #ebe7e2; background: transparent; }
        QLabel#canvasPaneBrand { background: #ff6b5f; border-radius: 10px; }
        QLabel#canvasPaneTitle { color: #303941; font-size: 17px; font-weight: 700; }
        QLabel#canvasSelectionBadge {
            color: #8b8b87; background: #f4f2ef; border: 1px solid #e6e2dd;
            border-radius: 11px; padding: 5px 10px; font-size: 10px; font-weight: 600;
        }
        QLabel#canvasSelectionBadge[hasSelection="true"] {
            color: #ef5d50; background: #fff3f0; border-color: #ffd3cc;
        }
        QToolButton#canvasPaneClose, QToolButton#canvasPaneCommand {
            color: #4f5961; background: transparent; border: none;
            border-radius: 9px; min-width: 30px; min-height: 30px; padding: 3px;
        }
        QToolButton#canvasPaneClose:hover { color: #d94e43; background: #fff0ed; }
        QToolButton#canvasPaneCommand:hover { color: #d94e43; background: #fff0ed; }
        QFrame#canvasPaneFooter { border: none; border-top: 1px solid #ebe7e2; background: transparent; }
        QLabel#canvasFooterStatus {
            color: #0f9f8f; background: transparent; font-size: 11px; font-weight: 650;
        }
        QLabel#canvasObjectType {
            color: #ef5d50; background: #fff3f0; border: 1px solid #ffd3cc;
            border-radius: 9px; padding: 6px 10px; font-weight: 700;
        }
        QLabel#canvasSelectionHint { color: #858b90; font-size: 9px; }
        QLabel#autoApplyStatus {
            color: #0f9f8f; background: #effbf8; border: 1px solid #c6eee7;
            border-radius: 9px; padding: 6px 9px; font-size: 9px; font-weight: 600;
        }
        QLabel#canvasPortRuntimeStatus {
            color: #5f6b73; background: #f7f5f2; border: 1px solid #e7e2dc;
            border-radius: 8px; padding: 6px 8px; font-size: 9px;
        }
        QLabel#canvasSaveStatus {
            color: #087f72; background: #effbf8; border: 1px solid #c6eee7;
            border-radius: 10px; padding: 9px;
        }
        QTabWidget#canvasEditorTabs::pane {
            border: none; background: transparent; top: 0px;
        }
        QTabBar#canvasEditorTabBar {
            background: #f3f1ee; border: none; border-radius: 12px;
            padding: 4px; margin: 0px 0px 6px 0px;
        }
        QTabBar#canvasEditorTabBar::tab {
            color: #667079; background: transparent; border: 1px solid transparent;
            border-radius: 9px; min-height: 25px; padding: 5px 3px; margin: 0px;
            font-size: 10px; font-weight: 600;
        }
        QTabBar#canvasEditorTabBar::tab:selected {
            color: #e95549; background: #fffefd; border-color: #ebe5df;
        }
        QTabBar#canvasEditorTabBar::tab:hover:!selected {
            color: #3f474e; background: #f9f7f4; border-color: #eee9e4;
        }
        QGroupBox {
            color: #303941; background: transparent; border: none;
            margin: 0px; padding: 36px 12px 12px 12px;
            font-weight: 600;
        }
        QGroupBox::title {
            color: transparent; background: transparent; border: none;
            padding: 0px; margin: 0px;
        }
        QPushButton, QToolButton {
            color: #3b444b; background: #fffefd; border: 1px solid #ddd9d3;
            border-radius: 9px; padding: 6px 9px; min-height: 27px;
        }
        QPushButton:hover, QToolButton:hover {
            color: #ef5d50; border-color: #ffb7ae; background: #fff4f1;
        }
        QPushButton:pressed, QToolButton:pressed { background: #ffe5df; }
        QPushButton:disabled, QToolButton:disabled { color: #b9b6b1; background: #f3f1ee; }
        QPushButton#primaryAction { color: #ffffff; background: #ff6b5f; border-color: #ff6b5f; font-weight: 650; }
        QPushButton#primaryAction:hover { background: #ef5d50; border-color: #ef5d50; }
        QPushButton#dangerAction { color: #d94e43; background: #fff6f4; border-color: #ffd3cc; }
        QPushButton#dangerAction:hover { background: #ffe9e5; border-color: #ffb7ae; }
        QToolButton#canvasArrangeAction {
            background: transparent; border: none; border-radius: 8px; min-width: 31px; min-height: 31px;
        }
        QToolButton#canvasArrangeAction:hover { background: #fff0ed; }
        QFrame#canvasPaletteTile {
            background: #fffefd; border: 1px solid #e3dfda; border-radius: 10px;
        }
        QFrame#canvasPaletteTile:hover { border-color: #ffc0b8; background: #fff8f6; }
        QToolButton#canvasPaletteAdd {
            color: #3e474e; background: transparent; border: none; border-radius: 7px;
            padding: 5px 3px; min-height: 27px; text-align: left; font-weight: 600;
        }
        QToolButton#canvasPaletteAdd:hover { color: #e95549; background: transparent; }
        QToolButton#canvasPaletteFavorite {
            background: transparent; border: none; border-radius: 7px; padding: 3px;
        }
        QToolButton#canvasPaletteFavorite:hover { background: #fff0d8; }
        QLineEdit#canvasPaletteSearch { padding-left: 7px; }
        QLabel#canvasPaletteCount { color: #8c8984; font-size: 9px; }
        QLineEdit, QDoubleSpinBox, QComboBox, QListWidget {
            color: #303941; background: #fffefd; border: 1px solid #d9d6d1;
            border-radius: 10px; padding: 4px 10px; min-height: 30px;
            selection-background-color: #ffd8d2;
        }
        QLineEdit:hover, QDoubleSpinBox:hover, QComboBox:hover { border-color: #c6c1bb; }
        QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus, QListWidget:focus {
            border: 1px solid #ff8c80; background: #ffffff;
        }
        QLineEdit:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
            color: #aaa6a1; background: #f4f2ef; border-color: #e5e1dc;
        }
        QLineEdit[mixedValue="true"], QDoubleSpinBox[mixedValue="true"] {
            color: #8b8179; background: #faf8f5; border-color: #d7cec5;
        }
        QComboBox { padding-right: 28px; }
        QComboBox::drop-down { background: transparent; border: none; width: 27px; }
        QComboBox::down-arrow {
            image: url(__SPIN_DOWN__); width: 10px; height: 7px;
        }
        QDoubleSpinBox { padding-right: 29px; }
        QDoubleSpinBox::up-button {
            subcontrol-origin: padding; subcontrol-position: top right;
            background: transparent; border: none; border-radius: 6px;
            width: 24px; height: 14px; margin: 3px 3px 0px 0px;
        }
        QDoubleSpinBox::down-button {
            subcontrol-origin: padding; subcontrol-position: bottom right;
            background: transparent; border: none; border-radius: 6px;
            width: 24px; height: 14px; margin: 0px 3px 3px 0px;
        }
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
            background: #fff0ed;
        }
        QDoubleSpinBox::up-arrow {
            image: url(__SPIN_UP__); width: 10px; height: 7px;
        }
        QDoubleSpinBox::down-arrow {
            image: url(__SPIN_DOWN__); width: 10px; height: 7px;
        }
        QCheckBox { color: #3b444b; spacing: 8px; }
        QCheckBox::indicator {
            width: 16px; height: 16px; background: #fffefd;
            border: 1px solid #cfcac4; border-radius: 5px;
        }
        QCheckBox::indicator:hover { border-color: #ff8c80; background: #fff7f5; }
        QCheckBox::indicator:checked { background: #ff6b5f; border-color: #ff6b5f; }
        QListWidget { padding: 4px; }
        QListWidget::item { border-radius: 6px; padding: 7px; margin: 1px; }
        QListWidget::item:selected { color: #d94e43; background: #ffe9e5; }
        QListWidget::item:hover:!selected { background: #f5f2ee; }
        QScrollArea { background: transparent; border: none; }
        QWidget#canvasInspectorBody, QWidget#canvasViewBody { background: transparent; }
        QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
        QScrollBar::handle:vertical { background: #d8d4cf; border-radius: 4px; min-height: 28px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        QLabel { color: #50585f; }
        """
        return (
            stylesheet
            .replace("__SPIN_UP__", (icon_root / "canvas-chevron-up.svg").as_posix())
            .replace("__SPIN_DOWN__", (icon_root / "canvas-chevron-down.svg").as_posix())
        )

    def _elements_tab(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 4, 0, 0)
        page_layout.setSpacing(7)
        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self._palette_search = QLineEdit()
        self._palette_search.setObjectName("canvasPaletteSearch")
        self._palette_search.setPlaceholderText("Search components…")
        self._palette_search.addAction(
            _canvas_icon("search"), QLineEdit.ActionPosition.LeadingPosition
        )
        search_row.addWidget(self._palette_search, 1)
        self._palette_filter = QComboBox()
        self._palette_filter.setMinimumWidth(126)
        self._palette_filter.addItem("All", "all")
        self._palette_filter.addItem("Favorites", "favorites")
        self._palette_filter.addItem("Recent", "recent")
        self._palette_filter.insertSeparator(3)
        for category in self.canvas.elementRegistry().categories():
            self._palette_filter.addItem(category, category)
        search_row.addWidget(self._palette_filter)
        page_layout.addLayout(search_row)
        self._palette_count = QLabel()
        self._palette_count.setObjectName("canvasPaletteCount")
        page_layout.addWidget(self._palette_count)
        self._palette_scroll = QScrollArea()
        self._palette_scroll.setWidgetResizable(True)
        self._palette_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._palette_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._palette_body = QWidget()
        self._palette_body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._palette_grid = QGridLayout(self._palette_body)
        self._palette_grid.setContentsMargins(3, 3, 3, 3)
        self._palette_grid.setHorizontalSpacing(6)
        self._palette_grid.setVerticalSpacing(6)
        self._palette_grid.setColumnStretch(0, 1)
        self._palette_grid.setColumnStretch(1, 1)
        self._palette_scroll.setWidget(self._palette_body)
        page_layout.addWidget(self._palette_scroll, 1)
        connect_selected = QPushButton("Connect 2 selected items")
        connect_selected.setObjectName("primaryAction")
        connect_selected.setIcon(_canvas_icon("connector", "#ffffff"))
        connect_selected.setToolTip("Create a selectable connector between exactly two selected items")
        connect_selected.clicked.connect(self.canvas.connectSelected)
        page_layout.addWidget(connect_selected)
        buttons = QHBoxLayout()
        duplicate = QPushButton("Duplicate")
        duplicate.setIcon(_canvas_icon("duplicate"))
        duplicate.clicked.connect(self.canvas.duplicateSelection)
        delete = QPushButton("Delete")
        delete.setObjectName("dangerAction")
        delete.setIcon(_canvas_icon("delete", "#b91c1c"))
        delete.clicked.connect(self.canvas.deleteSelected)
        buttons.addWidget(duplicate)
        buttons.addWidget(delete)
        page_layout.addLayout(buttons)
        drop_hint = QLabel("Drag PNG, JPG, WebP or GIF files directly onto the canvas.")
        drop_hint.setWordWrap(True)
        drop_hint.setStyleSheet("color: #64748b")
        page_layout.addWidget(drop_hint)
        self._palette_search.textChanged.connect(self._rebuild_element_palette)
        self._palette_filter.currentIndexChanged.connect(self._rebuild_element_palette)
        self.canvas.palettePreferencesChanged.connect(
            lambda _favorites, _recent: self._rebuild_element_palette()
        )
        self._rebuild_element_palette()
        return page

    def _palette_entries(self) -> tuple[PaletteEntry, ...]:
        return tuple(
            PaletteEntry(
                definition.type_id,
                definition.label,
                definition.category,
                definition.icon,
                tuple(definition.capabilities) + (definition.plugin_id,),
            )
            for definition in self.canvas.elementRegistry().definitions()
        )

    def _rebuild_element_palette(self, _value: Any = None) -> None:
        if not hasattr(self, "_palette_grid"):
            return
        while self._palette_grid.count():
            item = self._palette_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        entries = search_palette(
            self._palette_entries(),
            self._palette_search.text(),
            category=str(self._palette_filter.currentData() or "all"),
            favorites=self.canvas.paletteFavorites(),
            recent=self.canvas.paletteRecent(),
        )
        favorites = set(self.canvas.paletteFavorites())
        for index, entry in enumerate(entries):
            definition = self.canvas.elementRegistry().require(entry.type_id)
            tile = _CanvasPaletteTile(
                definition,
                entry.type_id in favorites,
                lambda kind=entry.type_id: self.canvas.addPaletteElement(kind),
                lambda kind=entry.type_id: self.canvas.togglePaletteFavorite(kind),
            )
            self._palette_grid.addWidget(tile, index // 2, index % 2)
        if not entries:
            empty = QLabel("No matching components")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #96918c; padding: 28px")
            self._palette_grid.addWidget(empty, 0, 0, 1, 2)
        self._palette_grid.setRowStretch(max(1, (len(entries) + 1) // 2), 1)
        label = "component" if len(entries) == 1 else "components"
        self._palette_count.setText(f"{len(entries)} {label}")

    def _inspector_tab(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 4, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("canvasInspectorBody")
        body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(7)

        general = _CanvasCardGroup("Selection")
        form = QFormLayout(general)
        self._type_label = QLabel("No selection")
        self._type_label.setObjectName("canvasObjectType")
        self._id_edit = QLineEdit()
        form.addRow("Type", self._type_label)
        form.addRow("Object ID", self._id_edit)
        self._selection_hint = QLabel()
        self._selection_hint.setObjectName("canvasSelectionHint")
        self._selection_hint.setWordWrap(True)
        self._selection_hint.hide()
        form.addRow("", self._selection_hint)
        layout.addWidget(general)

        self._multi_select_group = _CanvasCardGroup("Quick arrange")
        arrange_layout = QHBoxLayout(self._multi_select_group)
        arrange_layout.setContentsMargins(8, 10, 8, 8)
        arrange_layout.setSpacing(3)
        arrange_actions = (
            ("align_left", "Align left", lambda: self.canvas.alignSelected("left")),
            ("align_hcenter", "Align horizontal centers", lambda: self.canvas.alignSelected("hcenter")),
            ("align_right", "Align right", lambda: self.canvas.alignSelected("right")),
            ("align_top", "Align top", lambda: self.canvas.alignSelected("top")),
            ("align_vcenter", "Align vertical centers", lambda: self.canvas.alignSelected("vcenter")),
            ("align_bottom", "Align bottom", lambda: self.canvas.alignSelected("bottom")),
            ("distribute_horizontal", "Distribute horizontally", lambda: self.canvas.distributeSelected("horizontal")),
            ("distribute_vertical", "Distribute vertically", lambda: self.canvas.distributeSelected("vertical")),
            ("rectangle", "Match width", self.canvas.matchSelectedWidth),
            ("rectangle", "Match height", self.canvas.matchSelectedHeight),
            ("rectangle", "Match width and height", self.canvas.matchSelectedDimensions),
        )
        self._arrange_buttons: list[QToolButton] = []
        for icon_name, tooltip, callback in arrange_actions:
            button = QToolButton()
            button.setObjectName("canvasArrangeAction")
            button.setIcon(_canvas_icon(icon_name))
            button.setIconSize(QSize(19, 19))
            button.setFixedSize(30, 32)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked=False, action=callback: action())
            arrange_layout.addWidget(button)
            self._arrange_buttons.append(button)
        arrange_layout.addStretch(1)
        layout.addWidget(self._multi_select_group)

        self._content_group = _CanvasCardGroup("Content")
        content_form = QFormLayout(self._content_group)
        self._text_edit = QLineEdit()
        self._data_edit = QLineEdit()
        self._data_edit.setPlaceholderText("Chart values: 20, 40, 60")
        content_form.addRow("Text / title", self._text_edit)
        self._data_label = QLabel("Data")
        content_form.addRow(self._data_label, self._data_edit)
        layout.addWidget(self._content_group)

        self._ports_group = _CanvasCardGroup("Node ports")
        ports_layout = QVBoxLayout(self._ports_group)
        self._ports_list = QListWidget()
        self._ports_list.setMaximumHeight(112)
        self._ports_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._ports_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._ports_list.itemSelectionChanged.connect(self._load_selected_port)
        ports_layout.addWidget(self._ports_list)
        port_form = QGridLayout()
        self._port_id_edit = QLineEdit()
        self._port_id_edit.setPlaceholderText("port-id")
        self._port_label_edit = QLineEdit()
        self._port_label_edit.setPlaceholderText("Visible label")
        self._port_mode_combo = QComboBox()
        self._port_mode_combo.addItems(("Input", "Output", "Free"))
        self._port_side_combo = QComboBox()
        self._port_side_combo.addItems(("Left", "Right", "Top", "Bottom"))
        self._port_data_type_combo = QComboBox()
        self._port_data_type_combo.setEditable(True)
        self._port_data_type_combo.addItems(
            ("any", "bool", "int", "float", "str", "dict", "list", "bytes")
        )
        self._port_unit_edit = QLineEdit()
        self._port_unit_edit.setPlaceholderText("Unit, e.g. V or °C")
        self._port_required_check = QCheckBox("Required")
        self._port_max_connections_field = QDoubleSpinBox()
        self._port_max_connections_field.setDecimals(0)
        self._port_max_connections_field.setRange(0, 10000)
        self._port_max_connections_field.setSpecialValueText("Unlimited")
        self._port_max_connections_field.setToolTip("0 allows unlimited connectors")
        self._port_accepted_types_edit = QLineEdit()
        self._port_accepted_types_edit.setPlaceholderText("Accepted source types")
        self._port_converts_to_edit = QLineEdit()
        self._port_converts_to_edit.setPlaceholderText("Can convert to…")
        self._port_accepted_units_edit = QLineEdit()
        self._port_accepted_units_edit.setPlaceholderText("Accepted source units")
        self._port_default_edit = QLineEdit()
        self._port_default_edit.setPlaceholderText("Default JSON value")
        self._port_tooltip_edit = QLineEdit()
        self._port_tooltip_edit.setPlaceholderText("Port description / usage hint")
        self._port_runtime_status = QLabel("Runtime · unset")
        self._port_runtime_status.setObjectName("canvasPortRuntimeStatus")
        port_form.addWidget(self._port_id_edit, 0, 0)
        port_form.addWidget(self._port_label_edit, 0, 1)
        port_form.addWidget(self._port_mode_combo, 1, 0)
        port_form.addWidget(self._port_side_combo, 1, 1)
        port_form.addWidget(QLabel("Data type"), 2, 0)
        port_form.addWidget(QLabel("Unit"), 2, 1)
        port_form.addWidget(self._port_data_type_combo, 3, 0)
        port_form.addWidget(self._port_unit_edit, 3, 1)
        port_form.addWidget(self._port_required_check, 4, 0)
        port_form.addWidget(self._port_max_connections_field, 4, 1)
        port_form.addWidget(self._port_accepted_types_edit, 5, 0)
        port_form.addWidget(self._port_converts_to_edit, 5, 1)
        port_form.addWidget(self._port_accepted_units_edit, 6, 0)
        port_form.addWidget(self._port_default_edit, 6, 1)
        port_form.addWidget(self._port_tooltip_edit, 7, 0, 1, 2)
        port_form.addWidget(self._port_runtime_status, 8, 0, 1, 2)
        ports_layout.addLayout(port_form)
        port_actions = QHBoxLayout()
        add_port = QPushButton("Add / update")
        add_port.setIcon(_canvas_icon("check"))
        add_port.clicked.connect(self._safe_upsert_port)
        remove_port = QPushButton("Remove")
        remove_port.setIcon(_canvas_icon("delete"))
        remove_port.clicked.connect(self._remove_port_from_editor)
        port_actions.addWidget(add_port)
        port_actions.addWidget(remove_port)
        ports_layout.addLayout(port_actions)
        for field in (
            self._port_label_edit,
            self._port_unit_edit,
            self._port_accepted_types_edit,
            self._port_accepted_units_edit,
            self._port_converts_to_edit,
            self._port_default_edit,
            self._port_tooltip_edit,
        ):
            field.editingFinished.connect(self._auto_update_selected_port)
        for combo in (
            self._port_mode_combo, self._port_side_combo, self._port_data_type_combo
        ):
            combo.activated.connect(self._auto_update_selected_port)
        self._port_data_type_combo.lineEdit().editingFinished.connect(
            self._auto_update_selected_port
        )
        self._port_required_check.toggled.connect(self._auto_update_selected_port)
        self._port_max_connections_field.valueChanged.connect(
            self._auto_update_selected_port
        )
        layout.addWidget(self._ports_group)

        self._geometry_group = _CanvasCardGroup("Position / size")
        geometry_form = QGridLayout(self._geometry_group)
        geometry_form.setContentsMargins(13, 20, 13, 13)
        geometry_form.setHorizontalSpacing(14)
        geometry_form.setVerticalSpacing(7)
        geometry_form.setColumnStretch(0, 1)
        geometry_form.setColumnStretch(1, 1)
        self._number_fields: dict[str, QDoubleSpinBox] = {}
        self._number_labels: dict[str, QLabel] = {}
        fields = (
            ("x", "X", -100000.0, 100000.0, 1),
            ("y", "Y", -100000.0, 100000.0, 1),
            ("width", "Width", 24.0, 100000.0, 1),
            ("height", "Height", 24.0, 100000.0, 1),
            ("rotation", "Rotation", -3600.0, 3600.0, 1),
            ("opacity", "Opacity", 0.0, 1.0, 2),
            ("z", "Layer Z", -10000.0, 10000.0, 1),
        )
        for index, (key, label, minimum, maximum, decimals) in enumerate(fields):
            field = _CanvasNumberField()
            field.setRange(minimum, maximum)
            field.setDecimals(decimals)
            field.setSingleStep(0.1 if key == "opacity" else 1.0)
            field.setMinimumWidth(0)
            field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._number_fields[key] = field
            label_widget = QLabel(label)
            self._number_labels[key] = label_widget
            column = index % 2
            row = (index // 2) * 2
            geometry_form.addWidget(label_widget, row, column)
            geometry_form.addWidget(field, row + 1, column)
        layout.addWidget(self._geometry_group)

        self._group_properties_group = _CanvasCardGroup("Group / subflow")
        group_form = QFormLayout(self._group_properties_group)
        self._group_kind_combo = QComboBox()
        self._group_kind_combo.addItems(("Frame", "Swimlane", "Subflow"))
        self._group_label_edit = QLineEdit()
        self._group_label_edit.setPlaceholderText("Visible group title")
        self._group_members_edit = QLineEdit()
        self._group_members_edit.setPlaceholderText("node-a, node-b, nested-group")
        self._group_collapsed_check = QCheckBox("Collapse member contents")
        self._group_lanes_edit = QLineEdit()
        self._group_lanes_edit.setPlaceholderText("Lane 1, Lane 2, Lane 3")
        self._group_orientation_combo = QComboBox()
        self._group_orientation_combo.addItems(("Horizontal", "Vertical"))
        group_form.addRow("Type", self._group_kind_combo)
        group_form.addRow("Title", self._group_label_edit)
        group_form.addRow("Members", self._group_members_edit)
        group_form.addRow(self._group_collapsed_check)
        self._group_lanes_label = QLabel("Lanes")
        group_form.addRow(self._group_lanes_label, self._group_lanes_edit)
        self._group_orientation_label = QLabel("Direction")
        group_form.addRow(self._group_orientation_label, self._group_orientation_combo)
        group_actions = QWidget()
        group_actions_layout = QHBoxLayout(group_actions)
        group_actions_layout.setContentsMargins(0, 0, 0, 0)
        group_actions_layout.setSpacing(6)
        fit_group = QPushButton("Fit contents")
        fit_group.setIcon(_canvas_icon("fit"))
        fit_group.clicked.connect(self._fit_selected_group)
        export_group = QPushButton("Export")
        export_group.setIcon(_canvas_icon("save"))
        export_group.setToolTip("Save this group as a reusable JSON subflow template")
        export_group.clicked.connect(self._export_selected_group)
        ungroup = QPushButton("Ungroup")
        ungroup.setObjectName("dangerAction")
        ungroup.setIcon(_canvas_icon("delete"))
        ungroup.clicked.connect(self._ungroup_selected)
        group_actions_layout.addWidget(fit_group)
        group_actions_layout.addWidget(export_group)
        group_actions_layout.addWidget(ungroup)
        group_form.addRow(group_actions)
        layout.insertWidget(layout.indexOf(self._geometry_group), self._group_properties_group)

        self._media_group = _CanvasCardGroup("Media")
        media_layout = QVBoxLayout(self._media_group)
        self._source_edit = QLineEdit()
        self._source_edit.setPlaceholderText("Image or animated GIF source")
        media_layout.addWidget(self._source_edit)
        browse = QPushButton("Browse media…")
        browse.setIcon(_canvas_icon("folder"))
        browse.clicked.connect(self._browse_selected_media)
        media_layout.addWidget(browse)
        layout.addWidget(self._media_group)

        self._stroke_group = _CanvasCardGroup("Line / signal")
        stroke_form = QFormLayout(self._stroke_group)
        self._route_combo = QComboBox()
        self._route_combo.addItems(("Bezier", "Auto", "Orthogonal", "Straight", "Polyline"))
        self._source_combo = QComboBox()
        self._target_combo = QComboBox()
        self._source_port_combo = QComboBox()
        self._target_port_combo = QComboBox()
        for combo in (self._source_combo, self._target_combo):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(12)
        self._source_combo.currentIndexChanged.connect(
            lambda _index: self._refresh_endpoint_port_controls()
        )
        self._target_combo.currentIndexChanged.connect(
            lambda _index: self._refresh_endpoint_port_controls()
        )
        self._line_style_combo = QComboBox()
        self._line_style_combo.addItems(("Solid", "Dash", "Dot", "DashDot"))
        self._line_width_field = QDoubleSpinBox()
        self._line_width_field.setRange(0.5, 40.0)
        self._line_width_field.setDecimals(1)
        self._connector_label_edit = QLineEdit()
        self._connector_label_edit.setPlaceholderText("Optional edge label")
        self._label_position_field = QDoubleSpinBox()
        self._label_position_field.setRange(0.0, 100.0)
        self._label_position_field.setSuffix(" %")
        self._corner_radius_field = QDoubleSpinBox()
        self._corner_radius_field.setRange(0.0, 80.0)
        self._corner_radius_field.setSuffix(" px")
        self._parallel_spacing_field = QDoubleSpinBox()
        self._parallel_spacing_field.setRange(0.0, 120.0)
        self._parallel_spacing_field.setSuffix(" px")
        self._obstacle_clearance_field = QDoubleSpinBox()
        self._obstacle_clearance_field.setRange(0.0, 160.0)
        self._obstacle_clearance_field.setSuffix(" px")
        self._bridge_crossings_check = QCheckBox("Draw bridge over crossings")
        self._bridge_size_field = QDoubleSpinBox()
        self._bridge_size_field.setRange(3.0, 30.0)
        self._bridge_size_field.setSuffix(" px")
        self._bus_style_combo = QComboBox()
        self._bus_style_combo.addItems(("None", "Trunk", "Double"))
        self._bus_width_field = QDoubleSpinBox()
        self._bus_width_field.setRange(2.0, 80.0)
        self._bus_width_field.setSuffix(" px")
        self._bus_id_edit = QLineEdit()
        self._bus_id_edit.setPlaceholderText("Optional shared bus ID")
        self._arrow_start_check = QCheckBox("Start")
        self._arrow_end_check = QCheckBox("End")
        arrow_row = QWidget()
        arrow_layout = QHBoxLayout(arrow_row)
        arrow_layout.setContentsMargins(0, 0, 0, 0)
        arrow_layout.addWidget(self._arrow_start_check)
        arrow_layout.addWidget(self._arrow_end_check)
        self._animated_check = QCheckBox("Enable effect")
        self._effect_combo = QComboBox()
        self._effect_combo.addItems(("Flow", "Pulse", "Glow", "Particles", "Packet"))
        self._flow_speed_field = QDoubleSpinBox()
        self._flow_speed_field.setRange(0.1, 20.0)
        self._flow_speed_field.setDecimals(1)
        self._flow_direction_combo = QComboBox()
        self._flow_direction_combo.addItems(("Forward", "Reverse"))
        self._flow_spacing_field = QDoubleSpinBox()
        self._flow_spacing_field.setRange(1.0, 20.0)
        self._flow_spacing_field.setDecimals(1)
        self._effect_intensity_field = QDoubleSpinBox()
        self._effect_intensity_field.setRange(0.2, 4.0)
        self._effect_intensity_field.setDecimals(1)
        self._effect_intensity_field.setSingleStep(0.1)
        self._packet_loop_check = QCheckBox("Repeat continuously")
        self._packet_duration_field = QDoubleSpinBox()
        self._packet_duration_field.setRange(0.1, 120.0)
        self._packet_duration_field.setDecimals(2)
        self._packet_duration_field.setSuffix(" s")
        self._packet_interval_field = QDoubleSpinBox()
        self._packet_interval_field.setRange(0.05, 120.0)
        self._packet_interval_field.setDecimals(2)
        self._packet_interval_field.setSuffix(" s")
        self._packet_icon_edit = QLineEdit()
        self._packet_icon_edit.setPlaceholderText("Default envelope")
        self._packet_icon_row = QWidget()
        packet_icon_layout = QHBoxLayout(self._packet_icon_row)
        packet_icon_layout.setContentsMargins(0, 0, 0, 0)
        packet_icon_layout.setSpacing(5)
        packet_icon_layout.addWidget(self._packet_icon_edit, 1)
        packet_icon_browse = QToolButton()
        packet_icon_browse.setIcon(_canvas_icon("folder"))
        packet_icon_browse.setToolTip("Choose packet icon")
        packet_icon_browse.clicked.connect(self._choose_packet_icon)
        packet_icon_layout.addWidget(packet_icon_browse)
        self._send_packet_button = QPushButton("Send test packet")
        self._send_packet_button.setIcon(_canvas_icon("send"))
        self._send_packet_button.clicked.connect(self._send_test_packet)
        self._connector_opacity_field = QDoubleSpinBox()
        self._connector_opacity_field.setRange(0.0, 1.0)
        self._connector_opacity_field.setDecimals(2)
        self._connector_z_field = QDoubleSpinBox()
        self._connector_z_field.setRange(-10000.0, 10000.0)
        self._points_edit = QLineEdit()
        self._points_edit.setPlaceholderText("[[x, y], [x, y]]")
        self._waypoint_actions = QWidget()
        waypoint_layout = QHBoxLayout(self._waypoint_actions)
        waypoint_layout.setContentsMargins(0, 0, 0, 0)
        waypoint_layout.setSpacing(5)
        add_waypoint = QPushButton("Add point")
        add_waypoint.setIcon(_canvas_icon("add"))
        add_waypoint.clicked.connect(self._add_selected_waypoint)
        clear_waypoints = QPushButton("Clear")
        clear_waypoints.setIcon(_canvas_icon("delete"))
        clear_waypoints.clicked.connect(self._clear_selected_waypoints)
        waypoint_layout.addWidget(add_waypoint)
        waypoint_layout.addWidget(clear_waypoints)
        self._route_label = QLabel("Route")
        self._source_label = QLabel("Source")
        self._target_label = QLabel("Target")
        self._source_port_label = QLabel("Source port")
        self._target_port_label = QLabel("Target port")
        self._animation_label = QLabel("Animation")
        self._effect_label = QLabel("Effect")
        self._flow_speed_label = QLabel("Flow speed")
        self._flow_direction_label = QLabel("Direction")
        self._flow_spacing_label = QLabel("Spacing")
        self._effect_intensity_label = QLabel("Intensity")
        self._packet_loop_label = QLabel("Loop")
        self._packet_duration_label = QLabel("Travel time")
        self._packet_interval_label = QLabel("Emit every")
        self._packet_icon_label = QLabel("Packet icon")
        self._connector_opacity_label = QLabel("Opacity")
        self._connector_z_label = QLabel("Layer Z")
        self._points_label = QLabel("Waypoints")
        stroke_form.addRow(self._source_label, self._source_combo)
        stroke_form.addRow(self._source_port_label, self._source_port_combo)
        stroke_form.addRow(self._target_label, self._target_combo)
        stroke_form.addRow(self._target_port_label, self._target_port_combo)
        stroke_form.addRow(self._route_label, self._route_combo)
        stroke_form.addRow("Stroke", self._line_style_combo)
        stroke_form.addRow("Width", self._line_width_field)
        self._connector_label_label = QLabel("Edge label")
        self._label_position_label = QLabel("Label position")
        self._corner_radius_label = QLabel("Corner radius")
        self._parallel_spacing_label = QLabel("Parallel spacing")
        self._obstacle_clearance_label = QLabel("Obstacle gap")
        self._bridge_crossings_label = QLabel("Crossings")
        self._bridge_size_label = QLabel("Bridge size")
        self._bus_style_label = QLabel("Bus style")
        self._bus_width_label = QLabel("Bus width")
        self._bus_id_label = QLabel("Bus ID")
        stroke_form.addRow(self._connector_label_label, self._connector_label_edit)
        stroke_form.addRow(self._label_position_label, self._label_position_field)
        stroke_form.addRow(self._corner_radius_label, self._corner_radius_field)
        stroke_form.addRow(self._parallel_spacing_label, self._parallel_spacing_field)
        stroke_form.addRow(self._obstacle_clearance_label, self._obstacle_clearance_field)
        stroke_form.addRow(self._bridge_crossings_label, self._bridge_crossings_check)
        stroke_form.addRow(self._bridge_size_label, self._bridge_size_field)
        stroke_form.addRow(self._bus_style_label, self._bus_style_combo)
        stroke_form.addRow(self._bus_width_label, self._bus_width_field)
        stroke_form.addRow(self._bus_id_label, self._bus_id_edit)
        stroke_form.addRow("Arrowheads", arrow_row)
        stroke_form.addRow(self._animation_label, self._animated_check)
        stroke_form.addRow(self._effect_label, self._effect_combo)
        stroke_form.addRow(self._flow_speed_label, self._flow_speed_field)
        stroke_form.addRow(self._flow_direction_label, self._flow_direction_combo)
        stroke_form.addRow(self._flow_spacing_label, self._flow_spacing_field)
        stroke_form.addRow(self._effect_intensity_label, self._effect_intensity_field)
        stroke_form.addRow(self._packet_loop_label, self._packet_loop_check)
        stroke_form.addRow(self._packet_duration_label, self._packet_duration_field)
        stroke_form.addRow(self._packet_interval_label, self._packet_interval_field)
        stroke_form.addRow(self._packet_icon_label, self._packet_icon_row)
        stroke_form.addRow("", self._send_packet_button)
        stroke_form.addRow(self._connector_opacity_label, self._connector_opacity_field)
        stroke_form.addRow(self._connector_z_label, self._connector_z_field)
        stroke_form.addRow(self._points_label, self._points_edit)
        self._waypoint_actions_label = QLabel("Reroute")
        stroke_form.addRow(self._waypoint_actions_label, self._waypoint_actions)
        layout.addWidget(self._stroke_group)

        self._colors_group = _CanvasCardGroup("Appearance")
        colors = QGridLayout(self._colors_group)
        self._color_buttons: dict[str, QPushButton] = {}
        for column, (label, role) in enumerate(
            (("Accent", "accent"), ("Surface", "background"), ("Text", "text"), ("Flow", "flow"))
        ):
            button = QPushButton(label)
            button.setIcon(_canvas_icon("color"))
            button.clicked.connect(lambda _checked=False, value=role: self._choose_color(value))
            self._color_buttons[role] = button
            colors.addWidget(button, column // 2, column % 2)
        layout.addWidget(self._colors_group)

        self._extension_inspector_host = QWidget()
        self._extension_inspector_layout = QVBoxLayout(self._extension_inspector_host)
        self._extension_inspector_layout.setContentsMargins(0, 0, 0, 0)
        self._extension_inspector_widget: QWidget | None = None
        self._extension_inspector_host.hide()
        layout.insertWidget(2, self._extension_inspector_host)

        auto_apply = QLabel("●  Auto apply is on")
        auto_apply.setObjectName("autoApplyStatus")
        layout.addWidget(auto_apply)
        order = QHBoxLayout()
        front = QPushButton("Bring front")
        front.setIcon(_canvas_icon("front"))
        front.clicked.connect(self.canvas.bringSelectedToFront)
        back = QPushButton("Send back")
        back.setIcon(_canvas_icon("back"))
        back.clicked.connect(self.canvas.sendSelectedToBack)
        order.addWidget(front)
        order.addWidget(back)
        layout.addLayout(order)
        layout.addStretch(1)
        self._connect_inspector_auto_apply()
        self._effect_combo.currentIndexChanged.connect(self._sync_packet_controls)
        scroll.setWidget(body)
        page_layout.addWidget(scroll)
        return page

    def _layers_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(7)
        self._layer_search = QLineEdit()
        self._layer_search.setPlaceholderText("Search objects by ID, type or label…")
        self._layer_search.addAction(
            _canvas_icon("search"), QLineEdit.ActionPosition.LeadingPosition
        )
        self._layer_search.textChanged.connect(self.refreshLayers)
        layout.addWidget(self._layer_search)
        self._layers = QListWidget()
        self._layers.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._layers.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._layers.setWordWrap(True)
        self._layers.itemSelectionChanged.connect(self._select_layers)
        self._layers.itemDoubleClicked.connect(lambda _item: self.canvas.zoomToSelection())
        layout.addWidget(self._layers, 1)
        actions = QHBoxLayout()
        for icon, tooltip, callback in (
            ("lock", "Lock or unlock selected objects", self._toggle_layer_lock),
            ("eye_off", "Hide or show selected objects", self._toggle_layer_visibility),
            ("focus", "Isolate selected objects", self._isolate_layers),
            ("eye", "Show all and clear isolation", self._show_all_layers),
            ("fit", "Zoom to selected objects", self.canvas.zoomToSelection),
        ):
            button = QToolButton()
            button.setIcon(_canvas_icon(icon))
            button.setToolTip(tooltip)
            button.setFixedSize(34, 32)
            button.clicked.connect(lambda _checked=False, action=callback: action())
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        return page

    def _view_tab(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("canvasViewBody")
        body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        navigation = _CanvasCardGroup("Viewport")
        navigation_layout = QGridLayout(navigation)
        actions = (
            ("Zoom out", "zoom_out", self.canvas.zoomOut, 0, 0),
            ("100%", "actual_size", self.canvas.resetZoom, 0, 1),
            ("Zoom in", "zoom_in", self.canvas.zoomIn, 0, 2),
            ("Fit all", "fit", self.canvas.fitContent, 1, 0),
            ("Center", "align_center", self.canvas.centerOnSelection, 1, 1),
            ("Pan mode", "pan", self.canvas.togglePanMode, 1, 2),
        )
        for label, icon, callback, row, column in actions:
            button = QToolButton()
            button.setIcon(_canvas_icon(icon))
            button.setIconSize(QSize(18, 18))
            button.setToolTip(label)
            button.setFixedHeight(34)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(callback)
            navigation_layout.addWidget(button, row, column)
        move_row = QHBoxLayout()
        move_row.addWidget(QLabel("Move"))
        for direction, delta in (
            ("left", (-120, 0)), ("right", (120, 0)),
            ("up", (0, -120)), ("down", (0, 120)),
        ):
            button = QToolButton()
            button.setIcon(_canvas_icon(f"arrow_{direction}"))
            button.setToolTip(f"Move viewport {direction}")
            button.clicked.connect(
                lambda _checked=False, value=delta: self.canvas.moveViewport(*value)
            )
            move_row.addWidget(button)
        move_row.addStretch(1)
        navigation_layout.addLayout(move_row, 2, 0, 1, 3)
        layout.addWidget(navigation)

        auto_layout = _CanvasCardGroup("Auto layout")
        auto_layout_grid = QGridLayout(auto_layout)
        self._layout_strategy_combo = QComboBox()
        for label, value in (
            ("Layered", "layered"), ("Tree", "tree"),
            ("Radial", "radial"), ("Force", "force"),
        ):
            self._layout_strategy_combo.addItem(label, value)
        self._layout_direction_combo = QComboBox()
        for label, value in (
            ("Left → right", "right"), ("Top → bottom", "down"),
            ("Right → left", "left"), ("Bottom → top", "up"),
        ):
            self._layout_direction_combo.addItem(label, value)
        self._layout_scope_combo = QComboBox()
        for label, value in (
            ("Smart scope", "auto"), ("Whole document", "document"),
            ("Selection", "selection"), ("Connected component", "component"),
            ("Selected group", "group"),
        ):
            self._layout_scope_combo.addItem(label, value)
        auto_layout_grid.addWidget(QLabel("Strategy"), 0, 0)
        auto_layout_grid.addWidget(QLabel("Direction"), 0, 1)
        auto_layout_grid.addWidget(self._layout_strategy_combo, 1, 0)
        auto_layout_grid.addWidget(self._layout_direction_combo, 1, 1)
        auto_layout_grid.addWidget(QLabel("Scope"), 2, 0, 1, 2)
        auto_layout_grid.addWidget(self._layout_scope_combo, 3, 0, 1, 2)
        self._layout_node_spacing = QDoubleSpinBox()
        self._layout_node_spacing.setRange(4, 1000)
        self._layout_node_spacing.setValue(48)
        self._layout_node_spacing.setSuffix(" px")
        self._layout_layer_spacing = QDoubleSpinBox()
        self._layout_layer_spacing.setRange(8, 2000)
        self._layout_layer_spacing.setValue(120)
        self._layout_layer_spacing.setSuffix(" px")
        auto_layout_grid.addWidget(QLabel("Node gap"), 4, 0)
        auto_layout_grid.addWidget(QLabel("Layer gap"), 4, 1)
        auto_layout_grid.addWidget(self._layout_node_spacing, 5, 0)
        auto_layout_grid.addWidget(self._layout_layer_spacing, 5, 1)
        self._layout_iterations = QDoubleSpinBox()
        self._layout_iterations.setDecimals(0)
        self._layout_iterations.setRange(10, 2000)
        self._layout_iterations.setValue(180)
        self._layout_iterations.setSingleStep(10)
        self._layout_iterations.setSuffix(" steps")
        self._layout_iterations.setToolTip(
            "Simulation steps used by Force layout; higher values settle more slowly"
        )
        self._layout_iterations_label = QLabel("Force quality")
        auto_layout_grid.addWidget(self._layout_iterations_label, 6, 0, 1, 2)
        auto_layout_grid.addWidget(self._layout_iterations, 7, 0, 1, 2)
        self._layout_preserve_center = QCheckBox("Keep center")
        self._layout_preserve_center.setChecked(True)
        self._layout_fit_groups = QCheckBox("Fit groups")
        self._layout_fit_groups.setChecked(True)
        self._layout_fit_view = QCheckBox("Fit view")
        auto_layout_grid.addWidget(self._layout_preserve_center, 8, 0)
        auto_layout_grid.addWidget(self._layout_fit_groups, 8, 1)
        auto_layout_grid.addWidget(self._layout_fit_view, 9, 0)
        apply_layout = QPushButton("Arrange graph")
        apply_layout.setObjectName("primaryAction")
        apply_layout.setIcon(_canvas_icon("node", "#ffffff"))
        apply_layout.clicked.connect(self._apply_auto_layout_controls)
        auto_layout_grid.addWidget(apply_layout, 10, 0, 1, 2)
        self._layout_strategy_combo.currentIndexChanged.connect(
            self._sync_auto_layout_strategy_controls
        )
        self._sync_auto_layout_strategy_controls()
        layout.addWidget(auto_layout)

        grid_group = _CanvasCardGroup("Grid")
        grid_layout = QGridLayout(grid_group)
        self._grid_visible_check = QCheckBox("Show grid")
        self._grid_visible_check.toggled.connect(self.canvas.setGridVisible)
        grid_layout.addWidget(self._grid_visible_check, 0, 0)
        self._grid_style_combo = QComboBox()
        self._grid_style_combo.addItems(("Lines", "Dots", "Cross"))
        self._grid_style_combo.currentIndexChanged.connect(self.canvas.setGridStyle)
        grid_layout.addWidget(self._grid_style_combo, 0, 1)
        grid_color = QPushButton("Grid color")
        grid_color.setIcon(_canvas_icon("color"))
        grid_color.clicked.connect(self._choose_grid_color)
        grid_layout.addWidget(grid_color, 1, 0, 1, 2)
        layout.addWidget(grid_group)

        snapping = _CanvasCardGroup("Snapping & guides")
        snapping_layout = QGridLayout(snapping)
        self._snap_checks: dict[str, QCheckBox] = {}
        labels = {"grid": "Grid", "edges": "Edges", "centers": "Centers", "ports": "Ports"}
        for index, target in enumerate(SNAP_TARGETS):
            check = QCheckBox(labels[target])
            check.toggled.connect(self._update_snap_targets)
            snapping_layout.addWidget(check, index // 2, index % 2)
            self._snap_checks[target] = check
        self._smart_guides_check = QCheckBox("Show smart guides")
        self._smart_guides_check.toggled.connect(self.canvas.setSmartGuidesVisible)
        snapping_layout.addWidget(self._smart_guides_check, 2, 0)
        self._snap_distance_field = QDoubleSpinBox()
        self._snap_distance_field.setRange(1.0, 40.0)
        self._snap_distance_field.setSuffix(" px")
        self._snap_distance_field.setToolTip("Maximum distance before an item snaps")
        self._snap_distance_field.valueChanged.connect(self.canvas.setSnapDistance)
        snapping_layout.addWidget(self._snap_distance_field, 2, 1)
        layout.addWidget(snapping)

        navigator = _CanvasCardGroup("Navigator")
        navigator_layout = QGridLayout(navigator)
        self._minimap_check = QCheckBox("Show minimap")
        self._minimap_check.toggled.connect(self.canvas.setMinimapVisible)
        navigator_layout.addWidget(self._minimap_check, 0, 0, 1, 2)
        self._bookmark_combo = QComboBox()
        self._bookmark_combo.setPlaceholderText("No saved views")
        navigator_layout.addWidget(self._bookmark_combo, 1, 0, 1, 2)
        for column, (label, icon, callback) in enumerate((
            ("Add", "star", self._add_viewport_bookmark),
            ("Go", "focus", self._go_viewport_bookmark),
            ("Remove", "delete", self._remove_viewport_bookmark),
        )):
            button = QPushButton(label)
            button.setIcon(_canvas_icon(icon))
            button.clicked.connect(callback)
            navigator_layout.addWidget(button, 2, column)
        layout.addWidget(navigator)
        self.canvas.viewportBookmarksChanged.connect(self._sync_viewport_bookmarks)

        background = _CanvasCardGroup("Canvas background")
        background_layout = QGridLayout(background)
        background_color = QPushButton("Background color")
        background_color.setIcon(_canvas_icon("color"))
        background_color.clicked.connect(self._choose_background_color)
        background_layout.addWidget(background_color, 0, 0)
        browse_background = QPushButton("Choose image")
        browse_background.setIcon(_canvas_icon("background"))
        browse_background.clicked.connect(self._choose_background_image)
        background_layout.addWidget(browse_background, 0, 1)
        self._background_path = QLineEdit()
        self._background_path.setReadOnly(True)
        self._background_path.setPlaceholderText("No background image")
        background_layout.addWidget(self._background_path, 1, 0, 1, 2)
        self._background_mode_combo = QComboBox()
        self._background_mode_combo.addItems(("Fit", "Fill", "Scale"))
        self._background_mode_combo.currentIndexChanged.connect(self.canvas.setBackgroundImageMode)
        background_layout.addWidget(self._background_mode_combo, 2, 0)
        clear_background = QPushButton("Clear image")
        clear_background.setIcon(_canvas_icon("delete"))
        clear_background.clicked.connect(lambda _checked=False: self.canvas.setBackgroundImage(""))
        background_layout.addWidget(clear_background, 2, 1)
        layout.addWidget(background)
        layout.addStretch(1)
        scroll.setWidget(body)
        page_layout.addWidget(scroll)
        self._sync_view_controls()
        return page

    def _save_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(7)
        self._save_status = QLabel("Autosave draft: waiting for changes")
        self._save_status.setObjectName("canvasSaveStatus")
        self._save_status.setWordWrap(True)
        layout.addWidget(self._save_status)
        session = _CanvasCardGroup("Current app session")
        session_layout = QVBoxLayout(session)
        save_session = QPushButton("Save session checkpoint")
        save_session.setIcon(_canvas_icon("save"))
        save_session.clicked.connect(self.canvas.saveSession)
        restore_session = QPushButton("Restore session checkpoint")
        restore_session.setIcon(_canvas_icon("refresh"))
        restore_session.clicked.connect(self.canvas.restoreSession)
        session_layout.addWidget(save_session)
        session_layout.addWidget(restore_session)
        layout.addWidget(session)
        persistent = _CanvasCardGroup("Persistent across app restarts")
        persistent_layout = QVBoxLayout(persistent)
        save_persistent = QPushButton("Save persistent now")
        save_persistent.setObjectName("primaryAction")
        save_persistent.setIcon(_canvas_icon("save", "#ffffff"))
        save_persistent.clicked.connect(lambda: self.canvas.savePersistent())
        load_persistent = QPushButton("Load persistent data")
        load_persistent.setIcon(_canvas_icon("folder"))
        load_persistent.clicked.connect(self.canvas.loadPersistent)
        persistent_layout.addWidget(save_persistent)
        persistent_layout.addWidget(load_persistent)
        layout.addWidget(persistent)
        history = _CanvasCardGroup("History")
        history_layout = QHBoxLayout(history)
        self._undo_button = QPushButton("Undo")
        self._undo_button.setIcon(_canvas_icon("undo"))
        self._undo_button.clicked.connect(self.canvas.undo)
        self._redo_button = QPushButton("Redo")
        self._redo_button.setIcon(_canvas_icon("redo"))
        self._redo_button.clicked.connect(self.canvas.redo)
        history_layout.addWidget(self._undo_button)
        history_layout.addWidget(self._redo_button)
        self.canvas.historyChanged.connect(self._sync_history_controls)
        self._sync_history_controls(
            self.canvas.canUndo(), self.canvas.canRedo(),
            self.canvas.undoText(), self.canvas.redoText(),
        )
        layout.addWidget(history)
        path = QLabel(str(self.canvas.persistentPath()))
        path.setWordWrap(True)
        path.setStyleSheet("color: #64748b")
        layout.addWidget(path)
        layout.addStretch(1)
        return page

    def _sync_history_controls(
        self, can_undo: bool, can_redo: bool, undo_text: str, redo_text: str
    ) -> None:
        self._undo_button.setEnabled(can_undo)
        self._redo_button.setEnabled(can_redo)
        self._undo_button.setText(f"Undo {undo_text}" if undo_text else "Undo")
        self._redo_button.setText(f"Redo {redo_text}" if redo_text else "Redo")

    def _choose_media(self, kind: str) -> None:
        pattern = "Animated GIF (*.gif)" if kind == "animated_image" else "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        path, _selected_filter = QFileDialog.getOpenFileName(self, "Add media", "", pattern)
        if path:
            self.canvas.addMedia(path, animated=kind == "animated_image")

    def _choose_color(self, role: str) -> None:
        items = [
            self.canvas.canvasObject(object_id)
            for object_id in self.canvas.selectedObjectIds()
        ]
        items = [item for item in items if item is not None]
        item = items[0] if items else None
        if item is None:
            return
        if isinstance(item, _CanvasConnector):
            current = item.flow_color if role == "flow" else item.color
        elif isinstance(item, _CanvasGroup):
            current = item.background if role == "background" else item.color
        else:
            current = (
                item.flow_color if role == "flow" and item.kind == "line"
                else item.background if role == "background"
                else item.text_color if role == "text"
                else item.color
            )
        chosen = QColorDialog.getColor(current, self, f"Choose {role} color")
        if chosen.isValid():
            use_macro = len(items) > 1
            if use_macro:
                self.canvas.beginCommandMacro(f"Set color on {len(items)} objects")
            try:
                for target in items:
                    if isinstance(target, _CanvasConnector):
                        key = "flowColor" if role == "flow" else "color"
                        self.canvas.updateConnector(target.connector_id, **{key: chosen})
                    elif isinstance(target, _CanvasGroup):
                        key = "background" if role in ("background", "surface") else "color"
                        self.canvas.updateGroup(target.group_id, **{key: chosen})
                    else:
                        key = (
                            "flowColor" if role == "flow" and target.kind == "line"
                            else "background" if role in ("background", "surface")
                            else "textColor" if role in ("text", "foreground")
                            else "color"
                        )
                        self.canvas.updateElement(target.element_id, **{key: chosen})
            finally:
                if use_macro:
                    self.canvas.endCommandMacro()

    def _choose_grid_color(self) -> None:
        chosen = QColorDialog.getColor(self.canvas.gridColor, self, "Choose grid color")
        if chosen.isValid():
            self.canvas.setGridColor(chosen)

    def _apply_auto_layout_controls(self) -> None:
        try:
            self.canvas.autoLayout(
                str(self._layout_strategy_combo.currentData()),
                str(self._layout_direction_combo.currentData()),
                scope=str(self._layout_scope_combo.currentData()),
                node_spacing=self._layout_node_spacing.value(),
                layer_spacing=self._layout_layer_spacing.value(),
                iterations=int(self._layout_iterations.value()),
                preserve_center=self._layout_preserve_center.isChecked(),
                fit_groups=self._layout_fit_groups.isChecked(),
                fit_view=self._layout_fit_view.isChecked(),
            )
        except (KeyError, PermissionError, TypeError, ValueError) as error:
            self.canvas.diagnosticMessage.emit(f"Auto-layout rejected: {error}")

    def _sync_auto_layout_strategy_controls(self) -> None:
        force = self._layout_strategy_combo.currentData() == "force"
        self._layout_iterations_label.setVisible(force)
        self._layout_iterations.setVisible(force)
        self._layout_direction_combo.setEnabled(
            self._layout_strategy_combo.currentData() in ("layered", "tree")
        )

    def _choose_background_color(self) -> None:
        chosen = QColorDialog.getColor(self.canvas.backgroundColor, self, "Choose canvas background")
        if chosen.isValid():
            self.canvas.setBackgroundColor(chosen)

    def _choose_background_image(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose canvas background image",
            self.canvas.getBackgroundImage(),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if path:
            self.canvas.setBackgroundImage(path)

    def _choose_packet_icon(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self, "Choose packet icon", self._packet_icon_edit.text(),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.svg)",
        )
        if path:
            self._packet_icon_edit.setText(path)
            self._schedule_inspector_apply(0)

    def _send_test_packet(self) -> None:
        object_id = self.canvas.selectedElementId()
        if object_id:
            self.canvas.send_a_message(
                object_id,
                icon=self._packet_icon_edit.text(),
                travel_time=self._packet_duration_field.value(),
            )

    def _add_selected_waypoint(self) -> None:
        object_id = self.canvas.selectedElementId()
        if self.canvas.connector(object_id) is not None:
            self.canvas.addConnectorWaypoint(object_id)

    def _clear_selected_waypoints(self) -> None:
        object_id = self.canvas.selectedElementId()
        if self.canvas.connector(object_id) is not None:
            self.canvas.clearConnectorWaypoints(object_id)

    def _sync_view_controls(self) -> None:
        widgets = (
            self._grid_visible_check,
            self._grid_style_combo,
            self._background_path,
            self._background_mode_combo,
            self._smart_guides_check,
            self._snap_distance_field,
            self._minimap_check,
            *self._snap_checks.values(),
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
        self._grid_visible_check.setChecked(self.canvas.gridVisible)
        self._grid_style_combo.setCurrentIndex(self.canvas.getGridStyle())
        self._background_path.setText(self.canvas.getBackgroundImage())
        self._background_mode_combo.setCurrentIndex(self.canvas.getBackgroundImageMode())
        enabled_targets = set(self.canvas.snapTargets())
        for target, check in self._snap_checks.items():
            check.setChecked(target in enabled_targets)
        self._smart_guides_check.setChecked(self.canvas.smartGuidesVisible())
        self._snap_distance_field.setValue(self.canvas.snapDistance())
        self._minimap_check.setChecked(self.canvas.minimapVisible())
        self._sync_viewport_bookmarks()
        del blockers

    def _update_snap_targets(self, _checked: bool = False) -> None:
        self.canvas.setSnapTargets(
            target for target, check in self._snap_checks.items() if check.isChecked()
        )

    def _sync_viewport_bookmarks(self, _bookmarks=None) -> None:
        current = self._bookmark_combo.currentData()
        blocker = QSignalBlocker(self._bookmark_combo)
        self._bookmark_combo.clear()
        for bookmark in self.canvas.viewportBookmarks():
            self._bookmark_combo.addItem(bookmark["label"], bookmark["id"])
        index = self._bookmark_combo.findData(current)
        self._bookmark_combo.setCurrentIndex(index if index >= 0 else (0 if self._bookmark_combo.count() else -1))
        del blocker

    def _add_viewport_bookmark(self) -> None:
        bookmark_id = self.canvas.addViewportBookmark()
        self._sync_viewport_bookmarks()
        self._bookmark_combo.setCurrentIndex(self._bookmark_combo.findData(bookmark_id))

    def _go_viewport_bookmark(self) -> None:
        bookmark_id = self._bookmark_combo.currentData()
        if bookmark_id:
            self.canvas.goToViewportBookmark(str(bookmark_id))

    def _remove_viewport_bookmark(self) -> None:
        bookmark_id = self._bookmark_combo.currentData()
        if bookmark_id:
            self.canvas.removeViewportBookmark(str(bookmark_id))

    def _browse_selected_media(self) -> None:
        item = self.canvas.element(self.canvas.selectedElementId())
        if item is None or item.kind not in ("image", "animated_image"):
            return
        path, _selected_filter = QFileDialog.getOpenFileName(
            self, "Choose media", item.source, "Media (*.png *.jpg *.jpeg *.bmp *.webp *.gif)"
        )
        if path:
            self._source_edit.setText(path)
            self._apply_inspector()

    def _fit_selected_group(self) -> None:
        item = self.canvas.canvasObject(self.canvas.selectedElementId())
        if isinstance(item, _CanvasGroup):
            self.canvas.fitGroupToContents(item.group_id)

    def _ungroup_selected(self) -> None:
        item = self.canvas.canvasObject(self.canvas.selectedElementId())
        if isinstance(item, _CanvasGroup):
            self.canvas.removeGroup(item.group_id)

    def _export_selected_group(self) -> None:
        item = self.canvas.canvasObject(self.canvas.selectedElementId())
        if not isinstance(item, _CanvasGroup):
            return
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export reusable subflow",
            f"{item.group_id}.monkez-subflow.json",
            "Monkez subflow (*.monkez-subflow.json *.json)",
        )
        if path:
            self.canvas.saveSubflowTemplate(item.group_id, path)

    def _connect_inspector_auto_apply(self) -> None:
        for key, field in (
            ("text", self._text_edit), ("data", self._data_edit),
            ("source", self._source_edit), ("points", self._points_edit),
            ("packetIcon", self._packet_icon_edit),
            ("connectorLabel", self._connector_label_edit),
            ("busId", self._bus_id_edit),
            ("groupLabel", self._group_label_edit),
            ("groupMembers", self._group_members_edit),
            ("groupLanes", self._group_lanes_edit),
        ):
            field.textEdited.connect(
                lambda _text, name=key: self._schedule_inspector_apply(150, name)
            )
        self._id_edit.editingFinished.connect(
            lambda: self._schedule_inspector_apply(0, "id")
        )
        numeric_fields = {
            **{f"geometry:{key}": field for key, field in self._number_fields.items()},
            "lineWidth": self._line_width_field,
            "flowSpeed": self._flow_speed_field,
            "flowSpacing": self._flow_spacing_field,
            "effectIntensity": self._effect_intensity_field,
            "packetDuration": self._packet_duration_field,
            "packetInterval": self._packet_interval_field,
            "connectorOpacity": self._connector_opacity_field,
            "connectorZ": self._connector_z_field,
            "labelPosition": self._label_position_field,
            "cornerRadius": self._corner_radius_field,
            "parallelSpacing": self._parallel_spacing_field,
            "obstacleClearance": self._obstacle_clearance_field,
            "bridgeSize": self._bridge_size_field,
            "busWidth": self._bus_width_field,
        }
        for key, field in numeric_fields.items():
            field.valueChanged.connect(
                lambda _value, name=key: self._schedule_inspector_apply(0, name)
            )
        for combo in (
            self._source_combo, self._target_combo, self._source_port_combo,
            self._target_port_combo, self._route_combo, self._line_style_combo,
            self._effect_combo, self._flow_direction_combo, self._bus_style_combo,
            self._group_kind_combo, self._group_orientation_combo,
        ):
            combo.currentIndexChanged.connect(
                lambda _index: self._schedule_inspector_apply(0, "choice")
            )
        for check in (
            self._arrow_start_check, self._arrow_end_check, self._animated_check,
            self._packet_loop_check,
            self._bridge_crossings_check,
            self._group_collapsed_check,
        ):
            check.toggled.connect(
                lambda _checked: self._schedule_inspector_apply(0, "choice")
            )

    def _schedule_inspector_apply(self, delay: int = 80, field: str = "") -> None:
        if (
            not self._syncing_inspector
            and not self.canvas.isReadOnly()
            and self.canvas.selectedElementId()
        ):
            if field:
                self._pending_inspector_fields.add(str(field))
            if int(delay) <= 0:
                self._inspector_apply_timer.stop()
                self._apply_inspector()
            else:
                self._inspector_apply_timer.start(int(delay))

    def _sync_packet_controls(self, _index: int = -1) -> None:
        visible = self._effect_combo.currentText().lower() == "packet"
        self._animation_label.setVisible(not visible)
        self._animated_check.setVisible(not visible)
        for widget in (
            self._packet_loop_label, self._packet_loop_check,
            self._packet_duration_label, self._packet_duration_field,
            self._packet_interval_label, self._packet_interval_field,
            self._packet_icon_label, self._packet_icon_row, self._send_packet_button,
        ):
            widget.setVisible(visible)

    def _apply_inspector(self) -> None:
        if self._syncing_inspector:
            return
        try:
            self._apply_inspector_values()
        except (KeyError, PermissionError, TypeError, ValueError) as error:
            self.canvas.diagnosticMessage.emit(f"Inspector change rejected: {error}")
        finally:
            self._pending_inspector_fields.clear()

    def _apply_inspector_values(self) -> None:
        selected_ids = self.canvas.selectedObjectIds()
        if len(selected_ids) > 1:
            self._apply_multi_inspector_values(selected_ids)
            return
        element_id = self.canvas.selectedElementId()
        if not element_id:
            return
        item = self.canvas.canvasObject(element_id)
        if item is None:
            return
        if isinstance(item, _CanvasGroup):
            requested_id = self._id_edit.text().strip()
            if requested_id and requested_id != item.group_id:
                element_id = self.canvas.renameGroup(item.group_id, requested_id)
                item = self.canvas.group(element_id)
            lanes = [
                value.strip()
                for value in self._group_lanes_edit.text().split(",")
                if value.strip()
            ]
            members = [
                value.strip()
                for value in self._group_members_edit.text().split(",")
                if value.strip()
            ]
            values = {key: field.value() for key, field in self._number_fields.items()}
            delta = QPointF(
                values.pop("x") - item.pos().x(),
                values.pop("y") - item.pos().y(),
            )
            moving = not math.isclose(delta.x(), 0.0) or not math.isclose(delta.y(), 0.0)
            if moving:
                self.canvas.beginCommandMacro("Edit group")
            try:
                if moving:
                    self.canvas._commit_group_move(item.group_id, delta)
                self.canvas.updateGroup(
                item.group_id,
                    kind=self._group_kind_combo.currentText().lower(),
                    label=self._group_label_edit.text(),
                    members=members,
                    collapsed=self._group_collapsed_check.isChecked(),
                    lanes=lanes,
                    orientation=self._group_orientation_combo.currentText().lower(),
                    **values,
                )
            finally:
                if moving:
                    self.canvas.endCommandMacro()
            self.refreshLayers()
            return
        requested_id = self._id_edit.text().strip()
        if requested_id and requested_id != element_id:
            element_id = (
                self.canvas.renameConnector(element_id, requested_id)
                if isinstance(item, _CanvasConnector)
                else self.canvas.renameElement(element_id, requested_id)
            )
        points = self._parse_points(self._points_edit.text())
        if isinstance(item, _CanvasConnector):
            source_id = self._source_combo.currentData()
            target_id = self._target_combo.currentData()
            if source_id and target_id:
                self.canvas.reconnectConnector(
                    element_id,
                    str(source_id),
                    str(target_id),
                    str(self._source_port_combo.currentData() or ""),
                    str(self._target_port_combo.currentData() or ""),
                )
            self.canvas.updateConnector(
                element_id,
                route=self._route_combo.currentText().lower(),
                lineStyle=self._line_style_combo.currentText().lower(),
                lineWidth=self._line_width_field.value(),
                arrowStart=self._arrow_start_check.isChecked(),
                arrowEnd=self._arrow_end_check.isChecked(),
                animated=self._animated_check.isChecked(),
                animationEffect=self._effect_combo.currentText().lower(),
                flowSpeed=self._flow_speed_field.value(),
                flowDirection=self._flow_direction_combo.currentText().lower(),
                flowSpacing=self._flow_spacing_field.value(),
                effectIntensity=self._effect_intensity_field.value(),
                packetLoop=self._packet_loop_check.isChecked(),
                packetDuration=self._packet_duration_field.value(),
                packetInterval=self._packet_interval_field.value(),
                packetIcon=self._packet_icon_edit.text(),
                opacity=self._connector_opacity_field.value(),
                z=self._connector_z_field.value(),
                waypoints=points,
                label=self._connector_label_edit.text(),
                labelPosition=self._label_position_field.value() / 100.0,
                cornerRadius=self._corner_radius_field.value(),
                parallelSpacing=self._parallel_spacing_field.value(),
                obstacleClearance=self._obstacle_clearance_field.value(),
                bridgeCrossings=self._bridge_crossings_check.isChecked(),
                bridgeSize=self._bridge_size_field.value(),
                busStyle=self._bus_style_combo.currentText().lower(),
                busWidth=self._bus_width_field.value(),
                busId=self._bus_id_edit.text(),
            )
        else:
            values = {key: field.value() for key, field in self._number_fields.items()}
            values["text"] = self._text_edit.text()
            if item.supports_ports:
                self.canvas.setNodePorts(element_id, self._ports_from_editor())
            if item.kind in ("image", "animated_image"):
                values["source"] = self._source_edit.text()
            if item.kind in ("bar_chart", "line_chart"):
                values["data"] = self._parse_values(self._data_edit.text())
            if item.kind == "line":
                values.update(
                    lineStyle=self._line_style_combo.currentText().lower(),
                    lineWidth=self._line_width_field.value(),
                    arrowStart=self._arrow_start_check.isChecked(),
                    arrowEnd=self._arrow_end_check.isChecked(),
                    animated=self._animated_check.isChecked(),
                    animationEffect=self._effect_combo.currentText().lower(),
                    flowSpeed=self._flow_speed_field.value(),
                    flowDirection=self._flow_direction_combo.currentText().lower(),
                    flowSpacing=self._flow_spacing_field.value(),
                    effectIntensity=self._effect_intensity_field.value(),
                    packetLoop=self._packet_loop_check.isChecked(),
                    packetDuration=self._packet_duration_field.value(),
                    packetInterval=self._packet_interval_field.value(),
                    packetIcon=self._packet_icon_edit.text(),
                )
                values["points"] = points
            self.canvas.updateElement(element_id, **values)
        self.refreshLayers()

    def _apply_multi_inspector_values(self, selected_ids: list[str]) -> None:
        element_ids = [
            object_id for object_id in selected_ids
            if self.canvas.element(object_id) is not None
        ]
        if len(element_ids) != len(selected_ids):
            return
        values: dict[str, Any] = {}
        for key, field in self._number_fields.items():
            if f"geometry:{key}" in self._pending_inspector_fields:
                values[key] = field.value()
        if "text" in self._pending_inspector_fields and self._content_group.isVisible():
            values["text"] = self._text_edit.text()
        if not values:
            return
        self.canvas.beginCommandMacro(f"Edit {len(element_ids)} objects")
        try:
            for element_id in element_ids:
                self.canvas.updateElement(element_id, **values)
        finally:
            self.canvas.endCommandMacro()
        self.refreshLayers()

    @staticmethod
    def _set_mixed_field(widget: QLineEdit | QDoubleSpinBox, values: list[Any]) -> None:
        mixed = any(value != values[0] for value in values[1:])
        if isinstance(widget, _CanvasNumberField):
            widget.setMixedValue(mixed, float(values[0]))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(values[0]))
        else:
            widget.setProperty("mixedValue", mixed)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.setText("" if mixed else str(values[0]))
            widget.setPlaceholderText("Mixed" if mixed else "")

    def _sync_multi_inspector(self, items: list[_CanvasElement | _CanvasConnector]) -> None:
        count = len(items)
        elements = [item for item in items if isinstance(item, _CanvasElement)]
        homogeneous_elements = len(elements) == count
        kinds = {item.kind for item in items}
        self._type_label.setText(
            f"{count} × {next(iter(kinds))}" if len(kinds) == 1
            else f"{count} mixed objects"
        )
        self._id_edit.clear()
        self._id_edit.setPlaceholderText("Multiple IDs")
        self._id_edit.setEnabled(False)
        self._selection_hint.setText(
            "Only common properties are shown. Mixed values stay unchanged until you edit the field."
        )
        self._selection_hint.show()
        self._ports_group.hide()
        self._media_group.hide()
        self._stroke_group.hide()
        self._content_group.setVisible(homogeneous_elements and len(kinds) == 1)
        self._geometry_group.setVisible(homogeneous_elements)
        self._colors_group.setVisible(homogeneous_elements)
        self._data_label.hide()
        self._data_edit.hide()
        if not homogeneous_elements:
            return
        self._set_mixed_field(self._text_edit, [item.text for item in elements])
        geometry_values = {
            "x": [item.pos().x() for item in elements],
            "y": [item.pos().y() for item in elements],
            "width": [item._rect.width() for item in elements],
            "height": [item._rect.height() for item in elements],
            "rotation": [item.rotation() for item in elements],
            "opacity": [item.opacity() for item in elements],
            "z": [item.zValue() for item in elements],
        }
        for key, values in geometry_values.items():
            self._set_mixed_field(self._number_fields[key], values)
        all_lines = all(item.kind == "line" for item in elements)
        self._color_buttons["background"].setVisible(not all_lines)
        self._color_buttons["text"].setVisible(not all_lines)
        self._color_buttons["flow"].setVisible(all_lines)

    def _sync_inspector(self, element_id: str) -> None:
        self._syncing_inspector = True
        self._pending_inspector_fields.clear()
        self._inspector_apply_timer.stop()
        selected_ids = self.canvas.selectedObjectIds()
        items = [self.canvas.canvasObject(object_id) for object_id in selected_ids]
        items = [item for item in items if item is not None]
        item = self.canvas.canvasObject(element_id)
        selected_count = len(items)
        selected_element_count = len(self.canvas.selectedElementIds())
        self._multi_select_group.setVisible(selected_element_count >= 2)
        for index, button in enumerate(self._arrange_buttons):
            button.setEnabled(selected_element_count >= (3 if index >= 6 else 2))
        widgets = [
            self._id_edit, self._text_edit, self._data_edit, self._source_edit,
            self._ports_list, self._port_id_edit, self._port_label_edit,
            self._port_mode_combo, self._port_side_combo,
            self._port_data_type_combo, self._port_unit_edit,
            self._port_required_check, self._port_max_connections_field,
            self._port_accepted_types_edit, self._port_accepted_units_edit,
            self._port_converts_to_edit, self._port_default_edit,
            self._port_tooltip_edit,
            self._source_combo, self._target_combo,
            self._source_port_combo, self._target_port_combo, self._route_combo,
            self._line_style_combo, self._line_width_field,
            self._arrow_start_check, self._arrow_end_check, self._animated_check,
            self._effect_combo, self._flow_speed_field, self._flow_direction_combo,
            self._flow_spacing_field, self._effect_intensity_field,
            self._packet_loop_check, self._packet_duration_field,
            self._packet_interval_field, self._packet_icon_edit,
            self._connector_opacity_field,
            self._connector_z_field, self._points_edit, self._connector_label_edit,
            self._label_position_field, self._corner_radius_field,
            self._parallel_spacing_field, self._obstacle_clearance_field,
            self._bridge_crossings_check, self._bridge_size_field,
            self._bus_style_combo, self._bus_width_field, self._bus_id_edit,
            self._group_kind_combo, self._group_label_edit,
            self._group_members_edit,
            self._group_collapsed_check, self._group_lanes_edit,
            self._group_orientation_combo,
            *self._number_fields.values(),
        ]
        blockers = [QSignalBlocker(widget) for widget in widgets]
        for field in (self._text_edit, *self._number_fields.values()):
            if isinstance(field, _CanvasNumberField):
                field.setMixedValue(False)
            else:
                field.setProperty("mixedValue", False)
                field.style().unpolish(field)
                field.style().polish(field)
        self._text_edit.setPlaceholderText("")
        if selected_count == 0 or item is None:
            self._type_label.setText("No selection")
            self._id_edit.setEnabled(True)
            self._id_edit.setPlaceholderText("")
            self._selection_hint.hide()
            self._id_edit.clear()
            self._text_edit.clear()
            self._data_edit.clear()
            self._source_edit.clear()
            self._content_group.hide()
            self._ports_group.hide()
            self._geometry_group.hide()
            self._media_group.hide()
            self._stroke_group.hide()
            self._colors_group.hide()
            self._group_properties_group.hide()
        elif selected_count > 1:
            self._group_properties_group.hide()
            self._sync_multi_inspector(items)
        else:
            self._id_edit.setEnabled(True)
            self._id_edit.setPlaceholderText("")
            self._selection_hint.hide()
            self._type_label.setText(item.kind)
            self._id_edit.setText(item.element_id)
            if isinstance(item, _CanvasGroup):
                self._id_edit.setEnabled(True)
                self._content_group.hide()
                self._ports_group.hide()
                self._media_group.hide()
                self._stroke_group.hide()
                self._group_properties_group.show()
                self._geometry_group.show()
                self._colors_group.show()
                self._color_buttons["background"].show()
                self._color_buttons["text"].hide()
                self._color_buttons["flow"].hide()
                self._group_kind_combo.setCurrentText(item.kind.title())
                self._group_label_edit.setText(item.text)
                self._group_members_edit.setText(", ".join(item.members))
                self._group_collapsed_check.setChecked(item.collapsed)
                self._group_lanes_edit.setText(", ".join(item.lanes))
                self._group_orientation_combo.setCurrentText(item.orientation.title())
                swimlane = item.kind == "swimlane"
                self._group_lanes_label.setVisible(swimlane)
                self._group_lanes_edit.setVisible(swimlane)
                self._group_orientation_label.setVisible(swimlane)
                self._group_orientation_combo.setVisible(swimlane)
                values = {
                    "x": item.pos().x(), "y": item.pos().y(),
                    "width": item._rect.width(), "height": item._rect.height(),
                    "rotation": item.rotation(), "opacity": item.opacity(), "z": item.zValue(),
                }
                for key, value in values.items():
                    self._number_fields[key].setValue(value)
                del blockers
                self._sync_extension_inspector(None)
                self._syncing_inspector = False
                self._sync_packet_controls()
                return
            self._group_properties_group.hide()
            connector = isinstance(item, _CanvasConnector)
            definition = None if connector else self.canvas.elementRegistry().definition(item.kind)
            capabilities = (
                definition.capabilities
                if definition is not None and definition.capabilities
                else frozenset({"content", "geometry", "appearance"})
            )
            media = not connector and "media" in capabilities
            chart = not connector and "chart" in capabilities
            line = not connector and "signal" in capabilities
            content = not connector and "content" in capabilities
            self._content_group.setVisible(content)
            self._ports_group.setVisible(not connector and "ports" in capabilities)
            self._geometry_group.setVisible(not connector and "geometry" in capabilities)
            self._media_group.setVisible(media)
            self._stroke_group.setVisible(connector or line)
            self._colors_group.setVisible(connector or "appearance" in capabilities)
            self._color_buttons["background"].setVisible(not connector and not line)
            self._color_buttons["text"].setVisible(content)
            self._color_buttons["flow"].setVisible(connector or line)
            self._route_combo.setEnabled(connector)
            for widget in (self._source_label, self._source_combo, self._source_port_label,
                           self._source_port_combo, self._target_label, self._target_combo,
                           self._target_port_label, self._target_port_combo,
                           self._route_label, self._route_combo, self._connector_opacity_label,
                           self._connector_opacity_field, self._connector_z_label, self._connector_z_field,
                           self._connector_label_label, self._connector_label_edit,
                           self._label_position_label, self._label_position_field,
                           self._corner_radius_label, self._corner_radius_field,
                           self._parallel_spacing_label, self._parallel_spacing_field,
                           self._obstacle_clearance_label, self._obstacle_clearance_field,
                           self._bridge_crossings_label, self._bridge_crossings_check,
                           self._bridge_size_label, self._bridge_size_field,
                           self._bus_style_label, self._bus_style_combo,
                           self._bus_width_label, self._bus_width_field,
                           self._bus_id_label, self._bus_id_edit,
                           self._waypoint_actions_label, self._waypoint_actions):
                widget.setVisible(connector)
            for widget in (
                self._animation_label, self._animated_check, self._effect_label,
                self._effect_combo, self._flow_speed_label, self._flow_speed_field,
                self._flow_direction_label, self._flow_direction_combo,
                self._flow_spacing_label, self._flow_spacing_field,
                self._effect_intensity_label, self._effect_intensity_field,
            ):
                widget.setVisible(connector or line)
            show_points = connector or line
            self._points_label.setVisible(show_points)
            self._points_edit.setVisible(show_points)
            if connector:
                self._source_combo.clear()
                self._target_combo.clear()
                for candidate_id in self.canvas.elements():
                    candidate = self.canvas.element(candidate_id)
                    label = f"{candidate_id}  ·  {candidate.kind}"
                    self._source_combo.addItem(label, candidate_id)
                    self._target_combo.addItem(label, candidate_id)
                self._source_combo.setCurrentIndex(self._source_combo.findData(item.source.element_id))
                self._target_combo.setCurrentIndex(self._target_combo.findData(item.target.element_id))
                self._refresh_endpoint_port_controls(item.source_port, item.target_port)
                routes = ("bezier", "auto", "orthogonal", "straight", "polyline")
                styles = ("solid", "dash", "dot", "dashdot")
                self._route_combo.setCurrentIndex(routes.index(item.route) if item.route in routes else 0)
                self._line_style_combo.setCurrentIndex(styles.index(item.line_style) if item.line_style in styles else 0)
                self._line_width_field.setValue(item.line_width)
                self._arrow_start_check.setChecked(item.arrow_start)
                self._arrow_end_check.setChecked(item.arrow_end)
                self._animated_check.setChecked(item.animated)
                self._effect_combo.setCurrentIndex(_LINE_EFFECTS.index(item.animation_effect) if item.animation_effect in _LINE_EFFECTS else 0)
                self._flow_speed_field.setValue(item.flow_speed)
                self._flow_direction_combo.setCurrentIndex(1 if item.flow_direction < 0 else 0)
                self._flow_spacing_field.setValue(item.flow_spacing)
                self._effect_intensity_field.setValue(item.effect_intensity)
                self._packet_loop_check.setChecked(item.packet_loop)
                self._packet_duration_field.setValue(item.packet_duration)
                self._packet_interval_field.setValue(item.packet_interval)
                self._packet_icon_edit.setText(item.packet_icon)
                self._connector_opacity_field.setValue(item.opacity())
                self._connector_z_field.setValue(item.zValue())
                self._connector_label_edit.setText(item.label)
                self._label_position_field.setValue(item.label_position * 100.0)
                self._corner_radius_field.setValue(item.corner_radius)
                self._parallel_spacing_field.setValue(item.parallel_spacing)
                self._obstacle_clearance_field.setValue(item.obstacle_clearance)
                self._bridge_crossings_check.setChecked(item.bridge_crossings)
                self._bridge_size_field.setValue(item.bridge_size)
                self._bus_style_combo.setCurrentIndex(
                    ("none", "trunk", "double").index(item.bus_style)
                    if item.bus_style in ("none", "trunk", "double") else 0
                )
                self._bus_width_field.setValue(item.bus_width)
                self._bus_id_edit.setText(item.bus_id)
                self._points_edit.setText(json.dumps([[point.x(), point.y()] for point in item.waypoints]))
            else:
                self._text_edit.setText(item.text)
                self._data_edit.setText(", ".join(str(value) for value in item.data) if chart else "")
                self._data_label.setVisible(chart)
                self._data_edit.setVisible(chart)
                self._source_edit.setText(item.source)
                self._set_ports_editor(item.ports if item.supports_ports else [])
                values = {
                    "x": item.pos().x(), "y": item.pos().y(),
                    "width": item._rect.width(), "height": item._rect.height(),
                    "rotation": item.rotation(), "opacity": item.opacity(), "z": item.zValue(),
                }
                for key, value in values.items():
                    self._number_fields[key].setValue(value)
                if line:
                    styles = ("solid", "dash", "dot", "dashdot")
                    self._line_style_combo.setCurrentIndex(styles.index(item.line_style) if item.line_style in styles else 0)
                    self._line_width_field.setValue(item.line_width)
                    self._arrow_start_check.setChecked(item.arrow_start)
                    self._arrow_end_check.setChecked(item.arrow_end)
                    self._animated_check.setChecked(item.animated)
                    self._effect_combo.setCurrentIndex(_LINE_EFFECTS.index(item.animation_effect) if item.animation_effect in _LINE_EFFECTS else 0)
                    self._flow_speed_field.setValue(item.flow_speed)
                    self._flow_direction_combo.setCurrentIndex(1 if item.flow_direction < 0 else 0)
                    self._flow_spacing_field.setValue(item.flow_spacing)
                    self._effect_intensity_field.setValue(item.effect_intensity)
                    self._packet_loop_check.setChecked(item.packet_loop)
                    self._packet_duration_field.setValue(item.packet_duration)
                    self._packet_interval_field.setValue(item.packet_interval)
                    self._packet_icon_edit.setText(item.packet_icon)
                    self._points_edit.setText(json.dumps([[point.x(), point.y()] for point in item.points]))
        del blockers
        self._sync_extension_inspector(item if selected_count == 1 else None)
        self._syncing_inspector = False
        self._sync_packet_controls()

    def _sync_extension_inspector(self, item: _CanvasElement | _CanvasConnector | None) -> None:
        if self._extension_inspector_widget is not None:
            self._extension_inspector_layout.removeWidget(self._extension_inspector_widget)
            self._extension_inspector_widget.deleteLater()
            self._extension_inspector_widget = None
        self._extension_inspector_host.hide()
        if item is None or isinstance(item, _CanvasConnector):
            return
        definition = self.canvas.elementRegistry().definition(item.kind)
        if definition is None or definition.inspector_factory is None:
            return
        try:
            widget = definition.inspector_factory(self.canvas, item)
        except Exception as error:  # plugin boundary: selection must remain safe
            self.canvas.diagnosticMessage.emit(
                f"Inspector {definition.type_id!r} failed: {error}"
            )
            return
        if widget is None:
            return
        if not isinstance(widget, QWidget):
            self.canvas.diagnosticMessage.emit(
                f"Inspector factory for {definition.type_id!r} must return QWidget or None"
            )
            return
        self._extension_inspector_widget = widget
        self._extension_inspector_layout.addWidget(widget)
        self._extension_inspector_host.show()

    @staticmethod
    def _parse_points(text: str) -> list[list[float]]:
        if not text.strip():
            return []
        values = json.loads(text)
        if not isinstance(values, list) or any(not isinstance(point, list | tuple) or len(point) != 2 for point in values):
            raise ValueError("Points must use [[x, y], ...] format")
        return [[float(point[0]), float(point[1])] for point in values]

    def _set_ports_editor(self, ports: list[dict[str, Any]]) -> None:
        selected = self._ports_list.currentItem()
        selected_id = "" if selected is None else str(
            selected.data(Qt.ItemDataRole.UserRole).get("id", "")
        )
        blocker = QSignalBlocker(self._ports_list)
        self._ports_list.clear()
        element_id = self.canvas.selectedElementId()
        for port in ports:
            data_type = str(port.get("dataType", "any"))
            unit = f" [{port['unit']}]" if port.get("unit") else ""
            count = self.canvas.portConnectionCount(element_id, port["id"]) if element_id else 0
            limit = int(port.get("maxConnections", 0))
            cardinality = f"{count}/{limit}" if limit else str(count)
            item = QListWidgetItem(
                f"{port['id']}  ·  {port['mode']}  ·  {data_type}{unit}  ·  {cardinality} links"
            )
            item.setData(Qt.ItemDataRole.UserRole, dict(port))
            item.setToolTip(
                f"{port.get('label', port['id'])}\n{port['mode']} · {port['side']}\n"
                f"Type: {data_type}{unit}\nConnections: {cardinality}"
            )
            self._ports_list.addItem(item)
            if port["id"] == selected_id:
                self._ports_list.setCurrentItem(item)
        if self._ports_list.currentItem() is None and self._ports_list.count():
            self._ports_list.setCurrentRow(0)
        del blocker
        self._load_selected_port()

    def _ports_from_editor(self) -> list[dict[str, Any]]:
        return [
            dict(self._ports_list.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self._ports_list.count())
        ]

    def _load_selected_port(self) -> None:
        selected = self._ports_list.selectedItems()
        if not selected:
            return
        self._syncing_port_editor = True
        port = dict(selected[0].data(Qt.ItemDataRole.UserRole))
        self._port_id_edit.setText(port["id"])
        self._port_label_edit.setText(port.get("label", ""))
        self._port_mode_combo.setCurrentText(port["mode"].title())
        self._port_side_combo.setCurrentText(port["side"].title())
        self._port_data_type_combo.setCurrentText(str(port.get("dataType", "any")))
        self._port_unit_edit.setText(str(port.get("unit", "")))
        self._port_required_check.setChecked(bool(port.get("required", False)))
        self._port_max_connections_field.setValue(int(port.get("maxConnections", 0)))
        self._port_accepted_types_edit.setText(", ".join(port.get("acceptedTypes", ())))
        self._port_accepted_units_edit.setText(", ".join(port.get("acceptedUnits", ())))
        self._port_converts_to_edit.setText(", ".join(port.get("convertsTo", ())))
        self._port_default_edit.setText(
            json.dumps(port["defaultValue"], ensure_ascii=False)
            if "defaultValue" in port else ""
        )
        self._port_tooltip_edit.setText(str(port.get("tooltip", "")))
        element_id = self.canvas.selectedElementId()
        canvas_item = self.canvas.element(element_id) if element_id else None
        if canvas_item is not None and canvas_item.port(port["id"]) is not None:
            state = self.canvas.portRuntimeState(element_id, port["id"])
            color = "#0f9f8f" if state["valid"] else "#d94e43"
            self._port_runtime_status.setText(
                f"Runtime · {state['source']} · {state['actualType']} · {state['reason']}"
            )
            self._port_runtime_status.setStyleSheet(f"color: {color};")
        else:
            self._port_runtime_status.setText("Runtime · pending port update")
            self._port_runtime_status.setStyleSheet("color: #8b8179;")
        self._syncing_port_editor = False

    def _auto_update_selected_port(self, _value: Any = None) -> None:
        if (
            self._syncing_port_editor
            or self._syncing_inspector
            or self._ports_list.currentItem() is None
        ):
            return
        self._safe_upsert_port()

    def _safe_upsert_port(self, _value: Any = None) -> None:
        try:
            self._upsert_port()
        except (TypeError, ValueError) as error:
            self._port_runtime_status.setText(f"Port contract rejected · {error}")
            self._port_runtime_status.setStyleSheet("color: #d94e43;")
            self.canvas.diagnosticMessage.emit(f"Port contract rejected: {error}")

    @staticmethod
    def _parse_default_value(text: str) -> Any:
        value = text.strip()
        if not value:
            raise ValueError("No default value")
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _upsert_port(self) -> None:
        port_id = self._port_id_edit.text().strip()
        if not port_id:
            return
        selected = self._ports_list.currentItem()
        base = (
            dict(selected.data(Qt.ItemDataRole.UserRole)) if selected is not None else {}
        )
        base.update({
            "id": port_id,
            "label": self._port_label_edit.text().strip() or port_id,
            "mode": self._port_mode_combo.currentText().lower(),
            "side": self._port_side_combo.currentText().lower(),
            "dataType": self._port_data_type_combo.currentText(),
            "unit": self._port_unit_edit.text(),
            "required": self._port_required_check.isChecked(),
            "maxConnections": int(self._port_max_connections_field.value()),
            "acceptedTypes": self._port_accepted_types_edit.text(),
            "acceptedUnits": self._port_accepted_units_edit.text(),
            "convertsTo": self._port_converts_to_edit.text(),
            "tooltip": self._port_tooltip_edit.text(),
        })
        if self._port_default_edit.text().strip():
            base["defaultValue"] = self._parse_default_value(self._port_default_edit.text())
        else:
            base.pop("defaultValue", None)
        normalized = _normalize_node_ports([base])[0]
        ports = self._ports_from_editor()
        if selected is not None:
            ports[self._ports_list.row(selected)] = normalized
        else:
            for index, port in enumerate(ports):
                if port["id"] == port_id:
                    ports[index] = normalized
                    break
            else:
                ports.append(normalized)
        self._set_ports_editor(ports)
        self._schedule_inspector_apply(0)

    def _remove_port_from_editor(self) -> None:
        selected = self._ports_list.selectedItems()
        if selected:
            self._ports_list.takeItem(self._ports_list.row(selected[0]))
            self._schedule_inspector_apply(0)

    def _refresh_endpoint_port_controls(
        self,
        preferred_source: str | None = None,
        preferred_target: str | None = None,
    ) -> None:
        source_id = self._source_combo.currentData()
        target_id = self._target_combo.currentData()
        self._populate_port_combo(self._source_port_combo, source_id, preferred_source, True)
        self._populate_port_combo(self._target_port_combo, target_id, preferred_target, False)

    def _populate_port_combo(
        self,
        combo: QComboBox,
        element_id: Any,
        preferred: str | None,
        source: bool,
    ) -> None:
        current = str(preferred if preferred is not None else combo.currentData() or "")
        blocker = QSignalBlocker(combo)
        combo.clear()
        combo.addItem("Auto edge", "")
        item = self.canvas.element(str(element_id)) if element_id else None
        if item is not None:
            allowed = ("output", "free") if source else ("input", "free")
            for port in item.ports:
                if port["mode"] in allowed:
                    unit = f" [{port['unit']}]" if port.get("unit") else ""
                    combo.addItem(
                        f"{port['label']}  ·  {port['mode']}  ·  "
                        f"{port.get('dataType', 'any')}{unit}",
                        port["id"],
                    )
        index = combo.findData(current)
        combo.setCurrentIndex(max(0, index))
        del blocker

    @staticmethod
    def _parse_values(text: str) -> list[float]:
        if not text.strip():
            return []
        if text.lstrip().startswith("["):
            values = json.loads(text)
        else:
            values = [value.strip() for value in text.split(",")]
        return [float(value) for value in values]

    def refreshLayers(self) -> None:
        if self._syncing_layers:
            return
        selected = set(self.canvas.selectedObjectIds())
        blocker = QSignalBlocker(self._layers)
        self._layers.clear()
        query = self._layer_search.text().casefold().strip()
        objects = [
            *self.canvas._elements.values(),
            *self.canvas._connectors.values(),
            *self.canvas._groups.values(),
        ]
        for item in sorted(objects, key=lambda value: value.zValue(), reverse=True):
            description = getattr(item, "text", "")
            if query and query not in f"{item.element_id} {item.kind} {description}".casefold():
                continue
            state = "Hidden" if item.hidden else "Locked" if item.locked else "Visible"
            primary = description or item.element_id
            secondary = f"{item.kind} · {item.element_id}" if description else item.kind
            label = QListWidgetItem(
                _canvas_icon("eye_off" if item.hidden else "lock" if item.locked else "eye"),
                f"{primary}\n{secondary}",
            )
            label.setSizeHint(QSize(0, 44))
            label.setData(Qt.ItemDataRole.UserRole, item.element_id)
            label.setToolTip(f"ID: {item.element_id}\nType: {item.kind}\nState: {state}")
            if item.hidden:
                label.setForeground(QColor("#9aa1ab"))
            self._layers.addItem(label)
            if item.element_id in selected:
                label.setSelected(True)
        del blocker

    def _select_layers(self) -> None:
        element_ids = [
            str(item.data(Qt.ItemDataRole.UserRole))
            for item in self._layers.selectedItems()
        ]
        self._syncing_layers = True
        try:
            self.canvas.selectElements(element_ids)
        finally:
            self._syncing_layers = False

    def _selected_layer_ids(self) -> list[str]:
        return [
            str(item.data(Qt.ItemDataRole.UserRole))
            for item in self._layers.selectedItems()
        ]

    def _toggle_layer_lock(self) -> None:
        ids = self._selected_layer_ids()
        if ids:
            locked = not all(self.canvas.objectState(object_id)["locked"] for object_id in ids)
            self.canvas.setObjectsLocked(ids, locked)
            self.refreshLayers()

    def _toggle_layer_visibility(self) -> None:
        ids = self._selected_layer_ids()
        if ids:
            hidden = not all(self.canvas.objectState(object_id)["hidden"] for object_id in ids)
            self.canvas.setObjectsHidden(ids, hidden)
            self.refreshLayers()

    def _isolate_layers(self) -> None:
        ids = self._selected_layer_ids()
        self.canvas.selectElements(ids)
        if self.canvas.isolateSelection():
            self.refreshLayers()

    def _show_all_layers(self) -> None:
        self.canvas.clearIsolation()
        self.canvas.showAllObjects()
        self.refreshLayers()

    def _show_save_status(self, target: str) -> None:
        modified = self.canvas.isDocumentModified()
        prefix = "Session" if modified else "Saved"
        self._save_status.setText(f"{prefix}: {target}")
        color = "#c66a12" if modified else "#0f9f8f"
        self._footer_icon.setPixmap(
            _canvas_icon("save" if modified else "check", color).pixmap(19, 19)
        )
        self._footer_status.setText("Session saved" if modified else "Saved")
        self._footer_status.setStyleSheet(f"color: {color}; font-weight: 700;")
        self._footer_status.setToolTip(str(target))

    def _sync_modified_status(self, modified: bool) -> None:
        if self.canvas.isReadOnly():
            return
        color = "#ef6a5b" if modified else "#0f9f8f"
        self._footer_icon.setPixmap(
            _canvas_icon("save" if modified else "check", color).pixmap(19, 19)
        )
        self._footer_status.setText("Unsaved changes" if modified else "Saved")
        self._footer_status.setStyleSheet(f"color: {color}; font-weight: 700;")

    def _sync_read_only_status(self, read_only: bool, reason: str) -> None:
        for index in (0, 1, 3, 4):
            self._tabs.setTabEnabled(index, not read_only)
        if read_only:
            color = "#d97706"
            self._footer_icon.setPixmap(_canvas_icon("lock", color).pixmap(19, 19))
            self._footer_status.setText("Read only · newer format")
            self._footer_status.setToolTip(reason)
            self._footer_status.setStyleSheet(f"color: {color}; font-weight: 700;")
            if self._tabs.currentIndex() in (0, 1, 3, 4):
                self._tabs.setCurrentIndex(2)
        else:
            self._sync_modified_status(self.canvas.isDocumentModified())


class _CanvasQuickToolbar(QFrame):
    """Compact in-canvas actions shown only while runtime editing is active."""

    def __init__(self, canvas: "MonkezCanva") -> None:
        super().__init__(canvas)
        self.canvas = canvas
        self.setObjectName("monkezCanvaQuickToolbar")
        self.setStyleSheet(
            "#monkezCanvaQuickToolbar { background: #ffffff; border: 1px solid #d7e0ea; border-radius: 12px; }"
            "#monkezCanvaQuickToolbar QToolButton { color: #334155; background: transparent; border: none; "
            "border-radius: 7px; padding: 5px 8px; min-height: 24px; font-weight: 600; }"
            "#monkezCanvaQuickToolbar QToolButton:hover { color: #1d4ed8; background: #eff6ff; }"
            "#monkezCanvaQuickToolbar QToolButton:pressed { background: #dbeafe; }"
            "#monkezCanvaQuickToolbar QToolButton:disabled { color: #b6c0cd; background: transparent; }"
            "#monkezCanvaQuickToolbar QToolButton#quickSave { color: #ffffff; background: #2563eb; }"
            "#monkezCanvaQuickToolbar QToolButton#quickSave:hover { background: #1d4ed8; }"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(15, 23, 42, 60))
        self.setGraphicsEffect(shadow)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 6, 7, 6)
        layout.setSpacing(2)
        self._save_button = self._button(
            "", lambda _checked=False: canvas.savePersistent(),
            "Save project workspace", 36, "save",
        )
        self._save_button.setObjectName("quickSave")
        self._separator(layout)
        self._undo_button = self._button("", canvas.undo, "Undo", 34, "undo")
        self._redo_button = self._button("", canvas.redo, "Redo", 34, "redo")
        canvas.historyChanged.connect(self._update_history_state)
        canvas.readOnlyChanged.connect(self._update_read_only_state)
        self._update_history_state(
            canvas.canUndo(), canvas.canRedo(), canvas.undoText(), canvas.redoText()
        )
        self._separator(layout)
        self._button("", canvas.zoomOut, "Zoom out", 34, "zoom_out")
        self._button("", canvas.resetZoom, "Reset zoom to 100%", 34, "actual_size")
        self._button("", canvas.zoomIn, "Zoom in", 34, "zoom_in")
        self._button("", canvas.fitContent, "Fit all items", 34, "fit")
        self._separator(layout)
        self._align_buttons: list[QToolButton] = []
        for alignment in (
            "left", "hcenter", "right", "top", "vcenter", "bottom", "center",
        ):
            button = self._button(
                "",
                lambda _checked=False, value=alignment: canvas.alignSelected(value),
                f"Align selected items: {alignment}",
                34,
                f"align_{alignment}",
            )
            self._align_buttons.append(button)
        canvas.selectionSetChanged.connect(self._update_alignment_state)
        self._update_alignment_state(canvas.selectedElementIds())
        self._update_read_only_state(canvas.isReadOnly(), canvas.readOnlyReason())

    def _update_history_state(
        self, can_undo: bool, can_redo: bool, undo_text: str, redo_text: str
    ) -> None:
        self._undo_button.setEnabled(can_undo and not self.canvas.isReadOnly())
        self._redo_button.setEnabled(can_redo and not self.canvas.isReadOnly())
        self._undo_button.setToolTip(f"Undo {undo_text}" if undo_text else "Undo")
        self._redo_button.setToolTip(f"Redo {redo_text}" if redo_text else "Redo")

    def _update_read_only_state(self, read_only: bool, reason: str) -> None:
        self._save_button.setEnabled(not read_only)
        self._save_button.setToolTip(reason if read_only else "Save project workspace")
        self._update_history_state(
            self.canvas.canUndo(), self.canvas.canRedo(),
            self.canvas.undoText(), self.canvas.redoText(),
        )
        self._update_alignment_state(self.canvas.selectedElementIds())

    def _button(
        self,
        label: str,
        callback,
        tooltip: str = "",
        width: int | None = None,
        icon: str = "",
    ) -> QToolButton:
        button = QToolButton(self)
        button.setText(label)
        button.setToolTip(tooltip or label)
        if icon:
            button.setIcon(_canvas_icon(icon, "#ffffff" if icon == "save" else "#475569"))
            button.setIconSize(QSize(18, 18))
        if width is not None:
            button.setFixedWidth(width)
        button.clicked.connect(callback)
        self.layout().addWidget(button)
        return button

    @staticmethod
    def _separator(layout: QHBoxLayout) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #e2e8f0; margin: 4px 2px")
        layout.addWidget(line)

    def _update_alignment_state(self, element_ids: list[str]) -> None:
        enabled = (
            len([element_id for element_id in element_ids if element_id in self.canvas._elements]) >= 2
            and not self.canvas.isReadOnly()
        )
        for button in self._align_buttons:
            button.setEnabled(enabled)


class _CanvasView(QGraphicsView):
    def __init__(self, canvas: "MonkezCanva", scene: QGraphicsScene) -> None:
        super().__init__(scene, canvas)
        self.canvas = canvas
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)
        self._right_pan_active = False
        self._right_pan_origin = None
        self._right_pan_start = None
        self._right_pan_moved = False
        self._connection_origin: tuple[_CanvasElement, dict[str, Any]] | None = None
        self._connection_hover_key: tuple[str, str] | None = None
        self._connection_preview = QGraphicsPathItem()
        preview_pen = QPen(QColor("#2563eb"), 2.5, Qt.PenStyle.DashLine)
        preview_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._connection_preview.setPen(preview_pen)
        self._connection_preview.setZValue(100000)
        self._connection_preview.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._connection_preview.hide()
        scene.addItem(self._connection_preview)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self.canvas, "_quick_toolbar"):
            self.canvas._place_quick_toolbar()
        if hasattr(self.canvas, "_minimap"):
            self.canvas._place_minimap()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            current = self.transform().m11()
            target = min(4.0, max(0.2, current * factor))
            if current > 0 and not math.isclose(target, current):
                applied = target / current
                self.scale(applied, applied)
            event.accept()
            if hasattr(self.canvas, "_minimap"):
                self.canvas._minimap.update()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        point = event.position().toPoint()
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.canvas.editMode
            and not self.canvas.isReadOnly()
        ):
            endpoint = self._port_at(point)
            if endpoint is not None:
                self._connection_origin = endpoint
                start = endpoint[0].portScenePosition(endpoint[1]["id"])
                preview = QPainterPath(start)
                preview.lineTo(start)
                self._connection_preview.setPath(preview)
                self._connection_preview.show()
                self._show_connection_candidates(endpoint[0], endpoint[1])
                self.viewport().setCursor(Qt.CursorShape.CrossCursor)
                self.canvas.diagnosticMessage.emit(
                    f"Connector drag started: {endpoint[0].element_id}.{endpoint[1]['id']}"
                )
                event.accept()
                return
        if event.button() == Qt.MouseButton.RightButton and self.itemAt(point) is None:
            self._right_pan_active = True
            self._right_pan_origin = point
            self._right_pan_start = point
            self._right_pan_moved = False
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._connection_origin is not None:
            source, port = self._connection_origin
            start = source.portScenePosition(port["id"])
            end = self.mapToScene(event.position().toPoint())
            self._update_connection_hover(self._port_at(event.position().toPoint()))
            delta = max(40.0, abs(end.x() - start.x()) * 0.45)
            direction = 1 if end.x() >= start.x() else -1
            preview = QPainterPath(start)
            preview.cubicTo(
                start + QPointF(delta * direction, 0),
                end - QPointF(delta * direction, 0),
                end,
            )
            self._connection_preview.setPath(preview)
            event.accept()
            return
        if self._right_pan_active and self._right_pan_origin is not None:
            point = event.position().toPoint()
            delta = point - self._right_pan_origin
            if self._right_pan_start is not None and (point - self._right_pan_start).manhattanLength() > 4:
                self._right_pan_moved = True
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._right_pan_origin = point
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._connection_origin is not None and event.button() == Qt.MouseButton.LeftButton:
            source, source_port = self._connection_origin
            self._connection_origin = None
            self._connection_preview.hide()
            target = self._port_at(event.position().toPoint())
            self._clear_connection_feedback()
            self.viewport().unsetCursor()
            if target is not None and (target[0] is not source or target[1]["id"] != source_port["id"]):
                try:
                    connector_id = self.canvas.connectPorts(
                        source.element_id,
                        source_port["id"],
                        target[0].element_id,
                        target[1]["id"],
                    )
                    self.scene().clearSelection()
                    self.canvas.connector(connector_id).setSelected(True)
                    self.canvas.diagnosticMessage.emit(f"Connector created from ports: {connector_id}")
                except (KeyError, ValueError) as error:
                    self.canvas.diagnosticMessage.emit(f"Connector rejected: {error}")
            event.accept()
            return
        if self._right_pan_active and event.button() == Qt.MouseButton.RightButton:
            show_menu = not self._right_pan_moved
            self._right_pan_active = False
            self._right_pan_origin = None
            self._right_pan_start = None
            self.viewport().unsetCursor()
            if show_menu:
                self.canvas.showContextMenu(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseReleaseEvent(event)
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, _CanvasElement):
            self.canvas.elementClicked.emit(item.element_id)
            self.canvas.objectClicked.emit(item.element_id)
        elif isinstance(item, _CanvasConnector):
            self.canvas.connectorClicked.emit(item.connector_id)
            self.canvas.objectClicked.emit(item.connector_id)

    def keyPressEvent(self, event) -> None:
        if self._connection_origin is not None and event.key() == Qt.Key.Key_Escape:
            self._connection_origin = None
            self._connection_preview.hide()
            self._clear_connection_feedback()
            self.viewport().unsetCursor()
            self.canvas.diagnosticMessage.emit("Connector drag cancelled")
            event.accept()
            return
        super().keyPressEvent(event)

    def _set_connection_preview_state(self, state: str) -> None:
        color = {
            "compatible": "#10b981",
            "conversion": "#8b5cf6",
            "incompatible": "#ef4444",
        }.get(state, "#2563eb")
        pen = QPen(QColor(color), 2.5, Qt.PenStyle.DashLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._connection_preview.setPen(pen)

    def _show_connection_candidates(
        self, origin: _CanvasElement, origin_port: dict[str, Any]
    ) -> None:
        for item in self.canvas._elements.values():
            feedback: dict[str, tuple[str, str]] = {}
            for port in item.ports:
                if item is origin and port["id"] == origin_port["id"]:
                    feedback[port["id"]] = ("origin", "Connection origin")
                    continue
                compatibility = self.canvas.portCompatibility(
                    origin.element_id,
                    origin_port["id"],
                    item.element_id,
                    port["id"],
                )
                state = (
                    "conversion" if compatibility.compatible and compatibility.conversion
                    else "compatible" if compatibility.compatible
                    else "incompatible"
                )
                feedback[port["id"]] = (state, compatibility.reason)
            item.setPortFeedback(feedback)
        self._connection_hover_key = None
        self._set_connection_preview_state("origin")

    def _update_connection_hover(
        self, target: tuple[_CanvasElement, dict[str, Any]] | None
    ) -> None:
        if self._connection_origin is None:
            return
        key = None if target is None else (target[0].element_id, target[1]["id"])
        if key == self._connection_hover_key:
            return
        self._connection_hover_key = key
        if target is None:
            self._set_connection_preview_state("origin")
            return
        origin, origin_port = self._connection_origin
        if target[0] is origin and target[1]["id"] == origin_port["id"]:
            compatibility = PortCompatibility(False, "Choose a different target port")
        else:
            compatibility = self.canvas.portCompatibility(
                origin.element_id,
                origin_port["id"],
                target[0].element_id,
                target[1]["id"],
            )
        state = (
            "conversion" if compatibility.compatible and compatibility.conversion
            else "compatible" if compatibility.compatible
            else "incompatible"
        )
        self._set_connection_preview_state(state)
        self.canvas.diagnosticMessage.emit(compatibility.reason)

    def _clear_connection_feedback(self) -> None:
        for item in self.canvas._elements.values():
            item.clearPortFeedback()
        self._connection_hover_key = None
        self._set_connection_preview_state("origin")

    def contextMenuEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if isinstance(item, (_CanvasElement, _CanvasConnector)):
            if not item.isSelected():
                self.scene().clearSelection()
                item.setSelected(True)
            self.canvas.showContextMenu(event.globalPos(), item.element_id)
            event.accept()
            return
        event.ignore()

    def _port_at(self, view_position) -> tuple[_CanvasElement, dict[str, Any]] | None:
        item = self.itemAt(view_position)
        if not isinstance(item, _CanvasElement) or not item.supports_ports:
            return None
        port = item.portAt(self.mapToScene(view_position))
        return (item, port) if port is not None else None

    def dragEnterEvent(self, event) -> None:
        if self._media_urls(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._media_urls(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        urls = self._media_urls(event.mimeData())
        if not urls or self.canvas.isReadOnly():
            super().dropEvent(event)
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        for index, path in enumerate(urls):
            self.canvas.addMedia(path, scene_pos.x() + index * 30, scene_pos.y() + index * 30)
        event.acceptProposedAction()

    @staticmethod
    def _media_urls(mime_data) -> list[str]:
        supported = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
        return [
            url.toLocalFile()
            for url in mime_data.urls()
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in supported
        ]


class MonkezCanva(QWidget):
    """Canvas editor with runtime edit mode and a code-friendly element API.

    The name intentionally follows the requested product spelling ``Canva``.
    Press ``Ctrl+D`` followed by ``E`` while its window is active to toggle the
    editing toolbox.
    """

    editModeChanged = pyqtSignal(bool)
    elementAdded = pyqtSignal(str)
    elementRemoved = pyqtSignal(str)
    connectorAdded = pyqtSignal(str)
    connectorRemoved = pyqtSignal(str)
    elementClicked = pyqtSignal(str)
    connectorClicked = pyqtSignal(str)
    objectClicked = pyqtSignal(str)
    selectionChanged = pyqtSignal(str)
    selectionSetChanged = pyqtSignal(list)
    documentChanged = pyqtSignal()
    documentOperation = pyqtSignal(dict)
    diagnosticMessage = pyqtSignal(str)
    itemIdChanged = pyqtSignal(str, str)
    autoSaved = pyqtSignal(str)
    persistentSaved = pyqtSignal(str)
    persistentLoaded = pyqtSignal(str)
    messageSent = pyqtSignal(str, str)
    messageArrived = pyqtSignal(str, str)
    historyChanged = pyqtSignal(bool, bool, str, str)
    documentModifiedChanged = pyqtSignal(bool)
    readOnlyChanged = pyqtSignal(bool, str)
    recoveryLoaded = pyqtSignal(str, str)
    assetIntegrityChecked = pyqtSignal(list)
    palettePreferencesChanged = pyqtSignal(list, list)
    viewportBookmarksChanged = pyqtSignal(list)
    objectStateChanged = pyqtSignal(str, bool, bool)
    groupAdded = pyqtSignal(str)
    groupRemoved = pyqtSignal(str)
    portRuntimeValueChanged = pyqtSignal(str, str, object)
    layoutApplied = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._background_color = QColor("#f8fafc")
        self._grid_color = QColor("#e2e8f0")
        self._grid_visible = True
        self._snap_to_grid = True
        self._snap_targets = SNAP_TARGETS
        self._snap_distance = 8.0
        self._smart_guides_visible = True
        self._grid_size = 20
        self._grid_style = 0
        self._background_image = ""
        self._background_image_mode = 0
        self._palette_favorites: tuple[str, ...] = ()
        self._palette_recent: tuple[str, ...] = ()
        self._viewport_bookmarks: tuple[dict[str, Any], ...] = ()
        self._minimap_visible = True
        self._isolated_ids: set[str] = set()
        self._message_payloads: dict[str, dict[str, Any]] = {}
        self._port_runtime_values: dict[tuple[str, str], Any] = {}
        self._clipboard_paste_count = 0
        self._element_registry = create_default_element_registry()
        self._background_pixmap = QPixmap()
        self._project_directory = ""
        self._edit_mode = False
        self._shortcut_enabled = True
        self._fit_pending = False
        self._pan_mode = False
        self._persistent_key = ""
        self._persistent_auto_load_attempted = False
        self._auto_save_enabled = True
        self._auto_save_delay = 500
        self._session_document: dict[str, Any] | None = None
        self._draft_document: dict[str, Any] | None = None
        self._read_only_reason = ""
        self._last_recovery_source = ""
        self._asset_integrity_issues: list[str] = []
        self._restoring = False
        self._document_render_notification = False
        self._animations: dict[str, QPropertyAnimation] = {}
        self._elements: dict[str, _CanvasElement] = {}
        self._connectors: dict[str, _CanvasConnector] = {}
        self._groups: dict[str, _CanvasGroup] = {}
        self._routing_revision = 0
        self._document_model: CanvasDocument | None = None
        self._document_subscription = ""
        self._last_rendered_document_revision = 0
        self._scene = _CanvasScene(self)
        self._scene.setSceneRect(-2000, -2000, 4000, 4000)
        self._view = _CanvasView(self, self._scene)
        self._animation_scheduler = CanvasAnimationScheduler(self)
        self._document_model = CanvasDocument.from_dict(self._graphics_document())
        self._document_subscription = self._document_model.subscribe(self._on_document_operation)
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(80)
        self._undo_stack.indexChanged.connect(self._emit_history_state)
        self._undo_stack.cleanChanged.connect(self._on_history_clean_changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._quick_toolbar = _CanvasQuickToolbar(self)
        self._quick_toolbar.hide()
        layout.addWidget(self._view)
        self._minimap = CanvasMinimap(self)
        self._minimap.hide()
        self.documentChanged.connect(self._update_minimap)
        self._view.horizontalScrollBar().valueChanged.connect(self._update_minimap)
        self._view.verticalScrollBar().valueChanged.connect(self._update_minimap)
        self._toolbox: _CanvasEditorToolbox | None = None
        self._command_palette: _CanvasCommandPalette | None = None
        self._scene.selectionChanged.connect(self._emit_selection)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._flush_autosave)
        self.documentChanged.connect(self._queue_autosave)
        self._toggle_shortcuts: list[QShortcut] = []
        for sequence, label in (
            ("Ctrl+D, E", "Ctrl+D then E"),
            ("Ctrl+D, Ctrl+E", "hold Ctrl and press D then E"),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(
                lambda source=label: self._activate_editor_shortcut(source)
            )
            shortcut.activatedAmbiguously.connect(
                lambda source=label: self.diagnosticMessage.emit(
                    f"Editor shortcut is ambiguous: {source}"
                )
            )
            self._toggle_shortcuts.append(shortcut)
        delete_shortcut = QShortcut(QKeySequence.StandardKey.Delete, self)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        delete_shortcut.activated.connect(self.deleteSelected)
        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        undo_shortcut.activated.connect(self.undo)
        redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        redo_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        redo_shortcut.activated.connect(self.redo)
        self._editor_shortcuts: list[QShortcut] = []
        for standard_key, callback in (
            (QKeySequence.StandardKey.Copy, self.copySelection),
            (QKeySequence.StandardKey.Cut, self.cutSelection),
            (QKeySequence.StandardKey.Paste, self.pasteSelection),
        ):
            shortcut = QShortcut(QKeySequence(standard_key), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._editor_shortcuts.append(shortcut)
        for sequence, dx, dy in (
            ("Left", -1.0, 0.0), ("Right", 1.0, 0.0),
            ("Up", 0.0, -1.0), ("Down", 0.0, 1.0),
            ("Shift+Left", -10.0, 0.0), ("Shift+Right", 10.0, 0.0),
            ("Shift+Up", 0.0, -10.0), ("Shift+Down", 0.0, 10.0),
            ("Alt+Left", -0.1, 0.0), ("Alt+Right", 0.1, 0.0),
            ("Alt+Up", 0.0, -0.1), ("Alt+Down", 0.0, 0.1),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(
                lambda x=dx, y=dy: self.nudgeSelected(x, y)
            )
            self._editor_shortcuts.append(shortcut)
        QApplication.instance().installEventFilter(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._emit_history_state()

    def eventFilter(self, watched, event) -> bool:
        if (
            self._shortcut_enabled
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_K
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and isinstance(watched, QWidget)
        ):
            owner = watched.window()
            if owner in (self.window(), self._toolbox, self._command_palette):
                self.showCommandPalette()
                return True
        return super().eventFilter(watched, event)

    def sizeHint(self) -> QSize:
        return QSize(640, 420)

    def minimumSizeHint(self) -> QSize:
        return QSize(240, 160)

    def scene(self) -> QGraphicsScene:
        return self._scene

    def view(self) -> QGraphicsView:
        return self._view

    def animationStats(self) -> dict[str, int | bool]:
        """Return lightweight shared-clock metrics for profiling and tests."""

        return self._animation_scheduler.stats()

    def setAnimationFrameInterval(self, milliseconds: int) -> None:
        """Set the one shared animation-clock interval (minimum 16 ms)."""

        self._animation_scheduler.timer.setInterval(max(16, int(milliseconds)))

    def animationFrameInterval(self) -> int:
        return self._animation_scheduler.timer.interval()

    def elementRegistry(self) -> ElementRegistry:
        """Return this canvas' component registry."""
        return self._element_registry

    def paletteFavorites(self) -> tuple[str, ...]:
        return self._palette_favorites

    def paletteRecent(self) -> tuple[str, ...]:
        return self._palette_recent

    def setPaletteFavorite(self, type_id: str, favorite: bool = True) -> bool:
        """Persist one component favorite with the portable canvas document."""

        key = str(type_id).strip().lower()
        self._element_registry.require(key)
        favorites = list(self._palette_favorites)
        if favorite and key not in favorites:
            favorites.append(key)
        elif not favorite and key in favorites:
            favorites.remove(key)
        else:
            return False
        normalized = list(normalize_component_ids(favorites))
        return self._push_document_mutation(
            lambda document: document.update_scene({PALETTE_FAVORITES_KEY: normalized}),
            "Update palette favorites",
            merge_key="palette:favorites",
        )

    def togglePaletteFavorite(self, type_id: str) -> bool:
        key = str(type_id).strip().lower()
        return self.setPaletteFavorite(key, key not in self._palette_favorites)

    def addPaletteElement(self, type_id: str) -> str:
        """Add a registry component, opening the appropriate media picker if needed."""

        definition = self._element_registry.require(type_id)
        if definition.media_picker:
            pattern = (
                "Animated GIF (*.gif)" if definition.type_id == "animated_image"
                else "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
            )
            path, _selected_filter = QFileDialog.getOpenFileName(
                self.window(), f"Add {definition.label}", "", pattern
            )
            if not path:
                return ""
            return self.addMedia(
                path, animated=definition.type_id == "animated_image"
            )
        return self.addElement(definition.type_id)

    def showCommandPalette(self, query: str = "") -> None:
        """Show the context-aware command launcher (Ctrl+K)."""

        if not self._edit_mode:
            self.setEditMode(True)
        if self._command_palette is None:
            self._command_palette = _CanvasCommandPalette(self)
        self._command_palette.showPalette(query)

    def selectAllElements(self) -> list[str]:
        return self.selectElements(self.elements())

    def zoomToSelection(self) -> bool:
        items = [
            self.canvasObject(object_id) for object_id in self.selectedObjectIds()
        ]
        items = [item for item in items if item is not None]
        if not items:
            return False
        bounds = QRectF(items[0].sceneBoundingRect())
        for item in items[1:]:
            bounds = bounds.united(item.sceneBoundingRect())
        self._view.fitInView(
            bounds.adjusted(-35, -35, 35, 35), Qt.AspectRatioMode.KeepAspectRatio
        )
        scale = self._view.transform().m11()
        if scale > 4.0:
            self._view.scale(4.0 / scale, 4.0 / scale)
        elif 0 < scale < 0.2:
            self._view.scale(0.2 / scale, 0.2 / scale)
        return True

    def registerElementDefinition(
        self,
        definition: ElementDefinition,
        *,
        replace_existing: bool = False,
    ) -> "MonkezCanva":
        """Register component metadata used by add APIs and the Elements pane."""
        existing = self._element_registry.definition(definition.type_id)
        replace_missing = existing is not None and existing.plugin_id == "__missing__"
        self._element_registry.register(
            definition, replace_existing=replace_existing or replace_missing
        )
        self._reconcile_registry_records(definition.type_id)
        if self._toolbox is not None:
            was_visible = self._toolbox.isVisible()
            self._toolbox.close()
            self._toolbox.deleteLater()
            self._toolbox = None
            if was_visible:
                self._ensure_toolbox()
                self._toolbox.show()
        return self

    def unregisterElementPlugin(self, plugin_id: str) -> tuple[str, ...]:
        """Unload registry metadata owned by one plugin; existing records stay intact."""
        removed = self._element_registry.unregister_owner(plugin_id)
        for definition in removed:
            for item in self._elements.values():
                if item.kind == definition.type_id:
                    item.definition = None
                    item.update()
        if self._toolbox is not None:
            self._toolbox._sync_inspector(self.selectedElementId())
        return tuple(definition.type_id for definition in removed)

    def element(self, element_id: str) -> _CanvasElement | None:
        return self._elements.get(str(element_id))

    def group(self, group_id: str) -> _CanvasGroup | None:
        return self._groups.get(str(group_id))

    def groups(self) -> list[str]:
        return list(self._groups)

    def canvasObject(
        self, object_id: str
    ) -> _CanvasElement | _CanvasConnector | _CanvasGroup | None:
        key = str(object_id)
        return self._elements.get(key) or self._connectors.get(key) or self._groups.get(key)

    def elements(self) -> list[str]:
        return list(self._elements)

    def selectedElementId(self) -> str:
        selected = self.selectedObjectIds()
        return selected[0] if selected else ""

    def selectedElementIds(self) -> list[str]:
        return [
            element_id
            for element_id, item in self._elements.items()
            if item.isSelected()
        ]

    def selectedObjectIds(self) -> list[str]:
        selected = self.selectedElementIds()
        selected.extend(
            connector_id
            for connector_id, connector in self._connectors.items()
            if connector.isSelected()
        )
        selected.extend(
            group_id for group_id, group in self._groups.items() if group.isSelected()
        )
        return selected

    def objectState(self, object_id: str) -> dict[str, bool]:
        item = self.canvasObject(object_id)
        if item is None:
            raise KeyError(f"Unknown MonkezCanva object: {object_id}")
        return {"locked": bool(item.locked), "hidden": bool(item.hidden)}

    def setObjectsLocked(self, object_ids, locked: bool = True) -> bool:
        ids = tuple(dict.fromkeys(str(object_id) for object_id in object_ids))
        value = bool(locked)

        def mutate(document: CanvasDocument) -> None:
            for object_id in ids:
                if document.element(object_id) is not None:
                    document.update_element(object_id, {"locked": value})
                elif document.connector(object_id) is not None:
                    document.update_connector(object_id, {"locked": value})
                elif document.group(object_id) is not None:
                    document.update_group(object_id, {"locked": value})

        changed = self._push_document_mutation(
            mutate, f"{'Lock' if value else 'Unlock'} {len(ids)} object{'s' if len(ids) != 1 else ''}"
        )
        if changed:
            for object_id in ids:
                state = self.objectState(object_id)
                self.objectStateChanged.emit(object_id, state["locked"], state["hidden"])
        return changed

    def setObjectLocked(self, object_id: str, locked: bool = True) -> bool:
        return self.setObjectsLocked((object_id,), locked)

    def setObjectsHidden(self, object_ids, hidden: bool = True) -> bool:
        ids = tuple(dict.fromkeys(str(object_id) for object_id in object_ids))
        value = bool(hidden)

        def mutate(document: CanvasDocument) -> None:
            for object_id in ids:
                if document.element(object_id) is not None:
                    document.update_element(object_id, {"hidden": value})
                elif document.connector(object_id) is not None:
                    document.update_connector(object_id, {"hidden": value})
                elif document.group(object_id) is not None:
                    document.update_group(object_id, {"hidden": value})

        changed = self._push_document_mutation(
            mutate, f"{'Hide' if value else 'Show'} {len(ids)} object{'s' if len(ids) != 1 else ''}"
        )
        if changed:
            for object_id in ids:
                state = self.objectState(object_id)
                self.objectStateChanged.emit(object_id, state["locked"], state["hidden"])
        return changed

    def setObjectHidden(self, object_id: str, hidden: bool = True) -> bool:
        return self.setObjectsHidden((object_id,), hidden)

    def lockSelected(self, locked: bool = True) -> bool:
        return self.setObjectsLocked(self.selectedObjectIds(), locked)

    def hideSelected(self) -> bool:
        return self.setObjectsHidden(self.selectedObjectIds(), True)

    def showAllObjects(self) -> bool:
        ids = [
            object_id for object_id in (*self._elements, *self._connectors, *self._groups)
            if self.canvasObject(object_id).hidden
        ]
        return self.setObjectsHidden(ids, False) if ids else False

    def isolateSelection(self) -> bool:
        selected = set(self.selectedObjectIds())
        if not selected:
            return False
        for connector_id, connector in self._connectors.items():
            if connector.source.element_id in selected and connector.target.element_id in selected:
                selected.add(connector_id)
        self._isolated_ids = selected
        self._sync_object_states()
        self.diagnosticMessage.emit(f"Isolated {len(selected)} canvas objects")
        return True

    def clearIsolation(self) -> bool:
        if not self._isolated_ids:
            return False
        self._isolated_ids.clear()
        self._sync_object_states()
        self.diagnosticMessage.emit("Canvas isolation cleared")
        return True

    def isolatedObjectIds(self) -> list[str]:
        return list(self._isolated_ids)

    def _sync_object_states(self) -> None:
        writable_edit = self._edit_mode and not self.isReadOnly()
        isolated = self._isolated_ids
        group_records = {
            model.id: model.to_dict() for model in self._document_model.groups
        }
        collapsed_elements: set[str] = set()
        collapsed_groups: set[str] = set()
        for group_id, record in group_records.items():
            if not bool(record.get("collapsed", False)):
                continue
            collapsed_elements.update(
                descendant_element_ids(group_id, group_records, self._elements)
            )
            pending = list(record.get("members", ()))
            while pending:
                member = str(pending.pop())
                if member in group_records and member not in collapsed_groups:
                    collapsed_groups.add(member)
                    pending.extend(group_records[member].get("members", ()))
        for group_id, item in self._groups.items():
            visible = (
                not item.hidden
                and group_id not in collapsed_groups
                and (not isolated or group_id in isolated)
            )
            item.setVisible(visible)
            item.setEditable(writable_edit and visible)
            if not visible:
                item.setSelected(False)
        for element_id, item in self._elements.items():
            visible = (
                not item.hidden
                and element_id not in collapsed_elements
                and (not isolated or element_id in isolated)
            )
            item.setVisible(visible)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, writable_edit and visible)
            item.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
                writable_edit and visible and not item.locked,
            )
            if not visible:
                item.setSelected(False)
        for connector_id, connector in self._connectors.items():
            visible = (
                not connector.hidden
                and connector.source.isVisible()
                and connector.target.isVisible()
                and (not isolated or connector_id in isolated)
            )
            connector.setVisible(visible)
            connector._handles_editable = writable_edit
            connector.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                writable_edit and visible,
            )
            if not visible:
                connector.setSelected(False)
            connector._sync_waypoint_handles()
        if hasattr(self, "_minimap"):
            self._minimap.update()

    def createContextMenu(self, object_id: str = "") -> QMenu:
        """Build a context-aware menu without displaying it (also useful to hosts/tests)."""
        menu = QMenu(self)
        writable = not self.isReadOnly()
        selected = self.selectedObjectIds()
        selected_elements = self.selectedElementIds()
        clipboard_objects = bool(selected) and all(
            object_id not in self._groups for object_id in selected
        )

        def action(label: str, callback, *, enabled: bool = True, icon: str = ""):
            entry = menu.addAction(_canvas_icon(icon), label) if icon else menu.addAction(label)
            entry.setEnabled(enabled)
            entry.triggered.connect(lambda _checked=False: callback())
            return entry

        if not object_id:
            clipboard = QApplication.clipboard().mimeData()
            can_paste = bool(clipboard and clipboard.hasFormat(CANVAS_CLIPBOARD_MIME_TYPE))
            action("Paste", self.pasteSelection, enabled=writable and can_paste, icon="duplicate")
            action(
                "Import subflow template…",
                self.importSubflowFromDialog,
                enabled=writable,
                icon="folder",
            )
            add_menu = menu.addMenu(_canvas_icon("rectangle"), "Add component")
            for definition in self._element_registry.definitions():
                entry = add_menu.addAction(_canvas_icon(definition.icon), definition.label)
                entry.setEnabled(writable)
                entry.triggered.connect(
                    lambda _checked=False, kind=definition.type_id: self.addPaletteElement(kind)
                )
            menu.addSeparator()
            action("Select all", self.selectAllElements, enabled=bool(self._elements))
            action("Fit all content", self.fitContent, icon="fit")
            layout_menu = menu.addMenu(_canvas_icon("node"), "Auto layout")
            for strategy, label in (
                ("layered", "Layered"), ("tree", "Tree"),
                ("radial", "Radial"), ("force", "Force-directed"),
            ):
                entry = layout_menu.addAction(label)
                entry.setEnabled(writable and len(self._auto_layout_scope_ids("auto")) >= 2)
                entry.triggered.connect(
                    lambda _checked=False, value=strategy: self.autoLayout(value)
                )
            action("Toggle grid", lambda: self.setGridVisible(not self.gridVisible), enabled=writable, icon="grid")
            action("Show all objects", self.showAllObjects, enabled=writable, icon="eye")
            action("Clear isolation", self.clearIsolation, enabled=bool(self._isolated_ids), icon="focus")
            action("Command palette…", self.showCommandPalette, icon="command")
            return menu

        action("Copy", self.copySelection, enabled=clipboard_objects, icon="duplicate")
        action("Cut", self.cutSelection, enabled=writable and clipboard_objects, icon="delete")
        action("Duplicate", self.duplicateSelection, enabled=writable and clipboard_objects, icon="duplicate")
        action("Delete", self.deleteSelected, enabled=writable and bool(selected), icon="delete")
        all_locked = bool(selected) and all(self.objectState(item_id)["locked"] for item_id in selected)
        action(
            "Unlock selection" if all_locked else "Lock selection",
            lambda: self.lockSelected(not all_locked),
            enabled=writable and bool(selected), icon="lock",
        )
        action("Hide selection", self.hideSelected, enabled=writable and bool(selected), icon="eye_off")
        action("Isolate selection", self.isolateSelection, enabled=bool(selected), icon="focus")
        if len(selected_elements) >= 2:
            menu.addSeparator()
            group_menu = menu.addMenu(_canvas_icon("front"), "Create group")
            for kind, label in (
                ("frame", "Frame"),
                ("swimlane", "Swimlane"),
                ("subflow", "Reusable subflow"),
            ):
                entry = group_menu.addAction(label)
                entry.setEnabled(writable)
                entry.triggered.connect(
                    lambda _checked=False, value=kind: self.groupSelected(kind=value)
                )
            align_menu = menu.addMenu("Align")
            for alignment, label in (
                ("left", "Left"), ("hcenter", "Horizontal center"), ("right", "Right"),
                ("top", "Top"), ("vcenter", "Vertical center"), ("bottom", "Bottom"),
            ):
                entry = align_menu.addAction(label)
                entry.setEnabled(writable)
                entry.triggered.connect(
                    lambda _checked=False, value=alignment: self.alignSelected(value)
                )
            size_menu = menu.addMenu("Match size")
            for mode, label in (("width", "Width"), ("height", "Height"), ("both", "Width and height")):
                entry = size_menu.addAction(label)
                entry.setEnabled(writable)
                entry.triggered.connect(
                    lambda _checked=False, value=mode: self.matchSelectedSize(value)
                )
            layout_menu = menu.addMenu(_canvas_icon("node"), "Auto layout")
            for strategy, label in (
                ("layered", "Layered"), ("tree", "Tree"),
                ("radial", "Radial"), ("force", "Force-directed"),
            ):
                entry = layout_menu.addAction(label)
                entry.setEnabled(writable)
                entry.triggered.connect(
                    lambda _checked=False, value=strategy: self.autoLayout(
                        value, scope="selection"
                    )
                )
        menu.addSeparator()
        action("Bring to front", self.bringSelectedToFront, enabled=writable)
        action("Send to back", self.sendSelectedToBack, enabled=writable)
        action("Zoom to selection", self.zoomToSelection, enabled=bool(selected), icon="fit")
        if object_id in self._connectors:
            connector = self._connectors[object_id]
            action("Route around obstacles", lambda: self.autoRouteConnector(object_id), enabled=writable, icon="focus")
            action("Add reroute point", lambda: self.addConnectorWaypoint(object_id), enabled=writable, icon="add")
            action("Clear reroute points", lambda: self.clearConnectorWaypoints(object_id), enabled=writable and bool(connector.waypoints), icon="delete")
            action(
                "Disable crossing bridges" if connector.bridge_crossings else "Enable crossing bridges",
                lambda: self.setConnectorBridges(object_id, not connector.bridge_crossings, connector.bridge_size),
                enabled=writable,
            )
            bus_menu = menu.addMenu("Bus style")
            for style, label in (("none", "None"), ("trunk", "Trunk"), ("double", "Double rail")):
                entry = bus_menu.addAction(label)
                entry.setCheckable(True)
                entry.setChecked(connector.bus_style == style)
                entry.setEnabled(writable)
                entry.triggered.connect(
                    lambda _checked=False, value=style: self.setConnectorBus(
                        object_id, connector.bus_id, style=value, width=connector.bus_width
                    )
                )
            action("Send test message", lambda: self.send_a_message(object_id), enabled=writable)
        elif object_id in self._groups:
            group = self._groups[object_id]
            action(
                "Expand group" if group.collapsed else "Collapse group",
                lambda: self.setGroupCollapsed(object_id, not group.collapsed),
                enabled=writable,
            )
            action(
                "Fit frame to contents",
                lambda: self.fitGroupToContents(object_id),
                enabled=writable and not group.collapsed,
                icon="fit",
            )
            action(
                "Ungroup",
                lambda: self.removeGroup(object_id),
                enabled=writable,
                icon="delete",
            )
            action(
                "Export reusable subflow…",
                lambda: self.exportSubflowToDialog(object_id),
                enabled=True,
                icon="save",
            )
        return menu

    def showContextMenu(self, global_position, object_id: str = "") -> None:
        self.createContextMenu(object_id).exec(global_position)

    def selectionClipboardPayload(self) -> dict[str, Any]:
        """Return the selected subgraph without accessing the system clipboard."""

        return build_selection_payload(
            self._document_model.to_dict(), self.selectedObjectIds()
        )

    def copySelection(self) -> dict[str, Any]:
        """Copy selected nodes and every internal connector as versioned JSON."""

        payload = self.selectionClipboardPayload()
        if not payload["elements"]:
            return {}
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        mime = QMimeData()
        mime.setData(CANVAS_CLIPBOARD_MIME_TYPE, QByteArray(encoded))
        mime.setText(encoded.decode("utf-8"))
        QApplication.clipboard().setMimeData(mime)
        self._clipboard_paste_count = 0
        self.diagnosticMessage.emit(
            f"Copied {len(payload['elements'])} elements and "
            f"{len(payload['connectors'])} connectors"
        )
        return payload

    def cutSelection(self) -> dict[str, Any]:
        """Copy then remove the exact current selection as one undoable command."""

        self._ensure_writable()
        selected = self.selectedObjectIds()
        payload = self.copySelection()
        if not payload:
            return {}

        def remove_selected(document: CanvasDocument) -> None:
            for object_id in selected:
                if document.connector(object_id) is not None:
                    document.remove_connector(object_id)
            for object_id in selected:
                if document.element(object_id) is not None:
                    document.remove_element(object_id)

        self._push_document_mutation(
            remove_selected, f"Cut {len(selected)} object{'s' if len(selected) != 1 else ''}"
        )
        return payload

    def pasteSelection(
        self,
        payload: dict[str, Any] | str | bytes | None = None,
        *,
        offset: tuple[float, float] | None = None,
    ) -> list[str]:
        """Paste a validated clipboard subgraph and return all new object IDs."""

        self._ensure_writable()
        if payload is None:
            mime = QApplication.clipboard().mimeData()
            if mime is None or not mime.hasFormat(CANVAS_CLIPBOARD_MIME_TYPE):
                return []
            payload = bytes(mime.data(CANVAS_CLIPBOARD_MIME_TYPE))
            self._clipboard_paste_count += 1
            distance = 30.0 * self._clipboard_paste_count
            offset = offset or (distance, distance)
        else:
            payload = decode_selection_payload(payload)
            offset = offset or (30.0, 30.0)
        occupied = {*self._elements, *self._connectors}
        elements, connectors, _id_map = remap_selection_payload(
            payload, occupied, offset=offset
        )
        for index, record in enumerate(elements):
            kind = str(record.get("type", "")).lower()
            definition = self._element_registry.definition(kind)
            if definition is None:
                raise ValueError(f"Clipboard element type is not registered: {kind}")
            elements[index] = definition.prepare_record(record)

        def add_records(document: CanvasDocument) -> None:
            for record in elements:
                document.add_element(record)
            for record in connectors:
                document.add_connector(record)

        if not self._push_document_mutation(
            add_records,
            f"Paste {len(elements) + len(connectors)} objects",
        ):
            return []
        new_ids = [str(record["id"]) for record in (*elements, *connectors)]
        self.selectElements(new_ids)
        self.diagnosticMessage.emit(
            f"Pasted {len(elements)} elements and {len(connectors)} connectors"
        )
        return new_ids

    def duplicateSelection(self) -> list[str]:
        """Duplicate the full selected subgraph without replacing clipboard data."""

        payload = self.selectionClipboardPayload()
        if not payload["elements"]:
            return []
        return self.pasteSelection(payload, offset=(30.0, 30.0))

    def nudgeSelected(self, dx: float, dy: float) -> bool:
        """Move selected elements by an exact delta as one mergeable command."""

        if not self._edit_mode:
            return False
        element_ids = tuple(self.selectedElementIds())
        if not element_ids or (not float(dx) and not float(dy)):
            return False

        def move(document: CanvasDocument) -> None:
            for element_id in element_ids:
                record = document.element(element_id)
                if record is not None:
                    values = record.to_dict()
                    document.update_element(
                        element_id,
                        {
                            "x": float(values.get("x", 0.0)) + float(dx),
                            "y": float(values.get("y", 0.0)) + float(dy),
                        },
                    )

        return self._push_document_mutation(
            move,
            f"Nudge {len(element_ids)} object{'s' if len(element_ids) != 1 else ''}",
            merge_key=f"nudge:{','.join(sorted(element_ids))}",
        )

    def addElement(
        self,
        kind: str,
        x: float | None = None,
        y: float | None = None,
        width: float | None = None,
        height: float | None = None,
        element_id: str | None = None,
        **options,
    ) -> str:
        kind = str(kind).lower().strip()
        if kind == "arrow":
            options.setdefault("arrowEnd", True)
            kind = "line"
        elif kind == "polyline":
            kind = "line"
        definition = self._element_registry.definition(kind)
        if kind == "splitter" and not options.get("ports"):
            options["ports"] = _splitter_ports()
        elif (
            kind == "node"
            or definition is not None and "ports" in definition.capabilities
        ) and "ports" not in options:
            options["ports"] = _normalize_node_ports(None)
        if definition is None:
            raise ValueError(f"Unsupported MonkezCanva element type: {kind}")
        default_width, default_height = definition.default_size
        for key, value in definition.defaults.items():
            options.setdefault(key, value)
        element_id = str(element_id or uuid.uuid4().hex[:10])
        if element_id in self._elements or element_id in self._connectors:
            raise ValueError(f"Duplicate MonkezCanva object id: {element_id}")
        if not self._restoring:
            resolved_width = width or default_width
            resolved_height = height or default_height
            center = self._view.mapToScene(self._view.viewport().rect().center())
            record = self._element_model_record(
                element_id,
                kind,
                center.x() - resolved_width / 2 if x is None else float(x),
                center.y() - resolved_height / 2 if y is None else float(y),
                resolved_width,
                resolved_height,
                options,
            )
            prepared_record = definition.prepare_record(record)

            def add_and_record_recent(document: CanvasDocument) -> None:
                document.add_element(prepared_record)
                recent = record_recent_component(
                    document.scene.properties.get(PALETTE_RECENT_KEY, ()), kind
                )
                document.update_scene({PALETTE_RECENT_KEY: list(recent)})

            self._push_document_mutation(
                add_and_record_recent,
                f"Add {definition.label}",
            )
            return element_id
        item = _CanvasElement(
            self,
            element_id,
            kind,
            width or default_width,
            height or default_height,
            options,
            definition,
        )
        center = self._view.mapToScene(self._view.viewport().rect().center())
        item.setPos(center.x() - item._rect.width() / 2 if x is None else x, center.y() - item._rect.height() / 2 if y is None else y)
        item.setEditable(self._edit_mode and not self.isReadOnly())
        item.changed.connect(self._element_changed)
        item.packetArrived.connect(self._on_packet_arrived)
        self._scene.addItem(item)
        self._elements[element_id] = item
        self._sync_object_states()
        if self._edit_mode:
            self._scene.clearSelection()
            item.setSelected(True)
        self.elementAdded.emit(element_id)
        self.documentChanged.emit()
        return element_id

    def addText(self, text: str, x: float = 0, y: float = 0, **options) -> str:
        return self.addElement("text", x, y, text=text, **options)

    def addNode(self, text: str, x: float = 0, y: float = 0, **options) -> str:
        return self.addElement("node", x, y, text=text, **options)

    def addSplitter(self, x: float = 0, y: float = 0, output_count: int = 3, **options) -> str:
        """Add a one-to-many signal junction whose packets propagate to every output."""
        options.setdefault("ports", _splitter_ports(output_count))
        options.setdefault("text", "Splitter")
        return self.addElement("splitter", x, y, **options)

    def nodePorts(self, element_id: str) -> list[dict[str, Any]]:
        item = self._required_element(element_id)
        if not item.supports_ports:
            raise TypeError(f"Element {element_id!r} does not support ports")
        return [dict(port) for port in item.ports]

    def portConnectionCount(
        self, element_id: str, port_id: str, exclude_connector: str = ""
    ) -> int:
        """Return the number of connectors currently attached to one port."""

        element_id, port_id = str(element_id), str(port_id)
        return sum(
            1
            for connector in self._connectors.values()
            if connector.connector_id != str(exclude_connector)
            and (
                connector.source.element_id == element_id
                and connector.source_port == port_id
                or connector.target.element_id == element_id
                and connector.target_port == port_id
            )
        )

    def portCompatibility(
        self,
        first_element_id: str,
        first_port_id: str,
        second_element_id: str,
        second_port_id: str,
        exclude_connector: str = "",
    ) -> PortCompatibility:
        """Evaluate orientation, cardinality, type and unit compatibility."""

        first = self._required_element(first_element_id)
        second = self._required_element(second_element_id)
        first_port = first.port(first_port_id)
        second_port = second.port(second_port_id)
        if first_port is None or second_port is None:
            raise KeyError("Both node ports must exist")
        return evaluate_port_pair(
            first_port,
            second_port,
            first_connections=self.portConnectionCount(
                first.element_id, first_port["id"], exclude_connector
            ),
            second_connections=self.portConnectionCount(
                second.element_id, second_port["id"], exclude_connector
            ),
        )

    def setPortRuntimeValue(
        self, element_id: str, port_id: str, value: Any, validate: bool = True
    ) -> "MonkezCanva":
        """Set a transient, non-persistent value for runtime visualization."""

        item = self._required_element(element_id)
        port = item.port(port_id)
        if port is None:
            raise KeyError(f"Unknown port {port_id!r} on {element_id!r}")
        validation = validate_port_value(port, value)
        if validate and not validation.valid:
            self.diagnosticMessage.emit(validation.reason)
            raise TypeError(validation.reason)
        key = (item.element_id, port["id"])
        self._port_runtime_values[key] = value
        item.update()
        self.portRuntimeValueChanged.emit(key[0], key[1], value)
        return self

    def portRuntimeValue(
        self, element_id: str, port_id: str, use_default: bool = True
    ) -> Any:
        item = self._required_element(element_id)
        port = item.port(port_id)
        if port is None:
            raise KeyError(f"Unknown port {port_id!r} on {element_id!r}")
        key = (item.element_id, port["id"])
        if key in self._port_runtime_values:
            return self._port_runtime_values[key]
        return port.get("defaultValue") if use_default else None

    def portRuntimeState(self, element_id: str, port_id: str) -> dict[str, Any]:
        item = self._required_element(element_id)
        port = item.port(port_id)
        if port is None:
            raise KeyError(f"Unknown port {port_id!r} on {element_id!r}")
        key = (item.element_id, port["id"])
        source = "runtime" if key in self._port_runtime_values else (
            "default" if "defaultValue" in port else "unset"
        )
        value = self.portRuntimeValue(element_id, port_id)
        validation = validate_port_value(port, value)
        return {
            "value": value,
            "source": source,
            "valid": validation.valid,
            "reason": validation.reason,
            "actualType": validation.actual_type,
        }

    def clearPortRuntimeValue(self, element_id: str, port_id: str) -> bool:
        item = self._required_element(element_id)
        if item.port(port_id) is None:
            raise KeyError(f"Unknown port {port_id!r} on {element_id!r}")
        key = (item.element_id, str(port_id))
        if key not in self._port_runtime_values:
            return False
        self._port_runtime_values.pop(key)
        item.update()
        self.portRuntimeValueChanged.emit(key[0], key[1], None)
        return True

    def setNodePorts(self, element_id: str, ports) -> "MonkezCanva":
        item = self._required_element(element_id)
        if not item.supports_ports:
            raise TypeError(f"Element {element_id!r} does not support ports")
        if not self._restoring:
            self._ensure_writable()
            normalized = _normalize_node_ports(ports)
            valid_ids = {port["id"] for port in normalized}

            def mutate(document: CanvasDocument) -> None:
                for connector in tuple(document.connectors):
                    changes: dict[str, str] = {}
                    if connector.source == str(element_id) and connector.source_port not in valid_ids:
                        changes["sourcePort"] = ""
                    if connector.target == str(element_id) and connector.target_port not in valid_ids:
                        changes["targetPort"] = ""
                    if changes:
                        document.update_connector(connector.id, changes)
                document.update_element(str(element_id), {"ports": normalized})

            self._push_document_mutation(
                mutate, "Edit node ports", merge_key=f"element:{element_id}"
            )
            return self
        item.ports = _normalize_node_ports(ports)
        valid_ids = {port["id"] for port in item.ports}
        for key in tuple(self._port_runtime_values):
            if key[0] == item.element_id and key[1] not in valid_ids:
                self._port_runtime_values.pop(key, None)
        for connector in self._connectors.values():
            if connector.source is item and connector.source_port not in valid_ids:
                connector.source_port = ""
            if connector.target is item and connector.target_port not in valid_ids:
                connector.target_port = ""
            connector.updatePath()
        item.update()
        self.documentChanged.emit()
        return self

    def addNodePort(
        self,
        element_id: str,
        port_id: str,
        mode: str = "free",
        side: str | None = None,
        label: str = "",
        position: float | None = None,
        **properties,
    ) -> "MonkezCanva":
        ports = self.nodePorts(element_id)
        port: dict[str, Any] = {
            "id": port_id, "mode": mode, "label": label or port_id, **properties
        }
        if side is not None:
            port["side"] = side
        if position is not None:
            port["position"] = position
        ports.append(port)
        return self.setNodePorts(element_id, ports)

    def removeNodePort(self, element_id: str, port_id: str) -> bool:
        ports = self.nodePorts(element_id)
        filtered = [port for port in ports if port["id"] != str(port_id)]
        if len(filtered) == len(ports):
            return False
        self.setNodePorts(element_id, filtered)
        return True

    def addLine(self, x: float = 0, y: float = 0, **options) -> str:
        return self.addElement("line", x, y, **options)

    def addPolyline(self, points, x: float = 0, y: float = 0, **options) -> str:
        options["points"] = [[float(point[0]), float(point[1])] for point in points]
        return self.addElement("line", x, y, **options)

    def addChart(self, values, chart_type: str = "bar", x: float = 0, y: float = 0, **options) -> str:
        kind = "line_chart" if str(chart_type).lower() == "line" else "bar_chart"
        return self.addElement(kind, x, y, data=list(values), **options)

    def addMedia(
        self,
        path: str | Path,
        x: float | None = None,
        y: float | None = None,
        animated: bool | None = None,
        **options,
    ) -> str:
        source = str(Path(path).expanduser().resolve())
        if not Path(source).is_file():
            raise FileNotFoundError(source)
        is_animated = Path(source).suffix.lower() == ".gif" if animated is None else bool(animated)
        kind = "animated_image" if is_animated else "image"
        options.setdefault("text", Path(source).name)
        return self.addElement(kind, x, y, source=source, **options)

    def selectElement(self, element_id: str, additive: bool = False) -> bool:
        item = self.canvasObject(str(element_id))
        if item is None:
            return False
        if not additive:
            self._scene.clearSelection()
        if self._edit_mode:
            item.setSelected(True)
        else:
            self.selectionChanged.emit(item.element_id)
            self.selectionSetChanged.emit([item.element_id])
        self._view.centerOn(item)
        return True

    def selectElements(self, element_ids, clear: bool = True) -> list[str]:
        requested = [str(element_id) for element_id in element_ids]
        if clear:
            self._scene.clearSelection()
        if not self._edit_mode:
            return []
        selected = []
        for element_id in requested:
            item = self.canvasObject(element_id)
            if item is not None:
                item.setSelected(True)
                selected.append(element_id)
        return selected

    def alignSelected(self, alignment: str) -> bool:
        self._ensure_writable()
        alignment = str(alignment).lower().replace("-", "").replace("_", "")
        aliases = {"horizontalcenter": "hcenter", "verticalcenter": "vcenter", "middle": "center"}
        alignment = aliases.get(alignment, alignment)
        supported = {"left", "right", "top", "bottom", "hcenter", "vcenter", "center"}
        if alignment not in supported:
            raise ValueError(f"Unsupported MonkezCanva alignment: {alignment}")
        items = [self._elements[element_id] for element_id in self.selectedElementIds()]
        if len(items) < 2:
            return False
        bounds = [item.sceneBoundingRect() for item in items]
        group = QRectF(bounds[0])
        for item_bounds in bounds[1:]:
            group = group.united(item_bounds)

        previous_restoring = self._restoring
        previous_snap = self._snap_to_grid
        self._restoring = True
        self._snap_to_grid = False
        try:
            for item, item_bounds in zip(items, bounds):
                dx = 0.0
                dy = 0.0
                if alignment == "left":
                    dx = group.left() - item_bounds.left()
                elif alignment == "right":
                    dx = group.right() - item_bounds.right()
                elif alignment == "top":
                    dy = group.top() - item_bounds.top()
                elif alignment == "bottom":
                    dy = group.bottom() - item_bounds.bottom()
                elif alignment == "hcenter":
                    dx = group.center().x() - item_bounds.center().x()
                elif alignment == "vcenter":
                    dy = group.center().y() - item_bounds.center().y()
                else:
                    dx = group.center().x() - item_bounds.center().x()
                    dy = group.center().y() - item_bounds.center().y()
                item.setPos(item.pos() + QPointF(dx, dy))
        finally:
            self._snap_to_grid = previous_snap
            self._restoring = previous_restoring
        if not previous_restoring:
            self.documentChanged.emit()
        self.diagnosticMessage.emit(
            f"Aligned {len(items)} items: {alignment}"
        )
        return True

    def alignSelectedLeft(self) -> bool:
        return self.alignSelected("left")

    def alignSelectedRight(self) -> bool:
        return self.alignSelected("right")

    def alignSelectedTop(self) -> bool:
        return self.alignSelected("top")

    def alignSelectedBottom(self) -> bool:
        return self.alignSelected("bottom")

    def alignSelectedCenter(self) -> bool:
        return self.alignSelected("center")

    def distributeSelected(self, direction: str = "horizontal") -> bool:
        """Evenly distribute three or more selected elements by their centers."""
        self._ensure_writable()
        direction = str(direction).lower().strip()
        aliases = {"h": "horizontal", "x": "horizontal", "v": "vertical", "y": "vertical"}
        direction = aliases.get(direction, direction)
        if direction not in ("horizontal", "vertical"):
            raise ValueError(f"Unsupported MonkezCanva distribution: {direction}")
        items = [self._elements[element_id] for element_id in self.selectedElementIds()]
        if len(items) < 3:
            return False
        coordinate = (
            (lambda item: item.sceneBoundingRect().center().x())
            if direction == "horizontal"
            else (lambda item: item.sceneBoundingRect().center().y())
        )
        items.sort(key=coordinate)
        start = coordinate(items[0])
        step = (coordinate(items[-1]) - start) / (len(items) - 1)
        previous_restoring = self._restoring
        previous_snap = self._snap_to_grid
        self._restoring = True
        self._snap_to_grid = False
        try:
            for index, item in enumerate(items[1:-1], 1):
                delta = start + step * index - coordinate(item)
                offset = QPointF(delta, 0) if direction == "horizontal" else QPointF(0, delta)
                item.setPos(item.pos() + offset)
        finally:
            self._snap_to_grid = previous_snap
            self._restoring = previous_restoring
        if not previous_restoring:
            self.documentChanged.emit()
        self.diagnosticMessage.emit(f"Distributed {len(items)} items: {direction}")
        return True

    def distributeSelectedHorizontally(self) -> bool:
        return self.distributeSelected("horizontal")

    def distributeSelectedVertically(self) -> bool:
        return self.distributeSelected("vertical")

    def _auto_layout_scope_ids(
        self,
        scope: str,
        element_ids: Any = None,
        group_id: str = "",
    ) -> tuple[list[str], str]:
        requested_scope = str(scope or "auto").lower().strip().replace("_", "-")
        requested_scope = {
            "all": "document", "canvas": "document", "selected": "selection",
            "connected": "component", "subflow": "group",
        }.get(requested_scope, requested_scope)
        group_records = {
            model.id: model.to_dict() for model in self._document_model.groups
        }
        if element_ids is not None:
            requested = list(dict.fromkeys(str(value) for value in element_ids))
            return [value for value in requested if value in self._elements], "explicit"
        selected_objects = self.selectedObjectIds()
        selected_elements = self.selectedElementIds()
        selected_group = str(group_id or next(
            (object_id for object_id in selected_objects if object_id in self._groups), ""
        ))
        if requested_scope == "auto":
            requested_scope = (
                "group" if selected_group else
                "selection" if len(selected_elements) >= 2 else
                "component" if selected_elements else "document"
            )
        if requested_scope == "document":
            return list(self._elements), requested_scope
        if requested_scope == "selection":
            requested = list(selected_elements)
            for selected_id in selected_objects:
                if selected_id in group_records:
                    requested.extend(
                        descendant_element_ids(
                            selected_id, group_records, self._elements
                        )
                    )
            return list(dict.fromkeys(requested)), requested_scope
        if requested_scope == "group":
            if not selected_group or selected_group not in group_records:
                raise ValueError("Auto-layout group scope requires a selected or explicit group")
            return list(
                descendant_element_ids(selected_group, group_records, self._elements)
            ), requested_scope
        if requested_scope == "component":
            seeds = selected_elements
            if not seeds:
                raise ValueError("Auto-layout component scope requires a selected element")
            adjacency: dict[str, list[str]] = defaultdict(list)
            for connector in self._document_model.connectors:
                adjacency[connector.source].append(connector.target)
                adjacency[connector.target].append(connector.source)
            result: list[str] = []
            seen: set[str] = set()
            queue = deque(seeds)
            while queue:
                current = queue.popleft()
                if current in seen or current not in self._elements:
                    continue
                seen.add(current)
                result.append(current)
                queue.extend(adjacency[current])
            return result, requested_scope
        raise ValueError(f"Unsupported MonkezCanva auto-layout scope: {scope}")

    def _auto_layout_input(
        self,
        scope: str,
        element_ids: Any,
        group_id: str,
        include_hidden: bool,
        include_lines: bool,
        respect_locked: bool,
    ) -> tuple[list[LayoutNode], list[LayoutEdge], list[str], str]:
        requested_ids, resolved_scope = self._auto_layout_scope_ids(
            scope, element_ids, group_id
        )
        nodes: list[LayoutNode] = []
        included: list[str] = []
        for element_id in requested_ids:
            model = self._document_model.element(element_id)
            if model is None:
                continue
            record = model.to_dict()
            if not include_hidden and bool(record.get("hidden", False)):
                continue
            if not include_lines and model.type == "line":
                continue
            nodes.append(
                LayoutNode(
                    element_id,
                    float(record.get("x", 0.0)),
                    float(record.get("y", 0.0)),
                    max(1.0, float(record.get("width", 120.0))),
                    max(1.0, float(record.get("height", 72.0))),
                    respect_locked and bool(record.get("locked", False)),
                )
            )
            included.append(element_id)
        included_set = set(included)
        edges = [
            LayoutEdge(connector.source, connector.target)
            for connector in self._document_model.connectors
            if connector.source in included_set and connector.target in included_set
        ]
        return nodes, edges, included, resolved_scope

    def computeAutoLayout(
        self,
        strategy: str = "layered",
        direction: str = "right",
        *,
        scope: str = "auto",
        element_ids: Any = None,
        group_id: str = "",
        node_spacing: float = 48.0,
        layer_spacing: float = 120.0,
        component_spacing: float = 160.0,
        iterations: int = 180,
        preserve_center: bool = True,
        include_hidden: bool = False,
        include_lines: bool = False,
        respect_locked: bool = True,
    ) -> LayoutResult:
        """Compute an auto-layout without mutating the canonical document."""

        nodes, edges, _included, _resolved_scope = self._auto_layout_input(
            scope, element_ids, group_id, include_hidden, include_lines, respect_locked
        )
        return layout_graph(
            nodes,
            edges,
            options=LayoutOptions(
                strategy=strategy,
                direction=direction,
                node_spacing=node_spacing,
                layer_spacing=layer_spacing,
                component_spacing=component_spacing,
                iterations=iterations,
                preserve_center=preserve_center,
            ),
        )

    def autoLayout(
        self,
        strategy: str = "layered",
        direction: str = "right",
        *,
        scope: str = "auto",
        element_ids: Any = None,
        group_id: str = "",
        node_spacing: float = 48.0,
        layer_spacing: float = 120.0,
        component_spacing: float = 160.0,
        iterations: int = 180,
        preserve_center: bool = True,
        include_hidden: bool = False,
        include_lines: bool = False,
        respect_locked: bool = True,
        fit_groups: bool = True,
        fit_view: bool = False,
    ) -> LayoutResult:
        """Apply a deterministic layout as one undoable document command."""

        self._ensure_writable()
        nodes, edges, included, resolved_scope = self._auto_layout_input(
            scope, element_ids, group_id, include_hidden, include_lines, respect_locked
        )
        result = layout_graph(
            nodes,
            edges,
            options=LayoutOptions(
                strategy=strategy,
                direction=direction,
                node_spacing=node_spacing,
                layer_spacing=layer_spacing,
                component_spacing=component_spacing,
                iterations=iterations,
                preserve_center=preserve_center,
            ),
        )
        if not result.moved_count:
            self.diagnosticMessage.emit(
                f"Auto-layout {result.strategy}: no movable items in {resolved_scope} scope"
            )
            return result
        included_set = set(included)
        group_records = {
            model.id: model.to_dict() for model in self._document_model.groups
        }
        fitted_groups: list[str] = []
        if fit_groups:
            for current_id, record in group_records.items():
                descendants = set(
                    descendant_element_ids(current_id, group_records, self._elements)
                )
                if (
                    descendants
                    and descendants.issubset(included_set)
                    and not bool(record.get("locked", False))
                ):
                    fitted_groups.append(current_id)

        def mutate(document: CanvasDocument) -> None:
            for element_id, (x, y) in result.positions.items():
                model = document.element(element_id)
                if model is None or (respect_locked and bool(model.properties.get("locked", False))):
                    continue
                document.update_element(element_id, {"x": x, "y": y})
            for current_id in fitted_groups:
                model = document.group(current_id)
                if model is None:
                    continue
                descendants = descendant_element_ids(
                    current_id, group_records, self._elements
                )
                rectangles = []
                for element_id in descendants:
                    element = document.element(element_id)
                    if element is None:
                        continue
                    record = element.to_dict()
                    rectangles.append((
                        float(record.get("x", 0.0)), float(record.get("y", 0.0)),
                        float(record.get("width", 120.0)), float(record.get("height", 72.0)),
                    ))
                x, y, width, height = group_bounds(
                    rectangles,
                    padding=float(model.properties.get("padding", 28.0)),
                )
                document.update_group(
                    current_id, {"x": x, "y": y, "width": width, "height": height}
                )

        changed = self._push_document_mutation(
            mutate, f"Auto layout ({result.strategy})"
        )
        metrics = {
            "strategy": result.strategy,
            "direction": result.direction,
            "scope": resolved_scope,
            "items": len(result.positions),
            "moved": result.moved_count,
            "components": result.component_count,
            "layers": result.layer_count,
            "groupsFitted": len(fitted_groups),
            "changed": changed,
        }
        self.layoutApplied.emit(metrics)
        self.diagnosticMessage.emit(
            f"Auto-layout {result.strategy}/{result.direction}: "
            f"moved {result.moved_count}/{len(result.positions)} items; "
            f"components={result.component_count}; layers={result.layer_count}; "
            f"scope={resolved_scope}"
        )
        if fit_view and result.bounds[2] > 0 and result.bounds[3] > 0:
            self._apply_fit_content(QRectF(*result.bounds))
        return result

    def autoLayoutSelection(self, strategy: str = "layered", **options) -> LayoutResult:
        return self.autoLayout(strategy, scope="selection", **options)

    def autoLayoutGroup(
        self, group_id: str, strategy: str = "layered", **options
    ) -> LayoutResult:
        return self.autoLayout(strategy, scope="group", group_id=group_id, **options)

    def matchSelectedSize(self, mode: str = "both") -> bool:
        """Match selected element dimensions to the first selected element."""
        normalized = str(mode).lower().replace("-", "").replace("_", "")
        aliases = {"w": "width", "h": "height", "size": "both"}
        normalized = aliases.get(normalized, normalized)
        if normalized not in ("width", "height", "both"):
            raise ValueError(f"Unsupported MonkezCanva size match: {mode}")
        element_ids = self.selectedElementIds()
        if len(element_ids) < 2:
            return False
        reference = self._document_model.element(element_ids[0]).to_dict()

        def mutate(document: CanvasDocument) -> None:
            changes = {}
            if normalized in ("width", "both"):
                changes["width"] = float(reference.get("width", 120.0))
            if normalized in ("height", "both"):
                changes["height"] = float(reference.get("height", 72.0))
            for element_id in element_ids[1:]:
                document.update_element(element_id, changes)

        changed = self._push_document_mutation(mutate, f"Match {normalized}")
        if changed:
            self.diagnosticMessage.emit(
                f"Matched {normalized} for {len(element_ids)} items"
            )
        return changed

    def matchSelectedWidth(self) -> bool:
        return self.matchSelectedSize("width")

    def matchSelectedHeight(self) -> bool:
        return self.matchSelectedSize("height")

    def matchSelectedDimensions(self) -> bool:
        return self.matchSelectedSize("both")

    def renameElement(self, element_id: str, new_id: str) -> str:
        if not self._restoring:
            self._ensure_writable()
            requested = str(new_id).strip()
            candidate = CanvasDocument.from_dict(self._document_model.to_dict())
            events = candidate.rename_element(element_id, requested)
            if events:
                self._undo_stack.push(
                    CanvasRenameCommand(
                        self._document_model, str(element_id), requested
                    )
                )
                return requested
            return str(element_id)
        item = self._required_element(element_id)
        requested = str(new_id).strip()
        if not requested:
            raise ValueError("MonkezCanva item ID cannot be empty")
        if requested != element_id and (requested in self._elements or requested in self._connectors):
            raise ValueError(f"Duplicate MonkezCanva object id: {requested}")
        if requested == element_id:
            return requested
        self._elements.pop(element_id)
        item.element_id = requested
        self._elements[requested] = item
        if element_id in self._animations:
            self._animations[requested] = self._animations.pop(element_id)
        for key in tuple(self._port_runtime_values):
            if key[0] == element_id:
                self._port_runtime_values[(requested, key[1])] = self._port_runtime_values.pop(key)
        self.itemIdChanged.emit(element_id, requested)
        self.documentChanged.emit()
        return requested

    def updateElement(self, element_id: str, **values) -> "MonkezCanva":
        if not self._restoring:
            model = self._document_model.element(element_id)
            if model is None:
                raise KeyError(f"Unknown MonkezCanva element: {element_id}")
            current = model.to_dict()
            current.update(self._model_values(values))
            kind = str(current["type"])
            source = str(current.get("source", ""))
            if "source" in values and kind in ("image", "animated_image") and source:
                kind = "animated_image" if Path(source).suffix.lower() == ".gif" else "image"
            if str(current.get("animationEffect", "flow")).lower() not in _LINE_EFFECTS:
                raise ValueError(
                    f"Unsupported line animation effect: {current['animationEffect']}"
                )
            definition = self._element_registry.require(kind)
            default_width, default_height = definition.default_size
            normalized = self._element_model_record(
                str(element_id),
                kind,
                float(current.get("x", 0.0)),
                float(current.get("y", 0.0)),
                float(current.get("width", default_width)),
                float(current.get("height", default_height)),
                current,
            )
            prepared = definition.prepare_record(normalized)
            self._push_document_mutation(
                lambda document: document.update_element(element_id, prepared),
                f"Update {definition.label}",
                merge_key=f"element:{element_id}",
            )
            return self
        item = self._required_element(element_id)
        object_state_changed = (
            "locked" in values and bool(values["locked"]) != item.locked
            or "hidden" in values and bool(values["hidden"]) != item.hidden
        )
        if "x" in values or "y" in values:
            item.setPos(float(values.get("x", item.pos().x())), float(values.get("y", item.pos().y())))
        if "width" in values or "height" in values:
            item.prepareGeometryChange()
            item._rect.setWidth(max(24.0, float(values.get("width", item._rect.width()))))
            item._rect.setHeight(max(24.0, float(values.get("height", item._rect.height()))))
        if "text" in values:
            item.text = str(values["text"])
        if "source" in values and str(values["source"]) != item.source:
            source = str(values["source"])
            if item.kind in ("image", "animated_image") and source:
                item.kind = "animated_image" if Path(source).suffix.lower() == ".gif" else "image"
            item.setSource(source)
        if "rotation" in values:
            item.setRotation(float(values["rotation"]))
        if "opacity" in values:
            item.setOpacity(max(0.0, min(1.0, float(values["opacity"]))))
        if "z" in values:
            item.setZValue(float(values["z"]))
        if "metadata" in values:
            item.metadata = dict(values["metadata"])
        if "locked" in values:
            item.locked = bool(values["locked"])
        if "hidden" in values:
            item.hidden = bool(values["hidden"])
        if "data" in values:
            item.data = list(values["data"])
        if "lineWidth" in values:
            item.line_width = max(0.5, float(values["lineWidth"]))
        if "lineStyle" in values:
            item.line_style = str(values["lineStyle"]).lower()
        if "arrowStart" in values:
            item.arrow_start = bool(values["arrowStart"])
        if "arrowEnd" in values:
            item.arrow_end = bool(values["arrowEnd"])
        if "animated" in values:
            item.animated = bool(values["animated"])
        if "animationEffect" in values:
            effect = str(values["animationEffect"]).lower()
            if effect not in _LINE_EFFECTS:
                raise ValueError(f"Unsupported line animation effect: {effect}")
            item.animation_effect = effect
        if "flowColor" in values:
            item.flow_color = _color(values["flowColor"], "#38bdf8")
        if "flowSpeed" in values:
            item.flow_speed = max(0.1, float(values["flowSpeed"]))
        if "flowDirection" in values:
            item.flow_direction = -1 if str(values["flowDirection"]).lower() == "reverse" else 1
        if "flowSpacing" in values:
            item.flow_spacing = max(1.0, float(values["flowSpacing"]))
        if "effectIntensity" in values:
            item.effect_intensity = max(0.2, min(4.0, float(values["effectIntensity"])))
        if "packetLoop" in values:
            item.packet_loop = bool(values["packetLoop"])
        if "packetDuration" in values:
            item.packet_duration = max(0.1, float(values["packetDuration"]))
        if "packetInterval" in values:
            item.packet_interval = max(0.05, float(values["packetInterval"]))
        if "packetIcon" in values:
            item.packet_icon = str(values["packetIcon"])
        if "points" in values:
            item.points = [QPointF(float(point[0]), float(point[1])) for point in values["points"]]
        if "ports" in values:
            self.setNodePorts(element_id, values["ports"])
        item.custom_properties.update(
            {
                key: value for key, value in values.items()
                if key not in _ELEMENT_STANDARD_PROPERTIES
            }
        )
        item._sync_line_animation()
        item.changed.emit(item.element_id)
        if object_state_changed:
            self._sync_object_states()
        self.documentChanged.emit()
        return self

    def duplicateSelected(self) -> str:
        """Compatibility helper returning the first ID from graph duplication."""

        duplicated = self.duplicateSelection()
        return duplicated[0] if duplicated else ""

    def bringSelectedToFront(self) -> None:
        self._ensure_writable()
        item = self.canvasObject(self.selectedElementId())
        if item is not None:
            objects = [*self._elements.values(), *self._connectors.values()]
            item.setZValue(max((entry.zValue() for entry in objects), default=0) + 1)
            self.documentChanged.emit()

    def sendSelectedToBack(self) -> None:
        self._ensure_writable()
        item = self.canvasObject(self.selectedElementId())
        if item is not None:
            objects = [*self._elements.values(), *self._connectors.values()]
            item.setZValue(min((entry.zValue() for entry in objects), default=0) - 1)
            self.documentChanged.emit()

    def connectElements(
        self,
        source_id: str,
        target_id: str,
        color: Any = "#64748b",
        connector_id: str | None = None,
        **options,
    ) -> str:
        source = self._elements.get(str(source_id))
        target = self._elements.get(str(target_id))
        if source is None or target is None:
            raise KeyError("Both connector endpoints must exist")
        source_port = str(options.get("sourcePort", ""))
        target_port = str(options.get("targetPort", ""))
        if source.supports_ports and target.supports_ports and (
            not source_port or not target_port
        ):
            source_candidates = (
                [source.port(source_port)] if source_port
                else [port for port in source.ports if port["mode"] in ("output", "free")]
            )
            target_candidates = (
                [target.port(target_port)] if target_port
                else [port for port in target.ports if port["mode"] in ("input", "free")]
            )
            for source_candidate in filter(None, source_candidates):
                for target_candidate in filter(None, target_candidates):
                    compatibility = evaluate_directed_ports(
                        source_candidate,
                        target_candidate,
                        source_connections=self.portConnectionCount(
                            source.element_id, source_candidate["id"]
                        ),
                        target_connections=self.portConnectionCount(
                            target.element_id, target_candidate["id"]
                        ),
                    )
                    if compatibility.compatible:
                        source_port = source_candidate["id"]
                        target_port = target_candidate["id"]
                        break
                if source_port and target_port:
                    break
        if source.supports_ports and not source_port:
            source_port = next(
                (port["id"] for port in source.ports if port["mode"] in ("output", "free")), ""
            )
        if target.supports_ports and not target_port:
            target_port = next(
                (port["id"] for port in target.ports if port["mode"] in ("input", "free")), ""
            )
        self._validate_connection_ports(source, source_port, target, target_port)
        options["sourcePort"] = source_port
        options["targetPort"] = target_port
        connector_id = str(connector_id or uuid.uuid4().hex[:10])
        if connector_id in self._connectors or connector_id in self._elements:
            raise ValueError(f"Duplicate MonkezCanva object id: {connector_id}")
        options.setdefault("color", color)
        if not self._restoring:
            record = self._connector_model_record(
                connector_id, source.element_id, target.element_id, options
            )
            self._push_document_mutation(
                lambda document: document.add_connector(record),
                "Connect elements",
            )
            return connector_id
        connector = _CanvasConnector(self, connector_id, source, target, options)
        connector.changed.connect(self._connector_changed)
        connector.packetArrived.connect(self._on_packet_arrived)
        self._scene.addItem(connector)
        self._connectors[connector_id] = connector
        for sibling in self._connectors.values():
            if {sibling.source.element_id, sibling.target.element_id} == {source_id, target_id}:
                sibling.updatePath()
        self._sync_object_states()
        self.connectorAdded.emit(connector_id)
        self.documentChanged.emit()
        return connector_id

    def _validate_connection_ports(
        self,
        source: _CanvasElement,
        source_port: str,
        target: _CanvasElement,
        target_port: str,
        exclude_connector: str = "",
    ) -> None:
        source_config = source.port(source_port) if source_port else None
        target_config = target.port(target_port) if target_port else None
        if source_port and source_config is None:
            raise KeyError(f"Unknown source port {source_port!r} on {source.element_id!r}")
        if target_port and target_config is None:
            raise KeyError(f"Unknown target port {target_port!r} on {target.element_id!r}")
        if source_config and target_config:
            compatibility = evaluate_directed_ports(
                source_config,
                target_config,
                source_connections=self.portConnectionCount(
                    source.element_id, source_port, exclude_connector
                ),
                target_connections=self.portConnectionCount(
                    target.element_id, target_port, exclude_connector
                ),
            )
            if not compatibility.compatible:
                raise ValueError(compatibility.reason)
        elif source_config and source_config["mode"] == "input":
            raise ValueError("A connector cannot start from an input port")
        elif target_config and target_config["mode"] == "output":
            raise ValueError("A connector cannot end at an output port")

    def connectPorts(
        self,
        first_element_id: str,
        first_port_id: str,
        second_element_id: str,
        second_port_id: str,
        **options,
    ) -> str:
        """Connect two ports, automatically orienting output -> input where possible."""
        first = self._required_element(first_element_id)
        second = self._required_element(second_element_id)
        first_port = first.port(first_port_id)
        second_port = second.port(second_port_id)
        if first_port is None or second_port is None:
            raise KeyError("Both node ports must exist")
        compatibility = self.portCompatibility(
            first.element_id, first_port["id"], second.element_id, second_port["id"]
        )
        if not compatibility.compatible:
            raise ValueError(compatibility.reason)
        if not compatibility.source_is_first:
            first, second = second, first
            first_port, second_port = second_port, first_port
        options["sourcePort"] = first_port["id"]
        options["targetPort"] = second_port["id"]
        return self.connectElements(first.element_id, second.element_id, **options)

    def connectSelected(self, **options) -> str:
        """Connect exactly two selected elements and select the new connector."""
        selected = self.selectedElementIds()
        if len(selected) != 2:
            self.diagnosticMessage.emit("Select exactly two elements to create a connector")
            return ""
        connector_id = self.connectElements(selected[0], selected[1], **options)
        if self._edit_mode:
            self._scene.clearSelection()
            self._connectors[connector_id].setSelected(True)
        return connector_id

    def reconnectConnector(
        self,
        connector_id: str,
        source_id: str,
        target_id: str,
        source_port: str | None = None,
        target_port: str | None = None,
    ) -> "MonkezCanva":
        """Change connector endpoints while preserving its ID and visual settings."""
        if not self._restoring:
            self._ensure_writable()
        connector = self._required_connector(connector_id)
        source = self._required_element(source_id)
        target = self._required_element(target_id)
        source_port = connector.source_port if source_port is None else str(source_port)
        target_port = connector.target_port if target_port is None else str(target_port)
        if source is not connector.source and source_port and source.port(source_port) is None:
            source_port = ""
        if target is not connector.target and target_port and target.port(target_port) is None:
            target_port = ""
        if source.supports_ports and not source_port:
            source_port = next((port["id"] for port in source.ports if port["mode"] in ("output", "free")), "")
        if target.supports_ports and not target_port:
            target_port = next((port["id"] for port in target.ports if port["mode"] in ("input", "free")), "")
        self._validate_connection_ports(
            source, source_port, target, target_port, connector.connector_id
        )
        if (
            connector.source is source and connector.target is target
            and connector.source_port == source_port and connector.target_port == target_port
        ):
            return self
        for endpoint in (connector.source, connector.target):
            try:
                endpoint.changed.disconnect(connector.updatePath)
            except TypeError:
                pass
        connector.source = source
        connector.target = target
        connector.source_port = source_port
        connector.target_port = target_port
        source.changed.connect(connector.updatePath)
        target.changed.connect(connector.updatePath)
        connector.updatePath()
        connector.changed.emit(connector.connector_id)
        return self

    def connector(self, connector_id: str) -> _CanvasConnector | None:
        return self._connectors.get(str(connector_id))

    def connectors(self) -> list[str]:
        return list(self._connectors)

    def addConnectorWaypoint(
        self, connector_id: str, point: QPointF | tuple[float, float] | None = None,
        index: int | None = None,
    ) -> int:
        connector = self._required_connector(connector_id)
        resolved = connector._path.pointAtPercent(0.5) if point is None else QPointF(*point) if isinstance(point, tuple) else QPointF(point)
        waypoints = [[item.x(), item.y()] for item in connector.waypoints]
        position = len(waypoints) if index is None else max(0, min(len(waypoints), int(index)))
        waypoints.insert(position, [resolved.x(), resolved.y()])
        self.updateConnector(connector_id, waypoints=waypoints)
        return position

    def moveConnectorWaypoint(
        self, connector_id: str, index: int, point: QPointF | tuple[float, float]
    ) -> bool:
        connector = self._required_connector(connector_id)
        position = int(index)
        if position < 0 or position >= len(connector.waypoints):
            return False
        resolved = QPointF(*point) if isinstance(point, tuple) else QPointF(point)
        waypoints = [[item.x(), item.y()] for item in connector.waypoints]
        waypoints[position] = [resolved.x(), resolved.y()]
        self.updateConnector(connector_id, waypoints=waypoints)
        return True

    def removeConnectorWaypoint(self, connector_id: str, index: int) -> bool:
        connector = self._required_connector(connector_id)
        position = int(index)
        if position < 0 or position >= len(connector.waypoints):
            return False
        waypoints = [[item.x(), item.y()] for item in connector.waypoints]
        waypoints.pop(position)
        self.updateConnector(connector_id, waypoints=waypoints)
        return True

    def clearConnectorWaypoints(self, connector_id: str) -> bool:
        connector = self._required_connector(connector_id)
        if not connector.waypoints:
            return False
        self.updateConnector(connector_id, waypoints=[])
        return True

    def setConnectorLabel(
        self, connector_id: str, label: str, position: float = 0.5
    ) -> "MonkezCanva":
        return self.updateConnector(
            connector_id, label=str(label), labelPosition=float(position)
        )

    def autoRouteConnector(
        self, connector_id: str, clearance: float | None = None
    ) -> "MonkezCanva":
        values: dict[str, Any] = {"route": "auto"}
        if clearance is not None:
            values["obstacleClearance"] = float(clearance)
        return self.updateConnector(connector_id, **values)

    def setConnectorBus(
        self,
        connector_id: str,
        bus_id: str = "",
        *,
        style: str = "trunk",
        width: float = 10.0,
    ) -> "MonkezCanva":
        return self.updateConnector(
            connector_id,
            busId=str(bus_id),
            busStyle=str(style).lower(),
            busWidth=float(width),
        )

    def setConnectorBridges(
        self, connector_id: str, enabled: bool = True, size: float = 7.0
    ) -> "MonkezCanva":
        return self.updateConnector(
            connector_id, bridgeCrossings=bool(enabled), bridgeSize=float(size)
        )

    def updateConnector(self, connector_id: str, **values) -> "MonkezCanva":
        if not self._restoring:
            model = self._document_model.connector(connector_id)
            if model is None:
                raise KeyError(f"Unknown MonkezCanva connector: {connector_id}")
            current = model.to_dict()
            current.update(self._model_values(values))
            route = str(current.get("route", "bezier")).lower()
            if route not in ("bezier", "auto", "orthogonal", "straight", "polyline"):
                raise ValueError(f"Unsupported connector route: {route}")
            style = str(current.get("lineStyle", "solid")).lower()
            if style not in ("solid", "dash", "dot", "dashdot"):
                raise ValueError(f"Unsupported connector line style: {style}")
            effect = str(current.get("animationEffect", "flow")).lower()
            if effect not in _LINE_EFFECTS:
                raise ValueError(f"Unsupported connector animation effect: {effect}")
            bus_style = str(current.get("busStyle", "none")).lower()
            if bus_style not in ("none", "trunk", "double"):
                raise ValueError(f"Unsupported connector bus style: {bus_style}")
            source = self._required_element(str(current["source"]))
            target = self._required_element(str(current["target"]))
            self._validate_connection_ports(
                source,
                str(current.get("sourcePort", "")),
                target,
                str(current.get("targetPort", "")),
            )
            normalized = self._connector_model_record(
                str(connector_id),
                source.element_id,
                target.element_id,
                current,
            )
            self._push_document_mutation(
                lambda document: document.update_connector(connector_id, normalized),
                "Update connector",
                merge_key=f"connector:{connector_id}",
            )
            return self
        connector = self._required_connector(connector_id)
        object_state_changed = (
            "locked" in values and bool(values["locked"]) != connector.locked
            or "hidden" in values and bool(values["hidden"]) != connector.hidden
        )
        if any(key in values for key in ("source", "target", "sourcePort", "targetPort")):
            self.reconnectConnector(
                connector_id,
                str(values.get("source", connector.source.element_id)),
                str(values.get("target", connector.target.element_id)),
                str(values.get("sourcePort", connector.source_port)),
                str(values.get("targetPort", connector.target_port)),
            )
            connector = self._required_connector(connector_id)
        if "route" in values:
            route = str(values["route"]).lower()
            if route not in ("bezier", "auto", "orthogonal", "straight", "polyline"):
                raise ValueError(f"Unsupported connector route: {route}")
            connector.route = route
        if "lineStyle" in values:
            style = str(values["lineStyle"]).lower()
            if style not in ("solid", "dash", "dot", "dashdot"):
                raise ValueError(f"Unsupported connector line style: {style}")
            connector.line_style = style
        if "lineWidth" in values:
            connector.line_width = max(0.5, float(values["lineWidth"]))
        if "color" in values:
            connector.color = _color(values["color"], "#64748b")
        if "flowColor" in values:
            connector.flow_color = _color(values["flowColor"], "#38bdf8")
        if "arrowStart" in values:
            connector.arrow_start = bool(values["arrowStart"])
        if "arrowEnd" in values:
            connector.arrow_end = bool(values["arrowEnd"])
        if "animated" in values:
            connector.animated = bool(values["animated"])
        if "animationEffect" in values:
            effect = str(values["animationEffect"]).lower()
            if effect not in _LINE_EFFECTS:
                raise ValueError(f"Unsupported connector animation effect: {effect}")
            connector.animation_effect = effect
        if "flowSpeed" in values:
            connector.flow_speed = max(0.1, float(values["flowSpeed"]))
        if "flowDirection" in values:
            connector.flow_direction = -1 if str(values["flowDirection"]).lower() == "reverse" else 1
        if "flowSpacing" in values:
            connector.flow_spacing = max(1.0, float(values["flowSpacing"]))
        if "effectIntensity" in values:
            connector.effect_intensity = max(0.2, min(4.0, float(values["effectIntensity"])))
        if "packetLoop" in values:
            connector.packet_loop = bool(values["packetLoop"])
        if "packetDuration" in values:
            connector.packet_duration = max(0.1, float(values["packetDuration"]))
        if "packetInterval" in values:
            connector.packet_interval = max(0.05, float(values["packetInterval"]))
        if "packetIcon" in values:
            connector.packet_icon = str(values["packetIcon"])
        if "waypoints" in values:
            connector.waypoints = [QPointF(float(point[0]), float(point[1])) for point in values["waypoints"]]
        if "cornerRadius" in values:
            connector.corner_radius = max(0.0, min(80.0, float(values["cornerRadius"])))
        if "label" in values:
            connector.label = str(values["label"])
        if "labelPosition" in values:
            connector.label_position = max(0.0, min(1.0, float(values["labelPosition"])))
        if "parallelSpacing" in values:
            connector.parallel_spacing = max(0.0, min(120.0, float(values["parallelSpacing"])))
        if "obstacleClearance" in values:
            connector.obstacle_clearance = max(0.0, min(160.0, float(values["obstacleClearance"])))
        if "bridgeCrossings" in values:
            connector.bridge_crossings = bool(values["bridgeCrossings"])
        if "bridgeSize" in values:
            connector.bridge_size = max(3.0, min(30.0, float(values["bridgeSize"])))
        if "busStyle" in values:
            bus_style = str(values["busStyle"]).lower()
            if bus_style not in ("none", "trunk", "double"):
                raise ValueError(f"Unsupported connector bus style: {bus_style}")
            connector.bus_style = bus_style
        if "busWidth" in values:
            connector.bus_width = max(2.0, min(80.0, float(values["busWidth"])))
        if "busId" in values:
            connector.bus_id = str(values["busId"])
        if "opacity" in values:
            connector.setOpacity(max(0.0, min(1.0, float(values["opacity"]))))
        if "z" in values:
            connector.setZValue(float(values["z"]))
        if "metadata" in values:
            connector.metadata = dict(values["metadata"])
        if "locked" in values:
            connector.locked = bool(values["locked"])
        if "hidden" in values:
            connector.hidden = bool(values["hidden"])
        connector.updatePath()
        connector._sync_animation()
        connector.changed.emit(connector.connector_id)
        if object_state_changed:
            self._sync_object_states()
        return self

    def animateConnector(
        self,
        connector_id: str,
        enabled: bool = True,
        speed: float = 1.0,
        color: Any = "#38bdf8",
    ) -> "MonkezCanva":
        return self.updateConnector(
            connector_id,
            animated=enabled,
            flowSpeed=speed,
            flowColor=color,
        )

    def send_a_message(
        self,
        line_id: str,
        icon: Any = None,
        speed: float = 1.0,
        travel_time: float | None = None,
        wait_to_end: bool = False,
        message_id: str | None = None,
    ) -> str:
        """Send one addressable packet over a line or connector.

        ``speed`` is a multiplier applied to the configured/default travel time.
        Multiple calls intentionally create concurrent packets. When a packet
        reaches a splitter it is copied to every unvisited outgoing branch.
        """
        item = self.canvasObject(str(line_id))
        if item is None or (not isinstance(item, _CanvasConnector) and item.kind != "line"):
            raise TypeError(f"Object {line_id!r} is not a line or connector")
        speed = max(0.01, float(speed))
        duration = max(0.1, float(travel_time if travel_time is not None else item.packet_duration) / speed)
        message_id = str(message_id or uuid.uuid4().hex[:10])
        if message_id in self._message_payloads:
            raise ValueError(f"Message id is already in flight: {message_id}")
        self._message_payloads[message_id] = {
            "icon": item.packet_icon if icon is None else icon,
            "duration": duration,
            "pending": 1,
            "visited": {str(line_id)},
        }
        loop = QEventLoop(self) if wait_to_end else None
        if loop is not None:
            def stop_when_arrived(_object_id: str, arrived_id: str) -> None:
                if arrived_id == message_id:
                    loop.quit()
            self.messageArrived.connect(stop_when_arrived)
        item.sendPacket(message_id, icon, duration)
        self.messageSent.emit(str(line_id), message_id)
        if loop is not None:
            loop.exec()
            self.messageArrived.disconnect(stop_when_arrived)
        return message_id

    def sendMessage(self, line_id: str, **options) -> str:
        """Qt-style alias for :meth:`send_a_message`."""
        return self.send_a_message(line_id, **options)

    def _on_packet_arrived(self, object_id: str, message_id: str) -> None:
        payload = self._message_payloads.get(message_id)
        if payload is None:
            self.messageArrived.emit(object_id, message_id)
            return
        payload["pending"] -= 1
        connector = self._connectors.get(object_id)
        outgoing: list[_CanvasConnector] = []
        if connector is not None and connector.target.kind == "splitter":
            outgoing = [
                candidate for candidate in self._connectors.values()
                if candidate.source is connector.target
                and candidate.connector_id not in payload["visited"]
                and (not candidate.source_port or (candidate.source.port(candidate.source_port) or {}).get("mode") in ("output", "free"))
            ]
        if outgoing:
            payload["pending"] += len(outgoing)
            for branch in outgoing:
                payload["visited"].add(branch.connector_id)
                branch.sendPacket(message_id, payload["icon"], payload["duration"])
                self.messageSent.emit(branch.connector_id, message_id)
        if payload["pending"] <= 0:
            self._message_payloads.pop(message_id, None)
            self.messageArrived.emit(object_id, message_id)

    def renameConnector(self, connector_id: str, new_id: str) -> str:
        if not self._restoring:
            self._ensure_writable()
            requested = str(new_id).strip()
            candidate = CanvasDocument.from_dict(self._document_model.to_dict())
            event = candidate.rename_connector(connector_id, requested)
            if event is not None:
                self._undo_stack.push(
                    CanvasRenameCommand(
                        self._document_model,
                        str(connector_id),
                        requested,
                        connector=True,
                    )
                )
                return requested
            return str(connector_id)
        connector = self._required_connector(connector_id)
        requested = str(new_id).strip()
        if not requested:
            raise ValueError("MonkezCanva connector ID cannot be empty")
        if requested != connector_id and (requested in self._connectors or requested in self._elements):
            raise ValueError(f"Duplicate MonkezCanva object id: {requested}")
        if requested == connector_id:
            return requested
        self._connectors.pop(connector_id)
        connector.connector_id = requested
        connector.element_id = requested
        self._connectors[requested] = connector
        self.itemIdChanged.emit(connector_id, requested)
        self.documentChanged.emit()
        return requested

    def removeConnector(self, connector_id: str) -> bool:
        if not self._restoring:
            if self._document_model.connector(connector_id) is None:
                return False
            self._push_document_mutation(
                lambda document: document.remove_connector(connector_id),
                "Delete connector",
            )
            return True
        connector = self._connectors.pop(str(connector_id), None)
        if connector is None:
            return False
        connector.release()
        endpoints = {connector.source.element_id, connector.target.element_id}
        self._scene.removeItem(connector)
        connector.deleteLater()
        for sibling in self._connectors.values():
            if {sibling.source.element_id, sibling.target.element_id} == endpoints:
                sibling.updatePath()
        self.connectorRemoved.emit(str(connector_id))
        self.documentChanged.emit()
        return True

    def setElementColor(self, element_id: str, color: Any, role: str = "accent") -> "MonkezCanva":
        self._ensure_writable()
        item = self._required_element(element_id)
        value = _color(color)
        if role in ("background", "surface"):
            item.background = value
        elif role in ("text", "foreground"):
            item.text_color = value
        else:
            item.color = value
        item.update()
        self.documentChanged.emit()
        return self

    def setElementText(self, element_id: str, text: str) -> "MonkezCanva":
        self._ensure_writable()
        item = self._required_element(element_id)
        item.text = str(text)
        item.update()
        self.documentChanged.emit()
        return self

    def setChartData(self, element_id: str, values) -> "MonkezCanva":
        self._ensure_writable()
        item = self._required_element(element_id)
        if item.kind not in ("bar_chart", "line_chart"):
            raise TypeError(f"Element {element_id!r} is not a chart")
        item.data = list(values)
        item.update()
        self.documentChanged.emit()
        return self

    def highlightElement(self, element_id: str, color: Any = "#f59e0b", duration: int = 900) -> "MonkezCanva":
        item = self._required_element(element_id)
        item._highlight = _color(color, "#f59e0b")
        item.update()
        QTimer.singleShot(max(0, int(duration)), lambda target=item: self._clear_highlight(target))
        return self

    def highlightObject(self, object_id: str, color: Any = "#f59e0b", duration: int = 900) -> "MonkezCanva":
        item = self.canvasObject(object_id)
        if item is None:
            raise KeyError(f"Unknown MonkezCanva object: {object_id}")
        item._highlight = _color(color, "#f59e0b")
        item.update()
        QTimer.singleShot(max(0, int(duration)), lambda target=item: self._clear_highlight(target))
        return self

    def animateElement(self, element_id: str, effect: str = "pulse", duration: int = 500) -> QPropertyAnimation:
        item = self._required_element(element_id)
        effect = str(effect).lower()
        property_name = b"scale" if effect == "pulse" else b"opacity"
        previous = self._animations.pop(element_id, None)
        if previous is not None:
            previous.stop()
            previous.deleteLater()
        animation = ScheduledPropertyAnimation(self, item, property_name)
        animation.setDuration(max(80, int(duration)))
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        if effect == "pulse":
            animation.setKeyValueAt(0.0, 1.0)
            animation.setKeyValueAt(0.5, 1.08)
            animation.setKeyValueAt(1.0, 1.0)
        else:
            animation.setKeyValueAt(0.0, item.opacity())
            animation.setKeyValueAt(0.5, 0.25)
            animation.setKeyValueAt(1.0, 1.0)
        self._animations[element_id] = animation
        animation.finished.connect(
            lambda key=element_id, value=animation: self._finish_runtime_animation(
                key, value
            )
        )
        animation.start()
        return animation

    def _finish_runtime_animation(
        self, element_id: str, animation: QPropertyAnimation
    ) -> None:
        if self._animations.get(element_id) is animation:
            self._animations.pop(element_id, None)
        animation.deleteLater()

    def deleteSelected(self) -> None:
        selected = list(self._scene.selectedItems())
        use_macro = not self._restoring and len(selected) > 1
        if use_macro:
            self.beginCommandMacro(f"Delete {len(selected)} objects")
        try:
            for item in selected:
                if isinstance(item, _CanvasElement):
                    self.removeElement(item.element_id)
                elif isinstance(item, _CanvasConnector):
                    self.removeConnector(item.connector_id)
                elif isinstance(item, _CanvasGroup):
                    self.removeGroup(item.group_id)
        finally:
            if use_macro:
                self.endCommandMacro()

    def removeElement(self, element_id: str) -> bool:
        if not self._restoring:
            if self._document_model.element(element_id) is None:
                return False
            self._push_document_mutation(
                lambda document: document.remove_element(element_id),
                "Delete element",
            )
            return True
        item = self._elements.pop(str(element_id), None)
        if item is None:
            return False
        for key in tuple(self._port_runtime_values):
            if key[0] == str(element_id):
                self._port_runtime_values.pop(key, None)
        animation = self._animations.pop(str(element_id), None)
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        attached = [key for key, connector in self._connectors.items() if item in (connector.source, connector.target)]
        for key in attached:
            connector = self._connectors.pop(key)
            connector.release()
            self._scene.removeItem(connector)
            connector.deleteLater()
            self.connectorRemoved.emit(key)
        item.release()
        self._scene.removeItem(item)
        item.deleteLater()
        self.elementRemoved.emit(str(element_id))
        self.documentChanged.emit()
        return True

    def clear(self) -> None:
        element_ids = list(self._elements)
        group_ids = list(self._groups)
        use_macro = not self._restoring and len(element_ids) + len(group_ids) > 1
        if use_macro:
            self.beginCommandMacro("Clear canvas")
        try:
            for element_id in element_ids:
                self.removeElement(element_id)
            for group_id in group_ids:
                if self._restoring:
                    self._remove_group_graphics(group_id)
                else:
                    self.removeGroup(group_id)
        finally:
            if use_macro:
                self.endCommandMacro()
        self._message_payloads.clear()
        self._port_runtime_values.clear()

    def documentModel(self) -> CanvasDocument:
        """Return the canonical Qt-free document shared by this canvas view."""
        return self._document_model

    def canvasDocument(self) -> CanvasDocument:
        """Readable alias for :meth:`documentModel`."""
        return self.documentModel()

    def addGroup(
        self,
        members,
        group_id: str | None = None,
        **properties,
    ) -> str:
        group_id = str(group_id or uuid.uuid4().hex[:10])
        member_ids = tuple(dict.fromkeys(str(member) for member in members))
        rectangles = [
            item.sceneBoundingRect()
            for member in member_ids
            for item in (self.canvasObject(member),)
            if item is not None
        ]
        padding = max(0.0, min(120.0, float(properties.pop("padding", 28.0))))
        default_x, default_y, default_width, default_height = group_bounds(
            (
                (rect.x(), rect.y(), rect.width(), rect.height())
                for rect in rectangles
            ),
            padding=padding,
        )
        kind = normalize_group_kind(properties.pop("kind", "frame"))
        record = {
            "id": group_id,
            "members": list(member_ids),
            "kind": kind,
            "label": str(properties.pop("label", properties.pop("text", "Group"))),
            "x": float(properties.pop("x", default_x)),
            "y": float(properties.pop("y", default_y)),
            "width": max(120.0, float(properties.pop("width", default_width))),
            "height": max(54.0, float(properties.pop("height", default_height))),
            "padding": padding,
            "collapsed": bool(properties.pop("collapsed", False)),
            "color": _color(properties.pop("color", "#64748b"), "#64748b").name(
                QColor.NameFormat.HexArgb
            ),
            "background": _color(
                properties.pop("background", "#f8fafc"), "#f8fafc"
            ).name(QColor.NameFormat.HexArgb),
            "headerColor": _color(
                properties.pop("headerColor", "#64748b"), "#64748b"
            ).name(QColor.NameFormat.HexArgb),
            "lanes": [str(value) for value in properties.pop("lanes", ())],
            "orientation": (
                "vertical"
                if str(properties.pop("orientation", "horizontal")).lower() == "vertical"
                else "horizontal"
            ),
            "opacity": max(0.0, min(1.0, float(properties.pop("opacity", 1.0)))),
            "z": float(properties.pop("z", -20.0)),
            "locked": bool(properties.pop("locked", False)),
            "hidden": bool(properties.pop("hidden", False)),
            **self._model_values(properties),
        }
        self._push_document_mutation(
            lambda document: document.add_group(record), "Group objects"
        )
        if self._edit_mode and group_id in self._groups:
            self.selectElements((group_id,))
        return group_id

    def groupSelected(self, group_id: str | None = None, **properties) -> str:
        members = [
            object_id
            for object_id in self.selectedObjectIds()
            if object_id in self._elements or object_id in self._groups
        ]
        if not members:
            return ""
        return self.addGroup(members, group_id, **properties)

    def addFrame(self, members, group_id: str | None = None, **properties) -> str:
        properties["kind"] = "frame"
        return self.addGroup(members, group_id, **properties)

    def addSwimlane(
        self,
        members,
        group_id: str | None = None,
        *,
        lanes=("Lane 1", "Lane 2"),
        orientation: str = "horizontal",
        **properties,
    ) -> str:
        properties.update(kind="swimlane", lanes=list(lanes), orientation=orientation)
        return self.addGroup(members, group_id, **properties)

    def addSubflow(self, members, group_id: str | None = None, **properties) -> str:
        properties["kind"] = "subflow"
        return self.addGroup(members, group_id, **properties)

    def updateGroup(self, group_id: str, **changes) -> "MonkezCanva":
        values = self._model_values(changes)
        if "kind" in values:
            values["kind"] = normalize_group_kind(values["kind"])
        if "members" in values:
            values["members"] = list(
                dict.fromkeys(str(member) for member in values["members"])
            )
        if "width" in values:
            values["width"] = max(120.0, float(values["width"]))
        if "height" in values:
            values["height"] = max(54.0, float(values["height"]))
        if "opacity" in values:
            values["opacity"] = max(0.0, min(1.0, float(values["opacity"])))
        self._push_document_mutation(
            lambda document: document.update_group(group_id, values),
            "Update group",
            merge_key=f"group:{group_id}",
        )
        return self

    def renameGroup(self, group_id: str, new_id: str) -> str:
        self._ensure_writable()
        requested = str(new_id).strip()
        candidate = CanvasDocument.from_dict(self._document_model.to_dict())
        events = candidate.rename_group(str(group_id), requested)
        if events:
            self._undo_stack.push(
                CanvasRenameCommand(
                    self._document_model,
                    str(group_id),
                    requested,
                    group=True,
                )
            )
            return requested
        return str(group_id)

    def removeGroup(self, group_id: str) -> bool:
        if self._document_model.group(group_id) is None:
            return False
        self._push_document_mutation(
            lambda document: document.remove_group(group_id), "Ungroup objects"
        )
        return True

    def setGroupCollapsed(self, group_id: str, collapsed: bool = True) -> "MonkezCanva":
        return self.updateGroup(group_id, collapsed=bool(collapsed))

    def moveGroup(self, group_id: str, x: float, y: float) -> bool:
        item = self._groups.get(str(group_id))
        if item is None:
            raise KeyError(f"Unknown MonkezCanva group: {group_id}")
        return self._commit_group_move(
            str(group_id), QPointF(float(x) - item.pos().x(), float(y) - item.pos().y())
        )

    def fitGroupToContents(self, group_id: str) -> bool:
        model = self._document_model.group(str(group_id))
        if model is None:
            return False
        item = self._groups.get(str(group_id))
        padding = item.padding if item is not None else float(model.properties.get("padding", 28.0))
        rectangles = [
            target.sceneBoundingRect()
            for member in model.members
            for target in (self.canvasObject(member),)
            if target is not None
        ]
        x, y, width, height = group_bounds(
            ((rect.x(), rect.y(), rect.width(), rect.height()) for rect in rectangles),
            padding=padding,
        )
        return self._push_document_mutation(
            lambda document: document.update_group(
                str(group_id), {"x": x, "y": y, "width": width, "height": height}
            ),
            "Fit group to contents",
        )

    def _nested_group_ids(self, group_id: str) -> tuple[str, ...]:
        records = {model.id: model.to_dict() for model in self._document_model.groups}
        result: list[str] = []
        pending = list(records.get(str(group_id), {}).get("members", ()))
        while pending:
            member = str(pending.pop(0))
            if member in records and member not in result:
                result.append(member)
                pending.extend(records[member].get("members", ()))
        return tuple(result)

    def _preview_group_move(self, group_id: str, delta: QPointF) -> None:
        if math.isclose(delta.x(), 0.0) and math.isclose(delta.y(), 0.0):
            return
        records = {model.id: model.to_dict() for model in self._document_model.groups}
        elements = descendant_element_ids(str(group_id), records, self._elements)
        previous = self._restoring
        self._restoring = True
        try:
            for element_id in elements:
                item = self._elements.get(element_id)
                if item is not None:
                    item.setPos(item.pos() + delta)
            for nested_id in self._nested_group_ids(group_id):
                item = self._groups.get(nested_id)
                if item is not None:
                    item.setPos(item.pos() + delta)
            for connector in self._connectors.values():
                connector.updatePath()
        finally:
            self._restoring = previous

    def _commit_group_move(self, group_id: str, delta: QPointF) -> bool:
        records = {model.id: model.to_dict() for model in self._document_model.groups}
        elements = descendant_element_ids(str(group_id), records, self._elements)
        nested_groups = self._nested_group_ids(group_id)

        def mutate(document: CanvasDocument) -> None:
            for element_id in elements:
                model = document.element(element_id)
                if model is not None:
                    document.update_element(
                        element_id,
                        {
                            "x": float(model.properties.get("x", 0.0)) + delta.x(),
                            "y": float(model.properties.get("y", 0.0)) + delta.y(),
                        },
                    )
            for nested_id in nested_groups:
                model = document.group(nested_id)
                if model is not None:
                    document.update_group(
                        nested_id,
                        {
                            "x": float(model.properties.get("x", 0.0)) + delta.x(),
                            "y": float(model.properties.get("y", 0.0)) + delta.y(),
                        },
                    )
            model = document.group(str(group_id))
            if model is not None:
                document.update_group(
                    str(group_id),
                    {
                        "x": float(model.properties.get("x", 0.0)) + delta.x(),
                        "y": float(model.properties.get("y", 0.0)) + delta.y(),
                    },
                )

        return self._push_document_mutation(mutate, "Move group")

    def exportSubflow(self, group_id: str) -> dict[str, Any]:
        """Return a portable JSON-only template for one group and its descendants."""

        key = str(group_id)
        root = self._document_model.group(key)
        if root is None:
            raise KeyError(f"Unknown MonkezCanva group: {key}")
        group_records = {
            model.id: model.to_dict() for model in self._document_model.groups
        }
        element_ids = descendant_element_ids(key, group_records, self._elements)
        nested_ids = self._nested_group_ids(key)
        included_groups = (key, *nested_ids)
        origin_x = float(root.properties.get("x", 0.0))
        origin_y = float(root.properties.get("y", 0.0))
        elements: list[dict[str, Any]] = []
        for element_id in element_ids:
            model = self._document_model.element(element_id)
            if model is None:
                continue
            record = model.to_dict()
            record["x"] = float(record.get("x", 0.0)) - origin_x
            record["y"] = float(record.get("y", 0.0)) - origin_y
            elements.append(record)
        element_set = set(element_ids)
        connectors: list[dict[str, Any]] = []
        for model in self._document_model.connectors:
            if model.source not in element_set or model.target not in element_set:
                continue
            record = model.to_dict()
            record["waypoints"] = [
                [float(point[0]) - origin_x, float(point[1]) - origin_y]
                for point in record.get("waypoints", ())
            ]
            connectors.append(record)
        groups: list[dict[str, Any]] = []
        for current_id in included_groups:
            record = dict(group_records[current_id])
            record["x"] = float(record.get("x", 0.0)) - origin_x
            record["y"] = float(record.get("y", 0.0)) - origin_y
            groups.append(record)
        return {
            "format": "monkez-subflow",
            "version": 1,
            "root": key,
            "elements": elements,
            "connectors": connectors,
            "groups": groups,
        }

    def importSubflow(
        self,
        payload: dict[str, Any],
        x: float | None = None,
        y: float | None = None,
    ) -> str:
        """Instantiate a reusable subflow template with collision-safe IDs."""

        self._ensure_writable()
        data = json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False))
        if data.get("format") != "monkez-subflow" or int(data.get("version", 0)) != 1:
            raise ValueError("Unsupported MonkezCanva subflow template")
        records = [*data.get("elements", ()), *data.get("connectors", ()), *data.get("groups", ())]
        source_ids = [str(record.get("id", "")).strip() for record in records]
        if any(not value for value in source_ids) or len(source_ids) != len(set(source_ids)):
            raise ValueError("Subflow template IDs must be non-empty and unique")
        occupied = set(self._elements) | set(self._connectors) | set(self._groups)
        mapping: dict[str, str] = {}
        for source_id in source_ids:
            candidate = source_id
            while candidate in occupied or candidate in mapping.values():
                candidate = f"{source_id}-{uuid.uuid4().hex[:6]}"
            mapping[source_id] = candidate
        center = self._view.mapToScene(self._view.viewport().rect().center())
        offset_x = center.x() if x is None else float(x)
        offset_y = center.y() if y is None else float(y)
        prepared_elements: list[dict[str, Any]] = []
        for raw in data.get("elements", ()):
            record = dict(raw)
            record["id"] = mapping[str(record["id"])]
            record["x"] = float(record.get("x", 0.0)) + offset_x
            record["y"] = float(record.get("y", 0.0)) + offset_y
            prepared_elements.append(self._element_registry.prepare_record(record))
        prepared_connectors: list[dict[str, Any]] = []
        for raw in data.get("connectors", ()):
            record = dict(raw)
            record["id"] = mapping[str(record["id"])]
            record["source"] = mapping[str(record["source"])]
            record["target"] = mapping[str(record["target"])]
            record["waypoints"] = [
                [float(point[0]) + offset_x, float(point[1]) + offset_y]
                for point in record.get("waypoints", ())
            ]
            prepared_connectors.append(record)
        prepared_groups: list[dict[str, Any]] = []
        for raw in data.get("groups", ()):
            record = dict(raw)
            record["id"] = mapping[str(record["id"])]
            record["members"] = [mapping[str(member)] for member in record.get("members", ())]
            record["x"] = float(record.get("x", 0.0)) + offset_x
            record["y"] = float(record.get("y", 0.0)) + offset_y
            prepared_groups.append(record)

        def mutate(document: CanvasDocument) -> None:
            for record in prepared_elements:
                document.add_element(record)
            for record in prepared_connectors:
                document.add_connector(record)
            pending = list(prepared_groups)
            while pending:
                progress = False
                for record in tuple(pending):
                    if all(
                        document.element(str(member)) is not None
                        or document.group(str(member)) is not None
                        for member in record.get("members", ())
                    ):
                        document.add_group(record)
                        pending.remove(record)
                        progress = True
                if not progress:
                    raise ValueError("Subflow template contains invalid nested groups")

        self._push_document_mutation(mutate, "Import subflow")
        root_id = mapping.get(str(data.get("root", "")), "")
        if root_id and self._edit_mode:
            self.selectElements((root_id,))
        return root_id

    def saveSubflowTemplate(self, group_id: str, path: str | Path) -> Path:
        target = Path(path)
        atomic_write_json(target, self.exportSubflow(group_id))
        return target

    def loadSubflowTemplate(
        self, path: str | Path, x: float | None = None, y: float | None = None
    ) -> str:
        source = Path(path)
        return self.importSubflow(json.loads(source.read_text(encoding="utf-8")), x, y)

    def exportSubflowToDialog(self, group_id: str) -> str:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self.window(),
            "Export reusable subflow",
            f"{group_id}.monkez-subflow.json",
            "Monkez subflow (*.monkez-subflow.json *.json)",
        )
        if not path:
            return ""
        return str(self.saveSubflowTemplate(group_id, path))

    def importSubflowFromDialog(self) -> str:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self.window(),
            "Import reusable subflow",
            "",
            "Monkez subflow (*.monkez-subflow.json *.json)",
        )
        return self.loadSubflowTemplate(path) if path else ""

    def addResource(
        self, kind: str, uri: str, resource_id: str | None = None, **properties
    ) -> str:
        resource_id = str(resource_id or uuid.uuid4().hex[:10])
        record = {
            "id": resource_id,
            "kind": str(kind),
            "uri": str(uri),
            **self._model_values(properties),
        }
        self._push_document_mutation(
            lambda document: document.add_resource(record), "Add resource"
        )
        return resource_id

    def updateResource(self, resource_id: str, **changes) -> "MonkezCanva":
        values = self._model_values(changes)
        self._push_document_mutation(
            lambda document: document.update_resource(resource_id, values),
            "Update resource",
            merge_key=f"resource:{resource_id}",
        )
        return self

    def removeResource(self, resource_id: str) -> bool:
        if self._document_model.resource(resource_id) is None:
            return False
        self._push_document_mutation(
            lambda document: document.remove_resource(resource_id), "Remove resource"
        )
        return True

    def undoStack(self) -> QUndoStack:
        return self._undo_stack

    def canUndo(self) -> bool:
        return self._undo_stack.canUndo()

    def canRedo(self) -> bool:
        return self._undo_stack.canRedo()

    def undoText(self) -> str:
        return self._undo_stack.undoText()

    def redoText(self) -> str:
        return self._undo_stack.redoText()

    def isDocumentModified(self) -> bool:
        return not self._undo_stack.isClean()

    def isReadOnly(self) -> bool:
        return bool(self._read_only_reason)

    def readOnlyReason(self) -> str:
        return self._read_only_reason

    def lastRecoverySource(self) -> str:
        return self._last_recovery_source

    def assetIntegrityIssues(self) -> tuple[str, ...]:
        return tuple(self._asset_integrity_issues)

    def _set_read_only_reason(self, reason: str) -> None:
        normalized = str(reason).strip()
        if normalized == self._read_only_reason:
            return
        self._read_only_reason = normalized
        self._sync_object_states()
        self.readOnlyChanged.emit(bool(normalized), normalized)
        if normalized:
            self.diagnosticMessage.emit(f"Read-only document: {normalized}")

    def _ensure_writable(self) -> None:
        if self.isReadOnly():
            raise PermissionError(self._read_only_reason)

    def beginCommandMacro(self, text: str) -> None:
        self._ensure_writable()
        self._undo_stack.beginMacro(str(text))

    def endCommandMacro(self) -> None:
        self._undo_stack.endMacro()

    def _emit_history_state(self, _index: int = 0) -> None:
        self.historyChanged.emit(
            self.canUndo(), self.canRedo(), self.undoText(), self.redoText()
        )

    def _on_history_clean_changed(self, clean: bool) -> None:
        self.documentModifiedChanged.emit(not clean)

    def _push_document_mutation(
        self,
        mutation: Callable[[CanvasDocument], Any],
        text: str,
        *,
        merge_key: str = "",
    ) -> bool:
        self._ensure_writable()
        before = self._document_model.to_dict()
        candidate = CanvasDocument.from_dict(before)
        mutation(candidate)
        after = candidate.to_dict()
        patches = patches_from_documents(before, after)
        if not patches:
            return False
        self._undo_stack.push(
            CanvasDocumentCommand(
                self._document_model,
                patches,
                text,
                merge_key=merge_key,
            )
        )
        return True

    def setDocumentModel(self, document: CanvasDocument) -> "MonkezCanva":
        """Attach a canonical document; the same instance may back many views."""
        if not isinstance(document, CanvasDocument):
            raise TypeError("MonkezCanva.setDocumentModel expects a CanvasDocument")
        if document is self._document_model:
            return self
        source = document.to_dict()
        reasons = self._compatibility_reasons(document)
        if not reasons:
            prepared = self._prepare_document_for_registry(source)
            document.reconcile(prepared, origin=self)
        if self._document_model is not None and self._document_subscription:
            self._document_model.unsubscribe(self._document_subscription)
        self._port_runtime_values.clear()
        self._document_model = document
        self._document_subscription = document.subscribe(self._on_document_operation)
        self._last_rendered_document_revision = document.revision
        self._undo_stack.clear()
        self._set_read_only_reason("; ".join(reason for reason in reasons if reason))
        self._render_document(document.to_dict())
        return self

    def _newer_component_reasons(self, data: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        for entry in data.get("elements", []):
            definition = self._element_registry.definition(str(entry.get("type", "")))
            if definition is None:
                continue
            version = int(entry.get("componentVersion", 1))
            if version > definition.schema_version:
                reasons.append(
                    f"Component {entry.get('id', '?')!r} ({definition.type_id}) uses "
                    f"schema {version}; supported {definition.schema_version}"
                )
        return reasons

    def _compatibility_reasons(self, document: CanvasDocument) -> list[str]:
        reasons = [document.read_only_reason] if document.is_read_only else []
        reasons.extend(self._newer_component_reasons(document.to_dict()))
        return [reason for reason in reasons if reason]

    def _prepare_document_for_registry(self, data: dict[str, Any]) -> dict[str, Any]:
        prepared = json.loads(json.dumps(data))
        prepared["elements"] = [
            self._element_registry.prepare_record(entry)
            if self._element_registry.definition(str(entry.get("type", ""))) is not None
            else entry
            for entry in prepared.get("elements", [])
        ]
        return prepared

    def _reconcile_registry_records(self, type_id: str) -> None:
        if self._document_model is None:
            return
        data = self._document_model.to_dict()
        changed = False
        for index, entry in enumerate(data.get("elements", [])):
            if str(entry.get("type", "")).lower() != str(type_id).lower():
                continue
            migrated = self._element_registry.prepare_record(entry, allow_newer=True)
            if migrated != entry:
                data["elements"][index] = migrated
                changed = True
        if changed:
            self._document_model.reconcile(data)
        else:
            for item in self._elements.values():
                if item.kind == str(type_id).lower():
                    item.definition = self._element_registry.require(type_id)
                    item.update()
        self._set_read_only_reason(
            "; ".join(self._compatibility_reasons(self._document_model))
        )

    @staticmethod
    def _model_values(values: dict[str, Any]) -> dict[str, Any]:
        """Convert common Qt/path values before they enter the JSON document core."""

        def convert(value: Any) -> Any:
            if isinstance(value, QColor):
                return value.name(QColor.NameFormat.HexArgb)
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, dict):
                return {str(key): convert(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [convert(item) for item in value]
            return value

        result = {str(key): convert(value) for key, value in values.items()}
        for key, fallback in (
            ("color", "#2563eb"),
            ("background", "#ffffff"),
            ("textColor", "#0f172a"),
            ("flowColor", "#38bdf8"),
        ):
            if key in result:
                result[key] = _color(result[key], fallback).name(QColor.NameFormat.HexArgb)
        return result

    def _element_model_record(
        self,
        element_id: str,
        kind: str,
        x: float,
        y: float,
        width: float,
        height: float,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        values = self._model_values(options)
        definition = self._element_registry.definition(kind)
        supports_ports = kind in _PORT_KINDS or bool(
            definition is not None and "ports" in definition.capabilities
        )
        direction = str(values.get("flowDirection", "forward")).lower()
        record = {
            "id": element_id,
            "type": kind,
            "x": float(x),
            "y": float(y),
            "width": max(24.0, float(width)),
            "height": max(24.0, float(height)),
            "text": str(values.get("text", kind.replace("_", " ").title())),
            "color": _color(values.get("color", "#2563eb")).name(QColor.NameFormat.HexArgb),
            "background": _color(values.get("background", "#ffffff"), "#ffffff").name(QColor.NameFormat.HexArgb),
            "textColor": _color(values.get("textColor", "#0f172a"), "#0f172a").name(QColor.NameFormat.HexArgb),
            "data": list(values.get("data", [32, 68, 46, 82, 58])),
            "metadata": dict(values.get("metadata", {})),
            "source": str(values.get("source", "")),
            "lineWidth": max(0.5, float(values.get("lineWidth", 2.2))),
            "lineStyle": str(values.get("lineStyle", "solid")).lower(),
            "arrowStart": bool(values.get("arrowStart", False)),
            "arrowEnd": bool(values.get("arrowEnd", False)),
            "animated": bool(values.get("animated", False)),
            "animationEffect": str(values.get("animationEffect", "flow")).lower(),
            "flowColor": _color(values.get("flowColor", "#38bdf8"), "#38bdf8").name(QColor.NameFormat.HexArgb),
            "flowSpeed": max(0.1, float(values.get("flowSpeed", 1.0))),
            "flowDirection": "reverse" if direction == "reverse" else "forward",
            "flowSpacing": max(1.0, float(values.get("flowSpacing", 5.0))),
            "effectIntensity": max(0.2, min(4.0, float(values.get("effectIntensity", 1.0)))),
            "packetLoop": bool(values.get("packetLoop", False)),
            "packetDuration": max(0.1, float(values.get("packetDuration", 1.5))),
            "packetInterval": max(0.05, float(values.get("packetInterval", 0.7))),
            "packetIcon": str(values.get("packetIcon", "")),
            "points": [[float(point[0]), float(point[1])] for point in values.get("points", [])],
            "ports": _normalize_node_ports(values.get("ports")) if supports_ports else [],
            "opacity": max(0.0, min(1.0, float(values.get("opacity", 1.0)))),
            "rotation": float(values.get("rotation", 0.0)),
            "z": float(values.get("z", 0.0)),
            "locked": bool(values.get("locked", False)),
            "hidden": bool(values.get("hidden", False)),
        }
        record.update(
            {
                key: value for key, value in values.items()
                if key not in _ELEMENT_STANDARD_PROPERTIES
            }
        )
        return record

    @classmethod
    def _connector_model_record(
        cls,
        connector_id: str,
        source_id: str,
        target_id: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        values = cls._model_values(options)
        direction = str(values.get("flowDirection", "forward")).lower()
        route = str(values.get("route", "bezier")).lower()
        if route not in ("bezier", "auto", "orthogonal", "straight", "polyline"):
            raise ValueError(f"Unsupported connector route: {route}")
        bus_style = str(values.get("busStyle", "none")).lower()
        if bus_style not in ("none", "trunk", "double"):
            raise ValueError(f"Unsupported connector bus style: {bus_style}")
        return {
            "id": connector_id,
            "type": "connector",
            "source": source_id,
            "target": target_id,
            "sourcePort": str(values.get("sourcePort", "")),
            "targetPort": str(values.get("targetPort", "")),
            "color": _color(values.get("color", "#64748b"), "#64748b").name(QColor.NameFormat.HexArgb),
            "flowColor": _color(values.get("flowColor", "#38bdf8"), "#38bdf8").name(QColor.NameFormat.HexArgb),
            "route": route,
            "lineStyle": str(values.get("lineStyle", "solid")).lower(),
            "lineWidth": max(0.5, float(values.get("lineWidth", 2.2))),
            "arrowStart": bool(values.get("arrowStart", False)),
            "arrowEnd": bool(values.get("arrowEnd", True)),
            "animated": bool(values.get("animated", False)),
            "animationEffect": str(values.get("animationEffect", "flow")).lower(),
            "flowSpeed": max(0.1, float(values.get("flowSpeed", 1.0))),
            "flowDirection": "reverse" if direction == "reverse" else "forward",
            "flowSpacing": max(1.0, float(values.get("flowSpacing", 5.0))),
            "effectIntensity": max(0.2, min(4.0, float(values.get("effectIntensity", 1.0)))),
            "packetLoop": bool(values.get("packetLoop", False)),
            "packetDuration": max(0.1, float(values.get("packetDuration", 1.5))),
            "packetInterval": max(0.05, float(values.get("packetInterval", 0.7))),
            "packetIcon": str(values.get("packetIcon", "")),
            "waypoints": [[float(point[0]), float(point[1])] for point in values.get("waypoints", [])],
            "cornerRadius": max(0.0, min(80.0, float(values.get("cornerRadius", 14.0)))),
            "label": str(values.get("label", "")),
            "labelPosition": max(0.0, min(1.0, float(values.get("labelPosition", 0.5)))),
            "parallelSpacing": max(0.0, min(120.0, float(values.get("parallelSpacing", 22.0)))),
            "obstacleClearance": max(0.0, min(160.0, float(values.get("obstacleClearance", 20.0)))),
            "bridgeCrossings": bool(values.get("bridgeCrossings", True)),
            "bridgeSize": max(3.0, min(30.0, float(values.get("bridgeSize", 7.0)))),
            "busStyle": bus_style,
            "busWidth": max(2.0, min(80.0, float(values.get("busWidth", 10.0)))),
            "busId": str(values.get("busId", "")),
            "metadata": dict(values.get("metadata", {})),
            "opacity": max(0.0, min(1.0, float(values.get("opacity", 1.0)))),
            "z": float(values.get("z", -1.0)),
            "locked": bool(values.get("locked", False)),
            "hidden": bool(values.get("hidden", False)),
        }

    def _graphics_document(self) -> dict[str, Any]:
        return {
            "format": "monkez-canva",
            "version": 1,
            "scene": {
                "width": self._scene.sceneRect().width(),
                "height": self._scene.sceneRect().height(),
                "gridVisible": self._grid_visible,
                "snapToGrid": self._snap_to_grid,
                SNAP_TARGETS_KEY: list(self._snap_targets),
                SNAP_DISTANCE_KEY: self._snap_distance,
                SMART_GUIDES_KEY: self._smart_guides_visible,
                "gridSize": self._grid_size,
                "gridStyle": self._grid_style,
                "gridColor": self._grid_color.name(QColor.NameFormat.HexArgb),
                "backgroundColor": self._background_color.name(QColor.NameFormat.HexArgb),
                "backgroundImage": self._background_image,
                "backgroundImageMode": self._background_image_mode,
                PALETTE_FAVORITES_KEY: list(self._palette_favorites),
                PALETTE_RECENT_KEY: list(self._palette_recent),
                _VIEWPORT_BOOKMARKS_KEY: self.viewportBookmarks(),
                _MINIMAP_VISIBLE_KEY: self._minimap_visible,
            },
            "elements": [item.to_dict() for item in self._elements.values()],
            "connectors": [item.to_dict() for item in self._connectors.values()],
            "groups": [item.to_dict() for item in self._groups.values()],
            "resources": (
                [model.to_dict() for model in self._document_model.resources]
                if self._document_model is not None else []
            ),
        }

    def _sync_document_from_graphics(self) -> tuple[OperationEvent, ...]:
        if self._restoring or self._document_model is None or self.isReadOnly():
            return ()
        before = self._document_model.to_dict()
        after = self._graphics_document()
        events = self._document_model.reconcile(after, origin=self)
        if events:
            self._last_rendered_document_revision = self._document_model.revision
            patches = patches_from_documents(before, self._document_model.to_dict())
            merge_key = ""
            text = "Edit canvas"
            if len(patches) == 1:
                patch = patches[0]
                if patch.collection == "elements":
                    merge_key = f"element:{patch.record_id}"
                    text = "Edit element"
                elif patch.collection == "connectors":
                    merge_key = f"connector:{patch.record_id}"
                    text = "Edit connector"
                elif patch.collection == "scene":
                    merge_key = "scene"
                    text = "Edit canvas view"
            self._undo_stack.push(
                CanvasDocumentCommand(
                    self._document_model,
                    patches,
                    text,
                    merge_key=merge_key,
                    already_applied=True,
                )
            )
        return events

    def _on_document_operation(self, event: OperationEvent) -> None:
        self.documentOperation.emit(event.to_dict())
        if event.origin is self:
            self._last_rendered_document_revision = max(
                self._last_rendered_document_revision, event.revision
            )
            return
        previous_restoring = self._restoring
        self._restoring = True
        try:
            self._apply_document_operation(event)
            self._sync_graphics_record_order()
            self._last_rendered_document_revision = max(
                self._last_rendered_document_revision, event.revision
            )
        finally:
            self._restoring = previous_restoring
        if not previous_restoring:
            self._document_render_notification = True
            try:
                self.documentChanged.emit()
            finally:
                self._document_render_notification = False

    def _sync_graphics_record_order(self) -> None:
        element_order = [model.id for model in self._document_model.elements]
        connector_order = [model.id for model in self._document_model.connectors]
        group_order = [model.id for model in self._document_model.groups]
        self._elements = {
            element_id: self._elements[element_id]
            for element_id in element_order
            if element_id in self._elements
        }
        self._connectors = {
            connector_id: self._connectors[connector_id]
            for connector_id in connector_order
            if connector_id in self._connectors
        }
        self._groups = {
            group_id: self._groups[group_id]
            for group_id in group_order
            if group_id in self._groups
        }

    def _apply_document_operation(self, event: OperationEvent) -> None:
        """Apply one model operation without rebuilding unrelated graphics items."""

        action = event.action
        current = dict(event.current or {})
        previous = dict(event.previous or {})
        if action == "scene.updated":
            self._apply_scene_record(current)
        elif action == "element.added":
            self._add_element_record(current)
        elif action == "element.updated":
            existing = self._elements.get(event.target_id)
            if existing is not None and existing.kind == current.get("type", existing.kind):
                self._apply_element_record(event.target_id, current)
            else:
                was_selected = bool(existing and existing.isSelected())
                if existing is not None:
                    self.removeElement(event.target_id)
                self._add_element_record(current)
                if was_selected and self._edit_mode:
                    self._elements[event.target_id].setSelected(True)
        elif action == "element.renamed":
            old_id = str(previous.get("id", ""))
            if old_id in self._elements:
                self.renameElement(old_id, str(current.get("id", event.target_id)))
        elif action == "element.removed":
            self.removeElement(event.target_id)
        elif action == "connector.added":
            self._add_connector_record(current)
        elif action == "connector.updated":
            existing = self._connectors.get(event.target_id)
            if existing is None:
                self._add_connector_record(current)
            else:
                self._apply_connector_record(event.target_id, current)
        elif action == "connector.renamed":
            old_id = str(previous.get("id", ""))
            if old_id in self._connectors:
                self.renameConnector(old_id, str(current.get("id", event.target_id)))
        elif action == "connector.removed":
            self.removeConnector(event.target_id)
        elif action == "group.added":
            self._add_group_record(current)
        elif action == "group.updated":
            if event.target_id in self._groups:
                self._apply_group_record(event.target_id, current)
            else:
                self._add_group_record(current)
        elif action == "group.renamed":
            old_id = str(previous.get("id", ""))
            item = self._groups.pop(old_id, None)
            if item is not None:
                item.group_id = str(current.get("id", event.target_id))
                item.element_id = item.group_id
                self._groups[item.group_id] = item
                self.itemIdChanged.emit(old_id, item.group_id)
        elif action == "group.removed":
            self._remove_group_graphics(event.target_id)

    def _apply_scene_record(self, scene: dict[str, Any]) -> None:
        width = max(100.0, float(scene.get("width", self._scene.sceneRect().width())))
        height = max(100.0, float(scene.get("height", self._scene.sceneRect().height())))
        self._scene.setSceneRect(-width / 2, -height / 2, width, height)
        self._grid_visible = bool(scene.get("gridVisible", self._grid_visible))
        self._snap_to_grid = bool(scene.get("snapToGrid", self._snap_to_grid))
        self._snap_targets = normalize_snap_targets(
            scene.get(SNAP_TARGETS_KEY, self._snap_targets)
        )
        self._snap_distance = max(
            1.0, min(40.0, float(scene.get(SNAP_DISTANCE_KEY, self._snap_distance)))
        )
        self._smart_guides_visible = bool(
            scene.get(SMART_GUIDES_KEY, self._smart_guides_visible)
        )
        self._grid_size = max(4, int(scene.get("gridSize", self._grid_size)))
        self._grid_style = max(
            0, min(len(_GRID_STYLES) - 1, int(scene.get("gridStyle", self._grid_style)))
        )
        self._grid_color = _color(scene.get("gridColor", self._grid_color), "#e2e8f0")
        self._background_color = _color(
            scene.get("backgroundColor", self._background_color), "#f8fafc"
        )
        self._background_image = str(scene.get("backgroundImage", self._background_image))
        self._background_image_mode = max(
            0,
            min(
                len(_BACKGROUND_IMAGE_MODES) - 1,
                int(scene.get("backgroundImageMode", self._background_image_mode)),
            ),
        )
        self._background_pixmap = (
            QPixmap(self._background_image) if self._background_image else QPixmap()
        )
        self._apply_palette_preferences(scene)
        self._apply_navigation_preferences(scene)
        self._scene.invalidate(
            self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer
        )

    def _apply_palette_preferences(self, scene: dict[str, Any]) -> None:
        favorites = normalize_component_ids(scene.get(PALETTE_FAVORITES_KEY, ()))
        recent = normalize_component_ids(scene.get(PALETTE_RECENT_KEY, ()), limit=12)
        changed = (
            favorites != self._palette_favorites or recent != self._palette_recent
        )
        self._palette_favorites = favorites
        self._palette_recent = recent
        if changed:
            self.palettePreferencesChanged.emit(list(favorites), list(recent))

    def _apply_navigation_preferences(self, scene: dict[str, Any]) -> None:
        bookmarks: list[dict[str, Any]] = []
        used: set[str] = set()
        for index, raw in enumerate(scene.get(_VIEWPORT_BOOKMARKS_KEY, ())):
            if not isinstance(raw, dict):
                continue
            bookmark_id = str(raw.get("id", f"view-{index + 1}")).strip()
            if not bookmark_id or bookmark_id in used:
                continue
            used.add(bookmark_id)
            bookmarks.append({
                "id": bookmark_id,
                "label": str(raw.get("label", f"View {index + 1}")),
                "x": float(raw.get("x", 0.0)),
                "y": float(raw.get("y", 0.0)),
                "zoom": max(0.2, min(4.0, float(raw.get("zoom", 1.0)))),
            })
            if len(bookmarks) >= 32:
                break
        normalized = tuple(bookmarks)
        changed = normalized != self._viewport_bookmarks
        self._viewport_bookmarks = normalized
        self._minimap_visible = bool(scene.get(_MINIMAP_VISIBLE_KEY, self._minimap_visible))
        if hasattr(self, "_minimap"):
            self._minimap.setVisible(self._edit_mode and self._minimap_visible)
            self._place_minimap()
        if changed:
            self.viewportBookmarksChanged.emit(self.viewportBookmarks())

    def _add_element_record(self, entry: dict[str, Any]) -> str:
        values = dict(entry)
        kind = str(values["type"])
        if self._element_registry.definition(kind) is None:
            self._element_registry.register(
                ElementDefinition(
                    kind,
                    f"Missing: {kind}",
                    "Missing components",
                    float(values.get("width", 160)),
                    float(values.get("height", 80)),
                    icon="rectangle",
                    defaults={
                        "text": values.get("text", f"Missing component\n{kind}"),
                        "color": "#dc2626",
                        "background": "#fef2f2",
                    },
                    plugin_id="__missing__",
                )
            )
            self.diagnosticMessage.emit(
                f"Missing component type {kind!r}; rendered a safe placeholder"
            )
        values = self._element_registry.prepare_record(
            values, allow_newer=self.isReadOnly()
        )
        kind = values.pop("type")
        element_id = values.pop("id")
        x = values.pop("x", 0)
        y = values.pop("y", 0)
        width = values.pop("width", None)
        height = values.pop("height", None)
        return self.addElement(kind, x, y, width, height, element_id, **values)

    def _apply_element_record(self, element_id: str, entry: dict[str, Any]) -> None:
        values = dict(entry)
        values.pop("id", None)
        values.pop("type", None)
        if not self._required_element(element_id).supports_ports:
            values.pop("ports", None)
        self.updateElement(element_id, **values)
        item = self._required_element(element_id)
        item.definition = self._element_registry.definition(item.kind)
        item.color = _color(values.get("color", item.color), "#2563eb")
        item.background = _color(values.get("background", item.background), "#ffffff")
        item.text_color = _color(values.get("textColor", item.text_color), "#0f172a")
        item.update()

    def _add_connector_record(self, entry: dict[str, Any]) -> str:
        values = dict(entry)
        source_id = values.pop("source")
        target_id = values.pop("target")
        connector_id = values.pop("id")
        values.pop("type", None)
        color = values.pop("color", "#64748b")
        return self.connectElements(source_id, target_id, color, connector_id, **values)

    def _apply_connector_record(self, connector_id: str, entry: dict[str, Any]) -> None:
        values = dict(entry)
        values.pop("id", None)
        values.pop("type", None)
        self.updateConnector(connector_id, **values)

    def _add_group_record(self, entry: dict[str, Any]) -> str:
        item = _CanvasGroup(self, dict(entry))
        self._scene.addItem(item)
        self._groups[item.group_id] = item
        self._sync_object_states()
        self.groupAdded.emit(item.group_id)
        return item.group_id

    def _apply_group_record(self, group_id: str, entry: dict[str, Any]) -> None:
        item = self._groups[str(group_id)]
        item.prepareGeometryChange()
        item.kind = normalize_group_kind(entry.get("kind", item.kind))
        item.members = tuple(str(member) for member in entry.get("members", item.members))
        item.text = str(entry.get("label", entry.get("text", item.text)))
        item.color = _color(entry.get("color", item.color), "#64748b")
        item.background = _color(entry.get("background", item.background), "#f8fafc")
        item.header_color = _color(entry.get("headerColor", item.header_color), "#64748b")
        item.padding = max(0.0, min(120.0, float(entry.get("padding", item.padding))))
        item.collapsed = bool(entry.get("collapsed", item.collapsed))
        item.lanes = tuple(str(value) for value in entry.get("lanes", item.lanes))
        item.orientation = (
            "vertical" if str(entry.get("orientation", item.orientation)).lower() == "vertical"
            else "horizontal"
        )
        item.locked = bool(entry.get("locked", item.locked))
        item.hidden = bool(entry.get("hidden", item.hidden))
        item.custom_properties = {
            key: value for key, value in entry.items()
            if key not in _GROUP_STANDARD_PROPERTIES
        }
        item._rect.setWidth(max(120.0, float(entry.get("width", item._rect.width()))))
        item._rect.setHeight(max(54.0, float(entry.get("height", item._rect.height()))))
        item.setPos(float(entry.get("x", item.pos().x())), float(entry.get("y", item.pos().y())))
        item.setZValue(float(entry.get("z", item.zValue())))
        item.setOpacity(max(0.0, min(1.0, float(entry.get("opacity", item.opacity())))))
        item.setRotation(float(entry.get("rotation", item.rotation())))
        item.update()
        self._sync_object_states()

    def _remove_group_graphics(self, group_id: str) -> bool:
        item = self._groups.pop(str(group_id), None)
        if item is None:
            return False
        self._scene.removeItem(item)
        item.deleteLater()
        self.groupRemoved.emit(str(group_id))
        self._sync_object_states()
        return True

    def toDocument(self) -> dict[str, Any]:
        # Graphics-originated edits reconcile synchronously through
        # documentChanged, so serialization can read canonical state directly.
        return self._document_model.to_dict()

    def toJson(self, indent: int | None = 2) -> str:
        return json.dumps(self.toDocument(), ensure_ascii=False, indent=indent)

    def saveDocument(self, path: str | Path) -> Path:
        self._ensure_writable()
        target = Path(path)
        payload = self.toDocument()
        manifest = build_asset_manifest(payload, target.parent)
        if manifest:
            payload[ASSET_MANIFEST_KEY] = manifest
        else:
            payload.pop(ASSET_MANIFEST_KEY, None)
        atomic_write_json(target, payload)
        self._undo_stack.setClean()
        return target

    def persistentPath(self) -> Path:
        key = self._persistent_key or self.objectName() or "monkez_canva"
        safe_key = "".join(character if character.isalnum() or character in "-_." else "_" for character in key)
        return self.projectDirectoryPath() / ".monkez_canva" / f"{safe_key}.json"

    def projectDirectoryPath(self) -> Path:
        if self._project_directory:
            return Path(self._project_directory).expanduser().resolve()
        configured = os.environ.get("MONKEZ_CANVA_PROJECT_DIR", "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        candidates = [Path.cwd()]
        if sys.argv and sys.argv[0]:
            candidates.append(Path(sys.argv[0]).expanduser().resolve().parent)
        markers = (".git", "pyproject.toml", "setup.py", "requirements.txt")
        for candidate in candidates:
            for directory in (candidate, *candidate.parents):
                if any((directory / marker).exists() for marker in markers):
                    return directory
        return Path.cwd().resolve()

    def legacyPersistentPath(self) -> Path:
        root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        return root / "monkez_canva" / self.persistentPath().name

    def setProjectDirectory(self, path: str | Path) -> "MonkezCanva":
        self._project_directory = str(Path(path).expanduser().resolve()) if str(path).strip() else ""
        self._persistent_auto_load_attempted = False
        if self._persistent_key:
            QTimer.singleShot(0, self._auto_load_persistent)
        return self

    def getProjectDirectory(self) -> str:
        return str(self.projectDirectoryPath())

    def setPersistenceKey(self, key: str) -> "MonkezCanva":
        self._persistent_key = str(key).strip()
        self._persistent_auto_load_attempted = False
        if self._persistent_key:
            QTimer.singleShot(0, self._auto_load_persistent)
        return self

    def getPersistenceKey(self) -> str:
        return self._persistent_key

    def _auto_load_persistent(self) -> None:
        if self._persistent_auto_load_attempted or not self._persistent_key:
            return
        self._persistent_auto_load_attempted = True
        if self._elements or self._connectors:
            self.diagnosticMessage.emit("Portable auto-load skipped: canvas already contains objects")
            return
        persistent = self.persistentPath()
        legacy = self.legacyPersistentPath()
        if any(path.is_file() for path in (persistent, backup_path(persistent), legacy, backup_path(legacy))):
            self.loadPersistent()

    def saveSession(self) -> dict[str, Any]:
        self._session_document = json.loads(self.toJson(indent=None))
        self.autoSaved.emit("session checkpoint")
        return self._session_document

    def restoreSession(self) -> bool:
        if self._session_document is None:
            return False
        self._restore_document(self._session_document)
        self.autoSaved.emit("session checkpoint restored")
        return True

    def savePersistent(self, document: dict[str, Any] | None = None) -> Path:
        self._ensure_writable()
        target = self.persistentPath()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.loads(json.dumps(document if document is not None else self.toDocument()))
        assets = target.parent / "assets" / target.stem
        for entry in payload.get("elements", []):
            source_text = str(entry.get("source", ""))
            safe_id = "".join(character if character.isalnum() or character in "-_" else "_" for character in str(entry["id"]))
            if entry.get("type") in ("image", "animated_image") and source_text:
                managed = self._copy_managed_asset(source_text, safe_id, target, assets)
                if managed:
                    entry["source"] = managed
            packet_icon = str(entry.get("packetIcon", ""))
            if packet_icon:
                managed = self._copy_managed_asset(packet_icon, f"{safe_id}-packet", target, assets)
                if managed:
                    entry["packetIcon"] = managed
        for entry in payload.get("connectors", []):
            packet_icon = str(entry.get("packetIcon", ""))
            if packet_icon:
                safe_id = "".join(character if character.isalnum() or character in "-_" else "_" for character in str(entry["id"]))
                managed = self._copy_managed_asset(packet_icon, f"{safe_id}-packet", target, assets)
                if managed:
                    entry["packetIcon"] = managed
        scene = payload.setdefault("scene", {})
        background_image = str(scene.get("backgroundImage", ""))
        if background_image:
            managed = self._copy_managed_asset(background_image, "background", target, assets)
            if managed:
                scene["backgroundImage"] = managed
        for entry in payload.get("resources", []):
            uri = str(entry.get("uri", ""))
            if not uri:
                continue
            safe_id = "".join(
                character if character.isalnum() or character in "-_" else "_"
                for character in str(entry["id"])
            )
            managed = self._copy_managed_asset(uri, f"resource-{safe_id}", target, assets)
            if managed:
                entry["uri"] = managed
        payload[ASSET_MANIFEST_KEY] = build_asset_manifest(payload, target.parent)
        atomic_write_json(target, payload)
        self._asset_integrity_issues = []
        self.assetIntegrityChecked.emit([])
        self._undo_stack.setClean()
        self.persistentSaved.emit(str(target))
        self.autoSaved.emit(str(target))
        return target

    def loadPersistent(self) -> bool:
        source = self.persistentPath()
        if not source.is_file() and not backup_path(source).is_file():
            legacy = self.legacyPersistentPath()
            if legacy.is_file() or backup_path(legacy).is_file():
                source = legacy
                self.diagnosticMessage.emit(f"Migrating legacy persistent document: {legacy}")
            else:
                self.diagnosticMessage.emit(f"Persistent document not found: {source}")
                return False
        loaded = load_json_with_recovery(source)
        payload = loaded.payload
        self._last_recovery_source = str(loaded.source) if loaded.recovered_from_backup else ""
        if loaded.recovered_from_backup:
            self.diagnosticMessage.emit(
                f"Recovered persistent document from backup {loaded.source}; "
                f"primary error: {loaded.primary_error}"
            )
            self.recoveryLoaded.emit(str(source), str(loaded.source))
        self._prepare_loaded_assets(payload, source.parent)
        self._restore_document(payload, allow_newer=True)
        if source != self.persistentPath():
            if not self.isReadOnly():
                self.savePersistent()
        self.persistentLoaded.emit(str(source))
        self.autoSaved.emit(f"loaded {source}")
        return True

    def verifyPersistentAssets(self, path: str | Path | None = None) -> tuple[str, ...]:
        """Verify all relative managed assets against the saved SHA-256 manifest."""

        target = Path(path) if path is not None else self.persistentPath()
        loaded = load_json_with_recovery(target)
        issues = verify_asset_manifest(loaded.payload, target.parent)
        self._asset_integrity_issues = [issue.message() for issue in issues]
        self.assetIntegrityChecked.emit(list(self._asset_integrity_issues))
        return tuple(self._asset_integrity_issues)

    def _prepare_loaded_assets(self, payload: dict[str, Any], root: Path) -> None:
        issues = verify_asset_manifest(payload, root)
        self._asset_integrity_issues = [issue.message() for issue in issues]
        self.assetIntegrityChecked.emit(list(self._asset_integrity_issues))
        for issue in self._asset_integrity_issues:
            self.diagnosticMessage.emit(f"Asset integrity warning: {issue}")

        def resolve(value: Any) -> str:
            text = str(value or "")
            if (
                not text
                or "://" in text
                or text.lower().startswith(("data:", "qrc:"))
                or Path(text).is_absolute()
            ):
                return text
            candidate = (root / Path(text)).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                return ""
            return str(candidate)

        for entry in payload.get("elements", []):
            if entry.get("source"):
                entry["source"] = resolve(entry["source"])
            if entry.get("packetIcon"):
                entry["packetIcon"] = resolve(entry["packetIcon"])
        for entry in payload.get("connectors", []):
            if entry.get("packetIcon"):
                entry["packetIcon"] = resolve(entry["packetIcon"])
        scene = payload.get("scene", {})
        if scene.get("backgroundImage"):
            scene["backgroundImage"] = resolve(scene["backgroundImage"])
        for entry in payload.get("resources", []):
            if entry.get("uri"):
                entry["uri"] = resolve(entry["uri"])

    @staticmethod
    def _copy_managed_asset(source_text: str, asset_id: str, target: Path, assets: Path) -> str:
        source = Path(source_text).expanduser()
        if not source.is_file():
            return ""
        try:
            source.resolve().relative_to(assets.resolve())
            return source.resolve().relative_to(target.parent.resolve()).as_posix()
        except ValueError:
            pass
        safe_name = "".join(character if character.isalnum() or character in "-_." else "_" for character in source.name)
        destination = assets / f"{asset_id}-{safe_name}"
        assets.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            copy_asset_atomically(source, destination)
        return destination.relative_to(target.parent).as_posix()

    def setAutoSaveEnabled(self, enabled: bool) -> None:
        self._auto_save_enabled = bool(enabled)

    def getAutoSaveEnabled(self) -> bool:
        return self._auto_save_enabled

    def setAutoSaveDelay(self, milliseconds: int) -> None:
        self._auto_save_delay = max(100, int(milliseconds))

    def getAutoSaveDelay(self) -> int:
        return self._auto_save_delay

    def _queue_autosave(self) -> None:
        if self._restoring or self.isReadOnly():
            return
        if not self._document_render_notification:
            self._sync_document_from_graphics()
        document = json.loads(json.dumps(self._document_model.to_dict()))
        self._draft_document = document
        self._autosave_timer.start(self._auto_save_delay)

    def _flush_autosave(self) -> None:
        if self._restoring or self.isReadOnly():
            return
        document = json.loads(json.dumps(self._document_model.to_dict()))
        self._draft_document = document
        self.autoSaved.emit("in-memory draft")
        if self._auto_save_enabled and self._persistent_key:
            self.savePersistent(document)

    def undo(self) -> bool:
        if self.isReadOnly():
            return False
        self._flush_autosave()
        if not self._undo_stack.canUndo():
            return False
        self._undo_stack.undo()
        self.autoSaved.emit("undo")
        return True

    def redo(self) -> bool:
        if self.isReadOnly():
            return False
        if not self._undo_stack.canRedo():
            return False
        self._undo_stack.redo()
        self.autoSaved.emit("redo")
        return True

    def loadDocument(self, document: dict[str, Any] | str | Path) -> "MonkezCanva":
        asset_root: Path | None = None
        if isinstance(document, dict):
            data = document
        else:
            serialized = str(document)
            if serialized.lstrip().startswith("{"):
                data = json.loads(serialized)
            else:
                document_path = Path(serialized)
                loaded = load_json_with_recovery(document_path)
                data = loaded.payload
                asset_root = document_path.parent
                self._last_recovery_source = (
                    str(loaded.source) if loaded.recovered_from_backup else ""
                )
                if loaded.recovered_from_backup:
                    self.diagnosticMessage.emit(
                        f"Recovered document from backup {loaded.source}; "
                        f"primary error: {loaded.primary_error}"
                    )
                    self.recoveryLoaded.emit(serialized, str(loaded.source))
        if asset_root is not None:
            self._prepare_loaded_assets(data, asset_root)
        model = CanvasDocument.from_dict(data, allow_newer=True)
        return self.setDocumentModel(model)

    def _restore_document(
        self, data: dict[str, Any], *, allow_newer: bool = False
    ) -> None:
        model = CanvasDocument.from_dict(data, allow_newer=allow_newer)
        if model.is_read_only or self._newer_component_reasons(model.to_dict()):
            self.setDocumentModel(model)
            return
        events = self._document_model.reconcile(model.to_dict())
        self._set_read_only_reason("")
        if events:
            self._last_rendered_document_revision = self._document_model.revision
        self._undo_stack.clear()

    def _render_document(self, data: dict[str, Any]) -> None:
        if data.get("format") != "monkez-canva":
            raise ValueError("Unsupported MonkezCanva document")
        previous = self._restoring
        self._restoring = True
        scene = data.get("scene", {})
        width = max(100.0, float(scene.get("width", self._scene.sceneRect().width())))
        height = max(100.0, float(scene.get("height", self._scene.sceneRect().height())))
        self._scene.setSceneRect(-width / 2, -height / 2, width, height)
        self._grid_visible = bool(scene.get("gridVisible", self._grid_visible))
        self._snap_to_grid = bool(scene.get("snapToGrid", self._snap_to_grid))
        self._snap_targets = normalize_snap_targets(
            scene.get(SNAP_TARGETS_KEY, self._snap_targets)
        )
        self._snap_distance = max(
            1.0, min(40.0, float(scene.get(SNAP_DISTANCE_KEY, self._snap_distance)))
        )
        self._smart_guides_visible = bool(
            scene.get(SMART_GUIDES_KEY, self._smart_guides_visible)
        )
        self._grid_size = max(4, int(scene.get("gridSize", self._grid_size)))
        self._grid_style = max(0, min(len(_GRID_STYLES) - 1, int(scene.get("gridStyle", self._grid_style))))
        self._grid_color = _color(scene.get("gridColor", self._grid_color), "#e2e8f0")
        self._background_color = _color(scene.get("backgroundColor", self._background_color), "#f8fafc")
        self._background_image = str(scene.get("backgroundImage", ""))
        self._background_image_mode = max(
            0,
            min(len(_BACKGROUND_IMAGE_MODES) - 1, int(scene.get("backgroundImageMode", 0))),
        )
        self._background_pixmap = QPixmap(self._background_image) if self._background_image else QPixmap()
        self._apply_palette_preferences(scene)
        self._apply_navigation_preferences(scene)
        self.clear()
        for entry in data.get("elements", []):
            self._add_element_record(dict(entry))
        for entry in data.get("connectors", []):
            self._add_connector_record(dict(entry))
        for group in tuple(self._groups.values()):
            self._scene.removeItem(group)
            group.deleteLater()
        self._groups.clear()
        for entry in data.get("groups", []):
            self._add_group_record(dict(entry))
        self._restoring = previous
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        if not previous:
            self._document_render_notification = True
            try:
                self.documentChanged.emit()
            finally:
                self._document_render_notification = False

    def fitContent(self) -> None:
        bounds = self._scene.itemsBoundingRect()
        if bounds.isEmpty():
            return
        viewport = self._view.viewport()
        if not self.isVisible() or viewport.width() < 160 or viewport.height() < 120:
            self._fit_pending = True
            self.diagnosticMessage.emit(
                f"Fit deferred until canvas is visible; viewport={viewport.width()}x{viewport.height()}"
            )
            return
        self._apply_fit_content(bounds)

    def _apply_fit_content(self, bounds: QRectF | None = None) -> None:
        bounds = bounds or self._scene.itemsBoundingRect()
        if bounds.isEmpty():
            return
        padded = bounds.adjusted(-50, -50, 50, 50)
        self._view.resetTransform()
        self._view.fitInView(padded, Qt.AspectRatioMode.KeepAspectRatio)
        scale = self._view.transform().m11()
        target = min(2.0, max(0.2, scale))
        if scale > 0 and not math.isclose(scale, target):
            correction = target / scale
            self._view.scale(correction, correction)
        self._view.centerOn(bounds.center())
        self._fit_pending = False
        self.diagnosticMessage.emit(
            f"Content fitted; items={bounds.width():.0f}x{bounds.height():.0f}; zoom={target:.2f}x"
        )

    def zoomIn(self) -> None:
        self._set_zoom(self._view.transform().m11() * 1.2)

    def zoomOut(self) -> None:
        self._set_zoom(self._view.transform().m11() / 1.2)

    def resetZoom(self) -> None:
        center = self._view.mapToScene(self._view.viewport().rect().center())
        self._view.resetTransform()
        self._view.centerOn(center)
        self.diagnosticMessage.emit("Viewport zoom=1.00x")

    def _set_zoom(self, target: float) -> None:
        current = self._view.transform().m11()
        target = min(4.0, max(0.2, float(target)))
        if current > 0:
            factor = target / current
            self._view.scale(factor, factor)
            self.diagnosticMessage.emit(f"Viewport zoom={target:.2f}x")

    def moveViewport(self, dx: float, dy: float) -> None:
        center = self._view.mapToScene(self._view.viewport().rect().center())
        self._view.centerOn(center + QPointF(float(dx), float(dy)))

    def viewportBookmarks(self) -> list[dict[str, Any]]:
        return [dict(bookmark) for bookmark in self._viewport_bookmarks]

    def addViewportBookmark(self, label: str = "") -> str:
        center = self._view.mapToScene(self._view.viewport().rect().center())
        bookmark_id = uuid.uuid4().hex[:10]
        bookmark = {
            "id": bookmark_id,
            "label": str(label).strip() or f"View {len(self._viewport_bookmarks) + 1}",
            "x": center.x(),
            "y": center.y(),
            "zoom": self._view.transform().m11(),
        }
        bookmarks = [*self.viewportBookmarks(), bookmark]
        self._push_document_mutation(
            lambda document: document.update_scene({_VIEWPORT_BOOKMARKS_KEY: bookmarks}),
            "Add viewport bookmark",
        )
        return bookmark_id

    def removeViewportBookmark(self, bookmark_id: str) -> bool:
        key = str(bookmark_id)
        bookmarks = [item for item in self.viewportBookmarks() if item["id"] != key]
        if len(bookmarks) == len(self._viewport_bookmarks):
            return False
        return self._push_document_mutation(
            lambda document: document.update_scene({_VIEWPORT_BOOKMARKS_KEY: bookmarks}),
            "Remove viewport bookmark",
        )

    def goToViewportBookmark(self, bookmark_id: str) -> bool:
        key = str(bookmark_id)
        bookmark = next(
            (item for item in self._viewport_bookmarks if item["id"] == key or item["label"] == key),
            None,
        )
        if bookmark is None:
            return False
        self._set_zoom(float(bookmark["zoom"]))
        self._view.centerOn(float(bookmark["x"]), float(bookmark["y"]))
        self._minimap.update()
        return True

    def minimapVisible(self) -> bool:
        return self._minimap_visible

    def setMinimapVisible(self, visible: bool) -> None:
        normalized = bool(visible)
        if normalized == self._minimap_visible:
            return
        self._push_document_mutation(
            lambda document: document.update_scene({_MINIMAP_VISIBLE_KEY: normalized}),
            "Toggle minimap",
        )

    def _place_minimap(self) -> None:
        minimap = self._minimap
        view_rect = self._view.geometry()
        minimap.move(
            view_rect.right() - minimap.width() - 14,
            view_rect.bottom() - minimap.height() - 14,
        )

    def _update_minimap(self, *_args) -> None:
        self._minimap.update()

    def centerOnSelection(self) -> bool:
        item = self.canvasObject(self.selectedElementId())
        if item is None:
            return False
        self._view.centerOn(item)
        return True

    def togglePanMode(self) -> bool:
        self._pan_mode = not self._pan_mode
        mode = QGraphicsView.DragMode.ScrollHandDrag if self._pan_mode else QGraphicsView.DragMode.RubberBandDrag
        self._view.setDragMode(mode)
        self.diagnosticMessage.emit(f"Pan mode={self._pan_mode}")
        return self._pan_mode

    def toggleEditMode(self) -> None:
        self.setEditMode(not self._edit_mode)

    def _activate_editor_shortcut(self, source: str) -> None:
        self.diagnosticMessage.emit(f"Editor shortcut received: {source}")
        self.toggleEditMode()

    def getEditMode(self) -> bool:
        return self._edit_mode

    def setEditMode(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._edit_mode:
            return
        self._edit_mode = enabled
        self._sync_object_states()
        if enabled:
            self._place_quick_toolbar()
            self._quick_toolbar.show()
            self._quick_toolbar.raise_()
            self._place_minimap()
            self._minimap.setVisible(self._minimap_visible)
            self._minimap.raise_()
        else:
            self._quick_toolbar.hide()
            self._minimap.hide()
            if self._command_palette is not None:
                self._command_palette.hide()
        self._view.setDragMode(QGraphicsView.DragMode.RubberBandDrag if enabled else QGraphicsView.DragMode.ScrollHandDrag)
        if enabled:
            if self._toolbox is None:
                self._toolbox = _CanvasEditorToolbox(self)
            self._toolbox.setParent(self.window(), self._toolbox.windowFlags())
            self._toolbox.show()
            self._place_toolbox_on_screen()
            self._toolbox.raise_()
        elif self._toolbox is not None:
            self._toolbox.hide()
        toolbox_state = "visible" if self._toolbox is not None and self._toolbox.isVisible() else "hidden"
        self.diagnosticMessage.emit(f"Edit mode={enabled}; toolbox={toolbox_state}")
        self.editModeChanged.emit(enabled)

    def _place_quick_toolbar(self) -> None:
        toolbar = self._quick_toolbar
        toolbar.adjustSize()
        view_rect = self._view.geometry()
        x = view_rect.left() + max(10, (view_rect.width() - toolbar.width()) // 2)
        toolbar.move(x, view_rect.top() + 12)

    def _place_toolbox_on_screen(self) -> None:
        if self._toolbox is None:
            return
        host = self.window()
        screen = host.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        toolbox_size = self._toolbox.sizeHint().expandedTo(self._toolbox.minimumSizeHint())
        host_top_right = host.mapToGlobal(host.rect().topRight())
        x = host_top_right.x() + 12
        y = host.mapToGlobal(host.rect().topLeft()).y() + 48
        if x + toolbox_size.width() > available.right():
            x = host_top_right.x() - toolbox_size.width() - 20
        x = min(max(x, available.left()), available.right() - toolbox_size.width() + 1)
        y = min(max(y, available.top()), available.bottom() - toolbox_size.height() + 1)
        self._toolbox.move(x, y)
        self.diagnosticMessage.emit(
            f"Toolbox placed at ({x}, {y}), size={toolbox_size.width()}x{toolbox_size.height()}"
        )

    def getShortcutEnabled(self) -> bool:
        return self._shortcut_enabled

    def setShortcutEnabled(self, enabled: bool) -> None:
        self._shortcut_enabled = bool(enabled)
        for shortcut in self._toggle_shortcuts:
            shortcut.setEnabled(self._shortcut_enabled)
        self.diagnosticMessage.emit(f"Editor shortcuts enabled={self._shortcut_enabled}")

    def getGridVisible(self) -> bool:
        return self._grid_visible

    def setGridVisible(self, visible: bool) -> None:
        visible = bool(visible)
        if visible == self._grid_visible:
            return
        self._ensure_writable()
        self._grid_visible = visible
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getSnapToGrid(self) -> bool:
        return self._snap_to_grid

    def setSnapToGrid(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._snap_to_grid:
            return
        self._ensure_writable()
        self._snap_to_grid = enabled
        self.documentChanged.emit()

    def snapTargets(self) -> tuple[str, ...]:
        return self._snap_targets

    def setSnapTargets(self, targets) -> None:
        normalized = normalize_snap_targets(targets)
        if normalized == self._snap_targets:
            return
        self._ensure_writable()
        self._snap_targets = normalized
        self.documentChanged.emit()

    def snapDistance(self) -> float:
        return self._snap_distance

    def setSnapDistance(self, distance: float) -> None:
        normalized = max(1.0, min(40.0, float(distance)))
        if math.isclose(normalized, self._snap_distance):
            return
        self._ensure_writable()
        self._snap_distance = normalized
        self.documentChanged.emit()

    def smartGuidesVisible(self) -> bool:
        return self._smart_guides_visible

    def setSmartGuidesVisible(self, visible: bool) -> None:
        normalized = bool(visible)
        if normalized == self._smart_guides_visible:
            return
        self._ensure_writable()
        self._smart_guides_visible = normalized
        if not normalized:
            self._scene.clearSmartGuides()
        self.documentChanged.emit()

    def _snap_item_position(self, item: _CanvasElement, position: QPointF) -> QPointF:
        targets = tuple(
            target for target in self._snap_targets
            if target != "grid" or self._snap_to_grid
        )
        if not targets:
            self._scene.clearSmartGuides()
            return position
        selected = set(self.selectedElementIds())
        candidates = [
            SnapRect(other.pos().x(), other.pos().y(), other._rect.width(), other._rect.height())
            for element_id, other in self._elements.items()
            if element_id != item.element_id and element_id not in selected
        ]
        candidate_ports = [
            (point.x(), point.y())
            for element_id, other in self._elements.items()
            if element_id != item.element_id and element_id not in selected
            for port in other.ports
            for point in (other.portScenePosition(port["id"]),)
        ]
        offset = position - item.pos()
        moving_ports = [
            (point.x() + offset.x(), point.y() + offset.y())
            for port in item.ports
            for point in (item.portScenePosition(port["id"]),)
        ]
        result = snap_rect(
            SnapRect(position.x(), position.y(), item._rect.width(), item._rect.height()),
            candidates,
            targets=targets,
            grid_size=self._grid_size,
            threshold=self._snap_distance,
            moving_ports=moving_ports,
            candidate_ports=candidate_ports,
        )
        self._scene.setSmartGuides(result.guides)
        return QPointF(result.x, result.y)

    def getGridSize(self) -> int:
        return self._grid_size

    def setGridSize(self, size: int) -> None:
        size = max(4, int(size))
        if size == self._grid_size:
            return
        self._ensure_writable()
        self._grid_size = size
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getGridStyle(self) -> int:
        return self._grid_style

    def setGridStyle(self, style: int | str) -> None:
        if isinstance(style, str):
            normalized = style.lower().strip()
            if normalized not in _GRID_STYLES:
                raise ValueError(f"Unsupported MonkezCanva grid style: {style}")
            index = _GRID_STYLES.index(normalized)
        else:
            index = max(0, min(len(_GRID_STYLES) - 1, int(style)))
        if index == self._grid_style:
            return
        self._ensure_writable()
        self._grid_style = index
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: Any) -> None:
        color = _color(value, "#f8fafc")
        if color == self._background_color:
            return
        self._ensure_writable()
        self._background_color = color
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getBackgroundImage(self) -> str:
        return self._background_image

    def setBackgroundImage(self, path: str | Path) -> None:
        text = str(path).strip()
        source = str(Path(text).expanduser().resolve()) if text else ""
        if source == self._background_image:
            return
        self._ensure_writable()
        pixmap = QPixmap(source) if source else QPixmap()
        if source and pixmap.isNull():
            raise ValueError(f"Unsupported canvas background image: {source}")
        self._background_image = source
        self._background_pixmap = pixmap
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getBackgroundImageMode(self) -> int:
        return self._background_image_mode

    def setBackgroundImageMode(self, mode: int | str) -> None:
        if isinstance(mode, str):
            normalized = mode.lower().strip()
            if normalized not in _BACKGROUND_IMAGE_MODES:
                raise ValueError(f"Unsupported canvas background image mode: {mode}")
            index = _BACKGROUND_IMAGE_MODES.index(normalized)
        else:
            index = max(0, min(len(_BACKGROUND_IMAGE_MODES) - 1, int(mode)))
        if index == self._background_image_mode:
            return
        self._ensure_writable()
        self._background_image_mode = index
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getGridColor(self) -> QColor:
        return QColor(self._grid_color)

    def setGridColor(self, value: Any) -> None:
        color = _color(value, "#e2e8f0")
        if color == self._grid_color:
            return
        self._ensure_writable()
        self._grid_color = color
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def _required_element(self, element_id: str) -> _CanvasElement:
        item = self._elements.get(str(element_id))
        if item is None:
            raise KeyError(f"Unknown MonkezCanva element: {element_id}")
        return item

    def _required_connector(self, connector_id: str) -> _CanvasConnector:
        connector = self._connectors.get(str(connector_id))
        if connector is None:
            raise KeyError(f"Unknown MonkezCanva connector: {connector_id}")
        return connector

    def _clear_highlight(
        self, item: _CanvasElement | _CanvasConnector | _CanvasGroup
    ) -> None:
        if self.canvasObject(item.element_id) is item:
            item._highlight = QColor()
            item.update()

    def _element_changed(self, _element_id: str) -> None:
        self._routing_revision += 1
        for connector in self._connectors.values():
            if connector.route == "auto":
                connector.updatePath()
        self.documentChanged.emit()

    def _connector_changed(self, _connector_id: str) -> None:
        self._routing_revision += 1
        self.documentChanged.emit()

    def _emit_selection(self) -> None:
        element_ids = self.selectedObjectIds()
        self.selectionChanged.emit(element_ids[0] if element_ids else "")
        self.selectionSetChanged.emit(element_ids)

    editMode = pyqtProperty(bool, getEditMode, setEditMode)
    editorShortcutEnabled = pyqtProperty(bool, getShortcutEnabled, setShortcutEnabled)
    gridVisible = pyqtProperty(bool, getGridVisible, setGridVisible)
    snapToGrid = pyqtProperty(bool, getSnapToGrid, setSnapToGrid)
    gridSize = pyqtProperty(int, getGridSize, setGridSize)
    gridStyle = pyqtProperty(int, getGridStyle, setGridStyle)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    backgroundImage = pyqtProperty(str, getBackgroundImage, setBackgroundImage)
    backgroundImageMode = pyqtProperty(int, getBackgroundImageMode, setBackgroundImageMode)
    gridColor = pyqtProperty(QColor, getGridColor, setGridColor)
    persistenceKey = pyqtProperty(str, getPersistenceKey, setPersistenceKey)
    projectDirectory = pyqtProperty(str, getProjectDirectory, setProjectDirectory)
    autoSaveEnabled = pyqtProperty(bool, getAutoSaveEnabled, setAutoSaveEnabled)
    autoSaveDelay = pyqtProperty(int, getAutoSaveDelay, setAutoSaveDelay)

    def closeEvent(self, event) -> None:
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()
            self._flush_autosave()
        if self._toolbox is not None:
            self._toolbox.close()
        if self._command_palette is not None:
            self._command_palette.close()
        if self._document_model is not None and self._document_subscription:
            self._document_model.unsubscribe(self._document_subscription)
            self._document_subscription = ""
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._fit_pending:
            QTimer.singleShot(0, self._apply_fit_content)
        QTimer.singleShot(0, self._animation_scheduler.visibility_changed)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._animation_scheduler.visibility_changed()
