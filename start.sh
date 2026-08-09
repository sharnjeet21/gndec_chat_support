#!/usr/bin/env bash
# ─────────────────────────────────────────────
# start.sh — Start all services for tech_support_ai
# Usage: ./start.sh
# ─────────────────────────────────────────────
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

info()  { echo -e "${GREEN}[✔]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✘]${NC} $1"; }

# ── 1. PostgreSQL ──────────────────────────────
if pg_isready -h localhost -p 5432 -q 2>/dev/null; then
  info "PostgreSQL already running"
else
  warn "Starting PostgreSQL..."
  brew services start postgresql@14 || echo "Please make sure postgresql@14 is running"
fi

# ── 2. Redis ──────────────────────────────────
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
  info "Redis already running"
else
  warn "Starting Redis..."
  brew services start redis 2>/dev/null || redis-server --daemonize yes
fi

# ── 3. Ollama ─────────────────────────────────
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  info "Ollama already running"
else
  warn "Starting Ollama..."
  ollama serve &>/tmp/ollama.log &
  sleep 2
fi

# ── 4. Backend ────────────────────────────────
info "Starting FastAPI backend on http://localhost:8000 ..."
"$ROOT/venv/bin/python" -m uvicorn backend.app:app \
  --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 3
if curl -s http://localhost:8000/health | grep -q "ok"; then
  info "Backend is up → http://localhost:8000"
else
  error "Backend failed to start. Check logs above."
fi

# ── 5. Frontend ───────────────────────────────
info "Starting React frontend on http://localhost:5173 ..."
cd "$ROOT/support_ui"
npm run dev &
FRONTEND_PID=$!
cd "$ROOT"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Frontend  →  ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend   →  ${GREEN}http://localhost:8000${NC}"
echo -e "  API Docs  →  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo ""

# Wait and clean up on Ctrl+C
trap "echo ''; warn 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT
wait
