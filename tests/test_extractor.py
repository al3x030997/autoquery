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


class TestExtractSection:
    @pytest.fixture
    def extractor(self):
        return ProfileExtractor(
            ollama_url="http://test:11434",
            model="test-model",
        )

    def test_splits_by_agent_name(self, extractor):
        text = (
            "About Our Agents\n\n"
            "Alice Johnson is a literary agent who loves fantasy and science fiction. "
            "She is looking for epic worldbuilding and diverse voices.\n\n"
            "Bob Martinez represents thriller and mystery authors. "
            "He wants fast-paced plots with unreliable narrators.\n\n"
            "Carol Chen focuses on romance and women's fiction. "
            "She is drawn to emotional depth and family sagas."
        )
        all_names = ["Alice Johnson", "Bob Martinez", "Carol Chen"]

        alice_section = extractor._extract_section(text, "Alice Johnson", all_names=all_names)
        assert "Alice Johnson" in alice_section
        assert "epic worldbuilding" in alice_section
        assert "Bob Martinez" not in alice_section

        bob_section = extractor._extract_section(text, "Bob Martinez", all_names=all_names)
        assert "Bob Martinez" in bob_section
        assert "fast-paced plots" in bob_section
        assert "Carol Chen" not in bob_section

        carol_section = extractor._extract_section(text, "Carol Chen", all_names=all_names)
        assert "Carol Chen" in carol_section
        assert "family sagas" in carol_section

    def test_section_hint_fallback(self, extractor):
        text = "Team Members\n\nShe loves fantasy and sci-fi. Looking for bold voices.\n\nHe represents thrillers."
        section = extractor._extract_section(
            text, "Unknown Agent", section_hint="She loves fantasy",
            all_names=["Unknown Agent"],
        )
        assert "fantasy" in section

    def test_returns_full_text_if_not_found(self, extractor):
        text = "Some page text about agents."
        section = extractor._extract_section(text, "Nonexistent Person", all_names=[])
        assert section == text


class TestValidateGrounding:
    @pytest.fixture
    def extractor(self):
        return ProfileExtractor(
            ollama_url="http://test:11434",
            model="test-model",
        )

    def test_name_present_no_warnings(self, extractor):
        data = {"name": "Jane Smith", "email": "jane@example.com"}
        source = "Jane Smith is a literary agent at Example Agency. Contact: jane@example.com"
        warnings = extractor._validate_grounding(data, source)
        assert len(warnings) == 0
        assert "_grounding_failed" not in data

    def test_name_absent_sets_grounding_failed(self, extractor):
        data = {"name": "Sarah Johnson"}
        source = "Alice Williams is a literary agent specializing in fantasy."
        warnings = extractor._validate_grounding(data, source)
        assert any("name" in w for w in warnings)
        assert data.get("_grounding_failed") is True

    def test_email_present_kept(self, extractor):
        data = {"name": "Jane Smith", "email": "jane@smithlit.com"}
        source = "Jane Smith. Email: jane@smithlit.com"
        extractor._validate_grounding(data, source)
        assert data["email"] == "jane@smithlit.com"

    def test_email_absent_removed(self, extractor):
        data = {"name": "Jane Smith", "email": "fake@hallucinated.com"}
        source = "Jane Smith is a literary agent."
        warnings = extractor._validate_grounding(data, source)
        assert data["email"] is None
        assert any("email" in w for w in warnings)

    def test_wishlist_low_overlap_warns(self, extractor):
        data = {
            "name": "Jane Smith",
            "wishlist_raw": "I am seeking manuscripts about quantum physics and interdimensional travel with complex mathematical proofs and alien civilizations exploring deep space",
        }
        source = "Jane Smith represents romance and women's fiction. She loves emotional stories with strong heroines."
        warnings = extractor._validate_grounding(data, source)
        assert any("overlap" in w for w in warnings)

    def test_wishlist_high_overlap_no_warning(self, extractor):
        data = {
            "name": "Jane Smith",
            "wishlist_raw": "I am looking for bold literary fiction with diverse voices and unreliable narrators set in contemporary settings",
        }
        source = "Jane Smith is looking for bold literary fiction with diverse voices and unreliable narrators set in contemporary settings and beyond."
        warnings = extractor._validate_grounding(data, source)
        assert not any("overlap" in w for w in warnings)


class TestValidateWishlist:
    @pytest.fixture
    def extractor(self):
        return ProfileExtractor(
            ollama_url="http://test:11434",
            model="test-model",
        )

    def test_short_wishlist_warns(self, extractor):
        data = {"wishlist_raw": "fantasy"}
        warnings = extractor._validate_wishlist(data, section_word_count=500)
        assert len(warnings) == 1
        assert "suspiciously short" in warnings[0]

    def test_adequate_wishlist_no_warning(self, extractor):
        data = {"wishlist_raw": " ".join(["word"] * 50)}
        warnings = extractor._validate_wishlist(data, section_word_count=500)
        assert len(warnings) == 0

    def test_short_section_no_warning(self, extractor):
        data = {"wishlist_raw": "fantasy"}
        warnings = extractor._validate_wishlist(data, section_word_count=50)
        assert len(warnings) == 0


