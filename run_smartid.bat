@echo off
echo ============================
echo   GTZ ID Studio - Starting App
echo ============================

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Install requirements if needed
if not exist ".installed" (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo. > .installed
)

REM Launch the app
python main.py

pause