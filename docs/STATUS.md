# AutoQuery — Implementation Status

| Step | Name | Status | Date |
|------|------|--------|------|
| 1 | Infrastruktur & Datenbank | DONE | 2026-03-04 |
| 2 | Crawler & Content Extraction | DONE | 2026-03-07 |
| 3 | LLM-Extraktion & Review | DONE | 2026-03-08 |
| 4 | Daten befüllen (≥ 200 Profile) | NOT STARTED | — |
| 5 | Embedding-Pipeline | DONE | 2026-03-08 |
| 6 | Matching-Algorithmus | DONE | 2026-03-08 |
| 7 | Backend-API | DONE | 2026-03-09 |
| 8 | Frontend | DONE | 2026-03-09 |
| 9 | Integration, Compliance & Logging | DONE | 2026-03-09 |
| 10 | Qualitätssicherung & Soft Launch | DONE | 2026-03-14 |

---

## Step 1 — Completion Notes
- Docker Compose with all services (PostgreSQL+pgvector, Redis, Ollama, FastAPI, Celery, Streamlit)
- Alembic migrations: 001_initial_schema (14 tables), 002_add_crawled_pages
- All models defined in `autoquery/database/models.py`

## Step 2 — Completion Notes
- `autoquery/crawler/crawler_engine.py`: Playwright fetcher, RateLimiter, CrawlRun, blacklist, robots.txt
- `autoquery/crawler/content_extractor.py`: HTML→clean text, canonical URL, link extraction
- `autoquery/crawler/page_classifier.py`: Ollama-based INDEX/CONTENT/UNKNOWN classifier
- `autoquery/crawler/quality_gate.py`: 7-dimension quality scoring
- `autoquery/crawler/orchestrator.py`: Domain BFS crawl + backfill
- `autoquery/crawler/tasks.py`: Celery task for single URL crawl

## Step 3 — Completion Notes
- `autoquery/extractor/prompts.py`: Versioned extraction prompt (v1.0)
- `autoquery/extractor/profile_extractor.py`: ProfileExtractor class — Ollama extraction, validation, genre canonicalization, Agent upsert
- `autoquery/review/operations.py`: approve/reject agents, CSV parsing, domain validation, seed list management
- `autoquery/review/app.py`: Full Streamlit app (Review Queue, Domain Management, Statistics)
- `config/genre_aliases.yaml`: ~40 genre aliases populated
- Migration 003: Added quality_score, quality_action, reviewed_by, reviewed_at, rejection_reason to agents
- Crawler integration: orchestrator.py and tasks.py call ProfileExtractor after quality gate
- 28 tests passing (17 extractor + 11 review)

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-08 | Inline extraction (not Celery) | Crawler already async, avoids serializing large text through Redis |
| 2026-03-08 | SQLite test adapter | PostgreSQL ARRAY/JSONB/Vector adapted via TypeDecorators for test portability |

## Step 7 — Completion Notes
- `autoquery/api/auth.py`: JWT + bcrypt password utilities (HS256, 30min access + 7d refresh)
- `autoquery/api/deps.py`: get_current_user, get_optional_user, get_session_id, RateLimiter, get_embedding_model
- Schemas: auth, matching (ManuscriptInput with HTML stripping), events (10 allowed types), upload, optout
- Routes: POST /api/auth/{register,login,refresh}, POST /api/match, GET /api/results/{id}, GET /api/genres, POST /api/upload, POST /api/events, POST /api/opt-out
- Session middleware: UUID v4 HttpOnly cookie, consistent between dep and middleware
- Migration 004: session_id column on manuscripts
- 38 new tests (12 auth, 4 optout, 5 events, 7 upload, 10 matching)
- 139 total tests passing

## Step 8 — Completion Notes
- Next.js 14 App Router + TypeScript + Tailwind CSS (dark theme: stone-900/amber-500)
- Fonts: Crimson Pro (headings) + DM Sans (body) via next/font/google
- 11 pages: Landing, Flow, Loading, Results/[id], Login, Opt-Out, Für Agenten, Impressum, Datenschutz, 404
- Conversational flow: 7 questions with chat bubbles (framer-motion), editable answers, progress dots
- FlowContext (useReducer) + AuthContext with SessionStorage persistence
- Upload: drag & drop, category selection, MIME/size validation, query letter fallback logic
- Results: guest (3 teaser cards + CTA) → inline registration → 20 full cards
- Expanded cards: all genres/keywords, submission checklist (✅❌⚠️○), source links, verification notice
- FeedbackBanner: appears after 60s engagement, auto-dismiss 15s, once per session
- API client: typed fetch wrappers, Bearer token auth, fire-and-forget event tracking
- JWT in localStorage, refresh on mount, inline registration on results page
- Dockerfile: multi-stage build (standalone output), docker-compose updated with NEXT_PUBLIC_API_URL
- Production build: all 11 routes compile, 87.3kB shared JS

## Step 9 — Completion Notes
- Session→user linking: registration now links anonymous manuscripts + events via session_id
- Opt-out processing: `compliance/optout_processor.py` marks agents opted_out, deletes `*_raw` fields
- Celery Beat schedule: hourly opt-out processing, daily SLA check, weekly session cleanup, 5min Ollama health, daily monitoring report
- Session cleanup: anonymous events deleted and manuscript session_ids nulled after 90 days
- Monitoring: `monitoring/health.py` with DB, Redis, Ollama, opt-out SLA checks; `/health?detailed=true`
- Backup/restore scripts: `scripts/backup.sh` (pg_dump with 7d/4w/3m retention), `scripts/restore.sh`
- Compliance checklist: 7 automated tests verifying AgentPublic schema, blacklist, opt-out filtering, event types
- Bug fix: `OptOutRequest.processed` field now has `default=False` (SQLite compatibility)
- 25 new tests (4 session linking, 7 opt-out processor, 3 session cleanup, 4 monitoring, 7 compliance checklist)
- 164 total tests passing

## Step 10 — Completion Notes
- Evaluation harness: `autoquery/evaluation/` package with metrics (P@K, recall@K, hard-nos violations, agency diversity), 20 synthetic backward test cases, evaluation orchestrator
- Readiness checks: agent count, genre/audience coverage, embedding completeness, launch-ready gate
- Edge case coverage: 13 tests for degenerate inputs (None genres/audience/embeddings, empty comps, long query letters, AB weights)
- E2E flow tests: 4 tests covering guest journey, registration unlock, auth matching, event linking
- Analytics E2E: 6 tests covering all 10 event types, persistence, auth, funnel, payloads
- Performance regression: 3 tests (200-agent pipeline <3s, 1000-agent scoring <5s, MMR rerank <500ms)
- Weight tuning CLI: `scripts/tune_weights.py` with grid search over weight combinations
- 51 new tests, 215 total passing

## Known Issues
- No IMPLEMENTATION_PLAN.md or feature specs were on disk (only in conversation transcript) — fixed 2026-03-08
- `seed_list.yaml` is empty — needs to be populated in Step 4
- No integration tests against real Ollama yet
