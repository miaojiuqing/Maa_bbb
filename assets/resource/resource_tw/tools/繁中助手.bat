@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYW="
where pythonw >nul 2>nul && set "PYW=pythonw"
where py      >nul 2>nul && if not defined PYW set "PYW=py -3"
where python  >nul 2>nul && if not defined PYW set "PYW=python"

if not defined PYW (
    echo.
    echo [!] 没找到 Python。请先安装 Python 3（https://www.python.org/downloads/）
    echo     安装时记得勾选 "Add python.exe to PATH"。
    echo.
    pause
    exit /b 1
)

start "" %PYW% "tw_helper.py"
