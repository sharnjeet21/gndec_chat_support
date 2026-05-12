# backend/app.py
"""
GNDEC College AI Assistant — FastAPI Backend
=============================================
Provides REST endpoints for the GNDEC RAG chatbot.
"""

import logging
import os
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List

from .agent import answer_sync, answer_stream, clear_redis_session
from .chat_store import (
    get_session_history,
    list_sessions,
    get_or_create_session_id,
    close_session_for_phone,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GNDEC College AI Assistant",
    description="RAG-powered chatbot for Guru Nanak Dev Engineering College, Ludhiana",
    version="1.0.0",
)

# ============================== AUTH MIDDLEWARE ==============================
API_KEY = os.getenv("API_KEY")


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    # Skip auth for health check and all frontend static routes
    path = request.url.path
    if path == "/health" or not path.startswith("/api"):
        return await call_next(request)

    client_key = request.headers.get("X-API-KEY")
    if client_key != API_KEY:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: Invalid or missing API key"},
        )
    return await call_next(request)


# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: lock down to your frontend domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "GNDEC AI Assistant"}


@app.get("/api/start_session")
async def start_session(phone: str = Query(...), session_id: str = Query(...)):
    """Initialise a session — Redis manages conversation memory."""
    if not phone or not session_id:
        raise HTTPException(status_code=400, detail="phone and session_id required")

    logging.info(f"Session started: phone={phone}, session_id={session_id}")
    return {"ok": True}


@app.get("/api/ask")
async def ask(
    phone: str = Query(...),
    session_id: str = Query(...),
    q: str = Query(...),
):
    """Synchronous (non-streaming) answer endpoint."""
    if not phone or not session_id:
        raise HTTPException(status_code=400, detail="phone and session_id required")

    logging.info(f"SYNC request: {q!r}")
    res = await answer_sync(q, phone, session_id)
    return JSONResponse(res)


@app.get("/api/ask_stream")
async def ask_stream_route(
    phone: str = Query(...),
    session_id: str = Query(...),
    q: str = Query(...),
):
    """Streaming answer endpoint — returns JSON chunks via SSE."""
    if not phone or not session_id:
        raise HTTPException(status_code=400, detail="phone and session_id required")

    logging.info(f"STREAM request: {q!r}")
    gen = answer_stream(q, phone, session_id)
    return StreamingResponse(gen, media_type="text/event-stream")


@app.get("/api/history")
async def history(
    phone: str = Query(...),
    session_id: str = Query(...),
    limit: int = Query(200),
):
    """Return saved chat messages for a session."""
    rows = await get_session_history(phone, session_id, limit)

    safe_rows = []
    for r in rows:
        r = dict(r)
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
        safe_rows.append(r)

    return JSONResponse(safe_rows)


@app.get("/api/sessions")
async def sessions(phone: str = Query(...)):
    """Return list of session IDs for a user."""
    sess = await list_sessions(phone)
    return {"sessions": sess}


@app.get("/api/get_or_create_session")
async def get_or_create_session(phone: str = Query(...)):
    """
    Returns the active session for a phone number,
    or creates a new one if none exists.
    """
    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")

    try:
        sess = await get_or_create_session_id(phone)
        logging.info(f"Session resolved: phone={phone} → {sess}")
        return {"session": sess}
    except Exception:
        logging.exception("Failed to get_or_create_session")
        raise HTTPException(status_code=500, detail="Session service unavailable")


@app.post("/api/close_session")
async def close_session_api(phone: str | None = Query(default=None)):
    """Close all active sessions for a phone number."""
    logging.info(f"[API] close_session | phone={phone!r}")

    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")

    try:
        session_ids: List[str] = await close_session_for_phone(phone)

        if not session_ids:
            logging.warning("[API] No active sessions found to close")
            return {"closed": False, "mode": "phone", "session_ids": []}

        closed = await clear_redis_session(phone, session_ids)
        logging.info(f"[API] Closed {len(session_ids)} session(s), Redis cleared={closed}")

        return {"closed": closed, "mode": "phone", "session_ids": session_ids}

    except Exception:
        logging.exception("Failed to close session")
        raise HTTPException(status_code=500, detail="Failed to close session")


# ── Serve React frontend (built files) ──────────────────────
# Activated only when support_ui/dist exists (after npm run build)
_DIST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "support_ui", "dist")
)

if os.path.isdir(_DIST):
    # Static assets: JS, CSS, images
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_DIST, "assets")),
        name="assets",
    )

    # Serve any other static files at root (favicon, vite.svg, etc.)
    @app.get("/vite.svg", include_in_schema=False)
    async def vite_svg():
        return FileResponse(os.path.join(_DIST, "vite.svg"))

    # Catch-all: return index.html for all non-API paths (React Router)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
