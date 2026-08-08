"""Interactive canvas, chart and flow-diagram editor for Monkez applications."""

from __future__ import annotations

import json
import math
import shutil
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
    QKeySequence,
    QMovie,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
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
        self.source = str(options.get("source", ""))
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

        if self.kind in ("image", "animated_image"):
            self._paint_media(painter, rect)
        elif self.kind == "ellipse":
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
            "opacity": self.opacity(),
            "rotation": self.rotation(),
            "z": self.zValue(),
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
        badge = QLabel("EDIT")
        badge.setObjectName("canvasPaneBadge")
        layout.addWidget(badge)
        layout.addStretch(1)
        close = QToolButton()
        close.setObjectName("canvasPaneClose")
        close.setText("x")
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
        self.setMinimumSize(380, 560)
        self.resize(396, 584)
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
        canvas.selectionChanged.connect(self._sync_inspector)
        canvas.selectionSetChanged.connect(lambda _element_ids: self.refreshLayers())
        canvas.autoSaved.connect(self._show_save_status)
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
        QLabel#canvasPaneBadge {
            color: #1d4ed8; background: #dbeafe; border: none;
            border-radius: 8px; padding: 3px 7px; font-size: 9px; font-weight: 700;
        }
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
        QLineEdit, QDoubleSpinBox, QListWidget {
            color: #0f172a; background: #ffffff; border: 1px solid #d7e0ea;
            border-radius: 7px; padding: 4px 7px; selection-background-color: #bfdbfe;
        }
        QLineEdit:focus, QDoubleSpinBox:focus, QListWidget:focus { border: 1px solid #60a5fa; }
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
            "Shapes": (("Text", "text"), ("Rectangle", "rectangle"), ("Ellipse", "ellipse"), ("Button", "button")),
            "Data": (("Bar chart", "bar_chart"), ("Line chart", "line_chart")),
            "Flow & media": (("Node", "node"), ("Image", "image"), ("Animated GIF", "animated_image")),
        }
        for group_name, entries in groups.items():
            group = QGroupBox(group_name)
            grid = QGridLayout(group)
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(6)
            for index, (label, kind) in enumerate(entries):
                button = QToolButton()
                button.setText(label)
                button.setMinimumSize(100, 34)
                if kind in ("image", "animated_image"):
                    button.clicked.connect(lambda _checked=False, value=kind: self._choose_media(value))
                else:
                    button.clicked.connect(lambda _checked=False, value=kind: self.canvas.addElement(value))
                grid.addWidget(button, index // 2, index % 2)
            layout.addWidget(group)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        duplicate = QPushButton("Duplicate")
        duplicate.clicked.connect(self.canvas.duplicateSelected)
        delete = QPushButton("Delete")
        delete.setObjectName("dangerAction")
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
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(7)
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(6)
        self._type_label = QLabel("No selection")
        self._id_edit = QLineEdit()
        self._text_edit = QLineEdit()
        self._source_edit = QLineEdit()
        form.addRow("Type", self._type_label)
        form.addRow("Item ID", self._id_edit)
        form.addRow("Text / title", self._text_edit)
        form.addRow("Media source", self._source_edit)
        self._number_fields: dict[str, QDoubleSpinBox] = {}
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
            form.addRow(label, field)
        layout.addLayout(form)
        colors = QGridLayout()
        for column, (label, role) in enumerate(
            (("Accent", "accent"), ("Background", "background"), ("Text", "text"))
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, value=role: self._choose_color(value))
            colors.addWidget(button, 0, column)
        layout.addLayout(colors)
        actions = QHBoxLayout()
        browse = QPushButton("Browse media…")
        browse.clicked.connect(self._browse_selected_media)
        apply_button = QPushButton("Apply changes")
        apply_button.setObjectName("primaryAction")
        apply_button.clicked.connect(self._apply_inspector)
        actions.addWidget(browse)
        actions.addWidget(apply_button)
        layout.addLayout(actions)
        order = QHBoxLayout()
        front = QPushButton("Bring front")
        front.clicked.connect(self.canvas.bringSelectedToFront)
        back = QPushButton("Send back")
        back.clicked.connect(self.canvas.sendSelectedToBack)
        order.addWidget(front)
        order.addWidget(back)
        layout.addLayout(order)
        layout.addStretch(1)
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
        refresh.clicked.connect(self.refreshLayers)
        layout.addWidget(refresh)
        return page

    def _view_tab(self) -> QWidget:
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        actions = (
            ("Zoom +", self.canvas.zoomIn, 0, 0), ("Zoom −", self.canvas.zoomOut, 0, 1),
            ("100%", self.canvas.resetZoom, 1, 0), ("Fit all", self.canvas.fitContent, 1, 1),
            ("←", lambda: self.canvas.moveViewport(-120, 0), 2, 0),
            ("→", lambda: self.canvas.moveViewport(120, 0), 2, 1),
            ("↑", lambda: self.canvas.moveViewport(0, -120), 3, 0),
            ("↓", lambda: self.canvas.moveViewport(0, 120), 3, 1),
            ("Center selection", self.canvas.centerOnSelection, 4, 0),
            ("Pan / select", self.canvas.togglePanMode, 4, 1),
        )
        for label, callback, row, column in actions:
            button = QPushButton(label)
            button.clicked.connect(callback)
            layout.addWidget(button, row, column)
        layout.setRowStretch(5, 1)
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
        save_session.clicked.connect(self.canvas.saveSession)
        restore_session = QPushButton("Restore session checkpoint")
        restore_session.clicked.connect(self.canvas.restoreSession)
        session_layout.addWidget(save_session)
        session_layout.addWidget(restore_session)
        layout.addWidget(session)
        persistent = QGroupBox("Persistent across app restarts")
        persistent_layout = QVBoxLayout(persistent)
        save_persistent = QPushButton("Save persistent now")
        save_persistent.setObjectName("primaryAction")
        save_persistent.clicked.connect(lambda: self.canvas.savePersistent())
        load_persistent = QPushButton("Load persistent data")
        load_persistent.clicked.connect(self.canvas.loadPersistent)
        persistent_layout.addWidget(save_persistent)
        persistent_layout.addWidget(load_persistent)
        layout.addWidget(persistent)
        history = QGroupBox("History")
        history_layout = QHBoxLayout(history)
        undo = QPushButton("Undo")
        undo.clicked.connect(self.canvas.undo)
        redo = QPushButton("Redo")
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
        item = self.canvas.element(self.canvas.selectedElementId())
        if item is None:
            return
        current = item.background if role == "background" else item.text_color if role == "text" else item.color
        chosen = QColorDialog.getColor(current, self, f"Choose {role} color")
        if chosen.isValid():
            self.canvas.setElementColor(item.element_id, chosen, role)

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
        requested_id = self._id_edit.text().strip()
        if requested_id and requested_id != element_id:
            element_id = self.canvas.renameElement(element_id, requested_id)
        values = {key: field.value() for key, field in self._number_fields.items()}
        values.update(text=self._text_edit.text(), source=self._source_edit.text())
        self.canvas.updateElement(element_id, **values)
        self.refreshLayers()

    def _sync_inspector(self, element_id: str) -> None:
        item = self.canvas.element(element_id)
        widgets = [self._id_edit, self._text_edit, self._source_edit, *self._number_fields.values()]
        blockers = [QSignalBlocker(widget) for widget in widgets]
        if item is None:
            self._type_label.setText("No selection")
            self._id_edit.clear()
            self._text_edit.clear()
            self._source_edit.clear()
        else:
            self._type_label.setText(item.kind)
            self._id_edit.setText(item.element_id)
            self._text_edit.setText(item.text)
            self._source_edit.setText(item.source)
            values = {
                "x": item.pos().x(), "y": item.pos().y(),
                "width": item._rect.width(), "height": item._rect.height(),
                "rotation": item.rotation(), "opacity": item.opacity(), "z": item.zValue(),
            }
            for key, value in values.items():
                self._number_fields[key].setValue(value)
        del blockers

    def refreshLayers(self) -> None:
        if self._syncing_layers:
            return
        selected = set(self.canvas.selectedElementIds())
        blocker = QSignalBlocker(self._layers)
        self._layers.clear()
        for item in sorted(self.canvas._elements.values(), key=lambda value: value.zValue(), reverse=True):
            label = QListWidgetItem(f"{item.element_id}  ·  {item.kind}  ·  {item.text}")
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
            "Save", lambda _checked=False: canvas.savePersistent(),
            "Save persistent data now", 54,
        )
        save.setObjectName("quickSave")
        self._separator(layout)
        self._button("-", canvas.zoomOut, "Zoom out", 28)
        self._button("100", canvas.resetZoom, "Reset zoom to 100%", 42)
        self._button("+", canvas.zoomIn, "Zoom in", 28)
        self._button("Fit", canvas.fitContent, "Fit all items", 38)
        self._separator(layout)
        self._align_buttons: list[QToolButton] = []
        for label, alignment, width in (
            ("Left", "left", 42), ("H-C", "hcenter", 38), ("Right", "right", 46),
            ("Top", "top", 38), ("V-C", "vcenter", 38), ("Bottom", "bottom", 56),
            ("Center", "center", 52),
        ):
            button = self._button(
                label,
                lambda _checked=False, value=alignment: canvas.alignSelected(value),
                width=width,
            )
            button.setToolTip(f"Align selected items: {alignment}")
            self._align_buttons.append(button)
        canvas.selectionSetChanged.connect(self._update_alignment_state)
        self._update_alignment_state(canvas.selectedElementIds())

    def _button(self, label: str, callback, tooltip: str = "", width: int | None = None) -> QToolButton:
        button = QToolButton(self)
        button.setText(label)
        button.setToolTip(tooltip or label)
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
        enabled = len(element_ids) >= 2
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
        if event.button() == Qt.MouseButton.RightButton and self.itemAt(point) is None:
            self._right_pan_active = True
            self._right_pan_origin = point
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
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
    elementClicked = pyqtSignal(str)
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
        self._edit_mode = False
        self._shortcut_enabled = True
        self._fit_pending = False
        self._pan_mode = False
        self._persistent_key = ""
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

    def elements(self) -> list[str]:
        return list(self._elements)

    def selectedElementId(self) -> str:
        selected = self.selectedElementIds()
        return selected[0] if selected else ""

    def selectedElementIds(self) -> list[str]:
        return [
            element_id
            for element_id, item in self._elements.items()
            if item.isSelected()
        ]

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
        item = self._elements.get(str(element_id))
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
            item = self._elements.get(element_id)
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
        if requested != element_id and requested in self._elements:
            raise ValueError(f"Duplicate MonkezCanva element id: {requested}")
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
        item.update()
        item.changed.emit(item.element_id)
        self.documentChanged.emit()
        return self

    def duplicateSelected(self) -> str:
        item = self.element(self.selectedElementId())
        if item is None:
            return ""
        values = item.to_dict()
        values.pop("id", None)
        kind = values.pop("type")
        x = values.pop("x") + 30
        y = values.pop("y") + 30
        width = values.pop("width")
        height = values.pop("height")
        return self.addElement(kind, x, y, width, height, **values)

    def bringSelectedToFront(self) -> None:
        item = self.element(self.selectedElementId())
        if item is not None:
            item.setZValue(max((entry.zValue() for entry in self._elements.values()), default=0) + 1)
            self.documentChanged.emit()

    def sendSelectedToBack(self) -> None:
        item = self.element(self.selectedElementId())
        if item is not None:
            item.setZValue(min((entry.zValue() for entry in self._elements.values()), default=0) - 1)
            self.documentChanged.emit()

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
            "scene": {"width": self._scene.sceneRect().width(), "height": self._scene.sceneRect().height()},
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
        root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        key = self._persistent_key or self.objectName() or "monkez_canva"
        safe_key = "".join(character if character.isalnum() or character in "-_." else "_" for character in key)
        return root / "monkez_canva" / f"{safe_key}.json"

    def setPersistenceKey(self, key: str) -> "MonkezCanva":
        self._persistent_key = str(key).strip()
        return self

    def getPersistenceKey(self) -> str:
        return self._persistent_key

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
            source = Path(source_text)
            if not source.is_file():
                continue
            safe_id = "".join(character if character.isalnum() or character in "-_" else "_" for character in str(entry["id"]))
            destination = assets / f"{safe_id}-{source.name}"
            assets.mkdir(parents=True, exist_ok=True)
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
            entry["source"] = str(destination)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.persistentSaved.emit(str(target))
        self.autoSaved.emit(str(target))
        return target

    def loadPersistent(self) -> bool:
        source = self.persistentPath()
        if not source.is_file():
            self.diagnosticMessage.emit(f"Persistent document not found: {source}")
            return False
        self._restore_document(json.loads(source.read_text(encoding="utf-8")))
        self.persistentLoaded.emit(str(source))
        self.autoSaved.emit(f"loaded {source}")
        return True

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
        self._restoring = previous
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
        item = self.element(self.selectedElementId())
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
        element_ids = self.selectedElementIds()
        self.selectionChanged.emit(element_ids[0] if element_ids else "")
        self.selectionSetChanged.emit(element_ids)

    editMode = pyqtProperty(bool, getEditMode, setEditMode)
    editorShortcutEnabled = pyqtProperty(bool, getShortcutEnabled, setShortcutEnabled)
    gridVisible = pyqtProperty(bool, getGridVisible, setGridVisible)
    snapToGrid = pyqtProperty(bool, getSnapToGrid, setSnapToGrid)
    gridSize = pyqtProperty(int, getGridSize, setGridSize)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    gridColor = pyqtProperty(QColor, getGridColor, setGridColor)
    persistenceKey = pyqtProperty(str, getPersistenceKey, setPersistenceKey)
    autoSaveEnabled = pyqtProperty(bool, getAutoSaveEnabled, setAutoSaveEnabled)
    autoSaveDelay = pyqtProperty(int, getAutoSaveDelay, setAutoSaveDelay)

    def closeEvent(self, event) -> None:
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()
            self._flush_autosave()
        if self._toolbox is not None:
            self._toolbox.close()
        super().closeEvent(event)
