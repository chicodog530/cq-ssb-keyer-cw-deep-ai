@echo off
echo ==============================================
echo   CQ Voice Keyer - Installer
echo ==============================================
echo.
echo Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found! Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment (.venv)...
    python -m venv .venv
) else (
    echo Virtual environment already exists.
)

echo.
echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt

echo.
echo ==============================================
echo   Installation Complete!
echo ==============================================
echo You can now double-click "run.bat" to start the application.
pause
