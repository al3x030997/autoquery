# Feature 08 — Matching-Algorithmus (Phase 1)

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul E (9.1–9.5), Modul G (11.1–11.3)

## Scope

4-Schichten-Pipeline: Filter → Scoring → MMR → Erklärbarkeit. Abstrakte Scorer-Schnittstelle für Phase-Upgrade.

## Dateien

```
matching/phase1/
├── filter.py          # Schicht 1: Harte Constraints
├── scorer.py          # Schicht 2: Konvexkombination
├── reranker.py        # Schicht 3: MMR
└── query_expander.py  # Query Expansion via Ollama
```

---

## Architektur-Anforderung

Abstrakte Schnittstelle: `score_candidates(manuscript, candidates) → list[ScoredAgent]`
Bleibt in Phase 2 und 3 identisch — nur Implementierung wird ausgetauscht.

---

## Schicht 1 — Harte Constraints (Filter)

Ausschluss wenn:
- `is_open = FALSE`
- `opted_out = TRUE`
- `review_status != 'approved'`
- Hard-Nos-Match: Manuskript-Embedding vs. Hard-Nos-Keywords-Embedding > Schwellenwert 0.75

Hard-Nos-Threshold 0.75 ist Startwert — nach ersten Reviews validieren.

---

## Schicht 2 — Hybrid Scoring via Gewichteter Konvexkombination

```
final_score = w₁·norm(genre) + w₂·norm(audience) + w₃·norm(fts) + w₄·norm(semantic)
```

**Initiale Gewichte:** w₁=0.35, w₂=0.15, w₃=0.25, w₄=0.25 (in `.env`, Summe = 1.0)

**Normalisierung (DBSF):** `norm(x) = clip((x - μ) / σ, 0, 1)`. μ und σ beim Server-Start aus aktuellen Agenten-Scores berechnen, cachen, bei >10% neuen Profilen neu berechnen.

**Warum nicht RRF:** RRF verwirft Score-Magnituden durch Rang-Konvertierung. Bei vollständig berechenbaren Scores (500–5000 Items) ist das unnötiger Informationsverlust. CC übertrifft RRF (Bruch et al. 2023, ACM TOIS). ~20 gelabelte Matches reichen für optimale Gewichte (Sun et al. 2025).

**Tuning:** Initial manuell via Expert Review. Ab ~50 gelabelten Matches per Grid Search optimieren. Gewichte in `algorithm_version` versionieren.

**Fallback:** Signal nicht berechenbar → Gewicht proportional auf verbleibende verteilen.

### Signal A — Genre-Match-Score
Exakter Match = 1.0, Alias-Match = 0.85, semantischer Match via Embedding = bis 0.7.

**Genre-Alias-Tabelle** (`matching/genre_aliases.yaml`): Kanonische Namen + Aliasse. Beim Server-Start laden. Min. 30 Einträge vor Launch. Beide Seiten normalisieren, erst bei Nicht-Match → Embedding-Fallback.

### Signal B — Audience-Proximity-Score
Children's → Middle Grade → YA → Adult. Exakt = 1.0, 1 Stufe = 0.6, 2 = 0.3, 3 = 0.1.

### Signal C — Full-Text-Search (ts_rank_cd)
PostgreSQL FTS auf `fts_vector`. Query aus: Genre + Themen + Comp Titles + Query-Expansion-Keywords. `ts_rank_cd` (Cover Density) statt `ts_rank`.

### Signal D — Semantische Cosine Similarity
Finales Manuskript-Embedding vs. Agenten-Embedding. Erfasst semantische Nähe ohne exakte Keywords.

---

## Schicht 3 — MMR Re-Ranking

Maximal Marginal Relevance. λ=0.7 (konfigurierbar in `.env`).
- Input: Top-50 nach Scoring
- Output: Top-20 (eingeloggt), Top-3 (nicht eingeloggt)
- **Hartes Strukturlimit:** Max. 3 Agenten derselben Agentur in Top-10

**Post-MVP:** DPP (Chen et al. 2018, NeurIPS) + Calibration (Steck 2018, RecSys) als Upgrade.

---

## Schicht 4 — Erklärbarkeit

**Match-Tags** (serverseitig berechnet): Genre (✓/~/✗), Themen (Keyword-Overlap), Audience (Proximity).

**Snippet:** Kein Originalzitat. Maschinell generiert aus Keywords: z.B. "Sucht: Cozy Fantasy · Character-driven · Queer Protagonists"

**LLM-Erklärung:** Optional, auf Klick, gecacht pro (manuscript_id, agent_id). Generiert aus Keywords + Genres + Manuskript-Profil — nie aus Originaltext.

---

## Qualitätskriterien

| Kriterium | Ziel | Typ |
|---|---|---|
| Precision@10 | > 0.7 | Soft |
| Hard-Nos Violation Rate | **0%** | **Hard** |
| Semantische Tiefe (mit vs. ohne Query Expansion) | +15% | Soft |
| Intra-List Diversity | > 0.4 | Soft |
| Max. Agenten pro Agentur in Top-10 | **≤ 3** | **Hard** |
| Expert Review Score | ≥ 4/5 | Soft |

**Messung vor Launch:** Bekannte Agent-Autor-Beziehungen rückwärts testen. 1–2 Branchenkenner bewerten 20–30 Matchings.
