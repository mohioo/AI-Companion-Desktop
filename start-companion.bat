@echo off
title Desktop Companion Launcher
echo ===================================================
echo     Verifying Environment and Launching Pet...
echo ===================================================

:: 1. VERIFY AND INSTALL PYTHON
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [SYSTEM] Python is missing! Initializing native Windows installation...
    winget install Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo [ERROR] Automatic installation failed. Please download Python 3.11 manually from python.org.
        pause
        exit /b
    )
    echo [SYSTEM] Python installed successfully! Please re-run this shortcut.
    pause
    exit /b
)

:: 2. UPGRADE PIP TO PREVENT PACKAGING FAILS
python -m pip install --upgrade pip --quiet >nul 2>&1

:: 3. SCAN AND INSTALL MISSING PACKAGES EN MASSE
if not exist requirements.txt (
    echo [WARNING] requirements.txt missing. Creating configuration automatically...
    (
    echo PyQt5
    echo feedparser
    echo edge-tts
    echo flask
    ) > requirements.txt
)

echo [SYSTEM] Verifying system libraries...
python -m pip install --upgrade -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Library sync failed. Check your internet connection.
    pause
    exit /b
)

:: 4. FIRE UP THE DASHBOARD AND PET IMMEDIATELY 
echo [SUCCESS] Everything looks perfect. Waking up avatar...
cls
start /b python main.py

exit