@echo off
echo ==================================================
echo.
echo      WoWLauncher Executable Builder (.exe)
echo.
echo ==================================================
echo.
echo Starting PyInstaller to build WoWLauncher.exe...
echo This may take a few moments.
echo.

REM Run the PyInstaller build command
pyinstaller WoWLauncher.spec > build.log 2>&1

echo.
echo ==================================================
echo.
echo      Build process finished.
echo.
echo ==================================================
echo Check the 'dist' folder for the new WoWLauncher.exe.
echo If there were any errors, they will be displayed above.
echo.
pause
