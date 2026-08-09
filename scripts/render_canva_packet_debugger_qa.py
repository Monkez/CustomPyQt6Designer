"""Render packet link metrics and replay controls for visual QA."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap
from PyQt6.QtTest import QTest
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
    source = canvas.addNode("Sensor", -340, 0, element_id="qa-sensor")
    splitter = canvas.addSplitter(-50, 0, output_count=2, element_id="qa-splitter")
    dashboard = canvas.addNode("Dashboard", 270, -120, element_id="qa-dashboard")
    archive = canvas.addNode("Historian", 270, 130, element_id="qa-historian")
    incoming = canvas.connectElements(
        source, splitter, connector_id="telemetry-ingress",
        sourcePort="out", targetPort="in", packetDuration=0.1,
        animated=True, animationEffect="packet",
    )
    canvas.connectElements(
        splitter, dashboard, connector_id="live-dashboard",
        sourcePort="out-1", targetPort="in", packetDuration=0.1,
        animated=True, animationEffect="particles",
    )
    canvas.connectElements(
        splitter, archive, connector_id="historian-write",
        sourcePort="out-2", targetPort="in", packetDuration=0.1,
        animated=True, animationEffect="flow",
    )
    window.resize(820, 630)
    window.show()
    canvas.fitContent()
    for index in range(4):
        canvas.sendMessageTicket(
            incoming, message_id=f"qa-packet-{index}",
            payload={"sequence": index}, travel_time=0.1,
        )
    QTest.qWait(420)
    canvas.sendMessageTicket(
        incoming, message_id="qa-timeout", travel_time=1.0, timeout=0.08
    )
    QTest.qWait(120)
    canvas.showRuntimeDebugger()
    debugger = canvas._runtime_debugger
    debugger.resize(690, 590)
    debugger._tabs.setCurrentIndex(3)
    if debugger._links.count():
        debugger._links.setCurrentRow(0)
    app.processEvents()

    margin = 18
    left = window.grab()
    right = debugger.grab()
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
        raise RuntimeError(f"Could not save packet debugger QA image: {path}")
    canvas.close()


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "build" / "qa" / "monkez-canva-packet-debugger.png"
    )
    render(destination.resolve())
    print(destination.resolve())
