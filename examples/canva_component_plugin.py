"""Minimal trusted MonkezCanva SDK plugin used by the diagnostic demo.

Host applications import this module themselves and pass ``PLUGIN`` to
``canvas.registerElementPlugin``. A canvas document never imports Python code.
"""

from __future__ import annotations

from PyQt6.QtCore import QLineF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QWidget

from monkez_pyqt6.monkez_canva import ElementDefinition, component_plugin


PLUGIN_ID = "com.monkez.examples.telemetry"


def paint_telemetry_sensor(painter, item, rect, _option, _widget) -> None:
    """Render a compact telemetry card without owning any persistent state."""

    value = float(item.custom_properties.get("value", 0.0))
    unit = str(item.custom_properties.get("unit", "°C"))
    accent = QColor(item.color)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(accent, 2))
    painter.setBrush(QColor(item.background))
    painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 14, 14)
    painter.setPen(QPen(accent, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(
        QLineF(rect.left() + 3, rect.top() + 18, rect.left() + 3, rect.bottom() - 18)
    )
    painter.setPen(QColor(item.text_color))
    title_font = QFont(painter.font())
    title_font.setBold(True)
    painter.setFont(title_font)
    painter.drawText(
        rect.adjusted(18, 10, -12, -rect.height() / 2),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        item.text,
    )
    value_font = QFont(painter.font())
    value_font.setPointSizeF(max(12.0, value_font.pointSizeF() + 4.0))
    painter.setFont(value_font)
    painter.drawText(
        rect.adjusted(18, rect.height() / 2 - 8, -12, -8),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        f"{value:.1f} {unit}",
    )


class TelemetryInspector(QWidget):
    """Small auto-apply Inspector extension for the example component."""

    def __init__(self, canvas, item) -> None:
        super().__init__()
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        value = QDoubleSpinBox()
        value.setRange(-1_000_000, 1_000_000)
        value.setDecimals(2)
        value.setValue(float(item.custom_properties.get("value", 0.0)))
        value.setSuffix(f" {item.custom_properties.get('unit', '°C')}")
        value.valueChanged.connect(
            lambda reading: canvas.updateElement(item.element_id, value=reading)
        )
        layout.addRow("Reading", value)
        hint = QLabel("Changes apply immediately and participate in Undo.")
        hint.setWordWrap(True)
        hint.setObjectName("CanvasPluginHint")
        layout.addRow(hint)


def create_telemetry_inspector(canvas, item) -> QWidget:
    return TelemetryInspector(canvas, item)


PLUGIN = component_plugin(
    PLUGIN_ID,
    "Telemetry example",
    "1.0.0",
    (
        ElementDefinition(
            "telemetry_sensor",
            "Telemetry sensor",
            "SDK examples",
            190,
            110,
            icon="gauge",
            defaults={
                "text": "Temperature",
                "value": 23.5,
                "unit": "°C",
                "color": "#ff6b5f",
                "background": "#fff7f5",
                "ports": (
                    {
                        "id": "value",
                        "mode": "output",
                        "side": "right",
                        "label": "Value",
                        "dataType": "float",
                    },
                ),
            },
            schema={
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                }
            },
            renderer_factory=paint_telemetry_sensor,
            inspector_factory=create_telemetry_inspector,
            plugin_id=PLUGIN_ID,
            plugin_version="1.0.0",
            capabilities={"content", "geometry", "appearance", "ports"},
        ),
    ),
    description="A complete renderer, typed-port and auto-apply Inspector example.",
    metadata={"homepage": "https://github.com/Monkez/CustomPyQt6Designer"},
)
