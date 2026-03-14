"""Layer 3: MMR re-ranking with agency diversity constraint."""
from __future__ import annotations

from collections import Counter

from autoquery.matching.types import ScoredAgent

DEFAULT_LAMBDA = 0.7
MAX_PER_AGENCY_IN_TOP_10 = 3


def _cosine_sim(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity via dot product (L2-normalized vectors)."""
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def mmr_rerank(
    candidates: list[ScoredAgent],
    lambda_param: float = DEFAULT_LAMBDA,
    output_size: int = 20,
) -> list[ScoredAgent]:
    """
    Maximal Marginal Relevance re-ranking.

    MMR(d) = λ * relevance(d) - (1-λ) * max_sim(d, selected)

    Agency constraint: max 3 agents from same agency in top-10 positions.
    If agent embedding is None, diversity term = 0 (pure relevance).
    """
    if not candidates:
        return []

    remaining = list(candidates)
    selected: list[ScoredAgent] = []
    agency_count: Counter = Counter()

    while remaining and len(selected) < output_size:
        best_score = float("-inf")
        best_idx = 0

        for i, cand in enumerate(remaining):
            relevance = cand.composite_score

            # Max similarity to already-selected items
            if selected and cand.embedding:
                max_sim = max(
                    _cosine_sim(cand.embedding, s.embedding)
                    for s in selected
                )
            else:
                max_sim = 0.0

            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i

        candidate = remaining.pop(best_idx)

        # Agency constraint: max 3 per agency in top-10
        rank = len(selected) + 1
        if rank <= 10 and candidate.agency:
            if agency_count[candidate.agency] >= MAX_PER_AGENCY_IN_TOP_10:
                # Skip this candidate, try next
                continue

        if candidate.agency:
            agency_count[candidate.agency] += 1

        candidate.mmr_rank = rank
        selected.append(candidate)

    return selected
