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
    app.setOrganizationName("Monkez")
    app.setApplicationName("MonkezCanvaDemo")
    window = QMainWindow()
    window.setWindowTitle("MonkezCanva Demo — press Ctrl+D, then E")
    canvas = MonkezCanva()
    window.setCentralWidget(canvas)
    canvas.diagnosticMessage.connect(logger.info)
    canvas.editModeChanged.connect(lambda enabled: logger.info("editModeChanged -> %s", enabled))
    canvas.elementAdded.connect(lambda element_id: logger.info("elementAdded -> %s", element_id))
    canvas.connectorAdded.connect(lambda connector_id: logger.info("connectorAdded -> %s", connector_id))
    canvas.elementClicked.connect(lambda element_id: logger.info("elementClicked -> %s", element_id))
    canvas.connectorClicked.connect(lambda connector_id: logger.info("connectorClicked -> %s", connector_id))
    canvas.objectClicked.connect(lambda object_id: logger.info("objectClicked -> %s", object_id))
    canvas.autoSaved.connect(lambda target: logger.info("autoSaved -> %s", target))
    canvas.persistentSaved.connect(lambda path: logger.info("persistentSaved -> %s", path))
    canvas.setPersistenceKey("demo-workspace")
    logger.info("Portable project workspace: %s", canvas.persistentPath())

    if not canvas.loadPersistent():
        camera = canvas.addNode(
            "Camera", -360, -50, color="#0ea5e9", element_id="camera",
            ports=[
                {"id": "video", "mode": "output", "side": "right", "label": "Video"},
                {"id": "trigger", "mode": "input", "side": "left", "label": "Trigger"},
            ],
        )
        detector = canvas.addNode(
            "Object detector", -90, -50, color="#7c3aed", element_id="detector",
            ports=[
                {"id": "frames", "mode": "input", "side": "left", "label": "Frames"},
                {"id": "objects", "mode": "output", "side": "right", "label": "Objects"},
                {"id": "debug", "mode": "free", "side": "bottom", "label": "Debug"},
            ],
        )
        decision = canvas.addNode(
            "Decision", 180, -50, color="#f97316", element_id="decision",
            ports=[
                {"id": "input", "mode": "input", "side": "left", "label": "Input"},
                {"id": "yes", "mode": "output", "side": "right", "label": "Yes"},
                {"id": "no", "mode": "output", "side": "bottom", "label": "No"},
            ],
        )
        chart = canvas.addChart(
            [28, 56, 44, 78, 66, 88], "line", 450, -80,
            text="Confidence", color="#16a34a", element_id="confidence-chart",
        )
        canvas.connectElements(
            camera, detector, connector_id="camera-to-detector",
            sourcePort="video", targetPort="frames",
            route="bezier", arrowEnd=True, animated=True,
            flowColor="#38bdf8", flowSpeed=1.3,
        )
        canvas.connectElements(
            detector, decision, connector_id="detector-to-decision",
            sourcePort="objects", targetPort="input",
            route="orthogonal", lineStyle="dash", arrowEnd=True,
        )
        canvas.connectElements(
            decision, chart, connector_id="decision-to-chart",
            route="straight", arrowStart=True, arrowEnd=True,
        )
        canvas.addLine(-280, 190, element_id="signal-line", arrowEnd=True, text="Signal")
        canvas.addPolyline(
            [[0, 80], [90, 10], [190, 90]], 80, 190,
            element_id="pipeline", lineWidth=4, arrowEnd=True,
        )
    canvas.objectClicked.connect(lambda object_id: canvas.highlightObject(object_id))
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
