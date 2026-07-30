@echo off
setlocal

set "UNINSTALL_SCRIPT=%~dp0scripts\uninstall_user_designer.ps1"
if not exist "%UNINSTALL_SCRIPT%" set "UNINSTALL_SCRIPT=%~dp0tools\uninstall_user_designer.ps1"

if not exist "%UNINSTALL_SCRIPT%" (
    echo [ERROR] Uninstall helper was not found.
    exit /b 1
)

cd /d "%TEMP%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%UNINSTALL_SCRIPT%"
exit /b %errorlevel%
