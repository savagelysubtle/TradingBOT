@echo off
echo Testing server startup...
echo.

REM Kill any existing processes
echo Killing existing processes...
taskkill /IM python.exe /F >nul 2>&1

REM Try to start server
echo Starting server...
uv run uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000
echo Server command completed.

REM Check if it's running
echo Checking if server is running...
netstat -ano | findstr :8000
if %errorlevel% equ 0 (
    echo SUCCESS: Server is running on port 8000
) else (
    echo FAILED: Server is not running
)

pause



