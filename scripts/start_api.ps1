# PowerShell script to start the FastAPI backend server
Write-Host "Starting Trading Bot API..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .venv\Scripts\Activate.ps1
}

# Start the API server
Write-Host "Starting API server on http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs will be available at http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

# Check if port 8000 is already in use
$existingProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existingProcess) {
    Write-Host "ERROR: Port 8000 is already in use by process ID: $($existingProcess.OwningProcess)" -ForegroundColor Red
    Write-Host "Please stop the existing server first or use a different port." -ForegroundColor Red
    exit 1
}

# Start the API server (removed --reload to prevent multiple processes)
uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000

