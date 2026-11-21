@echo off
rem IronPulse - run with Docker Desktop on Windows
rem The GUI is shown through an X server running on Windows:
rem   1. Install VcXsrv (https://sourceforge.net/projects/vcxsrv/)
rem   2. Start "XLaunch": Multiple windows -> Start no client -> tick "Disable access control"
rem   3. Run this file.
rem (On Windows 11 you can instead run ./docker-run.sh inside a WSL2 Ubuntu terminal.)
cd /d "%~dp0"

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop is not running. Start it and try again.
    pause
    exit /b 1
)

if not exist exports mkdir exports
set DISPLAY=host.docker.internal:0.0
if "%TZ%"=="" set TZ=UTC

docker compose up --build -d %*
if errorlevel 1 (
    pause
    exit /b 1
)
echo.
echo IronPulse is starting. If no window appears, check that XLaunch is running
echo with "Disable access control" ticked, then run:  docker compose logs app
echo Stop with:  docker compose down
pause
