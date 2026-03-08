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
## Schritt 2 — Crawler & Content Extraction
**Ziel:** Eine einzelne Agentur-Domain kann gecrawlt werden und liefert sauberen Text mit Quality Gate Score.
**Was gebaut wird:**
- `crawler_engine.py`: Playwright-Crawler mit robots.txt-Parser, URL-Normalisierung, Rate Limiting (2s/Domain), Blacklist-Check
- `blacklist.yaml` mit Aggregatoren (MSWL, QueryTracker, PublishersMarketplace)
- `page_classifier.py`: Ollama-basiert, INDEX vs. CONTENT
- `content_extractor.py`: HTML → sauberer Text, CSS-Klassen-Filter, Canonical URL
- Quality Gate: alle 7 Dimensionen (Mindestlänge, Signal-Rausch, Struktur, Rausch, Encoding, Sprache, Duplikat)
- Crawl-Run-Logging in `crawl_runs`-Tabelle
**Nicht in diesem Schritt:** Browser Agent (Schritt 4), Sitemap/BFS (nur für manuelle Tests nötig), monatlicher Re-Crawl (Post-MVP)
**Feature-Dateien:** `02_crawler_engine.md`, `04_content_extractor.md`
**Testbar wenn:**
- Crawler fetcht 1 Seite einer bekannten Agentur (z.B. janklow.com/agents)
- Blacklist-Check wirft Exception bei QueryTracker-URL
- Page Classifier unterscheidet Agenten-Übersicht von Einzel-Profil (≥ 80% auf 10 Testseiten)
- Quality Gate produziert Score + Issues für 5 verschiedene Seiten
- Content Extractor liefert sauberen Text ohne Nav/Footer/Cookie-Rauschen
- Crawl-Run wird in DB protokolliert
---
## Schritt 3 — LLM-Extraktion & Review-Interface
**Ziel:** Aus bereinigtem Text werden strukturierte Profile extrahiert und können im Review-Interface geprüft werden.
**Was gebaut wird:**
- `profile_extractor.py`: Ollama-basierte Extraktion aller Felder (Name, Agency, Genres, Audience, Keywords, Hard-Nos, Submission-Req, Wishlist/Bio/Hard-Nos als Rohtext)
- `prompts.py`: Versionierte Prompts, JSON-Format erzwungen, Keywords-Prompt mit Fließtext-Verbot
- Qualitätsprüfung nach Extraktion (Name vorhanden, Genres min. 1, Keywords min. 3)
- Streamlit Review-Interface: Profil-Anzeige (Fakten + Keywords + Rohtext), Editieren, Genehmigen/Ablehnen/Überspringen, Quality Gate Anzeige, Link zur Originalseite
- Domain-Verwaltung im Streamlit: Einzel-URL + CSV-Upload
**Feature-Dateien:** `05_llm_extraction.md`, `06_review_interface.md`
**Testbar wenn:**
- Extractor produziert valides JSON für 5 verschiedene Agenten-Seiten
- Alle Pflichtfelder befüllt (Name, min. 1 Genre)
- Keywords sind kompakte Begriffe (keine ganzen Sätze)
- Rohtext-Felder (`wishlist_raw`, `bio_raw`, `hard_nos_raw`) korrekt befüllt
- Streamlit zeigt extrahiertes Profil an + erlaubt Edit + Approve
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
## Schritt 5 — Embedding-Pipeline
**Ziel:** Alle 200+ genehmigten Agenten haben Embeddings, und ein Test-Manuskript kann eingebettet werden.
**Was gebaut wird:**
- `model.py`: Abstrakte Embedding-Schnittstelle, BGE-large-en-v1.5 Implementierung, Instruction Prefixes
- `pipeline.py`: Agenten-Embedding (aus `wishlist_raw` + `bio_raw`), Manuskript-Embedding (zweistufig: Volltext + Query Expansion), L2-Normalisierung, Gewichtung 70/30
- Query Expansion via Ollama: 12 Keywords in Agenten-Sprache
- `recompute_all_embeddings` Skript (für Modell-Wechsel oder Bulk-Update)
- Embedding-Trigger bei Review-Approval (Integration mit Schritt 3)
**Feature-Dateien:** `07_embedding_pipeline.md`
**Testbar wenn:**
- Alle ≥ 200 genehmigten Agenten haben `embedding IS NOT NULL`
- Cosine Similarity zwischen einem Fantasy-Manuskript und einem Fantasy-Agenten ist höher als zu einem Non-Fiction-Agenten
- Query Expansion produziert 12 sinnvolle Keywords für 3 Test-Manuskripte
- Gewichtetes Embedding (70/30) liegt im erwarteten Wertebereich
- `recompute_all_embeddings` läuft ohne Fehler durch
---
## Schritt 6 — Matching-Algorithmus
**Ziel:** Für ein Test-Manuskript kommen sinnvoll gerankte Ergebnisse zurück. Alle 4 Scoring-Signale funktionieren.
**Was gebaut wird:**
- `filter.py`: Harte Constraints (is_open, opted_out, review_status, Hard-Nos-Threshold 0.75)
- `scorer.py`: Konvexkombination mit DBSF-Normalisierung (Genre 0.35, FTS 0.25, Semantic 0.25, Audience 0.15), Fallback bei fehlendem Signal
- `reranker.py`: MMR mit λ=0.7, max. 3 pro Agentur in Top-10
- Genre-Alias-Matching: Exakt → Alias → Embedding-Fallback
- Audience-Proximity-Score: Stufenmodell
- FTS: `ts_rank_cd` auf `fts_vector`
- Match-Tags-Berechnung (serverseitig): ✓/~/✗ pro Dimension
**Feature-Dateien:** `08_matching_algorithm.md`
**Testbar wenn:**
- Precision@10 > 0.5 auf Rückwärtstest (≥ 20 bekannte Agent-Autor-Beziehungen)
- Hard-Nos Violation Rate = 0%
- Max. 3 Agenten derselben Agentur in Top-10
- Genre "Cozy Fantasy" matcht auf Agent mit "Cozy Mystery" niedriger als auf "Cozy Fantasy"
- Match-Tags sind spezifisch (nicht generisch)
- Ergebnis in < 3 Sekunden (200+ Agenten)
- DBSF-Normalisierung: Scores liegen in [0,1]
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
| Schritt | Baut auf | Feature-Dateien |
|---|---|---|
| 1. Infrastruktur & DB | — | `01_database_schema`, `15_infrastructure` |
| 2. Crawler | Schritt 1 | `02_crawler_engine`, `04_content_extractor` |
| 3. Extraktion & Review | Schritt 2 | `05_llm_extraction`, `06_review_interface` |
| 4. Daten befüllen | Schritt 3 | `03_browser_agent`, `06_review_interface` |
| 5. Embeddings | Schritt 4 | `07_embedding_pipeline` |
| 6. Matching | Schritt 5 | `08_matching_algorithm` |
| 7. Backend-API | Schritt 6 | `09_auth_and_users`, `10_author_input_flow`, `12_interaction_logging` |
| 8. Frontend | Schritt 7 | `00_mvp_definition`, `11_results_display` |
| 9. Integration | Schritt 8 | `12_interaction_logging`, `14_compliance_and_gdpr`, `15_infrastructure` |
| 10. QA & Launch | Schritt 9 | `00_mvp_definition` |
