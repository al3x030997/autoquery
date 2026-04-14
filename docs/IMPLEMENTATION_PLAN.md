# AutoQuery MVP — Implementierungsplan
> Dieses Dokument ist die zentrale Steuerung für die MVP-Implementierung. Jeder Schritt wird in genau dieser Reihenfolge umgesetzt und getestet bevor der nächste beginnt.
> Referenzen: `PROJECT_CONTEXT.md` für Gesamtkontext, `00_mvp_definition.md` für MVP-Scope und Metriken, Feature-Dateien `01`–`15` für technische Details.
---
## Prinzipien
1. **Vertikal, nicht horizontal.** Jeder Schritt produziert etwas Testbares — kein Schritt endet mit "halb fertig".
2. **Datenpipeline zuerst.** Ohne Agenten-Daten kann nichts getestet werden. Daten sind das Fundament.
3. **Backend vor Frontend.** API-Endpunkte stehen und sind getestet bevor das Frontend gebaut wird.
4. **MVP-Scope strikt.** Nur Features die in `00_mvp_definition.md` stehen. Alles andere ist Sprint 2.
---
## Daten-Pipeline-Architektur (L0–L3)
> Die Datenaufbereitung ist in diskrete Schichten gegliedert. Jede Schicht hat einen klar definierten Input, Output und eine einzige Verantwortung. Dieses Schichtmodell ersetzt den ursprünglich geplanten HTML-Crawl-Ansatz sowie das einstufige Embedding-Modell.
### Überblick
```
L0    Screenshot-Capture        (PNG pro Abschnitt)
  │
L0.3  Raw-Text-Extraktion       (document.body.innerText → .txt)
  │
L0.6  Text-Cleaning             (Nav/Footer/Sidebar strippen)
  │
L1    Note-Taker                (strukturierte natürliche Sprache)
  │
L1-V  Fact-Checker              (Verifikation gegen Quelltext)
  │
L2    Kanonisierung             (Tags + Boolean-Regeln)        [IN RECHERCHE]
  │
L3    Per-Section Embeddings    (ein Vektor pro Wishlist-Abschnitt) [IN RECHERCHE]
```
### L0 — Screenshot-Capture
**Zweck:** Vollständige visuelle Erfassung der Agenten-Seite als PNG-Abschnitte. Dient als QA-Fallback für den Fact-Checker bei Zweifelsfällen.
**Input:** Agent-URL (aus CSV)
**Output:** `screenshots/{agent_name}/section_NN.png`
**Implementierung:** `autoquery/simulation/page_capture.py` (Playwright, headless Chromium, 1920×1080 Viewport, device_scale_factor=2)
**Status:** DONE
### L0.3 — Raw-Text-Extraktion
**Zweck:** Extraktion des gerenderten DOM-Texts (kein Vision-OCR). Text-zu-Text, nicht Bild-zu-Text.
**Input:** Gerenderter DOM während derselben Playwright-Session wie L0
**Output:** `text_content/{agent_name}.txt` (via `document.body.innerText`)
**Implementierung:** Teil von `autoquery/simulation/page_capture.py`
**Status:** DONE
### L0.6 — Text-Cleaning
**Zweck:** Entfernung von Site-Chrome (Navigation, Footer, Sidebar-UI-Labels). Ergebnis ist reiner Profil-Text, bereit für den Note-Taker.
**Input:** `text_content/{agent_name}.txt`
**Output:** `cleaned/{agent_name}.txt`
**Implementierung:** `autoquery/simulation/text_cleaner.py` (regelbasiert, keine LLM)
**Status:** DONE
### L1 — Semi-strukturierte Extraktion (Note-Taker)
**Zweck:** Umwandlung des bereinigten Rohtexts in eine strukturierte, aber natürlich-sprachliche Darstellung. Keine Kanonisierung, keine induzierten Genres — die Sprache des Agenten bleibt erhalten.
**Input:** `cleaned/{agent_name}.txt`
**Output:** Strukturierter Text mit Feldern: Identity, Global Conditions, Preference Sections (mit Wants/Does-Not-Want/Conditions/Comp Titles), Hard Nos, Submission Requirements, Taste References, Cross-Cutting Themes, Confidence Flags
**Implementierung:** Erweiterung von `autoquery/extractor/profile_extractor.py` mit neuem System Prompt
**System Prompt:** Entwurf unter `/Users/alex/Downloads/extraction_system_prompt.txt`
**Beispiel-Output:** `/Users/alex/Downloads/aashna_avachat_structured.txt`
**Status:** SYSTEM PROMPT ENTWORFEN, INTEGRATION OFFEN
**Qualitätsmessung:** 4 Dimensionen
- Completeness: ≥95% Hard-Nos, ≥90% Comp Titles, 100% Sections
- Faithfulness: 100% (jede Zeile im Quelltext belegbar — keine Halluzinationen)
- Condition Preservation: 100% (Klauseln wie "only if X", "where Y", "but not Z" bleiben erhalten)
- Structural Linkage: korrekte Section-Grenzen, Comps zu Wants verknüpft
**Benchmark:** 8 manuell gecheckte MSWL-Profile als permanente Testsuite (`/Users/alex/autoquery/batch_capture_output/cleaned/`)
### L1-V — Verifikation (Fact-Checker)
**Zweck:** Unabhängiger zweiter Agent prüft L1-Output gegen den Quelltext. Flaggt Halluzinationen, fehlende Felder und gedropte Conditions. Liefert Korrekturreport.
**Input:** L1-Output + `cleaned/{agent_name}.txt` (+ Screenshots als optionaler QA-Fallback)
**Output:** Verifikationsreport (JSON) mit Scores, Misses, Hallucinations + korrigiertes L1
**Architektur:** Claude (stärkeres Reasoning als Note-Taker) — läuft einmal pro Profil, nicht pro Query
**Status:** DESIGN, NOCH NICHT IMPLEMENTIERT
### L2 — Kanonisierung (Platzhalter)
**Zweck:** Verifiziertes L1 → kanonische Genre-Tags, Audience-Enums, Hard-No-Keyword-Listen, strukturierte Conditions. Ermöglicht günstige Boolean-Filterung (3000 → 50 Kandidaten in Millisekunden).
**Status:** IN RECHERCHE — konkrete Methode (LLM-basierte Kanonisierung vs. Alias-Dictionary vs. Hybrid) noch nicht entschieden
**Offen:** Umgang mit mehrdeutigen Genres, Erweiterbarkeit des kanonischen Vokabulars, Confidence-Scoring pro Tag
### L3 — Per-Section Embeddings (Platzhalter)
**Zweck:** Ein Embedding pro Preference Section (nicht pro Agent). Matching via `max(cosine_similarity(manuscript, section_i))`. Ersetzt das alte 70/30 gewichtete Gesamt-Embedding und löst das Wishlist-Blurring-Problem.
**Status:** IN RECHERCHE — Section-Granularität, Embedding-Modell für kurze Textsegmente und Aggregationsstrategie noch nicht entschieden
### Verbindung zu den 10 Schritten
| Layer | Schritt im Plan | Status |
|---|---|---|
| L0, L0.3, L0.6 | Schritt 2 (neu interpretiert) | DONE |
| L1, L1-V | Schritt 3 (neu interpretiert) | In Arbeit |
| L2 | Neu — Zwischenschicht vor Schritt 5 | In Recherche |
| L3 | Schritt 5 (ersetzt altes Modell) | In Recherche |
**Hinweis:** Die Schritte 2, 3 und 5 sind laut STATUS.md formal "DONE", wurden aber architektonisch durch das Schichtmodell ersetzt. Der alte Code (HTML-Crawler in `autoquery/crawler/`, einstufiger Extractor, gewichtetes Gesamt-Embedding) existiert weiterhin, gilt aber als deprecated zugunsten der Screenshot-basierten Pipeline.
---
## Übersicht: 10 Schritte
```
Schritt 1:  Infrastruktur & Datenbank           ░░░░░░░░░░░░░░░░░░░░
Schritt 2:  Crawler & Content Extraction         ░░░░░░░░░░░░░░░░░░░░░░░░
Schritt 3:  LLM-Extraktion & Review              ░░░░░░░░░░░░░░░░░░░░
Schritt 4:  Daten befüllen (≥ 200 Profile)       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Schritt 5:  Embedding-Pipeline                   ░░░░░░░░░░░░░░░░
Schritt 6:  Matching-Algorithmus                  ░░░░░░░░░░░░░░░░░░░░░░░░
Schritt 7:  Backend-API                           ░░░░░░░░░░░░░░░░░░░░
Schritt 8:  Frontend                              ░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Schritt 9:  Integration, Compliance & Logging     ░░░░░░░░░░░░░░░░░░░░
Schritt 10: Qualitätssicherung & Soft Launch      ░░░░░░░░░░░░░░░░
```
---
## Schritt 1 — Infrastruktur & Datenbank
**Ziel:** Alle Services laufen lokal, Schema steht, Migrations-Workflow funktioniert.
**Was gebaut wird:**
- Docker Compose mit allen Services: PostgreSQL + pgvector, Redis, Ollama, FastAPI (Stub), Celery Worker + Beat, Next.js (Stub), Streamlit (Stub)
- Benannte Volumes für persistente Daten
- Alembic eingerichtet mit initialem Schema
- Alle Tabellen aus Feature 01: `agents`, `manuscripts`, `users`, `matching_results`, `interaction_events`, `known_profile_urls`, `opt_out_requests`, `recrawl_queue`, `crawl_runs`
- pgvector Extension + IVFFlat Index
- FTS-Trigger auf `agents`
- Ollama Health-Check (Docker)
**Feature-Dateien:** `01_database_schema.md`, `15_infrastructure.md`
**Testbar wenn:**
- `docker compose up` startet alle Services ohne Fehler
- `alembic upgrade head` erstellt alle Tabellen
- Ollama antwortet auf Health-Check
- Ein manueller INSERT in `agents` funktioniert inkl. Embedding-Vektor
- FTS-Trigger befüllt `fts_vector` automatisch
---
## Schritt 2 — Capture & Text-Cleaning (L0 / L0.3 / L0.6)
> **Architektur-Update:** Dieser Schritt deckt nun die Schichten **L0 / L0.3 / L0.6** der neuen Daten-Pipeline ab. Die Implementierung erfolgt durch `autoquery/simulation/page_capture.py` (Screenshot + DOM-Text) und `autoquery/simulation/text_cleaner.py` (Chrome-Stripping). Der ursprünglich geplante HTML-Crawl mit BeautifulSoup + Quality Gate (7 Dimensionen) wurde durch den Screenshot-basierten Ansatz ersetzt. Siehe Abschnitt "Daten-Pipeline-Architektur (L0–L3)".
> **Archivierte Entwürfe:** siehe `IMPLEMENTATION_PLAN_ARCHIVE.md` (Schritt 2 deprecated).
**Ziel:** Eine einzelne Agentur-URL kann erfasst werden und liefert bereinigten, profilfokussierten Text — bereit für den Note-Taker (L1).
**Was gebaut wird:**
- `crawler_engine.py`: Playwright-basiert mit robots.txt-Parser, URL-Normalisierung, Rate Limiting (2s/Domain), Blacklist-Check
- `blacklist.yaml` mit Aggregatoren (MSWL, QueryTracker, PublishersMarketplace)
- `autoquery/simulation/page_capture.py` (L0 + L0.3): Sektionsweise PNG-Screenshots + `document.body.innerText` → `text_content/{agent}.txt`
- `autoquery/simulation/text_cleaner.py` (L0.6): regelbasiertes Strippen von Nav/Footer/Sidebar-Labels → `cleaned/{agent}.txt`
- Crawl-Run-Logging in `crawl_runs`-Tabelle
**Nicht in diesem Schritt:** Browser Agent (Schritt 4), Sitemap/BFS (nur für manuelle Tests nötig), monatlicher Re-Crawl (Post-MVP)
**Feature-Dateien:** `02_crawler_engine.md`
**Testbar wenn:**
- Crawler fetcht 1 Seite einer bekannten Agentur unter Beachtung von robots.txt und Rate Limit
- Blacklist-Check wirft Exception bei QueryTracker-URL
- `page_capture.py` liefert vollständige PNG-Abschnitte + innerText-Datei für 5 verschiedene Agenten-Seiten
- `text_cleaner.py` entfernt Nav/Footer/Sidebar zuverlässig (manuelle Stichprobe gegen 5 Profile)
- Crawl-Run wird in DB protokolliert
---
## Schritt 3 — Note-Taker & Fact-Checker (L1 / L1-V)
> **Architektur-Update:** Dieser Schritt deckt nun die Schichten **L1 (Note-Taker)** und **L1-V (Fact-Checker)** ab. Statt einer einstufigen JSON-Extraktion mit kanonischen Genres ist das Ziel ein zweistufiger agentischer Flow: Note-Taker erzeugt semi-strukturierten natürlich-sprachlichen Output, Fact-Checker verifiziert gegen den Quelltext und produziert einen Korrekturreport. Die Kanonisierung (Mapping auf feste Genre-Tags) wird in L2 verschoben. Siehe Abschnitt "Daten-Pipeline-Architektur (L0–L3)".
> **Archivierte Entwürfe:** siehe `IMPLEMENTATION_PLAN_ARCHIVE.md` (Schritt 3 deprecated).
**Ziel:** Aus bereinigtem Text (L0.6) entsteht ein strukturierter, verifizierter, natürlich-sprachlicher Profil-Output, der im Review-Interface geprüft werden kann.
**Was gebaut wird:**
- **L1 — Note-Taker:** `profile_extractor.py` wird auf den neuen System Prompt umgestellt (`/Users/alex/Downloads/extraction_system_prompt.txt`). Output: strukturierte natürliche Sprache mit Feldern Identity / Global Conditions / Preference Sections (mit Wants, Does-Not-Want, Conditions, Tropes, Comp Titles) / Hard Nos / Submission Requirements / Taste References / Cross-Cutting Themes / Confidence Flags. Keine induzierten Genres.
- **L1-V — Fact-Checker:** unabhängiger zweiter Agent (Claude) prüft L1 gegen `cleaned/{agent}.txt`, liefert Korrekturreport (Halluzinationen, fehlende Felder, gedropte Conditions) + korrigiertes L1.
- **Benchmark-Suite:** 8 manuell gecheckte MSWL-Profile in `batch_capture_output/cleaned/` als permanente Testsuite für die 4 Qualitätsdimensionen (Completeness, Faithfulness, Condition Preservation, Structural Linkage).
- **Streamlit Review-Interface:** Anzeige von L1-Output + L1-V-Report nebeneinander, Editieren, Genehmigen/Ablehnen/Überspringen, Link zur Originalseite. Dient als QA-Oberfläche für den Fact-Checker.
- Domain-Verwaltung im Streamlit: Einzel-URL + CSV-Upload
**Feature-Dateien:** `05_llm_extraction.md`, `06_review_interface.md`
**Testbar wenn:**
- L1-Output für alle 8 Benchmark-Profile entspricht der definierten Struktur (alle anwendbaren Sections vorhanden)
- Faithfulness = 100% auf Benchmark (jede Zeile aus Quelltext belegbar — keine Halluzinationen)
- Completeness ≥ 95% Hard-Nos, ≥ 90% Comp Titles, 100% Sections auf Benchmark
- Condition Preservation = 100% (Klauseln wie "only if X", "not set in Rome" bleiben erhalten)
- L1-V findet injizierte Halluzinationen in einem Adversarial-Test (≥ 3 künstliche Fehler pro Profil)
- Streamlit zeigt L1 + L1-V-Report + erlaubt Edit + Approve
- CSV-Upload mit 5 Domains funktioniert (Validierung, Vorschau, Import)
---
## Schritt 4 — Daten befüllen (≥ 200 Profile)
**Ziel:** Mindestens 200 genehmigte Agenten-Profile in der Datenbank, verteilt über ≥ 5 Genres und ≥ 3 Audience-Kategorien.
**Was gebaut wird:**
- `browser_agent.py`: Claude Haiku 4.5 basierter Agent für Erstcrawl — identifiziert Profil-URLs, schreibt in `known_profile_urls`
- `seed_list.yaml` mit ~50–80 Agentur-Domains (manuell recherchiert)
- `genre_aliases.yaml` mit min. 30 Einträgen
- Batch-Pipeline: Browser Agent → Crawler → Extractor → Review Queue
**Ablauf:**
1. Admin recherchiert 50–80 Agentur-Domains und trägt sie in `seed_list.yaml` ein
2. Browser Agent läuft pro Domain, findet Profil-URLs
3. Crawler fetcht alle Profil-URLs
4. Extractor extrahiert Profile
5. Admin reviewed alle Profile im Streamlit-Interface
6. Genre-Alias-Tabelle wird parallel befüllt und validiert
**Feature-Dateien:** `03_browser_agent.md`, `06_review_interface.md`
**Testbar wenn:**
- ≥ 200 Profile mit Status `approved` in DB
- Verteilung: ≥ 5 Genres, ≥ 3 Audiences, ≥ 20 Agenturen
- `known_profile_urls` enthält verifizierte URLs für alle Domains
- `genre_aliases.yaml` hat ≥ 30 Einträge und wird beim Server-Start geladen
**Hinweis:** Dies ist der zeitaufwändigste Schritt. Der Browser Agent spart Arbeit, aber das Review ist manuell. Parallelisierbar: während Profile reviewed werden, können weitere Domains gecrawlt werden.
---
## Schritt 5 — Per-Section Embeddings (L3)
> **Architektur-Update:** Dieser Schritt wird zu **L3 (Per-Section Embeddings)**. Das ursprünglich geplante Gesamt-Embedding pro Agent (70/30 gewichtet aus `wishlist_raw` + `bio_raw`) wird ersetzt durch ein Embedding pro Preference Section, mit Matching via `max(cosine_similarity(manuscript, section_i))`. Konkrete Methode noch IN RECHERCHE. Siehe Abschnitt "Daten-Pipeline-Architektur (L0–L3)".
> **Archivierte Entwürfe:** siehe `IMPLEMENTATION_PLAN_ARCHIVE.md` (Schritt 5 deprecated).
**Ziel:** Alle 200+ genehmigten Agenten haben pro Preference Section ein Embedding, und ein Test-Manuskript kann eingebettet + über `max(cosine_similarity)` gematcht werden.
**Was gebaut wird:**
- `model.py`: Abstrakte Embedding-Schnittstelle, BGE-large-en-v1.5 Implementierung, Instruction Prefixes
- `pipeline.py`: **pro Preference Section** ein Embedding (statt eines Gesamtvektors pro Agent); Manuskript-Embedding zweistufig (Volltext + Query Expansion); Matching-Score pro Agent = `max_i cosine(manuscript, section_i)`
- Query Expansion via Ollama: 12 Keywords in Agenten-Sprache
- `recompute_all_embeddings` Skript (für Modell-Wechsel oder Bulk-Update aller Sections)
- Embedding-Trigger bei Review-Approval (Integration mit Schritt 3 / L1-V)
- **Offen (IN RECHERCHE):** Section-Granularität (nur Preference Sections? auch Cross-Cutting Themes separat?), Embedding-Modell-Wahl für kurze Textsegmente, Aggregationsstrategie (max vs. top-k-Mittel)
**Feature-Dateien:** `07_embedding_pipeline.md`
**Testbar wenn:**
- Alle ≥ 200 genehmigten Agenten haben ≥ 1 Section-Embedding (`embedding IS NOT NULL` pro Section)
- Bei einem Agenten mit sowohl "YA Horror" als auch "PB STEAM": Horror-Manuskript matcht die Horror-Section deutlich stärker als die PB-Section
- Cosine Similarity zwischen Fantasy-Manuskript und einer Fantasy-Section ist höher als zu jeder Non-Fiction-Section
- Query Expansion produziert 12 sinnvolle Keywords für 3 Test-Manuskripte
- `recompute_all_embeddings` läuft ohne Fehler durch
---
## Schritt 6 — Matching-Algorithmus
> **Architektur-Update:** Hard-Nos werden nicht mehr per Cosine-Threshold (0.75) gefiltert, sondern deterministisch via L2-Keyword-Listen. Die finalen Scoring-Gewichte (vorher hand-tuned 0.35/0.25/0.25/0.15) werden neu bestimmt, sobald L2- und L3-Signale vorliegen — die alte Konvexkombination passt nicht mehr zur veränderten Signal-Struktur.
> **Archivierte Entwürfe:** siehe `IMPLEMENTATION_PLAN_ARCHIVE.md` (Schritt 6 deprecated — teilweise).
**Ziel:** Für ein Test-Manuskript kommen sinnvoll gerankte Ergebnisse zurück. Alle Scoring-Signale funktionieren; Hard-Nos werden deterministisch erzwungen.
**Was gebaut wird:**
- `filter.py`: Harte Constraints (`is_open`, `opted_out`, `review_status`) + **Hard-Nos-Filter via L2-Keyword-Listen** (deterministischer Boolean-Check, kein Cosine)
- `scorer.py`: kombiniert L2-Boolean-Signale (Genre-/Audience-Match), FTS (`ts_rank_cd` auf `fts_vector`) und L3-Semantic-Score (`max cosine` über Section-Embeddings). Gewichte und Normalisierung werden festgelegt, sobald L2/L3 stabil sind.
- `reranker.py`: MMR mit λ=0.7, max. 3 pro Agentur in Top-10
- Genre-Alias-Matching (aus L2): Exakt → Alias → Embedding-Fallback
- Audience-Proximity-Score: Stufenmodell
- Match-Tags-Berechnung (serverseitig): ✓/~/✗ pro Dimension
**Feature-Dateien:** `08_matching_algorithm.md`
**Testbar wenn:**
- Precision@10 > 0.5 auf Rückwärtstest (≥ 20 bekannte Agent-Autor-Beziehungen)
- Hard-Nos Violation Rate = 0% (deterministisch über L2-Keyword-Filter geprüft)
- Max. 3 Agenten derselben Agentur in Top-10
- Genre "Cozy Fantasy" matcht auf Agent mit "Cozy Mystery" niedriger als auf "Cozy Fantasy"
- Match-Tags sind spezifisch (nicht generisch)
- Ergebnis in < 3 Sekunden (200+ Agenten)
---
## Schritt 7 — Backend-API
**Ziel:** Alle API-Endpunkte stehen und sind mit Testdaten verifiziert. Frontend kann gebaut werden.
**Was gebaut wird:**
- FastAPI-Routen:
  - `POST /api/match` — Manuskript-Input (Conversational Flow Daten + Uploads) → Matching-Ergebnisse
  - `POST /api/upload` — Datei-Upload (MIME-Type-Validierung, Text-Extraktion, Kürzung)
  - `POST /api/auth/register` — Registrierung (E-Mail + Passwort)
  - `POST /api/auth/login` — Login → JWT
  - `GET /api/results/{manuscript_id}` — Ergebnisse abrufen (3 ohne Auth, 20 mit Auth)
  - `POST /api/opt-out` — Opt-Out-Formular
  - `POST /api/events` — Interaction Event loggen (async)
