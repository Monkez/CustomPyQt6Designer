"""Native Qt painters for the opt-in MonkezCanva component packs."""

from __future__ import annotations

import math
from typing import Any, Iterable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF


_PALETTE = (
    QColor("#ff685b"),
    QColor("#0f9f8f"),
    QColor("#5b7cfa"),
    QColor("#f2aa3b"),
    QColor("#8b5cf6"),
    QColor("#30a7d7"),
)


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    return result if math.isfinite(result) else fallback


def _numbers(values: Iterable[Any]) -> list[float]:
    return [_number(value) for value in values if isinstance(value, (int, float))]


def _ratio(item) -> float:
    values = item.custom_properties
    minimum = _number(values.get("minimum"), 0.0)
    maximum = _number(values.get("maximum"), 100.0)
    value = _number(values.get("value"), minimum)
    return max(0.0, min(1.0, (value - minimum) / max(1e-9, maximum - minimum)))


def _card(painter, item, rect: QRectF, radius: float = 12.0) -> None:
    painter.setPen(QPen(QColor(item.color), 1.5))
    painter.setBrush(QColor(item.background))
    painter.drawRoundedRect(rect, radius, radius)


def _title(painter, item, rect: QRectF, *, center: bool = False) -> None:
    font = QFont(painter.font())
    font.setPointSizeF(9.0)
    font.setWeight(QFont.Weight.DemiBold)
    painter.setFont(font)
    painter.setPen(QColor(item.text_color))
    alignment = Qt.AlignmentFlag.AlignCenter if center else (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    painter.drawText(rect, alignment, item.text)


def _selection(painter, item, rect: QRectF) -> None:
    if not item.isSelected():
        return
    painter.setPen(QPen(QColor("#2563eb"), 1.4, Qt.PenStyle.DashLine))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 10, 10)
    painter.setBrush(QColor("#ffffff"))
    for point in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
        painter.drawRect(QRectF(point.x() - 3.5, point.y() - 3.5, 7, 7))


