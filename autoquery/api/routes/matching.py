"""Core matching routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from autoquery.api.deps import (
    RateLimiter,
    get_current_user,
    get_embedding_model,
    get_optional_user,
    get_session_id,
)
from autoquery.api.schemas.agent import AgentPublic
from autoquery.api.schemas.matching import (
    ManuscriptInput,
    MatchResponse,
    MatchTagResponse,
    ScoreBreakdownResponse,
    ScoredAgentResponse,
)
from autoquery.database.db import get_db
from autoquery.database.models import (
    REVIEW_STATUS_APPROVED,
    Agent,
    Manuscript,
    MatchingResult,
    User,
)
from autoquery.embeddings.model import EmbeddingModel
from autoquery.embeddings.pipeline import (
    combine_manuscript_embeddings,
    embed_manuscript_fulltext,
    embed_manuscript_query_expanded,
    expand_query,
)
from autoquery.matching.genre_utils import load_genre_aliases
from autoquery.matching.phase1.pipeline import match, persist_results
from autoquery.matching.types import ScoredAgent

router = APIRouter(prefix="/api", tags=["matching"])

_match_rate_limit = RateLimiter(max_calls=10, period_seconds=3600, key_prefix="match")


def _build_match_response(
    manuscript_id: int,
    results: list[ScoredAgent],
    total_found: int,
    agents_by_id: dict[int, Agent],
) -> MatchResponse:
    """Convert ScoredAgent list into API response."""
    scored_responses = []
    for sa in results:
        agent = agents_by_id.get(sa.agent_id)
        if not agent:
            continue
        scored_responses.append(
            ScoredAgentResponse(
                agent=AgentPublic.model_validate(agent),
                composite_score=sa.composite_score,
                mmr_rank=sa.mmr_rank,
                match_tags=[
                    MatchTagResponse(dimension=t.dimension, indicator=t.indicator, label=t.label)
                    for t in sa.match_tags
                ],
                snippet=sa.snippet,
                scores=ScoreBreakdownResponse(
                    genre_score=sa.scores.genre_score,
                    fts_score=sa.scores.fts_score,
                    semantic_score=sa.scores.semantic_score,
                    audience_score=sa.scores.audience_score,
                ),
            )
        )
    return MatchResponse(
        manuscript_id=manuscript_id,
        results=scored_responses,
        total_found=total_found,
    )


@router.post("/match", response_model=MatchResponse)
async def run_match(
    body: ManuscriptInput,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
    session_id: str = Depends(get_session_id),
    embedding_model: EmbeddingModel = Depends(get_embedding_model),
    _rl: None = Depends(_match_rate_limit),
):
    output_size = 20 if user else 3

    # Create manuscript
    manuscript = Manuscript(
        user_id=user.id if user else None,
        session_id=session_id,
        title=f"{body.genre} manuscript",
        genre=body.genre,
        audience=[body.audience],
        comps=body.comps if body.comps else None,
        query_letter=body.query_letter or None,
        synopsis=body.synopsis or None,
    )
    db.add(manuscript)
    db.commit()
    db.refresh(manuscript)

    # Embed manuscript
    fulltext_emb = await embed_manuscript_fulltext(manuscript, embedding_model)
    manuscript.embedding_fulltext = fulltext_emb

    if manuscript.query_letter:
        keywords = await expand_query(manuscript.query_letter)
        query_expanded_emb = await embed_manuscript_query_expanded(keywords, embedding_model)
        manuscript.embedding_query_expanded = query_expanded_emb
        combined = combine_manuscript_embeddings(fulltext_emb, query_expanded_emb)
        manuscript.embedding_fulltext = combined
    db.commit()

    # Load approved agents
    agents = (
        db.query(Agent)
        .filter(Agent.review_status == REVIEW_STATUS_APPROVED)
        .all()
    )

    # Run matching (async, inline)
    all_results = await match(
        manuscript, agents, db_session=db,
        embedding_model=embedding_model, output_size=output_size,
    )

    # Persist all results
    if all_results:
        persist_results(manuscript.id, all_results, db)

    total_found = len(all_results)
    display_results = all_results[:output_size]

    agents_by_id = {a.id: a for a in agents}
    return _build_match_response(manuscript.id, display_results, total_found, agents_by_id)


@router.get("/results/{manuscript_id}", response_model=MatchResponse)
async def get_results(
    manuscript_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
    session_id: str = Depends(get_session_id),
):
    manuscript = db.query(Manuscript).filter(Manuscript.id == manuscript_id).first()
    if not manuscript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manuscript not found")

    # Verify ownership
    if user and manuscript.user_id == user.id:
        pass  # Authenticated owner
    elif manuscript.session_id == session_id:
        pass  # Anonymous owner via session cookie
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    output_size = 20 if user else 3

    stored = (
        db.query(MatchingResult)
        .filter(MatchingResult.manuscript_id == manuscript_id)
        .order_by(MatchingResult.mmr_rank.asc().nullslast())
        .limit(output_size)
        .all()
    )

    # Load agents for response building
    agent_ids = [r.agent_id for r in stored]
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all() if agent_ids else []
    agents_by_id = {a.id: a for a in agents}

    total = (
        db.query(MatchingResult)
        .filter(MatchingResult.manuscript_id == manuscript_id)
        .count()
    )

    results = []
    for r in stored:
        agent = agents_by_id.get(r.agent_id)
        if not agent:
            continue
        results.append(
            ScoredAgentResponse(
                agent=AgentPublic.model_validate(agent),
                composite_score=r.composite_score or 0.0,
                mmr_rank=r.mmr_rank,
                match_tags=[],
                snippet="",
                scores=ScoreBreakdownResponse(
                    genre_score=r.genre_score or 0.0,
                    fts_score=r.fts_score or 0.0,
                    semantic_score=r.semantic_score or 0.0,
                    audience_score=r.audience_score or 0.0,
                ),
            )
        )

    return MatchResponse(
        manuscript_id=manuscript_id,
        results=results,
        total_found=total,
    )


@router.get("/genres")
async def list_genres():
    """Return canonical genre list from genre_aliases.yaml."""
    alias_map = load_genre_aliases()
    # Canonical genres are the unique values in the alias map
    canonicals = sorted(set(alias_map.values()))
    return {"genres": canonicals}
