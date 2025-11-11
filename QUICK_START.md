# Quick Start Guide

## Running the GUI

### Option 1: Keyboard Shortcut (Easiest)
Press **`Ctrl+Shift+G`** to start both API and Frontend servers

### Option 2: Build Task
Press **`Ctrl+Shift+B`** (runs default build task = Run GUI)

### Option 3: Command Palette
1. Press **`Ctrl+Shift+P`**
2. Type: `Tasks: Run Task`
3. Select: **"Run GUI (API + Frontend)"**

## Individual Servers

- **API Server Only**: Press **`Ctrl+Shift+A`**
- **Frontend Only**: Press **`Ctrl+Shift+F`**

## What Happens

When you run the GUI task:
1. **Backend API** starts on `http://localhost:8000`
   - API docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/health`

2. **Frontend** starts on `http://localhost:3000`
   - Opens automatically in your browser
   - Connects to backend API automatically

## Stopping Servers

- Click the **trash icon** in the terminal panel
- Or press **`Ctrl+C`** in each terminal

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Ensure Python dependencies are installed: `uv sync --python 3.14 --prerelease=allow`

### Frontend won't start
- Check if port 3000 is available
- Ensure frontend dependencies are installed: `cd frontend && bun install`

### 500 Errors
- Check backend terminal for error messages
- Check `logs/trading_bot.log` for detailed errors
- Ensure backend is fully started before frontend makes requests

