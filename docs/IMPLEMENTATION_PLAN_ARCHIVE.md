# AutoQuery Implementation Plan — Archiv deprecierter Entwürfe

> Dieses Dokument konserviert Entwürfe, Implementierungsdetails und Testkriterien aus früheren Versionen von `IMPLEMENTATION_PLAN.md`, die durch die neue **L0–L3 Daten-Pipeline-Architektur** ersetzt wurden. Nichts hier ist aktiv — aber die Überlegungen bleiben als Referenz erhalten, damit Lernerkenntnisse und Designentscheidungen nicht verloren gehen.

> Begleitend zur Umstellung auf das Schichtmodell (Screenshot-Capture → Note-Taker → Fact-Checker → Kanonisierung → Per-Section-Embeddings) wurden folgende Abschnitte aus dem aktiven Plan entfernt und hier archiviert.

---

## Schritt 2 (deprecated) — HTML-Crawl + Quality Gate

### Ursprünglicher "Was gebaut wird"-Block
- `crawler_engine.py`: Playwright-Crawler mit robots.txt-Parser, URL-Normalisierung, Rate Limiting (2s/Domain), Blacklist-Check
- `blacklist.yaml` mit Aggregatoren (MSWL, QueryTracker, PublishersMarketplace)
- `page_classifier.py`: Ollama-basiert, INDEX vs. CONTENT
- `content_extractor.py`: HTML → sauberer Text, CSS-Klassen-Filter, Canonical URL
- Quality Gate: alle 7 Dimensionen (Mindestlänge, Signal-Rausch, Struktur, Rausch, Encoding, Sprache, Duplikat)
- Crawl-Run-Logging in `crawl_runs`-Tabelle

### Ursprüngliche Testbar-Kriterien
- Crawler fetcht 1 Seite einer bekannten Agentur (z.B. janklow.com/agents)
- Blacklist-Check wirft Exception bei QueryTracker-URL
- Page Classifier unterscheidet Agenten-Übersicht von Einzel-Profil (≥ 80% auf 10 Testseiten)
- Quality Gate produziert Score + Issues für 5 verschiedene Seiten
- Content Extractor liefert sauberen Text ohne Nav/Footer/Cookie-Rauschen
- Crawl-Run wird in DB protokolliert

### Warum ersetzt
Der Screenshot-basierte Ansatz (L0) + `document.body.innerText`-Extraktion (L0.3) + regelbasierter Text-Cleaner (L0.6) liefert robusteren und wartungsärmeren Profiltext als HTML-Parsing mit CSS-Selektoren. Die 7-Dimensionen-Quality-Gate wird überflüssig, weil:
- der gerenderte Browser-Text kein Markup-Rauschen enthält,
- der regelbasierte Cleaner deterministisch Nav/Footer entfernt,
- Qualitätskontrolle nun in L1-V (Fact-Checker gegen Quelltext) stattfindet, statt auf HTML-Heuristiken zu beruhen.

Der Page Classifier (INDEX vs. CONTENT) wird durch den Browser Agent in Schritt 4 ersetzt, der Profil-URLs direkt identifiziert.

**Weiterhin aktiv:** robots.txt-Parser, Rate Limiting, Blacklist, `crawl_runs`-Logging bleiben im aktuellen Plan erhalten.

---

## Schritt 3 (deprecated) — Einstufige JSON-Extraktion

### Ursprünglicher "Was gebaut wird"-Block
- `profile_extractor.py`: Ollama-basierte Extraktion aller Felder (Name, Agency, Genres, Audience, Keywords, Hard-Nos, Submission-Req, Wishlist/Bio/Hard-Nos als Rohtext)
- `prompts.py`: Versionierte Prompts, JSON-Format erzwungen, Keywords-Prompt mit Fließtext-Verbot
- Qualitätsprüfung nach Extraktion (Name vorhanden, Genres min. 1, Keywords min. 3)
- Streamlit Review-Interface: Profil-Anzeige (Fakten + Keywords + Rohtext), Editieren, Genehmigen/Ablehnen/Überspringen, Quality Gate Anzeige, Link zur Originalseite
- Domain-Verwaltung im Streamlit: Einzel-URL + CSV-Upload

### Ursprüngliche Testbar-Kriterien
- Extractor produziert valides JSON für 5 verschiedene Agenten-Seiten
- Alle Pflichtfelder befüllt (Name, min. 1 Genre)
- Keywords sind kompakte Begriffe (keine ganzen Sätze)
- Rohtext-Felder (`wishlist_raw`, `bio_raw`, `hard_nos_raw`) korrekt befüllt
- Streamlit zeigt extrahiertes Profil an + erlaubt Edit + Approve
- CSV-Upload mit 5 Domains funktioniert (Validierung, Vorschau, Import)

### Warum ersetzt
Die einstufige JSON-Extraktion erzwingt Kanonisierung (feste Genre-Tags, Audience-Enums, Keyword-Listen) zu früh in der Pipeline. Das vermischt zwei Aufgaben:
1. **Lesen/Verstehen** dessen, was der Agent wirklich geschrieben hat,
2. **Mappen** auf ein kanonisches Vokabular.

Der neue Flow trennt beide Aufgaben:
- **L1 (Note-Taker)** liest den Text und produziert strukturierte natürliche Sprache — die Sprache des Agenten bleibt erhalten (z.B. "bubblegum horror", "weird girl lit"), Conditions wie "only if fantasy elements are very light" gehen nicht verloren.
- **L1-V (Fact-Checker)** verifiziert L1 gegen den Quelltext (Halluzinationen, fehlende Felder, gedropte Conditions).
- **L2 (Kanonisierung)** mappt später auf feste Tags — erst wenn die Rohinformation sauber vorliegt.

