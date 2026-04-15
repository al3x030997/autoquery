# Feature 05 — LLM-Extraktion

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul B (6.1–6.4)

## Scope

LLM-basierte Profil-Extraktion aus bereinigtem Text via dem **Note-Taker-Prompt (v2.0)**, Parser für die strukturierte Sektionsausgabe, Persistenz nach `agents.profile_notes` (JSONB) plus Best-Effort-Projektion in die bestehenden flachen Spalten. **Nicht** in diesem Feature: Review-Interface (→ 06), Embedding-Berechnung (→ 07), Matcher (→ 08), L2-Kanonisierung (→ 16).

## Dateien

```
extractor/
├── profile_extractor.py        # LLM-Aufruf, Parser-Hookup, DB-Upsert
├── note_parser.py              # plain-text → strukturiertes dict
├── prompts.py                  # NOTE_TAKER_SYSTEM_PROMPT + Roster-Prompt
└── prompts/note_taker_v1.txt   # Prompt-Asset (Quelle der Wahrheit)
```

## L1-Output (Note-Taker, v2.0)

Der Prompt erzwingt eine deterministische 8-Schritt-Sektionsstruktur:

1. **IDENTITY** — Name, Organization, Role, Pronouns, Email, Submission portal, Availability
2. **GLOBAL CONDITIONS** — sektionsübergreifende Bedingungen mit Stärke (REQUIRED/STRONGLY PREFERRED/PREFERRED)
3. **PREFERENCE SECTIONS** — N offene Sektionen (nach Audience, Genre, Form oder Hybrid). Jede mit Audience, Genres, Wants, Conditions, Does Not Want, Tropes Wanted/Excluded, Comp Titles
4. **HARD NOS** — content / format / trope / category Buckets
5. **SUBMISSION REQUIREMENTS** — pro Kategorie oder global
6. **COMP TITLES & TASTE REFERENCES** — A) High-Priority-Comps, B) Personal Favorites
7. **CROSS-CUTTING THEMES** — sektionsübergreifende Soft-Boost-Signale
8. **CONFIDENCE FLAGS** — INFERRED / NUANCED / MISSING

`note_parser.parse(text)` produziert daraus ein dict mit eben diesen Top-Level-Keys. Fehlende Sektionen → leere Container, keine Exceptions.

## Persistenz

Neue Spalten (Migration `005_add_profile_notes`):

| Spalte | Typ | Inhalt |
|---|---|---|
| `profile_notes` | JSONB | Vollständig geparste Sektionsstruktur |
| `profile_notes_raw` | TEXT | Rohausgabe des LLM (Audit-Trail, Store-More-Show-Less) |
| `prompt_version` | VARCHAR(16) | Welcher Prompt diese Notes erzeugt hat |

**Kompatibilitäts-Projektion in flache Spalten** (`genres_raw`, `audience`, `hard_nos_keywords`, `keywords`, `wishlist_raw`, …) bleibt vorerst aktiv — siehe `_project_to_columns` in `profile_extractor.py`. Diese Projektion ist **temporär**; sie verschwindet, sobald Matcher (Step 6), Embeddings-Pipeline und Review-UI sektionsnativ umgebaut sind. Neuer Code darf sich nicht auf die flachen Spalten verlassen.

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
