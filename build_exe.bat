@echo off
echo ==============================================
echo   Building CQ Voice Keyer
echo ==============================================

echo [1/2] Compiling Python Code with PyInstaller...
.venv\Scripts\pyinstaller --noconfirm "CQ Voice Keyer.spec"
if errorlevel 1 (
    echo [ERROR] PyInstaller failed!
    pause
    exit /b 1
)

echo [2/2] Building Single Setup Executable (Inno Setup)...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
    echo.
    echo Build complete! Your installer is in the "installer_out" folder.
) else (
    echo.
    echo [WARNING] Inno Setup 6 was not found in the default installation path.
    echo The raw compiled application is in the "dist\CQ Voice Keyer" folder.
    echo To build the final Setup.exe, install Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo Then, right-click "setup.iss" and select "Compile".
)
pause
