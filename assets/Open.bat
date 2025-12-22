:: =====================================================
:: 识宝小助手——崩坏3 启动检查器（Honkai Impact 3 Launcher）
:: 功能：
::   - 若 BH3.exe 已在运行（有窗口）：
::       → 不做任何操作，5秒后静默退出
::   - 若 BH3.exe 未运行：
::       1. 关闭 MFAAvalonia.exe（避免干扰）
::       2. 启动 BH3.exe
::       3. 等待窗口出现
::       4. 等待10秒确保游戏加载完成
::       5. 再次关闭残留 MAA 进程 → 启动新实例
:: 日志：Open.log（位于 D:\aWa\bbb\maa_bbb\）
:: =====================================================
@echo off
setlocal enabledelayedexpansion

:: ========== 用户配置区 ==========
set "GAME_EXE=E:\MHY\miHoYo Launcher\games\Honkai Impact 3rd Game\BH3.exe"
set "BH3_PROCESS_NAME=BH3"                     :: ← 根据任务管理器中的进程名调整（如 BH3_CN）
set "MAA_EXE=D:\aWa\bbb\maa_bbb\MFAAvalonia.exe"
set "LOG_FILE=D:\aWa\bbb\maa_bbb\Open.log"
:: ==============================

:: 初始化日志
call :log "=== 识宝小助手启动检查器开始运行 ==="

:: 检查游戏路径是否存在
if not exist "%GAME_EXE%" (
    call :log "[-] 错误：游戏路径不存在！"
    call :log "    %GAME_EXE%"
    pause
    exit /b
)

:: 检查 MFAAvalonia.exe 文件是否存在
if not exist "%MAA_EXE%" (
    call :log "[-] 警告：MFAAvalonia.exe 未找到，将无法启动识宝小助手。"
    call :log "    %MAA_EXE%"
    set "maa_missing=1"
)

:check_window
call :log "[*] 正在检测崩坏3（进程名: %BH3_PROCESS_NAME%）是否已在运行..."
powershell -Command "$found = $false; Get-Process -Name '%BH3_PROCESS_NAME%' -ErrorAction SilentlyContinue | ForEach-Object { if ($_.MainWindowHandle -ne 0) { $found = $true } }; if ($found) { exit 0 } else { exit 1 }" >nul 2>&1

if %errorlevel% equ 0 (
    if defined launched (
        :: 是我们刚启动的游戏 → 等待10秒后重启 MAA
        call :log "[*] 崩坏3窗口已检测到，正在等待10秒（确保游戏完全加载）..."
        timeout /t 10 /nobreak >nul

        if not defined maa_missing (
            :: 启动前清理可能残留的 MFAAvalonia.exe
            call :log "[*] 正在关闭可能存在的识宝小助手进程..."
            taskkill /f /im MFAAvalonia.exe >nul 2>&1
            timeout /t 1 /nobreak >nul

            call :log "[*] 启动识宝小助手..."
            start "" "%MAA_EXE%"

            timeout /t 1 /nobreak >nul

            :: 验证是否成功启动
            tasklist /fi "imagename eq MFAAvalonia.exe" 2>nul | find /i "MFAAvalonia.exe" >nul
            if %errorlevel% equ 0 (
                call :log "[+] 识宝小助手已成功启动。"
            ) else (
                call :log "[-] 警告：识宝小助手未能启动。"
            )
        )
        call :log "[+] 崩坏3已成功启动并完成初始化，脚本将在5秒后关闭。"
        timeout /t 5 /nobreak >nul
    ) else (
        :: 游戏原本就在运行 → 完全静默退出
        call :log "[+] 检测到崩坏3已在运行，脚本将静默退出（5秒后）。"
        timeout /t 5 /nobreak >nul
    )
    call :log "=== 脚本正常退出 ==="
    exit /b
)

:: 如果没找到 BH3 窗口，且尚未启动，则执行启动流程
if not defined launched (
    call :log "[-] 未检测到崩坏3运行，正在尝试启动游戏..."

    :: 启动游戏前关闭 MAA，避免干扰
    taskkill /f /im MFAAvalonia.exe >nul 2>&1

    start "" "%GAME_EXE%"
    set "launched=1"
    call :log "[*] 已发送启动指令，正在等待游戏窗口出现..."
)

timeout /t 2 /nobreak >nul
goto :check_window


:: ==============================
:: 日志函数
:: ==============================
:log
set "msg=%~1"
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set "d=%%c-%%a-%%b"
)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
    set "t=%%a:%%b"
)
if "%t:~-2%"=="AM" set "t=!t:~0,-3!"
if "%t:~-2%"=="PM" (
    set "hour=!t:~0,2!"
    if !hour! lss 12 set /a hour+=12
    set "t=!hour!!t:~2,-3!"
)
echo [%d% %t%] %msg%
echo [%d% %t%] %msg% >> "%LOG_FILE%"
exit /b