@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\python.exe" call setup.bat
if errorlevel 1 exit /b %errorlevel%

".venv311\Scripts\python.exe" -m ruff --version >nul 2>nul
if errorlevel 1 call setup.bat
if errorlevel 1 exit /b %errorlevel%

".venv311\Scripts\python.exe" -m ruff check src tests demo_project splash_heavy_demo
exit /b %errorlevel%
