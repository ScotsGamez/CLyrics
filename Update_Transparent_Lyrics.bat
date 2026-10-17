@echo off
title Update Transparent Lyrics Overlay
cd /d "%~dp0"

echo ========================================================
echo   Updating Transparent Lyrics Overlay to Latest Version
echo ========================================================
echo.

git pull origin main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Git pull failed. Please check your internet connection or repository status.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Checking and updating Python dependencies...
pip install -r requirements.txt

echo.
echo ========================================================
echo   Update successfully completed!
echo   Run Launch_Transparent_Lyrics.bat to start the app.
echo ========================================================
echo.
pause
