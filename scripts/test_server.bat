@echo off
REM Simple test script to verify server starts and stops cleanly
echo Testing Trading Bot server management...

REM Step 1: Kill any existing servers
echo Step 1: Cleaning up existing processes...
call .\scripts\kill_servers.bat

REM Step 2: Check ports are free
echo Step 2: Checking ports are free...
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ERROR: Port 8000 still in use!
    exit /b 1
)
netstat -ano | findstr :3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ERROR: Port 3000 still in use!
    exit /b 1
)
echo Ports 8000 and 3000 are free

REM Step 3: Start server in background
echo Step 3: Starting API server...
start "TestServer" cmd /k "uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000"

REM Wait for server to start
timeout /t 5 /nobreak >nul

REM Step 4: Check server is running
echo Step 4: Checking server is running...
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Server failed to start on port 8000!
    call .\scripts\kill_servers.bat
    exit /b 1
)
echo Server is running on port 8000

REM Step 5: Stop server
echo Step 5: Stopping server...
taskkill /FI "WINDOWTITLE eq TestServer*" /F >nul 2>&1

REM Wait for server to stop
timeout /t 3 /nobreak >nul

REM Step 6: Verify server stopped cleanly
echo Step 6: Verifying server stopped cleanly...
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ERROR: Server did not stop cleanly - port 8000 still in use!
    call .\scripts\kill_servers.bat
    exit /b 1
)
echo Server stopped cleanly

echo All tests passed! Server management is working correctly.



