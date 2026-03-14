"""Performance regression tests."""
import time

import pytest
from unittest.mock import MagicMock

from autoquery.database.models import Agent, Manuscript, REVIEW_STATUS_APPROVED
from autoquery.matching.phase1.pipeline import match
from autoquery.matching.phase1.reranker import mmr_rerank
from autoquery.matching.phase1.scorer import score_candidates
from autoquery.matching.types import ScoreBreakdown, ScoredAgent


def _make_mock_agent(i, dim=3):
    agent = MagicMock(spec=Agent)
    agent.id = i
    agent.name = f"Agent {i}"
    agent.agency = f"Agency {i % 20}"
    agent.genres = ["literary_fiction"] if i % 2 == 0 else ["science_fiction"]
    agent.audience = ["adult"]
    agent.keywords = ["keyword1", "keyword2"]
    agent.embedding = [float(i % dim) / dim] * dim
    agent.is_open = True
    agent.opted_out = False
    agent.review_status = REVIEW_STATUS_APPROVED
    agent.hard_nos_keywords = None
    return agent


def _make_mock_manuscript(dim=3):
    ms = MagicMock(spec=Manuscript)
    ms.id = 1
    ms.genre = "literary_fiction"
    ms.audience = ["adult"]
    ms.embedding_fulltext = [0.5] * dim
    ms.comps = None
    ms.query_letter = None
    ms.genre_score_weight = None
    ms.fts_score_weight = None
    ms.semantic_score_weight = None
    ms.audience_score_weight = None
    return ms


@pytest.mark.slow
@pytest.mark.asyncio
async def test_pipeline_200_agents_under_3s():
    """Full pipeline with 200 agents should complete under 3s."""
    ms = _make_mock_manuscript()
    agents = [_make_mock_agent(i) for i in range(200)]

    start = time.perf_counter()
    results = await match(ms, agents, output_size=20)
    elapsed = time.perf_counter() - start

    assert len(results) <= 20
    assert elapsed < 3.0, f"Pipeline took {elapsed:.2f}s (limit: 3s)"


@pytest.mark.slow
def test_scorer_1000_agents_under_5s():
    """Scoring 1000 agents should complete under 5s."""
    ms = _make_mock_manuscript()
    agents = [_make_mock_agent(i) for i in range(1000)]

    start = time.perf_counter()
    results = score_candidates(ms, agents)
    elapsed = time.perf_counter() - start

    assert len(results) == 1000
    assert elapsed < 5.0, f"Scorer took {elapsed:.2f}s (limit: 5s)"


@pytest.mark.slow
def test_mmr_rerank_50_under_500ms():
    """MMR reranking 50 candidates should complete under 500ms."""
    candidates = []
    for i in range(50):
        sa = ScoredAgent(
            agent_id=i,
            agent_name=f"Agent {i}",
            agency=f"Agency {i % 10}",
            composite_score=1.0 - i * 0.01,
            scores=ScoreBreakdown(),
            embedding=[float(i % 3) / 3.0] * 3,
        )
        candidates.append(sa)

    start = time.perf_counter()
    results = mmr_rerank(candidates, output_size=20)
    elapsed = time.perf_counter() - start

    assert len(results) <= 20
    assert elapsed < 0.5, f"MMR took {elapsed * 1000:.1f}ms (limit: 500ms)"
