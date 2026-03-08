"""
Domain crawl orchestrator and backfill for known profile URLs.

Usage:
    python -m autoquery.crawler.orchestrator <domain>
    python -m autoquery.crawler.orchestrator --backfill
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections import deque
from urllib.parse import urlparse

from autoquery.crawler.content_extractor import (
    extract_canonical_url,
    extract_links,
    extract_text,
)
from autoquery.crawler.crawler_engine import (
    BlacklistError,
    CrawlRun,
    RateLimiter,
    fetch_page,
    normalize_url,
    robots_allowed,
)
from autoquery.crawler.page_classifier import PageType, classify_page
from autoquery.crawler.quality_gate import check_quality
from autoquery.database.db import SessionLocal
from autoquery.database.models import CrawledPage, KnownProfileUrl
from autoquery.extractor import ProfileExtractor
from autoquery.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Common agency index paths to seed BFS
_SEED_PATHS = [
    "/",
    "/about",
    "/team",
    "/our-agents",
    "/agents",
    "/literary-agents",
    "/staff",
    "/people",
    "/who-we-are",
    "/about-us",
    "/our-team",
]

_rate_limiter = RateLimiter()


def _quality_action(quality_result) -> str:
    if not quality_result.passed:
        return "discard"
    if quality_result.issues:
        return "extract_with_warning"
    return "extract"


async def _process_page(
    url: str,
    crawl_run: CrawlRun,
    seen_hashes: set[str],
    ollama_url: str,
) -> tuple[PageType | None, list[str]]:
    """
    Fetch, extract, quality-gate, and classify a single URL.
    Persists CrawledPage and (if applicable) KnownProfileUrl.
    Returns (page_type, discovered_links).
    """
    discovered_links: list[str] = []

    # Check robots.txt
    if not await robots_allowed(url):
        logger.info("Blocked by robots.txt: %s", url)
        crawl_run.pages_skipped += 1
        return None, []

    # Fetch
    try:
        result = await fetch_page(url, _rate_limiter)
    except BlacklistError:
        logger.info("Blacklisted: %s", url)
        crawl_run.pages_skipped += 1
        return None, []

    crawl_run.pages_fetched += 1

    if result.error or not result.html:
        logger.warning("Fetch error for %s: %s", url, result.error)
        crawl_run.pages_error += 1
        # Persist error record
        db = SessionLocal()
        try:
            db.add(CrawledPage(
                crawl_run_id=crawl_run.run_id,
                url=url,
                quality_action="error",
            ))
            db.commit()
        finally:
            db.close()
        return None, []

    # Extract text
    text = extract_text(result.html)
    canonical = extract_canonical_url(result.html, result.final_url)
    wc = len(text.split())

    # Quality gate
    quality = check_quality(text, seen_hashes)
    action = _quality_action(quality)

    # Classify (only if quality passed)
    page_type: PageType | None = None
    if quality.passed:
        page_type = await classify_page(result.html, result.final_url, ollama_url)

    # Update crawl run stats
    if quality.passed:
        if action == "extract":
            crawl_run.quality_extracted += 1
        else:
            crawl_run.quality_warned += 1
    else:
        crawl_run.quality_discarded += 1

    if page_type == PageType.INDEX:
        crawl_run.pages_index += 1
        # Extract links from INDEX pages only
        discovered_links = extract_links(result.html, result.final_url)
    elif page_type == PageType.CONTENT:
        crawl_run.pages_content += 1

    # Persist CrawledPage
    domain = urlparse(url).netloc.lower()
    db = SessionLocal()
    try:
        db.add(CrawledPage(
            crawl_run_id=crawl_run.run_id,
            url=url,
            canonical_url=canonical,
            page_type=page_type.value if page_type else None,
            clean_text=text,
            word_count=wc,
            quality_score=quality.score,
            quality_action=action,
            quality_dimensions=quality.dimensions,
            quality_issues=quality.issues,
        ))

        # Persist KnownProfileUrl for CONTENT pages that pass quality
        if quality.passed and page_type == PageType.CONTENT:
            existing = db.query(KnownProfileUrl).filter_by(url=url).first()
            if not existing:
                db.add(KnownProfileUrl(
                    url=url,
                    domain=domain,
                    discovery_method="domain_crawl",
                ))

        db.commit()

        # Extract agent profile for CONTENT pages that pass quality
        if quality.passed and page_type == PageType.CONTENT:
            try:
                extractor = ProfileExtractor(ollama_url=ollama_url)
                agent = await extractor.extract(
                    clean_text=text,
                    source_url=canonical or url,
                    quality_score=quality.score,
                    quality_action=action,
                    db=db,
                )
                if agent:
                    if agent.review_status == "pending":
                        crawl_run.profiles_new += 1
                    else:
                        crawl_run.profiles_updated += 1
            except Exception as exc:
                logger.error("Extraction failed for %s: %s", url, exc)
    finally:
        db.close()

    return page_type, discovered_links


async def crawl_domain(domain: str) -> dict:
    """
    BFS crawl of a domain: seed with common paths, discover links from INDEX
    pages, persist all results.
    """
    ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")
    seen_hashes: set[str] = set()
    visited: set[str] = set()
    quality_scores: list[float] = []

    # Build seed URLs
    base = f"https://{domain}"
    queue: deque[str] = deque()
    for path in _SEED_PATHS:
        seed = normalize_url(base + path)
        if seed not in visited:
            visited.add(seed)
            queue.append(seed)

    async with CrawlRun(domain=domain, run_type="domain_crawl") as crawl_run:
        while queue:
            url = queue.popleft()
            logger.info("Processing: %s", url)

            page_type, links = await _process_page(
                url, crawl_run, seen_hashes, ollama_url
            )

            # Only enqueue links discovered from INDEX pages
            if page_type == PageType.INDEX:
                for link in links:
                    normed = normalize_url(link)
                    if normed not in visited:
                        visited.add(normed)
                        queue.append(normed)

        return {
            "domain": domain,
            "run_id": crawl_run.run_id,
            "pages_fetched": crawl_run.pages_fetched,
            "pages_index": crawl_run.pages_index,
            "pages_content": crawl_run.pages_content,
            "pages_skipped": crawl_run.pages_skipped,
            "pages_error": crawl_run.pages_error,
            "profiles_new": crawl_run.profiles_new,
        }


async def backfill_known_urls() -> dict:
    """
    Re-crawl all known_profile_urls to populate crawled_pages records.
    Does NOT follow links.
    """
    ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")
    seen_hashes: set[str] = set()

    # Load all known URLs
    db = SessionLocal()
    try:
        urls = [row.url for row in db.query(KnownProfileUrl).all()]
    finally:
        db.close()

    logger.info("Backfilling %d known URLs", len(urls))

    async with CrawlRun(run_type="backfill") as crawl_run:
        for url in urls:
            logger.info("Backfill: %s", url)
            await _process_page(url, crawl_run, seen_hashes, ollama_url)

        return {
            "run_id": crawl_run.run_id,
            "total_urls": len(urls),
            "pages_fetched": crawl_run.pages_fetched,
            "pages_content": crawl_run.pages_content,
            "pages_error": crawl_run.pages_error,
            "quality_discarded": crawl_run.quality_discarded,
        }


# ---------------------------------------------------------------------------
# Celery task wrappers
# ---------------------------------------------------------------------------
@celery_app.task(name="autoquery.crawler.orchestrator.crawl_domain_task")
def crawl_domain_task(domain: str) -> dict:
    return asyncio.run(crawl_domain(domain))


@celery_app.task(name="autoquery.crawler.orchestrator.backfill_task")
def backfill_task() -> dict:
    return asyncio.run(backfill_known_urls())


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m autoquery.crawler.orchestrator <domain>")
        print("  python -m autoquery.crawler.orchestrator --backfill")
        sys.exit(1)

    if sys.argv[1] == "--backfill":
        result = asyncio.run(backfill_known_urls())
    else:
        result = asyncio.run(crawl_domain(sys.argv[1]))

    print(result)
