@echo off
title ChatCollect - Install Requirements
cd /d "%~dp0"
color 0B

echo ========================================
echo   ChatCollect - Dependency Installer
echo ========================================
echo.

REM Try using 'py' launcher first (most reliable on Windows)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Python detected via py launcher:
    py --version
    echo.
    echo Installing packages from requirements.txt...
    echo.
    py -m pip install --upgrade pip
    py -m pip install -r requirements.txt
    echo.
    echo ========================================
    echo   Installation Complete!
    echo ========================================
    echo.
    py -m pip show twitchio websockets PyQt5 pyinstaller
    echo.
    echo You can now run build_exe.bat
    echo.
    pause
    exit /b 0
)

REM If py launcher doesn't work, try python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Python detected:
    python --version
    echo.
    echo Installing packages from requirements.txt...
    echo.
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    echo.
    echo ========================================
    echo   Installation Complete!
    echo ========================================
    echo.
    python -m pip show twitchio websockets PyQt5 pyinstaller
    echo.
    echo You can now run build_exe.bat
    echo.
    pause
    exit /b 0
)

echo ERROR: Python not found! Please install Python 3.10+ and add it to PATH.
pause
exit /b 1
