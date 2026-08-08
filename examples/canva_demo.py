from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow

from monkez_pyqt6.monkez_widgets import MonkezCanva


def _configure_logging() -> logging.Logger:
    logger = logging.getLogger("monkez.canva.demo")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    log_path = Path(__file__).resolve().parents[1] / "canva_demo.log"
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.info("Log file: %s", log_path)
    return logger


def main() -> int:
    logger = _configure_logging()
    logger.info("Starting MonkezCanva demo with Python %s", sys.version.split()[0])
    app = QApplication.instance() or QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("MonkezCanva Demo — press Ctrl+D, then E")
    canvas = MonkezCanva()
    window.setCentralWidget(canvas)
    canvas.diagnosticMessage.connect(logger.info)
    canvas.editModeChanged.connect(lambda enabled: logger.info("editModeChanged -> %s", enabled))
    canvas.elementAdded.connect(lambda element_id: logger.info("elementAdded -> %s", element_id))
    canvas.elementClicked.connect(lambda element_id: logger.info("elementClicked -> %s", element_id))

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
    canvas.elementClicked.connect(lambda element_id: canvas.highlightElement(element_id))
    window.resize(1180, 680)
    window.show()
    QTimer.singleShot(0, canvas.fitContent)
    logger.info("Demo window shown: %sx%s", window.width(), window.height())
    logger.info("Shortcut option 1: press Ctrl+D, release Ctrl, then press E")
    logger.info("Shortcut option 2: hold Ctrl, press D, then press E")
    logger.info("When successful, logs will show 'Editor shortcut received' and toolbox state")
    result = app.exec()
    logger.info("Demo closed with exit code %s", result)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
