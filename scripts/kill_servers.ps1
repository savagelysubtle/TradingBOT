# PowerShell script to forcefully kill trading bot servers
Write-Host "Killing Trading Bot servers..." -ForegroundColor Yellow

# Kill processes using ports 8000 and 3000
$ports = @(8000, 3000)

foreach ($port in $ports) {
    Write-Host "Checking port $port..." -ForegroundColor Cyan
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $pid = $conn.OwningProcess
        Write-Host "Killing process $pid using port $port..." -ForegroundColor Red
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "Successfully killed process $pid" -ForegroundColor Green
        } catch {
            Write-Host "Failed to kill process $pid : $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# Kill any remaining Python processes that might be trading bot related
Write-Host "Checking for orphaned Python processes..." -ForegroundColor Cyan
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
foreach ($proc in $pythonProcesses) {
    try {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
        if ($cmdLine -and ($cmdLine -match "trading_bot" -or $cmdLine -match "uvicorn")) {
            Write-Host "Killing Python process $($proc.Id) (trading bot related)..." -ForegroundColor Red
            Stop-Process -Id $proc.Id -Force
            Write-Host "Successfully killed Python process $($proc.Id)" -ForegroundColor Green
        }
    } catch {
        # Ignore errors when checking process details
    }
}

# Kill any node processes (for frontend)
Write-Host "Checking for Node.js processes..." -ForegroundColor Cyan
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue
foreach ($proc in $nodeProcesses) {
    Write-Host "Killing Node process $($proc.Id)..." -ForegroundColor Red
    try {
        Stop-Process -Id $proc.Id -Force
        Write-Host "Successfully killed Node process $($proc.Id)" -ForegroundColor Green
    } catch {
        Write-Host "Failed to kill Node process $($proc.Id): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "Server cleanup complete!" -ForegroundColor Green



