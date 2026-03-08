# Feature 05 — LLM-Extraktion

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul B (6.1–6.4)

## Scope

Ollama-basierte Profil-Extraktion aus bereinigtem Text, Prompt-Management, Qualitätsprüfung. **Nicht** in diesem Feature: Review-Interface (→ 06), Embedding-Berechnung (→ 07).

## Dateien

```
extractor/
├── profile_extractor.py   # LLM-Extraktion
└── prompts.py             # Alle Prompts zentral, versioniert
```

---

## Strategie: Store More, Show Less

| Datentyp | Speichern? | Im Frontend? | Begründung |
|---|---|---|---|
| Genres, Audience, Submission-Anforderungen | ✅ | ✅ | Fakten, nicht schützbar |
| Maschinell extrahierte Keywords | ✅ | ✅ | Eigene maschinelle Schöpfung |
| Embedding-Vektor | ✅ | — | §44b UrhG — Text and Data Mining |
| Wunschliste als Fließtext | ✅ | ❌ (MVP) | Intern für Embedding-Qualität + Review |
| Bio als Fließtext | ✅ | ❌ (MVP) | Intern für Embedding-Qualität + Review |
| Hard-Nos als Fließtext | ✅ | ❌ (MVP) | Intern für Embedding-Qualität + Review |

Originaltexte werden intern gespeichert, im MVP nicht veröffentlicht. Frontend-Anzeige kann später ohne Architektur-Änderung aktiviert werden (reine UI-Entscheidung, idealerweise nach Rechtsberatung).

---

## Verarbeitungsreihenfolge

1. Bereinigter Text liegt im RAM (aus Feature 04)
2. LLM extrahiert strukturierte Felder (Fakten, Keywords)
3. LLM extrahiert Originaltext-Segmente (Wishlist, Bio, Hard-Nos) als separate Felder
4. Embedding wird aus dem Volltext berechnet (Feature 07)
5. Alles wird persistent gespeichert

---

## Zu extrahierende Felder

**Strukturierte Felder (öffentlich):**
- `name` — Vollständiger Name
- `agency` — Name der Agentur
- `email` — Submission-E-Mail (intern, nie öffentlich)
- `country` — Land
- `genres` — Liste der vertretenen Genres
- `audience` — Liste: Adult / YA / Middle Grade / Children's
- `keywords` — Maschinell extrahierte Keywords aus Wunschliste (kompakte Begriffe)
- `hard_nos_keywords` — Keywords aus Ablehnungen (kompakte Begriffe)
- `submission_req` — JSONB: query_letter (bool), synopsis (bool), pages (int|null), full_manuscript (bool), bio (bool), additional_notes (kurze faktische Notiz)
- `is_open` — Submissions-Status
- `response_time` — Faktische Angabe

**Originaltext-Felder (intern, nie im Frontend):**
- `wishlist_raw` — Wunschliste als Fließtext
- `bio_raw` — Bio/Über-mich als Fließtext
- `hard_nos_raw` — Ablehnungen als Fließtext

---

## Qualitätsprüfung nach Extraktion

- `name` muss vorhanden sein
- `genres` muss min. 1 Eintrag enthalten
- `keywords` sollte min. 3 Einträge enthalten

Schlägt die Prüfung fehl → Status `extraction_failed`, geloggt, nicht ins Review.

---

## Prompt-Anforderungen

- Alle Prompts zentral in `prompts.py`
- `format: "json"` im Ollama-Aufruf erzwingen
- Jeder Prompt versioniert — Änderungen = neue Versionsnummer
- Keywords-Prompt: keine Sätze, nur prägnante Begriffe (Keywords dienen als kompakte Repräsentation für FTS + Frontend)
- Separater Prompt-Abschnitt für Originaltext-Extraktion: Wishlist, Bio, Hard-Nos als zusammenhängende Textblöcke extrahieren
- Input: max. 4000 Wörter (Rest abschneiden)
