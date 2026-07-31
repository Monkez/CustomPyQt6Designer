@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\monkez-pyqt6.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

".venv311\Scripts\monkez-pyqt6.exe" %*
exit /b %errorlevel%
