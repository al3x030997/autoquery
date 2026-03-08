"""
Tests for ProfileExtractor: Ollama-based agent profile extraction.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoquery.extractor.profile_extractor import ProfileExtractor
from autoquery.database.models import Agent, REVIEW_STATUS_PENDING, REVIEW_STATUS_EXTRACTION_FAILED


def _make_ollama_response(data: dict) -> dict:
    """Build a mock Ollama /api/generate response."""
    return {"response": json.dumps(data)}


VALID_PROFILE = {
    "name": "Jane Smith",
    "agency": "Smith Literary Agency",
    "genres": ["literary_fiction", "sci-fi", "memoir"],
    "keywords": ["diverse voices", "unreliable narrator", "found family", "atmospheric"],
    "audience": ["adult", "ya"],
    "hard_nos_keywords": ["erotica", "fan fiction"],
    "submission_req": {"query_letter": True, "pages": 10},
    "is_open": True,
    "wishlist_raw": "I'm looking for bold literary fiction with diverse voices.",
    "bio_raw": "Jane has been an agent for 15 years.",
    "hard_nos_raw": "I do not represent erotica or fan fiction.",
    "email": "jane@smithlit.com",
    "response_time": "6-8 weeks",
    "country": "US",
}


@pytest.fixture
def extractor():
    return ProfileExtractor(
        ollama_url="http://test:11434",
        model="test-model",
        genre_config_path="config/genre_aliases.yaml",
    )


def _mock_httpx_post(data: dict, status_code: int = 200):
    """Create a mock for httpx.AsyncClient.post that returns given data."""
    mock_response = MagicMock()  # Use MagicMock since httpx resp.json() is sync
    mock_response.status_code = status_code
    mock_response.json.return_value = _make_ollama_response(data)
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestProfileExtractor:
    @pytest.mark.asyncio
    async def test_successful_extraction(self, extractor, db_session):
        mock_client = _mock_httpx_post(VALID_PROFILE)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client):
            agent = await extractor.extract(
                clean_text="Jane Smith is a literary agent at Smith Literary Agency...",
                source_url="https://smithlit.com/agents/jane",
                quality_score=0.85,
                quality_action="extract",
                db=db_session,
            )

        assert agent is not None
        assert agent.name == "Jane Smith"
        assert agent.agency == "Smith Literary Agency"
        assert agent.review_status == REVIEW_STATUS_PENDING
        assert agent.quality_score == 0.85
        assert agent.quality_action == "extract"
        assert "literary_fiction" in agent.genres
        assert len(agent.keywords) >= 3
        assert agent.wishlist_raw is not None

    @pytest.mark.asyncio
    async def test_missing_name_fails(self, extractor, db_session):
        data = {**VALID_PROFILE, "name": ""}
        mock_client = _mock_httpx_post(data)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client):
            agent = await extractor.extract(
                clean_text="Some agent text",
                source_url="https://example.com/agent1",
                quality_score=0.7,
                quality_action="extract",
                db=db_session,
            )

        assert agent is not None
        assert agent.review_status == REVIEW_STATUS_EXTRACTION_FAILED

    @pytest.mark.asyncio
    async def test_missing_genres_fails(self, extractor, db_session):
        data = {**VALID_PROFILE, "genres": []}
        mock_client = _mock_httpx_post(data)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client):
            agent = await extractor.extract(
                clean_text="Some agent text",
                source_url="https://example.com/agent2",
                quality_score=0.7,
                quality_action="extract",
                db=db_session,
            )

        assert agent is not None
        assert agent.review_status == REVIEW_STATUS_EXTRACTION_FAILED

    @pytest.mark.asyncio
    async def test_few_keywords_fails(self, extractor, db_session):
        data = {**VALID_PROFILE, "keywords": ["one", "two"]}
        mock_client = _mock_httpx_post(data)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client):
            agent = await extractor.extract(
                clean_text="Some agent text",
                source_url="https://example.com/agent3",
                quality_score=0.7,
                quality_action="extract",
                db=db_session,
            )

        assert agent is not None
        assert agent.review_status == REVIEW_STATUS_EXTRACTION_FAILED

    @pytest.mark.asyncio
    async def test_json_parse_error(self, extractor, db_session):
        """Ollama returns garbage — handled gracefully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "not valid json at all {{{"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client):
            agent = await extractor.extract(
                clean_text="Some agent text",
                source_url="https://example.com/agent4",
                quality_score=0.7,
                quality_action="extract",
                db=db_session,
            )

        assert agent is not None
        assert agent.review_status == REVIEW_STATUS_EXTRACTION_FAILED

    @pytest.mark.asyncio
    async def test_input_truncation(self, extractor):
        long_text = " ".join(["word"] * 5000)
        truncated = extractor._truncate(long_text)
        assert len(truncated.split()) == 4000

    @pytest.mark.asyncio
    async def test_genre_canonicalization(self, extractor):
        genres = ["sci-fi", "Literary Fiction", "memoir", "unknown_genre"]
        result = extractor._canonicalize_genres(genres)
        assert "science_fiction" in result
        assert "literary_fiction" in result
        assert "memoir" in result
        assert "unknown_genre" in result  # passes through

    @pytest.mark.asyncio
    async def test_upsert_on_duplicate_url(self, extractor, db_session):
        """Same source_url → update not insert."""
        mock_client = _mock_httpx_post(VALID_PROFILE)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client):
            agent1 = await extractor.extract(
                clean_text="Text v1",
                source_url="https://example.com/agent-dup",
                quality_score=0.7,
                quality_action="extract",
                db=db_session,
            )

        updated_profile = {**VALID_PROFILE, "name": "Jane Updated"}
        mock_client2 = _mock_httpx_post(updated_profile)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client2):
            agent2 = await extractor.extract(
                clean_text="Text v2",
                source_url="https://example.com/agent-dup",
                quality_score=0.8,
                quality_action="extract",
                db=db_session,
            )

        assert agent1.id == agent2.id
        assert agent2.name == "Jane Updated"
        # Only one record in DB
        count = db_session.query(Agent).filter_by(profile_url="https://example.com/agent-dup").count()
        assert count == 1


