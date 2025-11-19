# Test script to verify server starts and stops cleanly
Write-Host "Testing Trading Bot server management..." -ForegroundColor Green

# Step 1: Kill any existing servers
Write-Host "Step 1: Cleaning up existing processes..." -ForegroundColor Yellow
& .\scripts\kill_servers.ps1

# Step 2: Check ports are free
Write-Host "Step 2: Checking ports are free..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue

if ($port8000) {
    Write-Host "ERROR: Port 8000 still in use!" -ForegroundColor Red
    exit 1
}
if ($port3000) {
    Write-Host "ERROR: Port 3000 still in use!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Ports 8000 and 3000 are free" -ForegroundColor Green

# Step 3: Start server in background
Write-Host "Step 3: Starting API server..." -ForegroundColor Yellow
$serverJob = Start-Job -ScriptBlock {
    try {
        & uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000
    } catch {
        Write-Host "Server job failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Wait a bit for server to start
Start-Sleep -Seconds 5

# Step 4: Check server is running
Write-Host "Step 4: Checking server is running..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $port8000) {
    Write-Host "ERROR: Server failed to start on port 8000!" -ForegroundColor Red
    Stop-Job $serverJob
    Remove-Job $serverJob
    exit 1
}
Write-Host "✓ Server is running on port 8000" -ForegroundColor Green

# Step 5: Test server health
Write-Host "Step 5: Testing server health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Server health check passed" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Server health check failed with status $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "ERROR: Server health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 6: Stop server gracefully
Write-Host "Step 6: Stopping server gracefully..." -ForegroundColor Yellow
Stop-Job $serverJob
Remove-Job $serverJob

# Wait for server to stop
Start-Sleep -Seconds 3

# Step 7: Verify server stopped cleanly
Write-Host "Step 7: Verifying server stopped cleanly..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "ERROR: Server did not stop cleanly - port 8000 still in use!" -ForegroundColor Red
    # Force kill
    & .\scripts\kill_servers.ps1
    exit 1
}
Write-Host "✓ Server stopped cleanly" -ForegroundColor Green

Write-Host "All tests passed! Server management is working correctly." -ForegroundColor Green



