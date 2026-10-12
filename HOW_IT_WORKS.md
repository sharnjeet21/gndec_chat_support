# GNDEC AI Assistant — How Everything Works

> This document explains **every** technology in the GNDEC RAG chatbot, step by step.
> Every value that can be customised is read from the `.env` file — **nothing is hardcoded.**

---

## Table of Contents

1. [What is This System?](#1-what-is-this-system)
2. [The Journey of a Single Question](#2-the-journey-of-a-single-question)
3. [Knowledge Base (FAISS)](#3-knowledge-base-faiss)
4. [Keyword Search (BM25)](#4-keyword-search-bm25)
5. [Hybrid Retrieval & Re-ranking](#5-hybrid-retrieval--re-ranking)
6. [The LLM Provider Chain](#6-the-llm-provider-chain)
7. [Conversation Memory (Redis)](#7-conversation-memory-redis)
8. [Persistent Chat History (PostgreSQL)](#8-persistent-chat-history-postgresql)
9. [RAG Pipeline Stages](#9-rag-pipeline-stages)
10. [Domain Guard & Safety Filters](#10-domain-guard--safety-filters)
11. [Semantic Cache](#11-semantic-cache)
12. [API Layer (FastAPI)](#12-api-layer-fastapi)
13. [Frontend (React + Vite)](#13-frontend-react--vite)
14. [Voice Input (Groq Whisper)](#14-voice-input-groq-whisper)
15. [Infrastructure (Docker + Cloudflare)](#15-infrastructure-docker--cloudflare)
16. [Full .env Variable Reference](#16-full-env-variable-reference)
17. [How to Start Everything](#17-how-to-start-everything)

---

## 1. What is This System?

The GNDEC AI Assistant is a **Retrieval-Augmented Generation (RAG)** chatbot. RAG means the system does not rely on an LLM's training data to answer questions. Instead, it:

1. Stores verified GNDEC facts in a searchable database.
2. When a question arrives, it **retrieves** the most relevant facts.
3. It **feeds those facts** to the LLM along with the question.
4. The LLM generates an answer using **only** those facts — no hallucination.

This makes answers grounded, accurate, and up-to-date with real college data.

---

## 2. The Journey of a Single Question

Here is the complete lifecycle, from the student typing a question to the answer appearing on screen:

```
Student types: "What is the B.Tech CSE fee?"
                        │
                        ▼
          ┌─────────────────────────┐
          │   Browser (React UI)    │
          │  Sends: GET /api/ask_stream│
          │  Header: X-API-KEY: ***  │
          └────────────┬────────────┘
                       │ HTTPS
                       ▼
          ┌─────────────────────────┐
          │   FastAPI Auth Layer    │  ← checks X-API-KEY against API_KEY in .env
          └────────────┬────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │   Domain Guard          │  ← Is this a GNDEC question? (FAISS cosine check)
          └────────────┬────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │   Semantic Cache        │  ← Was this exact question answered recently in Redis?
          └────────────┬────────────┘
                       │ (cache miss — continues)
                       ▼
          ┌─────────────────────────┐
          │   FAISS Retrieval       │  ← Top-20 semantically similar docs from vector index
          │   + BM25 Retrieval      │  ← Top-20 keyword-matching docs
          │   → RRF Fusion          │  ← Combines & re-ranks → Top-8 best docs
          │   → Cross-Encoder       │  ← Re-ranks final Top-5 by relevance score
          └────────────┬────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │   Redis (Memory)        │  ← Loads last 10 messages for this session
          └────────────┬────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │   LLM Generation        │  ← GROQ/OMNIROUTE/NVIDIA/OLLAMA (auto-failover)
          │   Prompt = rules +       │
          │   history + top-5 docs + │
          │   student question       │
          └────────────┬────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │   Groundedness Check    │  ← LLM verifies its own answer vs. sources
          └────────────┬────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │   Save to Redis         │  ← Updates hot session memory (TTL: SESSION_TTL)
          │   Save to PostgreSQL    │  ← Permanent chat log
          └────────────┬────────────┘
                       │ SSE stream
                       ▼
          ┌─────────────────────────┐
          │   Browser renders       │  ← Answer appears word-by-word
          └─────────────────────────┘
```

---

## 3. Knowledge Base (FAISS)

**File:** `backend/build_vector_db.py`  
**Output:** `backend/faiss_store/faq.index` + `backend/faiss_store/meta.json`

### What is FAISS?

FAISS (Facebook AI Similarity Search) is a library for finding the most similar items in a collection of vectors. In our case, every GNDEC fact is converted into a vector (a list of 384 numbers), and FAISS finds the most relevant facts for any question in under 1 millisecond.

### What gets indexed?

| Data File | What it Contains |
|---|---|
| `data/gndec_facts.json` | Hand-written, verified facts about GNDEC |
| `data/gndec_data.json` | Scraped content from gndec.ac.in |
| `data/faculty.json` | 271 faculty members — names, designations, departments, emails |
| `data/syllabi.json` | Course syllabi and semester schemes |
| `data/tnp_data.json` | Training & Placement placement statistics |
| `data/external_facts.json` | External verified sources |
| `data/fee_structures.json` | Full fee tables for every program and semester |
| `data/courses_offered.json` | Complete list of UG, PG, and PhD programs |

### How it's built

Each fact is written as a combined string:
```
Q: What is the B.Tech fee for 1st semester?
A: The fee is Rs. 68,429 for General category...
Section: Fee Structure
```

The embedding model `intfloat/multilingual-e5-small` (configured via `EMBEDDING_MODEL_NAME`) converts this string into a 384-dimensional float32 vector. All vectors are L2-normalised and stored in a `faiss.IndexFlatIP` (Inner Product = cosine similarity after normalisation).

**Why IndexFlatIP?** It performs exact search (no approximation) which is fast enough at our scale (tens of thousands of documents) and guarantees finding the truly closest match every time.

**`.env` variables:**
```env
FAISS_DIR=backend/faiss_store
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
```

### Rebuilding the index

```bash
.venv/bin/python backend/build_vector_db.py
```

Run this any time you update the data files.

---

## 4. Keyword Search (BM25)

**File:** `backend/vectorstore.py`

BM25 (Best Match 25) is the algorithm that powers traditional search engines. It scores documents based on exact keyword frequency and document length. BM25 excels at:

- Finding exact terms (e.g., "hostel fee boys 1st semester")
- Matching rare/specific keywords that semantic search might miss

All documents except `fee_structures.json` are loaded into the BM25 index at startup. Fee documents are excluded because loading 26,000+ fee rows into BM25 would make startup take 10+ minutes — they are still fully available via FAISS.

---

## 5. Hybrid Retrieval & Re-ranking

**File:** `backend/vectorstore.py`

Neither FAISS nor BM25 alone is perfect. FAISS understands meaning but can miss exact terms. BM25 matches exact terms but misses paraphrasing. The system combines both using **Reciprocal Rank Fusion (RRF)**:

```
For each document in either result set:
  combined_score += 1 / (rank_in_faiss_list + 60) × 0.5
  combined_score += 1 / (rank_in_bm25_list + 60) × 0.5

→ Sort by combined_score descending
→ Return top-8 documents
```

The constant `60` prevents any single top-ranked document from dominating. Equal weights `0.5` ensure both signals contribute equally.

### Cross-Encoder Re-ranking

After RRF produces the top-8 candidates, a **Cross-Encoder** model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) re-scores each document by reading both the question and document together. This produces much more accurate relevance scores than vector similarity alone. The final Top-5 most relevant documents are sent to the LLM.

### Score Threshold

FAISS results below cosine score `0.5` are discarded before RRF. This prevents clearly irrelevant documents from entering the context.

---

## 6. The LLM Provider Chain

**File:** `backend/llm/llm.py`

The system never locks to a single AI provider. When one fails, it automatically tries the next. This guarantees near-100% uptime even if individual providers have outages or rate limits.

### Provider Priority (configurable via `.env`)

```
PROVIDER_PRIORITY=GROQ,OMNIROUTE,NVIDIA,OLLAMA
```

| Tier | Provider | Speed | Cost | Models |
|---|---|---|---|---|
| 1 | **GROQ** | ~800 tok/s | Free tier + paid | Qwen, Llama 3.3, Mixtral |
| 2 | **OMNIROUTE** | Fast | Antigravity | Gemini Flash |
| 3 | **NVIDIA NIM** | Medium | Paid | Nemotron 120B |
| 4 | **OLLAMA** | Slowest | Free (local) | Llama 3.1, Phi-3 |

### How Failover Works

```python
for each (provider, model) in priority_list:
    if model is in cooldown → skip
    try:
        response = call_api(model)
        return response  ← success, done
    except rate_limit (429):
        put model in 60s cooldown
    except model_not_found (400):
        record failure, skip model
    except other_error:
        record failure
    if model fails 3 times → put in cooldown

raise "All providers exhausted"
```

### Groq Auto-Discovery

Groq's model list changes frequently (models are added/removed). The system fetches the live model list from Groq's API every 6 hours (`GROQ_MODELS_CACHE_TTL`) and caches it. If the API is unreachable, it falls back to a hardcoded list (`GROQ_MODEL_FALLBACK` in `llm.py`).

Override which Groq models to try:
```env
GROQ_MODEL_PRIORITY=llama-3.3-70b-versatile,qwen/qwen3.8-27b
```

### Docker Bridge

When running inside Docker, `localhost` in `OMNIROUTE_BASE_URL` is automatically rewritten to `host.docker.internal` so the container can reach your local OmniRoute proxy. This is detected by checking for `/.dockerenv`.

**`.env` variables:**
```env
MODEL_PROVIDER=MULTI
PROVIDER_PRIORITY=GROQ,OMNIROUTE,NVIDIA,OLLAMA

GROQ_API_KEY=gsk_...
GROQ_API_BASE=https://api.groq.com/openai/v1
GROQ_MODEL_PRIORITY=qwen/qwen3.8-27b,openai/gpt-oss-120b

OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_API_KEY=sk-...
OMNIROUTE_MODELS=antigravity/gemini-3.8-flash-tiered

NVIDIA_NIM_API_KEY=nvapi-...
NVIDIA_NIM_API_BASE=https://integrate.api.nvidia.com/v1
NVIDIA_MODELS=nvidia/nemotron-3-super-120b-a12b

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODELS=llama3.1:8b,phi3:mini

LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.1
LLM_TOP_P=0.9
LLM_COOLDOWN_SEC=60
```

---

## 7. Conversation Memory (Redis)

**File:** `backend/db.py`, `backend/agent.py`

Redis stores **hot, temporary conversation history** so users can ask follow-up questions:
> "What about the hostel fee?" → the system remembers the previous "B.Tech fee" question.

### How it works

Every session is keyed as `{phone}:{session_id}` in Redis. The last **10 messages** of each session are kept in memory using `RedisChatMessageHistory` from LangChain.

Sessions auto-expire after `SESSION_TTL` seconds (default: 7 days). This prevents Redis from growing indefinitely.

**Graceful Fallback:** If Redis is unavailable at startup, the system uses an in-memory Python dict. The chat still works — it just resets on server restart.

**`.env` variables:**
```env
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
SESSION_TTL=604800
```

---

## 8. Persistent Chat History (PostgreSQL)

**File:** `backend/chat_store.py`, `init.sql`

PostgreSQL stores the **permanent, complete chat history** for every user. While Redis is ephemeral (expires after 7 days), PostgreSQL keeps everything forever.

### Database Tables

**`sessions`** — tracks each conversation:
```sql
id           VARCHAR  -- session_id
phone        VARCHAR  -- user's phone/identifier
title        VARCHAR  -- first message (used as chat title)
is_active    BOOLEAN
created_at   TIMESTAMP
```

**`messages`** — every single message:
```sql
id           SERIAL
session_id   VARCHAR
role         VARCHAR  -- 'user' or 'assistant'
content      TEXT
created_at   TIMESTAMP
```

After every LLM response, two writes happen in parallel:
1. Redis: sliding 10-message window for fast in-context retrieval
2. PostgreSQL: permanent append for history, analytics, and support

**`.env` variables:**
```env
DATABASE_URL=postgresql://support_user:support_pass@postgres:5432/support_ai
```

---

## 9. RAG Pipeline Stages

**Directory:** `backend/rag/`

The core logic is split into 6 ordered stages that each read from and write to a shared `PipelineContext` object:

```
PipelineContext {
  query, phone, session_id, language
  policy      → PolicyOutput       (ALLOW / DENY / REDIRECT / CLARIFY)
  resolution  → ResolutionOutput   (strategy, sub_queries)
  retrieval   → RetrievalOutput    (faiss_docs, bm25_docs, combined_docs)
  generation  → GenerationOutput   (answer, citations)
  verification→ VerificationOutput (GROUNDED / UNGROUNDED / SKIPPED, confidence)
  persistence → PersistenceRecord  (saved to DB)
  metadata    {} (cached, request_id, latency, etc.)
  errors      []
}
```

| Stage | File | What it does |
|---|---|---|
| **1. Policy** | `policy.py` | Decides if the query is allowed, should be denied, redirected, or needs clarification. Runs toxicity + domain checks. |
| **2. Resolution** | `resolution.py` | Plans retrieval strategy. Detects if the query needs multiple sub-queries (e.g., "compare B.Tech and M.Tech fees"). |
| **3. Retrieval** | `retrieval.py` | Runs FAISS + BM25 + RRF + Cross-Encoder to get the top-5 most relevant documents. |
| **4. Generation** | `generation.py` | Assembles the full prompt (system rules + chat history + retrieved docs + query) and calls the LLM. |
| **5. Verification** | `verification.py` | Uses a second LLM call to verify the answer is actually supported by the retrieved documents. If not grounded → abstain. |
| **6. Persistence** | `persistence.py` | Saves the Q&A to Redis and PostgreSQL. Only runs if verification passes. |

### The Generation Prompt Structure

```
[SYSTEM RULES]
You are the official GNDEC information assistant.
1. Answer ONLY using the provided GNDEC knowledge context...
...9 more strict rules...

[CONVERSATION HISTORY]
human: What programs does GNDEC offer?
assistant: GNDEC offers B.Tech in CSE, IT, ME...

[RETRIEVED KNOWLEDGE]
[1] Q: What is the B.Tech CSE fee?
    A: Rs. 68,429 for General category... (Source: fee_structures.json)
[2] Q: What is the hostel fee?
    A: Boys hostel Rs. 20,300... (Source: gndec_facts.json)
...

[STUDENT QUESTION]
What is the B.Tech CSE fee?

Answer:
```

---

## 10. Domain Guard & Safety Filters

**Files:** `backend/domain_guard.py`, `backend/verify.py`

### Domain Guard

Before spending any LLM tokens, the system checks if the question is actually about GNDEC:

```python
# Embed the query into a vector
vec = embed_model.encode([query])

# Find the closest document in the entire FAISS index
score, idx = faiss_index.search(vec, k=1)

# If the nearest document is < 65% similar, the question is off-topic
if score < OUT_OF_DOMAIN_THRESHOLD (0.65):
    return "I can only answer questions about GNDEC college."
```

If a student asks "write me a Python program" — the closest GNDEC document is maybe 30% similar — so the question is immediately rejected, no LLM cost incurred.

### Toxicity Filter

A fast regex-based check blocks slurs, threats, and offensive language before they reach the LLM. Returns `WARNING_TEXT` immediately.

### Sensitive Query Abstention

Certain categories of questions are always refused regardless of context (e.g., "Is Professor X good or bad?", exam questions, homework assignments). This is handled by `check_sensitive_or_unanswerable()` in `verify.py`.

### Groundedness Verification (`verify_groundedness`)

After the LLM generates an answer, a verification LLM call checks:
> "Given this retrieved context, is the following answer actually supported by it? Yes or No?"

If the answer is **not grounded** (the LLM hallucinated something not in the documents), the answer is replaced with the `ABSTENTION_MESSAGE`.

---

## 11. Semantic Cache

**File:** `backend/cache.py`

If two students ask the exact same question within a short time window, the second answer is served instantly from Redis without calling the LLM or doing retrieval. This:

- Cuts latency from ~3s to ~50ms for common questions
- Saves API credits
- Reduces load on the system

The cache uses **semantic similarity** (not exact string matching), so "btech fee" and "what is the b.tech fee?" both hit the same cached answer.

Cache is stored in Redis with the same `REDIS_URL` used for conversation memory.

---

## 12. API Layer (FastAPI)

**File:** `backend/app.py`

FastAPI exposes the backend as a set of HTTP endpoints. It is served by Uvicorn on port `8000`.

### Authentication

Every `/api/*` request must include the `X-API-KEY` header matching the `API_KEY` variable from `.env`:

```env
API_KEY=naman@1234
```

The middleware skips auth for `/health` and all non-`/api` paths (static files):

```python
@app.middleware("http")
async def verify_api_key(request, call_next):
    if path == "/health" or not path.startswith("/api"):
        return await call_next(request)  # No auth needed
    if request.headers.get("X-API-KEY") != API_KEY:
        return JSONResponse(401, {"detail": "Unauthorized"})
```

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | ❌ | Liveness probe — always returns `{"status":"ok"}` |
| `GET` | `/api/ask` | ✅ | Sync answer — waits for full answer, returns JSON |
| `GET` | `/api/ask_stream` | ✅ | **Primary endpoint** — streams answer chunks via SSE |
| `GET` | `/api/search` | ✅ | Raw FAISS search — skips LLM, returns raw docs |
| `POST` | `/api/transcribe` | ✅ | Converts voice recording to text (Groq Whisper) |
| `GET` | `/api/start_session` | ✅ | Creates a new chat session in PostgreSQL |
| `GET` | `/api/sessions` | ✅ | Lists all sessions for a phone number |
| `GET` | `/api/history` | ✅ | Returns full message history for a session |
| `GET` | `/api/get_or_create_session` | ✅ | Returns existing session or creates new one |
| `POST` | `/api/close_session` | ✅ | Clears Redis memory + marks session inactive |
| `GET` | `/*` | ❌ | Serves React frontend (`support_ui/dist/`) |

### CORS

Allowed origins are configured via `.env`:

```env
FRONTEND_URLS=http://localhost:5173,http://localhost:3010
```

---

## 13. Frontend (React + Vite)

**Directory:** `support_ui/`

The chat interface is built with **React** and bundled with **Vite**. The compiled output lives in `support_ui/dist/` and is served directly by FastAPI (no separate web server needed).

### How the frontend connects

All API calls flow through `support_ui/src/api.js`. It reads two values from `support_ui/.env`:

```env
VITE_API_URL=          # empty = same origin (FastAPI serves both)
VITE_API_KEY=naman@1234
```

Every request includes the key:
```javascript
function authHeaders() {
  return {
    "X-API-KEY": import.meta.env.VITE_API_KEY || "naman@1234",
    "ngrok-skip-browser-warning": "true",
  };
}
```

### Streaming

The frontend uses the browser's native `ReadableStream` API to receive SSE chunks from `/api/ask_stream`. Each chunk is a JSON line of one of three types:

```json
{"type": "sources", "sources": [...]}          ← received first (before LLM starts)
{"type": "content", "delta": "GNDEC offers..."}  ← received per-line as LLM generates
{"type": "blocked", "message": "..."}            ← received if query was rejected
{"type": "meta", "verification_status": "grounded"} ← received last
```

### Build for Production

```bash
cd support_ui
npm install
npm run build
```

This outputs to `support_ui/dist/` which FastAPI automatically serves.

---

## 14. Voice Input (Groq Whisper)

**File:** `backend/app.py` — `/api/transcribe`

The frontend can record audio directly from the microphone. The audio blob is uploaded to `/api/transcribe`, which sends it to Groq's Whisper API for transcription:

```env
GROQ_API_KEY=gsk_...   ← same key used for chat, also powers Whisper
```

The transcribed text is then sent to `/api/ask_stream` exactly like a typed message. Supported audio formats: `webm`, `mp3`, `mp4`, `wav`, `m4a`, `ogg`, `flac` (max 25MB).

---

## 15. Infrastructure (Docker + Cloudflare)

### Docker Compose

Three containers work together:

```yaml
# docker-compose.yml
tech_support_postgres:  PostgreSQL 16 — stores chat history permanently
tech_support_redis:     Redis 7 — stores hot session memory + semantic cache
tech_support_web:       FastAPI backend + React frontend (port 8000)
```

The `web` container:
- Loads all secrets from `.env` via `env_file: .env`
- Mounts `backend/`, `data/`, and `scripts/` as live volumes (code changes apply instantly without rebuilding)
- Uses `extra_hosts: host.docker.internal:host-gateway` to reach host services (Ollama, OmniRoute)

### Cloudflare Tunnel

`cloudflared` creates a secure HTTPS public URL that tunnels to `localhost:8000`. This exposes the local backend to the internet without opening firewall ports or needing a public IP. The tunnel URL is saved to `cloudflare_startup.log`.

### Health Checks

Both `postgres` and `redis` containers run health checks. The `web` container only starts after both are healthy, preventing startup failures due to race conditions.

---

## 16. Full .env Variable Reference

Copy this to a `.env` file at the project root and fill in your values:

```env
# ────────────────────────────────────────────
# DATABASE (PostgreSQL)
# ────────────────────────────────────────────
# Docker: use 'postgres' hostname
# Local dev: use 'localhost'
DATABASE_URL=postgresql://support_user:support_pass@postgres:5432/support_ai

# ────────────────────────────────────────────
# REDIS (Session Memory + Cache)
# ────────────────────────────────────────────
# Docker: use 'redis' hostname
# Local dev: use 'localhost'
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
SESSION_TTL=604800        # 7 days in seconds

# ────────────────────────────────────────────
# LLM PROVIDER CHAIN
# ────────────────────────────────────────────
# Set MODEL_PROVIDER to a single name (GROQ, OMNIROUTE, NVIDIA, OLLAMA)
# or MULTI to use all providers with auto-failover in priority order
MODEL_PROVIDER=MULTI
PROVIDER_PRIORITY=GROQ,OMNIROUTE,NVIDIA,OLLAMA

# ── GROQ (Tier 1 — fastest) ─────────────────
GROQ_API_KEY=gsk_...
GROQ_API_BASE=https://api.groq.com/openai/v1
# Optional: comma-separated list to override auto-fetched models
GROQ_MODEL_PRIORITY=qwen/qwen3.8-27b,openai/gpt-oss-120b,openai/gpt-oss-20b
GROQ_MODELS_CACHE_TTL=21600   # Refresh model list every 6 hours

# ── OMNIROUTE (Tier 2 — antigravity) ─────────
OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_API_KEY=sk-...
OMNIROUTE_MODELS=antigravity/gemini-3.8-flash-tiered,antigravity/gemini-3.7-flash-tiered

# ── NVIDIA NIM (Tier 3) ───────────────────────
NVIDIA_NIM_API_KEY=nvapi-...
NVIDIA_NIM_API_BASE=https://integrate.api.nvidia.com/v1
NVIDIA_MODELS=nvidia/nemotron-3-super-120b-a12b,nemotron-3-8b-instruct

# ── OLLAMA (Tier 4 — local fallback) ─────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODELS=llama3.1:8b,llama3:8b,phi3:mini

# ── Shared LLM Settings ───────────────────────
LLM_MODEL=qwen/qwen3.8-27b      # Used by legacy single-model callers
LLM_MAX_TOKENS=1024             # Max tokens the LLM can output
LLM_TEMPERATURE=0.1             # Lower = more deterministic/factual
LLM_TOP_P=0.9                   # Nucleus sampling probability
LLM_COOLDOWN_SEC=60             # Seconds to cool down a rate-limited model

# ────────────────────────────────────────────
# VECTORSTORE (FAISS)
# ────────────────────────────────────────────
FAISS_DIR=backend/faiss_store
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small

# ────────────────────────────────────────────
# API SECURITY
# ────────────────────────────────────────────
API_KEY=naman@1234              # X-API-KEY header value required for all /api/* calls
SECRET_KEY=your-32-char-random-key  # Used for JWT/session signing

# ────────────────────────────────────────────
# CORS — Frontend Origins
# ────────────────────────────────────────────
FRONTEND_URLS=http://localhost:5173,http://localhost:3010

# ────────────────────────────────────────────
# OPTIONAL SERVICES
# ────────────────────────────────────────────
# Tavily web search (set to 'dummy_key' to disable gracefully)
TAVILY_API_KEY=

# Email notifications
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# Public URL (used in emails / links)
PUBLIC_BASE_URL=http://localhost:3010
BACKEND_API_ENDPOINT=http://localhost:8001
```

---

## 17. How to Start Everything

### Option A — Docker (Recommended)

```bash
# 1. Copy and fill in your .env
cp .env.example .env
# Edit .env with your API keys

# 2. Start all containers
docker compose up -d

# 3. Check everything is healthy
docker compose ps
curl http://localhost:8000/health
```

### Option B — Local Development (No Docker)

```bash
# 1. Start PostgreSQL and Redis separately (or use Docker just for those)
docker compose up -d postgres redis

# 2. Activate Python environment
source .venv/bin/activate

# 3. Build FAISS index (first time only, or after data changes)
python backend/build_vector_db.py

# 4. Start FastAPI backend
DATABASE_URL=postgresql://support_user:support_pass@localhost:5432/support_ai \
REDIS_URL=redis://localhost:6379/0 \
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# 5. (Optional) Start frontend dev server with hot-reload
cd support_ui
npm install
npm run dev
```

### Verify Everything is Working

```bash
# Health
curl http://localhost:8000/health
# → {"status":"ok","service":"GNDEC AI Assistant"}

# Auth (should get 401)
curl http://localhost:8000/api/ask?phone=test&session_id=test&q=hi
# → {"detail":"Unauthorized: Invalid or missing API key"}

# With correct key (should get an answer)
curl "http://localhost:8000/api/ask?phone=test&session_id=test&q=What+is+GNDEC" \
     -H "X-API-KEY: naman@1234"
# → {"answer":"Guru Nanak Dev Engineering College...","sources":[...],...}
```

### Rebuild Frontend After Code Changes

```bash
cd support_ui
npm run build
# Restart the Docker container to pick up new dist/ files:
docker compose restart web
```
