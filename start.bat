@echo off
REM Epic Estimation System - Quick Start Script for Windows
REM This script will install dependencies and start both backend and frontend

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Epic Estimation System - Quick Start
echo ========================================
echo.

cd /d "%~dp0"

REM Check Python
echo [1/6] Checking Python installation...
py -3 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 not found. Please install Python 3.12
    pause
    exit /b 1
)
echo ✓ Python found

REM Check Node.js
echo [2/6] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Node.js not found. Frontend will not run.
    echo Please install Node.js 18+ from https://nodejs.org/
    timeout /t 5
) else (
    echo ✓ Node.js found
)

REM Setup Backend
echo [3/6] Setting up backend...
cd backend

if not exist venv (
    echo Creating virtual environment...
    py -3 -m venv venv
)

call venv\Scripts\activate.bat

echo Installing Python dependencies (this may take a few minutes)...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)
echo ✓ Backend dependencies installed

cd ..

REM Setup Frontend
echo [4/6] Setting up frontend...
cd frontend

if not exist node_modules (
    echo Installing Node dependencies (this may take a few minutes)...
    call npm install >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Failed to install Node dependencies
    ) else (
        echo ✓ Frontend dependencies installed
    )
) else (
    echo ✓ Frontend dependencies already installed
)

cd ..

REM Check for data files
echo [5/6] Checking for required data files...
if exist "Jira (3).csv" (
    echo ✓ Jira (3).csv found
) else (
    echo WARNING: Jira (3).csv not found in root directory
    echo          You will need to train models before using the system
)

if exist "HU_260226.xlsx" (
    echo ✓ HU_260226.xlsx found
) else (
    echo WARNING: HU_260226.xlsx not found in root directory
)

REM Start services
echo [6/6] Starting services...
echo.
echo ========================================
echo   Starting Backend and Frontend
echo ========================================
echo.
echo Backend will start in a new window on port 8000
echo Frontend will start in another window on port 3000
echo.
echo Once both are running, open: http://localhost:3000
echo Backend API docs: http://localhost:8000/docs
echo.
echo Press any key to start...
pause >nul

REM Start backend in new window
echo Launching backend server...
start "Epic Estimation - Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for backend to start
timeout /t 3 /nobreak

REM Start frontend in new window
echo Launching frontend server...
start "Epic Estimation - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo   Services Started Successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Wait for both servers to finish starting (10-15 seconds)
echo 2. Open: http://localhost:3000
echo 3. Upload Jira (3).csv to train models (if not already trained)
echo 4. Upload HU_260226.xlsx for testing
echo.
echo To stop the services, close the terminal windows.
echo.

pause
