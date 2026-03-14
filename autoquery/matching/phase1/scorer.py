"""Layer 2: Hybrid scoring — genre, audience, FTS, semantic signals."""
from __future__ import annotations

import logging
import math

from sqlalchemy.orm import Session

from autoquery.database.models import Agent, Manuscript
from autoquery.matching.genre_utils import genre_match_score, load_genre_aliases
from autoquery.matching.types import MatchWeights, ScoreBreakdown, ScoredAgent

logger = logging.getLogger(__name__)

AUDIENCE_ORDER = ["children's", "middle_grade", "young_adult", "adult"]
AUDIENCE_PROXIMITY = {0: 1.0, 1: 0.6, 2: 0.3, 3: 0.1}


def _dot_product(a: list[float], b: list[float]) -> float:
    """Dot product of two vectors."""
    return sum(x * y for x, y in zip(a, b))


def _dbsf_normalize(scores: list[float]) -> list[float]:
    """
    Distribution-Based Score Fusion normalization.
    norm(x) = clip((x - μ) / σ, 0, 1) with σ floor of 0.1.
    """
    n = len(scores)
    if n == 0:
        return []
    if n == 1:
        return [1.0] if scores[0] > 0 else [0.0]

    mu = sum(scores) / n
    variance = sum((x - mu) ** 2 for x in scores) / n
    sigma = max(math.sqrt(variance), 0.1)

    return [max(0.0, min(1.0, (x - mu) / sigma)) for x in scores]


def compute_genre_score(
    ms_genre: str | None,
    agent_genres: list[str] | None,
    alias_map: dict[str, str],
    ms_emb: list[float] | None = None,
    agent_emb: list[float] | None = None,
) -> float:
    """Genre match score via genre_utils."""
    return genre_match_score(ms_genre, agent_genres, alias_map, ms_emb, agent_emb)


def compute_audience_score(
    ms_audiences: list[str] | None,
    agent_audiences: list[str] | None,
) -> float:
    """Audience proximity score based on hierarchy distance."""
    if not ms_audiences or not agent_audiences:
        return 0.0

    best = 0.0
    for ms_aud in ms_audiences:
        ms_key = ms_aud.lower().strip()
        ms_idx = _audience_index(ms_key)
        if ms_idx is None:
            continue
        for ag_aud in agent_audiences:
            ag_key = ag_aud.lower().strip()
            ag_idx = _audience_index(ag_key)
            if ag_idx is None:
                continue
            dist = abs(ms_idx - ag_idx)
            score = AUDIENCE_PROXIMITY.get(dist, 0.0)
            best = max(best, score)

    return best


def _audience_index(key: str) -> int | None:
    """Find index in AUDIENCE_ORDER, with common alias handling."""
    aliases = {
        "children's": 0, "childrens": 0, "children": 0, "picture_books": 0,
        "middle_grade": 1, "middle grade": 1, "mg": 1,
        "young_adult": 2, "young adult": 2, "ya": 2,
        "adult": 3, "new_adult": 3, "new adult": 3,
    }
    return aliases.get(key)


def compute_fts_score(
    manuscript: Manuscript,
    agent: Agent,
    db_session: Session,
) -> float | None:
    """
    PostgreSQL full-text search score using ts_rank_cd.
    Returns None on non-PostgreSQL backends.
    """
    try:
        dialect = db_session.bind.dialect.name
        if dialect != "postgresql":
            return None
    except Exception:
        return None

    from sqlalchemy import func, cast, text
    from sqlalchemy.dialects.postgresql import TSVECTOR as PG_TSVECTOR

    # Build query from manuscript fields
    parts = []
    if manuscript.genre:
        parts.append(manuscript.genre)
    if manuscript.comps:
        parts.extend(manuscript.comps)
    if hasattr(manuscript, "query_letter") and manuscript.query_letter:
        # Extract first 200 words for FTS query
        words = manuscript.query_letter.split()[:200]
        parts.append(" ".join(words))

    if not parts:
        return 0.0

    query_text = " | ".join(parts)

    try:
        result = db_session.execute(
            text(
                "SELECT ts_rank_cd(fts_vector, plainto_tsquery('english', :query)) "
                "FROM agents WHERE id = :agent_id"
            ),
            {"query": query_text, "agent_id": agent.id},
        ).scalar()
        return float(result) if result is not None else 0.0
    except Exception as exc:
        logger.warning("FTS query failed for agent %d: %s", agent.id, exc)
        return None


