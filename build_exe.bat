@echo off
echo Building CQ Voice Keyer Executable...
.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name "CQ Voice Keyer" main.py
echo Build complete! Your executable is in the dist/ folder.
