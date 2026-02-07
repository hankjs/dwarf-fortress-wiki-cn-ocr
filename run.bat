@echo off
chcp 65001 >nul
title Dwarf Fortress Wiki OCR Tool (Interactive)

:: 切换到脚本所在目录
cd /d "%~dp0"

echo ==========================================
echo  Dwarf Fortress Wiki OCR Tool
echo  矮人要塞 Wiki OCR 识别工具
echo ==========================================
echo.

:: 询问是否使用代理
echo 是否需要使用代理？
echo.
echo 1. 不使用代理 (直连)
echo 2. Clash 代理 (127.0.0.1:7890)
echo 3. V2Ray/V2RayN 代理 (127.0.0.1:10809)
echo 4. 自定义代理
echo.
set /p PROXY_CHOICE="请选择 (1-4): "

:: 默认
set NO_PROXY=localhost,127.0.0.1
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890

if "%PROXY_CHOICE%"=="1" (
    echo [模式] 直连模式（无代理）
    set HTTP_PROXY=""
    set HTTPS_PROXY=""
    echo.
    goto :run_app
)

if "%PROXY_CHOICE%"=="2" (
    set HTTP_PROXY=http://127.0.0.1:7890
    set HTTPS_PROXY=http://127.0.0.1:7890
    echo [代理] Clash 代理: %HTTP_PROXY%
    echo.
    goto :run_app
)

if "%PROXY_CHOICE%"=="3" (
    set HTTP_PROXY=http://127.0.0.1:10809
    set HTTPS_PROXY=http://127.0.0.1:10809
    echo [代理] V2Ray/V2RayN 代理: %HTTP_PROXY%
    echo.
    goto :run_app
)

if "%PROXY_CHOICE%"=="4" (
    echo.
    set /p CUSTOM_PROXY="请输入代理地址 (例如: http://127.0.0.1:7890): "
    set HTTP_PROXY=%CUSTOM_PROXY%
    set HTTPS_PROXY=%CUSTOM_PROXY%
    echo [代理] 自定义代理: %HTTP_PROXY%
    echo.
    goto :run_app
)

echo [警告] 无效选择，使用Clash模式
echo.

:run_app
:: 设置不使用代理的地址
set NO_PROXY=localhost,127.0.0.1

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确保 Python 已安装并添加到环境变量
    pause
    exit /b 1
)

:: 运行主程序
echo 正在启动程序...
python src\ocr_tool.py

if errorlevel 1 (
    echo.
    echo [错误] 程序运行失败
    pause
)
