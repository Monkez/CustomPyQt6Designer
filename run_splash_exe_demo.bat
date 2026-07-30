@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\SplashHeavyDemo\SplashHeavyDemo.exe" (
    echo Demo executable was not found. Building it now...
    call build_splash_demo.bat
    if errorlevel 1 exit /b 1
)

start "" "dist\SplashHeavyDemo\SplashHeavyDemo.exe"
exit /b 0
