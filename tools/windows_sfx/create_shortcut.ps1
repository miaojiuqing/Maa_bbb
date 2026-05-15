# 解压完成后由 7-Zip SFX 的 RunProgram 调用；当前目录与脚本均在官方 7zSD 的「临时解压目录」内。
# 官方安装型 SFX 在退出后会删除该临时目录，因此由用户选择持久安装路径后复制文件并创建桌面快捷方式。

$ErrorActionPreference = "Stop"

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

$defaultInstall = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Programs\$appName"
if (-not (Test-Path -LiteralPath $defaultInstall)) {
    $defaultInstall = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Programs"
}

$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "请选择 $appName 的安装目录（程序文件将解压到该文件夹内）"
$dialog.UseDescriptionForTitle = $true
$dialog.ShowNewFolderButton = $true
$dialog.SelectedPath = $defaultInstall

if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
    [System.Windows.Forms.MessageBox]::Show(
        "已取消安装。",
        $appName,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
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
    [System.Windows.Forms.MessageBox]::Show(
        "复制安装文件失败（robocopy 退出码: $robocode）。",
        $appName,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
    exit 1
}

$mfw = Get-ChildItem -Path $installRoot -Recurse -File -Filter "MFW.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $mfw) {
    [System.Windows.Forms.MessageBox]::Show(
        "安装目录中未找到 MFW.exe，已跳过创建快捷方式。",
        $appName,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning) | Out-Null
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

[System.Windows.Forms.MessageBox]::Show(
    "安装完成。`n`n程序目录：`n$installRoot`n`n桌面快捷方式：`n$lnkPath",
    $appName,
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
