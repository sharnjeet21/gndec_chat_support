# Implementation plan

Base reviewed: `development@95d4366c3ed49f3255725fb2d85fe958f603068c`. All new paths below are proposals. Reconcile with current development before coding. Task IDs match `tasks.json` and `graphs/implementation-roadmap.mmd`.

## Priority and focus

**Now:** restore startup and enforce one verified answer path.  
**Next:** source provenance, session boundaries and a trustworthy evaluation baseline.  
**Then:** improve body-text retrieval and introduce a narrow knowledge graph.  
**Last:** refresh/promotion automation and measured production rollout.

Do not begin a full-corpus LLM graph extraction, model replacement, embedding fine-tune, UI redesign or another mass synthetic-question generation run before these gates. The existing retrieval components are worth retaining while their contracts are repaired.

## First implementation slice: T00–T02

Create a focused working branch based on the latest `development`; preserve all existing local work. Record the starting SHA. The immediate deliverable is a runnable, testable, shared answering path with graph mode off. User-facing behavior may initially buffer the answer to guarantee validation before delivery.

| Task | Required changes | Acceptance criteria |
|---|---|---|
| **T00 — Track the work and establish CI** | Narrow `.gitignore` rules to allow intended docs, tests and maintained scraper scripts. Add `requirements-dev.txt` and `.github/workflows/ci.yml`. Preserve existing secrets/artifact exclusions. | A deliberately selected test and doc are no longer ignored; no unrelated sensitive files are staged. Python 3.11 compile, isolated unit/contract tests, frontend lint/build and dependency checks have named CI jobs. CI initially exposes failures rather than suppressing them. |
| **T01 — Restore runtime contracts** | Fix malformed strings and precompute f-string context in `backend/agent.py`. Use `call_model_async(prompt=...)`; remove unsupported `model/messages` kwargs from callers. Use one fallible-memory adapter; make resolved query actually drive retrieval. Declare multipart/Groq dependencies consistently. Move index/model initialization behind explicit startup/loading and provide a documented build command. | Python 3.11 compile passes. Strict-signature fake LLM tests exercise sync and planner paths. Fresh startup with a fixture bundle reaches readiness; missing artifacts yield useful startup/readiness failure. Redis unavailable no longer crashes ordinary requests. Real-model index-build instructions are validated separately before release. |
| **T02 — Unify answer execution** | Extract proposed `backend/rag/contracts.py`, `pipeline.py`, `streaming.py` and `memory.py`; retain public functions in `agent.py` as adapters. Route every answer through policy → resolution → retrieval → generation/render → verification → persistence. Fix stream prompt persistence and buffer content until verified. | Sync and stream deliver the same final answer/source IDs for the same fixture request. Unsupported model claims are never emitted, stored or cached. Multihop/direct/cache paths obey the same guards. Assistant history contains the final answer once, not the prompt. Provider mid-generation failure does not concatenate incompatible responses. |

Temporarily disable the existing unvalidated LLM multi-hop detector while repairing the shared pipeline. This is an explicit documented fallback to hybrid retrieval, not silent exception-based success. Reintroduce bounded planning through T09 after schemas and tests exist.

## Backlog with file-level instructions

### T03 — Session access, request limits and cache scope

Depends on T02. Required before any public rollout.

- Change `backend/app.py`, `backend/chat_store.py`, `backend/cache.py`, `backend/domain_guard.py`, `backend/agent.py`, `support_ui/src/api.js` and session initialization in `support_ui/src/App.jsx` as needed.
- Remove the browser shared-key fallback. For this public information chatbot, use a server-issued opaque anonymous session token bound to a server-owned conversation ID; possession permits that conversation only. Do not use phone input as proof of identity. Authenticated cross-device phone history is out of scope until an identity/OTP system is implemented. Existing phone-linked histories stay inaccessible to unauthenticated migration guesses.
- Store only token digests server-side; define expiry/revocation, secure transport/cookie or bearer handling, CORS and CSRF behavior for the chosen transport. Missing production configuration fails closed. Treat trusted service clients separately.
- Scope every history/list/close query to the server-authorized owner, including the title subquery. Support at least two isolated anonymous sessions in tests. Redact phone numbers, full prompts and documents from routine logs.
- Apply input validation and bounded query length/rate limits to ask/stream/search/transcribe; enforce audio size during read and clean temporary files in `finally`.
- Route `/api/search` through the same access, domain and source filtering layer. It can omit generation, not authorization.
- Initially disable semantic answer reuse. Implement exact keys described in `GRAPH_DESIGN.md`; key language, conversation context, filters and corpus version explicitly.

