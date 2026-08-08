"""Interactive canvas, chart and flow-diagram editor for Monkez applications."""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from PyQt6.QtCore import (
    QSignalBlocker,
    QStandardPaths,
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
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
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
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


_ELEMENT_DEFAULTS: dict[str, tuple[float, float]] = {
    "rectangle": (140, 80),
    "ellipse": (120, 80),
    "text": (160, 48),
    "button": (120, 42),
    "node": (180, 96),
    "bar_chart": (260, 160),
    "line_chart": (260, 160),
    "image": (280, 180),
    "animated_image": (280, 180),
    "diamond": (120, 100),
    "triangle": (120, 100),
    "line": (220, 40),
}

_GRID_STYLES = ("lines", "dots", "cross")
_BACKGROUND_IMAGE_MODES = ("fit", "fill", "scale")


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
        port_id = str(raw.get("id", f"port-{index + 1}")).strip()
        if not port_id or port_id in used:
            raise ValueError(f"Node port ID must be unique and non-empty: {port_id!r}")
        used.add(port_id)
        mode = str(raw.get("mode", "free")).lower().strip()
        mode = {"in": "input", "out": "output", "io": "free", "bidirectional": "free"}.get(mode, mode)
        if mode not in ("input", "output", "free"):
            raise ValueError(f"Unsupported node port mode: {mode}")
        default_side = "left" if mode == "input" else "right" if mode == "output" else "bottom"
        side = str(raw.get("side", default_side)).lower().strip()
        if side not in ("left", "right", "top", "bottom"):
            raise ValueError(f"Unsupported node port side: {side}")
        position = raw.get("position")
        port = {
            "id": port_id,
            "mode": mode,
            "side": side,
            "label": str(raw.get("label", port_id)),
        }
        if position is not None:
            port["position"] = max(0.0, min(1.0, float(position)))
        ports.append(port)
    return ports


def _color(value: Any, fallback: str = "#2563eb") -> QColor:
    result = QColor(value)
    return result if result.isValid() else QColor(fallback)


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

    def __init__(
        self,
        element_id: str,
        kind: str,
        width: float,
        height: float,
        options: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        options = dict(options or {})
        self.element_id = element_id
        self.kind = kind
        self._rect = QRectF(0, 0, max(24.0, width), max(24.0, height))
        self.text = str(options.get("text", kind.replace("_", " ").title()))
        self.color = _color(options.get("color", "#2563eb"))
        self.background = _color(options.get("background", "#ffffff"), "#ffffff")
        self.text_color = _color(options.get("textColor", "#0f172a"), "#0f172a")
        self.data = list(options.get("data", [32, 68, 46, 82, 58]))
        self.metadata = dict(options.get("metadata", {}))
        self.source = str(options.get("source", ""))
        self.line_width = max(0.5, float(options.get("lineWidth", 2.2)))
        self.line_style = str(options.get("lineStyle", "solid")).lower()
        self.arrow_start = bool(options.get("arrowStart", False))
        self.arrow_end = bool(options.get("arrowEnd", False))
        raw_points = options.get("points", [])
        self.points = [QPointF(float(point[0]), float(point[1])) for point in raw_points]
        self.ports = _normalize_node_ports(options.get("ports")) if kind == "node" else []
        self._pixmap = QPixmap()
        self._movie: QMovie | None = None
        self._highlight = QColor()
        self._resizing = False
        self._resize_origin = QPointF()
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

    def setSource(self, source: str) -> None:
        self.source = str(source)
        self._load_media()
        self.update()
        self.changed.emit(self.element_id)

    def boundingRect(self) -> QRectF:
        margin = 11 if self.kind == "node" else 5
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
        if self.kind != "node":
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
            painter.setPen(QPen(QColor("#ffffff"), 1.8))
            painter.setBrush(color)
            if mode == "input":
                path = QPainterPath(QPointF(point.x() - 6, point.y() - 6))
                path.lineTo(QPointF(point.x() + 6, point.y()))
                path.lineTo(QPointF(point.x() - 6, point.y() + 6))
                path.closeSubpath()
                painter.drawPath(path)
            elif mode == "output":
                painter.drawEllipse(point, 6, 6)
                painter.setPen(QPen(QColor("#ffffff"), 1.3))
                painter.drawLine(point + QPointF(-2, 0), point + QPointF(3, 0))
                painter.drawLine(point + QPointF(1, -2), point + QPointF(3, 0))
                painter.drawLine(point + QPointF(1, 2), point + QPointF(3, 0))
            else:
                path = QPainterPath(QPointF(point.x(), point.y() - 7))
                path.lineTo(QPointF(point.x() + 7, point.y()))
                path.lineTo(QPointF(point.x(), point.y() + 7))
                path.lineTo(QPointF(point.x() - 7, point.y()))
                path.closeSubpath()
                painter.drawPath(path)

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
        if self.arrow_start and len(points) > 1:
            self._paint_line_arrow(painter, points[0], points[1])
        if self.arrow_end and len(points) > 1:
            self._paint_line_arrow(painter, points[-1], points[-2])

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
        self.changed.emit(self.element_id)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            canvas = self.scene().canvas
            if canvas.snapToGrid and canvas.editMode:
                size = canvas.gridSize
                value = QPointF(round(value.x() / size) * size, round(value.y() / size) * size)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.changed.emit(self.element_id)
        return super().itemChange(change, value)

    def to_dict(self) -> dict[str, Any]:
        return {
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
            "points": [[point.x(), point.y()] for point in self.points],
            "ports": [dict(port) for port in self.ports],
            "opacity": self.opacity(),
            "rotation": self.rotation(),
            "z": self.zValue(),
        }


class _CanvasConnector(QGraphicsObject):
    """Selectable, serializable signal path between two node-like elements."""

    changed = pyqtSignal(str)

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
        self.flow_speed = max(0.1, float(options.get("flowSpeed", 1.0)))
        self.waypoints = [QPointF(float(point[0]), float(point[1])) for point in options.get("waypoints", [])]
        self.metadata = dict(options.get("metadata", {}))
        self._highlight = QColor()
        self._path = QPainterPath()
        self._flow_phase = 0.0
        self._timer = QTimer(canvas)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._advance_flow)
        self.setZValue(float(options.get("z", -1)))
        self.setOpacity(max(0.0, min(1.0, float(options.get("opacity", 1.0)))))
        source.changed.connect(self.updatePath)
        target.changed.connect(self.updatePath)
        self.setEditable(canvas.editMode)
        self.updatePath()
        self._sync_animation()

    def boundingRect(self) -> QRectF:
        margin = max(12.0, self.line_width + 9.0)
        return self._path.boundingRect().adjusted(-margin, -margin, margin, margin)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(max(12.0, self.line_width + 8.0))
        return stroker.createStroke(self._path)

    def setEditable(self, enabled: bool) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, enabled)
        if not enabled:
            self.setSelected(False)

    def updatePath(self, *_args) -> None:
        self.prepareGeometryChange()
        start = self.source.portScenePosition(self.source_port, "source")
        end = self.target.portScenePosition(self.target_port, "target")
        path = QPainterPath(start)
        if self.route == "straight":
            path.lineTo(end)
        elif self.route in ("orthogonal", "elbow"):
            middle_x = (start.x() + end.x()) / 2
            path.lineTo(QPointF(middle_x, start.y()))
            path.lineTo(QPointF(middle_x, end.y()))
            path.lineTo(end)
        elif self.route == "polyline" and self.waypoints:
            for point in self.waypoints:
                path.lineTo(point)
            path.lineTo(end)
        else:
            delta = max(50.0, abs(end.x() - start.x()) * 0.5)
            direction = 1 if end.x() >= start.x() else -1
            path.cubicTo(
                QPointF(start.x() + delta * direction, start.y()),
                QPointF(end.x() - delta * direction, end.y()),
                end,
            )
        self._path = path
        self.update()

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
        painter.drawPath(self._path)
        if self.animated:
            flow_pen = QPen(self.flow_color, max(1.5, self.line_width * 0.65))
            flow_pen.setDashPattern([2.0, 5.0])
            flow_pen.setDashOffset(self._flow_phase)
            flow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(flow_pen)
            painter.drawPath(self._path)
        if self.arrow_start:
            self._paint_arrow(painter, 0.0)
        if self.arrow_end:
            self._paint_arrow(painter, 1.0)

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

    def _advance_flow(self) -> None:
        self._flow_phase -= self.flow_speed
        self.update()

    def _sync_animation(self) -> None:
        if self.animated and not self._timer.isActive():
            self._timer.start()
        elif not self.animated:
            self._timer.stop()
        self.update()

    def release(self) -> None:
        self._timer.stop()

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
            "flowSpeed": self.flow_speed,
            "waypoints": [[point.x(), point.y()] for point in self.waypoints],
            "metadata": dict(self.metadata),
            "opacity": self.opacity(),
            "z": self.zValue(),
        }


