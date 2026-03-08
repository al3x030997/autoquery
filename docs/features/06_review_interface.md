# Feature 06 — Review Interface (Streamlit)

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul B (6.5), Modul A (5.2)

## Scope

Streamlit Admin-UI: Profil-Review-Workflow, Domain-Verwaltung (URL-Eingabe, CSV-Upload), Statistiken. Plus Embedding-Trigger bei Genehmigung.

## Dateien

```
review/
└── app.py   # Streamlit App
```

---

## Review-Workflow

1. Admin öffnet Streamlit-App
2. Ausstehendes Profil wird angezeigt (Status: `pending`)
3. Anzeige: extrahierte Fakten + Keywords, **gespeicherte Originaltexte** (Wishlist, Bio, Hard-Nos), Link zur Originalseite, Crawl-Datum, Quality Gate Score + Issues
4. Alle Felder sind editierbar vor Genehmigung
5. Aktionen: Genehmigen / Ablehnen (mit Pflichtbegründung) / Überspringen
6. Profile mit `extract_with_warning` → gelbes Flag

## Embedding-Trigger

- Bei `approved`: Embedding wird automatisch neu berechnet
- Editierte Keywords/Genres fließen ins Embedding ein
- Nachträgliche Admin-Edits an approved Profilen → Save-Button triggert Neuberechnung

---

## Domain-Verwaltung

**Format 1 — Direkte URL-Eingabe:** Domain/URL + Name + Land. System normalisiert auf Root-Domain, prüft Blacklist + bestehende Einträge.

**Format 2 — CSV-Upload:** Pflichtfelder `domain`, `name`, `country`, optional `notes`. Validierung pro Zeile, Vorschau, Import nach Bestätigung. Fehlerhafte Zeilen überspringen, nicht abbrechen.

```csv
domain,name,country,notes
janklow.com,Janklow & Nesbit,US,
inkwellmanagement.com,InkWell Management,US,speculative fiction focus
```

Beide Formate schreiben in `seed_list.yaml`. Datum + Admin-Name automatisch.

---

## Statistiken-Dashboard

- Ausstehende Profile (Anzahl)
- Genehmigte / Abgelehnte Profile
- Häufigste Ablehnungsgründe (für Prompt-Optimierung)
- Fortschrittsanzeige: "X von Y ausstehend"
