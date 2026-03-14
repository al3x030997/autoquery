"""Edge case tests for the matching pipeline."""
import pytest
from unittest.mock import MagicMock

from autoquery.database.models import Agent, Manuscript, REVIEW_STATUS_APPROVED
from autoquery.matching.phase1.pipeline import match
from autoquery.matching.types import MatchWeights


_SENTINEL = object()


def _make_agent(id, name="Agent", agency=None, genres=_SENTINEL, audience=_SENTINEL,
                keywords=_SENTINEL, embedding=None, is_open=True, opted_out=False,
                review_status=REVIEW_STATUS_APPROVED, hard_nos_keywords=None):
    agent = MagicMock(spec=Agent)
    agent.id = id
    agent.name = name
    agent.agency = agency
    agent.genres = ["literary_fiction"] if genres is _SENTINEL else genres
    agent.audience = ["adult"] if audience is _SENTINEL else audience
    agent.keywords = ["upmarket", "character-driven", "diverse"] if keywords is _SENTINEL else keywords
    agent.embedding = embedding
    agent.is_open = is_open
    agent.opted_out = opted_out
    agent.review_status = review_status
    agent.hard_nos_keywords = hard_nos_keywords
    return agent


def _make_manuscript(genre="literary_fiction", audience=_SENTINEL, embedding=_SENTINEL,
                     comps=None, query_letter=None):
    ms = MagicMock(spec=Manuscript)
    ms.id = 1
    ms.genre = genre
    ms.audience = ["adult"] if audience is _SENTINEL else audience
    ms.embedding_fulltext = [0.5] * 3 if embedding is _SENTINEL else embedding
    ms.comps = comps
    ms.query_letter = query_letter
    ms.genre_score_weight = None
    ms.fts_score_weight = None
    ms.semantic_score_weight = None
    ms.audience_score_weight = None
    return ms


@pytest.mark.asyncio
async def test_manuscript_no_genre():
    """genre=None should produce genre_score=0, no crash."""
    ms = _make_manuscript(genre=None)
    agents = [_make_agent(1, embedding=[0.5] * 3)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1
    assert results[0].scores.genre_score == 0.0


@pytest.mark.asyncio
async def test_manuscript_empty_comps():
    """comps=[] should be handled gracefully."""
    ms = _make_manuscript(comps=[])
    agents = [_make_agent(1, embedding=[0.5] * 3)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_manuscript_no_query_letter():
    """query_letter=None should not crash the pipeline."""
    ms = _make_manuscript(query_letter=None)
    agents = [_make_agent(1)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_all_agents_filtered_out():
    """All is_open=False should return empty list."""
    ms = _make_manuscript()
    agents = [
        _make_agent(1, is_open=False),
        _make_agent(2, is_open=False),
    ]
    results = await match(ms, agents, output_size=10)
    assert results == []


@pytest.mark.asyncio
async def test_single_agent_in_db():
    """DBSF with n=1 should not cause division errors."""
    ms = _make_manuscript()
    agents = [_make_agent(1)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_agent_no_keywords():
    """keywords=None should produce snippet="" without crash."""
    ms = _make_manuscript()
    agents = [_make_agent(1, keywords=None)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1
    assert isinstance(results[0].snippet, str)


@pytest.mark.asyncio
async def test_agent_no_embedding():
    """embedding=None should produce semantic_score=0."""
    ms = _make_manuscript(embedding=[1.0, 0.0, 0.0])
    agents = [_make_agent(1, embedding=None)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1
    assert results[0].scores.semantic_score == 0.0


@pytest.mark.asyncio
async def test_agent_no_genres():
    """genres=None should produce genre_score=0."""
    ms = _make_manuscript()
    agents = [_make_agent(1, genres=None)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1
    assert results[0].scores.genre_score == 0.0


@pytest.mark.asyncio
async def test_agent_no_audience():
    """audience=None should produce audience_score=0."""
    ms = _make_manuscript()
    agents = [_make_agent(1, audience=None)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1
    assert results[0].scores.audience_score == 0.0


@pytest.mark.asyncio
async def test_all_zero_scores():
    """All signals 0 should produce composite=0 without crash."""
    ms = _make_manuscript(genre=None, audience=None, embedding=None)
    agents = [_make_agent(1, genres=None, audience=None, embedding=None, keywords=None)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1
    assert results[0].composite_score == 0.0


@pytest.mark.asyncio
async def test_duplicate_genres_in_agent():
    """Duplicate genres should not cause double-counting."""
    ms = _make_manuscript(genre="literary_fiction")
    agents = [_make_agent(1, genres=["literary_fiction", "literary_fiction"])]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1
    # Genre score should be same as single occurrence (exact match = 1.0)
    assert results[0].scores.genre_score == 1.0


@pytest.mark.asyncio
async def test_very_long_query_letter():
    """10K words should not crash the pipeline."""
    long_text = " ".join(["word"] * 10000)
    ms = _make_manuscript(query_letter=long_text)
    agents = [_make_agent(1)]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_ab_weight_override():
    """Per-manuscript weights should be applied."""
    ms = _make_manuscript()
    ms.genre_score_weight = 1.0
    ms.fts_score_weight = 0.0
    ms.semantic_score_weight = 0.0
    ms.audience_score_weight = 0.0

    agents = [
        _make_agent(1, genres=["literary_fiction"]),
        _make_agent(2, genres=["science_fiction"]),
    ]
    results = await match(ms, agents, output_size=10)
    assert len(results) == 2
    # With genre weight=1.0, the lit fic agent should rank first
    assert results[0].agent_name == agents[0].name