Das "Keywords als kompakte Begriffe, keine Sätze"-Verbot verlor Nuancen, die für hochwertiges Matching essenziell sind ("romantic comedies where both leads are POC" ≠ "romance, POC").

**Weiterhin aktiv:** Streamlit Review-Interface bleibt, wird aber zur Fact-Checker-QA-Oberfläche umgebaut; CSV-Domain-Upload bleibt.

---

## Schritt 5 (deprecated) — Gewichtetes Gesamt-Embedding (70/30)

### Ursprünglicher "Was gebaut wird"-Block
- `model.py`: Abstrakte Embedding-Schnittstelle, BGE-large-en-v1.5 Implementierung, Instruction Prefixes
- `pipeline.py`: Agenten-Embedding (aus `wishlist_raw` + `bio_raw`), Manuskript-Embedding (zweistufig: Volltext + Query Expansion), L2-Normalisierung, Gewichtung 70/30
- Query Expansion via Ollama: 12 Keywords in Agenten-Sprache
- `recompute_all_embeddings` Skript (für Modell-Wechsel oder Bulk-Update)
- Embedding-Trigger bei Review-Approval (Integration mit Schritt 3)

### Ursprüngliche Testbar-Kriterien
- Alle ≥ 200 genehmigten Agenten haben `embedding IS NOT NULL`
- Cosine Similarity zwischen einem Fantasy-Manuskript und einem Fantasy-Agenten ist höher als zu einem Non-Fiction-Agenten
- Query Expansion produziert 12 sinnvolle Keywords für 3 Test-Manuskripte
- Gewichtetes Embedding (70/30) liegt im erwarteten Wertebereich
- `recompute_all_embeddings` läuft ohne Fehler durch

### Warum ersetzt
Ein einziges Embedding pro Agent — gebildet aus `wishlist_raw` (70%) + `bio_raw` (30%) — mittelt widersprüchliche Preferenzen zu einem unscharfen Vektor. Beispiel: ein Agent, der gleichzeitig "YA Horror mit bubblegum-Vibes" und "lustige Picture Books über STEAM" sucht, bekommt einen Vektor, der weder Horror- noch PB-Manuskripte gut matcht.

**L3 (Per-Section Embeddings)** ersetzt dies: pro Preference Section (z.B. "YA Horror", "Picture Books STEAM") entsteht ein eigener Vektor. Matching läuft über `max(cosine_similarity(manuscript, section_i))` — ein Manuskript matcht genau dann stark, wenn es zu mindestens einer konkreten Section passt, statt zum verwässerten Agenten-Durchschnitt.

**Weiterhin aktiv:** BGE-large-en-v1.5, Instruction Prefixes, Query Expansion (12 Keywords), `recompute_all_embeddings` bleiben — nur die Aggregation ändert sich.

---

## Schritt 6 (deprecated — teilweise) — Cosine Hard-Nos + Hand-tuned Weights

### Entfernte Teile
- **Hard-Nos-Threshold 0.75** (Filter via Cosine-Similarity zwischen Manuskript und `hard_nos_raw`-Embedding)
- **Konvexkombination mit DBSF-Normalisierung:** Genre 0.35, FTS 0.25, Semantic 0.25, Audience 0.15

### Warum ersetzt
**Hard-Nos per Cosine:** unscharf und riskant. Ein Manuskript mit expliziter sexueller Gewalt kann einen Cosine-Score von 0.70 gegen `hard_nos_raw` haben und trotzdem durchrutschen. Hard-Nos sind semantisch binär — sie gehören in eine deterministische Keyword-/Pattern-Liste (L2), nicht in einen Fuzzy-Score.

**Hand-tuned Weights (0.35/0.25/0.25/0.15):** diese Gewichte wurden für die alte Signal-Struktur (ein Genre-Match, ein FTS-Score, ein Semantic-Score, ein Audience-Score) kalibriert. Mit L3 verändert sich das Semantic-Signal fundamental (max über mehrere Section-Vektoren statt ein Gesamtvektor), und L2 liefert zusätzlich strukturierte Boolean-Signale. Die Gewichte müssen nach Fertigstellung von L2/L3 neu bestimmt werden, ggf. mit gelerntem Ranker statt fixer Konvexkombination.

**Weiterhin aktiv (NICHT archiviert):** MMR-Reranker (λ=0.7, max 3 pro Agentur), Audience-Proximity-Score, FTS via `ts_rank_cd`, Genre-Alias-Matching (Exakt → Alias → Embedding-Fallback), Match-Tags-Berechnung bleiben im aktiven Plan.

---

## Meta-Beobachtungen aus der Umstellung

- **Aufgabentrennung zahlt sich aus:** Die klare Trennung Lesen (L1) / Verifizieren (L1-V) / Kanonisieren (L2) / Einbetten (L3) macht jeden Schritt einzeln testbar und verbessert die Gesamtqualität. Vorher waren diese Aufgaben in einem einzigen Ollama-Call vermischt.
- **Rohtext erhalten, nicht kanonisieren:** Viele Nuancen (Tropes, Conditions, Comp-Titel → Want-Verknüpfungen) gingen in der JSON-Extraktion verloren. Natürliche Sprache ist die bessere Zwischenrepräsentation.
- **Keine Fuzzy-Matches für harte Grenzen:** Hard-Nos, Opt-Out, `is_open` müssen deterministisch entscheiden. Cosine-Ähnlichkeit ist dafür das falsche Werkzeug.
- **Ein Vektor pro Aspekt, nicht pro Agent:** Agenten mit multiplen Preference-Bereichen (Genre × Audience × Aesthetic) lassen sich nicht sinnvoll in einen Vektor mitteln.
