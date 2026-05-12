# GNDEC AI Assistant

An AI-powered RAG (Retrieval-Augmented Generation) chatbot for **Guru Nanak Dev Engineering College (GNDEC), Ludhiana**. Built to answer questions about admissions, departments, fees, faculty, facilities, placements, and college life — directly from official GNDEC website data.

---

## What It Does

Students and visitors can chat with the bot to get instant, accurate answers about GNDEC without navigating the website. The bot retrieves relevant knowledge from a vector database built from scraped GNDEC web pages and curated facts, then generates a natural language response using a local LLM (Llama 3.2 via Ollama).

**Example questions it handles:**
- What B.Tech programs does GNDEC offer?
- What is the fee structure for B.Tech 2026?
- What are the admission helpline numbers?
- Tell me about the CSE department
- What scholarships are available?
- What is the rural area quota at GNDEC?
- Who are the notable alumni?

---

## Architecture

```
Browser (React UI)
      │
      ▼
FastAPI Backend (port 8080)
      │
      ├── Auth middleware (X-API-KEY header)
      ├── /api/ask_stream  ──► RAG Pipeline
      │                           │
      │                    ┌──────┴──────┐
      │                    │             │
      │               FAISS Vector   Ollama LLM
      │               DB (MiniLM     (llama3.2:3b)
      │               embeddings)
      │
      ├── PostgreSQL  (chat history + sessions)
      └── Redis       (conversation memory / TTL)
```

### RAG Pipeline (per query)

1. **Toxicity check** — Detoxify filters harmful input
2. **Domain guard** — FAISS L2 distance check rejects off-topic questions
3. **Vector retrieval** — Top-6 nearest Q&A pairs from FAISS index
4. **Prompt building** — System prompt + conversation history + retrieved context
5. **LLM generation** — Streamed token-by-token via Ollama
6. **Output moderation** — Toxicity check on generated response
7. **Persistence** — Message saved to PostgreSQL, memory updated in Redis

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.12 |
| LLM | Ollama — `llama3.2:3b` (local, Apple Silicon) |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| Vector DB | FAISS (IndexFlatL2) |
| Memory | Redis (LangChain RedisChatMessageHistory) |
| Database | PostgreSQL (psycopg3) |
| Scraper | requests + BeautifulSoup4 + PyMuPDF + python-docx |

---

## Project Structure

```
.
├── backend/
│   ├── app.py              # FastAPI app, routes, static file serving
│   ├── agent.py            # RAG pipeline, streaming, memory
│   ├── vectorstore.py      # FAISS index loading + retrieval
│   ├── build_vector_db.py  # Builds FAISS index from data/
│   ├── domain_guard.py     # Out-of-domain query rejection
│   ├── moderation.py       # Toxicity filtering (Detoxify)
│   ├── chat_store.py       # PostgreSQL message/session persistence
│   ├── db.py               # DB connection
│   ├── llm/
│   │   └── llm.py          # Ollama / OpenAI LLM wrapper
│   └── faiss_store/
│       ├── faq.index       # FAISS binary index
│       └── meta.json       # Q&A metadata
│
├── data/
│   ├── gndec_data.json     # Scraped GNDEC website data (4,869 Q&A pairs)
│   └── gndec_facts.json    # Curated GNDEC facts (52 high-quality pairs)
│
├── scraper/
│   ├── gndec_scraper.py    # Web scraper (depth-2, PDF/DOCX parsing)
│   ├── build_facts.py      # Generates curated gndec_facts.json
│   └── dedup.py            # Deduplication utility
│
├── support_ui/             # React frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx       # Phone number login
│   │   │   ├── Sessions.jsx    # Chat session list
│   │   │   └── Chat.jsx        # Main chat interface (streaming)
│   │   └── components/
│   │       ├── MessageBubble.jsx   # User/assistant message bubbles
│   │       ├── TypingIndicator.jsx # Animated loading dots
│   │       └── SourceCard.jsx      # Knowledge source reference cards
│   └── dist/               # Built frontend (served by FastAPI)
│
├── share.sh                # One-command ngrok sharing script
├── locustfile.py           # Load testing
├── Dockerfile              # Container build
└── requirements.txt        # Python dependencies
```

---

