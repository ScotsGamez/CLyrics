@echo off
title Create Desktop Shortcut - CLyrics
cd /d "%~dp0"

echo Creating Desktop Shortcut for CLyrics (C (See) Lyrics)...
powershell -ExecutionPolicy Bypass -NoProfile -File "scripts\create_shortcut.ps1"
echo.
pause
