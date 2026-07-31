@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python Launcher was not found. Install Python 3.11 first.
    exit /b 1
)

if not exist ".venv311\Scripts\python.exe" (
    echo [1/3] Creating Python 3.11 environment...
    py -3.11 -m venv .venv311
    if errorlevel 1 goto :error
) else (
    echo [1/3] Reusing .venv311...
)

echo [2/3] Updating packaging tools...
".venv311\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/3] Installing project and development tools...
".venv311\Scripts\python.exe" -m pip install -e ".[all,dev]" "pyinstaller==6.21.0"
if errorlevel 1 goto :error

echo.
echo Setup completed. Run run.bat to open Monkez Designer.
exit /b 0

:error
set "SETUP_EXIT=%errorlevel%"
echo.
echo [ERROR] Setup failed with exit code %SETUP_EXIT%.
exit /b %SETUP_EXIT%
