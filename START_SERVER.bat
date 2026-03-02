@echo off
title Digital Mushayara — Server
color 0A

echo.
echo  ==========================================
echo    🪔  Digital Mushayara
echo  ==========================================
echo.

:: Install dependencies if needed
echo  Checking dependencies...
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing Flask...
    pip install flask flask-cors
)

echo.
echo  Starting server...
echo  Open your browser at: http://localhost:5000
echo.
echo  Press Ctrl+C to stop
echo  ==========================================
echo.

python "%~dp0server.py"

pause
