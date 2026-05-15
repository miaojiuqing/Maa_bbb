# 解压完成后由 7-Zip SFX 的 RunProgram 调用；工作目录为解压目标目录。
# 在桌面创建指向 MFW.exe 的快捷方式（若存在多个则取第一个）。

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$mfw = Get-ChildItem -Path $root -Recurse -File -Filter "MFW.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $mfw) {
    Write-Warning "未找到 MFW.exe，跳过创建快捷方式。"
    exit 0
}

$nameFile = Join-Path $root "sfx_shortcut_name.txt"
if (Test-Path -LiteralPath $nameFile) {
    $linkName = (Get-Content -LiteralPath $nameFile -Raw -Encoding UTF8).Trim()
}
if ([string]::IsNullOrWhiteSpace($linkName)) {
    $linkName = "识宝小助手"
}
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

Write-Host "已创建快捷方式: $lnkPath -> $($mfw.FullName)"
