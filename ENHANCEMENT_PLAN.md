# GNDEC RAG — 12-Hour Enhancement Plan

**Branch:** `development` | **Date:** 2026-09-16 | **Status:** Post P0/P1 fixes

---

## Executive Summary

This plan outlines high-impact enhancements achievable in ~12 hours of focused work, building on the recently completed P0/P1 fixes:
- ✅ Numerical/entity grounding verification
- ✅ Dynamic Groq model fallback with caching
- ✅ Reciprocal Rank Fusion (RRF) + deeper retrieval

---

## Phase 1: Observability & Reliability (2.5 hrs)

### 1.1 Structured Logging & Metrics (1 hr)
- **Add request ID propagation** through async call chain (`answer_stream` → `call_model_async` → `retrieve`)
- **Log latency buckets** (p50/p95/p99) for: retrieval, rerank, LLM inference, verification
- **Export Prometheus metrics** via `/metrics` endpoint:
  - `rag_retrieval_latency_seconds` (histogram)
  - `rag_llm_latency_seconds` (histogram)
  - `rag_verification_failures_total` (counter with reason label)
  - `rag_cache_hit_ratio` (gauge)
  - `rag_model_failovers_total` (counter)

### 1.2 Health Checks & Graceful Degradation (1 hr)
- **`/health` endpoint** with dependency checks:
  - FAISS index load status & vector count
  - Embedding model loaded
  - Cross-encoder loaded
  - Redis connectivity (if configured)
  - Groq API reachability (cached)
- **Circuit breaker** for LLM provider: after 5 consecutive failures, return cached/abstention responses for 60s

### 1.3 Error Classification (0.5 hr)
- Classify errors as: `RETRIEVABLE` (rate limit, timeout), `NON_RETRIEVABLE` (bad request, auth), `INTERNAL`
- Add `X-Error-Class` header to streaming responses for UI retry logic

---

## Phase 2: Retrieval Quality (3 hrs)

### 2.1 Query Rewriting & Expansion (1.5 hrs)
- **Add `query_rewriter.py`** using small LLM (Haiku/8B) to:
  - Decompose compound queries → sub-queries
  - Expand abbreviations (CSE → Computer Science Engineering, HOD → Head of Department)
  - Add synonyms (fee → charges, tuition; placement → jobs, package)
  - Rewrite conversational follow-ups to standalone queries using chat history
- **Config:** `QUERY_REWRITE_ENABLED=true`, `QUERY_REWRITE_MODEL=groq:llama-3.1-8b-instant`

### 2.2 Hybrid Search Weighting (1 hr)
- **Tune RRF constant** via grid search on eval set (current: 60)
- **Add per-source weights** (structured fee/faculty vs dense vs sparse)
- **A/B test framework** in `retrieve()`: `strategy: "rrf" | "dense_only" | "sparse_only" | "weighted"`

### 2.3 Domain-Specific Re-ranking Signals (0.5 hr)
- **Boost signals** for exact matches on: fee amounts, program codes, faculty names, dates
- **Penalty** for stale data (documents older than 2 years without "current" marker)
- **Section-aware scoring**: prefer "Fee Structure" section for fee queries, "Faculty" for HOD queries

---

## Phase 3: Answer Quality & Safety (2.5 hrs)

### 3.1 Citation & Attribution (1.5 hrs)
- **Inline citations** in streaming answers: `[Doc 1]`, `[Fee Table]`, `[Faculty: Dr. X]`
- **Source mapping** in `verify_groundedness()`: return which doc supported each claim
- **UI integration**: hover tooltip showing source snippet for each citation
- **Citation format**: `{"claim": "...", "source_doc_id": "...", "source_section": "...", "char_span": [start, end]}`

### 3.2 Multi-Hop Reasoning Guard (1 hr)
- **Detect multi-hop queries**: "Who is the HOD of the department with highest placement?"
- **Chain verification**: if answer requires joining 2+ structured tables, verify each hop
- **Fail closed**: if any hop unverifiable → abstain with explanation

