#!/usr/bin/env python3
"""
Live integration test for the Browser Agent against 5 real agency websites.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/test_live_browser_agent.py
    python scripts/test_live_browser_agent.py --max-tokens 20000

Requires: Playwright browsers installed (playwright install chromium)
Runtime: ~2-5 minutes
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 0. Pre-flight: check API key before heavy imports
# ---------------------------------------------------------------------------

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
    print("  export ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

# Add project root to path so imports work when running from repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set dummy DATABASE_URL so autoquery.database.db can import without error
# (we use our own in-memory SQLite engine, not this one)
os.environ.setdefault("DATABASE_URL", "sqlite:///unused")

# ---------------------------------------------------------------------------
# 1. SQLite setup (mirrors tests/conftest.py)
# ---------------------------------------------------------------------------

from sqlalchemy import Text, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

from autoquery.database.models import Base, KnownProfileUrl


class JSONEncodedList(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return json.loads(value) if value is not None else None


class JSONEncodedDict(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return json.loads(value) if value is not None else None


def _adapt_pg_types_for_sqlite():
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
    from pgvector.sqlalchemy import Vector

    for table in Base.metadata.tables.values():
        for column in table.columns:
            col_type = type(column.type)
            if col_type is ARRAY:
                column.type = JSONEncodedList()
            elif col_type is JSONB:
                column.type = JSONEncodedDict()
            elif col_type is TSVECTOR:
                column.type = Text()
            elif col_type is Vector:
                column.type = Text()


# ---------------------------------------------------------------------------
# 2. Test domains
# ---------------------------------------------------------------------------

TEST_DOMAINS = [
    {"domain": "curtisbrown.co.uk", "agency": "Curtis Brown (UK)"},
    {"domain": "writershouse.com", "agency": "Writers House"},
    {"domain": "inkwellmanagement.com", "agency": "InkWell Management"},
    {"domain": "bookendsliterary.com", "agency": "BookEnds Literary"},
    {"domain": "nelsonagency.com", "agency": "Nelson Literary Agency"},
]

# ---------------------------------------------------------------------------
# 3. Token budget tracking
# ---------------------------------------------------------------------------


class TokenBudgetExceeded(Exception):
    """Raised when cumulative token usage exceeds the configured budget."""


class TokenTracker:
    """Wraps an AsyncAnthropic client's messages.create to track token usage."""

    def __init__(self, client, max_tokens: int):
        self.max_tokens = max_tokens
        self.total_input = 0
        self.total_output = 0
        self.calls = 0
        # Per-domain accumulators (set externally)
        self.domain_input = 0
        self.domain_output = 0
        self._original_create = client.messages.create

        async def tracked_create(*args, **kwargs):
            response = await self._original_create(*args, **kwargs)
            inp = response.usage.input_tokens
            out = response.usage.output_tokens
            self.total_input += inp
            self.total_output += out
            self.domain_input += inp
            self.domain_output += out
            self.calls += 1
            total = self.total_input + self.total_output
            if total > self.max_tokens:
                raise TokenBudgetExceeded(
                    f"Token budget exceeded: {total:,} / {self.max_tokens:,} "
                    f"({self.calls} API calls)"
                )
            return response

        client.messages.create = tracked_create

    @property
    def total(self) -> int:
        return self.total_input + self.total_output

    def reset_domain(self):
        self.domain_input = 0
        self.domain_output = 0

    def domain_total(self) -> int:
        return self.domain_input + self.domain_output


# ---------------------------------------------------------------------------
# 4. Main test runner
# ---------------------------------------------------------------------------

from autoquery.crawler.browser_agent import BrowserAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live browser agent test")
    parser.add_argument(
        "--max-tokens", type=int, default=50_000,
        help="Token budget cap (default: 50000, ~$0.07 with Haiku)",
    )
    return parser.parse_args()


