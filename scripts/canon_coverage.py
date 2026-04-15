#!/usr/bin/env python3
"""Dry-run coverage validator for the L2 canon.

For each cleaned benchmark profile, runs L1 extraction (cached), then checks
what fraction of raw subject / audience / hard-no phrases the current
canon/aliases.yaml resolves. Writes canon/coverage_report.md.

Extraction results are cached under canon/_cache/{profile}.json so the script
is cheap to rerun after editing aliases.yaml. Pass --refresh to re-extract.

Usage:
    python scripts/canon_coverage.py              # use cache if present
    python scripts/canon_coverage.py --refresh    # re-run extraction
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from autoquery.extractor.profile_extractor import ProfileExtractor  # noqa: E402

CANON_DIR = REPO / "canon"
CLEANED_DIR = REPO / "batch_capture_output" / "cleaned"
CACHE_DIR = CANON_DIR / "_cache"
REPORT_PATH = CANON_DIR / "coverage_report.md"

FACET_FIELDS = {
    "subject": "genres",
    "audience": "audience",
    "hard_no": "hard_nos_keywords",
}


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def load_aliases() -> dict[str, dict[str, str]]:
    raw = yaml.safe_load((CANON_DIR / "aliases.yaml").read_text())["aliases"]
    return {facet: {normalize(k): v for k, v in m.items()} for facet, m in raw.items()}


def load_canon_version() -> str:
    return (CANON_DIR / "VERSION").read_text().strip()


async def extract_one(extractor: ProfileExtractor, profile_path: Path) -> dict:
    cache_path = CACHE_DIR / f"{profile_path.stem}.json"
    text = profile_path.read_text()
    result = await extractor._call_llm(text)  # noqa: SLF001 — intentional reuse, no DB writes
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return result


async def get_extractions(refresh: bool) -> dict[str, dict]:
    profiles = sorted(CLEANED_DIR.glob("*.txt"))
    if not profiles:
        sys.exit(f"No cleaned profiles under {CLEANED_DIR}")

    extractions: dict[str, dict] = {}
    to_extract: list[Path] = []
    for p in profiles:
        cache_path = CACHE_DIR / f"{p.stem}.json"
        if cache_path.exists() and not refresh:
            extractions[p.stem] = json.loads(cache_path.read_text())
        else:
            to_extract.append(p)

    if to_extract:
        print(f"Extracting {len(to_extract)} profile(s) via Claude — this will hit the API.")
        extractor = ProfileExtractor()
        for p in to_extract:
            print(f"  {p.stem} ...", end=" ", flush=True)
            try:
                extractions[p.stem] = await extract_one(extractor, p)
                print("ok")
            except Exception as exc:
                print(f"FAILED: {exc}")
    return extractions


def classify_terms(
    extraction: dict, aliases: dict[str, dict[str, str]]
) -> dict[str, list[tuple[str, str | None]]]:
    out: dict[str, list[tuple[str, str | None]]] = {}
    for facet, field in FACET_FIELDS.items():
        raw_terms = extraction.get(field) or []
        if not isinstance(raw_terms, list):
            raw_terms = [raw_terms]
        mapped: list[tuple[str, str | None]] = []
        for term in raw_terms:
            if not isinstance(term, str) or not term.strip():
                continue
            code = aliases[facet].get(normalize(term))
            mapped.append((term, code))
        out[facet] = mapped
    return out


def build_report(
    extractions: dict[str, dict],
    classifications: dict[str, dict[str, list[tuple[str, str | None]]]],
    canon_version: str,
) -> str:
    lines: list[str] = []
    lines.append(f"# Canon coverage report — canon {canon_version}")
    lines.append("")
    lines.append(
        f"Generated against {len(extractions)} cleaned profile(s) under "
        f"`batch_capture_output/cleaned/`. Extraction output cached under "
        f"`canon/_cache/`."
    )
    lines.append("")

    # Overall coverage
    lines.append("## Overall coverage")
    lines.append("")
    lines.append("| Facet | Mapped | Total | Coverage |")
    lines.append("|---|---:|---:|---:|")
    totals: dict[str, tuple[int, int]] = {}
    for facet in FACET_FIELDS:
        mapped = 0
        total = 0
        for prof_name in classifications:
            for _term, code in classifications[prof_name][facet]:
                total += 1
                if code is not None:
                    mapped += 1
        totals[facet] = (mapped, total)
        pct = f"{(mapped / total * 100):.1f}%" if total else "n/a"
        lines.append(f"| {facet} | {mapped} | {total} | {pct} |")
    lines.append("")

    # Unmapped terms aggregated
    lines.append("## Unmapped raw terms")
    lines.append("")
    for facet in FACET_FIELDS:
        counter: Counter[str] = Counter()
        sources: defaultdict[str, set[str]] = defaultdict(set)
        for prof_name, facets in classifications.items():
            for term, code in facets[facet]:
                if code is None:
                    key = normalize(term)
                    counter[key] += 1
                    sources[key].add(prof_name)
        lines.append(f"### {facet}")
        if not counter:
            lines.append("_All terms mapped._")
            lines.append("")
            continue
        lines.append("| Normalized term | Count | Profiles |")
        lines.append("|---|---:|---|")
        for term, cnt in counter.most_common():
            lines.append(f"| `{term}` | {cnt} | {', '.join(sorted(sources[term]))} |")
        lines.append("")

    # Per-profile breakdown
    lines.append("## Per-profile breakdown")
    lines.append("")
    for prof_name in sorted(classifications):
        lines.append(f"### {prof_name}")
        lines.append("")
        for facet in FACET_FIELDS:
            mapped_list = classifications[prof_name][facet]
            if not mapped_list:
                continue
            lines.append(f"**{facet}**")
            lines.append("")
            for term, code in mapped_list:
                marker = f"→ `{code}`" if code else "→ _(unmapped)_"
                lines.append(f"- `{term}` {marker}")
            lines.append("")
    return "\n".join(lines) + "\n"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Re-run extraction, ignoring cache")
    args = parser.parse_args()

    aliases = load_aliases()
    canon_version = load_canon_version()
    extractions = await get_extractions(refresh=args.refresh)
    classifications = {
        name: classify_terms(extraction, aliases) for name, extraction in extractions.items()
    }
    report = build_report(extractions, classifications, canon_version)
    REPORT_PATH.write_text(report)
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
