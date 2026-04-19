@echo off
chcp 65001 >nul
title Fisherman 便携启动器

echo.
echo ========================================
echo   Fisherman 视觉自动化程序
echo ========================================
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"

echo 当前工作目录: %PROJECT_DIR%

REM 检查 uv 是否安装
echo [1/3] 检查 uv 环境...
uv --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未检测到 uv！
    echo.
    echo 请先安装 uv：
    echo 1. PowerShell 一键安装:
    echo    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    echo 2. 或通过 pip 安装:
    echo    pip install uv
    echo 3. 或查阅官方文档: https://docs.astral.sh/uv/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('uv --version') do set UV_VERSION=%%i
echo ✓ 检测到 %UV_VERSION%
echo.

REM 同步依赖（自动创建 .venv 并安装 pyproject.toml 中声明的依赖）
echo [2/3] 同步项目依赖...
cd /d "%PROJECT_DIR%"
uv sync
if errorlevel 1 (
    echo.
    echo ❌ 依赖同步失败！
    echo.
    echo 可能的解决方法:
    echo 1. 检查网络连接
    echo 2. 手动运行: uv sync --verbose
    echo 3. 清理环境后重试: rmdir /s /q .venv ^&^& uv sync
    pause
    exit /b 1
)
echo ✓ 依赖同步完成
echo.

REM 创建必要目录
if not exist "%PROJECT_DIR%logs" mkdir "%PROJECT_DIR%logs"
if not exist "%PROJECT_DIR%models" mkdir "%PROJECT_DIR%models"
if not exist "%PROJECT_DIR%training_data" mkdir "%PROJECT_DIR%training_data"

REM 启动程序
echo [3/3] 启动 Fisherman 程序...
echo.
echo ========================================
uv run python main.py

REM 如果程序异常退出，显示错误信息
if errorlevel 1 (
    echo.
    echo ========================================
    echo 程序异常退出
    echo ========================================
    echo.
    echo 请检查以下内容:
    echo 1. 查看日志文件: %PROJECT_DIR%logs\fisherman.log
    echo 2. 确保已安装 Visual C++ Redistributable
    echo 3. 尝试重建环境: rmdir /s /q .venv ^&^& uv sync
    echo.
    pause
)
