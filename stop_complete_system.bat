@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════════════════════════════╗
echo ║                     STM-2 Complete System Shutdown                ║
echo ╚════════════════════════════════════════════════════════════════════╝
echo.

REM ===========================================
REM 停止確認
REM ===========================================
echo 🛑 STM-2 監視システムを完全停止します。
echo.
echo 停止対象:
echo   • Docker コンテナ (InfluxDB, Grafana)
echo   • GUI アプリケーション
echo   • バックグラウンドプロセス
echo.
set /p CONFIRM=本当に停止しますか？ (y/N):
if /i not "%CONFIRM%"=="y" (
    echo.
    echo 停止をキャンセルしました。
    pause
    exit /b 0
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo                         停止処理開始
echo ═══════════════════════════════════════════════════════════════
echo.

REM ===========================================
REM GUI アプリケーション終了
REM ===========================================
echo [STEP 1/4] GUI アプリケーション終了中...

tasklist /FI "WINDOWTITLE eq STM-2 GUI*" /FO CSV | findstr "python" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    taskkill /F /FI "WINDOWTITLE eq STM-2 GUI*" >nul 2>&1
    echo         ✓ GUI アプリケーション終了完了
) else (
    echo         ℹ GUI アプリケーションは動作していません
)

REM Python プロセスで gui_app.py を実行中のものを終了
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr "python"') do (
    wmic process where "ProcessId=%%~i and CommandLine like '%%gui_app.py%%'" delete >nul 2>&1
)

REM ===========================================
REM Docker コンテナ停止
REM ===========================================
echo [STEP 2/4] Docker コンテナ停止中...

REM Docker が動作しているかチェック
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo         ℹ Docker Engine が動作していません
    goto :skip_docker
)

REM STM-2 関連コンテナの確認と停止
docker compose -f docker/docker-compose.yml ps -q >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo         STM-2 コンテナを停止中...
    docker compose -f docker/docker-compose.yml down
    if %ERRORLEVEL% equ 0 (
        echo         ✓ STM-2 コンテナ停止完了
    ) else (
        echo         ⚠ 一部コンテナの停止に失敗しました
    )
) else (
    echo         ℹ STM-2 コンテナは動作していません
)

:skip_docker

REM ===========================================
REM 一時ファイル・ログクリーンアップ
REM ===========================================
echo [STEP 3/4] 一時ファイルクリーンアップ中...

REM Python キャッシュファイル削除
if exist "src\__pycache__" (
    rmdir /s /q "src\__pycache__" >nul 2>&1
    echo         ✓ Python キャッシュファイル削除完了
)

REM 一時ログファイル削除
if exist "*.tmp" (
    del /q "*.tmp" >nul 2>&1
    echo         ✓ 一時ファイル削除完了
)

echo         ✓ クリーンアップ完了

REM ===========================================
REM ポート解放確認
REM ===========================================
echo [STEP 4/4] ポート解放確認中...

netstat -ano | findstr ":3000" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo         ⚠ ポート 3000 がまだ使用中です
    echo         (Grafana が完全に停止するまで少し時間がかかる場合があります)
) else (
    echo         ✓ ポート 3000 解放済み
)

netstat -ano | findstr ":8086" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo         ⚠ ポート 8086 がまだ使用中です
    echo         (InfluxDB が完全に停止するまで少し時間がかかる場合があります)
) else (
    echo         ✓ ポート 8086 解放済み
)

REM ===========================================
REM 停止完了メッセージ
REM ===========================================
echo.
echo ╔════════════════════════════════════════════════════════════════════╗
echo ║                      🏁 停止処理完了！ 🏁                          ║
echo ╠════════════════════════════════════════════════════════════════════╣
echo ║                                                                    ║
echo ║  ✅ すべてのSTM-2監視システムが正常に停止されました                   ║
echo ║                                                                    ║
echo ║  📝 停止されたコンポーネント:                                        ║
echo ║     • GUI アプリケーション                                          ║
echo ║     • Docker コンテナ (InfluxDB, Grafana)                        ║
echo ║     • バックグラウンドプロセス                                       ║
echo ║                                                                    ║
echo ║  🔄 再起動方法:                                                     ║
echo ║     start_complete_system.bat をダブルクリック                     ║
echo ║                                                                    ║
echo ║  💾 注意事項:                                                       ║
echo ║     データは保持されています（次回起動時に利用可能）                  ║
echo ║                                                                    ║
echo ╚════════════════════════════════════════════════════════════════════╝
echo.

REM ===========================================
REM オプション: Docker Desktop 終了
REM ===========================================
set /p STOP_DOCKER=Docker Desktop も終了しますか？ (y/N):
if /i "%STOP_DOCKER%"=="y" (
    echo.
    echo Docker Desktop 終了中...
    taskkill /F /IM "Docker Desktop.exe" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo         ✓ Docker Desktop 終了完了
    ) else (
        echo         ℹ Docker Desktop は既に終了しているか、終了権限がありません
    )
    echo.
) else (
    echo.
    echo Docker Desktop は起動したままです。
    echo （他のDockerアプリケーションで使用中の可能性があります）
    echo.
)

echo システムの完全停止が完了しました。
echo このウィンドウを閉じても構いません。
echo.
pause
