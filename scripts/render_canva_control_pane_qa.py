"""Render the collapsible MonkezCanva Control Pane for repeatable visual QA."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFont, QFontDatabase
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
    canvas.addNode(
        "Telemetry gateway",
        element_id="qa-node",
        ports=[
            {"id": "in", "mode": "input", "side": "left", "label": "Input"},
            {"id": "out", "mode": "output", "side": "right", "label": "Output"},
        ],
    )
    canvas.addDataBinding(
        "qa-node", "text", "gateway.status", binding_id="qa-status"
    )
    window.resize(920, 680)
    window.show()
    canvas.setEditMode(True)
    canvas.selectElement("qa-node")
    toolbox = canvas._toolbox
    toolbox._tabs.setCurrentIndex(1)
    toolbox._sync_inspector("qa-node")
    toolbox.resize(438, 720)
    toolbox.show()
    app.processEvents()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not toolbox.grab().save(str(path)):
        raise RuntimeError(f"Could not save Control Pane QA image: {path}")
    canvas.close()


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "build" / "qa" / "monkez-canva-collapsible-pane.png"
    )
    render(destination.resolve())
    print(destination.resolve())
