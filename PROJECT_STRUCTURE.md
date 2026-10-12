# GNDEC RAG — Project Structure

```
gndec_rag/
├── backend/                    # Core RAG backend (FastAPI + WebSocket)
│   ├── __init__.py
│   ├── agent.py               # Main RAG agent (answer_sync, answer_stream)
│   ├── app.py                 # FastAPI app + WebSocket endpoints
│   ├── build_vector_db.py     # Vector DB builder from JSON/CSV sources
│   ├── cache.py               # Semantic + exact query cache (Redis + in-memory LRU)
│   ├── chat_store.py          # Redis-backed session/history store
│   ├── db.py                  # SQLite helpers for feedback/logging
│   ├── domain_guard.py        # Domain relevance filter (GNDEC scope)
│   ├── tools.py               # Tool definitions for LLM function calling
│   ├── vectorstore.py         # FAISS + BM25 hybrid retriever
│   ├── verify.py              # Grounding verification + honest abstention
│   ├── ssh_executer.py        # Remote command execution helper
│   ├── llm/                   # LLM provider abstractions
│   │   ├── __init__.py
│   │   ├── llm.py             # Groq provider + model priority logic
│   │   ├── ollama_client.py   # Local Ollama client
│   │   ├── token_llm.py       # Token-based LLM wrapper
│   │   └── vllm_client.py     # vLLM server client
│   ├── routers/               # FastAPI route modules
│   │   ├── __init__.py
│   │   ├── admin.py           # Admin endpoints
│   │   ├── chat.py            # Chat WebSocket + REST
│   │   ├── feedback.py        # Feedback collection
│   │   └── health.py          # Health checks
│   └── faiss_store/           # Persisted FAISS index + metadata
│       ├── faq.index
│       └── meta.json
├── data/                      # Raw + processed knowledge sources
│   ├── raw/                   # Original scraped/downloaded files
│   │   ├── faculty.json
│   │   ├── syllabi.json
│   │   ├── admission_process.json
│   │   ├── tnp_notices.json
│   │   └── fee_structure.json
│   ├── processed/             # Cleaned/normalized for ingestion
│   │   ├── facts.jsonl
│   │   ├── chunks.jsonl
│   │   └── gold_set.jsonl
│   └── benchmarks/            # Evaluation datasets
│       ├── eval_queries.jsonl
│       └── gold_answers.jsonl
├── scripts/                   # One-off data preparation & evaluation
│   ├── build_facts.py         # Extract structured facts from raw data
│   ├── create_admission_routing.py
│   ├── deep_research.py       # Multi-source web research
│   ├── eval_harness.py        # RAG evaluation runner
│   ├── evaluate_rag.py        # Main evaluation script
│   ├── extract_facts.py
│   ├── firecrawl_verify.py    # Source verification via Firecrawl
│   ├── generate_gold_500.py
│   ├── generate_gold_set.py   # Gold QA pair generation
│   ├── scrape_gndec.py        # Main site scraper
│   ├── scrape_notices.py      # TNP notice scraper
│   ├── prepare_finetune_data.py
│   └── finetune_embeddings.py # Embedding fine-tuning
├── scraper/                   # Reusable scraping modules
│   ├── gndec_scraper.py       # Base GNDEC site scraper
│   ├── faculty_scraper.py     # Faculty directory scraper
│   ├── syllabus_scraper.py    # Syllabus PDF scraper
│   ├── tnp_scraper.py         # Training & Placement scraper
│   ├── extract_tnp_tables.py  # Table extraction from notices
│   ├── dedup.py               # Content deduplication
│   └── build_facts.py         # Fact extraction pipeline
├── tests/                     # Test suite
│   ├── test_rag.py            # Core RAG tests
│   ├── test_rag_local.py      # Local-only RAG tests
│   ├── test_faiss.py          # FAISS retriever tests
│   ├── test_stream.py         # Streaming response tests
│   ├── test_queries.py        # Query handling tests
│   ├── test_courses.py        # Course info tests
│   ├── test_trees.py          # Tree-based retrieval tests
│   ├── test_openai.py         # OpenAI compatibility tests
│   └── locustfile.py          # Load testing
├── .claude/                   # Claude Code configuration
│   ├── settings.local.json
│   └── agents/                # Custom agent definitions
├── .venv/                     # Python virtual environment
├── .codex-run/                # Codex run logs
├── .github/                   # CI/CD workflows
├── certs/                     # SSL certificates
├── .dockerignore
├── .env                       # Runtime config (secrets)
├── .env.example               # Template for .env
├── .gitignore
├── .ignore
├── .python-version
├── clean_errors.py            # Error log cleaner
├── cloudflared                # Cloudflare tunnel binary
├── cloudflare_startup.log
├── PROJECT_STRUCTURE.md       # This file
├── README.md
└── requirements.txt           # Python dependencies
```

## Key Architectural Components

| Component | Purpose |
|-----------|---------|
| `agent.py` | Orchestrates retrieval → verification → generation |
| `vectorstore.py` | Hybrid FAISS (dense) + BM25 (sparse) retrieval |
| `verify.py` | Grounding check + sensitive query abstention |
| `cache.py` | Semantic cache (cosine sim ≥ 0.96) + exact match |
| `domain_guard.py` | Filters out-of-scope queries before retrieval |
| `llm/llm.py` | Groq multi-model fallback with priority ordering |

## Data Flow

```
User Query
    ↓
domain_guard.is_out_of_domain()  →  abstain if True
    ↓
cache.lookup()                   →  return if HIT
    ↓
vectorstore.hybrid_search()      →  top-k chunks
    ↓
verify.verify_groundedness()     →  abstain if ungrounded
    ↓
LLM generation (Groq/ollama/vLLM)
    ↓
cache.store()
    ↓
Response
```

## Environment Variables (`.env`)

```bash
GROQ_API_KEY=xxx
REDIS_URL=redis://localhost:6379/1
CACHE_TTL=86400
SEMANTIC_CACHE_THRESHOLD=0.96
VERIFY_MIN_OVERLAP=0.35
OLLAMA_BASE_URL=http://localhost:11434
VLLM_BASE_URL=http://localhost:8000
```