**Done when:** cross-owner history/close requests fail; absent auth config cannot open protected routes; different languages/year/category/session context cannot reuse a cached answer; injected history/source text cannot change policy. No live account data is used in tests.

### T04 — Source and chunk contract

Depends on T01. Can be designed while T02 is repaired, but ingest nothing into serving indexes until policy is applied.

- Add proposed `backend/knowledge/schemas.py`, `normalize.py`, `source_policy.py`; update `backend/build_vector_db.py`, relevant `scraper/*.py` and a consolidated `scripts/build_knowledge.py`.
- Establish canonical URL, original source snapshot/hash, document classification, access scope, exact locator, parser revision, nullable published/effective/retrieved dates and stable IDs.
- Quarantine student rosters misclassified as syllabus, navigation/portal-only content, unknown provenance, unresolved conflicts and malformed fee tables from factual serving. Keep a review report and counts per reason.
- Distinguish imported legacy records from newly fetched evidence. Preserve unknown dates. Review the faculty identity collision and stop title-only qualification inference.
- Define source ownership and conflict/supersession policy per domain (fees, roles, programs, notices). No preference based only on JSON filename or ingestion order.

**Done when:** every approved chunk has a resolvable snapshot and locator; deterministic rebuilds produce stable IDs; conflict/withdrawal/failed-fetch cases preserve prior good data; public serving contains no student roster fixture; unknown validity remains unknown.

### T05 — Repair evaluation and freeze a baseline

Depends on T02 and T04. Evaluation design should begin immediately; actual baseline runs require a working pipeline.

- Refactor `scripts/eval_harness.py`; reconcile `data/gold_set.jsonl`, `gold_set_500.jsonl`, `sample_30_eval.jsonl`; retain historical originals with clear provenance.
- Create proposed `evaluation/cases.jsonl`, `evaluation/manifest.json` and `tests/fixtures/knowledge/` with no real student records. Use `EVALUATION_SPEC.md`.
- Resolve 20 shared-ID ground-truth differences against retained official evidence. Do not choose answers because the current model returns them. Assign new stable IDs where questions are not the same case.
- Report case counts from content. Separate semantic duplicates and paraphrase groups between tuning and held-out evaluation.
- Instrument the actual final evidence and answer route; do not run an unrelated retrieval call as a proxy for what generated the answer. Disable caches for cold-quality measurements and report warm cache separately.

**Done when:** all evaluated gold answers cite dated snapshots; each case has an answerability status; baseline report records commit/model/KB/prompt versions, failures, missing evidence and per-language metrics. Insufficient evidence is a labeled case, not a fabricated gold answer.

### T06 — Improve hybrid retrieval

Depends on T04 and T05.

- Change `backend/build_vector_db.py`, `backend/vectorstore.py`; extract proposed `backend/rag/retrieval.py`, `backend/knowledge/bundle.py` and `scripts/build_knowledge.py`.
- Embed/index body text plus useful headings and entity/qualifier metadata. Keep question text as additional retrieval context. Preserve model-required query/passage formatting and store dimension/revision/prefix rules in the manifest.
- Chunk by semantic sections/table rows and model token limits. Benchmark approximately 250–450-token narrative chunks as a starting experiment, not a universal rule; keep essential table headers/footnotes attached.
- Build dense and BM25 indexes from the same approved chunk IDs. Remove runtime metadata-only appends and consolidate competing append/rebuild scripts as wrappers or deprecated entry points.
- Retain RRF and reranking. Tune candidate count, top-k and abstention thresholds on the development set by language and query class. Compare reranker on/off to detect language harm before recommending a model change.
- Introduce a context token budget and required evidence groups for structured questions.

**Done when:** body-only answer facts become retrievable in fixtures; dense/meta dimensions and row counts align; unchanged corpus builds are deterministic; retrieval and answer metrics meet the baseline comparison gates without weakening abstention.

