$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = ".\.venv311\Scripts\python.exe"
$PyInstaller = ".\.venv311\Scripts\pyinstaller.exe"
$Version = & $Python -c "from custom_pyqt6_designer import __version__; print(__version__)"
$PythonHome = & $Python -c "import sys; print(sys.base_prefix)"
$OutputDirectory = "dist\MonkezPyQt6DesignerFull"

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
    --add-data "$PythonHome\Lib;python_runtime\Lib" `
    --add-data "$PythonHome\DLLs;python_runtime\DLLs" `
    --add-binary "$PythonHome\python3.dll;python_runtime" `
    --add-binary "$PythonHome\python311.dll;python_runtime" `
    --add-binary "$PythonHome\vcruntime140.dll;python_runtime" `
    --add-binary "$PythonHome\vcruntime140_1.dll;python_runtime" `
    src\custom_pyqt6_designer\exe_entry.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$VerificationUi = (Resolve-Path "examples\monkez_widgets_test.ui").Path
& "$OutputDirectory\MonkezPyQt6DesignerFull.exe" --verify-plugins $VerificationUi
if ($LASTEXITCODE -ne 0) {
    throw "Bundled Designer plugin verification failed."
}

Write-Host "Built: $OutputDirectory\MonkezPyQt6DesignerFull.exe"
