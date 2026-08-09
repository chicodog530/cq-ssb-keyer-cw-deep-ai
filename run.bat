@echo off
if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Please run installer.bat first!
    pause
    exit /b 1
)

echo Starting CQ Voice Keyer...
call .venv\Scripts\activate
python main.py
