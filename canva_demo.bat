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
echo [TIP] Ctrl+K, search "runtime debugger" to inspect packet tickets and timeline
echo [TIP] Debugger ^> Links shows throughput/latency; Replay compares a completed route
echo [TIP] Select a connector, then use Debugger ^> Breakpoint, Pause, Step and Resume
echo [TIP] Dashboard, Industrial and Software packs are enabled in this demo
echo [TIP] Select the KPI, Tank or Service to edit its component-specific properties
echo [TIP] Right-click blank canvas ^> Component packs, or Ctrl+K, to enable/disable packs
echo [TIP] Use the export icon on the floating toolbar for PNG, transparent PNG, SVG or PDF
echo [TIP] Ctrl+K, search "export" for selection, DOT, Mermaid, page setup and print preview
echo [TIP] Right-click blank canvas or Ctrl+K to import a Graphviz DOT graph
echo [TIP] "Import DOT as subflow" wraps the imported graph as one reusable group
echo [TIP] The SDK examples category contains a trusted plugin component with its own Inspector
echo [TIP] Ctrl+K, search "templates" to browse and insert reusable project templates
echo [TIP] Ctrl+K, search "health" to inspect document integrity and changes since save
echo [TIP] Ctrl+K, search "plugins" to discover, review and explicitly trust project packages
echo [TIP] View ^> Rendering selects adaptive Auto, full Quality or minimal Speed LOD
echo [TIP] Runtime Debugger ^> Bindings shows demo adapter health and live source counters
echo.

".venv311\Scripts\python.exe" -u "examples\canva_demo.py"
set "CANVA_EXIT=%errorlevel%"

echo.
echo [DONE] Demo exited with code %CANVA_EXIT%.
echo [LOG]  Full log: %CD%\canva_demo.log
if not "%CANVA_EXIT%"=="0" pause
exit /b %CANVA_EXIT%
