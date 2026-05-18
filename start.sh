#!/bin/bash
# ============================================================
# GNDEC AI Assistant — Start Script
# ============================================================
# Starts all required services and the application.
# Run: bash start.sh
# Stop: Ctrl+C
# ============================================================

set -e

# ── Colors ───────────────────────────────────────────────────
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'
B='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

LOG_DIR="/tmp/gndec_logs"
mkdir -p "$LOG_DIR"

BACKEND_PID=""
FRONTEND_PID=""

# ── Cleanup on exit ──────────────────────────────────────────
cleanup() {
    echo ""
    echo -e "${Y}Shutting down GNDEC AI Assistant...${NC}"
    [ -n "$BACKEND_PID"  ] && kill "$BACKEND_PID"  2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    echo -e "${G}Done.${NC}"
    exit 0
}
trap cleanup INT TERM

# ── Banner ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        GNDEC AI Assistant — Startup          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Check .env ───────────────────────────────────────
echo -e "${Y}[1/6] Checking environment...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${R}  .env file not found!${NC}"
    echo "  Copy .env.bak to .env and fill in your values."
    exit 1
fi
echo -e "${G}  .env found.${NC}"

# ── Step 2: Check FAISS index ────────────────────────────────
echo -e "${Y}[2/6] Checking FAISS vector index...${NC}"
if [ ! -f "backend/faiss_store/faq.index" ] || [ ! -f "backend/faiss_store/meta.json" ]; then
    echo -e "${Y}  FAISS index not found. Building now...${NC}"
    python3 backend/build_vector_db.py
    echo -e "${G}  FAISS index built.${NC}"
else
    COUNT=$(python3 -c "import json; d=json.load(open('backend/faiss_store/meta.json')); print(len(d))" 2>/dev/null || echo "?")
    echo -e "${G}  FAISS index found ($COUNT vectors).${NC}"
fi

# ── Step 3: Check & start Redis ──────────────────────────────
echo -e "${Y}[3/6] Checking Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${G}  Redis already running.${NC}"
else
    echo "  Starting Redis..."
    redis-server --daemonize yes --logfile "$LOG_DIR/redis.log"
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${G}  Redis started.${NC}"
    else
        echo -e "${R}  Redis failed to start. Check $LOG_DIR/redis.log${NC}"
        exit 1
    fi
fi

# ── Step 4: Check Ollama ─────────────────────────────────────
echo -e "${Y}[4/6] Checking Ollama...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    MODEL=$(grep "LLM_MODEL" .env | cut -d= -f2)
    FOUND=$(curl -s http://localhost:11434/api/tags | python3 -c "
import json,sys
d=json.load(sys.stdin)
models=[m['name'] for m in d.get('models',[])]
model='$MODEL'
print('yes' if any(model in m for m in models) else 'no')
" 2>/dev/null)
    if [ "$FOUND" = "yes" ]; then
        echo -e "${G}  Ollama running with model: $MODEL${NC}"
    else
        echo -e "${Y}  Ollama running but model '$MODEL' not found.${NC}"
        echo "  Pulling $MODEL (this may take a few minutes)..."
        /usr/local/bin/ollama pull "$MODEL"
        echo -e "${G}  Model ready.${NC}"
    fi
else
    echo -e "${Y}  Ollama not running. Starting...${NC}"
    open -a Ollama 2>/dev/null || /usr/local/bin/ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
    echo "  Waiting for Ollama to start..."
    for i in {1..15}; do
        sleep 2
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${G}  Ollama started.${NC}"
            break
        fi
        [ $i -eq 15 ] && { echo -e "${R}  Ollama failed to start.${NC}"; exit 1; }
    done
fi

# ── Step 5: Start backend ────────────────────────────────────
echo -e "${Y}[5/6] Starting backend (port 8080)...${NC}"
nohup uvicorn backend.app:app --host 0.0.0.0 --port 8080 --reload \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

echo "  Waiting for backend..."
for i in {1..20}; do
    sleep 2
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${G}  Backend ready (PID $BACKEND_PID).${NC}"
        break
    fi
    [ $i -eq 20 ] && {
        echo -e "${R}  Backend failed to start. Check $LOG_DIR/backend.log${NC}"
        tail -20 "$LOG_DIR/backend.log"
        exit 1
    }
done

# ── Step 6: Start frontend ───────────────────────────────────
echo -e "${Y}[6/6] Starting frontend dev server (port 5173)...${NC}"

# Make sure frontend .env points to localhost
cat > support_ui/.env <<EOF
VITE_API_URL=http://localhost:8080
VITE_API_KEY=$(grep "^API_KEY" .env | cut -d= -f2)
EOF

nohup npm run dev --prefix support_ui \
    > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

sleep 4
if grep -q "Local:" "$LOG_DIR/frontend.log" 2>/dev/null; then
    echo -e "${G}  Frontend ready (PID $FRONTEND_PID).${NC}"
else
    echo -e "${Y}  Frontend starting... (check $LOG_DIR/frontend.log if issues)${NC}"
fi

# ── Ready ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║              GNDEC AI IS READY               ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Frontend :${NC} ${B}http://localhost:5173${NC}"
echo -e "  ${BOLD}Backend  :${NC} ${B}http://localhost:8080${NC}"
echo -e "  ${BOLD}API Docs :${NC} ${B}http://localhost:8080/docs${NC}"
echo ""
echo -e "  ${BOLD}Logs     :${NC} $LOG_DIR/"
echo -e "  ${Y}Press Ctrl+C to stop all services.${NC}"
echo ""

# ── Keep alive ───────────────────────────────────────────────
wait
