#!/bin/bash
# scripts/dev.sh — start backend and frontend together

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "🔥 Starting OptimalFuel dev environment..."

# Backend
echo "▶ Starting backend on http://localhost:8000"
cd "$ROOT/backend"
if [ ! -d "venv" ]; then
  echo "  Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Frontend
echo "▶ Starting frontend on http://localhost:5173"
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
  echo "  Installing npm packages..."
  npm install
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Running!"
echo "   Backend:  http://localhost:8000"
echo "   API docs: http://localhost:8000/api/docs"
echo "   Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for Ctrl+C, then kill both
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '👋 Stopped'" INT TERM
wait
