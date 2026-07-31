from __future__ import annotations

import os
from pathlib import Path


def write_probe(message: str) -> None:
    probe_path = os.environ.get("CUSTOM_PYQT6_DESIGNER_PLUGIN_PROBE")
    if not probe_path:
        return

    path = Path(probe_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{message}\n")
