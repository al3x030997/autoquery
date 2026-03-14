"""Tests for embedding model and pipeline (mocked Ollama, no real model needed)."""

import json
import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoquery.database.models import Agent, Manuscript, REVIEW_STATUS_APPROVED
from autoquery.embeddings.model import OllamaEmbeddingModel, _l2_normalize
from autoquery.embeddings.pipeline import (
    AGENT_PREFIX,
    MANUSCRIPT_PREFIX,
    FULLTEXT_WEIGHT,
    QUERY_WEIGHT,
    combine_manuscript_embeddings,
    embed_agent,
    embed_manuscript_fulltext,
    embed_manuscript_query_expanded,
    expand_query,
    recompute_all_agent_embeddings,
)


DIMS = 1024


def _fake_vector(seed: float = 1.0, dims: int = DIMS) -> list[float]:
    """Return a non-normalized vector of given dims."""
    return [seed * (i + 1) for i in range(dims)]


def _l2_norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def _mock_ollama_response(vector: list[float]):
    """Build a mock httpx response for /api/embeddings."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"embedding": vector}
    return resp


class _FakeModel:
    """Fake EmbeddingModel that returns deterministic vectors."""

    dimensions = DIMS

    def __init__(self):
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        # Return a normalized vector based on call count
        raw = [float(len(self.calls) + i) for i in range(DIMS)]
        return _l2_normalize(raw)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


# ── Model tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ollama_embed():
    """OllamaEmbeddingModel calls /api/embeddings and normalizes result."""
    raw_vec = _fake_vector(0.5)
    model = OllamaEmbeddingModel(
        model_name="bge-large-en-v1.5",
        ollama_url="http://test:11434",
        dimensions=DIMS,
    )

    mock_resp = _mock_ollama_response(raw_vec)
    with patch("autoquery.embeddings.model.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await model.embed("test text")

    assert len(result) == DIMS
    assert abs(_l2_norm(result) - 1.0) < 1e-6
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/api/embeddings" in call_args[0][0]
    assert call_args[1]["json"]["prompt"] == "test text"


@pytest.mark.asyncio
async def test_dimension_validation():
    """Wrong dimension count raises ValueError."""
    wrong_vec = [1.0] * 768  # nomic-embed-text dims, not 1024
    model = OllamaEmbeddingModel(
        model_name="wrong-model",
        ollama_url="http://test:11434",
        dimensions=DIMS,
    )

    mock_resp = _mock_ollama_response(wrong_vec)
    with patch("autoquery.embeddings.model.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(ValueError, match="Expected 1024 dimensions, got 768"):
            await model.embed("test text")


@pytest.mark.asyncio
async def test_embed_batch():
    """embed_batch processes multiple texts sequentially."""
    raw_vec = _fake_vector(1.0)
    model = OllamaEmbeddingModel(
        model_name="bge-large-en-v1.5",
        ollama_url="http://test:11434",
        dimensions=DIMS,
    )

    mock_resp = _mock_ollama_response(raw_vec)
    with patch("autoquery.embeddings.model.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        results = await model.embed_batch(["text1", "text2", "text3"])

    assert len(results) == 3
    for vec in results:
        assert len(vec) == DIMS
        assert abs(_l2_norm(vec) - 1.0) < 1e-6


# ── Pipeline tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_embed_agent_from_raw_text():
    """embed_agent uses wishlist_raw + bio_raw with AGENT_PREFIX."""
    agent = Agent(
        id=1,
        name="Test Agent",
        profile_url="http://example.com/agent",
        wishlist_raw="I love literary fiction",
        bio_raw="20 years in publishing",
    )
    model = _FakeModel()
    vec = await embed_agent(agent, model)

    assert len(vec) == DIMS
    assert abs(_l2_norm(vec) - 1.0) < 1e-6
    assert len(model.calls) == 1
    assert model.calls[0].startswith(AGENT_PREFIX)
    assert "literary fiction" in model.calls[0]
    assert "20 years" in model.calls[0]


@pytest.mark.asyncio
async def test_embed_agent_fallback_keywords():
    """When no raw text, falls back to keywords."""
    agent = Agent(
        id=2,
        name="Keywords Agent",
        profile_url="http://example.com/agent2",
        wishlist_raw=None,
        bio_raw=None,
        keywords=["thriller", "suspense", "mystery"],
    )
    model = _FakeModel()
    vec = await embed_agent(agent, model)

    assert len(vec) == DIMS
    assert "thriller" in model.calls[0]


@pytest.mark.asyncio
async def test_embed_manuscript_fulltext():
    """embed_manuscript_fulltext combines all fields with MANUSCRIPT_PREFIX."""
    ms = Manuscript(
        id=1,
        title="My Novel",
        genre="Literary Fiction",
        audience=["Adult"],
        comps=["Normal People", "Beautiful World"],
        query_letter="Dear Agent, my novel is about...",
        synopsis="A story about...",
    )
    model = _FakeModel()
    vec = await embed_manuscript_fulltext(ms, model)

    assert len(vec) == DIMS
    assert abs(_l2_norm(vec) - 1.0) < 1e-6
    assert model.calls[0].startswith(MANUSCRIPT_PREFIX)
    assert "Literary Fiction" in model.calls[0]
    assert "Normal People" in model.calls[0]
    assert "Dear Agent" in model.calls[0]


@pytest.mark.asyncio
async def test_query_expansion():
    """expand_query calls Ollama /api/generate and extracts keywords."""
    keywords = ["upmarket", "literary", "family drama", "debut",
                "character-driven", "book club", "domestic", "emotional",
                "contemporary", "women's fiction", "relationships", "identity"]
    ollama_response = {"response": json.dumps({"keywords": keywords})}

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = ollama_response

    with patch("autoquery.embeddings.pipeline.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await expand_query(
            "Dear Agent, my novel...",
            ollama_url="http://test:11434",
            llm_model="llama3",
        )

    assert "upmarket" in result
    assert "literary" in result
    # Should be comma-separated
    assert ", " in result


@pytest.mark.asyncio
async def test_embed_manuscript_query_expanded():
    """Query-expanded embedding uses AGENT_PREFIX (cross-space matching)."""
    model = _FakeModel()
    vec = await embed_manuscript_query_expanded("upmarket, literary, drama", model)

    assert len(vec) == DIMS
    assert model.calls[0].startswith(AGENT_PREFIX)


def test_combine_embeddings():
    """70/30 weighted combination is L2-normalized."""
    fulltext = _l2_normalize(_fake_vector(1.0))
    query_exp = _l2_normalize(_fake_vector(2.0))

    combined = combine_manuscript_embeddings(fulltext, query_exp)

    assert len(combined) == DIMS
    assert abs(_l2_norm(combined) - 1.0) < 1e-6

    # Verify weights: manually compute expected
    expected_raw = [
        FULLTEXT_WEIGHT * f + QUERY_WEIGHT * q
        for f, q in zip(fulltext, query_exp)
    ]
    expected = _l2_normalize(expected_raw)
    for a, b in zip(combined, expected):
        assert abs(a - b) < 1e-10


@pytest.mark.asyncio
async def test_recompute_all(db_session):
    """recompute_all_agent_embeddings processes approved agents."""
    # Create test agents
    a1 = Agent(
        name="Agent One",
        profile_url="http://example.com/a1",
        review_status=REVIEW_STATUS_APPROVED,
        wishlist_raw="I want literary fiction",
    )
    a2 = Agent(
        name="Agent Two",
        profile_url="http://example.com/a2",
        review_status=REVIEW_STATUS_APPROVED,
        wishlist_raw="I want thrillers",
    )
    a3 = Agent(
        name="Agent Pending",
        profile_url="http://example.com/a3",
        review_status="pending",
        wishlist_raw="I want romance",
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    model = _FakeModel()
    count = await recompute_all_agent_embeddings(db_session, model)

    assert count == 2  # Only approved agents
    assert len(model.calls) == 2

    # Verify embeddings were stored (as text in SQLite)
    db_session.refresh(a1)
    db_session.refresh(a2)
    db_session.refresh(a3)
    assert a1.embedding is not None
    assert a2.embedding is not None
    assert a3.embedding is None
