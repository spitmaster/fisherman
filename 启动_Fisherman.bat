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
set "PYTHON_CMD=python"
set "REQUIREMENTS=%PROJECT_DIR%requirements.txt"

echo 当前工作目录: %PROJECT_DIR%

REM 检查Python是否安装
echo [1/4] 检查Python环境...
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未检测到Python！
    echo.
    echo 请先安装Python 3.8或更高版本：
    echo 下载地址: https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version') do set PYTHON_VERSION=%%i
echo ✓ 检测到 %PYTHON_VERSION%
echo.

REM 检查是否需要安装依赖
echo [2/4] 检查程序依赖...
%PYTHON_CMD% -c "import torch, PyQt5, ultralytics, cv2" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  检测到缺少依赖库
    echo.
    echo 正在自动安装依赖，这可能需要几分钟...
    echo.
    %PYTHON_CMD% -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    %PYTHON_CMD% -m pip install -r "%REQUIREMENTS%" -i https://pypi.tuna.tsinghua.edu.cn/simple
    
    if errorlevel 1 (
        echo.
        echo ❌ 依赖安装失败！
        echo.
        echo 可能的解决方法:
        echo 1. 检查网络连接
        echo 2. 手动运行: python -m pip install -r requirements.txt
        echo 3. 尝试使用国内镜像源
        pause
        exit /b 1
    )
    echo.
    echo ✓ 依赖安装完成
) else (
    echo ✓ 所有依赖已就绪
)
echo.

REM 检查Visual C++ Redistributable
echo [3/4] 检查系统组件...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  可能缺少 Visual C++ Redistributable
    echo.
    echo 如果程序运行失败，请安装：
    echo VC_redist.x64.exe (位于当前目录)
    pause
) else (
    echo ✓ Visual C++ 组件检测通过
)
echo.

REM 创建必要目录
if not exist "%PROJECT_DIR%logs" mkdir "%PROJECT_DIR%logs"
if not exist "%PROJECT_DIR%models" mkdir "%PROJECT_DIR%models"
if not exist "%PROJECT_DIR%training_data" mkdir "%PROJECT_DIR%training_data"

REM 启动程序
echo [4/4] 启动Fisherman程序...
echo.
echo ========================================
cd /d "%PROJECT_DIR%"
%PYTHON_CMD% main.py

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
    echo 3. 尝试重新安装依赖: python -m pip install -r requirements.txt --force-reinstall
    echo.
    pause
)
