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
    *,
    skip_blacklist: bool = False,
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
        result = await fetch_page(url, _rate_limiter, skip_blacklist=skip_blacklist)
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
    elif page_type == PageType.MULTI_AGENT:
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

        # Persist KnownProfileUrl for CONTENT/MULTI_AGENT pages that pass quality
        if quality.passed and page_type in (PageType.CONTENT, PageType.MULTI_AGENT):
            existing = db.query(KnownProfileUrl).filter_by(url=url).first()
            if not existing:
                db.add(KnownProfileUrl(
                    url=url,
                    domain=domain,
                    discovery_method="domain_crawl",
                ))

        db.commit()

        # Extract agent profile(s) for CONTENT / MULTI_AGENT pages that pass quality
        if quality.passed and page_type == PageType.MULTI_AGENT:
            try:
                extractor = ProfileExtractor(ollama_url=ollama_url)
                agents = await extractor.extract_multi(
                    clean_text=text,
                    source_url=canonical or url,
                    quality_score=quality.score,
                    quality_action=action,
                    db=db,
                )
                for agent in agents:
                    if agent.review_status == "pending":
                        crawl_run.profiles_new += 1
                    else:
                        crawl_run.profiles_updated += 1
            except Exception as exc:
                logger.error("Multi-agent extraction failed for %s: %s", url, exc)
        elif quality.passed and page_type == PageType.CONTENT:
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


async def crawl_single_url(url: str) -> dict:
    """
    Crawl exactly one user-provided URL.  Bypasses the domain blacklist so
    that individual agent pages on aggregator sites can be fetched.
    """
    ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")
    seen_hashes: set[str] = set()
    domain = urlparse(url).netloc.lower()

    async with CrawlRun(domain=domain, run_type="single_url") as crawl_run:
        page_type, _ = await _process_page(
            url, crawl_run, seen_hashes, ollama_url,
            skip_blacklist=True,
        )

        return {
            "url": url,
            "run_id": crawl_run.run_id,
            "page_type": page_type.value if page_type else None,
            "pages_fetched": crawl_run.pages_fetched,
            "profiles_new": crawl_run.profiles_new,
            "profiles_updated": crawl_run.profiles_updated,
            "pages_error": crawl_run.pages_error,
        }


async def crawl_site(start_url: str, *, max_pages: int = 200) -> dict:
    """
    BFS crawl starting from *start_url*.  Follows same-domain links discovered
    on INDEX pages, up to *max_pages*.  Respects the domain blacklist (BFS on
    aggregator sites stays blocked).
    """
    ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")
    seen_hashes: set[str] = set()
    visited: set[str] = set()

    start_norm = normalize_url(start_url)
    start_domain = urlparse(start_norm).netloc.lower()
    visited.add(start_norm)
    queue: deque[str] = deque([start_norm])

    async with CrawlRun(domain=start_domain, run_type="site_crawl") as crawl_run:
        while queue and crawl_run.pages_fetched < max_pages:
            url = queue.popleft()
            logger.info("Processing: %s", url)

            page_type, links = await _process_page(
                url, crawl_run, seen_hashes, ollama_url,
            )

            # Only enqueue same-domain links from INDEX pages
            if page_type == PageType.INDEX:
                for link in links:
                    normed = normalize_url(link)
                    if urlparse(normed).netloc.lower() == start_domain and normed not in visited:
                        visited.add(normed)
                        queue.append(normed)

        return {
            "start_url": start_url,
            "domain": start_domain,
            "run_id": crawl_run.run_id,
            "pages_fetched": crawl_run.pages_fetched,
            "pages_index": crawl_run.pages_index,
            "pages_content": crawl_run.pages_content,
            "pages_skipped": crawl_run.pages_skipped,
            "pages_error": crawl_run.pages_error,
            "profiles_new": crawl_run.profiles_new,
            "profiles_updated": crawl_run.profiles_updated,
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


@celery_app.task(name="autoquery.crawler.orchestrator.crawl_single_url_task")
def crawl_single_url_task(url: str) -> dict:
    return asyncio.run(crawl_single_url(url))


@celery_app.task(name="autoquery.crawler.orchestrator.crawl_site_task")
def crawl_site_task(start_url: str, max_pages: int = 200) -> dict:
    return asyncio.run(crawl_site(start_url, max_pages=max_pages))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m autoquery.crawler.orchestrator <domain>")
        print("  python -m autoquery.crawler.orchestrator --backfill")
        print("  python -m autoquery.crawler.orchestrator --url <url>        # single page")
        print("  python -m autoquery.crawler.orchestrator --site <start_url>  # site crawl")
        sys.exit(1)

    if sys.argv[1] == "--backfill":
        result = asyncio.run(backfill_known_urls())
    elif sys.argv[1] == "--url":
        if len(sys.argv) < 3:
            print("Error: --url requires a URL argument")
            sys.exit(1)
        result = asyncio.run(crawl_single_url(sys.argv[2]))
    elif sys.argv[1] == "--site":
        if len(sys.argv) < 3:
            print("Error: --site requires a start URL argument")
            sys.exit(1)
        max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        result = asyncio.run(crawl_site(sys.argv[2], max_pages=max_pages))
    else:
        result = asyncio.run(crawl_domain(sys.argv[1]))

    print(result)
