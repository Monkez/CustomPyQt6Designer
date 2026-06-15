$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = ".\.venv311\Scripts\python.exe"
$PyInstaller = ".\.venv311\Scripts\pyinstaller.exe"

& $Python -m pip install pyinstaller

& $PyInstaller `
    --clean `
    --noconfirm `
    --onedir `
    --console `
    --name MonkezPyQt6DesignerFull `
    --paths src `
    --add-data "src\custom_pyqt6_designer;custom_pyqt6_designer" `
    --add-data ".venv311\Lib\site-packages\PyQt6;PyQt6" `
    --add-data ".venv311\Lib\site-packages\pyqt6_plugins;pyqt6_plugins" `
    --add-data ".venv311\Lib\site-packages\qt6_applications;qt6_applications" `
    --add-data ".venv311\Lib\site-packages\qt6_tools;qt6_tools" `
    --add-data ".venv311\Lib\site-packages\pyqt6_tools;pyqt6_tools" `
    --add-data ".venv311\Lib\site-packages\cv2;cv2" `
    --add-data ".venv311\Lib\site-packages\numpy;numpy" `
    --add-data ".venv311\Lib\site-packages\numpy.libs;numpy.libs" `
    src\custom_pyqt6_designer\exe_entry.py

Write-Host "Built: dist\MonkezPyQt6DesignerFull\MonkezPyQt6DesignerFull.exe"
