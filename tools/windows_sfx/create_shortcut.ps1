# 解压完成后由 7-Zip SFX 的 RunProgram 调用；当前目录与脚本均在官方 7zSD 的「临时解压目录」内。
# 官方安装型 SFX 在退出后会删除该临时目录，因此必须先把文件复制到本机持久路径，再创建桌面快捷方式。

$ErrorActionPreference = "Stop"
$src = $PSScriptRoot
$installRoot = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Programs\Maa_bbb"
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
& robocopy.exe "$src" "$installRoot" /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
$robocode = $LASTEXITCODE
if ($robocode -ge 8) {
    throw "复制安装文件失败，robocopy 退出码: $robocode"
}

$mfw = Get-ChildItem -Path $installRoot -Recurse -File -Filter "MFW.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $mfw) {
    Write-Warning "未找到 MFW.exe，跳过创建快捷方式。"
    exit 0
}

$nameFile = Join-Path $installRoot "sfx_shortcut_name.txt"
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
