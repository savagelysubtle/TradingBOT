@echo off
REM Start the React frontend development server
echo Starting Trading Bot Frontend...
cd frontend
call bun install
call bun run dev

