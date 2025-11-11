# Trading Bot GUI Setup Guide

This guide explains how to set up and run the React frontend with FastAPI backend for the Trading Bot.

## Architecture

- **Backend**: FastAPI REST API (`src/trading_bot/api/`)
- **Frontend**: React + TypeScript + shadcn/ui (`frontend/`)
- **Communication**: REST API over HTTP (backend on port 8000, frontend on port 3000)

## Prerequisites

1. Python 3.13.4+ or 3.14+ installed
2. Bun installed (https://bun.sh)
3. UV package manager installed
4. Trading bot dependencies installed

## Backend Setup

1. Install Python dependencies:
```bash
uv sync --python 3.14 --prerelease=allow
```

2. The FastAPI backend will be available at `http://localhost:8000`

## Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
bun install
```

3. Start the development server:
```bash
bun run dev
```

The frontend will be available at `http://localhost:3000`

## Running Both Servers

### Option 1: Use the provided scripts (Windows)

Run both servers simultaneously:
```bash
scripts\start_all.bat
```

Or run them separately:
```bash
# Terminal 1 - Backend
scripts\start_api.bat

# Terminal 2 - Frontend
scripts\start_frontend.bat
```

### Option 2: Manual startup

**Backend (Terminal 1):**
```bash
uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (Terminal 2):**
```bash
cd frontend
bun install
bun run dev
```

## API Endpoints

### Status
- `GET /api/status` - Get bot status
- `GET /api/health` - Health check

### Strategies
- `GET /api/strategies` - List all strategies
- `GET /api/strategies/{name}` - Get strategy info

### Data
- `GET /api/data/fetch` - Fetch market data
  - Query params: `symbol`, `timeframe`, `limit`, `start_date`, `end_date`
- `GET /api/exchanges` - List available exchanges

### Backtest
- `POST /api/backtest/run` - Run a backtest
  - Body: `BacktestRequest` (strategy_name, symbol, timeframe, limit, engine, strategy_params)

## Frontend Features

### Dashboard
- View bot status
- Exchange information
- Data provider status

### Strategies
- Browse available strategies
- View strategy availability
- See strategy details

### Backtest
- Configure backtest parameters
- Select strategy and symbol
- Choose backtesting engine
- View results

### Data Fetch
- Fetch historical market data
- Configure symbol, timeframe, and limit
- Preview fetched data

## Development

### Backend Development

The FastAPI backend uses hot-reload when started with `--reload` flag. Changes to Python files will automatically restart the server.

### Frontend Development

The Vite dev server supports hot module replacement (HMR). Changes to React components will update in the browser automatically.

### API Documentation

FastAPI provides automatic API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Backend won't start

1. Check Python version: `python --version` (should be 3.13.4+ or 3.14+)
2. Install dependencies: `uv sync --python 3.14 --prerelease=allow`
3. Check if port 8000 is available

### Frontend won't start

1. Check Bun version: `bun --version`
2. Install dependencies: `cd frontend && bun install`
3. Check if port 3000 is available

### CORS errors

The backend is configured to allow requests from `http://localhost:3000` and `http://localhost:5173`. If you're using a different port, update the CORS configuration in `src/trading_bot/api/main.py`.

### API connection errors

1. Ensure backend is running on port 8000
2. Check browser console for errors
3. Verify CORS settings in backend

## Building for Production

### Backend

The backend can be run with uvicorn in production mode:
```bash
uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000
```

### Frontend

Build the frontend for production:
```bash
cd frontend
bun run build
```

The built files will be in `frontend/dist/`. You can serve them with any static file server or configure the FastAPI backend to serve them.

## Project Structure

```
TradingBOT/
├── src/trading_bot/
│   └── api/                    # FastAPI backend
│       ├── main.py             # FastAPI app and entry point
│       └── routes/             # API route handlers
│           ├── status.py       # Status endpoints
│           ├── strategies.py   # Strategy endpoints
│           ├── data.py         # Data fetching endpoints
│           └── backtest.py     # Backtest endpoints
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── ui/            # shadcn/ui components
│   │   │   └── Layout.tsx    # Main layout
│   │   ├── pages/             # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Backtest.tsx
│   │   │   ├── Strategies.tsx
│   │   │   └── DataFetch.tsx
│   │   └── lib/               # Utilities
│   │       ├── api.ts         # API client
│   │       └── utils.ts       # Helper functions
│   └── package.json
└── scripts/                    # Startup scripts
    ├── start_api.bat
    ├── start_frontend.bat
    └── start_all.bat
```

