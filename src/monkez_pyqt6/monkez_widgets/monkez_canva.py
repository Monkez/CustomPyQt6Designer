"""Interactive canvas, chart and flow-diagram editor for Monkez applications."""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path
from typing import Any

from PyQt6.QtCore import (
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
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFrame,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
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
}


def _color(value: Any, fallback: str = "#2563eb") -> QColor:
    result = QColor(value)
    return result if result.isValid() else QColor(fallback)


class _CanvasScene(QGraphicsScene):
    def __init__(self, canvas: "MonkezCanva") -> None:
        super().__init__(canvas)
        self.canvas = canvas

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, self.canvas.backgroundColor)
        if not self.canvas.gridVisible:
            return
        size = self.canvas.gridSize
        left = math.floor(rect.left() / size) * size
        top = math.floor(rect.top() / size) * size
        minor = QColor(self.canvas.gridColor)
        painter.setPen(QPen(minor, 0))
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
        self._highlight = QColor()
        self._resizing = False
        self._resize_origin = QPointF()
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return self._rect.adjusted(-5, -5, 5, 5)

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

        if self.kind == "ellipse":
            painter.drawEllipse(rect)
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
            painter.setBrush(self.color)
            painter.setPen(QPen(self.background, 2))
            painter.drawEllipse(QPointF(rect.left(), rect.center().y() + 14), 6, 6)
            painter.drawEllipse(QPointF(rect.right(), rect.center().y() + 14), 6, 6)
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
        }


class _CanvasConnector(QGraphicsPathItem):
    def __init__(self, connector_id: str, source: _CanvasElement, target: _CanvasElement, color: Any) -> None:
        super().__init__()
        self.connector_id = connector_id
        self.source = source
        self.target = target
        self.color = _color(color, "#64748b")
        self.setZValue(-1)
        self.setPen(QPen(self.color, 2.2))
        source.changed.connect(self.updatePath)
        target.changed.connect(self.updatePath)
        self.updatePath()

    def updatePath(self, *_args) -> None:
        start = self.source.mapToScene(self.source._rect.center())
        end = self.target.mapToScene(self.target._rect.center())
        delta = max(50.0, abs(end.x() - start.x()) * 0.5)
        path = QPainterPath(start)
        path.cubicTo(QPointF(start.x() + delta, start.y()), QPointF(end.x() - delta, end.y()), end)
        self.setPath(path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.connector_id,
            "source": self.source.element_id,
            "target": self.target.element_id,
            "color": self.color.name(QColor.NameFormat.HexArgb),
        }


class _CanvasToolbox(QDialog):
    def __init__(self, canvas: "MonkezCanva") -> None:
        super().__init__(canvas.window())
        self.canvas = canvas
        self.setWindowTitle("MonkezCanva Elements")
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(260)
        root = QVBoxLayout(self)
        title = QLabel("ELEMENTS")
        title.setStyleSheet("font-weight: 700; color: #64748b; padding: 4px")
        root.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        groups = {
            "Basics": (("Text", "text"), ("Rectangle", "rectangle"), ("Ellipse", "ellipse"), ("Button", "button")),
            "Charts": (("Bar chart", "bar_chart"), ("Line chart", "line_chart")),
            "Flow diagram": (("Node", "node"),),
        }
        for group_name, entries in groups.items():
            group = QGroupBox(group_name)
            grid = QGridLayout(group)
            for index, (label, kind) in enumerate(entries):
                button = QToolButton()
                button.setText(label)
                button.setMinimumSize(98, 42)
                button.clicked.connect(lambda _checked=False, value=kind: canvas.addElement(value))
                grid.addWidget(button, index // 2, index % 2)
            content_layout.addWidget(group)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        color_button = QPushButton("Color")
        color_button.clicked.connect(self._choose_color)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(canvas.deleteSelected)
        actions.addWidget(color_button)
        actions.addWidget(delete_button)
        root.addLayout(actions)
        hint = QLabel("Ctrl+D, E: close edit mode\nDel: delete · Ctrl+wheel: zoom")
        hint.setStyleSheet("color: #64748b; padding: 4px")
        root.addWidget(hint)

    def _choose_color(self) -> None:
        element_id = self.canvas.selectedElementId()
        if not element_id:
            return
        current = self.canvas.element(element_id).color
        chosen = QColorDialog.getColor(current, self, "Element color")
        if chosen.isValid():
            self.canvas.setElementColor(element_id, chosen)


class _CanvasView(QGraphicsView):
    def __init__(self, canvas: "MonkezCanva", scene: QGraphicsScene) -> None:
        super().__init__(scene, canvas)
        self.canvas = canvas
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            current = self.transform().m11()
            if 0.2 <= current * factor <= 4.0:
                self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, _CanvasElement):
            self.canvas.elementClicked.emit(item.element_id)


