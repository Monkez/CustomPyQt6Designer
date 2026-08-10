"""Portable Monkez PyQt6 project scaffolding."""
from __future__ import annotations

import json
import re
import struct
import subprocess
import zlib
from pathlib import Path


_PROJECT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _point_segment_distance(
    x: float,
    y: float,
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if not length_squared:
        return ((x - start[0]) ** 2 + (y - start[1]) ** 2) ** 0.5
    amount = max(0.0, min(1.0, ((x - start[0]) * dx + (y - start[1]) * dy) / length_squared))
    nearest_x = start[0] + amount * dx
    nearest_y = start[1] + amount * dy
    return ((x - nearest_x) ** 2 + (y - nearest_y) ** 2) ** 0.5


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def _default_logo_png(size: int) -> bytes:
    """Create a dependency-free RGBA Monkez placeholder brand asset."""
    rows = bytearray()
    radius = size * 0.22
    mark = ((0.25, 0.70), (0.25, 0.30), (0.50, 0.56), (0.75, 0.30), (0.75, 0.70))
    stroke = max(1.5, size * 0.075)
    for py in range(size):
        rows.append(0)
        y = (py + 0.5) / size
        for px in range(size):
            x = (px + 0.5) / size
            edge_x = min(px + 0.5, size - px - 0.5)
            edge_y = min(py + 0.5, size - py - 0.5)
            corner_dx = max(0.0, radius - edge_x)
            corner_dy = max(0.0, radius - edge_y)
            corner_distance = (corner_dx * corner_dx + corner_dy * corner_dy) ** 0.5
            alpha = max(0, min(255, round((radius + 0.5 - corner_distance) * 255)))
            distance = min(
                _point_segment_distance(px + 0.5, py + 0.5, (a[0] * size, a[1] * size), (b[0] * size, b[1] * size))
                for a, b in zip(mark, mark[1:])
            )
            if distance <= stroke:
                color = (255, 255, 255)
            else:
                blend = (x + y) / 2
                color = (
                    round(255 - 20 * blend),
                    round(111 - 42 * blend),
                    round(97 + 18 * blend),
                )
            rows.extend((*color, alpha))
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header) + _png_chunk(b"IDAT", zlib.compress(rows, 9)) + _png_chunk(b"IEND", b"")


def _default_app_icon() -> bytes:
    sizes = (16, 32, 48, 64, 128, 256)
    images = [_default_logo_png(size) for size in sizes]
    header_size = 6 + 16 * len(images)
    entries = bytearray()
    offset = header_size
    for size, image in zip(sizes, images):
        encoded_size = 0 if size == 256 else size
        entries.extend(struct.pack("<BBBBHHII", encoded_size, encoded_size, 0, 0, 1, 32, len(image), offset))
        offset += len(image)
    return struct.pack("<HHH", 0, 1, len(images)) + entries + b"".join(images)


def _write_default_branding(root: Path) -> None:
    (root / "assets" / "images" / "logo.png").write_bytes(_default_logo_png(512))
    (root / "assets" / "icons" / "app.ico").write_bytes(_default_app_icon())


def _main_py(project_name: str, python_version: str) -> str:
    return f'''from pathlib import Path
import json
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from monkez_pyqt6 import load_ui


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "assets" / "configs" / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> int:
    config = load_config()
    application_config = config.get("application", {{}})
    app = QApplication(sys.argv)
    app.setApplicationName(application_config.get("name", "{project_name}"))
    icon = ROOT / application_config.get("icon", "assets/icons/app.ico")
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    logo = ROOT / application_config.get("logo", "assets/images/logo.png")
    splash_pixmap = QPixmap(str(logo))
    if splash_pixmap.isNull():
        splash_pixmap = QPixmap(520, 260)
    else:
        splash_pixmap = splash_pixmap.scaled(
            360,
            360,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    splash = QSplashScreen(splash_pixmap)
    splash.showMessage("Loading {project_name}...", Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
    splash.show()
    app.processEvents()
    window = QMainWindow()
    load_ui(ROOT / "assets" / "qt-uis" / "main.ui", base_instance=window)
    window.show()
    splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _main_ui(project_name: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <property name="windowTitle"><string>{project_name}</string></property>
  <widget class="QWidget" name="centralwidget"/>
 </widget>
 <resources/>
 <connections/>
</ui>
'''


def _setup_bat(python_version: str) -> str:
    return fr'''@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv was not found. Installing uv for the current user...
  python -m pip install --user --upgrade uv
  if errorlevel 1 exit /b %errorlevel%
  echo Creating managed Python {python_version} environment with uv...
  python -m uv venv .venv --python {python_version} --python-preference managed
  if errorlevel 1 exit /b %errorlevel%
  python -m uv pip install --python .venv\Scripts\python.exe --upgrade -r requirements.txt
  if errorlevel 1 exit /b %errorlevel%
) else (
  echo Creating managed Python {python_version} environment with uv...
  uv venv .venv --python {python_version} --python-preference managed
  if errorlevel 1 exit /b %errorlevel%
  uv pip install --python .venv\Scripts\python.exe --upgrade -r requirements.txt
  if errorlevel 1 exit /b %errorlevel%
)
if errorlevel 1 exit /b %errorlevel%
echo Environment ready.
'''


def _run_bat() -> str:
    return r'''@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
call ".venv\Scripts\activate.bat"
python main.py
'''


def _build_bat(project_name: str) -> str:
    return fr'''@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call setup.bat
call ".venv\Scripts\activate.bat"
python -m PyInstaller --noconfirm --clean --windowed --name "{project_name}" --icon "assets\icons\app.ico" --add-data "assets;assets" main.py
echo Built dist\\{project_name}\\{project_name}.exe
'''


def create_project(path: str | Path, *, name: str | None = None, python_version: str = "3.11", run_setup: bool = True) -> Path:
    root = Path(path).expanduser().resolve()
    project_name = name or root.name
    if not _PROJECT_NAME.fullmatch(project_name):
        raise ValueError("Project name must start with a letter and contain only letters, numbers, '-' or '_'")
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Project directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for folder in ("qt-uis", "images", "icons", "logs", "configs", "modules"):
        (root / "assets" / folder).mkdir(parents=True, exist_ok=True)
    _write_default_branding(root)
    (root / "assets" / "configs" / "config.json").write_text(json.dumps({
        "application": {
            "name": project_name,
            "version": "0.1.0",
            "icon": "assets/icons/app.ico",
            "logo": "assets/images/logo.png",
        },
        "python": python_version,
    }, indent=2) + "\n", encoding="utf-8")
    (root / "assets" / "qt-uis" / "main.ui").write_text(_main_ui(project_name), encoding="utf-8")
    (root / "main.py").write_text(_main_py(project_name, python_version), encoding="utf-8")
    (root / "setup.bat").write_text(_setup_bat(python_version), encoding="utf-8")
    (root / "requirements.txt").write_text(
        "monkez-pyqt6[all] @ git+https://github.com/Monkez/CustomPyQt6Designer.git@main\npyinstaller>=6.0\n", encoding="utf-8"
    )
    (root / "run.bat").write_text(_run_bat(), encoding="utf-8")
    (root / "build.bat").write_text(_build_bat(project_name), encoding="utf-8")
    (root / "README.md").write_text(f"# {project_name}\n\nRun `setup.bat`, then `run.bat`.\n", encoding="utf-8")
    if run_setup:
        subprocess.run(["cmd", "/c", "setup.bat"], cwd=root, check=True)
    return root