class _CanvasPaneHeader(QFrame):
    """Custom title bar that keeps the compact editor pane draggable."""

    def __init__(self, dialog: QDialog, canvas: "MonkezCanva") -> None:
        super().__init__(dialog)
        self._drag_offset = None
        self.setObjectName("canvasPaneHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(0)
        title = QLabel("MonkezCanva")
        title.setObjectName("canvasPaneTitle")
        subtitle = QLabel("Visual workspace editor")
        subtitle.setObjectName("canvasPaneSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        layout.addStretch(1)
        close = QToolButton()
        close.setObjectName("canvasPaneClose")
        close.setIcon(_canvas_icon("close"))
        close.setIconSize(QSize(16, 16))
        close.setToolTip("Close edit mode (Ctrl+D, E)")
        close.clicked.connect(lambda _checked=False: canvas.setEditMode(False))
        layout.addWidget(close)

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


class _CanvasEditorToolbox(QDialog):
    """Floating multi-tab editor for elements, layers, viewport and persistence."""

    def __init__(self, canvas: "MonkezCanva") -> None:
        super().__init__(canvas.window())
        self.canvas = canvas
        self._syncing_layers = False
        self.setWindowTitle("MonkezCanva Editor")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(420, 580)
        self.resize(440, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        panel = QFrame()
        panel.setObjectName("canvasEditorPanel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(15, 23, 42, 70))
        panel.setGraphicsEffect(shadow)
        root.addWidget(panel)
        content = QVBoxLayout(panel)
        content.setContentsMargins(14, 12, 14, 10)
        content.setSpacing(10)
        content.addWidget(_CanvasPaneHeader(self, canvas))
        tabs = QTabWidget()
        tabs.setObjectName("canvasEditorTabs")
        tabs.setDocumentMode(True)
        tabs.tabBar().setExpanding(True)
        tabs.tabBar().setUsesScrollButtons(False)
        tabs.addTab(self._elements_tab(), "Add")
        tabs.addTab(self._inspector_tab(), "Inspect")
        tabs.addTab(self._layers_tab(), "Layers")
        tabs.addTab(self._view_tab(), "View")
        tabs.addTab(self._save_tab(), "Save")
        content.addWidget(tabs, 1)
        hint = QLabel("Ctrl+D, E  close     Del  remove     Ctrl+wheel  zoom")
        hint.setObjectName("canvasPaneHint")
        content.addWidget(hint)
        self.setStyleSheet(self._pane_stylesheet())
        canvas.elementAdded.connect(lambda _element_id: self.refreshLayers())
        canvas.elementRemoved.connect(lambda _element_id: self.refreshLayers())
        canvas.connectorAdded.connect(lambda _connector_id: self.refreshLayers())
        canvas.connectorRemoved.connect(lambda _connector_id: self.refreshLayers())
        canvas.selectionChanged.connect(self._sync_inspector)
        canvas.selectionSetChanged.connect(lambda _element_ids: self.refreshLayers())
        canvas.autoSaved.connect(self._show_save_status)
        canvas.documentChanged.connect(self._sync_view_controls)
        self._sync_inspector(canvas.selectedElementId())
        self.refreshLayers()

    @staticmethod
    def _pane_stylesheet() -> str:
        return """
        QFrame#canvasEditorPanel {
            background: #f8fafc;
            border: 1px solid #d7e0ea;
            border-radius: 16px;
        }
        QFrame#canvasPaneHeader { border: none; background: transparent; }
        QLabel#canvasPaneTitle { color: #0f172a; font-size: 16px; font-weight: 700; }
        QLabel#canvasPaneSubtitle { color: #64748b; font-size: 10px; }
        QToolButton#canvasPaneClose {
            color: #64748b; background: transparent; border: none;
            border-radius: 9px; min-width: 28px; min-height: 28px; font-weight: 700;
        }
        QToolButton#canvasPaneClose:hover { color: #b91c1c; background: #fee2e2; }
        QLabel#canvasPaneHint { color: #94a3b8; font-size: 9px; padding: 1px 3px; }
        QLabel#canvasSaveStatus {
            color: #166534; background: #dcfce7; border: 1px solid #bbf7d0;
            border-radius: 7px; padding: 7px;
        }
        QTabWidget#canvasEditorTabs::pane { border: none; background: transparent; }
        QTabBar::tab {
            color: #64748b; background: transparent; border: none;
            padding: 7px 10px; margin-right: 2px; font-weight: 600;
        }
        QTabBar::tab:selected { color: #2563eb; border-bottom: 2px solid #2563eb; }
        QTabBar::tab:hover:!selected { color: #334155; background: #eef2f7; border-radius: 6px; }
        QGroupBox {
            color: #334155; background: #ffffff; border: 1px solid #e2e8f0;
            border-radius: 10px; margin-top: 9px; padding: 10px 7px 7px 7px;
            font-weight: 600;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        QPushButton, QToolButton {
            color: #334155; background: #ffffff; border: 1px solid #d7e0ea;
            border-radius: 7px; padding: 5px 8px; min-height: 24px;
        }
        QPushButton:hover, QToolButton:hover {
            color: #1d4ed8; border-color: #93c5fd; background: #eff6ff;
        }
        QPushButton:pressed, QToolButton:pressed { background: #dbeafe; }
        QPushButton:disabled, QToolButton:disabled { color: #a8b3c2; background: #f1f5f9; }
        QPushButton#primaryAction { color: #ffffff; background: #2563eb; border-color: #2563eb; font-weight: 600; }
        QPushButton#primaryAction:hover { background: #1d4ed8; border-color: #1d4ed8; }
        QPushButton#dangerAction { color: #b91c1c; background: #fff7f7; border-color: #fecaca; }
        QPushButton#dangerAction:hover { background: #fee2e2; border-color: #fca5a5; }
        QLineEdit, QDoubleSpinBox, QComboBox, QListWidget {
            color: #0f172a; background: #ffffff; border: 1px solid #d7e0ea;
            border-radius: 7px; padding: 4px 7px; selection-background-color: #bfdbfe;
        }
        QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus, QListWidget:focus { border: 1px solid #60a5fa; }
        QComboBox::drop-down { border: none; width: 22px; }
        QCheckBox { color: #334155; spacing: 7px; }
        QListWidget { padding: 4px; }
        QListWidget::item { border-radius: 6px; padding: 7px; margin: 1px; }
        QListWidget::item:selected { color: #1d4ed8; background: #dbeafe; }
        QListWidget::item:hover:!selected { background: #f1f5f9; }
        QLabel { color: #475569; }
        """

    def _elements_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(7)
        groups = {
            "Shapes": (
                ("Text", "text"), ("Rectangle", "rectangle"), ("Ellipse", "ellipse"),
                ("Button", "button"), ("Diamond", "diamond"), ("Triangle", "triangle"),
            ),
            "Diagram & data": (
                ("Node", "node"), ("Line / arrow", "line"),
                ("Bar chart", "bar_chart"), ("Line chart", "line_chart"),
            ),
            "Media": (("Image", "image"), ("Animated GIF", "animated_image")),
        }
        for group_name, entries in groups.items():
            group = QGroupBox(group_name)
            grid = QGridLayout(group)
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(6)
            for index, (label, kind) in enumerate(entries):
                button = QToolButton()
                button.setText(label)
                button.setIcon(_canvas_icon("gif" if kind == "animated_image" else kind))
                button.setIconSize(QSize(17, 17))
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                button.setMinimumSize(100, 34)
                if kind in ("image", "animated_image"):
                    button.clicked.connect(lambda _checked=False, value=kind: self._choose_media(value))
                else:
                    button.clicked.connect(lambda _checked=False, value=kind: self.canvas.addElement(value))
                grid.addWidget(button, index // 2, index % 2)
            layout.addWidget(group)
        connect_selected = QPushButton("Connect 2 selected items")
        connect_selected.setObjectName("primaryAction")
        connect_selected.setIcon(_canvas_icon("connector", "#ffffff"))
        connect_selected.setToolTip("Create a selectable connector between exactly two selected items")
        connect_selected.clicked.connect(self.canvas.connectSelected)
        layout.addWidget(connect_selected)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        duplicate = QPushButton("Duplicate")
        duplicate.setIcon(_canvas_icon("duplicate"))
        duplicate.clicked.connect(self.canvas.duplicateSelected)
        delete = QPushButton("Delete")
        delete.setObjectName("dangerAction")
        delete.setIcon(_canvas_icon("delete", "#b91c1c"))
        delete.clicked.connect(self.canvas.deleteSelected)
        buttons.addWidget(duplicate)
        buttons.addWidget(delete)
        layout.addLayout(buttons)
        drop_hint = QLabel("Drag PNG, JPG, WebP or GIF files directly onto the canvas.")
        drop_hint.setWordWrap(True)
        drop_hint.setStyleSheet("color: #64748b")
        layout.addWidget(drop_hint)
        return page

    def _inspector_tab(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 4, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(7)

        general = QGroupBox("Selection")
        form = QFormLayout(general)
        self._type_label = QLabel("No selection")
        self._id_edit = QLineEdit()
        form.addRow("Type", self._type_label)
        form.addRow("Object ID", self._id_edit)
        layout.addWidget(general)

        self._content_group = QGroupBox("Content")
        content_form = QFormLayout(self._content_group)
        self._text_edit = QLineEdit()
        self._data_edit = QLineEdit()
        self._data_edit.setPlaceholderText("Chart values: 20, 40, 60")
        content_form.addRow("Text / title", self._text_edit)
        self._data_label = QLabel("Data")
        content_form.addRow(self._data_label, self._data_edit)
        layout.addWidget(self._content_group)

        self._ports_group = QGroupBox("Node ports")
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
        port_form.addWidget(self._port_id_edit, 0, 0)
        port_form.addWidget(self._port_label_edit, 0, 1)
        port_form.addWidget(self._port_mode_combo, 1, 0)
        port_form.addWidget(self._port_side_combo, 1, 1)
        ports_layout.addLayout(port_form)
        port_actions = QHBoxLayout()
        add_port = QPushButton("Add / update")
        add_port.setIcon(_canvas_icon("check"))
        add_port.clicked.connect(self._upsert_port)
        remove_port = QPushButton("Remove")
        remove_port.setIcon(_canvas_icon("delete"))
        remove_port.clicked.connect(self._remove_port_from_editor)
        port_actions.addWidget(add_port)
        port_actions.addWidget(remove_port)
        ports_layout.addLayout(port_actions)
        layout.addWidget(self._ports_group)

        self._geometry_group = QGroupBox("Geometry")
        geometry_form = QFormLayout(self._geometry_group)
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
        for key, label, minimum, maximum, decimals in fields:
            field = QDoubleSpinBox()
            field.setRange(minimum, maximum)
            field.setDecimals(decimals)
            field.setSingleStep(0.1 if key == "opacity" else 1.0)
            self._number_fields[key] = field
            label_widget = QLabel(label)
            self._number_labels[key] = label_widget
            geometry_form.addRow(label_widget, field)
        layout.addWidget(self._geometry_group)

        self._media_group = QGroupBox("Media")
        media_layout = QVBoxLayout(self._media_group)
        self._source_edit = QLineEdit()
        self._source_edit.setPlaceholderText("Image or animated GIF source")
        media_layout.addWidget(self._source_edit)
        browse = QPushButton("Browse media…")
        browse.setIcon(_canvas_icon("folder"))
        browse.clicked.connect(self._browse_selected_media)
        media_layout.addWidget(browse)
        layout.addWidget(self._media_group)

        self._stroke_group = QGroupBox("Line / signal")
        stroke_form = QFormLayout(self._stroke_group)
        self._route_combo = QComboBox()
        self._route_combo.addItems(("Bezier", "Orthogonal", "Straight", "Polyline"))
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
        self._arrow_start_check = QCheckBox("Start")
        self._arrow_end_check = QCheckBox("End")
        arrow_row = QWidget()
        arrow_layout = QHBoxLayout(arrow_row)
        arrow_layout.setContentsMargins(0, 0, 0, 0)
        arrow_layout.addWidget(self._arrow_start_check)
        arrow_layout.addWidget(self._arrow_end_check)
        self._animated_check = QCheckBox("Animated flow")
        self._flow_speed_field = QDoubleSpinBox()
        self._flow_speed_field.setRange(0.1, 20.0)
        self._flow_speed_field.setDecimals(1)
        self._connector_opacity_field = QDoubleSpinBox()
        self._connector_opacity_field.setRange(0.0, 1.0)
        self._connector_opacity_field.setDecimals(2)
        self._connector_z_field = QDoubleSpinBox()
        self._connector_z_field.setRange(-10000.0, 10000.0)
        self._points_edit = QLineEdit()
        self._points_edit.setPlaceholderText("[[x, y], [x, y]]")
        self._route_label = QLabel("Route")
        self._source_label = QLabel("Source")
        self._target_label = QLabel("Target")
        self._source_port_label = QLabel("Source port")
        self._target_port_label = QLabel("Target port")
        self._animation_label = QLabel("Animation")
        self._flow_speed_label = QLabel("Flow speed")
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
        stroke_form.addRow("Arrowheads", arrow_row)
        stroke_form.addRow(self._animation_label, self._animated_check)
        stroke_form.addRow(self._flow_speed_label, self._flow_speed_field)
        stroke_form.addRow(self._connector_opacity_label, self._connector_opacity_field)
        stroke_form.addRow(self._connector_z_label, self._connector_z_field)
        stroke_form.addRow(self._points_label, self._points_edit)
        layout.addWidget(self._stroke_group)

        self._colors_group = QGroupBox("Appearance")
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

        actions = QHBoxLayout()
        apply_button = QPushButton("Apply changes")
        apply_button.setObjectName("primaryAction")
        apply_button.setIcon(_canvas_icon("check", "#ffffff"))
        apply_button.clicked.connect(self._apply_inspector)
        actions.addWidget(apply_button)
        layout.addLayout(actions)
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
        scroll.setWidget(body)
        page_layout.addWidget(scroll)
        return page

    def _layers_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(7)
        self._layers = QListWidget()
        self._layers.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._layers.itemSelectionChanged.connect(self._select_layers)
        layout.addWidget(self._layers, 1)
        refresh = QPushButton("Refresh item list")
        refresh.setIcon(_canvas_icon("refresh"))
        refresh.clicked.connect(self.refreshLayers)
        layout.addWidget(refresh)
        return page

    def _view_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        navigation = QGroupBox("Viewport")
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
            button = QPushButton(label)
            button.setIcon(_canvas_icon(icon))
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

        grid_group = QGroupBox("Grid")
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

        background = QGroupBox("Canvas background")
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
        session = QGroupBox("Current app session")
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
        persistent = QGroupBox("Persistent across app restarts")
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
        history = QGroupBox("History")
        history_layout = QHBoxLayout(history)
        undo = QPushButton("Undo")
        undo.setIcon(_canvas_icon("undo"))
        undo.clicked.connect(self.canvas.undo)
        redo = QPushButton("Redo")
        redo.setIcon(_canvas_icon("redo"))
        redo.clicked.connect(self.canvas.redo)
        history_layout.addWidget(undo)
        history_layout.addWidget(redo)
        layout.addWidget(history)
        path = QLabel(str(self.canvas.persistentPath()))
        path.setWordWrap(True)
        path.setStyleSheet("color: #64748b")
        layout.addWidget(path)
        layout.addStretch(1)
        return page

    def _choose_media(self, kind: str) -> None:
        pattern = "Animated GIF (*.gif)" if kind == "animated_image" else "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        path, _selected_filter = QFileDialog.getOpenFileName(self, "Add media", "", pattern)
        if path:
            self.canvas.addMedia(path, animated=kind == "animated_image")

    def _choose_color(self, role: str) -> None:
        item = self.canvas.canvasObject(self.canvas.selectedElementId())
        if item is None:
            return
        if isinstance(item, _CanvasConnector):
            current = item.flow_color if role == "flow" else item.color
        else:
            current = item.background if role == "background" else item.text_color if role == "text" else item.color
        chosen = QColorDialog.getColor(current, self, f"Choose {role} color")
        if chosen.isValid():
            if isinstance(item, _CanvasConnector):
                key = "flowColor" if role == "flow" else "color"
                self.canvas.updateConnector(item.connector_id, **{key: chosen})
            else:
                self.canvas.setElementColor(item.element_id, chosen, role)

    def _choose_grid_color(self) -> None:
        chosen = QColorDialog.getColor(self.canvas.gridColor, self, "Choose grid color")
        if chosen.isValid():
            self.canvas.setGridColor(chosen)

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

    def _sync_view_controls(self) -> None:
        widgets = (
            self._grid_visible_check,
            self._grid_style_combo,
            self._background_path,
            self._background_mode_combo,
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
        self._grid_visible_check.setChecked(self.canvas.gridVisible)
        self._grid_style_combo.setCurrentIndex(self.canvas.getGridStyle())
        self._background_path.setText(self.canvas.getBackgroundImage())
        self._background_mode_combo.setCurrentIndex(self.canvas.getBackgroundImageMode())
        del blockers

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

    def _apply_inspector(self) -> None:
        element_id = self.canvas.selectedElementId()
        if not element_id:
            return
        item = self.canvas.canvasObject(element_id)
        if item is None:
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
                flowSpeed=self._flow_speed_field.value(),
                opacity=self._connector_opacity_field.value(),
                z=self._connector_z_field.value(),
                waypoints=points,
            )
        else:
            values = {key: field.value() for key, field in self._number_fields.items()}
            values["text"] = self._text_edit.text()
            if item.kind == "node":
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
                )
                values["points"] = points
            self.canvas.updateElement(element_id, **values)
        self.refreshLayers()

    def _sync_inspector(self, element_id: str) -> None:
        item = self.canvas.canvasObject(element_id)
        widgets = [
            self._id_edit, self._text_edit, self._data_edit, self._source_edit,
            self._ports_list, self._port_id_edit, self._port_label_edit,
            self._port_mode_combo, self._port_side_combo,
            self._source_combo, self._target_combo,
            self._source_port_combo, self._target_port_combo, self._route_combo,
            self._line_style_combo, self._line_width_field,
            self._arrow_start_check, self._arrow_end_check, self._animated_check,
            self._flow_speed_field, self._connector_opacity_field,
            self._connector_z_field, self._points_edit, *self._number_fields.values(),
        ]
        blockers = [QSignalBlocker(widget) for widget in widgets]
        if item is None:
            self._type_label.setText("No selection")
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
        else:
            self._type_label.setText(item.kind)
            self._id_edit.setText(item.element_id)
            connector = isinstance(item, _CanvasConnector)
            media = not connector and item.kind in ("image", "animated_image")
            chart = not connector and item.kind in ("bar_chart", "line_chart")
            line = not connector and item.kind == "line"
            content = not connector and item.kind not in (
                "image", "animated_image", "line",
            )
            self._content_group.setVisible(content)
            self._ports_group.setVisible(not connector and item.kind == "node")
            self._geometry_group.setVisible(not connector)
            self._media_group.setVisible(media)
            self._stroke_group.setVisible(connector or line)
            self._colors_group.show()
            self._color_buttons["background"].setVisible(not connector and not line)
            self._color_buttons["text"].setVisible(content)
            self._color_buttons["flow"].setVisible(connector)
            self._route_combo.setEnabled(connector)
            for widget in (self._source_label, self._source_combo, self._source_port_label,
                           self._source_port_combo, self._target_label, self._target_combo,
                           self._target_port_label, self._target_port_combo,
                           self._route_label, self._route_combo, self._animation_label, self._animated_check,
                           self._flow_speed_label, self._flow_speed_field, self._connector_opacity_label,
                           self._connector_opacity_field, self._connector_z_label, self._connector_z_field):
                widget.setVisible(connector)
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
                routes = ("bezier", "orthogonal", "straight", "polyline")
                styles = ("solid", "dash", "dot", "dashdot")
                self._route_combo.setCurrentIndex(routes.index(item.route) if item.route in routes else 0)
                self._line_style_combo.setCurrentIndex(styles.index(item.line_style) if item.line_style in styles else 0)
                self._line_width_field.setValue(item.line_width)
                self._arrow_start_check.setChecked(item.arrow_start)
                self._arrow_end_check.setChecked(item.arrow_end)
                self._animated_check.setChecked(item.animated)
                self._flow_speed_field.setValue(item.flow_speed)
                self._connector_opacity_field.setValue(item.opacity())
                self._connector_z_field.setValue(item.zValue())
                self._points_edit.setText(json.dumps([[point.x(), point.y()] for point in item.waypoints]))
            else:
                self._text_edit.setText(item.text)
                self._data_edit.setText(", ".join(str(value) for value in item.data) if chart else "")
                self._data_label.setVisible(chart)
                self._data_edit.setVisible(chart)
                self._source_edit.setText(item.source)
                self._set_ports_editor(item.ports if item.kind == "node" else [])
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
                    self._animated_check.setChecked(False)
                    self._points_edit.setText(json.dumps([[point.x(), point.y()] for point in item.points]))
        del blockers

    @staticmethod
    def _parse_points(text: str) -> list[list[float]]:
        if not text.strip():
            return []
        values = json.loads(text)
        if not isinstance(values, list) or any(not isinstance(point, list | tuple) or len(point) != 2 for point in values):
            raise ValueError("Points must use [[x, y], ...] format")
        return [[float(point[0]), float(point[1])] for point in values]

    def _set_ports_editor(self, ports: list[dict[str, Any]]) -> None:
        blocker = QSignalBlocker(self._ports_list)
        self._ports_list.clear()
        for port in ports:
            item = QListWidgetItem(
                f"{port['id']}  ·  {port['mode']}  ·  {port['side']}  ·  {port.get('label', '')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, dict(port))
            self._ports_list.addItem(item)
        del blocker

    def _ports_from_editor(self) -> list[dict[str, Any]]:
        return [
            dict(self._ports_list.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self._ports_list.count())
        ]

    def _load_selected_port(self) -> None:
        selected = self._ports_list.selectedItems()
        if not selected:
            return
        port = dict(selected[0].data(Qt.ItemDataRole.UserRole))
        self._port_id_edit.setText(port["id"])
        self._port_label_edit.setText(port.get("label", ""))
        self._port_mode_combo.setCurrentText(port["mode"].title())
        self._port_side_combo.setCurrentText(port["side"].title())

    def _upsert_port(self) -> None:
        port_id = self._port_id_edit.text().strip()
        if not port_id:
            return
        normalized = _normalize_node_ports([{
            "id": port_id,
            "label": self._port_label_edit.text().strip() or port_id,
            "mode": self._port_mode_combo.currentText().lower(),
            "side": self._port_side_combo.currentText().lower(),
        }])[0]
        ports = self._ports_from_editor()
        for index, port in enumerate(ports):
            if port["id"] == port_id:
                ports[index] = normalized
                break
        else:
            ports.append(normalized)
        self._set_ports_editor(ports)

    def _remove_port_from_editor(self) -> None:
        selected = self._ports_list.selectedItems()
        if selected:
            self._ports_list.takeItem(self._ports_list.row(selected[0]))

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
                    combo.addItem(f"{port['label']}  ·  {port['mode']}", port["id"])
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
        objects = [*self.canvas._elements.values(), *self.canvas._connectors.values()]
        for item in sorted(objects, key=lambda value: value.zValue(), reverse=True):
            description = getattr(item, "text", "")
            label = QListWidgetItem(f"{item.element_id}  ·  {item.kind}  ·  {description}")
            label.setData(Qt.ItemDataRole.UserRole, item.element_id)
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
        self.refreshLayers()

    def _show_save_status(self, target: str) -> None:
        self._save_status.setText(f"Saved: {target}")


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
        save = self._button(
            "", lambda _checked=False: canvas.savePersistent(),
            "Save project workspace", 36, "save",
        )
        save.setObjectName("quickSave")
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
        enabled = len([element_id for element_id in element_ids if element_id in self.canvas._elements]) >= 2
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
        self._connection_origin: tuple[_CanvasElement, dict[str, Any]] | None = None
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

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            current = self.transform().m11()
            target = min(4.0, max(0.2, current * factor))
            if current > 0 and not math.isclose(target, current):
                applied = target / current
                self.scale(applied, applied)
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        point = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton and self.canvas.editMode:
            endpoint = self._port_at(point)
            if endpoint is not None:
                self._connection_origin = endpoint
                start = endpoint[0].portScenePosition(endpoint[1]["id"])
                preview = QPainterPath(start)
                preview.lineTo(start)
                self._connection_preview.setPath(preview)
                self._connection_preview.show()
                self.viewport().setCursor(Qt.CursorShape.CrossCursor)
                self.canvas.diagnosticMessage.emit(
                    f"Connector drag started: {endpoint[0].element_id}.{endpoint[1]['id']}"
                )
                event.accept()
                return
        if event.button() == Qt.MouseButton.RightButton and self.itemAt(point) is None:
            self._right_pan_active = True
            self._right_pan_origin = point
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._connection_origin is not None:
            source, port = self._connection_origin
            start = source.portScenePosition(port["id"])
            end = self.mapToScene(event.position().toPoint())
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
            self._right_pan_active = False
            self._right_pan_origin = None
            self.viewport().unsetCursor()
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

    def _port_at(self, view_position) -> tuple[_CanvasElement, dict[str, Any]] | None:
        item = self.itemAt(view_position)
        if not isinstance(item, _CanvasElement) or item.kind != "node":
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
        if not urls:
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
    diagnosticMessage = pyqtSignal(str)
    itemIdChanged = pyqtSignal(str, str)
    autoSaved = pyqtSignal(str)
    persistentSaved = pyqtSignal(str)
    persistentLoaded = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._background_color = QColor("#f8fafc")
        self._grid_color = QColor("#e2e8f0")
        self._grid_visible = True
        self._snap_to_grid = True
        self._grid_size = 20
        self._grid_style = 0
        self._background_image = ""
        self._background_image_mode = 0
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
        self._history: list[dict[str, Any]] = []
        self._history_index = -1
        self._restoring = False
        self._suppress_next_autosave = False
        self._animations: dict[str, QPropertyAnimation] = {}
        self._elements: dict[str, _CanvasElement] = {}
        self._connectors: dict[str, _CanvasConnector] = {}
        self._scene = _CanvasScene(self)
        self._scene.setSceneRect(-2000, -2000, 4000, 4000)
        self._view = _CanvasView(self, self._scene)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._quick_toolbar = _CanvasQuickToolbar(self)
        self._quick_toolbar.setParent(self._view.viewport())
        self._quick_toolbar.hide()
        layout.addWidget(self._view)
        self._toolbox: _CanvasEditorToolbox | None = None
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
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._push_history(self.toDocument())

    def sizeHint(self) -> QSize:
        return QSize(640, 420)

    def minimumSizeHint(self) -> QSize:
        return QSize(240, 160)

    def scene(self) -> QGraphicsScene:
        return self._scene

    def view(self) -> QGraphicsView:
        return self._view

    def element(self, element_id: str) -> _CanvasElement | None:
        return self._elements.get(str(element_id))

    def canvasObject(self, object_id: str) -> _CanvasElement | _CanvasConnector | None:
        key = str(object_id)
        return self._elements.get(key) or self._connectors.get(key)

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
        return selected

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
        if kind not in _ELEMENT_DEFAULTS:
            raise ValueError(f"Unsupported MonkezCanva element type: {kind}")
        default_width, default_height = _ELEMENT_DEFAULTS[kind]
        element_id = str(element_id or uuid.uuid4().hex[:10])
        if element_id in self._elements or element_id in self._connectors:
            raise ValueError(f"Duplicate MonkezCanva object id: {element_id}")
        item = _CanvasElement(element_id, kind, width or default_width, height or default_height, options)
        center = self._view.mapToScene(self._view.viewport().rect().center())
        item.setPos(center.x() - item._rect.width() / 2 if x is None else x, center.y() - item._rect.height() / 2 if y is None else y)
        item.setEditable(self._edit_mode)
        item.changed.connect(self._element_changed)
        self._scene.addItem(item)
        self._elements[element_id] = item
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

    def nodePorts(self, element_id: str) -> list[dict[str, Any]]:
        item = self._required_element(element_id)
        if item.kind != "node":
            raise TypeError(f"Element {element_id!r} is not a node")
        return [dict(port) for port in item.ports]

    def setNodePorts(self, element_id: str, ports) -> "MonkezCanva":
        item = self._required_element(element_id)
        if item.kind != "node":
            raise TypeError(f"Element {element_id!r} is not a node")
        item.ports = _normalize_node_ports(ports)
        valid_ids = {port["id"] for port in item.ports}
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
    ) -> "MonkezCanva":
        ports = self.nodePorts(element_id)
        port: dict[str, Any] = {"id": port_id, "mode": mode, "label": label or port_id}
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

    def renameElement(self, element_id: str, new_id: str) -> str:
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
        self.itemIdChanged.emit(element_id, requested)
        self.documentChanged.emit()
        return requested

    def updateElement(self, element_id: str, **values) -> "MonkezCanva":
        item = self._required_element(element_id)
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
        if "points" in values:
            item.points = [QPointF(float(point[0]), float(point[1])) for point in values["points"]]
        if "ports" in values:
            self.setNodePorts(element_id, values["ports"])
        item.update()
        item.changed.emit(item.element_id)
        self.documentChanged.emit()
        return self

    def duplicateSelected(self) -> str:
        item = self.canvasObject(self.selectedElementId())
        if item is None:
            return ""
        if isinstance(item, _CanvasConnector):
            values = item.to_dict()
            values.pop("id", None)
            values.pop("type", None)
            source_id = values.pop("source")
            target_id = values.pop("target")
            color = values.pop("color")
            return self.connectElements(source_id, target_id, color, **values)
        values = item.to_dict()
        values.pop("id", None)
        kind = values.pop("type")
        x = values.pop("x") + 30
        y = values.pop("y") + 30
        width = values.pop("width")
        height = values.pop("height")
        return self.addElement(kind, x, y, width, height, **values)

    def bringSelectedToFront(self) -> None:
        item = self.canvasObject(self.selectedElementId())
        if item is not None:
            objects = [*self._elements.values(), *self._connectors.values()]
            item.setZValue(max((entry.zValue() for entry in objects), default=0) + 1)
            self.documentChanged.emit()

    def sendSelectedToBack(self) -> None:
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
        if source.kind == "node" and not source_port:
            source_port = next((port["id"] for port in source.ports if port["mode"] in ("output", "free")), "")
        if target.kind == "node" and not target_port:
            target_port = next((port["id"] for port in target.ports if port["mode"] in ("input", "free")), "")
        self._validate_connection_ports(source, source_port, target, target_port)
        options["sourcePort"] = source_port
        options["targetPort"] = target_port
        connector_id = str(connector_id or uuid.uuid4().hex[:10])
        if connector_id in self._connectors or connector_id in self._elements:
            raise ValueError(f"Duplicate MonkezCanva object id: {connector_id}")
        options.setdefault("color", color)
        connector = _CanvasConnector(self, connector_id, source, target, options)
        connector.changed.connect(self._connector_changed)
        self._scene.addItem(connector)
        self._connectors[connector_id] = connector
        self.connectorAdded.emit(connector_id)
        self.documentChanged.emit()
        return connector_id

    @staticmethod
    def _validate_connection_ports(
        source: _CanvasElement,
        source_port: str,
        target: _CanvasElement,
        target_port: str,
    ) -> None:
        source_config = source.port(source_port) if source_port else None
        target_config = target.port(target_port) if target_port else None
        if source_port and source_config is None:
            raise KeyError(f"Unknown source port {source_port!r} on {source.element_id!r}")
        if target_port and target_config is None:
            raise KeyError(f"Unknown target port {target_port!r} on {target.element_id!r}")
        if source_config and source_config["mode"] == "input":
            raise ValueError("A connector cannot start from an input port")
        if target_config and target_config["mode"] == "output":
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
        if first_port["mode"] == "input" or second_port["mode"] == "output":
            if second_port["mode"] not in ("output", "free") or first_port["mode"] not in ("input", "free"):
                raise ValueError("Ports are incompatible; connect output/free to input/free")
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
        connector = self._required_connector(connector_id)
        source = self._required_element(source_id)
        target = self._required_element(target_id)
        source_port = connector.source_port if source_port is None else str(source_port)
        target_port = connector.target_port if target_port is None else str(target_port)
        if source is not connector.source and source_port and source.port(source_port) is None:
            source_port = ""
        if target is not connector.target and target_port and target.port(target_port) is None:
            target_port = ""
        if source.kind == "node" and not source_port:
            source_port = next((port["id"] for port in source.ports if port["mode"] in ("output", "free")), "")
        if target.kind == "node" and not target_port:
            target_port = next((port["id"] for port in target.ports if port["mode"] in ("input", "free")), "")
        self._validate_connection_ports(source, source_port, target, target_port)
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

    def updateConnector(self, connector_id: str, **values) -> "MonkezCanva":
        connector = self._required_connector(connector_id)
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
            if route not in ("bezier", "orthogonal", "straight", "polyline"):
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
        if "flowSpeed" in values:
            connector.flow_speed = max(0.1, float(values["flowSpeed"]))
        if "waypoints" in values:
            connector.waypoints = [QPointF(float(point[0]), float(point[1])) for point in values["waypoints"]]
        if "opacity" in values:
            connector.setOpacity(max(0.0, min(1.0, float(values["opacity"]))))
        if "z" in values:
            connector.setZValue(float(values["z"]))
        if "metadata" in values:
            connector.metadata = dict(values["metadata"])
        connector.updatePath()
        connector._sync_animation()
        connector.changed.emit(connector.connector_id)
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

    def renameConnector(self, connector_id: str, new_id: str) -> str:
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
        connector = self._connectors.pop(str(connector_id), None)
        if connector is None:
            return False
        connector.release()
        self._scene.removeItem(connector)
        connector.deleteLater()
        self.connectorRemoved.emit(str(connector_id))
        self.documentChanged.emit()
        return True

    def setElementColor(self, element_id: str, color: Any, role: str = "accent") -> "MonkezCanva":
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
        item = self._required_element(element_id)
        item.text = str(text)
        item.update()
        self.documentChanged.emit()
        return self

    def setChartData(self, element_id: str, values) -> "MonkezCanva":
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
        animation = QPropertyAnimation(item, property_name, self)
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
        animation.finished.connect(lambda key=element_id: self._animations.pop(key, None))
        animation.start()
        return animation

    def deleteSelected(self) -> None:
        for item in list(self._scene.selectedItems()):
            if isinstance(item, _CanvasElement):
                self.removeElement(item.element_id)
            elif isinstance(item, _CanvasConnector):
                self.removeConnector(item.connector_id)

    def removeElement(self, element_id: str) -> bool:
        item = self._elements.pop(str(element_id), None)
        if item is None:
            return False
        attached = [key for key, connector in self._connectors.items() if item in (connector.source, connector.target)]
        for key in attached:
            connector = self._connectors.pop(key)
            connector.release()
            self._scene.removeItem(connector)
            connector.deleteLater()
            self.connectorRemoved.emit(key)
        item.releaseMedia()
        self._scene.removeItem(item)
        item.deleteLater()
        self.elementRemoved.emit(str(element_id))
        self.documentChanged.emit()
        return True

    def clear(self) -> None:
        for element_id in list(self._elements):
            self.removeElement(element_id)

    def toDocument(self) -> dict[str, Any]:
        return {
            "format": "monkez-canva",
            "version": 1,
            "scene": {
                "width": self._scene.sceneRect().width(),
                "height": self._scene.sceneRect().height(),
                "gridVisible": self._grid_visible,
                "snapToGrid": self._snap_to_grid,
                "gridSize": self._grid_size,
                "gridStyle": self._grid_style,
                "gridColor": self._grid_color.name(QColor.NameFormat.HexArgb),
                "backgroundColor": self._background_color.name(QColor.NameFormat.HexArgb),
                "backgroundImage": self._background_image,
                "backgroundImageMode": self._background_image_mode,
            },
            "elements": [item.to_dict() for item in self._elements.values()],
            "connectors": [item.to_dict() for item in self._connectors.values()],
        }

    def toJson(self, indent: int | None = 2) -> str:
        return json.dumps(self.toDocument(), ensure_ascii=False, indent=indent)

    def saveDocument(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.toJson(), encoding="utf-8")
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
        if self.persistentPath().is_file() or self.legacyPersistentPath().is_file():
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
        target = self.persistentPath()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.loads(json.dumps(document if document is not None else self.toDocument()))
        assets = target.parent / "assets" / target.stem
        for entry in payload.get("elements", []):
            source_text = str(entry.get("source", ""))
            if entry.get("type") not in ("image", "animated_image") or not source_text:
                continue
            safe_id = "".join(character if character.isalnum() or character in "-_" else "_" for character in str(entry["id"]))
            managed = self._copy_managed_asset(source_text, safe_id, target, assets)
            if managed:
                entry["source"] = managed
        scene = payload.setdefault("scene", {})
        background_image = str(scene.get("backgroundImage", ""))
        if background_image:
            managed = self._copy_managed_asset(background_image, "background", target, assets)
            if managed:
                scene["backgroundImage"] = managed
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.persistentSaved.emit(str(target))
        self.autoSaved.emit(str(target))
        return target

    def loadPersistent(self) -> bool:
        source = self.persistentPath()
        if not source.is_file():
            legacy = self.legacyPersistentPath()
            if legacy.is_file():
                source = legacy
                self.diagnosticMessage.emit(f"Migrating legacy persistent document: {legacy}")
            else:
                self.diagnosticMessage.emit(f"Persistent document not found: {source}")
                return False
        payload = json.loads(source.read_text(encoding="utf-8"))
        for entry in payload.get("elements", []):
            media = str(entry.get("source", ""))
            if media and not Path(media).is_absolute():
                entry["source"] = str((source.parent / Path(media)).resolve())
        scene = payload.get("scene", {})
        background_image = str(scene.get("backgroundImage", ""))
        if background_image and not Path(background_image).is_absolute():
            scene["backgroundImage"] = str((source.parent / Path(background_image)).resolve())
        self._restore_document(payload)
        if source != self.persistentPath():
            self.savePersistent()
        self.persistentLoaded.emit(str(source))
        self.autoSaved.emit(f"loaded {source}")
        return True

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
            shutil.copy2(source, destination)
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
        if self._restoring:
            return
        if self._suppress_next_autosave:
            self._suppress_next_autosave = False
            return
        # Capture history synchronously so Undo never depends on whether the
        # debounced persistence timer happened to fire before the next edit.
        document = json.loads(self.toJson(indent=None))
        self._draft_document = document
        self._push_history(document)
        self._autosave_timer.start(self._auto_save_delay)

    def _flush_autosave(self) -> None:
        if self._restoring:
            return
        document = json.loads(self.toJson(indent=None))
        self._draft_document = document
        self.autoSaved.emit("in-memory draft")
        if self._auto_save_enabled and self._persistent_key:
            self.savePersistent(document)

    def _push_history(self, document: dict[str, Any]) -> None:
        encoded = json.dumps(document, sort_keys=True)
        if self._history and json.dumps(self._history[self._history_index], sort_keys=True) == encoded:
            return
        if self._history_index < len(self._history) - 1:
            self._history = self._history[: self._history_index + 1]
        self._history.append(document)
        self._history = self._history[-80:]
        self._history_index = len(self._history) - 1

    def undo(self) -> bool:
        self._flush_autosave()
        if self._history_index <= 0:
            return False
        self._history_index -= 1
        self._suppress_next_autosave = True
        self._restore_document(self._history[self._history_index])
        self.autoSaved.emit("undo")
        return True

    def redo(self) -> bool:
        if self._history_index >= len(self._history) - 1:
            return False
        self._history_index += 1
        self._suppress_next_autosave = True
        self._restore_document(self._history[self._history_index])
        self.autoSaved.emit("redo")
        return True

    def loadDocument(self, document: dict[str, Any] | str | Path) -> "MonkezCanva":
        if isinstance(document, dict):
            data = document
        else:
            serialized = str(document)
            if serialized.lstrip().startswith("{"):
                data = json.loads(serialized)
            else:
                data = json.loads(Path(serialized).read_text(encoding="utf-8"))
        if data.get("format") != "monkez-canva":
            raise ValueError("Unsupported MonkezCanva document")
        self._restore_document(data)
        self.documentChanged.emit()
        return self

    def _restore_document(self, data: dict[str, Any]) -> None:
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
        self.clear()
        for entry in data.get("elements", []):
            values = dict(entry)
            kind = values.pop("type")
            element_id = values.pop("id")
            x = values.pop("x", 0)
            y = values.pop("y", 0)
            width = values.pop("width", None)
            height = values.pop("height", None)
            self.addElement(kind, x, y, width, height, element_id, **values)
        for entry in data.get("connectors", []):
            values = dict(entry)
            source_id = values.pop("source")
            target_id = values.pop("target")
            connector_id = values.pop("id", None)
            values.pop("type", None)
            color = values.pop("color", "#64748b")
            self.connectElements(source_id, target_id, color, connector_id, **values)
        self._restoring = previous
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        if not previous:
            self.documentChanged.emit()

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

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._fit_pending:
            QTimer.singleShot(0, self._apply_fit_content)

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
        for item in self._elements.values():
            item.setEditable(enabled)
        for connector in self._connectors.values():
            connector.setEditable(enabled)
        if enabled:
            self._place_quick_toolbar()
            self._quick_toolbar.show()
            self._quick_toolbar.raise_()
        else:
            self._quick_toolbar.hide()
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
        viewport = self._view.viewport()
        x = max(10, (viewport.width() - toolbar.width()) // 2)
        toolbar.move(x, 12)

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
        self._grid_visible = visible
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getSnapToGrid(self) -> bool:
        return self._snap_to_grid

    def setSnapToGrid(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._snap_to_grid:
            return
        self._snap_to_grid = enabled
        self.documentChanged.emit()

    def getGridSize(self) -> int:
        return self._grid_size

    def setGridSize(self, size: int) -> None:
        size = max(4, int(size))
        if size == self._grid_size:
            return
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
        self._grid_style = index
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: Any) -> None:
        color = _color(value, "#f8fafc")
        if color == self._background_color:
            return
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
        self._background_image_mode = index
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)
        self.documentChanged.emit()

    def getGridColor(self) -> QColor:
        return QColor(self._grid_color)

    def setGridColor(self, value: Any) -> None:
        color = _color(value, "#e2e8f0")
        if color == self._grid_color:
            return
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

    def _clear_highlight(self, item: _CanvasElement | _CanvasConnector) -> None:
        if item.element_id in self._elements:
            item._highlight = QColor()
            item.update()

    def _element_changed(self, _element_id: str) -> None:
        self.documentChanged.emit()

    def _connector_changed(self, _connector_id: str) -> None:
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
        super().closeEvent(event)