def compute_semantic_score(
    ms_embedding: list[float] | None,
    agent_embedding: list[float] | None,
) -> float:
    """Cosine similarity via dot product (vectors are L2-normalized)."""
    if not ms_embedding or not agent_embedding:
        return 0.0
    return max(0.0, _dot_product(ms_embedding, agent_embedding))


def score_candidates(
    manuscript: Manuscript,
    candidates: list[Agent],
    weights: MatchWeights | None = None,
    alias_map: dict[str, str] | None = None,
    db_session: Session | None = None,
) -> list[ScoredAgent]:
    """
    Compute 4 raw signals → DBSF normalize → weight → sort.
    Redistributes weights when FTS is unavailable.
    """
    if not candidates:
        return []

    if weights is None:
        weights = MatchWeights.from_env()
    if alias_map is None:
        alias_map = load_genre_aliases()

    ms_emb = manuscript.embedding_fulltext

    # Compute raw scores
    raw_genre: list[float] = []
    raw_audience: list[float] = []
    raw_fts: list[float | None] = []
    raw_semantic: list[float] = []
    agent_data: list[tuple[Agent, list[float] | None]] = []

    for agent in candidates:
        agent_emb = agent.embedding
        agent_data.append((agent, agent_emb))

        raw_genre.append(compute_genre_score(
            manuscript.genre, agent.genres, alias_map, ms_emb, agent_emb
        ))
        raw_audience.append(compute_audience_score(
            manuscript.audience, agent.audience
        ))
        if db_session is not None:
            raw_fts.append(compute_fts_score(manuscript, agent, db_session))
        else:
            raw_fts.append(None)
        raw_semantic.append(compute_semantic_score(ms_emb, agent_emb))

    # Determine FTS availability
    fts_available = any(s is not None for s in raw_fts)
    fts_values = [s if s is not None else 0.0 for s in raw_fts]

    # DBSF normalize each signal
    norm_genre = _dbsf_normalize(raw_genre)
    norm_audience = _dbsf_normalize(raw_audience)
    norm_fts = _dbsf_normalize(fts_values) if fts_available else [0.0] * len(candidates)
    norm_semantic = _dbsf_normalize(raw_semantic)

    # Weight redistribution
    available_signals = ["genre", "audience", "semantic"]
    if fts_available:
        available_signals.append("fts")
    effective_weights = weights.redistribute(available_signals)

    # Per-row A/B override support
    def _get_weights(ms: Manuscript) -> MatchWeights | None:
        overrides = {}
        if ms.genre_score_weight is not None:
            overrides["genre"] = ms.genre_score_weight
        if ms.fts_score_weight is not None:
            overrides["fts"] = ms.fts_score_weight
        if ms.semantic_score_weight is not None:
            overrides["semantic"] = ms.semantic_score_weight
        if ms.audience_score_weight is not None:
            overrides["audience"] = ms.audience_score_weight
        if overrides:
            w = MatchWeights(**{**{
                "genre": effective_weights.genre,
                "fts": effective_weights.fts,
                "semantic": effective_weights.semantic,
                "audience": effective_weights.audience,
            }, **overrides})
            ab_available = [s for s in available_signals if getattr(w, s) > 0]
            return w.redistribute(ab_available) if ab_available else w
        return None

    ab_weights = _get_weights(manuscript)
    w = ab_weights if ab_weights else effective_weights

    # Build ScoredAgent list
    results: list[ScoredAgent] = []
    for i, (agent, agent_emb) in enumerate(agent_data):
        breakdown = ScoreBreakdown(
            genre_score=raw_genre[i],
            audience_score=raw_audience[i],
            fts_score=fts_values[i],
            semantic_score=raw_semantic[i],
            genre_norm=norm_genre[i],
            audience_norm=norm_audience[i],
            fts_norm=norm_fts[i],
            semantic_norm=norm_semantic[i],
        )

        composite = (
            w.genre * norm_genre[i]
            + w.audience * norm_audience[i]
            + w.fts * norm_fts[i]
            + w.semantic * norm_semantic[i]
        )

        results.append(ScoredAgent(
            agent_id=agent.id,
            agent_name=agent.name,
            agency=agent.agency,
            composite_score=composite,
            scores=breakdown,
            embedding=agent_emb,
        ))

    results.sort(key=lambda x: x.composite_score, reverse=True)
    return results
