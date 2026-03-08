"""
Browser Agent — Claude Haiku 4.5 powered agent for discovering agent profile URLs
on literary agency websites.

Two-phase approach per domain:
  Phase 1 — Exploration: screenshot-based navigation to find agent listing page
  Phase 2 — URL Extraction: extract individual profile links from listing page

Separate script, not part of Celery. Admin triggers via CLI or Streamlit.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass, field

import anthropic
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from autoquery.crawler.content_extractor import extract_links, extract_text
from autoquery.crawler.crawler_engine import RateLimiter, normalize_url
from autoquery.database.models import KnownProfileUrl

logger = logging.getLogger(__name__)

MAX_NAV_STEPS = 5
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class DiscoveryResult:
    """Result of browser agent discovery for a single domain."""
    domain: str
    profile_urls: list[str] = field(default_factory=list)
    status: str = "success"  # success | needs_manual_review | login_wall | captcha | error
    steps_taken: int = 0
    error: str | None = None


class BrowserAgent:
    """Claude Haiku 4.5 powered browser agent for discovering agent profile URLs."""

    def __init__(
        self,
        anthropic_api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        rate_limiter: RateLimiter | None = None,
    ):
        api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._rate_limiter = rate_limiter or RateLimiter()

    async def discover_profiles(self, domain: str, db: Session) -> DiscoveryResult:
        """
        Two-phase discovery: explore domain → extract profile URLs.
        Returns DiscoveryResult with discovered profile URLs.
        """
        result = DiscoveryResult(domain=domain)
        homepage = f"https://{domain}"

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (compatible; AutoQuery/1.0; "
                    "+https://autoquery.app/bot)"
                ),
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()

            try:
                # Phase 1: Exploration
                listing_found = await self._explore(page, homepage, result)

                if not listing_found:
                    if result.status == "success":
                        result.status = "needs_manual_review"
                    return result

                # Phase 2: URL Extraction
                html = await page.content()
                current_url = page.url
                profile_urls = await self._extract_profile_urls(html, current_url, domain)

                if profile_urls:
                    saved = await self._save_profile_urls(domain, profile_urls, db)
                    result.profile_urls = profile_urls
                    logger.info(
                        "Domain %s: found %d profile URLs, saved %d new",
                        domain, len(profile_urls), saved,
                    )
                else:
                    result.status = "needs_manual_review"
                    logger.warning("Domain %s: listing page found but no profile URLs extracted", domain)

            except Exception as exc:
                result.status = "error"
                result.error = str(exc)
                logger.error("Domain %s: browser agent error: %s", domain, exc)
            finally:
                await browser.close()

        return result

    async def _explore(self, page, homepage: str, result: DiscoveryResult) -> bool:
        """
        Phase 1: Navigate from homepage to find agent listing page.
        Returns True if listing page found.
        """
        await self._rate_limiter.acquire(homepage)

        try:
            await page.goto(homepage, wait_until="networkidle", timeout=30_000)
        except Exception as exc:
            result.status = "error"
            result.error = f"Failed to load homepage: {exc}"
            return False

        for step in range(MAX_NAV_STEPS):
            result.steps_taken = step + 1
            logger.info("Domain %s: exploration step %d/%d at %s", result.domain, step + 1, MAX_NAV_STEPS, page.url)

            # Take screenshot
            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            # Ask Claude what to do
            action = await self._ask_claude_vision(screenshot_b64, page.url)

            if action is None:
                continue

            action_type = action.get("action")

            if action_type == "found":
                logger.info("Domain %s: listing page found at %s", result.domain, page.url)
                return True

            if action_type == "login_wall":
                result.status = "login_wall"
                logger.warning("Domain %s: login wall detected", result.domain)
                return False

            if action_type == "captcha":
                result.status = "captcha"
                logger.warning("Domain %s: captcha detected", result.domain)
                return False

            if action_type == "navigate":
                url = action.get("url", "")
                if url:
                    await self._rate_limiter.acquire(url)
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30_000)
                    except Exception as exc:
                        logger.warning("Domain %s: navigation failed to %s: %s", result.domain, url, exc)

            elif action_type == "click":
                selector = action.get("selector", "")
                if selector:
                    try:
                        await page.click(selector, timeout=5_000)
                        await page.wait_for_load_state("networkidle", timeout=15_000)
                    except Exception as exc:
                        logger.warning("Domain %s: click failed on %s: %s", result.domain, selector, exc)

            elif action_type == "scroll":
                await page.evaluate("window.scrollBy(0, 600)")
                await page.wait_for_timeout(1000)

        return False

    async def _extract_profile_urls(
        self, html: str, current_url: str, domain: str
    ) -> list[str]:
        """Phase 2: Extract individual agent profile URLs from listing page."""
        links = extract_links(html, current_url)
        text = extract_text(html)

        # Truncate for API call
        text_truncated = text[:4000] if len(text) > 4000 else text
        links_str = "\n".join(links[:200])

        response = await self._ask_claude_text(
            text_truncated,
            links,
            (
                "You are analyzing a literary agency website page that lists literary agents.\n\n"
                f"Page URL: {current_url}\n\n"
                f"Page text (truncated):\n{text_truncated}\n\n"
                f"Links found on page:\n{links_str}\n\n"
                "Which of these URLs are individual agent profile pages? "
                "An agent profile page typically has the agent's name in the URL "
                "(e.g. /agents/jane-smith or /team/john-doe).\n\n"
                'Respond with JSON: {"profile_urls": ["url1", "url2", ...]}\n'
                "Only include URLs that are very likely individual agent profiles. "
                "Do NOT include team overview pages, contact pages, or submission guidelines pages."
            ),
        )

        if response and "profile_urls" in response:
            urls = response["profile_urls"]
            # Normalize and filter to same domain
            valid = []
            for url in urls:
                normed = normalize_url(url)
                if domain.lower() in normed.lower():
                    valid.append(normed)
            return valid

        return []

    async def _ask_claude_vision(self, screenshot_b64: str, current_url: str) -> dict | None:
        """Send screenshot to Claude Haiku 4.5 for navigation decision."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": screenshot_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "You are navigating a literary agency website to find the page "
                                    "that lists all literary agents (team page, agents page, etc.).\n\n"
                                    f"Current URL: {current_url}\n\n"
                                    "Look at this screenshot. What should I do next?\n\n"
                                    "Respond with JSON only. Choose ONE action:\n"
                                    '- {"action": "found"} — if this page already shows a list of agents/team members with links to individual profiles\n'
                                    '- {"action": "navigate", "url": "https://..."} — navigate to a specific URL visible on the page\n'
                                    '- {"action": "click", "selector": "CSS selector"} — click an element (use simple selectors like "a[href*=agents]" or "nav a:nth-child(3)")\n'
                                    '- {"action": "scroll"} — scroll down to see more content\n'
                                    '- {"action": "login_wall"} — if the page requires login\n'
                                    '- {"action": "captcha"} — if there is a captcha\n\n'
                                    "Look for links like 'Our Agents', 'Team', 'Literary Agents', 'Staff', 'People', 'Who We Are'. "
                                    "Respond with only valid JSON, no explanation."
                                ),
                            },
                        ],
                    }
                ],
            )
            return self._parse_json_response(response.content[0].text)
        except Exception as exc:
            logger.error("Claude vision call failed: %s", exc)
            return None

    async def _ask_claude_text(
        self, page_text: str, links: list[str], prompt: str
    ) -> dict | None:
        """Text-only Claude call for Phase 2 URL filtering."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            return self._parse_json_response(response.content[0].text)
        except Exception as exc:
            logger.error("Claude text call failed: %s", exc)
            return None

    @staticmethod
    def _parse_json_response(text: str) -> dict | None:
        """Extract JSON from Claude's response, handling markdown code blocks."""
        text = text.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse Claude JSON response: %s", text[:200])
            return None

    async def _save_profile_urls(
        self, domain: str, urls: list[str], db: Session
    ) -> int:
        """Deduplicate and persist profile URLs to known_profile_urls."""
        saved = 0
        for url in urls:
            existing = db.query(KnownProfileUrl).filter_by(url=url).first()
            if not existing:
                db.add(KnownProfileUrl(
                    domain=domain,
                    url=url,
                    discovery_method="browser_agent",
                ))
                saved += 1
        db.commit()
        return saved
