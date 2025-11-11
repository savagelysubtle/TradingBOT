# Quick Start: Backend API Server

## The Problem
Your frontend is running but can't connect to the backend because the API server isn't running.

## Solution: Start the Backend

### Option 1: VS Code Task (Easiest)
1. Press `Ctrl+Shift+P`
2. Type "Tasks: Run Task"
3. Select **"Run API Server"**

### Option 2: Batch Script
Open a **NEW** terminal/PowerShell window and run:
```bash
cd D:\Coding\TradingBOT
scripts\start_api.bat
```

### Option 3: Manual Command
Open a **NEW** terminal/PowerShell window and run:
```powershell
cd D:\Coding\TradingBOT
.venv\Scripts\Activate.ps1
uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Verify It's Running

Once started, you should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

Then visit:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## Important Notes

- **Keep the backend terminal open** - don't close it
- The frontend terminal can stay open too
- You need **TWO terminals** running:
  1. Frontend (port 3000) - already running ✅
  2. Backend (port 8000) - needs to be started ⚠️

## Once Both Are Running

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

The frontend will automatically connect and show a green "Backend Connected" message.

