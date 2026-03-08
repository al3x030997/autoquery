# Feature 13 — Monatlicher Re-Crawl & Datenpflege (Post-MVP)

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul J (14.1–14.2)
> **Nicht im MVP.** Dieses Feature dokumentiert die Re-Crawl-Architektur für die Zeit nach dem Soft Launch. Im MVP werden Profile nur beim Erstcrawl angelegt — manueller Re-Crawl einzelner Profile bei Bedarf.

## Scope

Celery Beat monatlicher Zyklus, Incremental Requests, Änderungserkennung, Priority Re-Crawling, Timestamp-Anzeige.

## Dateien

```
tasks/
└── crawler_tasks.py   # Celery Tasks + Beat Schedule
```

---

## Monatlicher Crawl-Zyklus

**Trigger:** Celery Beat, monatlich (konfigurierbar).

**Ablauf:**
1. Alle URLs aus `known_profile_urls` mit `status = active` fetchen
2. Conditional Request: `If-Modified-Since` + `If-None-Match` (ETag)
3. HTTP 304 → nur `last_checked_at` updaten
4. Geänderte Seiten: Fakten und Keywords neu extrahieren, Embedding neu berechnen (aus gespeichertem Originaltext — Store More, Show Less), bei Änderungen → Status `pending`, Review-Queue
5. Neue Domains aus `seed_list.yaml` → vollständiger Erstaufnahme-Prozess (Browser Agent → Extraktion → Review)
6. Nicht erreichbare URLs: `consecutive_failures` inkrementieren (siehe Feature 01, `known_profile_urls` Lifecycle)

**Wichtig:** Re-Crawls lesen **nur** aus `known_profile_urls` — kein BFS, keine Sitemap.

---

## Priority Re-Crawling

**User-Flow:**
1. Eingeloggter Nutzer klickt "Fehler melden" bei Agenten-Profil
2. Freitext: Was stimmt nicht?
3. Eintrag in `recrawl_queue`

**System:**
- Celery-Task prüft Queue täglich
- Priorisierte Profiles werden innerhalb 48h re-gecrawlt
- Nach Re-Crawl: `recrawl_requested = FALSE`, Timestamp bleibt für Audit

---

## Timestamp-Anzeige

Jedes Profil im Frontend zeigt:
- "Zuletzt aktualisiert: [Datum]" (aus `last_checked_at`)
- Link zur Originalseite
- Hinweis: "Bitte prüfe Submission-Anforderungen direkt beim Agenten"
