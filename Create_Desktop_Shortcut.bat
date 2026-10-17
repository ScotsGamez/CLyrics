@echo off
title Create Desktop Shortcut
cd /d "%~dp0"

echo Creating Desktop Shortcut for Transparent Live Lyrics Overlay...
powershell -ExecutionPolicy Bypass -NoProfile -File "scripts\create_shortcut.ps1"
echo.
pause
