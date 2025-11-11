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

uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000 --reload

