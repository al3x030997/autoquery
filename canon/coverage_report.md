# Canon coverage report — canon v0.1

**Status: not yet generated.** The script ran but extraction was skipped — no
`ANTHROPIC_API_KEY` available in the environment when the canon was initialised.

## How to generate this report

```bash
cd /Users/alex/autoquery
export ANTHROPIC_API_KEY=...        # your key
export DATABASE_URL=sqlite:///tmp.db  # stub — the script does no DB writes
python scripts/canon_coverage.py
```

This extracts L1 output for the 7 cleaned benchmark profiles under
`batch_capture_output/cleaned/`, caches results to `canon/_cache/`, and
rewrites this file with:

- Overall coverage % per facet (subject / audience / hard_no).
- Unmapped raw terms, aggregated across profiles with source counts.
- Per-profile breakdown of every raw term and its canonical code.

## Expected dry-run signal (v0)

With 7 profiles the coverage numbers are indicative, not conclusive. The real
canon-v1 lock happens after Step 4 (≥200 profiles). For v0, the useful
outputs are:

1. **Which alias gaps the 7 benchmark profiles expose.** Add obvious ones to
   `aliases.yaml` and re-run; do NOT promote anything to `extensions.yaml` at
   this stage (the ≥5-profile rule cannot be established with 7 profiles).
2. **Which hard-no tags get zero hits.** These are candidates for removal in
   v1, but keep seeded entries for now.
3. **Discriminability**: profiles with distinct focus (e.g. `brent_taylor`
   covers PB/MG/YA/Adult across genres) should yield disjoint Thema-code sets.
   Collapse onto a single code indicates under-granular aliases.

After running, commit this file as the v0 audit baseline.
