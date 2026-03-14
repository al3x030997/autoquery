#!/usr/bin/env python3
"""Weight grid search CLI for matching pipeline tuning.

Usage: python scripts/tune_weights.py [--steps 5]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine, Text, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from autoquery.database.db import Base
from autoquery.matching.types import MatchWeights


# --- SQLite type adapters (same as tests/conftest.py) ---

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
    from sqlalchemy import BigInteger, Integer
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
                column.type = JSONEncodedList()
            elif col_type is BigInteger and column.primary_key:
                column.type = Integer()


class _FakeEmbeddingModel:
    dimensions = 1024

    async def embed(self, text: str) -> list[float]:
        return [0.0] * 1024

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 1024 for _ in texts]


def generate_weight_grid(step: float = 0.1) -> list[MatchWeights]:
    """Generate all (genre, fts, semantic, audience) combos summing to 1.0, each >= 0.05."""
    combos = []
    min_val = 0.05
    # Use integer arithmetic to avoid float precision issues
    int_step = round(step * 100)
    int_min = round(min_val * 100)

    for g in range(int_min, 101, int_step):
        for f in range(int_min, 101 - g, int_step):
            for s in range(int_min, 101 - g - f, int_step):
                a = 100 - g - f - s
                if a >= int_min:
                    combos.append(MatchWeights(
                        genre=g / 100, fts=f / 100,
                        semantic=s / 100, audience=a / 100,
                    ))
    return combos


async def run_grid_search(step: float = 0.1) -> None:
    from autoquery.evaluation.backward_test import run_backward_test_with_weights
    from autoquery.evaluation.test_data import get_test_cases

    _adapt_pg_types_for_sqlite()

    grid = generate_weight_grid(step)
    print(f"Testing {len(grid)} weight combinations (step={step})...\n")

    test_cases = get_test_cases()
    results: list[tuple[MatchWeights, dict]] = []

    for i, weights in enumerate(grid):
        # Fresh DB for each combo
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            model = _FakeEmbeddingModel()
            summary = await run_backward_test_with_weights(
                session, model, weights, test_cases=test_cases,
            )
            results.append((weights, summary))
        finally:
            session.close()
            Base.metadata.drop_all(engine)

        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{len(grid)}...")

    # Sort by mean P@10
    results.sort(key=lambda x: x[1]["mean_p_at_10"], reverse=True)

    # Print top 20
    print(f"\n{'=' * 80}")
    print(f"Top 20 weight combinations by mean P@10:")
    print(f"{'=' * 80}")
    print(f"{'Rank':<6} {'Genre':<8} {'FTS':<8} {'Sem':<8} {'Aud':<8} "
          f"{'P@5':<8} {'P@10':<8} {'R@10':<8} {'Div':<8}")
    print("-" * 80)

    for rank, (w, s) in enumerate(results[:20], 1):
        print(f"{rank:<6} {w.genre:<8.2f} {w.fts:<8.2f} {w.semantic:<8.2f} {w.audience:<8.2f} "
              f"{s['mean_p_at_5']:<8.3f} {s['mean_p_at_10']:<8.3f} "
              f"{s['mean_recall_at_10']:<8.3f} {s['mean_diversity']:<8.3f}")

    # Show defaults
    defaults = MatchWeights()
    default_result = next(
        (s for w, s in results if abs(w.genre - defaults.genre) < 0.01
         and abs(w.fts - defaults.fts) < 0.01
         and abs(w.semantic - defaults.semantic) < 0.01
         and abs(w.audience - defaults.audience) < 0.01),
        None,
    )
    print(f"\n{'=' * 80}")
    print(f"Current defaults: genre={defaults.genre}, fts={defaults.fts}, "
          f"semantic={defaults.semantic}, audience={defaults.audience}")
    if default_result:
        print(f"  P@5={default_result['mean_p_at_5']:.3f}, "
              f"P@10={default_result['mean_p_at_10']:.3f}, "
              f"R@10={default_result['mean_recall_at_10']:.3f}")
    else:
        print("  (defaults not in grid — adjust step size)")


def main():
    parser = argparse.ArgumentParser(description="Weight grid search for matching pipeline")
    parser.add_argument("--steps", type=int, default=5,
                        help="Number of steps from min to max (determines grid granularity)")
    args = parser.parse_args()

    # Convert steps to step size: e.g. 5 steps → 0.2, 10 steps → 0.1
    step = round(1.0 / args.steps, 2)
    asyncio.run(run_grid_search(step))


if __name__ == "__main__":
    main()
