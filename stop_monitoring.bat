@echo off
echo ============================================
echo   STM-2 Monitoring System - Stop Script
echo ============================================
echo.

cd /d "%~dp0"

echo Stopping STM-2 monitoring system...
docker compose -f docker/docker-compose.yml down

echo.
echo STM-2 monitoring system has been stopped.
echo Press any key to exit.
pause >nul