- Pydantic-Schemas: `AgentPublic` (ohne `*_raw`) vs. `AgentInternal` (mit `*_raw`)
- JWT-Auth (bcrypt, Access + Refresh Token)
- Rate Limiting: 5 Login-Versuche/15min, 10 Matchings/h
- Input-Sanitization: HTML-Strip, Pydantic-Validierung mit Längen-Limits
- Session-ID für nicht-eingeloggte Nutzer (UUID v4, HttpOnly-Cookie)
**Feature-Dateien:** `09_auth_and_users.md`, `10_author_input_flow.md`, `12_interaction_logging.md`
**Testbar wenn:**
- `POST /api/match` mit Test-Manuskript liefert 20 gerankte Ergebnisse mit Scores + Match-Tags
- `POST /api/upload` akzeptiert .docx/.txt/.pdf, lehnt .exe ab, extrahiert Text
- `POST /api/auth/register` erstellt User, `POST /api/auth/login` gibt JWT zurück
- `GET /api/results/{id}` liefert 3 Ergebnisse ohne JWT, 20 mit JWT
- `AgentPublic`-Schema enthält **kein** `wishlist_raw`, `bio_raw`, `hard_nos_raw`
- Rate Limiting: 6. Login-Versuch wird blockiert
- `POST /api/events` schreibt Event async in DB
- Alle Endpunkte via Swagger UI (/docs) testbar
---
## Schritt 8 — Frontend
**Ziel:** Die komplette MVP User Journey (Screens 1–8) ist im Browser nutzbar.
**Was gebaut wird:**
- Next.js App mit folgenden Seiten/Komponenten:
  - **Landing Page** (Screen 1): Headline, Subtext, CTA, Dreischritt-Explainer
  - **Conversational Flow** (Screen 2+3): Chat-UI, Fragensequenz, Upload-Zone, Animations
  - **Loading** (Screen 4): Fortschrittsindikator mit Textfeedback
  - **Ergebnisse** (Screen 5–7): Karten-Grid, Teaser (3) vs. Full (20), Aufklappen, Match-Tags, Submission-Checkliste
  - **Registrierung** (Screen 6): Inline auf Ergebnis-Seite
  - **Login** Seite (für Rückkehrer)
  - **Feedback-Banner** (Screen 8): One-Click nach 60s
