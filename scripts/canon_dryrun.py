#!/usr/bin/env python3
"""Canon dry-run against the MSWL sample.

Reads ``data/mswl_sample/notes_parsed/*.json`` + ``canon/aliases.yaml``.
For each profile, collects raw terms per facet, normalizes, looks up in the
alias map, and reports coverage + unmapped-term leaderboard with action tags
(alias_candidate / LOCAL_candidate / dismiss) per the decision-flow in
``docs/features/16_l2_canonicalization.md``.

This script supersedes the legacy ``scripts/canon_coverage.py`` for this
validation pass; the old script reads the removed flat columns and is broken
against the current Note-Taker shape.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO / "data" / "mswl_sample" / "notes_parsed"
ALIASES_PATH = REPO / "canon" / "aliases.yaml"
REPORT_PATH = REPO / "data" / "mswl_sample" / "canon_dryrun.md"

# Targets from docs/features/16_l2_canonicalization.md
COVERAGE_TARGETS = {"subject": 0.90, "audience": 0.90, "hard_no": 0.70}
LOCAL_EXTENSION_THRESHOLD = 5  # ≥5 distinct profiles

HARD_NO_BUCKETS = ["content", "format", "trope", "category"]


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def load_aliases() -> dict[str, dict[str, str]]:
    raw = yaml.safe_load(ALIASES_PATH.read_text())["aliases"]
    return {facet: {normalize(k): v for k, v in m.items()} for facet, m in raw.items()}


def load_profiles() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(NOTES_DIR.glob("*.json"))]


def collect_terms(entry: dict) -> dict[str, list[str]]:
    pn = entry.get("profile_notes") or {}
    sections = pn.get("preference_sections") or []
    hard_nos = pn.get("hard_nos") or {}

    subject: list[str] = []
    audience: list[str] = []
    hard_no: list[str] = []

    for s in sections:
        subject.extend(s.get("genres") or [])
        audience.extend(s.get("audience") or [])
        hard_no.extend(s.get("does_not_want") or [])

    for b in HARD_NO_BUCKETS:
        hard_no.extend(hard_nos.get(b) or [])

    return {"subject": subject, "audience": audience, "hard_no": hard_no}


def tag_unmapped(
    norm_term: str,
    profile_count: int,
    facet_aliases: dict[str, str],
) -> str:
    if profile_count >= LOCAL_EXTENSION_THRESHOLD:
        return "LOCAL_candidate"
    # Token-overlap heuristic for alias_candidate: does a canon entry share ≥1 word?
    term_tokens = set(norm_term.split())
    for canon_key in facet_aliases:
        if term_tokens & set(canon_key.split()):
            return "alias_candidate"
    return "dismiss"


def render(
    profiles: list[dict],
    aliases: dict[str, dict[str, str]],
) -> str:
    n = len(profiles)
    lines: list[str] = []
    lines.append(f"# Canon Dry-Run — MSWL Sample ({n} profiles)\n")
    lines.append("First-pass canon validation. Each raw term is normalized and looked up in")
    lines.append("`canon/aliases.yaml`. Unmapped terms are tagged via the decision-flow in")
    lines.append("`docs/features/16_l2_canonicalization.md`.\n")
    lines.append("**Not a v1 lock.** 50 profiles is a first pass; the LOCAL-extension threshold")
    lines.append(f"(≥{LOCAL_EXTENSION_THRESHOLD} profiles) at this sample size biases toward `dismiss`.")
    lines.append("v1 lock still requires ≥200 production profiles via Step 4.\n")

    # Aggregate
    mapped_per_facet: Counter[str] = Counter()
    total_per_facet: Counter[str] = Counter()
    unmapped_profile_sets: dict[str, defaultdict[str, set[str]]] = {
        f: defaultdict(set) for f in COVERAGE_TARGETS
    }

    for entry in profiles:
        slug = entry.get("slug", "?")
        buckets = collect_terms(entry)
        for facet, terms in buckets.items():
            for term in terms:
                if not isinstance(term, str) or not term.strip():
                    continue
                norm = normalize(term)
                total_per_facet[facet] += 1
                if norm in aliases.get(facet, {}):
                    mapped_per_facet[facet] += 1
                else:
                    unmapped_profile_sets[facet][norm].add(slug)

    lines.append("## Coverage per facet\n")
    lines.append("| Facet | Mapped | Total | Coverage | Target | Status |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for facet, target in COVERAGE_TARGETS.items():
        mapped = mapped_per_facet[facet]
        total = total_per_facet[facet]
        pct = mapped / total if total else 0.0
        status_label = "✅ above target" if pct >= target else "⚠️ below target"
        pct_str = f"{pct * 100:.1f}%" if total else "n/a"
        lines.append(f"| {facet} | {mapped} | {total} | {pct_str} | "
                     f"{target * 100:.0f}% | {status_label} |")
    lines.append("")

    # Leaderboards
    for facet in COVERAGE_TARGETS:
        facet_unmapped = unmapped_profile_sets[facet]
        if not facet_unmapped:
            lines.append(f"## {facet.capitalize()} — unmapped terms\n")
            lines.append("_All terms mapped._\n")
            continue

        counts_by_term = [(term, len(slugs)) for term, slugs in facet_unmapped.items()]
        counts_by_term.sort(key=lambda x: (-x[1], x[0]))
        top = counts_by_term[:50]

        local_count = sum(1 for _, c in counts_by_term if c >= LOCAL_EXTENSION_THRESHOLD)
        alias_guess = 0
        for term, count in counts_by_term:
            if count < LOCAL_EXTENSION_THRESHOLD:
                if tag_unmapped(term, count, aliases.get(facet, {})) == "alias_candidate":
                    alias_guess += 1

        lines.append(f"## {facet.capitalize()} — unmapped terms (top 50 of {len(counts_by_term)})\n")
        lines.append(f"- LOCAL-extension candidates (≥{LOCAL_EXTENSION_THRESHOLD} profiles): "
                     f"**{local_count}**")
        lines.append(f"- Alias-candidates (token overlap, <{LOCAL_EXTENSION_THRESHOLD} profiles): "
                     f"**{alias_guess}**")
        lines.append(f"- Dismiss: **{len(counts_by_term) - local_count - alias_guess}**")
        lines.append("")
        lines.append("| Normalized term | Profiles | Action |")
        lines.append("|---|---:|---|")
        for term, count in top:
            action = tag_unmapped(term, count, aliases.get(facet, {}))
            lines.append(f"| `{term}` | {count} | {action} |")
        lines.append("")

    lines.append("## Summary\n")
    any_below = any(
        (mapped_per_facet[f] / total_per_facet[f] if total_per_facet[f] else 0) < t
        for f, t in COVERAGE_TARGETS.items()
    )
    if any_below:
        lines.append("At least one facet is below its v1 target. Review the unmapped-term")
        lines.append("leaderboards, add aliases for clear synonyms, evaluate LOCAL-candidates")
        lines.append("against the decision-flow rules, then rerun.")
    else:
        lines.append("All facets meet or exceed v1 coverage targets on this 50-profile sample.")
        lines.append("This is encouraging but **not** sufficient for v1 lock — the full Step 4")
        lines.append("200-profile run must still run against the same canon version.")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    if not NOTES_DIR.exists():
        sys.exit(f"No {NOTES_DIR} — run scripts/harvest_mswl_sample.py first.")
    profiles = load_profiles()
    if not profiles:
        sys.exit(f"No parsed profiles under {NOTES_DIR}")
    aliases = load_aliases()
    REPORT_PATH.write_text(render(profiles, aliases), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
