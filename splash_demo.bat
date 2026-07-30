@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\python.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

".venv311\Scripts\python.exe" "examples\splash_demo.py"
exit /b %errorlevel%