## Setup & Running

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Redis
- [Ollama](https://ollama.com) with `llama3.2:3b` pulled

### 1. Clone and install dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd support_ui && npm install && cd ..
```

### 2. Set up PostgreSQL

```bash
psql postgres -c "CREATE USER gndec_user WITH PASSWORD 'gndec_pass';"
psql postgres -c "CREATE DATABASE gndec_ai OWNER gndec_user;"

psql gndec_ai -c "
CREATE TABLE IF NOT EXISTS chat_history (
  id SERIAL PRIMARY KEY,
  phone TEXT NOT NULL,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS chat_sessions (
  phone TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gndec_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gndec_user;
"
```

### 3. Configure environment

Copy `.env.bak` to `.env` and verify:

```env
DATABASE_URL=postgresql://gndec_user:gndec_pass@localhost:5432/gndec_ai
REDIS_URL=redis://localhost:6379/0
MODEL_PROVIDER=OLLAMA
MODEL_API_URL=http://localhost:11434
LLM_MODEL=llama3.2:3b
API_KEY=naman@1234
```

### 4. Pull the LLM model

```bash
ollama pull llama3.2:3b
```

### 5. Build the vector database

```bash
python3 backend/build_vector_db.py
```

This embeds all 4,921 Q&A pairs (scraped + curated) into a FAISS index.

### 6. Start services

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — Ollama
ollama serve

# Terminal 3 — Backend
uvicorn backend.app:app --host 0.0.0.0 --port 8080 --reload

# Terminal 4 — Frontend (dev)
cd support_ui && npm run dev
```

Open **http://localhost:5173** (dev) or **http://localhost:8080** (production build).

---

## Sharing via ngrok

To share with someone externally, run the one-command script:

```bash
bash share.sh
```

This will:
1. Start Redis, Ollama check, and the FastAPI backend
2. Create an ngrok tunnel
3. Build the React frontend with the ngrok URL baked in
4. Print the public URL to share

---

## Data Pipeline

### Scraping

```bash
python3 scraper/gndec_scraper.py
```

Crawls `gndec.ac.in` and all linked subdomains (ee, it, cse, ce, me, ece, mca, mba, tcc, etc.) up to **2 levels deep**. Downloads and parses PDF and DOCX files. Saves to `data/gndec_data.json`.

### Curated Facts

```bash
python3 scraper/build_facts.py
```

Generates `data/gndec_facts.json` — 52 hand-curated Q&A pairs covering admissions, fees, scholarships, eligibility, rural quota, faculty, rankings, and more. These take priority in retrieval due to higher quality.

### Rebuilding the Index

After updating either data file:

```bash
python3 backend/build_vector_db.py
```

---

## API Reference

All endpoints require `X-API-KEY` header.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check (no auth) |
| GET | `/api/ask` | Synchronous answer |
| GET | `/api/ask_stream` | Streaming answer (SSE) |
| GET | `/api/history` | Chat history for a session |
| GET | `/api/sessions` | List sessions for a phone |
| GET | `/api/get_or_create_session` | Get or create active session |
| POST | `/api/close_session` | Close active sessions |

### Streaming response format

Each chunk is a newline-delimited JSON object:

```json
{"type": "sources", "sources": [...]}
{"type": "content", "delta": "Hello"}
{"type": "content", "delta": " there"}
{"type": "blocked", "message": "..."}
```

---

## Domain Guard

The bot rejects off-topic questions using FAISS L2 distance. If the nearest neighbor in the knowledge base has a distance > 1.6, the query is considered out-of-domain and a redirect message is returned. Threshold can be tuned in `backend/domain_guard.py`.

---

## Knowledge Base Stats

| Source | Pairs |
|---|---|
| Curated facts (`gndec_facts.json`) | 52 |
| Scraped website data (`gndec_data.json`) | 4,869 |
| **Total vectors in FAISS** | **4,921** |

Sites scraped: `gndec.ac.in`, `cse.gndec.ac.in`, `it.gndec.ac.in`, `ee.gndec.ac.in`, `me.gndec.ac.in`, `ce.gndec.ac.in`, `ece.gndec.ac.in`, `mca.gndec.ac.in`, `mba.gndec.ac.in`, `tcc.gndec.ac.in`, `erp.gndec.ac.in`, and more.

---

## Docker

```bash
docker build -t gndec-assistant .
docker run -p 8080:8080 --env-file .env gndec-assistant
```

Note: Requires external PostgreSQL, Redis, and Ollama services.

---

## College Info

- **Full name:** Guru Nanak Dev Engineering College (GNDEC)
- **Location:** Gill Road, Ludhiana, Punjab – 141006, India
- **Website:** https://gndec.ac.in
- **Established:** 1956
- **Affiliation:** IKG Punjab Technical University (IKGPTU)
- **Accreditation:** NAAC Grade A, NBA (Tier-I), UGC Autonomous (2012–2032)
