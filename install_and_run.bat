@echo off
echo Setting up CQ Voice Keyer...

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt

echo Starting CQ Voice Keyer...
python main.py
pause
