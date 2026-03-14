"""Tests for matching pipeline orchestration."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from autoquery.database.models import (
    Agent, Manuscript, MatchingResult, User,
    REVIEW_STATUS_APPROVED,
)
from autoquery.matching.phase1.pipeline import match, persist_results, ALGORITHM_VERSION
from autoquery.matching.types import MatchWeights


def _make_agent(id, name="Agent", agency=None, genres=None, audience=None,
                keywords=None, embedding=None, is_open=True, opted_out=False,
                review_status=REVIEW_STATUS_APPROVED, hard_nos_keywords=None):
    agent = MagicMock(spec=Agent)
    agent.id = id
    agent.name = name
    agent.agency = agency
    agent.genres = genres or ["literary_fiction"]
    agent.audience = audience or ["adult"]
    agent.keywords = keywords or ["upmarket", "character-driven", "diverse"]
    agent.embedding = embedding
    agent.is_open = is_open
    agent.opted_out = opted_out
    agent.review_status = review_status
    agent.hard_nos_keywords = hard_nos_keywords
    return agent


def _make_manuscript(genre="literary_fiction", audience=None, embedding=None,
                     comps=None, query_letter=None):
    ms = MagicMock(spec=Manuscript)
    ms.id = 1
    ms.genre = genre
    ms.audience = audience or ["adult"]
    ms.embedding_fulltext = embedding or [0.5] * 3
    ms.comps = comps
    ms.query_letter = query_letter
    ms.genre_score_weight = None
    ms.fts_score_weight = None
    ms.semantic_score_weight = None
    ms.audience_score_weight = None
    return ms


class TestPipelineMatch:
    @pytest.mark.asyncio
    async def test_full_pipeline_returns_ranked(self):
        """Full pipeline without embedding model (no hard-nos check)."""
        ms = _make_manuscript(embedding=[1.0, 0.0, 0.0])
        agents = [
            _make_agent(1, name="Alice", genres=["literary_fiction"],
                        embedding=[0.9, 0.1, 0.0]),
            _make_agent(2, name="Bob", genres=["science_fiction"],
                        audience=["young_adult"], embedding=[0.1, 0.9, 0.0]),
            _make_agent(3, name="Carol", is_open=False),  # filtered out
        ]

        results = await match(ms, agents, output_size=10)

        assert len(results) == 2
        assert results[0].mmr_rank == 1
        assert results[0].agent_name == "Alice"
        # Embeddings should be dropped
        assert all(r.embedding is None for r in results)
        # Tags should be populated
        assert len(results[0].match_tags) > 0

    @pytest.mark.asyncio
    async def test_pipeline_algorithm_version_set(self):
        assert ALGORITHM_VERSION == "phase1-v1.0"


class TestPersistResults:
    def test_pipeline_persists_to_db(self, db_session):
        """persist_results writes correct scores to matching_results table."""
        # Create manuscript in DB
        ms = Manuscript(
            title="Test Novel",
            genre="literary_fiction",
            audience=["adult"],
        )
        db_session.add(ms)
        db_session.commit()
        db_session.refresh(ms)

        # Create agent in DB
        agent = Agent(
            name="Test Agent",
            profile_url="https://example.com/agent",
            genres=["literary_fiction"],
            keywords=["upmarket"],
            review_status=REVIEW_STATUS_APPROVED,
            is_open=True,
            opted_out=False,
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        # Build a ScoredAgent
        from autoquery.matching.types import ScoredAgent, ScoreBreakdown
        scored = ScoredAgent(
            agent_id=agent.id,
            agent_name=agent.name,
            agency=None,
            composite_score=0.85,
            scores=ScoreBreakdown(
                genre_score=1.0, audience_score=1.0,
                fts_score=0.0, semantic_score=0.7,
            ),
            mmr_rank=1,
        )

        records = persist_results(ms.id, [scored], db_session)

        assert len(records) == 1
        mr = db_session.query(MatchingResult).first()
        assert mr is not None
        assert mr.manuscript_id == ms.id
        assert mr.agent_id == agent.id
        assert mr.composite_score == 0.85
        assert mr.genre_score == 1.0
        assert mr.mmr_rank == 1
        assert mr.algorithm_version == ALGORITHM_VERSION
