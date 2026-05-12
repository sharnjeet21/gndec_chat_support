#!/bin/bash
# ============================================================
# GNDEC RAG — Share via ngrok  (single tunnel)
#
# How it works:
#   1. Builds the React frontend with the ngrok URL as API base
#   2. FastAPI serves both the API (/api/*) and the built
#      React files from the same port (8080)
#   3. One ngrok tunnel exposes port 8080 publicly
#   4. Your brother opens the ngrok URL — done.
#
# Run:  bash share.sh
# Stop: Ctrl+C
# ============================================================

set -e

PORT=8080
NGROK_BIN="/opt/homebrew/bin/ngrok"
LOG_DIR="/tmp/gndec_share"
mkdir -p "$LOG_DIR"

G='\033[0;32m'; B='\033[0;34m'; Y='\033[1;33m'
R='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       GNDEC RAG — Share via ngrok            ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── 0. Kill old processes ────────────────────────────────────
echo -e "${Y}[1/5] Cleaning up...${NC}"
pkill -f "uvicorn backend.app" 2>/dev/null || true
pkill -f "ngrok"               2>/dev/null || true
sleep 2

# ── 1. Ollama ────────────────────────────────────────────────
echo -e "${Y}[2/5] Checking Ollama...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  Starting Ollama..."
    open -a Ollama 2>/dev/null || true
    sleep 8
fi
echo -e "${G}  Ollama OK${NC}"

# ── 2. Redis ─────────────────────────────────────────────────
echo -e "${Y}[3/5] Checking Redis...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    redis-server --daemonize yes --logfile "$LOG_DIR/redis.log"
    sleep 2
fi
echo -e "${G}  Redis OK${NC}"

# ── 3. Get ngrok URL FIRST (before building frontend) ────────
echo -e "${Y}[4/5] Starting ngrok tunnel on :$PORT...${NC}"

nohup $NGROK_BIN http $PORT \
    --request-header-add "ngrok-skip-browser-warning: true" \
    --log "$LOG_DIR/ngrok.log" \
    --log-format json \
    > /dev/null 2>&1 &
NGROK_PID=$!
sleep 5

# Extract the public HTTPS URL
PUBLIC_URL=""
for i in {1..15}; do
    PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
        | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    for t in d.get('tunnels',[]):
        if t.get('proto')=='https':
            print(t['public_url']); break
except: pass
" 2>/dev/null)
    [ -n "$PUBLIC_URL" ] && break
    sleep 2
done

if [ -z "$PUBLIC_URL" ]; then
    echo -e "${R}  ngrok failed. Check $LOG_DIR/ngrok.log${NC}"
    exit 1
fi
echo -e "${G}  Public URL: $PUBLIC_URL${NC}"

# ── 4. Build frontend with the ngrok URL as API base ─────────
echo -e "${Y}[5/5] Building frontend → $PUBLIC_URL ...${NC}"

cat > support_ui/.env <<EOF
VITE_API_URL=$PUBLIC_URL
VITE_API_KEY=naman@1234
EOF

cd support_ui
npm run build > "$LOG_DIR/build.log" 2>&1
echo -e "${G}  Frontend built.${NC}"
cd ..

# ── 5. Start backend (serves API + built frontend) ───────────
nohup uvicorn backend.app:app --host 0.0.0.0 --port $PORT \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

echo "  Waiting for backend..."
for i in {1..20}; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo -e "${G}  Backend ready (PID $BACKEND_PID)${NC}"; break
    fi
    sleep 2
    [ $i -eq 20 ] && { echo -e "${R}  Backend failed. See $LOG_DIR/backend.log${NC}"; exit 1; }
done

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║              ALL SYSTEMS UP                  ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}${G}  ┌─────────────────────────────────────────────┐${NC}"
echo -e "${BOLD}${G}  │  SEND THIS LINK TO YOUR BROTHER:            │${NC}"
echo -e "${BOLD}${G}  │                                             │${NC}"
echo -e "${BOLD}${G}  │  $PUBLIC_URL                                │${NC}"
echo -e "${BOLD}${G}  │                                             │${NC}"
echo -e "${BOLD}${G}  └─────────────────────────────────────────────┘${NC}"
echo ""
echo -e "  Local : ${B}http://localhost:$PORT${NC}"
echo -e "  Logs  : $LOG_DIR/"
echo -e "${Y}  Press Ctrl+C to stop.${NC}"
echo ""

# ── Cleanup ──────────────────────────────────────────────────
cleanup() {
    echo ""
    echo -e "${Y}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $NGROK_PID   2>/dev/null || true
    pkill -f "ngrok"  2>/dev/null || true
    redis-cli shutdown nosave 2>/dev/null || true
    # Restore local .env
    cat > support_ui/.env <<EOF
VITE_API_URL=http://localhost:8080
VITE_API_KEY=naman@1234
EOF
    echo -e "${G}Done. Local .env restored.${NC}"
    exit 0
}
trap cleanup INT TERM EXIT

wait
