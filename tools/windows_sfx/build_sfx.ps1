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

function Find-SevenZipExe {
    foreach ($dir in @(
            (Join-Path ${env:ProgramFiles} "7-Zip"),
            (Join-Path ${env:ProgramFiles(x86)} "7-Zip")
        )) {
        $exe = Join-Path $dir "7z.exe"
        if (Test-Path -LiteralPath $exe) {
            return $exe
        }
    }
    $chocoBin = "C:\ProgramData\chocolatey\bin\7z.exe"
    if (Test-Path -LiteralPath $chocoBin) {
        return $chocoBin
    }
    $lib = "C:\ProgramData\chocolatey\lib"
    if (Test-Path -LiteralPath $lib) {
        Get-ChildItem -Path $lib -Directory -Filter "7zip*" -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                foreach ($rel in @("tools\7-Zip\7z.exe", "tools\7z.exe")) {
                    $p = Join-Path $_.FullName $rel
                    if (Test-Path -LiteralPath $p) {
                        return $p
                    }
                }
            }
    }
    $fromPath = (& where.exe 7z 2>$null | Select-Object -First 1)
    if ($fromPath -and (Test-Path -LiteralPath $fromPath)) {
        return $fromPath.Trim()
    }
    return $null
}

function Find-SevenZipSfx([string] $SevenZipExe) {
    $root = Split-Path -Parent $SevenZipExe
    $direct = Join-Path $root "7zSD.sfx"
    if (Test-Path -LiteralPath $direct) {
        return $direct
    }
    $hit = Get-ChildItem -LiteralPath $root -Recurse -Filter "7zSD.sfx" -File -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($hit) {
        return $hit.FullName
    }
    return $null
}

# Chocolatey 的 7zip.install 常不带 7zSD.sfx；从官网 Extra 包解压获取（需已有 7z.exe）
function Ensure-SevenZipSfx {
    param([string] $SevenZipExe)

    $existing = Find-SevenZipSfx -SevenZipExe $SevenZipExe
    if ($existing) {
        return @{ Sfx = $existing; Cleanup = $null }
    }

    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("7z_extra_" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $urls = @(
            "https://www.7-zip.org/a/7z2301-extra.7z",
            "https://www.7-zip.org/a/7z2408-extra.7z",
            "https://www.7-zip.org/a/7z2409-extra.7z",
            "https://www.7-zip.org/a/7z2500-extra.7z"
        )
        $lastErr = $null
        foreach ($url in $urls) {
            $dl = Join-Path $tmp ([System.IO.Path]::GetFileName($url))
            try {
                Invoke-WebRequest -Uri $url -OutFile $dl -UseBasicParsing
            }
            catch {
                $lastErr = $_
                continue
            }
            & $SevenZipExe x "$dl" "-o$tmp" -y | Out-Null
            if ($LASTEXITCODE -ne 0) {
                $lastErr = "7z x 退出码 $($LASTEXITCODE): $url"
                continue
            }
            $hit = Get-ChildItem -Path $tmp -Recurse -Filter "7zSD.sfx" -File -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($hit) {
                return @{ Sfx = $hit.FullName; Cleanup = $tmp }
            }
        }
        throw "无法从 7-zip.org 获取 7zSD.sfx（Chocolatey 版通常不含 SFX）。最后错误: $lastErr"
    }
    catch {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
        throw
    }
}

$sevenZip = Find-SevenZipExe
if (-not $sevenZip) {
    throw "未找到 7z.exe。请先安装 7-Zip（例如 choco install 7zip.install -y）。"
}

$sfxResolved = Ensure-SevenZipSfx -SevenZipExe $sevenZip
$sfxGui = $sfxResolved.Sfx
$sfxExtraCleanup = $sfxResolved.Cleanup

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
    if ($sfxExtraCleanup) { Remove-Item -LiteralPath $sfxExtraCleanup -Recurse -Force -ErrorAction SilentlyContinue }
}
