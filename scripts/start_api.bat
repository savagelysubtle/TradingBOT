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

uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000 --reload

