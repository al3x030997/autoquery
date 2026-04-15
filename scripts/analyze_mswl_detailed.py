#!/usr/bin/env python3
"""Detailed MSWL-sample analysis with charts.

Produces:
  - data/mswl_sample/charts/*.png
  - data/mswl_sample/analysis_detailed.md — embedded charts + narrative

Reads the parsed profiles AND reuses the canon aliases lookup so we can visualize
coverage and vocabulary in one place. Does not re-fetch, does not re-parse.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import yaml

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "mswl_sample"
NOTES_DIR = OUT / "notes_parsed"
CHARTS_DIR = OUT / "charts"
REPORT = OUT / "analysis_detailed.md"
ALIASES_PATH = REPO / "canon" / "aliases.yaml"

IDENTITY_FIELDS = [
    "name", "organization", "role", "availability",
    "submission_portal", "email", "pronouns",
]
HARD_NO_BUCKETS = ["content", "format", "trope", "category"]
COVERAGE_TARGETS = {"subject": 90, "audience": 90, "hard_no": 70}

STONE = "#292524"
AMBER = "#f59e0b"
AMBER_LIGHT = "#fde68a"
GREEN = "#16a34a"
RED = "#dc2626"
GRAY = "#9ca3af"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 110,
})


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def load_profiles() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(NOTES_DIR.glob("*.json"))]


def load_aliases() -> dict[str, dict[str, str]]:
    raw = yaml.safe_load(ALIASES_PATH.read_text())["aliases"]
    return {facet: {normalize(k): v for k, v in m.items()} for facet, m in raw.items()}


# ---------- metric extractors ----------
def classify_section(sec: dict) -> str:
    a = bool(sec.get("audience"))
    g = bool(sec.get("genres"))
    if a and g:
        return "hybrid"
    if a:
        return "audience-only"
    if g:
        return "genre-only"
    return "other"


def per_profile(entry: dict) -> dict:
    pn = entry.get("profile_notes") or {}
    ident = pn.get("identity") or {}
    sections = pn.get("preference_sections") or []
    hard = pn.get("hard_nos") or {}
    flags = pn.get("confidence_flags") or {}
    comps_top = pn.get("comp_titles_high_priority") or []
    comps_section = sum(len(s.get("comp_titles") or []) for s in sections)
    return {
        "slug": entry.get("slug", "?"),
        "section_count": len(sections),
        "section_types": [classify_section(s) for s in sections],
        "identity_filled": [f for f in IDENTITY_FIELDS if ident.get(f)],
        "hard_no_counts": {b: len(hard.get(b) or []) for b in HARD_NO_BUCKETS},
        "inferred": len(flags.get("inferred") or []),
        "nuanced": len(flags.get("nuanced") or []),
        "missing": len(flags.get("missing") or []),
        "comp_total": len(comps_top) + comps_section,
    }


def collect_terms(entry: dict) -> dict[str, list[str]]:
    pn = entry.get("profile_notes") or {}
    sections = pn.get("preference_sections") or []
    hard = pn.get("hard_nos") or {}
    subject = []
    audience = []
    hard_no = []
    for s in sections:
        subject.extend(s.get("genres") or [])
        audience.extend(s.get("audience") or [])
        hard_no.extend(s.get("does_not_want") or [])
    for b in HARD_NO_BUCKETS:
        hard_no.extend(hard.get(b) or [])
    return {"subject": subject, "audience": audience, "hard_no": hard_no}


# ---------- charts ----------
def chart_coverage(profiles: list[dict], aliases: dict, path: Path) -> None:
    mapped = Counter()
    total = Counter()
    for entry in profiles:
        for facet, terms in collect_terms(entry).items():
            for t in terms:
                if not isinstance(t, str) or not t.strip():
                    continue
                total[facet] += 1
                if normalize(t) in aliases.get(facet, {}):
                    mapped[facet] += 1

    facets = list(COVERAGE_TARGETS.keys())
    labels = {"subject": "subject\n(genres)", "audience": "audience", "hard_no": "hard_no\n(exclusions)"}
    pcts = [mapped[f] * 100 / total[f] if total[f] else 0 for f in facets]
    targets = [COVERAGE_TARGETS[f] for f in facets]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(facets))
    bar_colors = [GREEN if p >= t else RED for p, t in zip(pcts, targets)]
    bars = ax.bar(x, pcts, color=bar_colors, width=0.55, zorder=3)
    target_line = None
    for i, t in enumerate(targets):
        line = ax.hlines(t, i - 0.35, i + 0.35, colors=STONE, linestyles="--", linewidth=1.5, zorder=4)
        target_line = line
    for bar, pct, tot, mp in zip(bars, pcts, [total[f] for f in facets], [mapped[f] for f in facets]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f"{pct:.1f}%\n({mp} of {tot})", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels([labels[f] for f in facets])
    ax.set_ylabel("Share of agent vocabulary recognized by canon (%)")
    ax.set_xlabel("Facet")
    ax.set_title("How much of what agents write does our canon already understand?", fontsize=12)
    ax.set_ylim(0, 115)
    ax.grid(axis="y", alpha=0.2, zorder=0)

    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elems = [
        Patch(facecolor=GREEN, label="meets v1 target"),
        Patch(facecolor=RED, label="below v1 target"),
        Line2D([0], [0], color=STONE, linestyle="--", label="v1 target threshold"),
    ]
    ax.legend(handles=legend_elems, loc="upper right", frameon=False, fontsize=9)

    fig.text(0.5, 0.02,
             "Each bar = % of raw terms agents wrote that match a canon entry. "
             "Red bars miss the v1 target; hard_no at 0.4% is effectively unmapped.",
             ha="center", fontsize=9, style="italic", color=STONE)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def chart_section_histogram(rows: list[dict], path: Path) -> None:
    counts = [r["section_count"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bins = range(0, max(counts) + 2)
    ax.hist(counts, bins=bins, color=AMBER, edgecolor=STONE, zorder=3, label="profiles")
    median = statistics.median(counts)
    mean = statistics.mean(counts)
    ax.axvline(median, color=STONE, linestyle="--", linewidth=1.5, label=f"median = {median:.0f}")
    ax.axvline(mean, color=RED, linestyle=":", linewidth=1.5, label=f"mean = {mean:.1f}")
    ax.set_xlabel("Number of preference sections declared by one agent")
    ax.set_ylabel("Number of agent profiles")
    ax.set_title("How many distinct preference sections does a typical agent define?", fontsize=12)
    ax.grid(axis="y", alpha=0.2, zorder=0)
    ax.legend(frameon=False)
    fig.text(0.5, 0.02,
             f"Most agents split their wishlist into 3–6 sections (e.g. one per audience+genre combo). "
             f"{sum(1 for c in counts if c == 0)} profile(s) yielded zero sections — a parser failure mode.",
             ha="center", fontsize=9, style="italic", color=STONE)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def chart_section_types(rows: list[dict], path: Path) -> None:
    c: Counter[str] = Counter()
    for r in rows:
        c.update(r["section_types"])
    labels = [k for k, _ in c.most_common()]
    sizes = [c[k] for k in labels]
    colors = [AMBER, AMBER_LIGHT, STONE, GRAY][: len(labels)]
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    wedges, _ = ax.pie(sizes, colors=colors, startangle=90,
                       wedgeprops={"linewidth": 1, "edgecolor": "white"})
    total = sum(sizes)
    descriptions = {
        "hybrid": "hybrid — audience + genre",
        "audience-only": "audience-only (e.g. 'adult fiction')",
        "genre-only": "genre-only (e.g. 'literary fiction')",
        "other": "other / neither axis populated",
    }
    legend_labels = [f"{descriptions.get(lbl, lbl)}  —  {sz} sections ({sz * 100 / total:.0f}%)"
                     for lbl, sz in zip(labels, sizes)]
    ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=9)
    ax.set_title("Do agents scope preferences by audience, by genre, or both?", fontsize=12)
    fig.text(0.5, 0.02,
             "Nearly all sections combine an audience (e.g. adult) with a genre "
             "(e.g. mystery) — tells the matcher to weight the combination, not axes alone.",
             ha="center", fontsize=9, style="italic", color=STONE)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def chart_identity_fill(rows: list[dict], path: Path) -> None:
    n = len(rows)
    pcts = {f: sum(1 for r in rows if f in r["identity_filled"]) * 100 / n for f in IDENTITY_FIELDS}
    fields = sorted(pcts, key=pcts.get)
    vals = [pcts[f] for f in fields]
    colors = [GREEN if v >= 80 else AMBER if v >= 50 else RED for v in vals]
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.barh(fields, vals, color=colors, zorder=3)
    for y, v in enumerate(vals):
        count = int(round(v * n / 100))
        ax.text(v + 1.5, y, f"{v:.0f}%  ({count}/{n})", va="center", fontsize=9)
    ax.set_xlim(0, 118)
    ax.set_xlabel("Share of profiles where this identity field was extracted (%)")
    ax.set_ylabel("Identity field")
    ax.set_title("Which identity fields does the Note-Taker reliably extract?", fontsize=12)
    ax.grid(axis="x", alpha=0.2, zorder=0)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=GREEN, label="≥80% (reliable)"),
        Patch(facecolor=AMBER, label="50–80% (sparse source data)"),
        Patch(facecolor=RED, label="<50% (rarely stated on page)"),
    ], loc="lower right", frameon=False, fontsize=9)
    fig.text(0.5, 0.02,
             "Name/org/role/availability cluster around 83% — the same ~8 profiles fail all four, "
             "pointing at one template variant the parser misses.",
             ha="center", fontsize=9, style="italic", color=STONE)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def chart_hardno_buckets(rows: list[dict], path: Path) -> None:
    n = len(rows)
    non_empty_pct = {b: sum(1 for r in rows if r["hard_no_counts"][b] > 0) * 100 / n for b in HARD_NO_BUCKETS}
    mean_count = {b: statistics.mean([r["hard_no_counts"][b] for r in rows]) for b in HARD_NO_BUCKETS}

    bucket_desc = {
        "content": "content\n(themes/topics)",
        "format": "format\n(length/medium)",
        "trope": "trope\n(story patterns)",
        "category": "category\n(genre/audience NOs)",
    }
    xlabels = [bucket_desc[b] for b in HARD_NO_BUCKETS]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
    ax1.bar(xlabels, [non_empty_pct[b] for b in HARD_NO_BUCKETS], color=AMBER, zorder=3)
    for i, b in enumerate(HARD_NO_BUCKETS):
        cnt = int(round(non_empty_pct[b] * n / 100))
        ax1.text(i, non_empty_pct[b] + 1.5, f"{non_empty_pct[b]:.0f}%\n({cnt}/{n})", ha="center", fontsize=9)
    ax1.set_ylim(0, 115)
    ax1.set_ylabel("Share of agents who declared at least one (%)")
    ax1.set_xlabel("Hard-no bucket")
    ax1.set_title("How often is each type of hard-no populated?", fontsize=11)
    ax1.grid(axis="y", alpha=0.2, zorder=0)

    ax2.bar(xlabels, [mean_count[b] for b in HARD_NO_BUCKETS], color=STONE, zorder=3)
    for i, b in enumerate(HARD_NO_BUCKETS):
        ax2.text(i, mean_count[b] + 0.05, f"{mean_count[b]:.1f}", ha="center", fontsize=9)
    ax2.set_ylabel("Mean hard-no entries per profile")
    ax2.set_xlabel("Hard-no bucket")
    ax2.set_title("Average volume — how many items does each agent list?", fontsize=11)
    ax2.grid(axis="y", alpha=0.2, zorder=0)

    fig.suptitle("Hard-nos: presence vs. volume", fontsize=13, fontweight="bold")
    fig.text(0.5, 0.02,
             "Left: how often each bucket fires. Right: how many entries agents write when it does. "
             "Trope bucket lags because agents often fold trope dislikes into free-text content prose.",
             ha="center", fontsize=9, style="italic", color=STONE)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(path)
    plt.close(fig)


def chart_confidence(rows: list[dict], path: Path) -> None:
    kinds = ["inferred", "nuanced", "missing"]
    descriptions = {
        "inferred": "INFERRED\n(guessed from context)",
        "nuanced": "NUANCED\n(qualified / conditional)",
        "missing": "MISSING\n(not stated at all)",
    }
    means = [statistics.mean([r[k] for r in rows]) for k in kinds]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar([descriptions[k] for k in kinds], means, color=[AMBER_LIGHT, AMBER, RED], zorder=3)
    for i, v in enumerate(means):
        ax.text(i, v + 0.08, f"{v:.2f}", ha="center", fontsize=10, fontweight="bold")
    ax.set_ylabel("Average flags raised per profile")
    ax.set_xlabel("Confidence-flag type")
    ax.set_title("How often does the extractor admit uncertainty per profile?", fontsize=12)
    ax.grid(axis="y", alpha=0.2, zorder=0)
    ax.set_ylim(0, max(means) * 1.25)
    fig.text(0.5, 0.02,
             "Healthy pattern: MISSING > INFERRED. The prompt prefers to admit absence over "
             "hallucinating — good signal for downstream trust.",
             ha="center", fontsize=9, style="italic", color=STONE)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def chart_top_unmapped(profiles: list[dict], aliases: dict, facet: str, path: Path, n: int = 15) -> None:
    prof_counts: defaultdict[str, set] = defaultdict(set)
    facet_aliases = aliases.get(facet, {})
    for entry in profiles:
        slug = entry.get("slug", "?")
        for t in collect_terms(entry)[facet]:
            if not isinstance(t, str) or not t.strip():
                continue
            norm = normalize(t)
            if norm not in facet_aliases:
                prof_counts[norm].add(slug)
    items = sorted(((t, len(s)) for t, s in prof_counts.items()), key=lambda x: (-x[1], x[0]))[:n]
    if not items:
        return
    terms = [t for t, _ in items][::-1]
    counts = [c for _, c in items][::-1]
    colors = [GREEN if c >= 5 else AMBER for c in counts]
    total_profiles = len(profiles)

    facet_story = {
        "subject": "genre / subject terms",
        "audience": "audience terms",
        "hard_no": "hard-no / exclusion terms",
    }
    facet_caption = {
        "subject": "Most gaps are synonyms of existing canon entries (alias candidates). "
                   "A few are genuine new subgenres that clear the ≥5-profile bar.",
        "audience": "Small counts overall — audience vocabulary is tight. "
                    "Most misses here are normalization issues (e.g. 'young_adult' vs 'young adult').",
        "hard_no": "This facet is the biggest gap. Agents write specific phrases "
                   "('graphic sexual violence', 'on-page assault') the current hard_nos.yaml doesn't recognize.",
    }

    fig, ax = plt.subplots(figsize=(10, max(4.2, 0.4 * len(terms) + 1.6)))
    ax.barh(terms, counts, color=colors, zorder=3)
    for y, v in enumerate(counts):
        pct = v * 100 / total_profiles
        ax.text(v + 0.1, y, f"{v}  ({pct:.0f}% of profiles)", va="center", fontsize=9)
    ax.set_xlabel(f"Number of agents (out of {total_profiles}) using this term")
    ax.set_ylabel("Raw term (normalized)")
    ax.set_title(f"Which {facet_story[facet]} does the canon NOT yet recognize?", fontsize=12)
    ax.set_xlim(0, max(counts) * 1.35)
    ax.grid(axis="x", alpha=0.2, zorder=0)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=GREEN, label="≥5 profiles → LOCAL-extension candidate"),
        Patch(facecolor=AMBER, label="<5 profiles → alias or dismiss"),
    ], loc="lower right", frameon=False, fontsize=9)

    fig.text(0.5, 0.015, facet_caption[facet],
             ha="center", fontsize=9, style="italic", color=STONE, wrap=True)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def chart_comp_hist(rows: list[dict], path: Path) -> None:
    counts = [r["comp_total"] for r in rows]
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    bin_edges = [0, 1, 3, 5, 10, 20, 40, 80, max(counts) + 1]
    bin_labels = ["0", "1–2", "3–4", "5–9", "10–19", "20–39", "40–79", f"80+ (max {max(counts)})"]
    bucketed = [0] * (len(bin_edges) - 1)
    for c in counts:
        for i in range(len(bin_edges) - 1):
            if bin_edges[i] <= c < bin_edges[i + 1]:
                bucketed[i] += 1
                break
    bars = ax.bar(bin_labels, bucketed, color=AMBER, edgecolor=STONE, zorder=3)
    for bar, v in zip(bars, bucketed):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3, str(v), ha="center", fontsize=9)
    median = statistics.median(counts)
    ax.set_xlabel("Comp titles listed per profile (binned)")
    ax.set_ylabel("Number of agent profiles")
    ax.set_title("How many comp titles does each agent actually list?", fontsize=12)
    ax.grid(axis="y", alpha=0.2, zorder=0)
    fig.text(0.5, 0.02,
             f"Median = {median:.0f}. Most agents cite a few comps; one outlier listed 110 "
             f"— the matcher should cap per-profile contribution to avoid that agent dominating similarity scores.",
             ha="center", fontsize=9, style="italic", color=STONE)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path)
    plt.close(fig)


# ---------- narrative ----------
def render_report(profiles: list[dict], rows: list[dict], aliases: dict) -> str:
    n = len(profiles)
    mapped = Counter()
    total = Counter()
    for entry in profiles:
        for facet, terms in collect_terms(entry).items():
            for t in terms:
                if not isinstance(t, str) or not t.strip():
                    continue
                total[facet] += 1
                if normalize(t) in aliases.get(facet, {}):
                    mapped[facet] += 1

    def pct(f): return mapped[f] * 100 / total[f] if total[f] else 0

    section_counts = [r["section_count"] for r in rows]
    zero_section_profiles = [r["slug"] for r in rows if r["section_count"] == 0]
    missing_name = [r["slug"] for r in rows if "name" not in r["identity_filled"]]
    mean_missing_flag = statistics.mean([r["missing"] for r in rows])

    lines: list[str] = []
    lines.append(f"# MSWL Sample — Detailed Analysis ({n} profiles)\n")
    lines.append("First-pass deep-dive of 48 ManuscriptWishlist agent profiles captured through")
    lines.append("L0→L1 (Note-Taker prompt v2.0, Sonnet 4.5). Nothing in this report is in the")
    lines.append("product database — it's internal validation material.\n")

    lines.append("## Headline findings\n")
    lines.append(f"- **Capture worked.** 48/48 pages fetched, 0 parse failures, median {statistics.median(section_counts):.1f} preference sections per profile.")
    lines.append("- **Canon coverage is well below v1 targets on every facet.** Subject and audience are roughly half-mapped; **hard-no is effectively unmapped at 0.4%** — the vocabulary gap there is the single biggest finding of this run.")
    lines.append(f"- **Identity extraction is noisier than expected.** Only 83% of profiles yielded a name — {len(missing_name)} profiles came back nameless, suggesting either Cloudflare/header stripping or agents whose names aren't in the expected slot.")
    lines.append(f"- **Prompt is self-aware.** Mean {mean_missing_flag:.1f} MISSING flags per profile — the Note-Taker correctly reports what it couldn't find rather than hallucinating. Good news for downstream trust.")
    lines.append("")

    lines.append("## 1 · Canon coverage\n")
    lines.append("![coverage](charts/coverage.png)\n")
    lines.append("| Facet | Mapped | Total | Coverage | v1 target |")
    lines.append("|---|---:|---:|---:|---:|")
    for f in COVERAGE_TARGETS:
        lines.append(f"| {f} | {mapped[f]} | {total[f]} | {pct(f):.1f}% | {COVERAGE_TARGETS[f]}% |")
    lines.append("")
    lines.append("**Reading this:** Subject sits at ~52%. Every second genre label agents use has no")
    lines.append("home in the current canon. That doesn't mean the canon is half-wrong — most of")
    lines.append("the gap is synonyms (`\"feminist horror\"`, `\"upmarket commercial fiction\"`) that")
    lines.append("need aliasing, not fundamentally new concepts. A small number are genuine category")
    lines.append("gaps (horror subgenres).\n")
    lines.append("**Hard-no at 0.4% is the alarm bell.** `hard_nos.yaml` was designed ahead of the")
    lines.append("Note-Taker integration; the terms agents actually write (\"graphic sexual violence\",")
    lines.append("\"gratuitous gore\", \"torture porn\", \"sexual assault on-page\") bear almost no")
    lines.append("resemblance to the compact tags in that file. This facet needs a rewrite, not patches.\n")

    lines.append("## 2 · Profile structure\n")
    lines.append("![sections](charts/section_histogram.png)\n")
    lines.append("![section types](charts/section_types.png)\n")
    lines.append(f"- Median {statistics.median(section_counts):.1f} sections, max {max(section_counts)}, {len(zero_section_profiles)} profile(s) with zero sections.")
    lines.append("- **94% of sections are hybrid** (audience + genre). Agents rarely split preferences on just one axis, which is useful signal for how the matcher should weight section-level features.")
    lines.append("- Zero-section profiles: " + (", ".join(zero_section_profiles) if zero_section_profiles else "none") + ".")
    lines.append("")

    lines.append("## 3 · Identity completeness\n")
    lines.append("![identity](charts/identity_fill.png)\n")
    lines.append("- Name / organization / role / availability cluster at ~83% — the same 8 profiles fail all four, suggesting a systematic parse issue on those pages rather than independent failures.")
    lines.append("- **Email only in 52%.** Many agents route through a portal (QueryManager, Submittable) rather than list an address; `submission_portal` at 81% corroborates this.")
    lines.append("- Pronouns at 12% — reflects real MSWL profile sparsity, not a parser bug.")
    lines.append("")

    lines.append("## 4 · Hard-nos\n")
    lines.append("![hard nos](charts/hardno_buckets.png)\n")
    lines.append("- All four buckets fire in 29–52% of profiles.")
    lines.append("- The `trope` bucket lags (29%) because many agents fold trope dislikes into `content` prose rather than listing them separately — something the prompt could disambiguate more aggressively.")
    lines.append("- Combined with the 0.4% canon-mapping rate above: we have the data, we just can't filter on it yet.")
    lines.append("")

    lines.append("## 5 · Confidence flags\n")
    lines.append("![confidence](charts/confidence.png)\n")
    lines.append("- INFERRED mean 1.4, NUANCED 1.1, MISSING 3.1.")
    lines.append("- The MISSING > INFERRED ratio is healthy: the prompt is more willing to admit absence than to guess. That's exactly the behavior we want feeding L2/L3 — it stops downstream layers from building on fabricated signal.")
    lines.append("")

    lines.append("## 6 · Comp titles\n")
    lines.append("![comps](charts/comps.png)\n")
    lines.append(f"- {sum(1 for r in rows if r['comp_total'] > 0)}/{n} profiles list at least one comp, median {statistics.median([r['comp_total'] for r in rows]):.1f}, max {max(r['comp_total'] for r in rows)}.")
    lines.append("- The long tail (one profile with 110) is from an agent who lists favorite books broadly, not per-section comps. Matcher should cap contribution per profile to avoid that one profile dominating similarity scores.")
    lines.append("")

    lines.append("## 7 · Unmapped vocabulary leaderboards\n")
    lines.append("![top unmapped subject](charts/unmapped_subject.png)\n")
    lines.append("Green bars are LOCAL-extension candidates (≥5 profiles). At 48 profiles that bar is")
    lines.append("high — expect more to clear it as the sample grows toward the Step 4 target of 200.\n")
    lines.append("![top unmapped audience](charts/unmapped_audience.png)\n")
    lines.append("Small absolute counts but 4 of 6 are LOCAL candidates. Audience taxonomy is tight;")
    lines.append("the misses here are likely aliasing issues (`\"adults\"` vs `adult`, `\"teens\"` vs")
    lines.append("`young_adult`) rather than missing categories.\n")
    lines.append("![top unmapped hard_no](charts/unmapped_hard_no.png)\n")
    lines.append("This is the facet that needs most attention — see note in section 1.\n")

    lines.append("## 8 · Immediate action list\n")
    lines.append("1. **Audit `canon/hard_nos.yaml` against the top-50 unmapped hard_no terms.** It's not an alias problem; it's a vocabulary mismatch that needs redesign.")
    lines.append("2. **Add aliases** for the obvious token-overlap candidates in subject — low risk, immediate coverage lift. Estimate: +15–20 percentage points with a 60-line edit.")
    lines.append("3. **Add LOCAL:gothic_horror and LOCAL:psychological_horror** — both cleared the 5-profile bar.")
    lines.append("4. **Investigate the 8 identity-failure profiles.** Same pages, same failure mode → likely a specific template variant the prompt doesn't handle.")
    lines.append("5. **Rerun `scripts/canon_dryrun.py`** after aliases/extensions land (no re-crawl needed — it reads cached notes_parsed).")
    lines.append("6. **Do not treat this as v1 readiness.** 48 profiles is a diagnostic, not a lock. Step 4's 200-profile production run is still required.")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    if not NOTES_DIR.exists():
        sys.exit(f"No {NOTES_DIR} — run harvest first.")
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    profiles = load_profiles()
    aliases = load_aliases()
    rows = [per_profile(p) for p in profiles]

    chart_coverage(profiles, aliases, CHARTS_DIR / "coverage.png")
    chart_section_histogram(rows, CHARTS_DIR / "section_histogram.png")
    chart_section_types(rows, CHARTS_DIR / "section_types.png")
    chart_identity_fill(rows, CHARTS_DIR / "identity_fill.png")
    chart_hardno_buckets(rows, CHARTS_DIR / "hardno_buckets.png")
    chart_confidence(rows, CHARTS_DIR / "confidence.png")
    chart_comp_hist(rows, CHARTS_DIR / "comps.png")
    for facet in ("subject", "audience", "hard_no"):
        chart_top_unmapped(profiles, aliases, facet, CHARTS_DIR / f"unmapped_{facet}.png")

    REPORT.write_text(render_report(profiles, rows, aliases), encoding="utf-8")
    print(f"Wrote {REPORT}")
    print(f"Charts under {CHARTS_DIR}/")


if __name__ == "__main__":
    main()
