@echo off
REM Start both backend and frontend
echo Starting Trading Bot (Backend + Frontend)...
start "Trading Bot API" cmd /k "scripts\start_api.bat"
timeout /t 3 /nobreak >nul
start "Trading Bot Frontend" cmd /k "scripts\start_frontend.bat"
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all servers...
pause >nul
taskkill /FI "WINDOWTITLE eq Trading Bot API*" /F
taskkill /FI "WINDOWTITLE eq Trading Bot Frontend*" /F

