#!/usr/bin/env bash
# start.sh — Start FastAPI backend + React/Vite frontend (Linux/WSL)
# Usage: ./scripts/start.sh [--port 8000] [--frontend-port 5173] [--no-reload]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/src/frontend"

PORT=8000
FRONTEND_PORT=5173
RELOAD="--reload"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)           PORT="$2"; shift 2 ;;
    --frontend-port)  FRONTEND_PORT="$2"; shift 2 ;;
    --no-reload)      RELOAD=""; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Activate venv if present
if [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  source "$REPO_ROOT/.venv/bin/activate"
fi

echo ""
echo "  Starting FastAPI backend on port $PORT ..."
cd "$REPO_ROOT"
uvicorn src.backend.main:app --port "$PORT" $RELOAD &
BACKEND_PID=$!

sleep 2

echo "  Starting React/Vite frontend on port $FRONTEND_PORT ..."
cd "$FRONTEND_DIR"
VITE_BACKEND_URL="http://localhost:$PORT" npm run dev -- --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

echo ""
echo "  Backend  ->  http://localhost:$PORT"
echo "  API docs ->  http://localhost:$PORT/docs"
echo "  Frontend ->  http://localhost:$FRONTEND_PORT"
echo ""
echo "  Press Ctrl+C to stop both services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
