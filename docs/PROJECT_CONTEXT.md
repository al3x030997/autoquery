# AutoQuery — Projektkontext

> Dieses Dokument liefert den Kontext für alle Feature-Dateien. Bei Widersprüchen gilt immer der Master (`MASTER.md`).

## Was ist AutoQuery?

Öffentliche Web-Plattform die Buchautoren hilft, passende englischsprachige Literaturagenten zu finden. Das System crawlt Agentur-Websites direkt (nie Aggregatoren), extrahiert strukturierte Profile per LLM, und matcht diese semantisch gegen Manuskript-Profile.

## Zwei Kernstufen

**Stufe 1 — Agenten-Datenbank:** Direct-to-Source Crawling → LLM-Extraktion → manuelles Review → strukturierte DB. Fakten, Keywords, Embeddings und Originaltexte werden persistent gespeichert. Originaltexte (Wishlist, Bio, Hard-Nos) werden intern genutzt (Embedding-Qualität, Review) aber im Frontend **nicht angezeigt** (Store More, Show Less).

**Stufe 2 — Matching:** Autor durchläuft Conversational Flow (Chat-UI, eine Frage nach der anderen) → Embedding → 4-Signal-Scoring → MMR-Diversifizierung → gerankte, erklärbare Ergebnisse.

## Dreiphasige Matching-Strategie

- **Phase 1 (MVP):** Content-based Filtering auf strukturierten Features + Embedding-Similarity. Alle Interaktionen werden geloggt.
- **Phase 2 (~500 Interaktionen):** LightGBM/XGBoost auf geloggten Interaktionsdaten. Nur Scorer wird ausgetauscht.
- **Phase 3 (~10.000 Interaktionen):** ColBERTv2 Late Interaction oder Augmented SBERT Fine-Tuning.

Die gesamte Pipeline bleibt über alle Phasen identisch — nur die Scoring-Funktion wird ausgetauscht. Die Dateninfrastruktur für Phase 2/3 wird von Anfang an mitgebaut.

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Datenbank | PostgreSQL 15+ mit pgvector |
| LLM (lokal) | Ollama (llama3) |
| Embedding | BAAI/bge-large-en-v1.5 (1024d) |
| Crawler | Playwright + BeautifulSoup4 |
| Review-UI | Streamlit |
| Task Queue | Celery + Redis |
| Auth | JWT (bcrypt) |
| Frontend | Next.js |
| Container | Docker + Docker Compose |

## Projektstruktur

```
autoquery/
├── crawler/          # Crawling, Klassifikation, Content Extraction
├── extractor/        # LLM-Extraktion, Prompts
├── matching/phase1/  # Filter, Scorer, Reranker, Query Expander
├── matching/phase2/  # Stub (LightGBM)
├── matching/phase3/  # Stub (ColBERTv2)
├── logging/          # Interaction Logger
├── database/         # SQLAlchemy Models, Migrations
├── embeddings/       # Modell-Abstraktion, Pipeline
├── review/           # Streamlit Admin-App
├── api/              # FastAPI Routes, Schemas
├── tasks/            # Celery Tasks
├── frontend/         # Next.js
└── docker-compose.yml
```

## Harte Constraints

1. **Direct-to-Source:** Aggregatoren (MSWL, QueryTracker, PublishersMarketplace) werden nie gecrawlt — technisch via `blacklist.yaml` erzwungen.
2. **Store More, Show Less:** Originaltexte intern gespeichert, aber im MVP-Frontend nicht angezeigt. API-Endpunkte liefern `*_raw`-Felder nicht aus (separate Pydantic-Schemas). Anzeige kann später ohne Architektur-Änderung aktiviert werden.
3. **Nur Englisch:** Nur englischsprachige Agenturen im MVP.
4. **Kein MVP-Scope:** Keine Query-Letter-Generierung, keine Community-Features, keine direkte Kontaktaufnahme.

## Abgrenzung MVP vs. Post-MVP

| Im MVP | Post-MVP |
|---|---|
| Content-based Matching (Phase 1) | LightGBM (Phase 2), ColBERTv2 (Phase 3) |
| Kostenloser Account | Freemium (Feature-Flags vorbereitet) |
| Admin pflegt Domains | Nutzer schlagen Domains vor |
| MMR Diversity | DPP + Calibration |
| Genre-Aliases als YAML (`canon/aliases.yaml`, Thema-basiert) | Aliases + Extensions als DB-Tabelle mit Admin-UI |

## L2 — Kanonisches Vokabular (Thema)

Der kanonische Vokabularstand lebt im `canon/`-Verzeichnis (nicht in der DB, nicht im Code): Thema v1.6 (EDItEUR) als Backbone für Subject / Audience / Form, plus lokale `LOCAL:*`-Extensions für markt-relevante Terme, die Thema fehlen (romantasy, upmarket, women's fiction, dark_academia, …). Jeder Rohbegriff aus L1 wird via `canon/aliases.yaml` auf einen Canonical-Code abgebildet; unbekannte Terme gehen ins `unmapped_terms`-Review-Log und werden im Zyklus — **nicht zur Laufzeit** — entschieden. Design und Rationale: `docs/features/16_l2_canonicalization.md`.

## Referenzen

Alle Paper-Referenzen und rechtlichen Grundlagen sind im Master dokumentiert. Feature-Dateien referenzieren nur die für sie relevanten Paper.
