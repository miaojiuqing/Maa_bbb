<#
.SYNOPSIS
  使用 7-Zip 官方 SFX 模块生成自解压 exe（载荷为 7z 格式，非 zip 容器；业界常用做法）。

.DESCRIPTION
  将 SourceDir 打包后与 7zSD.sfx、配置文本二进制拼接。
  解压完成后通过 RunProgram 调用 create_shortcut.ps1，可在桌面生成快捷方式。

.PARAMETER SourceDir
  待打包目录（通常为 CI 中的 install/）。

.PARAMETER OutputExe
  输出的 .exe 路径。

.PARAMETER DisplayName
  安装/解压界面标题与默认快捷方式名称（不含 .lnk）。
#>
param(
    [Parameter(Mandatory = $true)]
    [string] $SourceDir,

    [Parameter(Mandatory = $true)]
    [string] $OutputExe,

    [string] $DisplayName = "识宝小助手"
)

$ErrorActionPreference = "Stop"

$SourceDir = [System.IO.Path]::GetFullPath($SourceDir)
if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    throw "SourceDir 不存在或不是目录: $SourceDir"
}

$sevenZipDir = Join-Path ${env:ProgramFiles} "7-Zip"
$sevenZip = Join-Path $sevenZipDir "7z.exe"
$sfxGui = Join-Path $sevenZipDir "7zSD.sfx"
if (-not (Test-Path -LiteralPath $sevenZip)) {
    throw "未找到 7-Zip: $sevenZip。请先安装 7-Zip（例如 choco install 7zip.install -y）。"
}
if (-not (Test-Path -LiteralPath $sfxGui)) {
    throw "未找到 SFX 模块: $sfxGui（完整 7-Zip 安装才包含 7zSD.sfx）。"
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$stage = Join-Path ([System.IO.Path]::GetTempPath()) ("sfx_stage_" + [Guid]::NewGuid().ToString("N"))
$archive = $null
$configPath = $null
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    robocopy $SourceDir $stage /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy 失败，退出码: $LASTEXITCODE"
    }

    Copy-Item -LiteralPath (Join-Path $here "create_shortcut.ps1") -Destination (Join-Path $stage "create_shortcut.ps1") -Force
    $namePath = Join-Path $stage "sfx_shortcut_name.txt"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($namePath, $DisplayName, $utf8NoBom)

    $archive = Join-Path ([System.IO.Path]::GetTempPath()) ("sfx_payload_" + [Guid]::NewGuid().ToString("N") + ".7z")
    & $sevenZip a -t7z -mx=9 -mmt=on $archive "$stage\*"
    if ($LASTEXITCODE -ne 0) {
        throw "7z 压缩失败，退出码: $LASTEXITCODE"
    }

    $configPath = Join-Path ([System.IO.Path]::GetTempPath()) ("sfx_config_" + [Guid]::NewGuid().ToString("N") + ".txt")
    $run = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File .\create_shortcut.ps1'
    $configBody = @"
;!@Install@!UTF-8!
Title="$DisplayName"
BeginPrompt="将把程序解压到所选文件夹。`n解压完成后会在桌面创建快捷方式（若找到 MFW.exe）。`n`n是否继续？"
ExtractPathText="请选择安装目录："
ExtractTitle="解压"
GUIMode="1"
Progress="yes"
OverwriteMode="2"
RunProgram="hidcon:$run"
;!@InstallEnd@!
"@
    $utf8Bom = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllText($configPath, $configBody, $utf8Bom)

    $outFull = [System.IO.Path]::GetFullPath($OutputExe)
    $outDir = Split-Path -Parent $outFull
    if (-not [string]::IsNullOrEmpty($outDir) -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    cmd.exe /c "copy /b `"$sfxGui`" + `"$configPath`" + `"$archive`" `"$outFull`""
    if ($LASTEXITCODE -ne 0) {
        throw "copy /b 拼接 SFX 失败，退出码: $LASTEXITCODE"
    }
    Write-Host "已生成: $outFull"
}
finally {
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
    if ($archive) { Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue }
    if ($configPath) { Remove-Item -LiteralPath $configPath -Force -ErrorAction SilentlyContinue }
}
