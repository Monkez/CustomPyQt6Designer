"""Portable Monkez PyQt6 project scaffolding."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


_PROJECT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


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
    app = QApplication(sys.argv)
    app.setApplicationName(config.get("application", {{}}).get("name", "{project_name}"))
    icon = ROOT / config.get("application", {{}}).get("icon", "assets/icons/app.ico")
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    splash = QSplashScreen(QPixmap(520, 260))
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
) else (
  echo Creating managed Python {python_version} environment with uv...
  uv venv .venv --python {python_version} --python-preference managed
  if errorlevel 1 exit /b %errorlevel%
  uv pip install --python .venv\Scripts\python.exe --upgrade -r requirements.txt
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
python -m PyInstaller --noconfirm --clean --windowed --name "{project_name}" --add-data "assets;assets" main.py
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
    (root / "assets" / "configs" / "config.json").write_text(json.dumps({
        "application": {"name": project_name, "version": "0.1.0", "icon": "assets/icons/app.ico"},
        "python": python_version,
    }, indent=2) + "\n", encoding="utf-8")
    (root / "assets" / "qt-uis" / "main.ui").write_text(_main_ui(project_name), encoding="utf-8")
    (root / "main.py").write_text(_main_py(project_name, python_version), encoding="utf-8")
    (root / "setup.bat").write_text(_setup_bat(python_version), encoding="utf-8")
    (root / "requirements.txt").write_text(
        "monkez-pyqt6[all]>=0.6.2\npyinstaller>=6.0\n", encoding="utf-8"
    )
    (root / "run.bat").write_text(_run_bat(), encoding="utf-8")
    (root / "build.bat").write_text(_build_bat(project_name), encoding="utf-8")
    (root / "README.md").write_text(f"# {project_name}\n\nRun `setup.bat`, then `run.bat`.\n", encoding="utf-8")
    if run_setup:
        subprocess.run(["cmd", "/c", "setup.bat"], cwd=root, check=True)
    return root
