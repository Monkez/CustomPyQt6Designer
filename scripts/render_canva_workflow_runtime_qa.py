"""Render the recurring workflow runtime debugger for visual QA."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow

from monkez_pyqt6.monkez_widgets import MonkezCanva


ROOT = Path(__file__).resolve().parents[1]


def _install_qa_font(app: QApplication) -> None:
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    app.setFont(QFont(families[0] if families else "Sans Serif", 10))


def render(path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    _install_qa_font(app)
    window = QMainWindow()
    canvas = MonkezCanva()
    window.setCentralWidget(canvas)
    canvas.enableWorkflowComponents()
    timer = canvas.addWorkflowComponent("timer", -240, 0, element_id="qa-timer")
    sink = canvas.addWorkflowComponent("sink", 120, 0, element_id="qa-sink")
    canvas.connectElements(
        timer, sink, source_port="out", target_port="in",
        connector_id="qa-timer-sink", packetDuration=0.12,
    )
    window.resize(840, 620)
    window.show()
    canvas.fitContent()
    canvas.scheduleWorkflow(
        timer, {"source": "heartbeat", "value": 42}, interval=1.0,
        initial_delay=0.0, max_occurrences=5, catch_up="latest",
        schedule_id="heartbeat", visualize=True,
    )
    canvas.runActiveWorkflow()
    canvas.advanceWorkflow(2.2)
    canvas.showRuntimeDebugger()
    debugger = canvas._runtime_debugger
    debugger.resize(700, 620)
    debugger._tabs.setCurrentIndex(2)
    app.processEvents()

    left = window.grab()
    right = debugger.grab()
    margin = 18
    output = QPixmap(
        left.width() + right.width() + margin * 3,
        max(left.height(), right.height()) + margin * 2,
    )
    output.fill(QColor("#eef1f4"))
    painter = QPainter(output)
    painter.drawPixmap(margin, margin, left)
    painter.drawPixmap(left.width() + margin * 2, margin, right)
    painter.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not output.save(str(path)):
        raise RuntimeError(f"Could not save workflow debugger QA image: {path}")
    canvas.close()


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "build" / "qa" / "monkez-canva-workflow-runtime.png"
    )
    render(destination.resolve())
    print(destination.resolve())
