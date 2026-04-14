"""
Playwright-based async crawler with rate limiting, robots.txt enforcement,
blacklist checking, and CrawlRun DB logging.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from playwright.async_api import async_playwright

from autoquery.database.db import SessionLocal
from autoquery.database.models import CrawlRun as CrawlRunModel

# ---------------------------------------------------------------------------
# Blacklist
# ---------------------------------------------------------------------------
_BLACKLIST_PATH = Path(__file__).parent.parent.parent / "config" / "blacklist.yaml"


def _load_blacklist() -> set[str]:
    try:
        with _BLACKLIST_PATH.open() as f:
            data = yaml.safe_load(f)
        return {d.lower() for d in (data.get("domains") or [])}
    except Exception:
        return set()


_BLACKLISTED_DOMAINS: set[str] = _load_blacklist()


class BlacklistError(Exception):
    """Raised when a URL's domain is on the blacklist."""


# ---------------------------------------------------------------------------
# CrawlResult
# ---------------------------------------------------------------------------
@dataclass
class CrawlResult:
    url: str
    html: str | None
    status_code: int | None
    final_url: str        # after redirects
    error: str | None


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------
def normalize_url(url: str) -> str:
    """Strip fragments, lowercase scheme/host, strip www., remove trailing slash."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        fragment="",
        path=parsed.path.rstrip("/") or "/",
    )
    return urlunparse(normalized)


# ---------------------------------------------------------------------------
# Robots.txt helpers
# ---------------------------------------------------------------------------
_robots_cache: dict[str, RobotFileParser | None] = {}
_robots_lock = asyncio.Lock()

USER_AGENT = "autoquery"


async def _fetch_robots(base_url: str) -> RobotFileParser | None:
    robots_url = base_url.rstrip("/") + "/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(robots_url, follow_redirects=True)
            rp.parse(resp.text.splitlines())
        return rp
    except Exception:
        return None


async def robots_allowed(url: str) -> bool:
    """Return True if robots.txt allows autoquery to fetch this URL."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    async with _robots_lock:
        if base not in _robots_cache:
            _robots_cache[base] = await _fetch_robots(base)

    rp = _robots_cache[base]
    if rp is None:
        return True  # default allow on fetch error
    return rp.can_fetch(USER_AGENT, url)


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """Per-domain 2-second minimum gap between requests."""

    def __init__(self, min_gap: float = 2.0) -> None:
        self._min_gap = min_gap
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._meta_lock = asyncio.Lock()

    async def _get_lock(self, domain: str) -> asyncio.Lock:
        async with self._meta_lock:
            if domain not in self._locks:
                self._locks[domain] = asyncio.Lock()
            return self._locks[domain]

    async def acquire(self, url: str) -> None:
        domain = urlparse(url).netloc.lower()
        lock = await self._get_lock(domain)
        async with lock:
            last = self._last_request.get(domain, 0.0)
            wait = self._min_gap - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request[domain] = time.monotonic()


# ---------------------------------------------------------------------------
# fetch_page
# ---------------------------------------------------------------------------
async def fetch_page(url: str, rate_limiter: RateLimiter, *, skip_blacklist: bool = False) -> CrawlResult:
    """Fetch a page with Playwright Chromium (headless), respecting blacklist and rate limit."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Blacklist check — hard exception (skipped for explicit single-page crawls)
    if not skip_blacklist and domain in _BLACKLISTED_DOMAINS:
        raise BlacklistError(f"Domain '{domain}' is blacklisted")

    # Rate limit
    await rate_limiter.acquire(url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (compatible; AutoQuery/1.0; "
                "+https://autoquery.app/bot)"
            )
        )
        page = await context.new_page()
        status_code: int | None = None
        final_url = url

        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30_000)
            if response:
                status_code = response.status
                final_url = page.url
            html = await page.content()
            return CrawlResult(
                url=url,
                html=html,
                status_code=status_code,
                final_url=final_url,
                error=None,
            )
        except Exception as exc:
            return CrawlResult(
                url=url,
                html=None,
                status_code=status_code,
                final_url=final_url,
                error=str(exc),
            )
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# CrawlRun context manager
# ---------------------------------------------------------------------------
class CrawlRun:
    """Async context manager that creates/updates a crawl_runs DB row."""

    def __init__(self, *, domain: str | None = None, run_type: str | None = None) -> None:
        self._db = None
        self._run_id: int | None = None
        self._domain = domain
        self._run_type = run_type

        # Mutable stats — callers increment these directly
        self.pages_fetched: int = 0
        self.pages_index: int = 0
        self.pages_content: int = 0
        self.pages_skipped: int = 0
        self.pages_error: int = 0
        self.quality_extracted: int = 0
        self.quality_warned: int = 0
        self.quality_discarded: int = 0
        self.avg_quality_score: float | None = None
        self.profiles_new: int = 0
        self.profiles_updated: int = 0
        self.profiles_unchanged: int = 0
        self.top_issues: dict | None = None
        self.error_message: str | None = None

    @property
    def run_id(self) -> int | None:
        return self._run_id

    async def __aenter__(self) -> "CrawlRun":
        self._db = SessionLocal()
        run = CrawlRunModel(
            status="running",
            domain=self._domain,
            run_type=self._run_type,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        self._run_id = run.id
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._db and self._run_id:
            run = self._db.get(CrawlRunModel, self._run_id)
            if run:
                run.finished_at = datetime.now(timezone.utc)
                run.status = "failed" if exc_type else "completed"
                run.pages_fetched = self.pages_fetched
                run.pages_index = self.pages_index
                run.pages_content = self.pages_content
                run.pages_skipped = self.pages_skipped
                run.pages_error = self.pages_error
                run.quality_extracted = self.quality_extracted
                run.quality_warned = self.quality_warned
                run.quality_discarded = self.quality_discarded
                run.avg_quality_score = self.avg_quality_score
                run.profiles_new = self.profiles_new
                run.profiles_updated = self.profiles_updated
                run.profiles_unchanged = self.profiles_unchanged
                run.top_issues = self.top_issues
                run.error_message = self.error_message
                self._db.commit()
            self._db.close()
