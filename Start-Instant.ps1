$ErrorActionPreference = "Stop"

function Resolve-CutCutFFmpegDirectories {
    $pathFfmpeg = Get-Command ffmpeg.exe -CommandType Application -ErrorAction SilentlyContinue
    $pathFfprobe = Get-Command ffprobe.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($pathFfmpeg -and $pathFfprobe -and (Test-Path -LiteralPath $pathFfmpeg.Source -PathType Leaf) -and (Test-Path -LiteralPath $pathFfprobe.Source -PathType Leaf)) {
        return @((Split-Path -Parent $pathFfmpeg.Source), (Split-Path -Parent $pathFfprobe.Source) | Select-Object -Unique)
    }

    $custom = $env:CUTCUT_FFMPEG_DIR
    if ($custom -and (Test-Path -LiteralPath (Join-Path $custom "ffmpeg.exe") -PathType Leaf) -and (Test-Path -LiteralPath (Join-Path $custom "ffprobe.exe") -PathType Leaf)) {
        return @($custom)
    }
    return @()
}

function Enable-CutCutFFmpeg {
    $directories = @(Resolve-CutCutFFmpegDirectories)
    if ($directories.Count -eq 0) {
        throw "CutCut requires both ffmpeg.exe and ffprobe.exe. Install FFmpeg (for example, run 'winget install Gyan.FFmpeg'), then add the folder containing both executables to Windows PATH or set CUTCUT_FFMPEG_DIR to that folder."
    }
    foreach ($directory in $directories) {
        if ($env:PATH -split [IO.Path]::PathSeparator -notcontains $directory) {
            $env:PATH = "$directory$([IO.Path]::PathSeparator)$env:PATH"
        }
    }
}

$root = $PSScriptRoot
Set-Location $root
Enable-CutCutFFmpeg
$env:TEMP = Join-Path $root "temp"
$env:TMP = $env:TEMP
$env:CUTCUT_DATA = Join-Path $root "data"
$env:CUTCUT_MODELS = Join-Path $env:CUTCUT_DATA "models"
$env:CUTCUT_JOB_WORKERS = "2"
$python = Join-Path $root "runtime\python\python.exe"
if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw "Run Setup-Instant.bat first." }
New-Item -ItemType Directory -Force -Path $env:TEMP, (Join-Path $root "data\logs") | Out-Null
Write-Host "CutCut at http://127.0.0.1:8765. Ctrl+C stops it."
& $python -m studio.server
