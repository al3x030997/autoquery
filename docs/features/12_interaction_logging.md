# Feature 12 — Interaction Logging

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul F (10.1–10.5)

## Scope

Event-Logging für Phase-2-Vorbereitung, Phase-2-Trigger, Datenschutz. **Muss von Tag 1 aktiv sein.** Explizites Feedback (1–5 Sterne) ist nicht im MVP — kommt ab ~200 aktive Nutzer.

## Dateien

```
logging/
└── interaction_logger.py
```

---

## Zweck

Interaction Logging ist die Investition in Phase 2. Ohne Interaktionsdaten kein Upgrade auf supervised Learning. Logging darf die Matching-Latenz nicht beeinflussen — **alle Events asynchron schreiben**.

---

## Event-Logging (MVP)

- `result_shown` — serverseitig bei jedem Matching
- `card_clicked`, `profile_expanded`, `submission_checklist`, `source_link_clicked` — vom Frontend per API
- `signup_cta_shown`, `signup_completed` — Konversions-Events
- `feedback_positive`, `feedback_neutral` — One-Click-Feedback-Banner
- `result_ignored` — ausgelöst nach 30s ohne Interaktion in sichtbarer Liste

Für vollständige Event-Typen und Signal-Stärken → siehe Feature 01 (Tabelle `interaction_events`).

---

## Phase-2-Trigger

Wöchentlicher Celery-Task prüft ob Mindestmenge erreicht:
- ≥ 500 unique (manuscript_id, agent_id)-Paare mit non-neutralem Event
- Davon ≥ 50 positive (contacted, full_ms_requested, offer_received)
- Davon ≥ 50 negative (marked_rejected, result_ignored)

Bei Erreichen → Admin-Notification. Schwellenwerte konfigurierbar.

---

## Datenschutz

- Events enthalten nur IDs + Metadaten — **keinen Manuskript-Inhalt**
- In Datenschutzerklärung dokumentieren
- Anonyme Session-IDs nach 90 Tagen löschen
