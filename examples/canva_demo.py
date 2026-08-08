from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow

from monkez_pyqt6.monkez_widgets import MonkezCanva


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("MonkezCanva Demo — press Ctrl+D, then E")
    canvas = MonkezCanva()
    window.setCentralWidget(canvas)

    camera = canvas.addNode("Camera", -360, -50, color="#0ea5e9")
    detector = canvas.addNode("Object detector", -90, -50, color="#7c3aed")
    decision = canvas.addNode("Decision", 180, -50, color="#f97316")
    chart = canvas.addChart(
        [28, 56, 44, 78, 66, 88], "line", 450, -80,
        text="Confidence", color="#16a34a",
    )
    canvas.connectElements(camera, detector)
    canvas.connectElements(detector, decision)
    canvas.connectElements(decision, chart)
    canvas.fitContent()

    canvas.elementClicked.connect(lambda element_id: canvas.highlightElement(element_id))
    window.resize(1180, 680)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