---

## Phase 4: Data Freshness & Coverage (2 hrs)

### 4.1 Automated Incremental Ingestion (1 hr)
- **Schedule** (cron/GitHub Actions): daily scrape of `gndec.ac.in` notices, fee pages, faculty pages
- **Diff detection**: hash-based change detection → only re-embed changed chunks
- **Versioned vectors**: keep last 3 versions, auto-expire old

### 4.2 Coverage Gap Analysis (1 hr)
- **Script** `scripts/analyze_coverage.py`:
  - Load eval queries → check retrieval recall@k
  - Identify query categories with < 50% recall
  - Output: "Missing: 2024 placement stats", "Missing: hostel fee for 2025"
  - Auto-create GitHub issues for content team

---

## Phase 5: UX & API Polish (1.5 hrs)

### 5.1 Streaming Improvements (0.5 hr)
- **Token-level streaming** with `data:` SSE format (already works, verify flush behavior)
- **Thinking indicator**: emit `{"type": "thinking", "step": "retrieving"}` before first token
- **Progress updates**: retrieval done → reranking → LLM streaming → verification

### 5.2 Request Validation & Rate Limiting (0.5 hr)
- **Input sanitization**: max query length (500 chars), strip injection patterns
- **Per-IP rate limit**: 30 req/min burst, 200 req/hour sustained (Redis-backed)
- **Abuse detection**: repeated identical queries → serve from cache silently

### 5.3 Conversation Memory (0.5 hr)
- **Short-term context**: last 3 turns embedded + stored in session
- **Follow-up detection**: cosine similarity > 0.85 to previous query → use previous retrieval + LLM re-rank
- **Session API**: `POST /sessions`, `GET /sessions/{id}/history`

---

## Phase 6: Evaluation & CI (0.5 hr)

### 6.1 Automated Eval Pipeline (0.5 hr)
- **GitHub Action** on PR: run `eval_harness.py` on 50 golden queries
- **Gate thresholds**:
  - Factual accuracy ≥ 85%
  - Abstention rate on unanswerable ≥ 90%
  - Latency p95 ≤ 3s (streaming first token ≤ 1s)
- **Regression alert**: Slack/Discord webhook on threshold breach

---

## Quick Wins (30 min total, do anytime)

| Task | Effort | Impact |
|------|--------|--------|
| Add `RERANK_MIN_SCORE` tuning via env | 5 min | Immediate recall boost |
| Cache embedding model across workers | 10 min | 2x throughput on multi-worker |
| Add `stream: false` sync endpoint for testing | 5 min | Easier debugging |
| Document all env vars in `ENV.md` | 10 min | Onboarding |

---

## Dependencies & Ordering

```
Phase 1 (Observability) ──┬──→ Phase 3 (Citations need metrics)
                          ├──→ Phase 4 (Ingestion needs health checks)
Phase 2 (Retrieval) ──────┤
                          ├──→ Phase 5 (API polish)
                          └──→ Phase 6 (Eval needs all above stable)
```

**Recommended execution order:** 1 → 2 → 3 → 4 → 5 → 6

---

## Success Metrics (Post-12h)

| Metric | Current | Target |
|--------|---------|--------|
| Factual accuracy (eval) | ~75% | ≥ 90% |
| Hallucination rate | ~15% | ≤ 3% |
| Unanswerable abstention | ~60% | ≥ 95% |
| p95 latency (first token) | ~2.5s | ≤ 1.5s |
| Cache hit rate | ~30% | ≥ 60% |
| Coverage (recall@6) | ~65% | ≥ 80% |

---

## Notes

- **No new external dependencies** — use existing: `prometheus-client`, `httpx`, `tenacity`
- **All env-configurable** — no code changes for tuning
- **Backwards compatible** — streaming API unchanged, only adds fields
- **Ponytail principle**: each phase ships a working increment; if time runs short, Phase 4/5 can defer