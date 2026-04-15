#!/usr/bin/env python3
"""Describe the shape of the MSWL sample.

Reads ``data/mswl_sample/notes_parsed/*.json`` and writes:
  - ``data/mswl_sample/analysis.md`` — prose report
  - ``data/mswl_sample/analysis.csv`` — one row per profile, columns for each metric

Purely descriptive. No canon lookups (that's scripts/canon_dryrun.py).
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "mswl_sample"
NOTES_DIR = OUT / "notes_parsed"
REPORT_MD = OUT / "analysis.md"
REPORT_CSV = OUT / "analysis.csv"

IDENTITY_FIELDS = [
    "name", "organization", "role", "pronouns",
    "email", "submission_portal", "availability",
]
HARD_NO_BUCKETS = ["content", "format", "trope", "category"]


def load_profiles() -> list[dict]:
    files = sorted(NOTES_DIR.glob("*.json"))
    return [json.loads(p.read_text()) for p in files]


def classify_section(sec: dict) -> str:
    has_aud = bool(sec.get("audience"))
    has_gen = bool(sec.get("genres"))
    if has_aud and has_gen:
        return "hybrid"
    if has_aud:
        return "audience-based"
    if has_gen:
        return "genre-based"
    return "other"


def per_profile_metrics(entry: dict) -> dict:
    pn = entry.get("profile_notes", {}) or {}
    identity = pn.get("identity") or {}
    sections = pn.get("preference_sections") or []
    hard_nos = pn.get("hard_nos") or {}
    submission = pn.get("submission") or []
    comps = pn.get("comp_titles_high_priority") or []
    flags = pn.get("confidence_flags") or {}

    identity_filled = [f for f in IDENTITY_FIELDS if identity.get(f)]
    section_types = [classify_section(s) for s in sections]

    anomalies = []
    if not sections:
        anomalies.append("zero_sections")
    if not identity.get("name"):
        anomalies.append("missing_name")
    if not any(hard_nos.get(b) for b in HARD_NO_BUCKETS):
        anomalies.append("no_hard_nos")

    return {
        "slug": entry.get("slug", ""),
        "url": entry.get("url", ""),
        "section_count": len(sections),
        "section_types": "|".join(section_types) or "",
        "identity_fields_filled": "|".join(identity_filled),
        "identity_fields_filled_count": len(identity_filled),
        "hard_no_content": len(hard_nos.get("content") or []),
        "hard_no_format": len(hard_nos.get("format") or []),
        "hard_no_trope": len(hard_nos.get("trope") or []),
        "hard_no_category": len(hard_nos.get("category") or []),
        "inferred_count": len(flags.get("inferred") or []),
        "nuanced_count": len(flags.get("nuanced") or []),
        "missing_count": len(flags.get("missing") or []),
        "comp_title_count": len(comps)
            + sum(len(s.get("comp_titles") or []) for s in sections),
        "has_submission_req": "true" if submission else "false",
        "anomaly_flags": "|".join(anomalies),
    }


def top_terms(profiles: list[dict], facet_getter) -> list[tuple[str, int]]:
    c: Counter[str] = Counter()
    for p in profiles:
        terms = facet_getter(p)
        for t in {t.strip().lower() for t in terms if isinstance(t, str) and t.strip()}:
            c[t] += 1
    return c.most_common(20)


def collect_genres(entry: dict) -> list[str]:
    sections = (entry.get("profile_notes") or {}).get("preference_sections") or []
    out: list[str] = []
    for s in sections:
        out.extend(s.get("genres") or [])
    return out


def collect_audience(entry: dict) -> list[str]:
    sections = (entry.get("profile_notes") or {}).get("preference_sections") or []
    out: list[str] = []
    for s in sections:
        out.extend(s.get("audience") or [])
    return out


def collect_does_not_want(entry: dict) -> list[str]:
    sections = (entry.get("profile_notes") or {}).get("preference_sections") or []
    out: list[str] = []
    for s in sections:
        out.extend(s.get("does_not_want") or [])
    return out


def collect_hard_nos(entry: dict) -> list[str]:
    hard = (entry.get("profile_notes") or {}).get("hard_nos") or {}
    out: list[str] = []
    for b in HARD_NO_BUCKETS:
        out.extend(hard.get(b) or [])
    return out


def render_report(profiles: list[dict], rows: list[dict]) -> str:
    n = len(profiles)
    section_counts = [r["section_count"] for r in rows]
    filled_counts = [r["identity_fields_filled_count"] for r in rows]

    def stat(line: list[int], label: str) -> str:
        if not line:
            return f"- {label}: n/a"
        return (
            f"- {label}: min {min(line)}, median {statistics.median(line):.1f}, "
            f"mean {statistics.mean(line):.1f}, max {max(line)}"
        )

    section_type_counter: Counter[str] = Counter()
    for r in rows:
        for t in r["section_types"].split("|"):
            if t:
                section_type_counter[t] += 1

    identity_fill_pct = {
        f: sum(1 for r in rows if f in r["identity_fields_filled"].split("|")) * 100 / max(n, 1)
        for f in IDENTITY_FIELDS
    }

    hard_no_fill_pct = {
        b: sum(1 for r in rows if r[f"hard_no_{b}"] > 0) * 100 / max(n, 1)
        for b in HARD_NO_BUCKETS
    }

    submission_set = sum(1 for r in rows if r["has_submission_req"] == "true")

    flag_means = {
        "inferred": statistics.mean([r["inferred_count"] for r in rows]) if rows else 0,
        "nuanced": statistics.mean([r["nuanced_count"] for r in rows]) if rows else 0,
        "missing": statistics.mean([r["missing_count"] for r in rows]) if rows else 0,
    }

    comp_counts = [r["comp_title_count"] for r in rows]
    comps_listing = sum(1 for c in comp_counts if c > 0)

    anomalies_counter: Counter[str] = Counter()
    for r in rows:
        for a in r["anomaly_flags"].split("|"):
            if a:
                anomalies_counter[a] += 1

    lines: list[str] = []
    lines.append(f"# MSWL Sample — Shape Analysis ({n} profiles)\n")
    lines.append("Describes what 50 real MSWL agent profiles look like after passing through")
    lines.append("the L0→L1 Note-Taker pipeline. Not a canon-coverage report — see")
    lines.append("`canon_dryrun.md` for that.\n")

    lines.append("## Structure\n")
    lines.append(stat(section_counts, "Preference sections per profile"))
    lines.append("")
    lines.append("Section type mix (across all sections in the sample):")
    total_sections = sum(section_type_counter.values()) or 1
    for t, c in section_type_counter.most_common():
        lines.append(f"- {t}: {c} ({c * 100 / total_sections:.0f}%)")
    lines.append("")

    lines.append("## Identity completeness\n")
    lines.append(stat(filled_counts, "Identity fields populated per profile"))
    lines.append("")
    lines.append("| Field | Populated in |")
    lines.append("|---|---|")
    for f, pct in identity_fill_pct.items():
        lines.append(f"| {f} | {pct:.0f}% |")
    lines.append("")

    lines.append("## Hard-no buckets\n")
    lines.append("| Bucket | Non-empty in |")
    lines.append("|---|---|")
    for b, pct in hard_no_fill_pct.items():
        lines.append(f"| {b} | {pct:.0f}% |")
    lines.append("")

    lines.append("## Submission requirements\n")
    lines.append(f"- {submission_set}/{n} profiles ({submission_set * 100 / max(n, 1):.0f}%) "
                 "have at least one submission-requirements entry.")
    lines.append("")

    lines.append("## Confidence flag density (Note-Taker self-signals)\n")
    lines.append(f"- mean INFERRED per profile: {flag_means['inferred']:.2f}")
    lines.append(f"- mean NUANCED per profile: {flag_means['nuanced']:.2f}")
    lines.append(f"- mean MISSING per profile: {flag_means['missing']:.2f}")
    lines.append("")

    lines.append("## Comp titles\n")
    lines.append(f"- {comps_listing}/{n} profiles list at least one comp title.")
    lines.append(stat(comp_counts, "Comp titles per profile"))
    lines.append("")

    def render_top(heading: str, terms: list[tuple[str, int]]) -> None:
        lines.append(f"### {heading}\n")
        if not terms:
            lines.append("_none_\n")
            return
        lines.append("| Raw term | Profiles |")
        lines.append("|---|---:|")
        for t, c in terms:
            lines.append(f"| `{t}` | {c} |")
        lines.append("")

    lines.append("## Vocabulary (top 20 raw terms per facet)\n")
    render_top("Genres", top_terms(profiles, collect_genres))
    render_top("Audience", top_terms(profiles, collect_audience))
    render_top("Does not want (per-section)", top_terms(profiles, collect_does_not_want))
    render_top("Hard nos (all buckets)", top_terms(profiles, collect_hard_nos))

    lines.append("## Anomalies\n")
    if anomalies_counter:
        for a, c in anomalies_counter.most_common():
            lines.append(f"- `{a}`: {c} profiles")
    else:
        lines.append("_none flagged_")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    if not NOTES_DIR.exists():
        sys.exit(f"No notes_parsed dir at {NOTES_DIR} — run harvest first.")
    profiles = load_profiles()
    if not profiles:
        sys.exit(f"No parsed profiles under {NOTES_DIR}")

    rows = [per_profile_metrics(p) for p in profiles]

    fieldnames = [
        "slug", "url", "section_count", "section_types",
        "identity_fields_filled", "identity_fields_filled_count",
        "hard_no_content", "hard_no_format", "hard_no_trope", "hard_no_category",
        "inferred_count", "nuanced_count", "missing_count",
        "comp_title_count", "has_submission_req", "anomaly_flags",
    ]
    with REPORT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    REPORT_MD.write_text(render_report(profiles, rows), encoding="utf-8")
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_CSV}")


if __name__ == "__main__":
    main()
