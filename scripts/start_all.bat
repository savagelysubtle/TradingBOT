@echo off
REM Start both backend and frontend with proper process management
echo Starting Trading Bot (Backend + Frontend)...

REM Kill any existing processes on ports 8000 and 3000
echo Checking for existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Killing process %%a using port 8000...
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo Killing process %%a using port 3000...
    taskkill /PID %%a /F >nul 2>&1
)

REM Small delay to ensure ports are freed
timeout /t 2 /nobreak >nul

start "Trading Bot API" cmd /k "scripts\start_api.bat"
timeout /t 3 /nobreak >nul
start "Trading Bot Frontend" cmd /k "scripts\start_frontend.bat"
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all servers...
pause >nul

echo Stopping servers...
taskkill /FI "WINDOWTITLE eq Trading Bot API*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Trading Bot Frontend*" /F >nul 2>&1

REM Also kill any remaining processes on ports 8000 and 3000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Force killing process %%a using port 8000...
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo Force killing process %%a using port 3000...
    taskkill /PID %%a /F >nul 2>&1
)

echo All servers stopped.

