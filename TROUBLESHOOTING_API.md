# API Troubleshooting Guide

## Common Issues

### "socket hang up" or Proxy Errors

If you see errors like:
```
[vite] http proxy error: /api/status
Error: socket hang up
```

This means the **backend API server is not running**. The frontend is trying to connect to `http://localhost:8000` but nothing is listening.

## Solution

### Step 1: Start the Backend API Server

You have several options:

#### Option A: Using VS Code Tasks (Recommended)

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "Tasks: Run Task"
3. Select **"Run API Server"**

Or use the keyboard shortcut:
- Press `Ctrl+Shift+B` and select "Run API Server"

#### Option B: Using Batch Script (Windows)

```bash
scripts\start_api.bat
```

#### Option C: Using PowerShell Script

```powershell
scripts\start_api.ps1
```

#### Option D: Manual Start

```bash
uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Verify Backend is Running

Once started, you should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

You can also verify by visiting:
- **API Root**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### Step 3: Check Frontend

The frontend should now be able to connect. You'll see a green "Backend Connected" alert on the Dashboard if everything is working.

## Running Both Servers

### Using VS Code Tasks

1. Press `Ctrl+Shift+B`
2. Select **"Run GUI (API + Frontend)"**

This will start both servers in parallel.

### Using Scripts

**Terminal 1** (Backend):
```bash
scripts\start_api.bat
```

**Terminal 2** (Frontend):
```bash
scripts\start_frontend.bat
```

Or use the combined script:
```bash
scripts\start_all.bat
```

## Port Conflicts

If port 8000 is already in use:

1. Find what's using the port:
   ```powershell
   netstat -ano | findstr :8000
   ```

2. Kill the process or change the port in:
   - `scripts/start_api.bat`
   - `.vscode/tasks.json`
   - `frontend/vite.config.ts` (proxy target)

## Dependencies Not Installed

If you get import errors:

1. Install Python dependencies:
   ```bash
   uv sync --python 3.14 --prerelease=allow
   ```

2. Install frontend dependencies:
   ```bash
   cd frontend
   bun install
   ```

## Virtual Environment Issues

If the virtual environment is not found:

1. Create/activate virtual environment:
   ```bash
   uv venv --python 3.14
   .venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   uv sync --python 3.14 --prerelease=allow
   ```

## Still Having Issues?

1. Check the backend logs in the terminal where you started it
2. Check browser console for detailed error messages
3. Verify both servers are running:
   - Backend: http://localhost:8000/docs
   - Frontend: http://localhost:3000

4. Make sure CORS is configured correctly in `src/trading_bot/api/main.py`

