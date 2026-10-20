@echo off
title CLyrics (C (See) Lyrics)
cd /d "%~dp0"

:: Auto-create Desktop Shortcut on first run if it doesn't exist
if not exist "%USERPROFILE%\Desktop\CLyrics.lnk" (
    powershell -ExecutionPolicy Bypass -NoProfile -NonInteractive -WindowStyle Hidden -File "scripts\create_shortcut.ps1" >nul 2>nul
)

:: Check if pythonw exists to run silently without an unwanted terminal window
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw run.py
) else (
    start "" python run.py
)
