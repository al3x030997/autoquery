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

## Pipeline-Schichten (L0–L3)

| Layer | Name | Status | Date |
|---|---|---|---|
| L0 / L0.3 / L0.6 | Screenshot-Capture / DOM-Text / Cleaning | DONE | — |
| L1 | Note-Taker | DONE (Prompt v2.0 integriert, Parser + Schema/Migration 005 in place; legacy flat columns als temporäre Projektion erhalten) | 2026-04-15 |
| L1-V | Fact-Checker | DESIGN ONLY | — |
| **L2** | **Kanonisierung (Thema-basiert)** | **v0 CANON ARTEFAKTE DEFINIERT** (50-Profile MSWL-Stichprobe + Dry-Run als pre-Step-4-Validierung; v1-Lock weiterhin nach Schritt 4) | **2026-04-15** |
| L3 | Per-Section Embeddings | IN RECHERCHE | — |

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

## L2 — Canon v0 Notes
- Thema v1.6 (2025-04-10 englisch) als Backbone, unter `canon/_source/` als Audit-Trail abgelegt
- Generierte Artefakte: `canon/thema_subjects.yaml` (629 Codes), `canon/thema_audience.yaml` (27), `canon/thema_form.yaml` (56)
- Handgepflegt: `canon/extensions.yaml` (8 `LOCAL:*`-Einträge), `canon/hard_nos.yaml` (23 Tags), `canon/aliases.yaml` (~200 Rohphrasen)
- Dry-Run-Script `scripts/canon_coverage.py` vorhanden; `canon/coverage_report.md` wartet auf Erstlauf mit API-Key
- Design-Dokumentation: `docs/features/16_l2_canonicalization.md`
- Laufzeit-Integration (Canonicalizer-Klasse, Alembic-Migration für `thema_*`-Spalten, `unmapped_terms`-Tabelle, Hook in `crawl_url_task`) explizit nicht in v0 — Folge-Spezifikation

## MSWL Sample & Canon Dry-Run Notes (pre-Step-4)
- Internal one-time Capture von 50 MSWL-Profilen (`manuscriptwishlist.com/mswl-post/...`) als Validierungs-Stichprobe — nicht im `agents`-Table, nicht im Produkt, Dateicache unter `data/mswl_sample/`
- MSWL bleibt in `config/blacklist.yaml`; Bypass nur am Call-Site dieser Capture-Skripte via `fetch_page(..., skip_blacklist=True)`
- Pipeline: `scripts/harvest_mswl_sample.py` → `scripts/analyze_mswl_sample.py` → `scripts/canon_dryrun.py`
- Outputs: `data/mswl_sample/analysis.md` (Profil-Struktur-Report), `data/mswl_sample/canon_dryrun.md` (Coverage + unmapped-term-Leaderboard mit alias/LOCAL/dismiss-Tags)
- Altes `scripts/canon_coverage.py` ist gegen das neue Note-Taker-Schema veraltet; `canon_dryrun.py` ersetzt es für diese Validierung (kein Rewrite des alten Scripts in diesem Pass)
- 50 Profile ist erste Stichprobe, kein v1-Lock; v1-Lock benötigt weiterhin ≥200 Profile via Step 4 (direct-to-source)

## L1 — Note-Taker Integration Notes (2026-04-15)
- Prompt-Asset: `autoquery/extractor/prompts/note_taker_v1.txt` (`PROMPT_VERSION = "2.0"`)
- Parser: `autoquery/extractor/note_parser.py` (deterministisch, 9 Unit-Tests grün)
- Persistenz: `agents.profile_notes` (JSONB) + `profile_notes_raw` + `prompt_version`
- Migration: `005_add_profile_notes.py`
- ProfileExtractor.`_project_to_columns` füllt `genres_raw`, `audience`, `hard_nos_keywords`, `keywords`, `wishlist_raw` als temporäre Kompatibilitätsschicht
- 235 Tests grün (incl. 9 Parser-Tests + 7 neue Extractor-Tests)
- **Bekannte Folge-Arbeiten** (eigene Pläne):
  - Matcher-Rewrite (Step 6) auf `preference_sections[*]` — derzeit in Recherche
  - Embeddings pro Sektion statt pro Agent (`autoquery/embeddings/`)
  - L2-Runtime-Canonicalizer + `unmapped_terms`-Tabelle, Hook in `crawl_url_task`
  - Review-UI (Streamlit) für Sektionen
  - `AgentPublic` API-Schema auf Sektionen umstellen
  - Backfill der bestehenden 7 Benchmark-Profile durch den neuen Prompt
  - Drop der flachen Legacy-Spalten — erst sicher, wenn alle Konsumenten umgestellt sind

## Known Issues
- No IMPLEMENTATION_PLAN.md or feature specs were on disk (only in conversation transcript) — fixed 2026-03-08
- `seed_list.yaml` is empty — needs to be populated in Step 4
- No integration tests against real Ollama yet
