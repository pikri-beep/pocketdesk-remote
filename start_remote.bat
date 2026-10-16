@echo off
chcp 65001 >nul
title PocketDesk Remote v2.0 - Server Launcher
cd /d "%~dp0"

echo ======================================================================
echo           POCKETDESK REMOTE v2.0 - WINDOWS AUTOMATION SERVER
echo ======================================================================
echo.

:: 1. Periksa ketersediaan Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di sistem Windows Anda!
    echo Silakan install Python 3.10+ dari https://www.python.org/
    echo Pastikan mencentang kotak "Add Python to PATH" saat instalasi.
    echo.
    pause
    exit /b 1
)

:: 2. Periksa & Install Dependensi
echo [1/2] Memeriksa dependensi requirements.txt...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [INFO] Menjalankan instalasi dependensi lengkap...
    pip install -r requirements.txt
)

:: 3. Jalankan Server PocketDesk Remote
echo.
echo [2/2] Meluncurkan server backend FastAPI & WebSockets...
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [PERINGATAN] Server berhenti atau terjadi error.
    pause
)