def _line_chart(painter, rect: QRectF, values: list[float], color: QColor, *, area: bool = False) -> None:
    if not values:
        return
    low, high = min(values), max(values)
    span = max(1e-9, high - low)
    points = [
        QPointF(
            rect.left() + rect.width() * index / max(1, len(values) - 1),
            rect.bottom() - rect.height() * (value - low) / span,
        )
        for index, value in enumerate(values)
    ]
    path = QPainterPath(points[0])
    for point in points[1:]:
        path.lineTo(point)
    if area:
        fill = QPainterPath(path)
        fill.lineTo(rect.bottomRight())
        fill.lineTo(rect.bottomLeft())
        fill.closeSubpath()
        shade = QColor(color)
        shade.setAlpha(48)
        painter.fillPath(fill, shade)
    painter.setPen(QPen(color, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def _dashboard(painter, item, rect: QRectF, visual: str) -> None:
    values = item.custom_properties
    color = QColor(item.color)
    data = list(item.data)
    _card(painter, item, rect)
    if visual == "kpi":
        _title(painter, item, rect.adjusted(14, 8, -14, -rect.height() + 30))
        font = QFont(painter.font())
        font.setPointSizeF(21)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(item.text_color))
        value = values.get("value", 0)
        unit = str(values.get("unit", ""))
        painter.drawText(
            rect.adjusted(14, 29, -14, -25),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{value:g}{unit}" if isinstance(value, (int, float)) else f"{value}{unit}",
        )
        trend = _number(values.get("trend"))
        painter.setPen(QColor("#0f9f8f") if trend >= 0 else QColor("#dc2626"))
        painter.drawText(
            rect.adjusted(14, rect.height() - 27, -14, -7),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{'↗' if trend >= 0 else '↘'} {abs(trend):g}%  {values.get('subtitle', '')}",
        )
        return
    if visual in ("sparkline", "area"):
        _title(painter, item, rect.adjusted(12, 5, -12, -rect.height() + 28))
        _line_chart(
            painter,
            rect.adjusted(12, 34, -12, -12),
            _numbers(data),
            color,
            area=visual == "area" or bool(values.get("showArea")),
        )
        return
    if visual in ("gauge", "progress_ring"):
        ratio = _ratio(item)
        center = QPointF(rect.center().x(), rect.center().y() + (9 if visual == "gauge" else 2))
        diameter = min(rect.width(), rect.height()) - 38
        ring = QRectF(center.x() - diameter / 2, center.y() - diameter / 2, diameter, diameter)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#e7e9ee"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if visual == "gauge":
            painter.drawArc(ring, 210 * 16, -240 * 16)
            painter.setPen(QPen(color, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(ring, 210 * 16, int(-240 * ratio * 16))
        else:
            painter.drawEllipse(ring)
            painter.setPen(QPen(color, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(ring, 90 * 16, int(-360 * ratio * 16))
        _title(painter, item, rect.adjusted(10, 6, -10, -rect.height() + 25), center=True)
        painter.setPen(QColor(item.text_color))
        font = QFont(painter.font())
        font.setPointSizeF(15)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(center.x() - 55, center.y() - 14, 110, 28),
            Qt.AlignmentFlag.AlignCenter,
            f"{_number(values.get('value')):g}{values.get('unit', '')}",
        )
        return
    if visual in ("pie", "donut"):
        _title(painter, item, rect.adjusted(10, 5, -10, -rect.height() + 25), center=True)
        numbers = [max(0.0, value) for value in _numbers(data)]
        total = sum(numbers) or 1.0
        pie = QRectF(rect.center().x() - 48, rect.center().y() - 42, 96, 96)
        start = 90 * 16
        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        for index, value in enumerate(numbers):
            span = int(-360 * 16 * value / total)
            painter.setBrush(_PALETTE[index % len(_PALETTE)])
            painter.drawPie(pie, start, span)
            start += span
        if visual == "donut":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(item.background))
            painter.drawEllipse(pie.adjusted(25, 25, -25, -25))
        return
    plot = rect.adjusted(18, 34, -16, -18)
    _title(painter, item, rect.adjusted(12, 5, -12, -rect.height() + 25))
    if visual == "scatter":
        pairs = [value for value in data if isinstance(value, (list, tuple)) and len(value) >= 2]
        xs = [_number(pair[0]) for pair in pairs] or [0]
        ys = [_number(pair[1]) for pair in pairs] or [0]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        painter.setPen(QPen(QColor("#d7dbe3"), 1))
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        painter.drawLine(plot.bottomLeft(), plot.topLeft())
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(color)
        for x, y in zip(xs, ys):
            point = QPointF(
                plot.left() + plot.width() * (x - x0) / max(1e-9, x1 - x0),
                plot.bottom() - plot.height() * (y - y0) / max(1e-9, y1 - y0),
            )
            painter.drawEllipse(point, 4.5, 4.5)
    elif visual == "histogram":
        numbers = _numbers(data)
        maximum = max(numbers, default=1) or 1
        slot = plot.width() / max(1, len(numbers))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for index, value in enumerate(numbers):
            height = plot.height() * max(0, value) / maximum
            painter.drawRoundedRect(
                QRectF(plot.left() + index * slot + 2, plot.bottom() - height, max(2, slot - 4), height), 2, 2
            )
    elif visual == "heatmap":
        numbers = _numbers(data)
        columns = max(1, int(_number(values.get("columns"), 4)))
        rows = max(1, math.ceil(len(numbers) / columns))
        maximum = max(numbers, default=1) or 1
        for index, value in enumerate(numbers):
            shade = QColor(color)
            shade.setAlpha(35 + int(220 * max(0, value) / maximum))
            cell = QRectF(
                plot.left() + (index % columns) * plot.width() / columns,
                plot.top() + (index // columns) * plot.height() / rows,
                plot.width() / columns - 2,
                plot.height() / rows - 2,
            )
            painter.fillRect(cell, shade)
    elif visual == "timeline":
        entries = [str(value) for value in data][:5]
        x = plot.left() + 9
        painter.setPen(QPen(color, 2))
        painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        for index, entry in enumerate(entries):
            y = plot.top() + (index + 0.5) * plot.height() / max(1, len(entries))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), 4, 4)
            painter.setPen(QColor(item.text_color))
            painter.drawText(QRectF(x + 12, y - 9, plot.width() - 20, 18), Qt.AlignmentFlag.AlignVCenter, entry)
            painter.setPen(QPen(color, 2))
    elif visual == "event_log":
        for index, entry in enumerate([str(value) for value in data][:6]):
            y = plot.top() + index * 19
            painter.setPen(QColor("#8792a5"))
            painter.drawText(QRectF(plot.left(), y, plot.width(), 18), Qt.AlignmentFlag.AlignVCenter, entry)
    elif visual == "data_table":
        columns = [str(value) for value in values.get("columns", [])] or ["Value"]
        rows = [row if isinstance(row, (list, tuple)) else [row] for row in data]
        cell_w = plot.width() / max(1, len(columns))
        row_h = min(24.0, plot.height() / max(2, len(rows) + 1))
        painter.fillRect(QRectF(plot.left(), plot.top(), plot.width(), row_h), QColor("#f0f2f6"))
        painter.setPen(QColor(item.text_color))
        for col, heading in enumerate(columns):
            painter.drawText(
                QRectF(plot.left() + col * cell_w + 4, plot.top(), cell_w - 8, row_h),
                Qt.AlignmentFlag.AlignVCenter,
                heading,
            )
        for row_index, row in enumerate(rows[:5]):
            for col, value in enumerate(row[: len(columns)]):
                painter.drawText(
                    QRectF(plot.left() + col * cell_w + 4, plot.top() + (row_index + 1) * row_h, cell_w - 8, row_h),
                    Qt.AlignmentFlag.AlignVCenter,
                    str(value),
                )
    elif visual == "status_light":
        status = str(values.get("status", "offline"))
        lamp = {"online": "#16a779", "warning": "#f2aa3b", "error": "#e14f4f"}.get(status, "#9aa3b2")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(lamp) if values.get("active", True) else QColor("#c8cdd6"))
        painter.drawEllipse(QPointF(rect.left() + 28, rect.center().y()), 10, 10)
        painter.setPen(QColor(item.text_color))
        _title(painter, item, rect.adjusted(48, 0, -10, 0))
        painter.setPen(QColor("#8792a5"))
        painter.drawText(
            rect.adjusted(48, 28, -10, -9), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, status.title()
        )
    elif visual == "alarm_banner":
        severity = str(values.get("severity", "warning"))
        alert = {"critical": QColor("#dc3f45"), "info": QColor("#3978d4")}.get(severity, QColor("#e7a53b"))
        painter.fillRect(QRectF(rect.left(), rect.top(), 7, rect.height()), alert)
        painter.setBrush(alert)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(rect.left() + 28, rect.center().y()), 10, 10)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(rect.left() + 22, rect.center().y() - 9, 12, 18), Qt.AlignmentFlag.AlignCenter, "!")
        _title(painter, item, rect.adjusted(48, 8, -12, -rect.height() + 28))
        painter.setPen(QColor("#7a8495"))
        painter.drawText(
            rect.adjusted(48, 31, -12, -8),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            str(values.get("message", "")),
        )


