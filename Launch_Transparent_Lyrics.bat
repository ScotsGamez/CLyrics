@echo off
title Transparent Live Lyrics Overlay
cd /d "%~dp0"

:: Auto-create Desktop Shortcut on first run if it doesn't exist
if not exist "%USERPROFILE%\Desktop\Clyrics.lnk" (
    powershell -ExecutionPolicy Bypass -NoProfile -File "scripts\create_shortcut.ps1" >nul 2>nul
)

:: Check if pythonw exists to run silently without an ugly terminal window
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw run.py
) else (
    start "" python run.py
)
