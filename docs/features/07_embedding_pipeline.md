# Feature 07 — Embedding-Pipeline

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul D (8.1–8.4)

## Scope

Embedding-Modell-Abstraktion, Agenten-Embedding (aus gespeichertem Originaltext), Manuskript-Embedding (zweistufig mit Query Expansion), Instruction Prefixes, Gewichtung.

## Dateien

```
embeddings/
├── model.py      # Abstrakte Schnittstelle (austauschbar)
└── pipeline.py   # Embedding-Erstellung & Update
```

---

## Modell: BAAI/bge-large-en-v1.5

- Stärkstes open-source Modell auf MTEB STS
- Asymmetrisches Matching via Instruction Prefix
- 1024 Dimensionen
- Lokal betreibbar, kommerziell nutzbar
- **Fallback:** `intfloat/e5-large-v2`
- **Similarity-Metrik:** Cosine Similarity (`<=>` in pgvector)

**Austauschbarkeit:** Abstrakte Schnittstelle, Modellname in `.env`. Bei Wechsel: `recompute_all_embeddings`-Skript + DB-Migration der Vektordimension.

---

## Das Asymmetrie-Problem

Agenten-Profile: ~100–300 Wörter Originaltext (Wishlist + Bio). Manuskript-Profile: ~800–3000 Wörter Fließtext. Plus Perspektiven-Problem (Autor vs. Agent).

**Lösung:** Drei Maßnahmen gemeinsam:
1. BGE Instruction Prefix (Längen-Asymmetrie)
2. Zweistufiges Manuskript-Embedding (Perspektiven-Problem)
3. Normalisierte Kombination beider Vektoren

---

## Agenten-Embedding

**Instruction Prefix:** `"Represent this literary agent profile for retrieval: This agent is looking for: "`

**Beim Erstcrawl und bei Re-Crawls:** Embedding wird aus dem gespeicherten Originaltext (`wishlist_raw`, `bio_raw`) berechnet — bestmögliche Qualität in beiden Fällen, da Originaltexte jetzt persistent sind.

**Fallback** (Legacy-Profile ohne Originaltext): Embedding aus gespeicherten Keywords rekonstruieren. Keywords doppelt einfügen für höheres Gewicht. Gleicher Instruction-Prefix.

---

## Manuskript-Embedding — Zweistufig

**Embedding 1 — Volltext (einmalig bei Upload):**
Alle Autoren-Inputs zusammengesetzt: Genre, Audience, Ton, Themen, Comp Titles, Query Letter, Kapitel-Ausschnitte.
Prefix: `"Represent this manuscript to find matching literary agents: "`

**Embedding 2 — Query Expansion (beim ersten Matching, dann gecacht):**
Ollama generiert 12 Keywords in Agenten-Sprache aus dem Query Letter. Eingebettet mit **Agenten**-Prefix (nicht Manuskript) → liegt im selben Vektor-Raum wie Agenten-Embeddings. Das ist die Brücke über die Perspektiven-Lücke.

**Finales Embedding:**
```
final = normalize(0.7 * embedding_fulltext + 0.3 * embedding_query_expanded)
```

- Gewichtung 70/30 ist Startwert — nach 100 Matchings empirisch tunen
- Beide Gewichte konfigurierbar in `.env`
- Pro Manuskript in DB gespeichert (für A/B-Testing)
- L2-Normalisierung für korrekte Cosine Similarity
