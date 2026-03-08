# Feature 02 — Crawler Engine

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul A (5.1, 5.4–5.13, 5.17)

## Scope

Playwright-basierter Crawler: Sitemap-Discovery, BFS-Fallback, URL-Normalisierung, Rate Limiting, Fehlerbehandlung, Pagination, Anti-Crawling-Erkennung, Incremental Crawling. **Nicht** in diesem Feature: Browser-Agent (→ 03), Content Extractor (→ 04), Page Classifier (→ 04).

## Dateien

```
crawler/
├── crawler_engine.py    # Playwright Crawling
├── seed_list.yaml       # Agentur-Domains (Admin-gepflegt)
└── blacklist.yaml       # Gesperrte Domains + Begründung
```

---

## Direct-to-Source Prinzip

Vor **jedem** Request: Blacklist-Check gegen `blacklist.yaml`. Verstoß → Exception + Log. Aggregatoren (MSWL, QueryTracker, PublishersMarketplace) sind permanent gesperrt.

---

## Crawl-Reihenfolge pro Domain (nur Erstcrawl-Fallback)

Monatliche Re-Crawls lesen ausschließlich aus `known_profile_urls` — Sitemap und BFS kommen nur beim Erstcrawl zum Einsatz, wenn der Browser-Agent (Feature 03) nicht eingesetzt wird oder fehlschlägt.

1. `robots.txt` abrufen und für den Run cachen
2. Sitemap-Discovery als primäre URL-Quelle
3. Bei fehlender Sitemap: BFS-Crawling als Fallback
4. Jede Seite vor Fetch: Blacklist → robots.txt → URL-Normalisierung → Deduplication

## Sitemap-Nutzung

Bevorzugte URL-Quelle. Gesucht wird in `robots.txt`, dann unter `/sitemap.xml` und `/sitemap_index.xml`. Verschachtelte Sitemap-Indizes rekursiv auflösen. `<lastmod>`-Feld für Incremental Crawling auswerten.

## BFS-Crawling (Fallback)

Max. 4 Ebenen tief, max. 200 Seiten pro Domain, nur interne Links. Index Pages werden vorne in die Queue eingereiht.

---

## URL-Normalisierung & Deduplication

Vor jedem Fetch:
- Schema auf HTTPS vereinheitlichen
- Trailing Slash entfernen
- `www.` normalisieren
- Tracking-Parameter entfernen (`utm_*`, `fbclid`, `gclid` etc.)
- Fragment-Anker entfernen
- Canonical URL aus `<link rel="canonical">` bevorzugen

Normalisierte URL = Deduplication-Key für den aktuellen Run.

---

## Playwright-Konfiguration

- Headless-Modus
- Custom User-Agent: AutoQuery identifiziert sich + Kontakt-URL (Best Practice / Transparenz)
- Wait: `networkidle` mit max. 8 Sekunden Obergrenze. Nach 8s mit vorhandenem Inhalt weitermachen
- Infinite Scroll: Nach initialem Load schrittweise scrollen, warten bis neue Inhalte geladen, max. 5 Scroll-Iterationen. Stoppen wenn Seitenhöhe stabil

---

## Rate Limiting

**Pro Domain**, nicht global. Mehrere Domains parallel, aber Requests an dieselbe Domain serialisiert.

| Situation | Verhalten |
|---|---|
| Standard | 2s zwischen Requests pro Domain (konfigurierbar pro Domain in `seed_list.yaml`) |
| Nach HTTP 429 | Min. 30s Pause, dann Exponential Backoff |
| Parallele Domains | Max. 5 im Erstcrawl, max. 10 im Re-Crawl |

Implementierung: Domain-scoped Semaphore mit Timestamp-Tracking. Delay wird nach jedem Request aktualisiert.

---

## Pagination

Pagination-Seiten (`?page=2`, `/page/2`, "Next"-Links, Load-More-Buttons) werden als Index Pages behandelt und vorne in die Queue eingereiht. Pagination-URLs normalisieren und deduplizieren um Endlosschleifen zu vermeiden.

---

## Fehlerbehandlung & Retry

**Permanente Fehler (404, 410):** Agent → `unreachable`. Kein Retry, kein Re-Crawl bis Admin manuell freigibt.

**Temporäre Fehler (429, 500, 503, Timeout):** Exponential Backoff, max. 3 Retries. Bei 429: zusätzlich min. 30s. Nach 3 Fehlversuchen: loggen, Seite überspringen.

**Redirects (301, 302):** Verfolgen, finale URL normalisieren und speichern.

---

## Anti-Crawling & Captcha-Erkennung

Captcha-Indikatoren (Cloudflare-Challenge, "Are you human") → Domain für aktuelle Session sperren, Admin notifizieren. Kein automatischer Bypass. Leere Responses bei HTTP 200 (Bot-Detection) → erkennen und loggen.

## Login-Wall-Erkennung

Weiterleitung auf Login-URL oder "Members only"-Inhalte → überspringen und loggen. Kein Umgehungsversuch.

---

## Incremental Crawling (Re-Crawl)

Conditional Requests beim monatlichen Re-Crawl:
- `If-Modified-Since` mit Datum des letzten Crawls
- `If-None-Match` mit gespeichertem ETag
- HTTP 304 → nur `last_checked_at` updaten, keine Neu-Extraktion
- ETag pro Agent in DB gespeichert

---

## Crawl-Run-Logging

Jeder Run wird in `crawl_runs` protokolliert (siehe Feature 01). Nach jedem Run: automatischer Check ob Discard-Rate > 40% oder Erfolgsrate < 50% → Admin-Alert.
