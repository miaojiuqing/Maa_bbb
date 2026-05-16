# 解压完成后由 7-Zip SFX 的 RunProgram 调用；当前目录与脚本均在官方 7zSD 的「临时解压目录」内。
# 官方安装型 SFX 在退出后会删除该临时目录，因此由用户选择持久安装路径后复制文件并创建桌面快捷方式。

$ErrorActionPreference = "Stop"

function Show-InstallMessage {
    param(
        [string] $Text,
        [string] $Title,
        [ValidateSet('Error', 'Warning', 'Information')]
        [string] $Icon = 'Information'
    )
    $btn = [System.Windows.Forms.MessageBoxButtons]::OK
    $ico = switch ($Icon) {
        'Error' { [System.Windows.Forms.MessageBoxIcon]::Error }
        'Warning' { [System.Windows.Forms.MessageBoxIcon]::Warning }
        default { [System.Windows.Forms.MessageBoxIcon]::Information }
    }
    [System.Windows.Forms.MessageBox]::Show($Text, $Title, $btn, $ico) | Out-Null
}

function Show-InstallError {
    param([string] $Text, [string] $Title = "安装失败")
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        Show-InstallMessage -Text $Text -Title $Title -Icon Error
    }
    catch {
        $ws = New-Object -ComObject WScript.Shell
        [void] $ws.Popup($Text, 0, $Title, 16)
    }
}

try {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.Application]::EnableVisualStyles()

    $src = $PSScriptRoot

    $nameFile = Join-Path $src "sfx_shortcut_name.txt"
    $appName = "识宝小助手"
    if (Test-Path -LiteralPath $nameFile) {
        $fromFile = (Get-Content -LiteralPath $nameFile -Raw -Encoding UTF8).Trim()
        if (-not [string]::IsNullOrWhiteSpace($fromFile)) {
            $appName = $fromFile
        }
    }

    # FolderBrowserDialog 要求 SelectedPath 指向「已存在」的目录，否则会抛异常（蓝窗一闪、红字即退）。
    $localApp = [Environment]::GetFolderPath("LocalApplicationData")
    $programs = Join-Path $localApp "Programs"
    if (Test-Path -LiteralPath $programs) {
        $defaultInstall = $programs
    }
    else {
        $defaultInstall = $localApp
    }

    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "请选择 $appName 的安装目录（程序文件将解压到该文件夹内）"
    $dialog.UseDescriptionForTitle = $true
    $dialog.ShowNewFolderButton = $true
    $dialog.SelectedPath = $defaultInstall

    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Show-InstallMessage -Text "已取消安装。" -Title $appName -Icon Information
        exit 0
    }

    $installRoot = $dialog.SelectedPath.Trim()
    if ([string]::IsNullOrWhiteSpace($installRoot)) {
        exit 0
    }

    New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
    & robocopy.exe "$src" "$installRoot" /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    $robocode = $LASTEXITCODE
    if ($robocode -ge 8) {
        Show-InstallMessage -Text "复制安装文件失败（robocopy 退出码: $robocode）。" -Title $appName -Icon Error
        exit 1
    }

    $mfw = Get-ChildItem -Path $installRoot -Recurse -File -Filter "MFW.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if (-not $mfw) {
        Show-InstallMessage -Text "安装目录中未找到 MFW.exe，已跳过创建快捷方式。" -Title $appName -Icon Warning
        exit 0
    }

    $linkName = $appName
    if (-not $linkName.EndsWith(".lnk")) {
        $linkName = "$linkName.lnk"
    }

    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnkPath = Join-Path $desktop $linkName

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($lnkPath)
    $shortcut.TargetPath = $mfw.FullName
    $shortcut.WorkingDirectory = $mfw.DirectoryName
    $shortcut.Description = "MFW / Maa 助手"
    try {
        $shortcut.Save()
    }
    finally {
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($shortcut) | Out-Null
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null
    }

    Show-InstallMessage -Text "安装完成。`n`n程序目录：`n$installRoot`n`n桌面快捷方式：`n$lnkPath" -Title $appName -Icon Information
}
catch {
    $detail = $_.Exception.Message
    if ($_.InvocationInfo.PositionMessage) {
        $detail += "`n`n" + $_.InvocationInfo.PositionMessage
    }
    Show-InstallError -Text $detail -Title "安装失败"
    exit 1
}