class MonkezCanva(QWidget):
    """Canvas editor with runtime edit mode and a code-friendly element API.

    The name intentionally follows the requested product spelling ``Canva``.
    Press ``Ctrl+D`` followed by ``E`` while its window is active to toggle the
    editing toolbox.
    """

    editModeChanged = pyqtSignal(bool)
    elementAdded = pyqtSignal(str)
    elementRemoved = pyqtSignal(str)
    elementClicked = pyqtSignal(str)
    selectionChanged = pyqtSignal(str)
    documentChanged = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._background_color = QColor("#f8fafc")
        self._grid_color = QColor("#e2e8f0")
        self._grid_visible = True
        self._snap_to_grid = True
        self._grid_size = 20
        self._edit_mode = False
        self._shortcut_enabled = True
        self._animations: dict[str, QPropertyAnimation] = {}
        self._elements: dict[str, _CanvasElement] = {}
        self._connectors: dict[str, _CanvasConnector] = {}
        self._scene = _CanvasScene(self)
        self._scene.setSceneRect(-2000, -2000, 4000, 4000)
        self._view = _CanvasView(self, self._scene)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self._toolbox: _CanvasToolbox | None = None
        self._scene.selectionChanged.connect(self._emit_selection)
        self._toggle_shortcut = QShortcut(QKeySequence("Ctrl+D, E"), self)
        self._toggle_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._toggle_shortcut.activated.connect(self.toggleEditMode)
        delete_shortcut = QShortcut(QKeySequence.StandardKey.Delete, self)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        delete_shortcut.activated.connect(self.deleteSelected)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

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

    def elements(self) -> list[str]:
        return list(self._elements)

    def selectedElementId(self) -> str:
        selected = self._scene.selectedItems()
        return selected[0].element_id if selected and isinstance(selected[0], _CanvasElement) else ""

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
        if kind not in _ELEMENT_DEFAULTS:
            raise ValueError(f"Unsupported MonkezCanva element type: {kind}")
        default_width, default_height = _ELEMENT_DEFAULTS[kind]
        element_id = str(element_id or uuid.uuid4().hex[:10])
        if element_id in self._elements:
            raise ValueError(f"Duplicate MonkezCanva element id: {element_id}")
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

    def addChart(self, values, chart_type: str = "bar", x: float = 0, y: float = 0, **options) -> str:
        kind = "line_chart" if str(chart_type).lower() == "line" else "bar_chart"
        return self.addElement(kind, x, y, data=list(values), **options)

    def connectElements(self, source_id: str, target_id: str, color: Any = "#64748b", connector_id: str | None = None) -> str:
        source = self._elements.get(str(source_id))
        target = self._elements.get(str(target_id))
        if source is None or target is None:
            raise KeyError("Both connector endpoints must exist")
        connector_id = str(connector_id or uuid.uuid4().hex[:10])
        connector = _CanvasConnector(connector_id, source, target, color)
        self._scene.addItem(connector)
        self._connectors[connector_id] = connector
        self.documentChanged.emit()
        return connector_id

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

    def removeElement(self, element_id: str) -> bool:
        item = self._elements.pop(str(element_id), None)
        if item is None:
            return False
        attached = [key for key, connector in self._connectors.items() if item in (connector.source, connector.target)]
        for key in attached:
            connector = self._connectors.pop(key)
            self._scene.removeItem(connector)
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
            "scene": {"width": self._scene.sceneRect().width(), "height": self._scene.sceneRect().height()},
            "elements": [item.to_dict() for item in self._elements.values()],
            "connectors": [item.to_dict() for item in self._connectors.values()],
        }

    def toJson(self, indent: int | None = 2) -> str:
        return json.dumps(self.toDocument(), ensure_ascii=False, indent=indent)

    def saveDocument(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(self.toJson(), encoding="utf-8")
        return target

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
            self.connectElements(entry["source"], entry["target"], entry.get("color", "#64748b"), entry.get("id"))
        self.documentChanged.emit()
        return self

    def fitContent(self) -> None:
        bounds = self._scene.itemsBoundingRect()
        if not bounds.isEmpty():
            self._view.fitInView(bounds.adjusted(-30, -30, 30, 30), Qt.AspectRatioMode.KeepAspectRatio)

    def toggleEditMode(self) -> None:
        self.setEditMode(not self._edit_mode)

    def getEditMode(self) -> bool:
        return self._edit_mode

    def setEditMode(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._edit_mode:
            return
        self._edit_mode = enabled
        for item in self._elements.values():
            item.setEditable(enabled)
        self._view.setDragMode(QGraphicsView.DragMode.RubberBandDrag if enabled else QGraphicsView.DragMode.ScrollHandDrag)
        if enabled:
            if self._toolbox is None:
                self._toolbox = _CanvasToolbox(self)
            self._toolbox.setParent(self.window(), self._toolbox.windowFlags())
            self._toolbox.show()
            self._toolbox.raise_()
        elif self._toolbox is not None:
            self._toolbox.hide()
        self.editModeChanged.emit(enabled)

    def getShortcutEnabled(self) -> bool:
        return self._shortcut_enabled

    def setShortcutEnabled(self, enabled: bool) -> None:
        self._shortcut_enabled = bool(enabled)
        self._toggle_shortcut.setEnabled(self._shortcut_enabled)

    def getGridVisible(self) -> bool:
        return self._grid_visible

    def setGridVisible(self, visible: bool) -> None:
        self._grid_visible = bool(visible)
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)

    def getSnapToGrid(self) -> bool:
        return self._snap_to_grid

    def setSnapToGrid(self, enabled: bool) -> None:
        self._snap_to_grid = bool(enabled)

    def getGridSize(self) -> int:
        return self._grid_size

    def setGridSize(self, size: int) -> None:
        self._grid_size = max(4, int(size))
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: Any) -> None:
        self._background_color = _color(value, "#f8fafc")
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)

    def getGridColor(self) -> QColor:
        return QColor(self._grid_color)

    def setGridColor(self, value: Any) -> None:
        self._grid_color = _color(value, "#e2e8f0")
        self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.SceneLayer.BackgroundLayer)

    def _required_element(self, element_id: str) -> _CanvasElement:
        item = self._elements.get(str(element_id))
        if item is None:
            raise KeyError(f"Unknown MonkezCanva element: {element_id}")
        return item

    def _clear_highlight(self, item: _CanvasElement) -> None:
        if item.element_id in self._elements:
            item._highlight = QColor()
            item.update()

    def _element_changed(self, _element_id: str) -> None:
        self.documentChanged.emit()

    def _emit_selection(self) -> None:
        self.selectionChanged.emit(self.selectedElementId())

    editMode = pyqtProperty(bool, getEditMode, setEditMode)
    editorShortcutEnabled = pyqtProperty(bool, getShortcutEnabled, setShortcutEnabled)
    gridVisible = pyqtProperty(bool, getGridVisible, setGridVisible)
    snapToGrid = pyqtProperty(bool, getSnapToGrid, setSnapToGrid)
    gridSize = pyqtProperty(int, getGridSize, setGridSize)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    gridColor = pyqtProperty(QColor, getGridColor, setGridColor)

    def closeEvent(self, event) -> None:
        if self._toolbox is not None:
            self._toolbox.close()
        super().closeEvent(event)
