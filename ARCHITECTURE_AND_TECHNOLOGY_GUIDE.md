# GNDEC RAG System — Architecture & Technology Guide

> **Audience:** Developers, contributors, and technical reviewers.  
> **Purpose:** Explain every major system component, how they interact, and why each technology was chosen.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Request Lifecycle](#2-request-lifecycle)
3. [Knowledge Base — FAISS Vector Index](#3-knowledge-base--faiss-vector-index)
4. [Hybrid Retrieval — FAISS + BM25 + RRF](#4-hybrid-retrieval--faiss--bm25--rrf)
5. [Multi-Tier LLM Provider Chain](#5-multi-tier-llm-provider-chain)
6. [Redis — Conversation Memory](#6-redis--conversation-memory)
7. [PostgreSQL — Persistent Chat Storage](#7-postgresql--persistent-chat-storage)
8. [RAG Pipeline — Stages & Contracts](#8-rag-pipeline--stages--contracts)
9. [Domain Guard & Safety Layer](#9-domain-guard--safety-layer)
10. [API Layer — FastAPI & Auth](#10-api-layer--fastapi--auth)
11. [Frontend — React + Vite + Tailwind](#11-frontend--vue--vite)
12. [Infrastructure & Deployment](#12-infrastructure--deployment)
13. [Environment Variables Reference](#13-environment-variables-reference)
14. [SerpAPI Live Web Search & Continuous Learning](#14-serpapi-live-web-search--continuous-learning)
15. [Dynamic Vector DB Ingestion & Persistence](#15-dynamic-vector-db-ingestion--persistence)
16. [Source File Attribution & Citation System](#16-source-file-attribution--citation-system)

---

## 1. System Overview

The GNDEC AI Assistant is a **Retrieval-Augmented Generation (RAG)** chatbot purpose-built for Guru Nanak Dev Engineering College, Ludhiana. It answers student and prospective-student questions about admissions, fee structures, faculty, courses, and campus life — exclusively from verified college data.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User (Browser)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│               FastAPI Backend  (port 8000)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Auth Middle  │  │  RAG Pipeline│  │  Streaming Endpoint   │  │
│  │  (X-API-KEY)│  │  (8 stages)  │  │  (/api/ask_stream)    │  │
│  └─────────────┘  └──────┬───────┘  └───────────────────────┘  │
└─────────────────────────-┼──────────────────────────────────────┘
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
  ┌───────▼───────┐ ┌──────▼──────┐ ┌────────▼────────┐
  │  FAISS Index  │ │  BM25 Index │ │  LLM Provider   │
  │ (vector store)│ │  (keyword)  │ │  GROQ→NIM→OLLAMA│
  └───────────────┘ └─────────────┘ └────────┬────────┘
                                             │
                              ┌──────────────┼──────────┐
                              │              │           │
                       ┌──────▼──┐  ┌────────▼──┐ ┌─────▼──────┐
                       │  Redis  │  │ PostgreSQL │ │ Cloudflare │
                       │(memory) │  │ (history)  │ │  Tunnel    │
                       └─────────┘  └───────────┘ └────────────┘
```

---

## 2. Request Lifecycle

A complete round-trip for a user message follows these steps:

```
1. Browser → POST /api/ask_stream?phone=X&session_id=Y&q=Z
2. Auth Middleware checks X-API-KEY header
3. Domain Guard checks if query is GNDEC-related (cosine similarity threshold)
4. Toxicity / Sensitive-query filter
5. Semantic Cache lookup (skip LLM if recent identical query exists)
6. Hybrid Retrieval: FAISS (semantic) + BM25 (keyword) → RRF fusion → top-K docs
7. Prompt Assembly: System prompt + conversation history (Redis) + retrieved docs
8. LLM Generation: GROQ → OMNIROUTE → NVIDIA → OLLAMA (auto-failover)
9. Groundedness Verification: LLM checks its own answer against source docs
10. Answer streamed chunk-by-chunk via SSE to browser
11. Message saved to Redis (hot) and PostgreSQL (cold/persistent)
```

---

## 3. Knowledge Base — FAISS Vector Index

**File:** [`backend/build_vector_db.py`](backend/build_vector_db.py)  
**Output:** `backend/faiss_store/faq.index` + `backend/faiss_store/meta.json`

### What it indexes

| Source File | Content |
|---|---|
| `data/gndec_facts.json` | Hand-curated high-confidence facts |
| `data/gndec_data.json` | Scraped website content |
| `data/faculty.json` | Faculty names, designations, emails, departments |
| `data/syllabi.json` | Course syllabi and scheme documents |
| `data/tnp_data.json` | Training & Placement cell data |
| `data/external_facts.json` | Verified external source facts |
| `data/fee_structures.json` | Detailed per-program, per-semester fee tables |
| `data/courses_offered.json` | Complete list of programs offered |

### How it works

Each `{question, answer, section}` triple is concatenated into a single string and embedded using `all-MiniLM-L6-v2` (a 384-dimensional Sentence Transformer). The resulting float32 vectors are L2-normalized and stored in a `faiss.IndexFlatIP` (Inner Product = cosine similarity after normalization).

**Why FAISS?**
- Runs entirely on CPU, zero GPU required.
- Sub-millisecond similarity search over tens of thousands of vectors.
- Zero network latency (file-based index, loaded on startup).

**Why `all-MiniLM-L6-v2`?**
- Optimized for semantic similarity, not just keyword matching.
- Small and fast (6-layer MiniLM), suited for CPU-only environments.
- Strong performance on question-answer pair retrieval tasks.

---

## 4. Hybrid Retrieval — FAISS + BM25 + RRF

**File:** [`backend/vectorstore.py`](backend/vectorstore.py)

Pure vector search excels at semantic understanding but can miss exact keywords. Pure keyword (BM25) search finds exact terms but misses paraphrasing. Combining both gives the best of both worlds.

### Step-by-Step

```
Query: "How much is the hostel fee for B.Tech 1st semester?"
         │
         ├─► FAISS: encodes query → finds top-20 semantically similar docs
         │          (e.g. finds fee-related docs even without the word "hostel")
         │
         ├─► BM25: tokenizes query → finds top-20 keyword-matching docs
         │         (e.g. finds docs containing the exact word "hostel")
         │
         └─► RRF Fusion (Reciprocal Rank Fusion):
                 For each doc:
                   score += 1/(rank_in_faiss_results + 60) * 0.5
                   score += 1/(rank_in_bm25_results + 60) * 0.5
                 Sort by combined score → return top-K (default: 8 docs)
```

**FAISS score threshold:** Documents with a cosine score < `0.5` are discarded before fusion. This prevents low-quality matches from polluting the context.

**BM25 exclusion:** `fee_structures.json` documents are excluded from the BM25 index because 26,000+ fee rows would make startup take 10+ minutes. Fee documents are still fully indexed in FAISS.

---

## 5. Multi-Tier LLM Provider Chain

**File:** [`backend/llm/llm.py`](backend/llm/llm.py)

The system never hard-codes a single LLM. Instead, it maintains a prioritized list of providers and models. If one fails (rate limit, model decommissioned, network error), it automatically tries the next.

### Provider Priority

```
Tier 1: GROQ         — Fastest inference (800+ tok/s), multiple Llama/Qwen models
Tier 2: OMNIROUTE    — Antigravity-managed routing (Gemini Flash, etc.)
Tier 3: NVIDIA NIM   — NVIDIA-hosted Nemotron / Llama models
Tier 4: OLLAMA       — Local offline fallback (llama3.1:8b, phi3:mini)
```

### Failover Logic

```python
for provider, client, model in tier_list:
    if model is on 60s cooldown → skip
    try:
        response = await client.chat.completions.create(model=model, ...)
        reset_failure_count(model)
        return response  ← success, stop here
    except RateLimitError (429):
        mark_cooldown(model, 60s)
    except ModelNotFound (400):
        record_failure(model)
        if failures >= 3: mark_cooldown(model)
    except other:
        record_failure(model)

raise RuntimeError("All tiers exhausted")
```

### Docker Networking

When running inside a Docker container, `localhost` in `OMNIROUTE_BASE_URL` is automatically rewritten to `host.docker.internal` so the container can reach services on the host machine. This is detected via the presence of `/.dockerenv`.

### Groq Model Auto-Discovery

Instead of hardcoding Groq model names, the system fetches the live model list from `api.groq.com/openai/v1/models` and caches it for 6 hours. If the fetch fails, it falls back to a hardcoded list (`GROQ_MODEL_FALLBACK`). This ensures deprecated models are never used.

---

## 6. Redis — Conversation Memory

**File:** [`backend/db.py`](backend/db.py), [`backend/agent.py`](backend/agent.py)

Redis stores **hot conversation history** — the last 10 messages of every active session. This enables contextual follow-up questions (e.g., "What about the hostel?" after asking about fees).

### Implementation

Each session is keyed as `{phone}:{session_id}` in Redis. The `RedisChatMessageHistory` from `langchain_community` serializes and deserializes messages. A TTL of 7 days (`SESSION_TTL=604800`) ensures stale sessions are automatically garbage-collected.

**Fallback:** If Redis is unavailable at startup, the system gracefully falls back to an in-memory `ChatMessageHistory` dict, which resets on restart but keeps the app functional.

---

## 7. PostgreSQL — Persistent Chat Storage

**File:** [`backend/chat_store.py`](backend/chat_store.py), [`init.sql`](init.sql)

PostgreSQL stores the **cold/permanent record** of every conversation. While Redis is ephemeral (TTL-based), PostgreSQL keeps the full chat history permanently for support, analytics, and audit purposes.

| Table | Purpose |
|---|---|
| `sessions` | Maps `phone` + `session_id` to a session record with timestamps |
| `messages` | Stores every user and assistant message with its session ID |

After each successful LLM response, two writes happen:
1. `Redis` — updates the sliding 10-message window for memory.
2. `PostgreSQL` — appends the message to the permanent log (`save_message`).

---

## 8. RAG Pipeline — Stages & Contracts

**Directory:** [`backend/rag/`](backend/rag/)

The core pipeline is organized as a series of composable stages, each reading from and writing to a shared `PipelineContext` object.

```
PipelineContext
    ├── query (str)
    ├── phone / session_id
    ├── retrieval (RetrievalResult)
    │       ├── faiss_documents
    │       ├── bm25_documents
    │       └── combined_documents (after RRF)
    ├── generation (GenerationResult)
    │       ├── answer (str)
    │       └── citations (List[dict])
    ├── verification (VerificationResult)
    │       └── status (GROUNDED | UNGROUNDED | SKIPPED)
    ├── metadata (dict)  ← cached, request_id, latency, etc.
    └── errors (List[str])
```

### Groundedness Verification

After generating an answer, the pipeline runs a second, lightweight LLM call to verify the answer is actually supported by the retrieved source documents. If the answer is deemed **ungrounded** (i.e., the LLM hallucinated), the response is replaced with a safe abstention message. This is the final anti-hallucination guard.

---

## 9. Domain Guard & Safety Layer

**Files:** [`backend/domain_guard.py`](backend/domain_guard.py), [`backend/verify.py`](backend/verify.py)

### Domain Guard

Before any retrieval or LLM call, every query is checked against the FAISS index:

```python
score, idx = faiss_index.search(embed(query), k=1)
if score < OUT_OF_DOMAIN_THRESHOLD (0.65):
    return "I can only answer questions about GNDEC college."
```

If the nearest document in the entire knowledge base is less than 65% similar to the query, the query is considered out-of-domain and is immediately rejected — no LLM cost is incurred.

### Sensitive / Unanswerable Guard (`verify.py`)

A rule-based filter blocks queries that:
- Ask the bot to write code or solve assignments.
- Contain toxic or offensive language (regex-based pattern matching).
- Ask for personal opinions or subjective judgments.

The `ABSTENTION_MESSAGE` constant provides a consistent, polite refusal string for these cases.

### Strip Scrape Leaks (`strip_scrape_leaks`)

A post-processing step removes any raw HTML artifacts, CSS class names, or JavaScript snippets that might have been accidentally included in scraped source documents before they reach the LLM context.

---

## 10. API Layer — FastAPI & Auth

**File:** [`backend/app.py`](backend/app.py)

### Authentication

All `/api/*` routes require an `X-API-KEY` header matching the `API_KEY` environment variable (`naman@1234` by default). The middleware is intentionally simple — it's a shared secret for bot-level access control, not per-user auth.

```python
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    path = request.url.path
    if path == "/health" or not path.startswith("/api"):
        return await call_next(request)  # Public routes skip auth
    client_key = request.headers.get("X-API-KEY")
    if client_key != API_KEY:
        return JSONResponse(status_code=401, ...)
    return await call_next(request)
```

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe (no auth required) |
| `GET` | `/api/ask` | Sync question → JSON answer |
| `GET` | `/api/ask_stream` | SSE streaming question → chunked answer |
| `GET` | `/api/start_session` | Register a new chat session |
| `GET` | `/api/sessions` | List all sessions for a phone number |
| `GET` | `/api/history` | Full message history for a session |

### Static File Serving

The compiled Vue frontend (`support_ui/dist/`) is mounted as a static directory. Non-`/api` paths fall through to `index.html`, enabling client-side routing.

---

## 11. Frontend — Vue + Vite

**Directory:** [`support_ui/`](support_ui/)

The chat UI is built with **Vue 3** and **Vite**. It communicates exclusively through the [`support_ui/src/api.js`](support_ui/src/api.js) module, which:

- Injects `X-API-KEY` into every request from `VITE_API_KEY` (`.env` file).
- Uses the Fetch API with `ReadableStream` for SSE streaming.
- Handles three chunk types from the backend: `sources`, `content`, and `blocked`.

Build the frontend for production:
```bash
cd support_ui && npm run build
```
The output lands in `support_ui/dist/` which is automatically served by FastAPI.

---

## 12. Infrastructure & Deployment

### Docker Compose

```
tech_support_postgres  — PostgreSQL 16 (port 5432)
tech_support_redis     — Redis 7 (port 6379)
tech_support_web       — FastAPI app (port 8000)
```

The `web` service uses `env_file: .env` to inject all secrets. It mounts `backend/`, `data/`, and `scripts/` as volumes so code changes take effect without rebuilding the image.

`extra_hosts: host.docker.internal:host-gateway` enables the container to reach services on the host (e.g., a local Ollama instance or OmniRoute proxy).

### Public Tunnel (Cloudflare)

`cloudflared` creates a zero-config HTTPS tunnel to expose the local FastAPI server on a public URL. The tunnel URL is stored in `cloudflare_startup.log`.

### Startup

```bash
# Full Docker stack
docker compose up -d

# Local development (no Docker)
source .venv/bin/activate
DATABASE_URL=postgresql://support_user:support_pass@localhost:5432/support_ai \
REDIS_URL=redis://localhost:6379/0 \
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 13. Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `naman@1234` | Shared secret for all `/api/*` routes |
| `MODEL_PROVIDER` | `MULTI` | Active provider (`GROQ`, `OMNIROUTE`, `NVIDIA`, `OLLAMA`, or `MULTI`) |
| `PROVIDER_PRIORITY` | `GROQ,OMNIROUTE,NVIDIA,OLLAMA` | Failover order when `MODEL_PROVIDER=MULTI` |
| `GROQ_API_KEY` | *(set in .env)* | Groq API key |
| `GROQ_API_BASE` | `https://api.groq.com/openai/v1` | Groq base URL |
| `GROQ_MODEL_PRIORITY` | `openai/gpt-oss-120b,qwen/qwen3.8-27b,openai/gpt-oss-20b` | High-capacity fast model priority for Groq |
| `SERPAPI_KEY` | *(set in .env)* | SerpAPI private key for Google live search |
| `SERP_ALWAYS_SEARCH` | `true` | Always execute concurrent SerpAPI search on every user query |
| `SERP_SITE_RESTRICT` | `site:gndec.ac.in OR site:admission.gndec.ac.in...` | Domain restriction for GNDEC web searches |
| `SERP_MAX_RESULTS` | `5` | Maximum search snippets to retrieve and index per query |
| `SERP_FALLBACK_THRESHOLD` | `2` | Trigger web search if local FAISS/BM25 returns fewer docs |
| `SERP_TRIGGER_KEYWORDS` | `latest,recent,current,2025,2026,notice...` | Keywords that trigger live SerpAPI search |
| `SERP_ENGINE` | `google` | Search engine for SerpAPI queries |
| `NVIDIA_NIM_API_KEY` | *(set in .env)* | NVIDIA NIM API key |
| `NVIDIA_NIM_API_BASE` | `https://integrate.api.nvidia.com/v1` | NVIDIA base URL |
| `NVIDIA_MODELS` | `nvidia/nemotron-3-super-120b-a12b,...` | Models to try on NVIDIA NIM |
| `OMNIROUTE_BASE_URL` | `http://localhost:20128/v1` | OmniRoute proxy URL |
| `OMNIROUTE_API_KEY` | *(set in .env)* | OmniRoute API key |
| `OMNIROUTE_MODELS` | `xpl-/gpt-6-sol,xpl-/claude-opus-5.5,...` | Models to try on OmniRoute |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL |
| `OLLAMA_MODELS` | `llama3.1:8b,llama3:8b,phi3:mini` | Ollama model priority list |
| `LLM_MAX_TOKENS` | `4096` | Max tokens per LLM response |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature for factual precision |
| `LLM_COOLDOWN_SEC` | `60` | Seconds to cool down a rate-limited model |
| `DATABASE_URL` | `postgresql://...@postgres:5432/support_ai` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `SESSION_TTL` | `604800` | Redis session TTL in seconds (7 days) |
| `FAISS_DIR` | `backend/faiss_store` | Path to FAISS index directory |
| `EMBEDDING_MODEL_NAME` | `intfloat/multilingual-e5-small` | Multilingual E5 embedding model |
| `RERANKER_MODEL_NAME` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder reranking model |

---

## 14. SerpAPI Live Web Search & Continuous Learning

When users ask about active notices, live events, recent updates, or queries not covered in the base training scrape, the RAG pipeline leverages **SerpAPI (Google Search Engine)**:

1. **Query Sanitization**: Strips conversational filler ("who is", "tell me about") via `clean_web_query()` to maximize Google search precision.
2. **Domain Scoping**: Appends `site:gndec.ac.in OR site:admission.gndec.ac.in` to ensure 100% official college sources.
3. **Concurrent Execution**: Runs asynchronously via `asyncio.to_thread` alongside FAISS/BM25 so user response times remain fast.
4. **Knowledge Priority**: Live results are injected at the top of the prompt context with explicit `[File: gndec.ac.in (Live Web)]` headers.

---

## 15. Dynamic Vector DB Ingestion & Persistence

Whenever SerpAPI retrieves new facts or notices, the system dynamically indexes them into the local vector database via `backend.vectorstore.add_to_vector_db`:

- **Real-Time FAISS Ingestion**: Uses $O(1)$ `faiss_index.add(vectors)` with `intfloat/multilingual-e5-small` embeddings in <1ms.
- **BM25 Corpus Extension**: Appends tokenized documents and recalculates Okapi weights in ~100ms.
- **Disk Persistence**: Immediately writes updated index to `backend/faiss_store/faq.index`, `meta.json`, and records human-verifiable facts in `data/learned_facts.json`.
- **Subsequent Queries**: Future queries regarding the same subject are answered directly from the local vector database without making external SerpAPI network calls.

---

## 16. Source File Attribution & Citation System

To prevent ambiguous citations (such as bare numbers `[1]` with no context):
- Every document in the knowledge base and web search is tagged with its origin file (e.g. `fee_structures.json`, `faculty.json`, `admission_process.json`, `external_facts.json`, `courses_offered.json`, `gndec.ac.in`).
- The prompt instructs the LLM:
  `When referencing information, cite the source file and number inline (e.g. [1: fee_structures.json]). At the very end, include an explicit '### Sources' section listing every referenced file and title.`
- The frontend `SourceCard` displays the exact file badge `[1] admission_process.json` alongside direct clickable links to official pages.