class TestGenreCanonicalization:
    @pytest.fixture
    def extractor(self):
        return ProfileExtractor(
            ollama_url="http://test:11434",
            model="test-model",
            genre_config_path="config/genre_aliases.yaml",
        )

    def test_exact_match(self, extractor):
        result = extractor._canonicalize_genres(["literary_fiction"])
        assert result == ["literary_fiction"]

    def test_alias_match(self, extractor):
        result = extractor._canonicalize_genres(["sci-fi"])
        assert result == ["science_fiction"]

    def test_case_insensitive(self, extractor):
        result = extractor._canonicalize_genres(["YA"])
        assert result == ["young_adult"]

    def test_unknown_passthrough(self, extractor):
        result = extractor._canonicalize_genres(["steampunk"])
        assert result == ["steampunk"]

    def test_deduplication(self, extractor):
        result = extractor._canonicalize_genres(["sci-fi", "science_fiction", "SF"])
        assert result == ["science_fiction"]


class TestValidation:
    @pytest.fixture
    def extractor(self):
        return ProfileExtractor(
            ollama_url="http://test:11434",
            model="test-model",
        )

    def test_valid_data_passes(self, extractor):
        is_valid, errors = extractor._validate(VALID_PROFILE)
        assert is_valid
        assert errors == []

    def test_null_name_fails(self, extractor):
        is_valid, errors = extractor._validate({**VALID_PROFILE, "name": None})
        assert not is_valid
        assert any("name" in e for e in errors)

    def test_empty_genres_fails(self, extractor):
        is_valid, errors = extractor._validate({**VALID_PROFILE, "genres": []})
        assert not is_valid
        assert any("genre" in e for e in errors)

    def test_few_keywords_fails(self, extractor):
        is_valid, errors = extractor._validate({**VALID_PROFILE, "keywords": ["a"]})
        assert not is_valid
        assert any("keyword" in e for e in errors)
