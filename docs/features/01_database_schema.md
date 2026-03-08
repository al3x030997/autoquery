# Feature 01 — Database Schema

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul C (7.1–7.7), Teile von Modul K (15.4)

## Scope

Alle PostgreSQL-Tabellen, Extensions, Indizes, Trigger und Migrations-Strategie. Dies ist das erste Feature das implementiert werden muss — alle anderen Features hängen davon ab.

## Dateien

```
database/
├── models.py       # SQLAlchemy Modelle
├── migrations/     # Alembic
└── db.py           # Verbindungsmanagement
```

---

## Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector für Embeddings
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- Trigram-Suche (optional)
```

---

## Tabelle `agents`

Kern-Tabelle. Enthält Fakten, Keywords, Embeddings und intern gespeicherte Originaltexte. Die `*_raw`-Felder werden im Frontend **nie** ausgeliefert — separate Pydantic-Schemas (intern vs. öffentlich) erzwingen das serverseitig.

**Felder:**
- `id` SERIAL PRIMARY KEY
- `name` TEXT NOT NULL
- `agency` TEXT
- `email` TEXT — intern, nie öffentlich angezeigt
- `country` TEXT
- `source_url` TEXT UNIQUE NOT NULL
- `genres` TEXT[]
- `audience` TEXT[]
- `keywords` TEXT[]
- `hard_nos_keywords` TEXT[]
- `wishlist_raw` TEXT — Originaltext, intern, nie im Frontend
- `bio_raw` TEXT — Originaltext, intern, nie im Frontend
- `hard_nos_raw` TEXT — Originaltext, intern, nie im Frontend
- `submission_req` JSONB
- `response_time` TEXT
- `is_open` BOOLEAN DEFAULT TRUE
- `embedding` vector(1024)
- `embedding_model` TEXT
- `embedding_updated_at` TIMESTAMP
- `fts_vector` TSVECTOR — via Trigger befüllt
- `review_status` TEXT DEFAULT 'pending' — pending/approved/rejected/extraction_failed/unreachable
- `rejection_reason` TEXT
- `reviewed_by` TEXT
- `reviewed_at` TIMESTAMP
- `crawled_at` TIMESTAMP NOT NULL
- `last_checked_at` TIMESTAMP
- `etag` TEXT — für Incremental Crawling
- `recrawl_requested` BOOLEAN DEFAULT FALSE
- `opted_out` BOOLEAN DEFAULT FALSE
- `opted_out_at` TIMESTAMP
- `created_at` TIMESTAMP DEFAULT NOW()
- `updated_at` TIMESTAMP DEFAULT NOW()

**Wichtig bei Opt-Out:** `*_raw`-Felder werden gelöscht (nicht nur ausgeblendet).

**API-Schemas:**
```python
# Öffentlich (Frontend) — OHNE Rohtexte
class AgentPublic(BaseModel):
    id, name, agency, country, source_url, genres, audience,
    keywords, hard_nos_keywords, submission_req, ...

# Intern (Review-Interface) — MIT Rohtexten
class AgentInternal(AgentPublic):
    wishlist_raw, bio_raw, hard_nos_raw, email, ...
