@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ██████╗ ████████╗███╗   ███╗      ██████╗     ███████╗██╗   ██╗███████╗████████╗███████╗███╗   ███╗
echo ██╔════╝╚══██╔══╝████╗ ████║     ██╔════╝     ██╔════╝╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔════╝████╗ ████║
echo ╚██████╗   ██║   ██╔████╔██║     ██║  ███╗    ███████╗ ╚████╔╝ ███████╗   ██║   █████╗  ██╔████╔██║
echo  ╚════██║   ██║   ██║╚██╔╝██║     ██║   ██║    ╚════██║  ╚██╔╝  ╚════██║   ██║   ██╔══╝  ██║╚██╔╝██║
echo ██████╔╝   ██║   ██║ ╚═╝ ██║     ╚██████╔╝    ███████║   ██║   ███████║   ██║   ███████╗██║ ╚═╝ ██║
echo ╚═════╝    ╚═╝   ╚═╝     ╚═╝      ╚═════╝     ╚══════╝   ╚═╝   ╚══════╝   ╚═╝   ╚══════╝╚═╝     ╚═╝
echo.
echo                              Complete Automation System v1.0
echo                                    Startup in Progress...
echo.

REM ===========================================
REM 管理者権限チェック
REM ===========================================
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] 管理者権限で再起動中...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b 0
)

REM ===========================================
REM システム要件チェック
REM ===========================================
echo [STEP 1/7] システム要件チェック中...

REM Python インストールチェック
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python がインストールされていません。
    echo         以下からインストールしてください：
    echo         https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo         ✓ Python インストール済み

REM Docker Desktop インストールチェック
if not exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    echo [ERROR] Docker Desktop がインストールされていません。
    echo         以下からインストールしてください：
    echo         https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)
echo         ✓ Docker Desktop インストール済み

REM ===========================================
REM ファイアウォール自動設定
REM ===========================================
echo [STEP 2/7] ファイアウォール設定中...

netsh advfirewall firewall show rule name="STM-2 Grafana Port 3000" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo         ファイアウォール規則を追加中...
    netsh advfirewall firewall add rule name="STM-2 Grafana Port 3000" dir=in action=allow protocol=TCP localport=3000
    if %ERRORLEVEL% equ 0 (
        echo         ✓ ファイアウォール規則を追加しました
    ) else (
        echo         ⚠ ファイアウォール規則の追加に失敗しました（手動設定が必要）
    )
) else (
    echo         ✓ ファイアウォール規則設定済み
)

REM ===========================================
REM IP アドレス自動取得
REM ===========================================
echo [STEP 3/7] ネットワーク設定取得中...

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /R "IPv4.*Address"') do (
    for /f "tokens=1" %%j in ("%%i") do set LOCAL_IP=%%j
    goto :ip_found
)

:ip_found
if "%LOCAL_IP%"=="" (
    echo [ERROR] ローカルIPアドレスの取得に失敗しました。
    set /p LOCAL_IP=手動でIPアドレスを入力してください:
)
echo         ✓ ローカルIP: %LOCAL_IP%

REM ===========================================
REM Python 依存関係インストール
REM ===========================================
echo [STEP 4/7] Python依存関係チェック中...

python -c "import influxdb, customtkinter, tkinterdnd2" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo         必要なライブラリをインストール中...
    pip install influxdb customtkinter tkinterdnd2 --quiet
    if %ERRORLEVEL% equ 0 (
        echo         ✓ Python依存関係インストール完了
    ) else (
        echo         ⚠ Python依存関係のインストールに失敗しました
    )
) else (
    echo         ✓ Python依存関係インストール済み
)

REM ===========================================
REM Docker 起動・待機
REM ===========================================
echo [STEP 5/7] Docker システム起動中...

