@echo off
REM Fix corrupted virtual environment and Python cache issues
echo Fixing corrupted virtual environment...

REM Step 1: Remove existing virtual environment
echo Step 1: Removing existing virtual environment...
if exist ".venv" (
    rmdir /s /q ".venv"
    echo Removed .venv directory
)

REM Step 2: Clear Python cache files
echo Step 2: Clearing Python cache files...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo Removed cache: %%d
    )
)

REM Remove all .pyc files
for /r %%f in (*.pyc) do (
    del /q "%%f"
)

REM Remove all .pyo files
for /r %%f in (*.pyo) do (
    del /q "%%f"
)

echo Cleared all Python cache files

REM Step 3: Clean uv cache (optional but helpful)
echo Step 3: Clearing uv cache...
uv cache clean
if %errorlevel% equ 0 (
    echo Cleared uv cache
) else (
    echo Could not clear uv cache (may not exist)
)

REM Step 4: Reinstall virtual environment
echo Step 4: Reinstalling virtual environment...
uv sync --python 3.13 --prerelease=allow
if %errorlevel% neq 0 (
    echo Failed to reinstall virtual environment
    exit /b 1
)
echo Successfully reinstalled virtual environment

REM Step 5: Test the installation
echo Step 5: Testing the installation...
uv run python -c "import uvicorn; import click; print('All imports successful')"
if %errorlevel% neq 0 (
    echo Import test failed
    exit /b 1
)
echo Virtual environment is working correctly

echo Virtual environment fixed successfully!



