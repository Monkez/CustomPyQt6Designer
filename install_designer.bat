@echo off
setlocal
cd /d "%~dp0"

set "INSTALL_ROOT=%LOCALAPPDATA%\MonkezDesigner"
set "INSTALL_PYTHON=%INSTALL_ROOT%\venv\Scripts\python.exe"
set "DESIGNER_EXE=%INSTALL_ROOT%\venv\Scripts\monkez-pyqt6.exe"

echo.
echo Monkez Designer - per-user installation
echo Install location: %INSTALL_ROOT%
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python Launcher was not found.
    echo Install Python 3.11 from https://www.python.org/downloads/
    echo Enable "Install launcher for all users" in the Python installer.
    exit /b 1
)

py -3.11 -c "import sys; print(sys.version)" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.11 was not found.
    echo The Designer bridge currently requires Python 3.11.
    echo Download: https://www.python.org/downloads/windows/
    exit /b 1
)

if not exist "%INSTALL_PYTHON%" (
    echo [1/4] Creating an isolated Python 3.11 environment...
    if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%"
    py -3.11 -m venv "%INSTALL_ROOT%\venv"
    if errorlevel 1 goto :error
) else (
    echo [1/4] Reusing the existing isolated environment...
)

echo [2/4] Installing package and Designer dependencies...
"%INSTALL_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :error
"%INSTALL_PYTHON%" -m pip install --upgrade ".[designer]"
if errorlevel 1 goto :error

echo [3/4] Checking the installation...
"%DESIGNER_EXE%" --doctor
if errorlevel 1 goto :error

echo [4/4] Creating Start Menu and Desktop shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install_user_designer.ps1" -InstallRoot "%INSTALL_ROOT%" -SourceRoot "%CD%"
if errorlevel 1 goto :error

echo.
echo Installation completed successfully.
echo Opening Monkez Designer...
start "" "%DESIGNER_EXE%"
exit /b 0

:error
set "INSTALL_EXIT=%errorlevel%"
echo.
echo [ERROR] Installation failed with exit code %INSTALL_EXIT%.
echo Run this file again after resolving the message shown above.
exit /b %INSTALL_EXIT%
