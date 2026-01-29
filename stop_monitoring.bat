@echo off
echo ============================================
echo   STM-2 Monitoring System - Stop Script
echo ============================================
echo.

echo Stopping STM-2 monitoring system...
docker compose down

echo.
echo STM-2 monitoring system has been stopped.
echo Press any key to exit.
pause >nul