async def run_live_test(args: argparse.Namespace):
    # --- DB setup ---
    _adapt_pg_types_for_sqlite()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # --- Agent setup ---
    agent = BrowserAgent()  # picks up ANTHROPIC_API_KEY from env

    # --- Token tracking ---
    tracker = TokenTracker(agent._client, max_tokens=args.max_tokens)
    budget_exceeded = False

    results = []
    total_start = time.monotonic()

    print("=" * 70)
    print("  Browser Agent — Live Integration Test")
    print(f"  Token budget: {args.max_tokens:,}")
    print("=" * 70)
    print()

    for i, entry in enumerate(TEST_DOMAINS, 1):
        domain = entry["domain"]
        agency = entry["agency"]
        print(f"[{i}/5] {agency} ({domain}) ...")

        tracker.reset_domain()
        t0 = time.monotonic()
        try:
            result = await agent.discover_profiles(domain, session)
            elapsed = time.monotonic() - t0
            rec = {
                "domain": domain,
                "agency": agency,
                "status": result.status,
                "steps_taken": result.steps_taken,
                "profile_urls": result.profile_urls,
                "profile_count": len(result.profile_urls),
                "error": result.error,
                "elapsed_s": round(elapsed, 1),
                "tokens": tracker.domain_total(),
            }
        except TokenBudgetExceeded as exc:
            elapsed = time.monotonic() - t0
            budget_exceeded = True
            rec = {
                "domain": domain,
                "agency": agency,
                "status": "budget_exceeded",
                "steps_taken": 0,
                "profile_urls": [],
                "profile_count": 0,
                "error": str(exc),
                "elapsed_s": round(elapsed, 1),
                "tokens": tracker.domain_total(),
            }
        except Exception as exc:
            elapsed = time.monotonic() - t0
            rec = {
                "domain": domain,
                "agency": agency,
                "status": "crash",
                "steps_taken": 0,
                "profile_urls": [],
                "profile_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_s": round(elapsed, 1),
                "tokens": tracker.domain_total(),
            }

        results.append(rec)
        status_icon = "OK" if rec["status"] == "success" else rec["status"].upper()
        print(f"       -> {status_icon} | {rec['profile_count']} URLs | "
              f"{rec['steps_taken']} steps | {rec['elapsed_s']}s | "
              f"{rec['tokens']:,} tokens")
        if rec["error"]:
            print(f"       -> Error: {rec['error']}")
        print()

        if budget_exceeded:
            print(f"  *** Token budget exhausted ({tracker.total:,} / "
                  f"{tracker.max_tokens:,}). Skipping remaining domains. ***\n")
            break

    total_elapsed = round(time.monotonic() - total_start, 1)

    # --- DB verification ---
    db_rows = session.query(KnownProfileUrl).all()
    db_by_domain: dict[str, list[str]] = {}
    for row in db_rows:
        db_by_domain.setdefault(row.domain, []).append(row.url)

    session.close()

    # --- Summary ---
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Domain':<30} {'Status':<14} {'Steps':>5} {'URLs':>5} {'Tokens':>8} {'Time':>6}")
    print("-" * 74)
    for r in results:
        print(f"{r['domain']:<30} {r['status']:<14} {r['steps_taken']:>5} "
              f"{r['profile_count']:>5} {r['tokens']:>8,} {r['elapsed_s']:>5}s")
    print("-" * 74)
    total_urls = sum(r["profile_count"] for r in results)
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"Total: {success_count}/5 succeeded | {total_urls} profile URLs | "
          f"{tracker.total:,} tokens ({tracker.calls} API calls) | {total_elapsed}s")
    print()

    # DB verification
    print("DB verification (known_profile_urls table):")
    if db_by_domain:
        for d, urls in sorted(db_by_domain.items()):
            print(f"  {d}: {len(urls)} URLs")
    else:
        print("  (no rows persisted)")
    print()

    # Errors
    errors = [r for r in results if r["error"]]
    if errors:
        print("Errors:")
        for r in errors:
            print(f"  {r['domain']}: {r['error']}")
        print()

    # --- Write JSON report ---
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_elapsed_s": total_elapsed,
        "success_count": success_count,
        "total_profile_urls": total_urls,
        "token_usage": {
            "total": tracker.total,
            "input_tokens": tracker.total_input,
            "output_tokens": tracker.total_output,
            "api_calls": tracker.calls,
            "budget": args.max_tokens,
            "budget_exceeded": budget_exceeded,
        },
        "domains": results,
        "db_counts": {d: len(urls) for d, urls in db_by_domain.items()},
    }
    report_path = Path(__file__).parent / "live_test_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Full report written to: {report_path}")

    # --- Exit code ---
    if success_count >= 3:
        print("\nPASS: 3+ domains succeeded.")
        return 0
    else:
        print(f"\nFAIL: Only {success_count}/5 domains succeeded (need 3+).")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_live_test(parse_args()))
    sys.exit(exit_code)
