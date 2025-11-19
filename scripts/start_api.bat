@echo off
REM Start the FastAPI backend server
echo Starting Trading Bot API...
echo.
echo API will be available at http://localhost:8000
echo API docs will be available at http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run: uv sync --python 3.14 --prerelease=allow
    pause
    exit /b 1
)

REM Check if port 8000 is already in use
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ERROR: Port 8000 is already in use!
    echo Please stop the existing server first.
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
        echo Process ID using port 8000: %%a
        tasklist /FI "PID eq %%a" 2>nul
    )
    pause
    exit /b 1
)

REM Start the API server (removed --reload to prevent multiple processes)
uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000