def _industrial(painter, item, rect: QRectF, visual: str) -> None:
    values = item.custom_properties
    color = QColor(item.color)
    _card(painter, item, rect, 10)
    body = rect.adjusted(14, 30, -14, -14)
    _title(painter, item, rect.adjusted(12, 4, -12, -rect.height() + 27))
    painter.setPen(QPen(color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(QColor("#ffffff"))
    active = bool(values.get("active", values.get("closed", True)))
    if visual == "tank":
        tank = body.adjusted(body.width() * 0.2, 0, -body.width() * 0.2, 0)
        painter.drawRoundedRect(tank, 14, 14)
        fill = tank.adjusted(5, 5 + (tank.height() - 10) * (1 - _ratio(item)), -5, -5)
        fluid = QColor(color)
        fluid.setAlpha(115)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fluid)
        painter.drawRoundedRect(fill, 7, 7)
        painter.setPen(QColor(item.text_color))
        painter.drawText(
            tank, Qt.AlignmentFlag.AlignCenter, f"{_number(values.get('value')):g}{values.get('unit', '')}"
        )
    elif visual == "pump":
        center = body.center()
        radius = min(body.width(), body.height()) * 0.32
        painter.drawEllipse(center, radius, radius)
        painter.setBrush(color if active else QColor("#c9ced7"))
        painter.drawPolygon(
            QPolygonF(
                [
                    center + QPointF(-radius * 0.25, -radius * 0.45),
                    center + QPointF(radius * 0.5, 0),
                    center + QPointF(-radius * 0.25, radius * 0.45),
                ]
            )
        )
        painter.drawLine(
            QPointF(body.left(), center.y()),
            QPointF(center.x() - radius, center.y()),
        )
        painter.drawLine(
            QPointF(center.x() + radius, center.y()),
            QPointF(body.right(), center.y()),
        )
    elif visual == "valve":
        center = body.center()
        w = min(34.0, body.width() * 0.22)
        h = min(28.0, body.height() * 0.35)
        painter.setBrush(QColor("#e8faf6") if active else QColor("#f1f2f4"))
        painter.drawPolygon(
            QPolygonF([QPointF(center.x() - w, center.y() - h), center, QPointF(center.x() - w, center.y() + h)])
        )
        painter.drawPolygon(
            QPolygonF([QPointF(center.x() + w, center.y() - h), center, QPointF(center.x() + w, center.y() + h)])
        )
        painter.drawLine(center, QPointF(center.x(), body.top() + 4))
        painter.drawLine(QPointF(center.x() - 14, body.top() + 4), QPointF(center.x() + 14, body.top() + 4))
    elif visual in ("motor", "fan"):
        center = body.center()
        radius = min(body.width(), body.height()) * 0.34
        painter.drawEllipse(center, radius, radius)
        if visual == "motor":
            font = QFont(painter.font())
            font.setPointSizeF(18)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(color if active else QColor("#a7aeba"))
            painter.drawText(
                QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2),
                Qt.AlignmentFlag.AlignCenter,
                "M",
            )
        else:
            painter.setBrush(color if active else QColor("#c9ced7"))
            for angle in range(0, 360, 90):
                painter.save()
                painter.translate(center)
                painter.rotate(angle)
                painter.drawEllipse(QRectF(2, -radius * 0.22, radius * 0.78, radius * 0.44))
                painter.restore()
            painter.drawEllipse(center, 5, 5)
    elif visual == "pipe":
        y = body.center().y()
        painter.setPen(QPen(QColor("#b8c1ce"), 15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(body.left(), y), QPointF(body.right(), y))
        painter.setPen(QPen(color if active else QColor("#9aa3b2"), 5, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(body.left() + 4, y), QPointF(body.right() - 4, y))
        painter.setPen(QColor(item.text_color))
        painter.drawText(body, Qt.AlignmentFlag.AlignCenter, f"{values.get('value', '')} {values.get('unit', '')}")
    elif visual == "sensor":
        painter.setBrush(QColor("#edf9f7"))
        painter.drawEllipse(body.center(), 28, 28)
        font = QFont(painter.font())
        font.setPointSizeF(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(
            QRectF(body.center().x() - 50, body.center().y() - 18, 100, 36),
            Qt.AlignmentFlag.AlignCenter,
            f"{_number(values.get('value')):g}{values.get('unit', '')}",
        )
    elif visual == "plc":
        panel = body.adjusted(10, 2, -10, -2)
        painter.drawRoundedRect(panel, 5, 5)
        for row in range(3):
            y = panel.top() + 16 + row * 20
            painter.setBrush(QColor("#18a779") if str(values.get("status")) == "run" else QColor("#d6dae1"))
            painter.drawEllipse(QPointF(panel.left() + 14, y), 3.5, 3.5)
            painter.drawLine(QPointF(panel.left() + 28, y), QPointF(panel.right() - 10, y))
        painter.setPen(QColor(item.text_color))
        painter.drawText(
            panel.adjusted(8, 4, -8, -4),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            str(values.get("program", "")),
        )
    elif visual == "breaker":
        y = body.center().y()
        gap = 22
        painter.drawEllipse(QPointF(body.center().x() - gap, y), 4, 4)
        painter.drawEllipse(QPointF(body.center().x() + gap, y), 4, 4)
        end = (
            QPointF(body.center().x() + gap, y)
            if values.get("closed", True)
            else QPointF(body.center().x() + gap - 5, y - 24)
        )
        painter.setPen(
            QPen(
                QColor("#dc3f45") if values.get("tripped") else color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap
            )
        )
        painter.drawLine(QPointF(body.center().x() - gap, y), end)
    elif visual == "battery":
        battery = body.adjusted(body.width() * 0.18, body.height() * 0.12, -body.width() * 0.18, -body.height() * 0.12)
        painter.drawRoundedRect(battery, 5, 5)
        painter.fillRect(QRectF(battery.right(), battery.center().y() - 8, 6, 16), color)
        fill = battery.adjusted(5, 5, -5 - (battery.width() - 10) * (1 - _ratio(item)), -5)
        painter.fillRect(fill, QColor("#20b486") if _ratio(item) > 0.2 else QColor("#dc3f45"))
        painter.setPen(QColor(item.text_color))
        painter.drawText(battery, Qt.AlignmentFlag.AlignCenter, f"{_number(values.get('value')):g}%")
    elif visual == "transformer":
        center = body.center()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(center.x() - 16, center.y()), 25, 25)
        painter.drawEllipse(QPointF(center.x() + 16, center.y()), 25, 25)
        painter.setPen(QColor(item.text_color))
        painter.drawText(
            body.adjusted(0, body.height() - 20, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            f"{values.get('primaryVoltage', 0):g}V → {values.get('secondaryVoltage', 0):g}V",
        )
    elif visual == "conveyor":
        belt = body.adjusted(4, 18, -4, -18)
        painter.setBrush(QColor("#eef0f4"))
        painter.drawRoundedRect(belt, belt.height() / 2, belt.height() / 2)
        painter.setBrush(color if active else QColor("#aeb5c0"))
        painter.drawEllipse(
            QPointF(belt.left() + belt.height() / 2, belt.center().y()), belt.height() * 0.32, belt.height() * 0.32
        )
        painter.drawEllipse(
            QPointF(belt.right() - belt.height() / 2, belt.center().y()), belt.height() * 0.32, belt.height() * 0.32
        )
        painter.setPen(QColor(item.text_color))
        painter.drawText(body, Qt.AlignmentFlag.AlignCenter, f"{values.get('speed', 0):g} {values.get('unit', '')}")
    item._paint_ports(painter)


def _software(painter, item, rect: QRectF, visual: str) -> None:
    values = item.custom_properties
    color = QColor(item.color)
    painter.setPen(QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(QColor(item.background))
    body = rect.adjusted(10, 10, -10, -10)
    if visual == "decision":
        path = QPainterPath(QPointF(rect.center().x(), rect.top() + 3))
        path.lineTo(QPointF(rect.right() - 3, rect.center().y()))
        path.lineTo(QPointF(rect.center().x(), rect.bottom() - 3))
        path.lineTo(QPointF(rect.left() + 3, rect.center().y()))
        path.closeSubpath()
        painter.drawPath(path)
    elif visual == "terminator":
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
    elif visual == "cloud":
        path = QPainterPath()
        path.addRoundedRect(body.adjusted(10, 22, -10, -10), 24, 24)
        path.addEllipse(QRectF(body.left() + 25, body.top() + 12, 50, 45))
        path.addEllipse(QRectF(body.center().x() - 12, body.top() + 2, 58, 54))
        painter.drawPath(path.simplified())
    elif visual == "database":
        db = body.adjusted(15, 2, -15, -2)
        painter.drawRect(QRectF(db.left(), db.top() + 12, db.width(), db.height() - 24))
        painter.drawEllipse(QRectF(db.left(), db.top(), db.width(), 24))
        painter.drawArc(QRectF(db.left(), db.bottom() - 24, db.width(), 24), 180 * 16, 180 * 16)
        for y in (db.top() + db.height() * 0.42, db.top() + db.height() * 0.68):
            painter.drawArc(QRectF(db.left(), y - 12, db.width(), 24), 180 * 16, 180 * 16)
    elif visual in ("server", "container"):
        painter.drawRoundedRect(body, 7, 7)
        if visual == "server":
            for row in range(3):
                y = body.top() + 10 + row * (body.height() - 20) / 3
                painter.drawRoundedRect(QRectF(body.left() + 9, y, body.width() - 18, 18), 3, 3)
                painter.setBrush(QColor("#18a779"))
                painter.drawEllipse(QPointF(body.right() - 20, y + 9), 2.5, 2.5)
                painter.setBrush(QColor(item.background))
        else:
            painter.drawRect(body.adjusted(12, 14, -12, -14))
            painter.drawLine(body.topLeft() + QPointF(12, 14), body.bottomRight() - QPointF(12, 14))
            painter.drawLine(body.topRight() + QPointF(-12, 14), body.bottomLeft() + QPointF(12, -14))
    elif visual in ("api", "service", "process"):
        painter.drawRoundedRect(body, 12 if visual != "process" else 4, 12 if visual != "process" else 4)
        painter.setPen(color)
        glyph_rect = body.adjusted(10, 8, -10, -28)
        if visual == "service":
            center = glyph_rect.center()
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, 11, 11)
            painter.drawEllipse(center, 4, 4)
            for angle in range(0, 360, 45):
                radians = math.radians(angle)
                painter.drawLine(
                    center + QPointF(math.cos(radians) * 12, math.sin(radians) * 12),
                    center + QPointF(math.cos(radians) * 17, math.sin(radians) * 17),
                )
        else:
            font = QFont(painter.font())
            font.setPointSizeF(15 if visual == "api" else 9)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                glyph_rect,
                Qt.AlignmentFlag.AlignCenter,
                "</>" if visual == "api" else "PROCESS",
            )
    elif visual in ("queue", "topic", "cache"):
        painter.drawRoundedRect(body, 8, 8)
        if visual == "queue":
            for index in range(3):
                painter.drawRoundedRect(QRectF(body.left() + 14 + index * 28, body.center().y() - 12, 22, 24), 4, 4)
        elif visual == "topic":
            center = body.center()
            painter.setBrush(color)
            painter.drawEllipse(center, 5, 5)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, 18, 18)
            painter.drawEllipse(center, 31, 31)
        else:
            for index in range(3):
                painter.drawRect(
                    QRectF(
                        body.left() + 20 + index * 18,
                        body.top() + 20 + index * 10,
                        body.width() - 70,
                        body.height() - 52,
                    )
                )
    elif visual in ("file", "document"):
        page = body.adjusted(18, 2, -18, -2)
        fold = min(22.0, page.width() * 0.25)
        path = QPainterPath(page.topLeft())
        path.lineTo(QPointF(page.right() - fold, page.top()))
        path.lineTo(QPointF(page.right(), page.top() + fold))
        path.lineTo(page.bottomRight())
        path.lineTo(page.bottomLeft())
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(page.right() - fold, page.top()), QPointF(page.right() - fold, page.top() + fold))
        painter.drawLine(QPointF(page.right() - fold, page.top() + fold), QPointF(page.right(), page.top() + fold))
        if visual == "document":
            painter.drawArc(QRectF(page.left(), page.bottom() - 12, page.width(), 24), 0, 180 * 16)
    elif visual in ("annotation", "sticky_note"):
        painter.drawRoundedRect(rect, 4 if visual == "sticky_note" else 10, 4 if visual == "sticky_note" else 10)
        if visual == "sticky_note":
            fold = 20
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(rect.right() - fold, rect.bottom()),
                        rect.bottomRight(),
                        QPointF(rect.right(), rect.bottom() - fold),
                    ]
                )
            )
    else:
        painter.drawRoundedRect(body, 10, 10)
    painter.setPen(QColor(item.text_color))
    label_rect = rect.adjusted(14, rect.height() * 0.56, -14, -8)
    if visual in ("decision", "terminator", "annotation", "sticky_note"):
        label_rect = rect.adjusted(18, 12, -18, -12)
    font = QFont(painter.font())
    font.setPointSizeF(9)
    font.setWeight(QFont.Weight.DemiBold)
    painter.setFont(font)
    painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, item.text)
    technology = str(values.get("technology", ""))
    if technology and visual not in ("decision", "terminator", "annotation", "sticky_note"):
        painter.setPen(QColor("#8792a5"))
        painter.drawText(rect.adjusted(14, rect.height() * 0.76, -14, -5), Qt.AlignmentFlag.AlignCenter, technology)
    item._paint_ports(painter)


def paint_component_pack_item(painter, item, rect: QRectF, _option=None, _widget=None) -> None:
    """RendererFactory shared by every built-in opt-in component pack item."""

    visual = str(item.custom_properties.get("packVisual", item.kind))
    if item.kind.startswith("dash_"):
        _dashboard(painter, item, rect, visual)
    elif item.kind.startswith("ind_"):
        _industrial(painter, item, rect, visual)
    else:
        _software(painter, item, rect, visual)
    _selection(painter, item, rect)


__all__ = ["paint_component_pack_item"]
