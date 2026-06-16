@echo off
echo --- Verifying Python Installation ---

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Installing via Windows Winget...
    winget install Python.Python.3.11 --silent
    if %errorlevel% neq 0 (
        echo Error: Could not install Python automatically. Please install it manually from python.org.
        pause
        exit /b
    )
    echo Python installed successfully. Please restart this setup.bat file.
    pause
    exit /b
)

echo Python is already installed.
echo --- Running Library Setup ---
python install_libs.py

pause