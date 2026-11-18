@echo off
set "HOME=%USERPROFILE%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Instant.ps1"
