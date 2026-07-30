@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
    call run.bat --new-splash
) else (
    call run.bat --new-splash "%~1"
)
exit /b %errorlevel%