class TestTwoPassExtractMulti:
    @pytest.fixture
    def extractor(self):
        return ProfileExtractor(
            ollama_url="http://test:11434",
            model="test-model",
            genre_config_path="config/genre_aliases.yaml",
        )

    @pytest.mark.asyncio
    async def test_two_pass_calls(self, extractor, db_session):
        """Roster call + 3 per-agent calls = 4 total Ollama calls."""
        roster_response = {
            "agency_info": {"name": "Test Agency", "exclusive_query": True, "response_time": "2 months"},
            "agents": [
                {"name": "Alice Johnson", "section_hint": "Alice loves fantasy"},
                {"name": "Bob Martinez", "section_hint": "Bob represents thrillers"},
                {"name": "Carol Chen", "section_hint": "Carol focuses on romance"},
            ],
        }

        agent_responses = [
            {
                "name": "Alice Johnson", "agency": "Test Agency",
                "genres": ["fantasy"], "keywords": ["epic worldbuilding", "diverse voices", "magic systems"],
                "audience": ["adult"], "hard_nos_keywords": [],
                "is_open": True, "wishlist_raw": "I love epic fantasy with diverse voices and complex magic systems.",
                "bio_raw": "Alice has been agenting for 10 years.", "hard_nos_raw": None,
                "email": "alice@testagency.com",
            },
            {
                "name": "Bob Martinez", "agency": "Test Agency",
                "genres": ["thriller", "mystery"], "keywords": ["fast-paced", "unreliable narrator", "dark secrets"],
                "audience": ["adult"], "hard_nos_keywords": ["erotica"],
                "is_open": True, "wishlist_raw": "Looking for fast-paced thrillers with unreliable narrators and dark secrets.",
                "bio_raw": "Bob joined the agency in 2020.", "hard_nos_raw": "No erotica.",
                "email": "bob@testagency.com",
            },
            {
                "name": "Carol Chen", "agency": "Test Agency",
                "genres": ["romance", "womens_fiction"], "keywords": ["emotional depth", "family sagas", "strong heroines"],
                "audience": ["adult"], "hard_nos_keywords": [],
                "is_open": True, "wishlist_raw": "Carol focuses on romance with emotional depth and family sagas.",
                "bio_raw": "Carol is passionate about women's stories.", "hard_nos_raw": None,
                "email": "carol@testagency.com",
            },
        ]

        page_text = (
            "Test Agency - Our Agents\n\n"
            "Alice Johnson loves fantasy and science fiction. She is looking for epic worldbuilding "
            "and diverse voices and complex magic systems. Contact: alice@testagency.com\n\n"
            "Bob Martinez represents thrillers and mystery. He wants fast-paced thrillers with "
            "unreliable narrators and dark secrets. No erotica. Contact: bob@testagency.com\n\n"
            "Carol Chen focuses on romance and women's fiction. She is drawn to emotional depth "
            "and family sagas and strong heroines. Contact: carol@testagency.com"
        )

        call_count = 0

        def _make_response(data):
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"response": json.dumps(data)}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        async def _mock_post(*args, **kwargs):
            nonlocal call_count
            prompt = kwargs.get("json", {}).get("prompt", "")
            system = kwargs.get("json", {}).get("system", "")

            if "list of literary agents" in prompt or "ROSTER" in system.upper():
                # Pass 1: roster call
                resp = _make_response(roster_response)
            else:
                # Pass 2: per-agent calls (in order)
                idx = min(call_count - 1, len(agent_responses) - 1)
                resp = _make_response(agent_responses[idx])
            call_count += 1
            return resp

        mock_client = AsyncMock()
        mock_client.post = _mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("autoquery.extractor.profile_extractor.httpx.AsyncClient", return_value=mock_client):
            agents = await extractor.extract_multi(
                clean_text=page_text,
                source_url="https://testagency.com/about",
                quality_score=0.8,
                quality_action="extract",
                db=db_session,
            )

        # 1 roster call + 3 per-agent calls = 4 total
        assert call_count == 4
        assert len(agents) == 3

        # Each agent should have non-empty wishlist
        for agent in agents:
            assert agent.wishlist_raw is not None
            assert len(agent.wishlist_raw.split()) > 5

        # Agency should be set
        for agent in agents:
            assert agent.agency == "Test Agency"
            assert agent.agency_id is not None
