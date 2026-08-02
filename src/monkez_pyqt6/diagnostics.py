from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from . import __version__
from .launcher import (
    find_designer,
    has_pyqt6_tools_bridge,
    plugin_dir,
)


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    label: str
    ok: bool
    detail: str
    solution: str = ""


def collect_diagnostics() -> list[DiagnosticCheck]:
    frozen = bool(getattr(sys, "frozen", False))
    python_version = sys.version_info[:3]
    runtime_python_ok = python_version >= (3, 10)
    designer_python_ok = frozen or python_version[:2] == (3, 11)
    plugins = sorted(plugin_dir().glob("*_plugin.py"))
    designer = find_designer()
    bridge_ok = frozen or has_pyqt6_tools_bridge()

    return [
        DiagnosticCheck(
            "Runtime package",
            True,
            f"monkez-pyqt6 {__version__} at {Path(__file__).resolve().parent}",
        ),
        DiagnosticCheck(
            "Python runtime",
            runtime_python_ok,
            f"Python {'.'.join(map(str, python_version))}",
            "Install Python 3.10 or newer.",
        ),
        DiagnosticCheck(
            "Designer Python",
            designer_python_ok,
            "Portable runtime" if frozen else f"Python {python_version[0]}.{python_version[1]}",
            "Use Python 3.11 for the pyqt6-tools Designer bridge, or use the portable ZIP.",
        ),
        DiagnosticCheck(
            "Monkez plugins",
            len(plugins) == 26,
            f"{len(plugins)} plugin modules in {plugin_dir()}",
            "Reinstall the package or download a complete portable release.",
        ),
        DiagnosticCheck(
            "Qt Designer",
            designer is not None,
            str(designer) if designer is not None else "Not found",
            'Install with the "designer" extra or use MonkezDesigner portable.',
        ),
        DiagnosticCheck(
            "Python plugin bridge",
            bridge_ok,
            "Bundled" if frozen else ("Available" if bridge_ok else "Not found"),
            'Run install_designer.bat or install the package with the "designer" extra.',
        ),
    ]


def run_doctor(stream: TextIO | None = None) -> int:
    output = stream or sys.stdout
    checks = collect_diagnostics()
    print(f"Custom PyQt6 Designer {__version__} - environment check", file=output)
    print("", file=output)
    for check in checks:
        status = "OK" if check.ok else "ERROR"
        print(f"[{status}] {check.label}: {check.detail}", file=output)
        if not check.ok and check.solution:
            print(f"        Fix: {check.solution}", file=output)

    failures = [check for check in checks if not check.ok]
    print("", file=output)
    if failures:
        print(f"Result: {len(failures)} issue(s) need attention.", file=output)
        return 2
    print("Result: ready to open Monkez Designer.", file=output)
    return 0
