#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# 1. Database
echo "[1/4] Starting PostgreSQL..."
docker start hismap-db 2>/dev/null || echo "  (already running)"

# Wait for postgres to accept connections
echo "[2/4] Waiting for database..."
for i in $(seq 1 30); do
  if docker exec hismap-db pg_isready -U hismap -q 2>/dev/null; then
    echo "  Database ready."
    break
  fi
  sleep 1
done

# 2. Run migrations
echo "[3/4] Running migrations..."
cd "$ROOT/backend"
conda run -n hismap alembic upgrade head

# 3. Start backend
echo "[4/4] Starting backend & frontend..."
conda run -n hismap python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 4. Start frontend
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "  Press Ctrl+C to stop both."
echo ""

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
