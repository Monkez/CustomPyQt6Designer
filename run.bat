@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\custom-pyqt6-designer.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

".venv311\Scripts\custom-pyqt6-designer.exe" %*
exit /b %errorlevel%
