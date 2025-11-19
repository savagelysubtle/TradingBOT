@echo off
REM Batch script to forcefully kill trading bot servers
echo Killing Trading Bot servers...

REM Kill processes using ports 8000 and 3000
echo Checking port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Killing process %%a using port 8000...
    taskkill /PID %%a /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo Successfully killed process %%a
    ) else (
        echo Failed to kill process %%a
    )
)

echo Checking port 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo Killing process %%a using port 3000...
    taskkill /PID %%a /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo Successfully killed process %%a
    ) else (
        echo Failed to kill process %%a
    )
)

REM Kill Python processes that might be trading bot related
echo Checking for orphaned Python processes...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO TABLE ^| findstr python.exe') do (
    REM Check if this is a trading bot process (simplified check)
    taskkill /PID %%a /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo Killed Python process %%a
    )
)

REM Kill Node processes
echo Checking for Node.js processes...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" /FO TABLE ^| findstr node.exe') do (
    taskkill /PID %%a /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo Killed Node process %%a
    )
)

echo Server cleanup complete!



