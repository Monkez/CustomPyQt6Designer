"""Reproducible native large-scene benchmark for MonkezCanva."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QEvent
from PyQt6.QtWidgets import QApplication

from monkez_pyqt6.monkez_canva import CanvasDocument
from monkez_pyqt6.monkez_widgets import MonkezCanva


def _document(node_count: int, with_connectors: bool) -> CanvasDocument:
    columns = max(1, math.ceil(math.sqrt(node_count)))
    rows = max(1, math.ceil(node_count / columns))
    elements = []
    for index in range(node_count):
        row, column = divmod(index, columns)
        elements.append(
            {
                "id": f"node-{index}",
                "type": "node",
                "text": f"Node {index}",
                "x": column * 150.0,
                "y": row * 100.0,
                "width": 124.0,
                "height": 72.0,
                "ports": [
                    {"id": "in", "mode": "input", "side": "left"},
                    {"id": "out", "mode": "output", "side": "right"},
                ],
            }
        )
    connectors = []
    if with_connectors:
        for index in range(1, node_count):
            connectors.append(
                {
                    "id": f"edge-{index - 1}",
                    "type": "connector",
                    "source": f"node-{index - 1}",
                    "target": f"node-{index}",
                    "sourcePort": "out",
                    "targetPort": "in",
                    "route": "straight",
                }
            )
    return CanvasDocument.from_dict(
        {
            "format": "monkez-canva",
            "version": 1,
            "scene": {
                "width": max(4_000.0, columns * 150.0 + 300.0),
                "height": max(4_000.0, rows * 100.0 + 300.0),
                "gridVisible": True,
            },
            "elements": elements,
            "connectors": connectors,
            "groups": [],
            "resources": [],
        }
    )


def _render_samples(
    app: QApplication, canvas: MonkezCanva, sample_count: int
) -> dict:
    cold_started = time.perf_counter_ns()
    cold_pixmap = canvas.view().viewport().grab()
    cold_ms = (time.perf_counter_ns() - cold_started) / 1_000_000.0
    app.processEvents()
    if cold_pixmap.isNull():
        raise RuntimeError("Canvas viewport returned a null benchmark frame")
    durations = []
    canvas.resetPerformanceStats()
    for _index in range(max(1, sample_count)):
        started = time.perf_counter_ns()
        pixmap = canvas.view().viewport().grab()
        durations.append((time.perf_counter_ns() - started) / 1_000_000.0)
        app.processEvents()
        if pixmap.isNull():
            raise RuntimeError("Canvas viewport returned a null benchmark frame")
    stats = canvas.performanceStats()
    stats["coldGrabMs"] = round(cold_ms, 4)
    stats["grabAverageMs"] = round(statistics.fmean(durations), 4)
    stats["grabMaxMs"] = round(max(durations), 4)
    return stats


def benchmark_case(
    app: QApplication,
    node_count: int,
    *,
    with_connectors: bool,
    samples: int,
) -> dict:
    canvas = MonkezCanva()
    canvas.resize(1280, 760)
    canvas.setPerformanceMode("auto")
    document = _document(node_count, with_connectors)
    started = time.perf_counter_ns()
    canvas.setDocumentModel(document)
    load_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    canvas.show()
    app.processEvents()

    canvas.resetZoom()
    canvas.view().centerOn(document.elements[0].properties["x"], document.elements[0].properties["y"])
    app.processEvents()
    detail = _render_samples(app, canvas, samples)

    canvas.fitContent()
    app.processEvents()
    overview = _render_samples(app, canvas, samples)
    result = {
        "nodes": node_count,
        "connectors": len(document.connectors),
        "loadMs": round(load_ms, 4),
        "detail": detail,
        "overview": overview,
    }
    canvas.close()
    canvas.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes", nargs="+", type=int, default=(100, 1_000, 10_000)
    )
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument(
        "--with-connectors",
        action="store_true",
        help="Add a chain connector between every pair of consecutive nodes.",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("canva_performance.json")
    )
    args = parser.parse_args(argv)
    if any(size <= 0 or size > 10_000 for size in args.sizes):
        parser.error("Every size must be in the range 1..10000")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    report = {
        "format": "monkez-canva-performance",
        "version": 1,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "qt": QT_VERSION_STR,
            "pyqt": PYQT_VERSION_STR,
        },
        "viewport": {"width": 1280, "height": 760},
        "samplesPerView": max(1, args.samples),
        "withConnectors": bool(args.with_connectors),
        "cases": [],
    }
    for size in args.sizes:
        print(f"[RUN] {size:,} nodes", flush=True)
        result = benchmark_case(
            app,
            size,
            with_connectors=args.with_connectors,
            samples=args.samples,
        )
        report["cases"].append(result)
        print(
            f"[OK]  load={result['loadMs']:.1f} ms  "
            f"detail={result['detail']['grabAverageMs']:.1f} ms  "
            f"overview={result['overview']['grabAverageMs']:.1f} ms  "
            f"tier={result['overview']['tierCounts']}",
            flush=True,
        )
    target = args.output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[DONE] Report: {target}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
