"""
Celery task: crawl a single URL through the full pipeline.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

from autoquery.tasks.celery_app import celery_app
from autoquery.database.db import SessionLocal
from autoquery.database.models import CrawledPage, KnownProfileUrl
from autoquery.crawler.crawler_engine import (
    BlacklistError,
    CrawlResult,
    RateLimiter,
    fetch_page,
    normalize_url,
)
from autoquery.crawler.content_extractor import extract_canonical_url, extract_text
from autoquery.crawler.page_classifier import PageType, classify_page
from autoquery.crawler.quality_gate import check_quality
from autoquery.extractor import ProfileExtractor

# Module-level rate limiter shared across task invocations in the same worker process
_rate_limiter = RateLimiter()

# In-memory duplicate hash set (per-worker lifetime)
_seen_hashes: set[str] = set()


def _quality_action(quality_result) -> str:
    """Map quality result to action string."""
    if not quality_result.passed:
        return "discard"
    if quality_result.issues:
        return "extract_with_warning"
    return "extract"


@celery_app.task(name="autoquery.crawler.tasks.crawl_url_task", bind=True)
def crawl_url_task(self, url: str, crawl_run_id: int | None = None) -> dict:
    """
    Fetch, classify, quality-gate, and persist a single agent profile URL.

    Returns a dict with keys: url, status, page_type, quality_score, error.
    """
    import asyncio

    url = normalize_url(url)
    ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")

    async def _run() -> dict:
        # 1. Blacklist check (raises BlacklistError if blocked)
        try:
            result: CrawlResult = await fetch_page(url, _rate_limiter)
        except BlacklistError as exc:
            return {"url": url, "status": "blacklisted", "error": str(exc)}

        if result.error or not result.html:
            return {
                "url": url,
                "status": "fetch_failed",
                "error": result.error,
                "page_type": None,
                "quality_score": None,
            }

        # 2. Content extraction
        text = extract_text(result.html)
        canonical = extract_canonical_url(result.html, result.final_url)
        wc = len(text.split())

        # 3. Quality gate
        quality = check_quality(text, _seen_hashes)
        action = _quality_action(quality)

        # 4. Page classification (only for pages that pass quality)
        page_type: PageType | None = None
        if quality.passed:
            page_type = await classify_page(result.html, result.final_url, ollama_url)

        # 5. Persist CrawledPage (all pages, including discarded)
        domain = urlparse(url).netloc.lower()
        db = SessionLocal()
        try:
            db.add(CrawledPage(
                crawl_run_id=crawl_run_id,
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

            # 6. Persist to known_profile_urls (only for passed pages)
            if quality.passed:
                existing = db.query(KnownProfileUrl).filter_by(url=url).first()
                if not existing:
                    db.add(KnownProfileUrl(url=url, domain=domain))

            db.commit()

            # 7. Extract agent profile (only for passed pages)
            if quality.passed:
                try:
                    extractor = ProfileExtractor(ollama_url=ollama_url)
                    await extractor.extract(
                        clean_text=text,
                        source_url=canonical or url,
                        quality_score=quality.score,
                        quality_action=action,
                        db=db,
                    )
                except Exception:
                    pass  # extraction failure doesn't fail the task
        finally:
            db.close()

        if not quality.passed:
            return {
                "url": url,
                "status": "quality_failed",
                "page_type": None,
                "quality_score": quality.score,
                "issues": quality.issues,
            }

        return {
            "url": url,
            "status": "ok",
            "page_type": page_type.value if page_type else None,
            "quality_score": quality.score,
        }

    return asyncio.run(_run())
