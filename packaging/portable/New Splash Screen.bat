@echo off
setlocal
cd /d "%~dp0"

if not exist "MonkezDesigner.exe" (
    echo [ERROR] MonkezDesigner.exe was not found beside this file.
    exit /b 1
)

if "%~1"=="" (
    "MonkezDesigner.exe" --new-splash
) else (
    "MonkezDesigner.exe" --new-splash "%~1"
)
exit /b %errorlevel%
