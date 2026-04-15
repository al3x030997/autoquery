#!/usr/bin/env python3
"""Harvest MSWL profile pages through L0→L1 for internal canon-validation.

Reads a CSV of ManuscriptWishlist profile URLs (one per line or single `url`
column), fetches each page, cleans it, runs it through the Note-Taker prompt,
parses the output, and caches every intermediate artifact under
``data/mswl_sample/``.

Internal one-off. Never writes to the agents table. Bypasses the MSWL
blacklist entry only at this call site.

Usage:
    python scripts/harvest_mswl_sample.py --csv <path> [--limit 50] \
        [--min-delay 3.0] [--max-delay 7.0] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from playwright.async_api import async_playwright  # noqa: E402

from autoquery.crawler import content_extractor  # noqa: E402
from autoquery.crawler.crawler_engine import RateLimiter  # noqa: E402
from autoquery.extractor import note_parser  # noqa: E402
from autoquery.extractor.profile_extractor import ProfileExtractor  # noqa: E402
from autoquery.extractor.prompts import PROMPT_VERSION  # noqa: E402

OUT = REPO / "data" / "mswl_sample"
RAW_HTML_DIR = OUT / "raw_html"
CLEANED_DIR = OUT / "cleaned"
NOTES_RAW_DIR = OUT / "notes_raw"
NOTES_PARSED_DIR = OUT / "notes_parsed"
MANIFEST_CSV = OUT / "manifest.csv"
FAILURES_CSV = OUT / "failures.csv"

# Real Chrome UA — the default fetch_page UA identifies as a bot, which increases
# the chance of a Cloudflare challenge on MSWL. Internal capture only.
REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

HARD_CAP = 100
ABORT_AFTER_CONSECUTIVE_FAILURES = 3


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.rsplit("/", 1)[-1] or "root"
    return re.sub(r"[^a-z0-9_-]+", "-", slug.lower()).strip("-")


def load_urls(csv_path: Path) -> list[str]:
    raw = csv_path.read_text(encoding="utf-8-sig")
    urls: list[str] = []
    reader = csv.reader(raw.splitlines())
    for row in reader:
        if not row:
            continue
        cell = row[0].strip()
        if not cell or cell.lower() == "url":
            continue
        urls.append(cell)
    # de-duplicate while preserving order
    seen: set[str] = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


async def fetch(url: str, rate_limiter: RateLimiter) -> tuple[int | None, str | None, str | None]:
    """Fetch with a real browser UA. Returns (status, html, error)."""
    await rate_limiter.acquire(url)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=REAL_UA)
        page = await context.new_page()
        try:
            resp = await page.goto(url, wait_until="networkidle", timeout=30_000)
            status = resp.status if resp else None
            html = await page.content()
            return status, html, None
        except Exception as exc:
            return None, None, str(exc)
        finally:
            await browser.close()


def append_csv(path: Path, row: dict, fieldnames: list[str]) -> None:
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if new_file:
            w.writeheader()
        w.writerow(row)


async def process_url(
    url: str,
    *,
    rate_limiter: RateLimiter,
    extractor: ProfileExtractor | None,
    min_delay: float,
    max_delay: float,
) -> tuple[str, dict]:
    """Returns (status_label, manifest_row). status_label in {'ok','skipped','fetch_fail','extract_fail','rate_limited'}."""
    slug = slug_from_url(url)
    notes_parsed_path = NOTES_PARSED_DIR / f"{slug}.json"
    if notes_parsed_path.exists():
        return "skipped", {
            "url": url, "slug": slug, "http_status": "",
            "fetched_at": "", "prompt_version": PROMPT_VERSION,
            "extraction_ok": "cached",
        }

    status, html, err = await fetch(url, rate_limiter)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if err or html is None:
        append_csv(
            FAILURES_CSV,
            {"url": url, "slug": slug, "phase": "fetch", "http_status": status or "",
             "error": err or "no-html", "at": fetched_at},
            ["url", "slug", "phase", "http_status", "error", "at"],
        )
        if status in (403, 429, 503):
            return "rate_limited", {
                "url": url, "slug": slug, "http_status": status,
                "fetched_at": fetched_at, "prompt_version": PROMPT_VERSION,
                "extraction_ok": "False",
            }
        return "fetch_fail", {
            "url": url, "slug": slug, "http_status": status or "",
            "fetched_at": fetched_at, "prompt_version": PROMPT_VERSION,
            "extraction_ok": "False",
        }

    (RAW_HTML_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
    cleaned = content_extractor.extract_text(html)
    (CLEANED_DIR / f"{slug}.txt").write_text(cleaned, encoding="utf-8")

    # dry-run stops here
    if extractor is None:
        return "ok", {
            "url": url, "slug": slug, "http_status": status,
            "fetched_at": fetched_at, "prompt_version": PROMPT_VERSION,
            "extraction_ok": "dry-run",
        }

    try:
        raw_notes = await extractor._call_llm(cleaned)  # noqa: SLF001 — intentional
        (NOTES_RAW_DIR / f"{slug}.txt").write_text(raw_notes, encoding="utf-8")
        parsed = note_parser.parse(raw_notes)
    except Exception as exc:
        append_csv(
            FAILURES_CSV,
            {"url": url, "slug": slug, "phase": "extract", "http_status": status,
             "error": str(exc), "at": fetched_at},
            ["url", "slug", "phase", "http_status", "error", "at"],
        )
        return "extract_fail", {
            "url": url, "slug": slug, "http_status": status,
            "fetched_at": fetched_at, "prompt_version": PROMPT_VERSION,
            "extraction_ok": "False",
        }

    notes_parsed_path.write_text(
        json.dumps(
            {
                "url": url,
                "slug": slug,
                "fetched_at": fetched_at,
                "prompt_version": PROMPT_VERSION,
                "profile_notes": parsed,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # jitter between requests
    await asyncio.sleep(random.uniform(min_delay, max_delay))
    return "ok", {
        "url": url, "slug": slug, "http_status": status,
        "fetched_at": fetched_at, "prompt_version": PROMPT_VERSION,
        "extraction_ok": "True",
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--min-delay", type=float, default=3.0)
    ap.add_argument("--max-delay", type=float, default=7.0)
    ap.add_argument("--dry-run", action="store_true", help="Fetch only, skip LLM")
    args = ap.parse_args()

    if args.limit > HARD_CAP:
        sys.exit(f"--limit {args.limit} exceeds hard cap {HARD_CAP}")

    urls = load_urls(args.csv)[: args.limit]
    if not urls:
        sys.exit(f"No URLs in {args.csv}")

    for d in (RAW_HTML_DIR, CLEANED_DIR, NOTES_RAW_DIR, NOTES_PARSED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    rate_limiter = RateLimiter(min_gap=args.min_delay)
    extractor = None if args.dry_run else ProfileExtractor()

    print(f"Harvesting {len(urls)} URL(s){' (dry-run)' if args.dry_run else ''}")
    start = time.time()

    consecutive_rl = 0
    counts = {"ok": 0, "skipped": 0, "fetch_fail": 0, "extract_fail": 0, "rate_limited": 0}

    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {url} ...", end=" ", flush=True)
        status_label, row = await process_url(
            url,
            rate_limiter=rate_limiter,
            extractor=extractor,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
        )
        counts[status_label] += 1
        print(status_label)
        append_csv(
            MANIFEST_CSV,
            row,
            ["url", "slug", "http_status", "fetched_at", "prompt_version", "extraction_ok"],
        )

        if status_label == "rate_limited":
            consecutive_rl += 1
            if consecutive_rl >= ABORT_AFTER_CONSECUTIVE_FAILURES:
                print(f"ABORT: {consecutive_rl} consecutive rate-limit responses — backing off")
                break
        else:
            consecutive_rl = 0

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s  {counts}")
    print(f"Artifacts under: {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
