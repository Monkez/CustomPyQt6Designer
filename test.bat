@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\python.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

set "QT_QPA_PLATFORM=offscreen"
".venv311\Scripts\python.exe" -m unittest discover -s tests -v
exit /b %errorlevel%
