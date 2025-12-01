@echo off
title ChatCollect - Build EXE
cd /d "%~dp0"
color 0E

echo ========================================
echo   ChatCollect - EXE Builder
echo ========================================
echo.

echo Force closing running instances...
taskkill /F /IM "ChatCollect.exe" >nul 2>&1
taskkill /F /IM "Setup.exe" >nul 2>&1

echo Cleaning up previous builds...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "ChatCollect.spec" del "ChatCollect.spec"
if exist "Setup.spec" del "Setup.spec"

if exist "ChatCollect.exe" (
    del "ChatCollect.exe"
    if exist "ChatCollect.exe" (
        echo.
        echo ERROR: Cannot delete ChatCollect.exe. Is it still running?
        echo Please close the bot and try again.
        echo.
        pause
        exit /b 1
    )
)
if exist "Setup.exe" (
    del "Setup.exe"
    if exist "Setup.exe" (
        echo.
        echo ERROR: Cannot delete Setup.exe. Is it still running?
        echo Please close the setup tool and try again.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Building ChatCollect.exe...
echo.

REM Check for icon
set "ICON_PARAM=--icon=NONE"
set "DATA_PARAM="
if exist "exe_icon.ico" (
    echo Found custom icon: exe_icon.ico
    set "ICON_PARAM=--icon=exe_icon.ico"
    set "DATA_PARAM=--add-data "exe_icon.ico;.""
) else (
    echo No exe_icon.ico found in root folder. Using default icon.
)

REM Determine Python Command
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py"
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    ) else (
        echo ERROR: Python not found!
        pause
        exit /b 1
    )
)

echo Using %PY_CMD%...

REM Build ChatCollect
%PY_CMD% -m PyInstaller --clean --noconfirm --onefile --windowed --name "ChatCollect" %ICON_PARAM% %DATA_PARAM% ^
    --hidden-import "twitchio" ^
    --hidden-import "twitchio.ext.commands" ^
    --hidden-import "websockets" ^
    --hidden-import "PyQt5" ^
    --hidden-import "aiohttp" ^
    chatcollect_gui.py

echo.
echo Building Setup.exe...
echo.

REM Build Setup
%PY_CMD% -m PyInstaller --clean --noconfirm --onefile --windowed --name "Setup" %ICON_PARAM% %DATA_PARAM% ^
    --hidden-import "PyQt5" ^
    setup_gui.py

echo.
echo Moving executables to root folder...

if exist "dist\ChatCollect.exe" (
    move /Y "dist\ChatCollect.exe" "%~dp0ChatCollect.exe"
) else (
    echo ERROR: ChatCollect build failed!
)

if exist "dist\Setup.exe" (
    move /Y "dist\Setup.exe" "%~dp0Setup.exe"
) else (
    echo ERROR: Setup build failed!
)

echo.
echo Cleaning up build folders...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "ChatCollect.spec" del "ChatCollect.spec"
if exist "Setup.spec" del "Setup.spec"

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo ChatCollect.exe and Setup.exe are ready in this folder:
echo %~dp0
echo.
echo Press any key to close...
pause >nul
