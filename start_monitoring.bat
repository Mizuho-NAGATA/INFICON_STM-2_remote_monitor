echo REAL BAT PATH: %~f0
pause

@echo off
cd /d "%~dp0"

echo ============================================
echo   STM-2 Monitoring System - Startup Script
echo ============================================
echo.

REM --- IP address input via GUI (English, safe from mojibake) ---
for /f "delims=" %%i in ('powershell -command "[void][System.Reflection.Assembly]::LoadWithPartialName('Microsoft.VisualBasic'); [Microsoft.VisualBasic.Interaction]::InputBox('Enter the fixed IP address of the STM-2 PC','IP Address','')"') do set STM2_IP=%%i

if "%STM2_IP%"=="" (
    echo [ERROR] No IP address entered.
    echo        Please run start_monitoring.bat again.
    pause
    exit /b 1
)

echo Using IP: %STM2_IP%
echo.

REM --- Docker Desktop のインストールチェック ---
if not exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    echo [ERROR] Docker Desktop がインストールされていません。
    echo         以下からインストールしてください：
    echo         https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

REM --- Docker Desktop が起動しているか確認 ---
echo Checking Docker Desktop status...

tasklist /FI "IMAGENAME eq Docker Desktop.exe" | find /I "Docker Desktop.exe" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo Docker Desktop is not running. Starting it now...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker Desktop to start...
) ELSE (
    echo Docker Desktop is already running.
)

REM --- Docker Engine が応答するまで待機 ---
echo Checking Docker Engine readiness...
:waitloop
docker info >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo   Docker Engine is not ready yet...
    timeout /t 3 >nul
    goto waitloop
)

echo Docker is ready!
echo.

REM --- docker compose up 実行 ---
echo Starting STM-2 monitoring system...
docker compose -f docker\docker-compose.yml up -d
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] docker compose up に失敗しました。
    echo        Docker Desktop が正常に動作しているか確認してください。
    echo.
    pause
    exit /b 1
)

echo STM-2 monitoring system is now running.
echo.

REM --- Grafana を自動で開く ---
echo Opening Grafana dashboard...
start "" http://%STM2_IP%:3000

REM --- ログウィンドウを表示 ---
echo Showing container logs...
echo (閉じるには Ctrl+C を押してください)
echo.
docker compose logs -f

pause


