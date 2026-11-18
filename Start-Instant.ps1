$ErrorActionPreference="Stop"
$root=$PSScriptRoot; Set-Location $root
$env:TEMP="$root\temp"; $env:TMP=$env:TEMP
$env:CUTCUT_DATA="$root\data"; $env:CUTCUT_MODELS="$root\data\models"
$env:CUTCUT_JOB_WORKERS="2"
$ff='D:\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin'; $env:CUTCUT_FFMPEG_DIR=$ff; $env:PATH="$ff;$env:PATH"
$python="$root\runtime\python\python.exe"; if (!(Test-Path $python)) { throw "Run Setup-Instant.bat first." }
New-Item -ItemType Directory -Force -Path $env:TEMP,"$root\data\logs" | Out-Null
Write-Host "Instant at http://127.0.0.1:8765. Ctrl+C stops it."
& $python -m studio.server
