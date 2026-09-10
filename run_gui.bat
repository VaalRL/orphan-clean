@echo off
cd /d "%~dp0"
if exist "orphan-clean.exe" (
    start "" "orphan-clean.exe"
    exit
)
python -m orphanclean.gui
pause
