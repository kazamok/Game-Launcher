@echo off
echo ==================================================
echo.
echo      Inno Setup Compiler for WoWLauncher
echo.
echo ==================================================
echo.
echo Starting Inno Setup command-line compiler (ISCC.exe)...
echo.

REM Define the path to the Inno Setup compiler
set INNO_SETUP_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

REM Check if the compiler exists at the default path
if not exist %INNO_SETUP_PATH% (
    echo Error: Inno Setup compiler not found at %INNO_SETUP_PATH%
    echo Please make sure Inno Setup is installed to the default location,
    echo or update the INNO_SETUP_PATH in this script.
    echo.
    pause
    exit /b
)

REM Run the Inno Setup compiler command
%INNO_SETUP_PATH% "setup.iss"

echo.
echo ==================================================
echo.
echo      Setup compilation finished.
echo.
echo ==================================================
echo Check the 'Output' folder for the new setup file.
echo If there were any errors, they will be displayed above.
echo.
pause
