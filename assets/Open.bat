:: =====================================================
:: 识宝小助手——崩坏3 启动检查器（Honkai Impact 3 Launcher）
:: 功能：
::   - 若游戏未运行：
::       1. 关闭 MFAAvalonia.exe
::       2. 启动 BH3.exe
::       3. 等待窗口出现
::       4. 重启 MFAAvalonia.exe
::       5. 验证 MAA 是否成功启动，并提示
::   - 若游戏已在运行：
::       1. 关闭 MFAAvalonia.exe（避免干扰）
::       2. 不启动游戏，直接退出
:: 使用前请修改 GAME_EXE 路径
:: =====================================================
@echo off
setlocal enabledelayedexpansion

:: ========== 用户配置区 ==========
set "GAME_EXE=E:\MHY\miHoYo Launcher\games\Honkai Impact 3rd Game\BH3.exe"
set "MAA_EXE=%~dp0MFAAvalonia.exe"
:: ==============================

:: 检查游戏路径
if not exist "%GAME_EXE%" (
    echo [-] 错误：游戏路径不存在！
    echo     %GAME_EXE%
    pause
    exit /b
)

:: 检查 MAA 文件是否存在
if not exist "%MAA_EXE%" (
    echo [-] 警告：MFAAvalonia.exe 未找到，将无法重启识宝小助手。
    echo     %MAA_EXE%
    set "maa_missing=1"
)

:check_window
echo [*] 正在查找窗口...
powershell -Command "$found = $false; Get-Process | ForEach-Object { if ($_.MainWindowTitle -ne '') { if ($_.MainWindowTitle -like '*崩坏3*' -or $_.MainWindowTitle -like '*Honkai Impact 3*') { $found = $true } } }; if ($found) { exit 0 } else { exit 1 }" >nul 2>&1

if %errorlevel% equ 0 (
    if defined launched (
        :: 我们刚启动的游戏 → 重启并验证 MAA
        if not defined maa_missing (
            echo [*] 启动窗口成功，正在尝试重启识宝小助手...
            start "" "%MAA_EXE%"

            :: 等待1秒让进程启动
            timeout /t 1 /nobreak >nul

            :: 检查 MAA 是否真的在运行
            tasklist /fi "imagename eq MFAAvalonia.exe" 2>nul | find /i "MFAAvalonia.exe" >nul
            if %errorlevel% equ 0 (
                echo [+] 识宝小助手已成功重启。
            ) else (
                echo [-] 警告：识宝小助手未能启动。
            )
        )
        echo [+] 成功启动崩坏3，将在5秒后关闭本窗口。
        timeout /t 5 /nobreak >nul
    ) else (
        :: 游戏原本就在运行 → 安全起见，关闭 MAA 避免冲突
        echo [+] 检测到游戏已在运行，正在关闭识宝小助手（避免干扰）...
        taskkill /f /im MFAAvalonia.exe >nul 2>&1
        echo [+] 已关闭识宝小助手，10秒后退出。
        timeout /t 10 /nobreak >nul
    )
    exit /b
)

:: 如果没找到窗口，且尚未启动，则执行启动流程
if not defined launched (
    echo [-] 未查找到窗口，正在尝试根据路径启动游戏...

    :: 关闭现有的 MFAAvalonia.exe（静默）
    taskkill /f /im MFAAvalonia.exe >nul 2>&1

    :: 启动游戏
    start "" "%GAME_EXE%"
    set "launched=1"
    echo [*] 启动指令已发送，正在等待游戏窗口出现...
)

:: 等待2秒后重试（最多约60秒）
timeout /t 2 /nobreak >nul
goto :check_window