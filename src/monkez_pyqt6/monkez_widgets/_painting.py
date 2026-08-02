from __future__ import annotations

from PyQt6.QtCore import QRect, QRectF
from PyQt6.QtGui import QPainter


def aligned_stroke_rect(rect: QRect | QRectF, pen_width: float) -> QRectF:
    """Keep an antialiased stroke fully inside *rect* on every edge."""

    inset = max(0.0, float(pen_width)) / 2.0
    return QRectF(rect).adjusted(inset, inset, -inset, -inset)


def aligned_corner_radius(rect: QRect | QRectF, radius: float, pen_width: float = 0.0) -> float:
    """Return the corner radius that belongs to an inset stroke rectangle."""

    inset = max(0.0, float(pen_width)) / 2.0
    bounds = aligned_stroke_rect(rect, pen_width)
    return max(0.0, min(float(radius) - inset, bounds.width() / 2.0, bounds.height() / 2.0))


def aligned_stroke_position(painter: QPainter, position: float, pen_width: float) -> float:
    """Snap a horizontal or vertical stroke center to physical device pixels."""

    device = painter.device()
    scale = float(device.devicePixelRatioF()) if device is not None else 1.0
    scale = max(1.0, scale)
    physical_width = max(1, round(max(0.0, float(pen_width)) * scale))
    physical_position = round(float(position) * scale)
    if physical_width % 2:
        physical_position += 0.5
    return physical_position / scale
