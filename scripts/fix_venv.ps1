# Fix corrupted virtual environment and Python cache issues
Write-Host "Fixing corrupted virtual environment..." -ForegroundColor Yellow

# Step 1: Remove existing virtual environment
Write-Host "Step 1: Removing existing virtual environment..." -ForegroundColor Cyan
if (Test-Path ".venv") {
    Remove-Item ".venv" -Recurse -Force
    Write-Host "✓ Removed .venv directory" -ForegroundColor Green
}

# Step 2: Clear Python cache files
Write-Host "Step 2: Clearing Python cache files..." -ForegroundColor Cyan
Get-ChildItem -Path "." -Recurse -Filter "__pycache__" -Directory | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    Write-Host "✓ Removed cache: $($_.FullName)" -ForegroundColor Green
}

# Find and remove all .pyc files
Get-ChildItem -Path "." -Recurse -Filter "*.pyc" | ForEach-Object {
    Remove-Item $_.FullName -Force
}

# Find and remove all .pyo files
Get-ChildItem -Path "." -Recurse -Filter "*.pyo" | ForEach-Object {
    Remove-Item $_.FullName -Force
}

Write-Host "✓ Cleared all Python cache files" -ForegroundColor Green

# Step 3: Clean uv cache (optional but helpful)
Write-Host "Step 3: Clearing uv cache..." -ForegroundColor Cyan
try {
    uv cache clean
    Write-Host "✓ Cleared uv cache" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Could not clear uv cache (may not exist): $($_.Exception.Message)" -ForegroundColor Yellow
}

# Step 4: Reinstall virtual environment
Write-Host "Step 4: Reinstalling virtual environment..." -ForegroundColor Cyan
try {
    uv sync --python 3.13 --prerelease=allow
    Write-Host "✓ Successfully reinstalled virtual environment" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to reinstall virtual environment: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 5: Test the installation
Write-Host "Step 5: Testing the installation..." -ForegroundColor Cyan
try {
    uv run python -c "import uvicorn; import click; print('✓ All imports successful')"
    Write-Host "✓ Virtual environment is working correctly" -ForegroundColor Green
} catch {
    Write-Host "❌ Import test failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Virtual environment fixed successfully!" -ForegroundColor Green



