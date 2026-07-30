@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\python.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo Building and verifying the heavy splash demo...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\build_splash_heavy_demo.ps1"
exit /b %errorlevel%
