"""Render a repeatable visual-QA snapshot of adapter health and live binding UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from canva_data_adapter import SimulatedTelemetryAdapter  # noqa: E402
from monkez_pyqt6.monkez_widgets import MonkezCanva  # noqa: E402


def _install_qa_font(app: QApplication) -> None:
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    app.setFont(QFont(families[0] if families else "Sans Serif", 10))


def render(path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    _install_qa_font(app)
    window = QMainWindow()
    window.setWindowTitle("MonkezCanva · External telemetry")
    canvas = MonkezCanva()
    window.setCentralWidget(canvas)

    source = canvas.addNode(
        "Temperature sensor", -310, -80, element_id="qa-source",
        ports=[{"id": "out", "mode": "output", "side": "right"}],
    )
    label = canvas.addText("Waiting", 15, -135, element_id="qa-value")
    chart = canvas.addChart(
        [18, 20, 21, 23], "line", 15, 15, text="Live temperature",
        element_id="qa-chart",
    )
    canvas.connectElements(
        source, label, sourcePort="out", route="bezier", arrowEnd=True,
        animated=True, animationEffect="particles",
    )
    canvas.addDataBinding(
        label, "text", "plant.temperature", binding_id="qa-temperature-text",
        transforms={"op": "get", "path": "value"}, format="{value} °C",
    )
    canvas.addDataBinding(
        chart, "data", "plant.series", binding_id="qa-temperature-series",
        transforms={"op": "get", "path": "samples"},
    )

    adapter = SimulatedTelemetryAdapter()
    canvas.registerDataAdapter(adapter)
    canvas.bindAdapterSource(
        "plant.temperature", "demo-telemetry", "temperature"
    )
    canvas.bindAdapterSource("plant.series", "demo-telemetry", "series")
    adapter.publish(
        "temperature", {"value": 24.8}, metadata={"quality": "good"}
    )
    adapter.publish("series", {"samples": [18, 20, 21, 23, 24.8]})

    window.resize(820, 620)
    window.show()
    canvas.fitContent()
    canvas.showRuntimeDebugger()
    debugger = canvas._runtime_debugger
    debugger.resize(650, 590)
    debugger._tabs.setCurrentIndex(3)
    app.processEvents()

    margin = 18
    left = window.grab()
    right = debugger.grab()
    output = QPixmap(left.width() + right.width() + margin * 3, max(
        left.height(), right.height()
    ) + margin * 2)
    output.fill(QColor("#eef1f4"))
    painter = QPainter(output)
    painter.drawPixmap(margin, margin, left)
    painter.drawPixmap(left.width() + margin * 2, margin, right)
    painter.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not output.save(str(path)):
        raise RuntimeError(f"Could not save visual QA image: {path}")
    canvas.close()


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "build" / "qa" / "monkez-canva-data-adapter.png"
    )
    render(destination.resolve())
    print(destination.resolve())
