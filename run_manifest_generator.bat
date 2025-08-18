@echo off
echo ==================================================
echo.
echo      WoW Launcher Manifest Generator
echo.
echo ==================================================
echo.
echo This script will scan your WoW client's 'Data' folder
echo to create a file manifest with hashes.
echo This process may take several minutes depending on
echo your disk speed. Please be patient.
echo.
echo Press any key to start...
pause > nul
echo.
echo Starting scan...
echo.

REM Execute the Python script
python create_manifest.py

echo.
echo ==================================================
echo.
echo      Manifest generation finished.
echo.
echo ==================================================
echo The file 'config\manifest.json' has been created or updated.
echo If there were any errors, they will be displayed above.
echo.
pause