- Responsive: Desktop + Mobile
- Interaction Event Tracking: Events an `POST /api/events` senden
- Session-Management: JWT in HttpOnly-Cookie oder Bearer Token
**Seiten die nicht Teil des MVP-Flows aber nötig sind:**
- Opt-Out-Seite (öffentlich, Formular → `POST /api/opt-out`)
- "Für Agenten"-Informationsseite (statisch)
- Impressum + Datenschutzerklärung (statisch)
**Feature-Dateien:** `00_mvp_definition.md` (Screens 1–8, Features F1–F7), `11_results_display.md`
**Testbar wenn:**
- Komplette User Journey durchspielbar: Landing → Conversational Flow → Upload → Loading → 3 Teaser → Registrierung → 20 Ergebnisse → Aufklappen → Checkliste
- Conversational Flow: Frage erscheint, Antwort wird bestätigt, nächste Frage erscheint
- Genre/Audience als Dropdown, Rest als Freitext
- Upload: Drag & Drop funktioniert, Typ-Zuordnung, Fortschritt
- Ergebnisse: Match-Tags sind spezifisch, Score-Balken sichtbar
- Aufklappen: Keywords, Submission-Anforderungen, Checkliste, Timestamp, Link
- Registrierung inline: 3 → 20 Karten ohne Neuladen
- Mobile: vollständig nutzbar
- Feedback-Banner erscheint nach 60s
---
## Schritt 9 — Integration, Compliance & Logging
**Ziel:** Alles hängt zusammen, Compliance-Checkliste ist abgehakt, Logging funktioniert End-to-End.
**Was gebaut wird / geprüft:**
- Interaction Logging End-to-End: Frontend sendet Events → API schreibt async → DB
- Session-ID-Lifecycle: Cookie gesetzt → Events geloggt → bei Login mit user_id verknüpft
- E-Mail-Verifizierung (nach Registrierung, non-blocking)
- Monitoring-Alerts konfigurieren: Ollama-Ausfall, DB-Speicher, Opt-Out-Eingang
- Backup: Erstes `pg_dump`, Restore testen
- Compliance-Checkliste durchgehen (Feature 14)
**Compliance-Checks (alle aus `14_compliance_and_gdpr.md`):**
- [ ] Blacklist technisch erzwungen
- [ ] `*_raw`-Felder nicht in öffentlicher API
- [ ] Frontend zeigt keinen Originaltext
- [ ] Opt-Out-Seite funktioniert End-to-End
- [ ] "Für Agenten"-Seite live
- [ ] Impressum + Datenschutz live
- [ ] Timestamps auf jedem Profil
- [ ] Quellenlinks auf jedem Profil
- [ ] Verifikations-Hinweis auf jedem Profil
- [ ] Interaction Logging in Datenschutzerklärung dokumentiert
**Feature-Dateien:** `12_interaction_logging.md`, `14_compliance_and_gdpr.md`, `15_infrastructure.md`
**Testbar wenn:**
- Ein kompletter User-Durchlauf (Landing → Ergebnisse) erzeugt die erwarteten Events in `interaction_events`
- Opt-Out-Formular → Agent wird als `opted_out` markiert, `*_raw`-Felder gelöscht, taucht nicht mehr in Matchings auf
- `pg_dump` + `pg_restore` erfolgreich getestet
- Alle Compliance-Checks oben abgehakt
---
## Schritt 10 — Qualitätssicherung & Soft Launch
**Ziel:** MVP ist validiert und bereit für echte Nutzer.
**Phase A — Matching-Qualität validieren:**
- Rückwärtstest: ≥ 20 bekannte Agent-Autor-Beziehungen (aus Danksagungen recherchiert)
- Precision@10 > 0.5
- Hard-Nos Violation Rate = 0%
- 1–2 Branchenkenner bewerten 20–30 Matchings (Expert Review Score ≥ 4/5)
- Gewichte ggf. anpassen (Genre, FTS, Semantic, Audience)
**Phase B — UX validieren:**
- Hallway-Test: 5 Autoren durchlaufen die Journey
- Versteht der Nutzer Landing Page in < 10s?
- Conversational Flow in < 5 Min abschließbar?
- Ergebnisse erzeugen Reaktion? (Freude, Neugier, Überraschung)
- Feedback einarbeiten
**Phase C — Soft Launch:**
- Analytics konfigurieren: Visit-to-Signup, Engagement-Timer, Feedback-Events
- Einladung an 100–200 Autoren (r/PubTips, AbsoluteWrite, Writing Twitter/BlueSky)
- 4 Wochen Validierungszeitraum
- Qualitative Interviews mit 10–15 Nutzern
- Entscheidungspunkte nach 4 Wochen (siehe `00_mvp_definition.md`)
**Feature-Dateien:** `00_mvp_definition.md` (Metriken, Launch-Strategie, Entscheidungspunkte)
**Testbar wenn:**
- Alle drei MVP-Metriken sind messbar konfiguriert
- Mindestens 1 vollständiger User-Durchlauf durch einen externen Tester ohne Hilfe
- Keine kritischen Bugs
---
## Abhängigkeiten auf einen Blick
```
Schritt 1 ──→ Schritt 2 ──→ Schritt 3 ──→ Schritt 4
   │              │              │              │
   │              │              │              ▼
   │              │              │         Schritt 5 ──→ Schritt 6
   │              │              │                           │
   │              │              │                           ▼
   │              │              │                      Schritt 7 ──→ Schritt 8
   │              │              │                                       │
   │              │              │                                       ▼
   │              │              │                                  Schritt 9 ──→ Schritt 10
```
Schritte 1–4 sind sequentiell (jeder braucht den vorherigen). Ab Schritt 5 ist die Abhängigkeitskette ebenfalls linear. **Kein Schritt kann parallelisiert werden** — jeder baut auf dem Ergebnis des vorherigen auf.
Einzige Ausnahme: Innerhalb von Schritt 4 können Crawling und Review parallelisiert werden (Admin reviewed während neue Domains gecrawlt werden).
---
## Schnellreferenz: Schritt → Feature-Dateien
| Schritt | Baut auf | Layer | Feature-Dateien |
|---|---|---|---|
| 1. Infrastruktur & DB | — | — | `01_database_schema`, `15_infrastructure` |
| 2. Capture & Cleaning | Schritt 1 | L0, L0.3, L0.6 | `02_crawler_engine` |
| 3. Extraktion & Review | Schritt 2 | L1, L1-V | `05_llm_extraction`, `06_review_interface` |
| 4. Daten befüllen | Schritt 3 | — (nutzt L0–L1-V) | `03_browser_agent`, `06_review_interface` |
| — | — | L2 (Kanonisierung) | in Recherche |
| 5. Embeddings | Schritt 4 | L3 | `07_embedding_pipeline` |
| 6. Matching | Schritt 5 | nutzt L2 + L3 (+ optional L1) | `08_matching_algorithm` |
| 7. Backend-API | Schritt 6 | — | `09_auth_and_users`, `10_author_input_flow`, `12_interaction_logging` |
| 8. Frontend | Schritt 7 | — | `00_mvp_definition`, `11_results_display` |
| 9. Integration | Schritt 8 | — | `12_interaction_logging`, `14_compliance_and_gdpr`, `15_infrastructure` |
| 10. QA & Launch | Schritt 9 | — | `00_mvp_definition` |
