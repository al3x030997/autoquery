"""
Tests for browser_agent.py and batch_pipeline.py.
Uses mocked Anthropic API and Playwright to avoid real network calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoquery.crawler.browser_agent import BrowserAgent, DiscoveryResult, MAX_NAV_STEPS
from autoquery.crawler.batch_pipeline import load_seed_list, run_batch_pipeline
from autoquery.database.models import KnownProfileUrl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claude_response(content_text: str):
    """Build a mock Anthropic messages.create response."""
    block = MagicMock()
    block.text = content_text
    resp = MagicMock()
    resp.content = [block]
    return resp


def _mock_page(url="https://example-agency.com", html="<html><body><a href='/agents/jane'>Jane</a></body></html>"):
    """Build a mock Playwright page object."""
    page = AsyncMock()
    page.url = url
    page.screenshot = AsyncMock(return_value=b"\x89PNG_fake_screenshot_data")
    page.content = AsyncMock(return_value=html)
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.evaluate = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    return page


# ---------------------------------------------------------------------------
# TestBrowserAgent
# ---------------------------------------------------------------------------

class TestBrowserAgent:

    @pytest.fixture
    def agent(self):
        """BrowserAgent with mocked Anthropic client."""
        with patch("autoquery.crawler.browser_agent.anthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            ba = BrowserAgent(anthropic_api_key="test-key")
            ba._client = mock_client
            yield ba

    @pytest.mark.asyncio
    async def test_discover_profiles_mock_claude(self, agent, db_session):
        """Mock Anthropic API → returns profile URLs via both phases."""
        listing_html = (
            "<html><body>"
            "<a href='https://example-agency.com/agents/jane-smith'>Jane Smith</a>"
            "<a href='https://example-agency.com/agents/john-doe'>John Doe</a>"
            "<a href='https://example-agency.com/about'>About</a>"
            "</body></html>"
        )
        mock_page = _mock_page(
            url="https://example-agency.com/team",
            html=listing_html,
        )

        # Phase 1: Claude says "found" on first screenshot
        agent._client.messages.create = AsyncMock(side_effect=[
            # Phase 1: exploration — found listing
            _make_claude_response('{"action": "found"}'),
            # Phase 2: extraction — identify profile URLs
            _make_claude_response(json.dumps({
                "profile_urls": [
                    "https://example-agency.com/agents/jane-smith",
                    "https://example-agency.com/agents/john-doe",
                ]
            })),
        ])

        with patch("autoquery.crawler.browser_agent.async_playwright") as mock_pw:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            pw_instance = AsyncMock()
            pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=pw_instance)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await agent.discover_profiles("example-agency.com", db_session)

        assert result.status == "success"
        assert len(result.profile_urls) == 2
        assert "https://example-agency.com/agents/jane-smith" in result.profile_urls

        # Verify URLs saved to DB
        saved = db_session.query(KnownProfileUrl).filter_by(domain="example-agency.com").all()
        assert len(saved) == 2
        assert all(row.discovery_method == "browser_agent" for row in saved)

    @pytest.mark.asyncio
    async def test_max_navigation_steps(self, agent, db_session):
        """Stops after MAX_NAV_STEPS steps and returns needs_manual_review."""
        mock_page = _mock_page()

        # Claude always says "scroll" — never finds listing
        agent._client.messages.create = AsyncMock(
            return_value=_make_claude_response('{"action": "scroll"}')
        )

        with patch("autoquery.crawler.browser_agent.async_playwright") as mock_pw:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            pw_instance = AsyncMock()
            pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=pw_instance)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await agent.discover_profiles("example-agency.com", db_session)

        assert result.status == "needs_manual_review"
        assert result.steps_taken == MAX_NAV_STEPS
        assert result.profile_urls == []

    @pytest.mark.asyncio
    async def test_deduplication(self, agent, db_session):
        """Same URL not inserted twice into known_profile_urls."""
        # Pre-insert a URL
        db_session.add(KnownProfileUrl(
            domain="example-agency.com",
            url="https://example-agency.com/agents/jane-smith",
            discovery_method="manual",
        ))
        db_session.commit()

        saved = await agent._save_profile_urls(
            "example-agency.com",
            [
                "https://example-agency.com/agents/jane-smith",  # duplicate
                "https://example-agency.com/agents/john-doe",    # new
            ],
            db_session,
        )

        assert saved == 1
        all_urls = db_session.query(KnownProfileUrl).filter_by(domain="example-agency.com").all()
        assert len(all_urls) == 2

    @pytest.mark.asyncio
    async def test_abort_on_login_wall(self, agent, db_session):
        """Login wall detected → abort with login_wall status."""
        mock_page = _mock_page()

        agent._client.messages.create = AsyncMock(
            return_value=_make_claude_response('{"action": "login_wall"}')
        )

        with patch("autoquery.crawler.browser_agent.async_playwright") as mock_pw:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            pw_instance = AsyncMock()
            pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=pw_instance)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await agent.discover_profiles("example-agency.com", db_session)

        assert result.status == "login_wall"
        assert result.profile_urls == []

    @pytest.mark.asyncio
    async def test_save_profile_urls(self, agent, db_session):
        """URLs persisted with correct discovery_method."""
        urls = [
            "https://example-agency.com/agents/alice",
            "https://example-agency.com/agents/bob",
        ]
        saved = await agent._save_profile_urls("example-agency.com", urls, db_session)

        assert saved == 2
        rows = db_session.query(KnownProfileUrl).all()
        assert len(rows) == 2
        for row in rows:
            assert row.discovery_method == "browser_agent"
            assert row.domain == "example-agency.com"

    def test_parse_json_response_plain(self):
        """Parse plain JSON."""
        result = BrowserAgent._parse_json_response('{"action": "found"}')
        assert result == {"action": "found"}

    def test_parse_json_response_markdown(self):
        """Parse JSON wrapped in markdown code block."""
        result = BrowserAgent._parse_json_response('```json\n{"action": "scroll"}\n```')
        assert result == {"action": "scroll"}

    def test_parse_json_response_with_text(self):
        """Parse JSON embedded in surrounding text."""
        result = BrowserAgent._parse_json_response('Here is the result: {"action": "navigate", "url": "https://foo.com"} done.')
        assert result["action"] == "navigate"


# ---------------------------------------------------------------------------
# TestBatchPipeline
# ---------------------------------------------------------------------------

class TestBatchPipeline:

    def test_load_seed_list(self, tmp_path):
        """Reads seed_list.yaml correctly."""
        seed_file = tmp_path / "seed_list.yaml"
        seed_file.write_text(
            "domains:\n"
            "  - domain: foo.com\n"
            "    agency_name: Foo Agency\n"
            "    country: US\n"
            "  - domain: bar.co.uk\n"
            "    agency_name: Bar Literary\n"
            "    country: UK\n"
        )
        domains = load_seed_list(seed_file)
        assert len(domains) == 2
        assert domains[0]["domain"] == "foo.com"
        assert domains[1]["country"] == "UK"

    def test_load_seed_list_empty(self, tmp_path):
        """Empty seed list returns empty list."""
        seed_file = tmp_path / "seed_list.yaml"
        seed_file.write_text("domains: []\n")
        domains = load_seed_list(seed_file)
        assert domains == []

    @pytest.mark.asyncio
    async def test_pipeline_end_to_end_mock(self, db_session):
        """Mock browser agent + crawler → pipeline runs without error."""
        mock_discovery = DiscoveryResult(
            domain="test-agency.com",
            profile_urls=["https://test-agency.com/agents/alice"],
            status="success",
            steps_taken=2,
        )

        with patch("autoquery.crawler.batch_pipeline.BrowserAgent") as MockAgent, \
             patch("autoquery.crawler.batch_pipeline.crawl_domain") as mock_crawl, \
             patch("autoquery.crawler.batch_pipeline.SessionLocal") as mock_sl:

            mock_agent_instance = AsyncMock()
            mock_agent_instance.discover_profiles = AsyncMock(return_value=mock_discovery)
            MockAgent.return_value = mock_agent_instance
            mock_sl.return_value = db_session
            mock_crawl.return_value = {"domain": "test-agency.com", "profiles_new": 3}

            result = await run_batch_pipeline(
                domains=[{"domain": "test-agency.com", "agency_name": "Test Agency", "country": "US"}]
            )

        assert result["total_domains"] == 1
        assert result["discovery_success"] == 1
        assert result["total_profile_urls"] == 1
        assert len(result["crawl_results"]) == 1

    @pytest.mark.asyncio
    async def test_pipeline_discover_only(self, db_session):
        """discover_only=True skips crawl phase."""
        mock_discovery = DiscoveryResult(
            domain="test-agency.com",
            profile_urls=["https://test-agency.com/agents/alice"],
            status="success",
            steps_taken=1,
        )

        with patch("autoquery.crawler.batch_pipeline.BrowserAgent") as MockAgent, \
             patch("autoquery.crawler.batch_pipeline.crawl_domain") as mock_crawl, \
             patch("autoquery.crawler.batch_pipeline.SessionLocal") as mock_sl:

            mock_agent_instance = AsyncMock()
            mock_agent_instance.discover_profiles = AsyncMock(return_value=mock_discovery)
            MockAgent.return_value = mock_agent_instance
            mock_sl.return_value = db_session

            result = await run_batch_pipeline(
                domains=[{"domain": "test-agency.com"}],
                discover_only=True,
            )

        assert result["discovery_success"] == 1
        mock_crawl.assert_not_called()
        assert result["crawl_results"] == []