```

**Indizes:**
```sql
CREATE INDEX agents_embedding_idx ON agents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX agents_fts_idx ON agents USING GIN (fts_vector);
CREATE INDEX agents_matching_filter_idx ON agents (review_status, is_open, opted_out);
```

**FTS-Trigger:** `fts_vector` automatisch aus `keywords`, `hard_nos_keywords`, `genres` befüllen. Arrays müssen für den Trigger zu Text konvertiert werden.

---

## Tabelle `manuscripts`

Autoren-Inputs + beide Embedding-Varianten. `user_id` ist nullable — Matching funktioniert ohne Account, das Manuskript wird bei Registrierung mit dem neuen User verknüpft.

**Felder:**
- `id` SERIAL PRIMARY KEY
- `user_id` INTEGER REFERENCES users(id) ON DELETE CASCADE — nullable, bei Registrierung nachgetragen
- `session_id` TEXT — UUID v4 für nicht-eingeloggte Nutzer, zum späteren Verknüpfen
- `genre` TEXT NOT NULL
- `audience` TEXT NOT NULL
- `tone` TEXT NOT NULL
- `themes` TEXT NOT NULL
- `comp_titles` TEXT NOT NULL
- `query_letter` TEXT NOT NULL — aus Upload oder Freitext
- `synopsis` TEXT — optional, aus Upload
- `first_chapter` TEXT — optional, aus Upload (Manuskript-Ausschnitt)
- `pitch_deck_text` TEXT — optional, aus Pitch Deck/One-Pager Upload
- `additional_wishes` TEXT — optional, Freitext aus Frage 7
- `embedding_fulltext` vector(1024)
- `embedding_query_expanded` vector(1024)
- `embedding_weight_fulltext` FLOAT DEFAULT 0.7
- `embedding_weight_expanded` FLOAT DEFAULT 0.3
- `embedding_model` TEXT
- `created_at` TIMESTAMP DEFAULT NOW()

Beide Gewichte werden pro Manuskript gespeichert für A/B-Testing.

---

## Tabelle `users`

- `id` SERIAL PRIMARY KEY
- `email` TEXT UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL
- `created_at` TIMESTAMP DEFAULT NOW()
- `last_login` TIMESTAMP
- `is_active` BOOLEAN DEFAULT TRUE
- `plan` TEXT DEFAULT 'free' — Freemium-Vorbereitung

---

## Tabelle `matching_results`

Einzel-Scores aus Phase 1 werden gespeichert — essenziell als Features für Phase 2.

**Felder:**
- `id` SERIAL PRIMARY KEY
- `user_id` INTEGER REFERENCES users(id) ON DELETE CASCADE — nullable, bei Registrierung nachgetragen
- `session_id` TEXT — für nicht-eingeloggte Nutzer
- `manuscript_id` INTEGER REFERENCES manuscripts(id) ON DELETE CASCADE
- `agent_id` INTEGER REFERENCES agents(id) ON DELETE CASCADE
- `final_score` FLOAT NOT NULL
- `semantic_score` FLOAT
- `fts_score` FLOAT
- `genre_score` FLOAT
- `audience_score` FLOAT
- `mmr_rank` INTEGER
- `algorithm_version` TEXT — für A/B-Testing
- `status` TEXT DEFAULT 'saved' — saved/contacted/full_ms_requested/rejected_by_agent/offer_received/withdrawn
- `status_updated_at` TIMESTAMP
- `notes` TEXT
- `user_rating` INTEGER — 1–5, optional
- `user_rating_at` TIMESTAMP
- `created_at` TIMESTAMP DEFAULT NOW()

Status-Funnel: `contacted → full_ms_requested → offer_received` — je weiter, desto stärkeres Trainings-Signal.

---

## Tabelle `interaction_events`

Wichtigste Investition in Phase 2. Logging ab Tag 1 Pflicht.

**Felder:**
- `id` BIGSERIAL PRIMARY KEY
- `user_id` INTEGER REFERENCES users(id) ON DELETE SET NULL
- `session_id` TEXT — UUID v4 für nicht-eingeloggte Nutzer
- `manuscript_id` INTEGER REFERENCES manuscripts(id) ON DELETE SET NULL
- `agent_id` INTEGER REFERENCES agents(id) ON DELETE SET NULL
- `event_type` TEXT NOT NULL
- `result_rank` INTEGER
- `session_score` FLOAT
- `algorithm_version` TEXT
- `created_at` TIMESTAMP DEFAULT NOW()

**Indizes:** `(manuscript_id, agent_id)`, `event_type`, `created_at`

**Event-Typen:**

| Event | Signal-Stärke |
|---|---|
| `result_shown` | Neutral (Baseline) |
| `card_clicked` | Schwach positiv |
| `profile_expanded` | Mittel positiv |
| `submission_checklist` | Mittel positiv |
| `source_link_clicked` | Stark positiv |
| `marked_contacted` | Sehr stark positiv |
| `full_ms_requested` | Stärkstes positiv |
| `offer_received` | Stärkstes positiv |
| `marked_rejected` | Negativ |
| `result_ignored` | Schwach negativ (30s Timer) |

**Session-ID:** UUID v4 in HttpOnly-Cookie, 24h Lebensdauer. Funktional notwendig → kein Cookie-Banner. Nach 90 Tagen aus DB löschen. Bei Login: offene Session-Events mit `user_id` verknüpfen.

---

## Tabelle `known_profile_urls`

Primärer URL-Input für monatliche Re-Crawls.

- `id` SERIAL PRIMARY KEY
- `domain` TEXT NOT NULL
- `url` TEXT UNIQUE NOT NULL
- `discovered_at` TIMESTAMP DEFAULT NOW()
- `discovery_method` TEXT — 'browser_agent' / 'sitemap' / 'manual'
- `status` TEXT DEFAULT 'active' — active/unreachable/removed
- `last_checked_at` TIMESTAMP
- `consecutive_failures` INTEGER DEFAULT 0

**Lifecycle:** Nach 3 aufeinanderfolgenden Fehlern → `status = unreachable`. Bei Erfolg → `consecutive_failures = 0`. Admin kann manuell URLs hinzufügen/entfernen/reaktivieren.

---

## Tabelle `opt_out_requests`

- id, agent_name (NOT NULL), agent_url, contact_email (NOT NULL), request_text, status (pending/processed), received_at (DEFAULT NOW()), processed_at

## Tabelle `recrawl_queue`

- id, agent_id (CASCADE), reason, reported_by (FK users), status (pending/processing/done), created_at, processed_at

## Tabelle `crawl_runs`

- id, domain, run_type (initial/monthly/priority), started_at, finished_at, status, pages_fetched, pages_index, pages_content, pages_skipped, pages_error, quality_extracted, quality_warned, quality_discarded, avg_quality_score, top_issues (JSONB), profiles_new, profiles_updated, profiles_unchanged, error_message

## Tabelle `suggested_domains` (Stub — nicht im MVP-Frontend)

- id, domain (NOT NULL), suggested_by (FK users, SET NULL), agency_name, country, notes, status (pending_review/accepted/rejected), reviewed_by, reviewed_at, created_at (DEFAULT NOW())

---

## Migrations-Strategie

Alembic für alle Schema-Änderungen. Bei Embedding-Modell-Wechsel: Vektordimension muss migriert werden — dokumentieren im Migrations-Workflow.
