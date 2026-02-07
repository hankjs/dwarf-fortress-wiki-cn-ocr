@echo off
chcp 65001 >nul
title Dwarf Fortress Wiki OCR Tool

:: 切换到脚本所在目录
cd /d "%~dp0"

echo ==========================================
echo  Dwarf Fortress Wiki OCR Tool
echo  矮人要塞 Wiki OCR 识别工具
echo ==========================================
echo.

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
