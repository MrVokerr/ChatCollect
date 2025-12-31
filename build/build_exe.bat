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

echo Cleaning up previous builds...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "ChatCollect.spec" del "ChatCollect.spec"

if exist "..\ChatCollect.exe" (
    del "..\ChatCollect.exe"
    if exist "..\ChatCollect.exe" (
        echo.
        echo ERROR: Cannot delete ..\ChatCollect.exe. Is it still running?
        echo Please close the bot and try again.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Building ChatCollect.exe...
echo.

REM Check for icon in current folder
set "ICON_PARAM=--icon=NONE"
set "DATA_PARAM="
if exist "exe_icon.ico" (
    echo Found custom icon: exe_icon.ico
    set "ICON_PARAM=--icon=exe_icon.ico"
    set "DATA_PARAM=--add-data "exe_icon.ico;.""
) else (
    echo No exe_icon.ico found in build folder. Using default icon.
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
    "chatcollect_gui.py"

echo.
echo Moving executables to root folder...

if exist "dist\ChatCollect.exe" (
    move /Y "dist\ChatCollect.exe" "..\ChatCollect.exe"
) else (
    echo ERROR: ChatCollect build failed!
)

echo.
echo Cleaning up build folders...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "ChatCollect.spec" del "ChatCollect.spec"

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo ChatCollect.exe is ready in the root folder.
echo.
echo Press any key to close...
exit
