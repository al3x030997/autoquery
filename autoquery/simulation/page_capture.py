"""
Page Capture — Screenshot + text extraction for agent profile pages.

Takes a CSV of agent URLs, visits each with Playwright, and saves:
  - Full-page high-resolution screenshot (PNG)
  - Complete rendered text content (TXT)

No LLM calls, no extraction, no embeddings — raw capture only.

Usage:
    python -m autoquery.simulation.page_capture --input agents.csv --output-dir ./capture_output
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; AutoQuery/1.0; +https://autoquery.app/bot)"

DISMISS_SELECTORS = [
    # Cookie banners
    "button:has-text('Accept All')",
    "button:has-text('Accept')",
    "button:has-text('Agree')",
    "button:has-text('OK')",
    "button:has-text('Got it')",
    "button:has-text('I agree')",
    ".cookie-accept",
    "#cookie-consent button",
    "[data-testid='cookie-accept']",
    ".cc-accept",
    ".cc-btn.cc-dismiss",
    # Newsletter / signup modals
    ".modal .close",
    ".modal-close",
    "[aria-label='Close']",
    "[aria-label='close']",
    "button:has-text('No thanks')",
    "button:has-text('Close')",
    "button:has-text('Not now')",
    ".popup-close",
    ".newsletter-close",
    # Generic overlay close buttons
    ".overlay .close",
    "button.close",
    "[data-dismiss='modal']",
]


class PageCapture:
    """Captures full-page screenshots and text content from agent profile URLs."""

    def __init__(self, output_dir: str, headless: bool = True):
        self.output_dir = Path(output_dir)
        self.screenshots_dir = self.output_dir / "screenshots"
        self.text_dir = self.output_dir / "text_content"
        self.headless = headless

    def _ensure_dirs(self) -> None:
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.text_dir.mkdir(parents=True, exist_ok=True)

    async def capture_batch(self, csv_path: str) -> dict:
        """Read CSV and capture all URLs. Returns summary stats."""
        entries = self._read_csv(csv_path)
        if not entries:
            logger.error("No entries found in %s", csv_path)
            return {"total": 0, "success": 0, "failed": 0}

        self._ensure_dirs()
        total = len(entries)
        success = 0
        failed = 0

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=2,
            )

            for i, (url, agent_name) in enumerate(entries, 1):
                logger.info("[%d/%d] Capturing %s from %s...", i, total, agent_name, url)
                try:
                    await self._capture_page(context, url, agent_name)
                    success += 1
                    logger.info("[%d/%d] Done: %s", i, total, agent_name)
                except Exception as exc:
                    failed += 1
                    logger.error("[%d/%d] Failed %s: %s", i, total, agent_name, exc)

            await browser.close()

        summary = {"total": total, "success": success, "failed": failed}
        logger.info("Capture complete: %d/%d succeeded, %d failed", success, total, failed)
        return summary

    async def _capture_page(self, context, url: str, agent_name: str) -> None:
        """Capture a single page: sectioned screenshots + text."""
        page = await context.new_page()
        page.set_default_timeout(30_000)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)

            await self._dismiss_overlays(page)
            await self._scroll_to_bottom(page)
            # Scroll back to top before capturing
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_load_state("networkidle", timeout=10_000)

            # Sectioned screenshots (viewport-sized chunks)
            agent_screenshot_dir = self.screenshots_dir / agent_name
            agent_screenshot_dir.mkdir(parents=True, exist_ok=True)

            total_height = await page.evaluate("document.documentElement.scrollHeight")
            viewport_height = 1080  # matches our viewport config
            section = 0

            while section * viewport_height < total_height:
                y_offset = section * viewport_height
                await page.evaluate(f"window.scrollTo(0, {y_offset})")
                await page.wait_for_timeout(300)

                screenshot_path = agent_screenshot_dir / f"section_{section:02d}.png"
                await page.screenshot(path=str(screenshot_path), type="png")
                section += 1

            logger.info("Saved %d screenshot sections for %s", section, agent_name)

            # Rendered text content
            text = await page.evaluate("document.body.innerText")
            text_path = self.text_dir / f"{agent_name}.txt"
            text_path.write_text(text, encoding="utf-8")

        finally:
            await page.close()

    async def _dismiss_overlays(self, page) -> None:
        """Try to dismiss cookie banners, newsletter popups, and modal overlays."""
        for selector in DISMISS_SELECTORS:
            try:
                await page.click(selector, timeout=1500)
                await page.wait_for_timeout(500)
            except Exception:
                continue

    async def _scroll_to_bottom(self, page) -> None:
        """Scroll incrementally to trigger lazy loading."""
        previous_height = 0
        max_scrolls = 50  # safety limit

        for _ in range(max_scrolls):
            current_height = await page.evaluate(
                "document.documentElement.scrollHeight"
            )
            viewport_height = await page.evaluate("window.innerHeight")
            scroll_top = await page.evaluate("window.pageYOffset")

            if scroll_top + viewport_height >= current_height:
                break

            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(0.5)

            # Check if page grew (lazy load triggered)
            new_height = await page.evaluate(
                "document.documentElement.scrollHeight"
            )
            if new_height == previous_height == current_height:
                break
            previous_height = current_height

    @staticmethod
    def _read_csv(csv_path: str) -> list[tuple[str, str]]:
        """Read CSV with columns: url, agent_name."""
        entries = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("url", "").strip()
                agent_name = row.get("agent_name", "").strip()
                if url and agent_name:
                    entries.append((url, agent_name))
                else:
                    logger.warning("Skipping invalid row: %s", row)
        return entries


async def main():
    parser = argparse.ArgumentParser(
        description="Capture full-page screenshots and text from agent profile URLs."
    )
    parser.add_argument(
        "--input", required=True, help="CSV file with columns: url, agent_name"
    )
    parser.add_argument(
        "--output-dir", default="./capture_output", help="Output directory"
    )
    parser.add_argument(
        "--headless",
        default="true",
        choices=["true", "false"],
        help="Run browser in headless mode (default: true)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    capture = PageCapture(
        output_dir=args.output_dir,
        headless=args.headless == "true",
    )
    await capture.capture_batch(args.input)


if __name__ == "__main__":
    asyncio.run(main())
