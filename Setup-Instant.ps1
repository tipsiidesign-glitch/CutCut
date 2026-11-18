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
        throw "CutCut requires both ffmpeg.exe and ffprobe.exe. Install FFmpeg (for example, run 'winget install Gyan.FFmpeg'), then add the folder containing both executables to Windows PATH or set CUTCUT_FFMPEG_DIR to that folder. Restart this script after changing PATH."
    }
    foreach ($directory in $directories) {
        if ($env:PATH -split [IO.Path]::PathSeparator -notcontains $directory) {
            $env:PATH = "$directory$([IO.Path]::PathSeparator)$env:PATH"
        }
    }
}

$root = $PSScriptRoot
Enable-CutCutFFmpeg
$env:TEMP = Join-Path $root "temp"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $root "cache\pip"
New-Item -ItemType Directory -Force -Path $env:TEMP, $env:PIP_CACHE_DIR, (Join-Path $root "downloads"), (Join-Path $root "runtime\python") | Out-Null
$python = Join-Path $root "runtime\python\python.exe"
if (!(Test-Path -LiteralPath $python -PathType Leaf)) {
    Invoke-WebRequest "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -OutFile (Join-Path $root "downloads\python.zip")
    Expand-Archive (Join-Path $root "downloads\python.zip") (Join-Path $root "runtime\python") -Force
    @("python311.zip", ".", "Lib\site-packages", "..\..", "import site") | Set-Content (Join-Path $root "runtime\python\python311._pth")
    New-Item -ItemType Directory -Force -Path (Join-Path $root "runtime\python\Lib\site-packages") | Out-Null
    Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile (Join-Path $root "downloads\get-pip.py")
    & $python (Join-Path $root "downloads\get-pip.py")
}
$env:CUTCUT_DATA = Join-Path $root "data"
$env:CUTCUT_MODELS = Join-Path $env:CUTCUT_DATA "models"
& $python -m pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE) { throw "Python dependencies failed." }
New-Item -ItemType Directory -Force -Path (Join-Path $root "data\logs") | Out-Null
Write-Host "Setup complete. Run Start-Instant.bat." -ForegroundColor Green
