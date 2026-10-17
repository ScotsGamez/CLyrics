@echo off
title Setup - Transparent Live Lyrics Overlay
cd /d "%~dp0"

echo ========================================================
echo   Transparent Live Lyrics Overlay - Quick Setup
echo ========================================================
echo.

echo [1/2] Installing required Python packages...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] pip install failed. Please make sure Python and pip are installed and added to PATH.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Generating Desktop Shortcut...
powershell -ExecutionPolicy Bypass -NoProfile -File "scripts\create_shortcut.ps1"

echo.
echo ========================================================
echo   Setup Complete!
echo   You can launch the overlay anytime from your Desktop
echo   shortcut or by running Launch_Transparent_Lyrics.bat.
echo ========================================================
echo.
pause