### T07 — Graph schema and read-only repository

Depends on T04. Production graph routing remains off.

- Add versioned migrations, proposed `backend/knowledge/graph_schema.py` and `graph_repository.py`. Reuse PostgreSQL with an explicit connection lifecycle; do not silently treat DB errors as empty authoritative results.
- Implement entities, aliases, assertions, evidence, coverage and KB versions from `GRAPH_DESIGN.md`. Add composite foreign keys tying evidence to the same version.
- Provide parameterized template queries, status/time/access filters, traversal bounds and typed errors. Handle empty/incomplete/unavailable as separate outcomes.
- Keep all graph diagnostics behind protected tooling; no public unrestricted graph query endpoint.

**Done when:** migration applies to fresh and existing test DBs; rollback/additive migration behavior is documented; wrong relation types, missing evidence and cross-version references are rejected; two-hop queries terminate under fan-out/cycle fixtures.

### T08 — Deterministic graph seed adapters

Depends on T07 and T04.

- Add proposed `backend/knowledge/extractors/faculty.py`, `fees.py`, `programs.py`, and `scripts/build_graph.py` as a subordinate step of the single knowledge-build command.
- Start with explicit faculty membership/profile facts, reviewed role assignments and qualified fee rows. Treat current hardcoded HOD data as a reconciliation input, not a trusted source. Use verified profiles/role pages to activate assertions.
- Parse program aggregates into reviewed program entities. Preserve program/department distinctions and category dimensions. Record the source field/row for every assertion.
- Report pending assertions, alias collisions, unknown dates and conflicts. Defer syllabus/course extraction until document classification is dependable; defer placement ranking until complete numeric source tables exist.

**Done when:** repeated builds add no duplicate entities/assertions; every served assertion has evidence; altered and withdrawn sources produce new versions; ambiguous people and unsupported PhD inference stay pending; fees retain all applicable qualifiers.

### T09 — Bounded graph-assisted query route

Depends on T02, T05, T06 and T08.

- Add proposed `backend/rag/query_planner.py`, `graph_retriever.py`, `evidence.py`; integrate via the shared pipeline.
- Register a small set of typed templates: department roster, department role/official contact, faculty qualification filter, and program fee comparison. Use entity binding between hops, not independently guessed subquestions.
- Resolve language/aliases and temporal filters; return clarification when a missing dimension changes the answer. Enforce depth/row/time/context budgets.
- Merge evidence by IDs with hybrid results; preserve required graph support. Handle graph timeout/unavailability with explicit hybrid fallback. Do not silently call that a successful graph answer.
- Add `GRAPH_MODE` off/shadow/on. Graph-only diagnostics compare evidence and cost during shadow mode; approved answers still come from the baseline.

**Done when:** the graph improves the held-out relationship slice under paired evaluation; missing/ambiguous/conflicting edges cannot produce definitive facts; current/date/category constraints are honored; general and multilingual queries satisfy non-regression gates.

### T10 — Evidence and protocol presentation

Depends on T02 and T04. Exact graph trace presentation follows T09.

- Change `backend/verify.py`, public serializers in `backend/app.py`, `support_ui/src/api.js`, `pages/Chat.jsx`, and `components/MessageBubble.jsx`.
- Validate citation IDs against the evidence actually used; do not certify an answer from evidence outside the prompt/renderer input.
- Show precise source URLs and available page/section/date. Unknown links remain unavailable; never synthesize a website from a local filename. Keep citations attached to the correct assistant message rather than one global latest-source list.
- Keep legacy JSON-line streaming operational while adding an explicit v2 endpoint/adapter with a documented media type and `status/sources/content/done/error` events. If adopting actual SSE, implement framing and parser together. Check HTTP status and abort/cancellation; handle split UTF-8/chunks.
- Keep implementation diagnostics out of ordinary student flows. Explain "not enough verified information" and request missing scope in the user's language.

**Done when:** frontend fixtures display accurate message-scoped citations, buffered verified answers, clarification and error states; HTTP/protocol failures are visible; every shown source belongs to that answer's evidence set.

### T11 — Freshness and artifact promotion

Depends on T06, T08 and T09.

