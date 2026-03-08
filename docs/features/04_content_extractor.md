# Feature 04 — Content Extractor & Quality Gate

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul A (5.14–5.16)

## Scope

Page Classifier (INDEX vs. CONTENT), HTML-zu-Text Extraktion, Quality Gate mit 7 Bewertungsdimensionen. Alles was zwischen Crawl-Output und LLM-Extraktion passiert.

## Dateien

```
crawler/
├── page_classifier.py     # INDEX vs. CONTENT
└── content_extractor.py   # HTML → sauberer Text + Quality Gate
```

**Hinweis:** Der extrahierte Rohtext wird nach LLM-Extraktion (Feature 05) persistent in der DB gespeichert (`*_raw`-Felder). Zwischenstationen (HTML, bereinigter Text vor Extraktion) existieren nur im RAM.

---

## Page Classifier

Entscheidet ob eine Seite eine Index Page (Agenten-Liste) oder Content Page (Einzel-Profil) ist.

- **Input:** Seiten-Titel + erste 500 Wörter des bereinigten Body-Texts
- **Modell:** Ollama lokal, Prompt auf Englisch
- **Output:** Exakt `INDEX` oder `CONTENT`
- **Fallback:** Bei uneindeutigem Output → `CONTENT` (lieber doppelt prüfen als Agent verpassen)
- **Vor Produktion:** Kalibrierung an min. 30 manuell gelabelten Beispielseiten. Ergebnisse dokumentieren.
- **Referenz:** Sasazawa & Sogawa (2025) — Titel + Body verwenden, Body auf 500 Wörter kürzen bei Rauschen

---

## Content Extractor

**Zu entfernen:** `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>`, `<form>`, Elemente mit CSS-Klassen: nav, menu, sidebar, footer, cookie, banner, advertisement, related, social, newsletter, popup, modal, breadcrumb

**Zu bevorzugen:** `<main>`, `<article>`, semantische `<section>`-Elemente

**Canonical URL** aus `<link rel="canonical">` extrahieren.

---

## Quality Gate — 7 Dimensionen (Gesamtscore 0–1)

| # | Dimension | Gewicht | Details |
|---|---|---|---|
| 1 | Mindestlänge | 20% | <150 Wörter → sofort Discard. 150–300 → reduziert. >5000 → kürzen auf 4000 |
| 2 | Signal-Rausch-Verhältnis | 25% | Anteil agenten-relevanter Begriffe (represent, seeking, wishlist, submit, genre...). <1% → stark reduziert, >3% → voll |
| 3 | Strukturelle Vollständigkeit | 25% | Wunschliste (50%), Bio/Name (30%), Submission (20%). Fehlt Wunschliste → kritisch |
| 4 | Rausch-Indikatoren | 15% | Cookie-Hinweise, Privacy, 404-Texte. ≥3 → proportional reduziert |
| 5 | Encoding & Lesbarkeit | 10% | Lesbare Zeichen / Gesamt. <60% → sofort Discard |
| 6 | Spracherkennung | 5% | Englische Funktionswörter in ersten 200 Wörtern. <3 Treffer → Discard |
| 7 | Duplikat-Erkennung | Hart | MD5-Hash vs. alle Hashes des Runs. Duplikat → Discard |

## Aktionen

| Score | Aktion |
|---|---|
| ≥ 0.65, keine kritischen Issues | `extract` — normal ans LLM |
| 0.40–0.65, keine kritischen Issues | `extract_with_warning` — gelbes Flag im Review |
| < 0.40 oder kritische Issues | `discard` |

Ergebnis wird **immer** geloggt — auch bei Discard.
