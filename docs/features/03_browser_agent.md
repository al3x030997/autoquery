# Feature 03 — Browser Agent (Erstcrawl)

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul A (5.3)

## Scope

Schlanker Browser-Agent via Claude Haiku API für den Erstcrawl neuer Domains. Identifiziert gezielt Agenten-Profil-URLs. Ergebnis: verifizierte URL-Liste in `known_profile_urls`. **Nicht** Teil des monatlichen Crawl-Zyklus.

## Dateien

```
crawler/
└── browser_agent.py   # Separates Script, manuell vom Admin ausgelöst
```

---

## Warum kein fertiges Tool?

Fertige Agent-Frameworks (OpenClaw etc.) sind für 24/7-Automation, nicht für strukturierte Einmal-Batch-Jobs. Eigener Agent: volle Kontrolle über Prompts, Fehlerbehandlung, Quality Gate Integration. Überschaubarer Aufwand.

---

## Architektur

Drei Komponenten:
1. **Playwright** — Browser-Steuerung (Seiten laden, JS rendern, Screenshots)
2. **Claude Haiku 4.5** (Anthropic API) — Navigations-Entscheidungen + Profil-URL-Extraktion
3. **Zustandsautomat** — Schleife: Screenshot → Claude entscheiden → Aktion ausführen

## Zwei Phasen pro Domain

**Phase 1 — Exploration (Claude entscheidet):**
1. Agent startet auf Agentur-Homepage
2. Screenshot aufnehmen
3. Claude fragen: "Wo finde ich eine Liste von Agenten oder deren Einzelprofile? Nenne die URL oder beschreibe wo ich klicken soll."
4. Claude antwortet mit Aktion (URL navigieren, Element klicken, scrollen)
5. Wiederholen bis Agenten-Übersichtsseite + mindestens ein Einzel-Profil gefunden
6. Max. 5 Navigationsschritte pro Domain

**Phase 2 — Profil-URL-Extraktion:**
1. Agenten-Übersichtsseite identifiziert
2. Claude extrahiert alle Links zu Einzel-Profilen
3. URLs werden in `known_profile_urls` gespeichert

---

## Modell-Wahl: Claude Haiku 4.5

Für Navigations-Entscheidungen reicht Haiku — Aufgaben sind klar definiert, keine komplexe Reasoning-Kapazität nötig. 3× günstiger als Sonnet.

## Kostenschätzung (Stand März 2026, Haiku 4.5: $1/MTok Input, $5/MTok Output)

| | Berechnung | Kosten |
|---|---|---|
| 500 Agenten × 6 Calls × 1.500 Token Input | 4,5 MTok | $4.50 |
| 500 Agenten × 6 Calls × 400 Token Output | 1,2 MTok | $6.00 |
| **Gesamt 500 Agenten** | | **~$10–15** |
| + 50% Puffer | | **$15–20 einmalig** |

Eskalation auf Sonnet 4.6 für ~20 besonders komplexe Domains: +$5–10.

---

## Abbruch-Kriterien

| Bedingung | Aktion |
|---|---|
| 5 Navigationsschritte ohne Agenten-Seite | Domain → `needs_manual_review`, Admin notifiziert |
| Login-Wall erkannt | Abbruch, Admin notifiziert |
| Captcha erkannt | Abbruch, Admin notifiziert |

---

## Integration

- Separates Script, nicht Teil von Celery
- Admin löst manuell aus (Streamlit oder CLI)
- Ergebnis → `known_profile_urls` (domain, url, discovered_at, discovery_method='browser_agent')
- Monatlicher Re-Crawl liest aus dieser Tabelle

## Abgrenzung Erstcrawl vs. Re-Crawl

Browser-Agent läuft **nur** bei Erstaufnahme. Re-Crawls lesen **nur** aus `known_profile_urls`. Einzige Ausnahme: Admin gibt Domain explizit zum erneuten Erstcrawl frei (z.B. nach Website-Relaunch) → alle bestehenden URLs der Domain → `status = removed`, neue URLs ersetzen sie.
