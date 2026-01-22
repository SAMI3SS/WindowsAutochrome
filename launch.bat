@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Error: Python script failed. Press any key to exit...
    pause >nul
)
