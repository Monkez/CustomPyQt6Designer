@echo off
setlocal
cd /d "%~dp0"

if not exist "MonkezDesigner.exe" (
    echo [ERROR] MonkezDesigner.exe was not found beside this file.
    exit /b 1
)

start "" "MonkezDesigner.exe" %*
exit /b 0
