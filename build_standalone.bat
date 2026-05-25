@echo off
chcp 65001 >nul
REM ============================================================
REM Fisherman 钓鱼独立 exe 一键构建脚本(M6 — SPEC §2.15)
REM
REM 用法:双击运行,或在终端 `build_standalone.bat`
REM 产物:dist\fisherman_fishing\fisherman_fishing.exe + 同级 dll/资源
REM 分发:整个 dist\fisherman_fishing\ 文件夹 zip 给最终用户
REM ============================================================

setlocal

cd /d "%~dp0"

echo.
echo [1/4] 同步依赖 (uv sync --group build)...
call uv sync --group build
if errorlevel 1 (
    echo 错误: uv sync 失败
    pause
    exit /b 1
)

echo.
echo [2/4] 清理上次产物 (build\ dist\fisherman_fishing\)...
if exist build rmdir /s /q build
if exist dist\fisherman_fishing rmdir /s /q dist\fisherman_fishing

echo.
echo [3/4] PyInstaller 打包 (onedir, 这一步约 1-3 分钟)...
call uv run --group build pyinstaller fishing_standalone.spec --noconfirm
if errorlevel 1 (
    echo 错误: PyInstaller 构建失败
    pause
    exit /b 1
)

echo.
echo [4/4] 检查产物...
if not exist dist\fisherman_fishing\fisherman_fishing.exe (
    echo 错误: 产物未生成 dist\fisherman_fishing\fisherman_fishing.exe
    pause
    exit /b 1
)
if not exist dist\fisherman_fishing\good_models\wow_fish.pt (
    echo 警告: 内置模型未打入 dist\fisherman_fishing\good_models\wow_fish.pt
    echo        请检查 fishing_standalone.spec 的 datas 配置
)

echo.
echo ============================================================
echo 构建成功!
echo   产物目录: %cd%\dist\fisherman_fishing\
echo   exe 路径: %cd%\dist\fisherman_fishing\fisherman_fishing.exe
echo.
echo 分发步骤:
echo   1. 把整个 dist\fisherman_fishing\ 文件夹打 zip
echo   2. 发给用户 → 用户解压 → 双击 fisherman_fishing.exe
echo.
echo 用户使用注意(详见 docs\standalone-build.md):
echo   - F11 启动 / F12 停止
echo   - 双屏游戏需在 UI 内点「选择区域」框选游戏窗口
echo   - Windows Defender 可能误报,选「允许」即可
echo ============================================================

pause
endlocal
