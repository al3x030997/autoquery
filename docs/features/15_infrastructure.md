# Feature 15 — Infrastructure

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul 4.1, 17 (NFRs, 17.1, 17.2)

## Scope

Docker Compose, Monitoring & Alerting, Backup & Recovery, Ollama Health-Check, Performance-Ziele.

---

## Docker Compose

Alle Komponenten lokal entwickelbar und deploybar. Benannte Volumes für persistente Daten (PostgreSQL, Redis, Ollama-Modelle) — keine anonymen Volumes.

Services: PostgreSQL, Redis, Ollama, FastAPI, Celery Worker, Celery Beat, Next.js Frontend, Streamlit Review-UI.

---

## Ollama Health-Check & Graceful Degradation

Docker Health-Check pingt Ollama alle 5 Minuten.

| Komponente | Bei Ausfall | Verhalten |
|---|---|---|
| Matching (Schicht 1–3) | Keine Auswirkung | Normal |
| Query Expansion | Gecachte Version oder 100% Volltext-Embedding | Degraded |
| LLM-Erklärungen | Button ausgeblendet | Degraded |
| Crawling & Extraktion | Blockiert | Alert an Admin |

---

## Monitoring & Alerting

**Kritische Alerts (sofortige E-Mail):**

| Trigger | Quelle |
|---|---|
| Monatlicher Crawl nicht gestartet | Celery Beat Watchdog |
| Ollama nicht erreichbar (5 Min) | Docker Health-Check |
| DB-Speicher > 80% | Täglicher Check |
| Discard-Rate > 40% im Crawl-Run | Crawl-Run-Auswertung |
| >10 unreachable URLs derselben Domain | Re-Crawl |
| Embedding-Pipeline-Fehler | Modell/Dimension |
| Opt-Out-Request eingegangen (72h Frist) | Opt-Out-Formular |

**Informations-Alerts (tägliche Zusammenfassung):**
Neue Profile im Review, offene Recrawl-Requests, Celery-Worker-Restarts, Login-Versuche über Schwellenwert.

**Nur Logging:** Einzelne Seiten-Fehler, Review-Entscheidungen, Matching-Requests, Events, erfolgreiche Crawls.

MVP: Alerts per E-Mail. Post-MVP: Webhook (Slack/Discord).

---

## Backup & Disaster Recovery

**Backup:** Tägliches `pg_dump` (komprimiert, separates Volume). Retention: 7 tägliche, 4 wöchentliche, 3 monatliche.

**Restore:** Vor Launch einmal vollständig testen. `pg_restore` + `REINDEX` (IVFFlat-Indizes). Prozedur dokumentiert im Repository.

**Priorität bei Datenverlust:**
1. `agents` inkl. Embeddings (Monate Review-Arbeit)
2. `known_profile_urls` (verifizierte URL-Struktur)
3. `interaction_events` (Phase-2-Investition)
4. `users` + `manuscripts`

---

## Performance-Ziele

| Operation | Ziel-Latenz |
|---|---|
| Matching gesamt (ohne LLM-Erklärung) | < 3s |
| davon Query Expansion (gecacht) | < 1s |
| LLM-Erklärung (on demand) | < 10s |
| Frontend Seiten-Load | < 2s |
| Event Logging | Non-blocking (async) |

**Skalierung:** 500–5000 Agenten, bis 10.000 Nutzer, min. 20 concurrent Matchings.

---

## Pflicht-Logging (explizit ausgeschlossen: Originaltext, Manuskript-Inhalte)

Crawl-Runs, Extraktionen, Review-Entscheidungen, Matching-Metadaten (nur IDs/Scores), Interaction Events, Opt-Out-Requests, Fehler-Reports, Blacklist-Verstöße.
