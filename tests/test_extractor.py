"""Tests for ProfileExtractor with the L1 Note-Taker prompt (v2.0)."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoquery.extractor.profile_extractor import ProfileExtractor
from autoquery.database.models import Agent, REVIEW_STATUS_PENDING


SAMPLE_NOTES = (Path(__file__).parent / "fixtures" / "note_taker_sample.txt").read_text()


@pytest.fixture
def extractor():
    return ProfileExtractor(
        ollama_url="http://test:11434",
        model="test-model",
        extractor_backend="ollama",
    )


def _mock_ollama(text: str):
    """Build a MagicMock httpx client that returns `text` from /api/generate."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"response": text}
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


SOURCE_TEXT = (
    "Aashna Avachat — Neighborhood Literary Agency. "
    "Email: aashna@neighborhoodlit.com. "
    "I'm currently open and accepting queries via QueryTracker. "
    "Looking for picture books, young adult, and adult fiction with diverse voices."
)


class TestNoteTakerExtraction:
    @pytest.mark.asyncio
    async def test_successful_extraction(self, extractor, db_session):
        client = _mock_ollama(SAMPLE_NOTES)
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            agent = await extractor.extract(
                clean_text=SOURCE_TEXT,
                source_url="https://neighborhoodlit.com/aashna",
                quality_score=0.9,
                quality_action="extract",
                db=db_session,
            )

        assert agent is not None
        assert agent.name == "Aashna Avachat"
        assert agent.agency == "Neighborhood Literary Agency"
        assert agent.email == "aashna@neighborhoodlit.com"
        assert agent.is_open is True
        assert agent.review_status == REVIEW_STATUS_PENDING
        assert agent.prompt_version == "2.0"

    @pytest.mark.asyncio
    async def test_profile_notes_persisted(self, extractor, db_session):
        client = _mock_ollama(SAMPLE_NOTES)
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            agent = await extractor.extract(
                clean_text=SOURCE_TEXT,
                source_url="https://neighborhoodlit.com/aashna",
                quality_score=0.9, quality_action="extract", db=db_session,
            )
        notes = agent.profile_notes
        assert notes["identity"]["name"] == "Aashna Avachat"
        labels = [s["label"] for s in notes["preference_sections"]]
        assert "Picture Books" in labels and "Young Adult" in labels and "Adult" in labels
        assert "sexual violence on the page" in notes["hard_nos"]["content"]
        assert agent.profile_notes_raw == SAMPLE_NOTES

    @pytest.mark.asyncio
    async def test_legacy_columns_projected(self, extractor, db_session):
        """Until the matcher is rewritten, flat columns must still be populated."""
        client = _mock_ollama(SAMPLE_NOTES)
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            agent = await extractor.extract(
                clean_text=SOURCE_TEXT,
                source_url="https://neighborhoodlit.com/aashna",
                quality_score=0.9, quality_action="extract", db=db_session,
            )
        assert "picture_books" in agent.audience
        assert "young_adult" in agent.audience
        assert "adult" in agent.audience
        assert any("romance" in g.lower() for g in agent.genres_raw)
        assert "sexual violence on the page" in agent.hard_nos_keywords
        assert "poetry collections" in agent.hard_nos_keywords
        assert "found family" in agent.keywords
        assert agent.wishlist_raw == SAMPLE_NOTES

    @pytest.mark.asyncio
    async def test_grounding_rejects_hallucinated_name(self, extractor, db_session):
        client = _mock_ollama(SAMPLE_NOTES)
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            agent = await extractor.extract(
                clean_text="An unrelated agency page about somebody else entirely.",
                source_url="https://example.com/x",
                quality_score=0.5, quality_action="extract", db=db_session,
            )
        assert agent is None

    @pytest.mark.asyncio
    async def test_missing_identity_rejected(self, extractor, db_session):
        client = _mock_ollama("STEP 4: HARD NOS\n--------\n- nothing\n")
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            agent = await extractor.extract(
                clean_text=SOURCE_TEXT,
                source_url="https://example.com/y",
                quality_score=0.5, quality_action="extract", db=db_session,
            )
        assert agent is None

    @pytest.mark.asyncio
    async def test_client_bio_skipped(self, extractor, db_session):
        client_text = "She is represented by Jane Smith. Her agent is Jane Smith of XYZ Agency."
        client = _mock_ollama(SAMPLE_NOTES)
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            agent = await extractor.extract(
                clean_text=client_text,
                source_url="https://example.com/client",
                quality_score=0.5, quality_action="extract", db=db_session,
            )
        assert agent is None

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self, extractor, db_session):
        client = AsyncMock()
        client.post = AsyncMock(side_effect=RuntimeError("Ollama down"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            agent = await extractor.extract(
                clean_text=SOURCE_TEXT,
                source_url="https://example.com/z",
                quality_score=0.5, quality_action="extract", db=db_session,
            )
        assert agent is None


class TestUpsert:
    @pytest.mark.asyncio
    async def test_upsert_by_profile_url(self, extractor, db_session):
        client = _mock_ollama(SAMPLE_NOTES)
        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=client):
            a1 = await extractor.extract(SOURCE_TEXT, "https://nl.com/aashna", 0.9, "extract", db_session)
            a2 = await extractor.extract(SOURCE_TEXT, "https://nl.com/aashna", 0.95, "extract", db_session)
        assert a1.id == a2.id
        assert db_session.query(Agent).count() == 1
