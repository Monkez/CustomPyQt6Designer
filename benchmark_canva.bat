@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  MonkezCanva large-scene benchmark
echo  Scenarios: 100, 1,000 and 10,000 nodes
echo  Report:    %CD%\canva_performance.json
echo  Log:       %CD%\canva_performance.log
echo ============================================================
echo.

if not exist ".venv311\Scripts\python.exe" (
    echo Environment is not ready. Running setup.bat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "& { & '.\.venv311\Scripts\python.exe' -u 'scripts\benchmark_canva_performance.py' --output 'canva_performance.json' 2>&1 | Tee-Object -FilePath 'canva_performance.log'; exit $LASTEXITCODE }"
set "BENCH_EXIT=%errorlevel%"

echo.
if "%BENCH_EXIT%"=="0" (
    echo [DONE] Benchmark completed successfully.
) else (
    echo [FAIL] Benchmark exited with code %BENCH_EXIT%.
)
exit /b %BENCH_EXIT%