tasklist /FI "IMAGENAME eq Docker Desktop.exe" | find /I "Docker Desktop.exe" >nul
if %ERRORLEVEL% neq 0 (
    echo         Docker Desktop を起動中...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo         Docker Engine 起動待機中...

    set /a timeout_counter=0
    :docker_wait_loop
    if %timeout_counter% gtr 120 (
        echo [ERROR] Docker の起動がタイムアウトしました。
        echo         手動でDocker Desktopを確認してください。
        pause
        exit /b 1
    )

    docker info >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo         待機中... (%timeout_counter%/120秒)
        timeout /t 3 >nul
        set /a timeout_counter+=3
        goto docker_wait_loop
    )
    echo         ✓ Docker Engine 起動完了
) else (
    echo         Docker Desktop は既に起動しています
    docker info >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo         Docker Engine 起動待機中...
        :docker_wait_loop2
        docker info >nul 2>&1
        if %ERRORLEVEL% neq 0 (
            timeout /t 2 >nul
            goto docker_wait_loop2
        )
    )
    echo         ✓ Docker Engine 準備完了
)

REM ===========================================
REM STM-2 監視システム起動
REM ===========================================
echo [STEP 6/7] STM-2 監視システム起動中...

docker compose -f docker/docker-compose.yml down >nul 2>&1
docker compose -f docker/docker-compose.yml up -d
if %ERRORLEVEL% neq 0 (
    echo [ERROR] STM-2 監視システムの起動に失敗しました。
    echo         Docker の状態を確認してください。
    pause
    exit /b 1
)

echo         サービス起動待機中...
timeout /t 10 >nul

REM サービスの起動確認
docker compose -f docker/docker-compose.yml ps | findstr "Up" >nul
if %ERRORLEVEL% neq 0 (
    echo         ⚠ 一部サービスが起動していない可能性があります
) else (
    echo         ✓ STM-2 監視システム起動完了
)

REM ===========================================
REM GUI アプリケーション起動
REM ===========================================
echo [STEP 7/7] GUI アプリケーション起動中...

start "STM-2 GUI" python src/gui_app.py
if %ERRORLEVEL% equ 0 (
    echo         ✓ GUI アプリケーション起動完了
) else (
    echo         ⚠ GUI アプリケーションの起動に失敗しました
)

REM Grafana ダッシュボードを開く
timeout /t 5 >nul
echo         ✓ Grafana ダッシュボードを開いています...
start "" http://%LOCAL_IP%:3000

REM ===========================================
REM システム起動完了
REM ===========================================
echo.
echo ╔════════════════════════════════════════════════════════════════════╗
echo ║                        🎉 システム起動完了！ 🎉                      ║
echo ╠════════════════════════════════════════════════════════════════════╣
echo ║                                                                    ║
echo ║  📊 Grafana ダッシュボード: http://%LOCAL_IP%:3000                ║
echo ║  🖥️  GUI アプリケーション: 起動済み                                   ║
echo ║  🐳 Docker サービス: 動作中                                        ║
echo ║                                                                    ║
echo ║  🔧 使用方法:                                                       ║
echo ║     1. GUI で目標厚さとマテリアルを設定                             ║
echo ║     2. STM-2 の .log ファイルを選択                                ║
echo ║     3. "Start Logging" をクリック                                  ║
echo ║     4. Grafana でリアルタイム監視                                   ║
echo ║                                                                    ║
echo ║  ⏹️  停止方法: stop_monitoring.bat をダブルクリック                ║
echo ║                                                                    ║
echo ╚════════════════════════════════════════════════════════════════════╝
echo.

REM ===========================================
REM ログ監視オプション
REM ===========================================
set /p SHOW_LOGS=ログを表示しますか？ (y/n):
if /i "%SHOW_LOGS%"=="y" (
    echo.
    echo システムログを表示中... (終了するには Ctrl+C)
    echo ─────────────────────────────────────────────────────────────
    docker compose -f docker/docker-compose.yml logs -f
) else (
    echo.
    echo システムはバックグラウンドで動作中です。
    echo ウィンドウを閉じても監視は継続されます。
    echo.
    pause
)
