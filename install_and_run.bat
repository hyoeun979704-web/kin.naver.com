@echo off
cd /d "%~dp0"
title Naver Kin Monitor - Auto Install

echo ============================================
echo   Naver Kin Monitor - Auto Install
echo ============================================
echo.

:: --- 1. Check Python ---
echo [1/4] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    py --version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Python is not installed.
        echo.
        echo    Download Python 3.10+ from:
        echo    https://www.python.org/downloads/
        echo.
        echo    IMPORTANT: Check "Add Python to PATH" during install!
        echo.
        echo    Run this file again after installing Python.
        echo.
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VER=%%i
echo    [OK] %PYTHON_VER% found

:: --- 2. Virtual environment ---
echo.
echo [2/4] Setting up virtual environment...
if not exist "venv" (
    echo    Creating venv... (first time only)
    %PYTHON_CMD% -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo    [OK] venv created
) else (
    echo    [OK] Using existing venv
)

call venv\Scripts\activate.bat

:: --- 3. Install packages ---
echo.
echo [3/4] Installing packages...

pip show playwright >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo    Installing packages... (may take a few minutes)
    pip install -r requirements.txt --quiet
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Package install failed
        pause
        exit /b 1
    )
    echo    [OK] Python packages installed

    echo    Installing Playwright browser... (may take a few minutes)
    playwright install chromium
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Playwright browser install failed
        pause
        exit /b 1
    )
    echo    [OK] Playwright browser installed
) else (
    echo    [OK] Packages already installed (skip)
)

:: --- 4. Check credentials.json ---
if not exist "credentials.json" (
    echo.
    echo [ERROR] credentials.json not found!
    echo    Please get the file from your team and place it in this folder.
    echo.
    pause
    exit /b 1
)

:: --- 5. Run ---
echo.
echo ============================================
echo   [OK] Setup complete! Starting bot...
echo ============================================
echo.

python naver_kin_monitor.py

echo.
echo Bot execution finished.
pause
