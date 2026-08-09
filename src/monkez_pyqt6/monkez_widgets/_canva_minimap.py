"""Floating scene overview used by MonkezCanva edit mode."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class CanvasMinimap(QWidget):
    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self.canvas = canvas
        self.setObjectName("canvasMinimap")
        self.setFixedSize(184, 122)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Canvas overview · click or drag to navigate")
        self._dragging = False

    def _content_bounds(self) -> QRectF:
        items = [
            *self.canvas._elements.values(),
            *self.canvas._connectors.values(),
            *self.canvas._groups.values(),
        ]
        bounds = QRectF()
        for item in items:
            item_bounds = item.sceneBoundingRect()
            bounds = item_bounds if bounds.isNull() else bounds.united(item_bounds)
        return bounds.adjusted(-80, -80, 80, 80) if not bounds.isNull() else self.canvas._scene.sceneRect()

    def _drawing_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(10, 10, -10, -10)

    def _map_scene_rect(self, scene_rect: QRectF, bounds: QRectF) -> QRectF:
        target = self._drawing_rect()
        scale = min(target.width() / max(1.0, bounds.width()), target.height() / max(1.0, bounds.height()))
        width, height = bounds.width() * scale, bounds.height() * scale
        origin = QPointF(target.center().x() - width / 2, target.center().y() - height / 2)
        return QRectF(
            origin.x() + (scene_rect.x() - bounds.x()) * scale,
            origin.y() + (scene_rect.y() - bounds.y()) * scale,
            scene_rect.width() * scale,
            scene_rect.height() * scale,
        )

    def _scene_point(self, point: QPointF) -> QPointF:
        bounds = self._content_bounds()
        target = self._drawing_rect()
        scale = min(target.width() / max(1.0, bounds.width()), target.height() / max(1.0, bounds.height()))
        width, height = bounds.width() * scale, bounds.height() * scale
        origin = QPointF(target.center().x() - width / 2, target.center().y() - height / 2)
        return QPointF(
            bounds.x() + (point.x() - origin.x()) / max(scale, 0.0001),
            bounds.y() + (point.y() - origin.y()) / max(scale, 0.0001),
        )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#d8d4cf"), 1))
        painter.setBrush(QColor(255, 254, 252, 242))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        bounds = self._content_bounds()
        for connector in self.canvas._connectors.values():
            if connector.isVisible():
                painter.setPen(QPen(QColor("#b3bac5"), 1))
                painter.drawLine(
                    self._map_scene_rect(QRectF(connector.source.sceneBoundingRect().center(), connector.source.sceneBoundingRect().center()), bounds).center(),
                    self._map_scene_rect(QRectF(connector.target.sceneBoundingRect().center(), connector.target.sceneBoundingRect().center()), bounds).center(),
                )
        painter.setPen(Qt.PenStyle.NoPen)
        for group in self.canvas._groups.values():
            if group.isVisible():
                painter.setPen(QPen(QColor(group.color), 1))
                painter.setBrush(QColor(100, 116, 139, 18))
                painter.drawRoundedRect(
                    self._map_scene_rect(group.sceneBoundingRect(), bounds), 2, 2
                )
        painter.setPen(Qt.PenStyle.NoPen)
        for item in self.canvas._elements.values():
            if item.isVisible():
                painter.setBrush(QColor(item.color).lighter(125))
                painter.drawRoundedRect(self._map_scene_rect(item.sceneBoundingRect(), bounds), 2, 2)
        viewport = self.canvas._view.mapToScene(self.canvas._view.viewport().rect()).boundingRect()
        painter.setPen(QPen(QColor("#ef6a5b"), 1.5))
        painter.setBrush(QColor(239, 106, 91, 24))
        painter.drawRoundedRect(self._map_scene_rect(viewport, bounds), 3, 3)

    def _navigate(self, position) -> None:
        self.canvas._view.centerOn(self._scene_point(QPointF(position)))
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._navigate(event.position())
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self._navigate(event.position())
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
