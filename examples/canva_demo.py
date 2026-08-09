from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow

from monkez_pyqt6.monkez_widgets import MonkezCanva

from canva_component_plugin import PLUGIN as TELEMETRY_PLUGIN


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
    canvas.groupAdded.connect(lambda group_id: logger.info("groupAdded -> %s", group_id))
    canvas.groupRemoved.connect(lambda group_id: logger.info("groupRemoved -> %s", group_id))
    canvas.elementClicked.connect(lambda element_id: logger.info("elementClicked -> %s", element_id))
    canvas.connectorClicked.connect(lambda connector_id: logger.info("connectorClicked -> %s", connector_id))
    canvas.objectClicked.connect(lambda object_id: logger.info("objectClicked -> %s", object_id))
    canvas.autoSaved.connect(lambda target: logger.info("autoSaved -> %s", target))
    canvas.persistentSaved.connect(lambda path: logger.info("persistentSaved -> %s", path))
    canvas.messageSent.connect(lambda edge, message: logger.info("messageSent -> %s via %s", message, edge))
    canvas.messageArrived.connect(lambda edge, message: logger.info("messageArrived -> %s at %s", message, edge))
    canvas.portRuntimeValueChanged.connect(
        lambda element, port, value: logger.info(
            "portRuntimeValueChanged -> %s.%s = %r", element, port, value
        )
    )
    canvas.layoutApplied.connect(
        lambda metrics: logger.info("layoutApplied -> %s", metrics)
    )
    canvas.messageTicketChanged.connect(
        lambda message_id, state: logger.info(
            "messageTicketChanged -> %s [%s] hops=%s pending=%s",
            message_id, state["status"], state["hopCount"], state["pendingSegments"],
        )
    )
    canvas.runtimeTraceEvent.connect(
        lambda event: logger.info(
            "runtimeTrace -> #%s %s %s @ %s",
            event["sequence"], event["event"], event["messageId"], event["objectId"],
        )
    )
    canvas.workflowTraceEvent.connect(
        lambda event: logger.info(
            "workflowTrace -> #%s %s node=%s token=%s",
            event["sequence"], event["event"], event["nodeId"], event["tokenId"],
        )
    )
    canvas.workflowFinished.connect(
        lambda result: logger.info(
            "workflowFinished -> %s steps=%s outputs=%s",
            result["state"], result["steps"], result["outputs"],
        )
    )
    canvas.dataBindingEvent.connect(
        lambda event: logger.info(
            "binding -> #%s %s %s [%s]",
            event["sequence"], event["bindingId"], event["event"], event["state"],
        )
    )
    canvas.componentPackChanged.connect(
        lambda pack_id, enabled: logger.info(
            "componentPackChanged -> %s enabled=%s", pack_id, enabled
        )
    )
    canvas.componentPluginChanged.connect(
        lambda plugin_id, enabled: logger.info(
            "componentPluginChanged -> %s enabled=%s", plugin_id, enabled
        )
    )
    canvas.exportCompleted.connect(
        lambda path, format_name, scope: logger.info("exportCompleted -> %s [%s/%s]", path, scope, format_name)
    )
    canvas.dotImported.connect(
        lambda report: logger.info(
            "dotImported -> %s nodes=%s connectors=%s group=%s warnings=%s",
            report["name"],
            len(report["elements"]),
            len(report["connectors"]),
            report["group"] or "none",
            len(report["warnings"]),
        )
    )
    canvas.enableWorkflowComponents()
    canvas.enableAllComponentPacks()
    canvas.registerElementPlugin(TELEMETRY_PLUGIN)
    canvas.setPersistenceKey("demo-workspace")
    logger.info("Portable project workspace: %s", canvas.persistentPath())

    if not canvas.loadPersistent():
        camera = canvas.addNode(
            "Camera", -360, -50, color="#0ea5e9", element_id="camera",
            ports=[
                {
                    "id": "video", "mode": "output", "side": "right", "label": "Video",
                    "dataType": "dict", "unit": "frame", "maxConnections": 1,
                    "tooltip": "Decoded camera frame and capture metadata",
                },
                {
                    "id": "trigger", "mode": "input", "side": "left", "label": "Trigger",
                    "dataType": "bool", "required": True, "defaultValue": False,
                },
            ],
        )
        detector = canvas.addNode(
            "Object detector", -90, -50, color="#7c3aed", element_id="detector",
            ports=[
                {
                    "id": "frames", "mode": "input", "side": "left", "label": "Frames",
                    "dataType": "dict", "unit": "frame", "required": True,
                    "maxConnections": 1,
                },
                {
                    "id": "objects", "mode": "output", "side": "right", "label": "Objects",
                    "dataType": "list", "unit": "detections",
                },
                {
                    "id": "debug", "mode": "free", "side": "bottom", "label": "Debug",
                    "dataType": "dict",
                },
            ],
        )
        decision = canvas.addNode(
            "Decision", 180, -50, color="#f97316", element_id="decision",
            ports=[
                {
                    "id": "input", "mode": "input", "side": "left", "label": "Input",
                    "dataType": "list", "unit": "detections", "required": True,
                },
                {
                    "id": "yes", "mode": "output", "side": "right", "label": "Yes",
                    "dataType": "dict", "unit": "decision",
                },
                {
                    "id": "no", "mode": "output", "side": "bottom", "label": "No",
                    "dataType": "dict", "unit": "decision",
                },
            ],
        )
        chart = canvas.addChart(
            [28, 56, 44, 78, 66, 88], "line", 450, -80,
            text="Confidence", color="#16a34a", element_id="confidence-chart",
        )
        splitter = canvas.addSplitter(390, 150, output_count=2, element_id="result-splitter")
        monitor = canvas.addNode("Event log", 650, 170, color="#db2777", element_id="event-log")
        canvas.addSwimlane(
            (camera, detector, decision, chart),
            "vision-flow",
            label="Vision inference pipeline",
            lanes=("Capture", "Inference", "Decision"),
            color="#0f9f8f",
            background="#f0fdfa",
        )
        canvas.addSubflow(
            (splitter, monitor),
            "result-delivery",
            label="Reusable result delivery",
            color="#7c3aed",
            background="#faf5ff",
        )
        canvas.connectElements(
            camera, detector, connector_id="camera-to-detector",
            sourcePort="video", targetPort="frames",
            route="bezier", arrowEnd=True, animated=True,
            animationEffect="particles", flowColor="#38bdf8", flowSpeed=1.3,
        )
        canvas.connectElements(
            detector, decision, connector_id="detector-to-decision",
            sourcePort="objects", targetPort="input",
            route="orthogonal", lineStyle="dash", arrowEnd=True,
            animated=True, animationEffect="glow", effectIntensity=0.8,
        )
        canvas.connectElements(
            decision, chart, connector_id="decision-to-chart",
            route="straight", arrowStart=True, arrowEnd=True,
        )
        canvas.connectElements(
            decision, splitter, connector_id="decision-to-splitter",
            sourcePort="no", targetPort="in", route="bezier", arrowEnd=True,
            animated=True, animationEffect="packet", packetLoop=True,
            packetDuration=1.8, packetInterval=0.75,
        )
        canvas.connectElements(
            splitter, monitor, connector_id="splitter-to-log",
            sourcePort="out-1", targetPort="in", route="bezier", arrowEnd=True,
        )
        canvas.connectElements(
            splitter, chart, connector_id="splitter-to-chart",
            sourcePort="out-2", route="orthogonal", arrowEnd=True,
        )
        canvas.addLine(
            -280, 190, element_id="signal-line", arrowEnd=True, text="Signal",
            animated=True, animationEffect="pulse", flowColor="#a855f7",
        )
        canvas.addPolyline(
            [[0, 80], [90, 10], [190, 90]], 80, 190,
            element_id="pipeline", lineWidth=4, arrowEnd=True,
        )
        canvas.setPortRuntimeValue(
            camera, "video", {"width": 1920, "height": 1080, "sequence": 1}
        )
        canvas.setPortRuntimeValue(
            detector, "objects", [{"label": "vehicle", "confidence": 0.94}]
        )
        canvas.addDataBinding(
            chart,
            "data",
            "vision.metrics",
            binding_id="confidence-series-binding",
            transforms={"op": "get", "path": "samples"},
            throttle=0.1,
            stale_after=5.0,
            fallback=[0],
        )
        canvas.addDataBinding(
            monitor,
            "text",
            "vision.status",
            binding_id="event-log-binding",
            format="Status: {value}",
            error_fallback="Status unavailable",
        )
        workflow_source = canvas.addWorkflowComponent(
            "source", -250, 410, element_id="workflow-source", text="Telemetry"
        )
        workflow_transform = canvas.addWorkflowComponent(
            "transform", 20, 410, element_id="workflow-transform",
            text="Normalize value",
        )
        workflow_sink = canvas.addWorkflowComponent(
            "sink", 290, 410, element_id="workflow-sink", text="Dashboard"
        )
        canvas.setWorkflowConfig(
            workflow_transform, operation="scale", value=1.5
        )
        canvas.connectElements(
            workflow_source, workflow_transform,
            sourcePort="out", targetPort="in", connector_id="workflow-normalize",
            route="bezier", arrowEnd=True,
        )
        canvas.connectElements(
            workflow_transform, workflow_sink,
            sourcePort="out", targetPort="in", connector_id="workflow-display",
            route="bezier", arrowEnd=True,
        )
        kpi = canvas.addPackComponent(
            "dash_kpi_card", 560, 400, element_id="pack-throughput-kpi",
            text="Throughput", value=72.4, unit="fps", trend=8.2,
        )
        canvas.addPackComponent(
            "ind_tank", 830, 360, element_id="pack-buffer-tank",
            text="Frame buffer", value=68, unit="%",
        )
        canvas.addPackComponent(
            "soft_service", 1080, 405, element_id="pack-api-service",
            text="Inference API", technology="FastAPI", status="online",
        )
        canvas.addElement(
            "telemetry_sensor",
            1310,
            405,
            element_id="sdk-temperature-sensor",
            text="Device temperature",
            value=41.7,
            unit="°C",
        )
        canvas.addDataBinding(
            kpi,
            "property.value",
            "vision.kpi",
            binding_id="throughput-kpi-binding",
            transforms={"op": "get", "path": "fps"},
            throttle=0.1,
        )
    canvas.objectClicked.connect(lambda object_id: canvas.highlightObject(object_id))
    window.resize(1180, 680)
    window.show()
    QTimer.singleShot(0, canvas.fitContent)
    if "decision-to-splitter" in canvas.connectors():
        QTimer.singleShot(
            900,
            lambda: canvas.sendMessageTicket(
                "decision-to-splitter",
                message_id="demo-runtime-packet",
                payload={"decision": "reject", "confidence": 0.92},
                metadata={"topic": "vision.result", "demo": True},
                priority=8,
                ttl=8,
                timeout=8,
                branch_policy="all",
            ),
        )
    if "workflow-source" in canvas.elements():
        QTimer.singleShot(
            1400,
            lambda: canvas.runWorkflow(
                "workflow-source", 42, metadata={"topic": "telemetry.demo"}
            ),
        )
    if canvas.dataBindings():
        QTimer.singleShot(
            1800,
            lambda: canvas.feedDataSources({
                "vision.metrics": {"samples": [42, 61, 57, 81, 74, 93]},
                "vision.status": "live telemetry connected",
                "vision.kpi": {"fps": 91.6},
            }),
        )
    logger.info("Demo window shown: %sx%s", window.width(), window.height())
    logger.info("Shortcut option 1: press Ctrl+D, release Ctrl, then press E")
    logger.info("Shortcut option 2: hold Ctrl, press D, then press E")
    logger.info("When successful, logs will show 'Editor shortcut received' and toolbox state")
    logger.info("Open the packet debugger with Ctrl+K, then search 'runtime debugger'")
    logger.info("Workflow Pack is enabled; select a workflow node to edit/run it")
    logger.info("Dashboard, Industrial and Software component packs are enabled")
    logger.info("Select an element and open Inspector > Data bindings for live data")
    result = app.exec()
    logger.info("Demo closed with exit code %s", result)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
