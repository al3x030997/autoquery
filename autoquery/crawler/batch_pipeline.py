"""
Batch pipeline: seed_list.yaml → Browser Agent → Crawler → Extractor → Review Queue.

Usage:
    python -m autoquery.crawler.batch_pipeline
    python -m autoquery.crawler.batch_pipeline --domain janklow.com
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import yaml

from autoquery.crawler.browser_agent import BrowserAgent, DiscoveryResult
from autoquery.crawler.orchestrator import crawl_domain
from autoquery.database.db import SessionLocal

logger = logging.getLogger(__name__)

_SEED_LIST_PATH = Path(__file__).parent.parent.parent / "config" / "seed_list.yaml"


def load_seed_list(path: Path | None = None) -> list[dict]:
    """Load domains from seed_list.yaml."""
    p = path or _SEED_LIST_PATH
    with p.open() as f:
        data = yaml.safe_load(f) or {}
    return data.get("domains") or []


async def run_browser_agent_for_domain(
    domain: str, agent: BrowserAgent | None = None
) -> DiscoveryResult:
    """Run browser agent for a single domain."""
    if agent is None:
        agent = BrowserAgent()
    db = SessionLocal()
    try:
        result = await agent.discover_profiles(domain, db)
        return result
    finally:
        db.close()


async def run_batch_pipeline(
    domains: list[dict] | None = None,
    discover_only: bool = False,
) -> dict:
    """
    Full pipeline: load domains from seed_list.yaml → browser agent → crawler → extractor.

    Args:
        domains: List of domain dicts. If None, loads from seed_list.yaml.
        discover_only: If True, only run browser agent (skip crawler/extractor).

    Returns aggregate stats.
    """
    if domains is None:
        domains = load_seed_list()

    if not domains:
        logger.warning("No domains to process")
        return {"total_domains": 0, "error": "No domains in seed list"}

    agent = BrowserAgent()
    stats = {
        "total_domains": len(domains),
        "discovery_success": 0,
        "discovery_manual_review": 0,
        "discovery_error": 0,
        "total_profile_urls": 0,
        "crawl_results": [],
    }

    for entry in domains:
        domain = entry["domain"] if isinstance(entry, dict) else entry
        logger.info("Processing domain: %s", domain)

        # Phase 1: Browser Agent discovery
        discovery = await run_browser_agent_for_domain(domain, agent)

        if discovery.status == "success":
            stats["discovery_success"] += 1
            stats["total_profile_urls"] += len(discovery.profile_urls)
        elif discovery.status == "needs_manual_review":
            stats["discovery_manual_review"] += 1
        else:
            stats["discovery_error"] += 1

        logger.info(
            "Domain %s: status=%s, urls=%d",
            domain, discovery.status, len(discovery.profile_urls),
        )

        # Phase 2: Crawl discovered URLs (reuse existing orchestrator)
        if not discover_only and discovery.profile_urls:
            try:
                crawl_result = await crawl_domain(domain)
                stats["crawl_results"].append(crawl_result)
            except Exception as exc:
                logger.error("Crawl failed for %s: %s", domain, exc)
                stats["crawl_results"].append({"domain": domain, "error": str(exc)})

    logger.info("Batch pipeline complete: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) > 1 and sys.argv[1] == "--domain":
        if len(sys.argv) < 3:
            print("Usage: python -m autoquery.crawler.batch_pipeline --domain <domain>")
            sys.exit(1)
        domain = sys.argv[2]
        result = asyncio.run(run_browser_agent_for_domain(domain))
        print(f"Domain: {result.domain}")
        print(f"Status: {result.status}")
        print(f"Steps: {result.steps_taken}")
        print(f"Profile URLs: {len(result.profile_urls)}")
        for url in result.profile_urls:
            print(f"  {url}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--discover-only":
        result = asyncio.run(run_batch_pipeline(discover_only=True))
        print(result)
    else:
        result = asyncio.run(run_batch_pipeline())
        print(result)
