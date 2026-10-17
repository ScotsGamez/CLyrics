@echo off
title Transparent Live Lyrics Overlay
cd /d "%~dp0"

:: Check if pythonw exists to run without an ugly terminal window
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw run.py
) else (
    start "" python run.py
)
