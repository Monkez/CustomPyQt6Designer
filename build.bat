@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\python.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo [1/2] Building Python package...
".venv311\Scripts\python.exe" -m build
if errorlevel 1 exit /b %errorlevel%

echo [2/2] Building portable Designer and verifying plugins...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\build_full_designer.ps1"
exit /b %errorlevel%
