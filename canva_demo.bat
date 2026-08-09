@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUNBUFFERED=1"

echo ============================================================
echo  MonkezCanva diagnostic demo
echo  Log file: %CD%\canva_demo.log
echo ============================================================
echo.

if not exist ".venv311\Scripts\python.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo [RUN] Starting demo with live logs...
echo [KEY] Option 1: Ctrl+D, release Ctrl, then E
echo [KEY] Option 2: Hold Ctrl, press D, then E
echo [TIP] Double-click a group header to collapse or expand its contents
echo [TIP] Right-click a group to fit, export, or ungroup it
echo [TIP] Drag from a port to see typed compatibility: green, purple conversion, red rejected
echo [TIP] Inspect Camera/Detector ports to edit type, unit, limits and runtime status
echo [TIP] Open View ^> Auto layout, or Ctrl+K and search "layout"
echo [TIP] Select several nodes before arranging to limit the layout scope
echo.

".venv311\Scripts\python.exe" -u "examples\canva_demo.py"
set "CANVA_EXIT=%errorlevel%"

echo.
echo [DONE] Demo exited with code %CANVA_EXIT%.
echo [LOG]  Full log: %CD%\canva_demo.log
if not "%CANVA_EXIT%"=="0" pause
exit /b %CANVA_EXIT%
