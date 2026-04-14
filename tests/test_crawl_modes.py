"""Tests for single-page and site-crawl modes + blacklist bypass."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoquery.crawler.crawler_engine import BlacklistError, CrawlResult, RateLimiter, fetch_page
from autoquery.crawler.page_classifier import PageType


class _FakeCrawlRun:
    """Lightweight CrawlRun substitute that skips the database."""

    def __init__(self, **kwargs):
        self._run_id = 1
        self.pages_fetched = 0
        self.pages_index = 0
        self.pages_content = 0
        self.pages_skipped = 0
        self.pages_error = 0
        self.quality_extracted = 0
        self.quality_warned = 0
        self.quality_discarded = 0
        self.profiles_new = 0
        self.profiles_updated = 0
        self.profiles_unchanged = 0
        self.avg_quality_score = None
        self.top_issues = None
        self.error_message = None

    @property
    def run_id(self):
        return self._run_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_crawl_result(url: str, html: str = "<html>agent page</html>") -> CrawlResult:
    return CrawlResult(url=url, html=html, status_code=200, final_url=url, error=None)


@dataclass
class _FakeQuality:
    score: float = 0.9
    passed: bool = True
    issues: list = None
    dimensions: dict = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.dimensions is None:
            self.dimensions = {}


_BLACKLISTED_URL = "https://manuscriptwishlist.com/mswl-post/test-agent/"
_NORMAL_URL = "https://example-agency.com/agents/smith"


# ---------------------------------------------------------------------------
# fetch_page blacklist tests
# ---------------------------------------------------------------------------
class TestFetchPageBlacklist:
    def test_fetch_page_default_blocks_blacklist(self):
        """Default fetch_page raises BlacklistError for blacklisted domains."""
        rl = RateLimiter()
        with pytest.raises(BlacklistError):
            asyncio.run(fetch_page(_BLACKLISTED_URL, rl))

    @patch("autoquery.crawler.crawler_engine.async_playwright")
    def test_fetch_page_skip_blacklist(self, mock_pw):
        """skip_blacklist=True does not raise BlacklistError."""
        # Set up minimal Playwright mock so fetch_page can proceed
        mock_page = AsyncMock()
        mock_page.url = _BLACKLISTED_URL
        mock_page.goto = AsyncMock(return_value=MagicMock(status=200))
        mock_page.content = AsyncMock(return_value="<html></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_instance = AsyncMock()
        mock_instance.chromium = mock_chromium
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_pw.return_value = mock_instance

        result = asyncio.run(fetch_page(_BLACKLISTED_URL, RateLimiter(), skip_blacklist=True))
        assert result.error is None
        assert result.status_code == 200


# ---------------------------------------------------------------------------
# crawl_single_url tests
# ---------------------------------------------------------------------------
class TestCrawlSingleUrl:
    @patch("autoquery.crawler.orchestrator.CrawlRun", _FakeCrawlRun)
    @patch("autoquery.crawler.orchestrator.SessionLocal")
    @patch("autoquery.crawler.orchestrator.ProfileExtractor")
    @patch("autoquery.crawler.orchestrator.check_quality")
    @patch("autoquery.crawler.orchestrator.classify_page")
    @patch("autoquery.crawler.orchestrator.extract_text", return_value="Some agent bio text here")
    @patch("autoquery.crawler.orchestrator.extract_canonical_url", return_value=None)
    @patch("autoquery.crawler.orchestrator.extract_links", return_value=[])
    @patch("autoquery.crawler.orchestrator.robots_allowed", new_callable=AsyncMock, return_value=True)
    @patch("autoquery.crawler.orchestrator.fetch_page", new_callable=AsyncMock)
    def test_crawl_single_url_bypasses_blacklist(
        self, mock_fetch, mock_robots, mock_links, mock_canon, mock_text,
        mock_classify, mock_quality, mock_extractor, mock_session_local,
    ):
        """crawl_single_url completes successfully on a blacklisted domain."""
        from autoquery.crawler.orchestrator import crawl_single_url

        mock_fetch.return_value = _make_crawl_result(_BLACKLISTED_URL)
        mock_classify.return_value = PageType.CONTENT
        mock_quality.return_value = _FakeQuality()

        # DB mocks
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_session_local.return_value = mock_db

        mock_agent = MagicMock()
        mock_agent.review_status = "pending"
        mock_ext_instance = AsyncMock()
        mock_ext_instance.extract = AsyncMock(return_value=mock_agent)
        mock_extractor.return_value = mock_ext_instance

        result = asyncio.run(crawl_single_url(_BLACKLISTED_URL))

        # Verify skip_blacklist=True was passed to fetch_page
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs.get("skip_blacklist") is True

        assert result["pages_fetched"] == 1
        assert result["page_type"] == "CONTENT"
        assert result["profiles_new"] == 1


# ---------------------------------------------------------------------------
# crawl_site tests
# ---------------------------------------------------------------------------
class TestCrawlSite:
    @patch("autoquery.crawler.orchestrator.CrawlRun", _FakeCrawlRun)
    @patch("autoquery.crawler.orchestrator.SessionLocal")
    @patch("autoquery.crawler.orchestrator.check_quality")
    @patch("autoquery.crawler.orchestrator.classify_page")
    @patch("autoquery.crawler.orchestrator.extract_text", return_value="text")
    @patch("autoquery.crawler.orchestrator.extract_canonical_url", return_value=None)
    @patch("autoquery.crawler.orchestrator.extract_links", return_value=[])
    @patch("autoquery.crawler.orchestrator.robots_allowed", new_callable=AsyncMock, return_value=True)
    @patch("autoquery.crawler.orchestrator.fetch_page", new_callable=AsyncMock)
    def test_crawl_site_respects_blacklist(
        self, mock_fetch, mock_robots, mock_links, mock_canon, mock_text,
        mock_classify, mock_quality, mock_session_local,
    ):
        """crawl_site does NOT pass skip_blacklist — blacklisted domains are blocked."""
        from autoquery.crawler.orchestrator import crawl_site

        # fetch_page raises BlacklistError (simulating default behavior)
        mock_fetch.side_effect = BlacklistError("blacklisted")
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        result = asyncio.run(crawl_site(_BLACKLISTED_URL, max_pages=5))

        # Page should be skipped, not fetched
        assert result["pages_fetched"] == 0
        assert result["pages_skipped"] == 1

    @patch("autoquery.crawler.orchestrator.CrawlRun", _FakeCrawlRun)
    @patch("autoquery.crawler.orchestrator.SessionLocal")
    @patch("autoquery.crawler.orchestrator.check_quality")
    @patch("autoquery.crawler.orchestrator.classify_page")
    @patch("autoquery.crawler.orchestrator.extract_text", return_value="text")
    @patch("autoquery.crawler.orchestrator.extract_canonical_url", return_value=None)
    @patch("autoquery.crawler.orchestrator.extract_links")
    @patch("autoquery.crawler.orchestrator.robots_allowed", new_callable=AsyncMock, return_value=True)
    @patch("autoquery.crawler.orchestrator.fetch_page", new_callable=AsyncMock)
    def test_crawl_site_follows_index_links(
        self, mock_fetch, mock_robots, mock_links, mock_canon, mock_text,
        mock_classify, mock_quality, mock_session_local,
    ):
        """crawl_site discovers and processes linked pages from INDEX pages."""
        from autoquery.crawler.orchestrator import crawl_site

        start = "https://example-agency.com/team"
        child = "https://example-agency.com/agents/smith"

        # First call returns INDEX with a link; second returns CONTENT
        mock_fetch.side_effect = [
            _make_crawl_result(start, "<html>team</html>"),
            _make_crawl_result(child, "<html>agent</html>"),
        ]
        mock_classify.side_effect = [PageType.INDEX, PageType.CONTENT]
        mock_quality.return_value = _FakeQuality()
        mock_links.side_effect = [[child], []]

        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_session_local.return_value = mock_db

        result = asyncio.run(crawl_site(start, max_pages=10))

        assert result["pages_fetched"] == 2
        assert result["pages_index"] == 1
        assert result["pages_content"] == 1

    @patch("autoquery.crawler.orchestrator.CrawlRun", _FakeCrawlRun)
    @patch("autoquery.crawler.orchestrator.SessionLocal")
    @patch("autoquery.crawler.orchestrator.check_quality")
    @patch("autoquery.crawler.orchestrator.classify_page")
    @patch("autoquery.crawler.orchestrator.extract_text", return_value="text")
    @patch("autoquery.crawler.orchestrator.extract_canonical_url", return_value=None)
    @patch("autoquery.crawler.orchestrator.extract_links")
    @patch("autoquery.crawler.orchestrator.robots_allowed", new_callable=AsyncMock, return_value=True)
    @patch("autoquery.crawler.orchestrator.fetch_page", new_callable=AsyncMock)
    def test_crawl_site_max_pages(
        self, mock_fetch, mock_robots, mock_links, mock_canon, mock_text,
        mock_classify, mock_quality, mock_session_local,
    ):
        """crawl_site stops after max_pages."""
        from autoquery.crawler.orchestrator import crawl_site

        base = "https://example-agency.com"
        # Create many child links so BFS would continue forever
        children = [f"{base}/agent/{i}" for i in range(50)]

        def _make_result(url, rl, **kwargs):
            return _make_crawl_result(url)

        mock_fetch.side_effect = [_make_crawl_result(f"{base}/team")] + [
            _make_crawl_result(c) for c in children
        ]
        mock_classify.return_value = PageType.INDEX
        mock_quality.return_value = _FakeQuality()
        mock_links.side_effect = [children] + [[] for _ in children]

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        result = asyncio.run(crawl_site(f"{base}/team", max_pages=3))

        assert result["pages_fetched"] == 3
