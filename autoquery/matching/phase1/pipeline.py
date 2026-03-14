"""Phase 1 matching pipeline orchestrator."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from autoquery.database.models import Agent, Manuscript, MatchingResult
from autoquery.matching.phase1.explainer import compute_match_tags, generate_snippet
from autoquery.matching.phase1.filter import filter_basic, filter_hard_nos
from autoquery.matching.phase1.reranker import mmr_rerank
from autoquery.matching.phase1.scorer import score_candidates
from autoquery.matching.genre_utils import load_genre_aliases
from autoquery.matching.types import MatchWeights, ScoredAgent

logger = logging.getLogger(__name__)

ALGORITHM_VERSION = "phase1-v1.0"
_TOP_N_FOR_MMR = 50


async def match(
    manuscript: Manuscript,
    agents: list[Agent],
    db_session: Session | None = None,
    embedding_model=None,
    weights: MatchWeights | None = None,
    output_size: int = 20,
    mmr_lambda: float = 0.7,
) -> list[ScoredAgent]:
    """
    Full matching pipeline: Filter → Score → MMR (top-50) → Explain.

    Public entry point for phase 1 matching.
    """
    alias_map = load_genre_aliases()

    # Layer 1: Filter
    passed, rejected_basic = filter_basic(agents)
    logger.info("Filter: %d passed, %d rejected (basic)", len(passed), len(rejected_basic))

    ms_emb = manuscript.embedding_fulltext
    if embedding_model and ms_emb:
        passed, rejected_hn = await filter_hard_nos(passed, ms_emb, embedding_model)
        logger.info("Filter: %d passed, %d rejected (hard-nos)", len(passed), len(rejected_hn))

    if not passed:
        return []

    # Layer 2: Score
    scored = score_candidates(
        manuscript, passed,
        weights=weights,
        alias_map=alias_map,
        db_session=db_session,
    )

    # Layer 3: MMR re-rank (top-50 → output_size)
    top_for_mmr = scored[:_TOP_N_FOR_MMR]
    reranked = mmr_rerank(top_for_mmr, lambda_param=mmr_lambda, output_size=output_size)

    # Layer 4: Explain
    agent_lookup = {a.id: a for a in passed}
    for sa in reranked:
        agent = agent_lookup.get(sa.agent_id)
        if agent:
            sa.match_tags = compute_match_tags(manuscript, agent, sa.scores, alias_map)
            sa.snippet = generate_snippet(agent)

    # Drop embeddings before returning
    for sa in reranked:
        sa.embedding = None

    return reranked


def persist_results(
    manuscript_id: int,
    results: list[ScoredAgent],
    db_session: Session,
) -> list[MatchingResult]:
    """Write results to matching_results table with algorithm_version."""
    records: list[MatchingResult] = []

    for sa in results:
        mr = MatchingResult(
            manuscript_id=manuscript_id,
            agent_id=sa.agent_id,
            genre_score=sa.scores.genre_score,
            fts_score=sa.scores.fts_score,
            semantic_score=sa.scores.semantic_score,
            audience_score=sa.scores.audience_score,
            composite_score=sa.composite_score,
            mmr_rank=sa.mmr_rank,
            algorithm_version=ALGORITHM_VERSION,
            queried_at=datetime.now(timezone.utc),
        )
        db_session.add(mr)
        records.append(mr)

    db_session.commit()
    return records
