@echo off
title Update CLyrics (C (See) Lyrics)
cd /d "%~dp0"

echo ========================================================
echo   Updating CLyrics (C (See) Lyrics) to Latest Version
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
echo Refreshing desktop shortcut...
powershell -ExecutionPolicy Bypass -NoProfile -File "scripts\create_shortcut.ps1"

echo.
echo ========================================================
echo   Update successfully completed!
echo   Relaunching CLyrics...
echo ========================================================
echo.

timeout /t 1 /nobreak >nul
call launch.bat
exit /b 0