- Repair `scripts/refresh_pipeline.py` by restoring maintained scraper modules or explicitly disabling unsupported jobs. Integrate one build/validate/promote pipeline with a lock and status report.
- Implement immutable bundle manifests, warm loading, per-request version pinning and rollback. Do not rely on a two-rename directory swap to reload in-memory workers.
- Add source-specific refresh policies: notices/exams often require shorter intervals than curricula; thresholds should be configured after source behavior is measured. Review failed/empty fetches and changed values before replacing prior good evidence.
- Invalidate by KB version, and include revoked/deleted assertions. Expose readiness, loaded KB version, refresh age and degraded components without leaking internals to public users.

**Done when:** failed fetch/build/DB transaction leaves the active bundle unchanged; concurrent readers see one complete version; a second worker can load the same manifest; rollback restores graph/vector/sparse/structured evidence together; stale current-fact queries are qualified or declined.

### T12 — Release gates, observability and handover

Depends on T03, T05, T09, T10 and T11.

- Add redacted per-stage timings, route distribution, evidence sufficiency, abstention reasons, cache isolation metrics, graph failures, source freshness and estimated/measured model usage. Preserve approved request IDs, not full phone/prompt dumps.
- Replace the unconditional promotion path in `.github/workflows/promote-to-prod.yml` with required CI/evaluation results and an actual readiness check before success status. Use small reviewed pull requests to development; production promotion is a distinct action.
- Run graph shadow comparison, then a controlled rollout with graph-off rollback. Record results by language and question type, not just a single average score.
- Deliver operating commands, dependency lock/constraints, example configuration without secrets, rollback instructions and known data gaps.

**Done when:** `EVALUATION_SPEC.md` release gates pass; a graph outage cannot break baseline serving; a tested rollback works; the release report distinguishes executed tests from skipped/deferred work.

## Suggested pull requests and stop conditions

| PR | Tasks | Reviewer evidence |
|---|---|---|
| 1: Executable baseline | T00–T01 | Python 3.11 compile, adapter/fallback tests, fixture startup, dependency/build instructions. |
| 2: One answer pipeline | T02 | Sync/stream/cache/direct/multihop equivalence; unsupported output never reaches client/history. |
| 3: Access and cache scope | T03 | Two-owner isolation and cross-language/year cache regressions. |
| 4: Sources and evaluation | T04–T05 | Approved/quarantined source manifest, reconciled gold evidence, reproducible baseline. |
| 5: Retrieval quality | T06 | Paired before/after retrieval and answer report, per-language analysis. |
| 6: Graph data | T07–T08 | Migration evidence, idempotency, conflicts/withdrawals and provenance coverage. |
| 7: Graph route and citations | T09–T10 | Paired graph ablation, query bounds, source UI/protocol tests. |
| 8: Operations and release | T11–T12 | Refresh failure drill, bundle rollback, shadow/canary report and readiness gates. |

Do not advance past a failed dependency gate. If a college source is absent or contradictory, code the explicit unknown/conflict behavior and report the data blocker; do not invent facts to finish a feature.

## Commands and validation ownership

Existing diagnostic commands: `python3 -m compileall -q backend scraper scripts`, `python3 -m pip check`, `git status --short`, `git check-ignore -v <intended-file>`, `git diff --check`. Run compilation with Python **3.11**, matching the declared target.

The following are **proposed commands that must first be implemented or supported by the corresponding tasks**:

```bash
python -m pytest tests/unit tests/contracts -q
python scripts/build_knowledge.py --source-config config/sources.yaml --dry-run
python scripts/build_knowledge.py --source-config config/sources.yaml --output data/knowledge_versions
python scripts/eval_harness.py --cases evaluation/cases.jsonl --manifest evaluation/manifest.json --graph-mode off --disable-cache
python scripts/eval_harness.py --cases evaluation/cases.jsonl --manifest evaluation/manifest.json --graph-mode on --disable-cache
```

Use `npm ci`, `npm run lint` and `npm run build` from `support_ui` with a supported pinned Node version and existing lockfile. Isolated tests must use deterministic fixtures/fakes; separately labeled integration tests may need PostgreSQL/Redis/model artifacts. Paid/live provider evaluations need configured credentials and an explicit request budget. Do not call a skipped network test a pass.
