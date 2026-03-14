"""Tests for matching Layer 4: explainability."""
import pytest
from unittest.mock import MagicMock

from autoquery.database.models import Agent, Manuscript
from autoquery.matching.phase1.explainer import compute_match_tags, generate_snippet
from autoquery.matching.types import ScoreBreakdown


def _make_agent(genres=None, audience=None, keywords=None):
    agent = MagicMock(spec=Agent)
    agent.genres = genres or []
    agent.audience = audience or []
    agent.keywords = keywords or []
    return agent


def _make_manuscript(genre=None, audience=None, comps=None):
    ms = MagicMock(spec=Manuscript)
    ms.genre = genre
    ms.audience = audience
    ms.comps = comps
    return ms


class TestGenreTag:
    def test_exact_match(self):
        alias_map = {"literary_fiction": "literary_fiction"}
        ms = _make_manuscript(genre="literary_fiction")
        agent = _make_agent(genres=["literary_fiction"])
        scores = ScoreBreakdown(genre_score=1.0)
        tags = compute_match_tags(ms, agent, scores, alias_map)
        genre_tags = [t for t in tags if t.dimension == "genre"]
        assert genre_tags[0].indicator == "exact"
        assert "\u2713" in genre_tags[0].label

    def test_alias_match(self):
        alias_map = {"lit fic": "literary_fiction", "literary_fiction": "literary_fiction"}
        ms = _make_manuscript(genre="lit fic")
        agent = _make_agent(genres=["literary_fiction"])
        scores = ScoreBreakdown(genre_score=0.85)
        tags = compute_match_tags(ms, agent, scores, alias_map)
        genre_tags = [t for t in tags if t.dimension == "genre"]
        assert genre_tags[0].indicator == "alias"
        assert "\u2248" in genre_tags[0].label

    def test_miss(self):
        alias_map = {"literary_fiction": "literary_fiction", "science_fiction": "science_fiction"}
        ms = _make_manuscript(genre="science_fiction")
        agent = _make_agent(genres=["literary_fiction"])
        scores = ScoreBreakdown()
        tags = compute_match_tags(ms, agent, scores, alias_map)
        genre_tags = [t for t in tags if t.dimension == "genre"]
        assert genre_tags[0].indicator == "miss"
        assert "\u2717" in genre_tags[0].label


class TestAudienceTag:
    def test_close(self):
        alias_map = {}
        ms = _make_manuscript(genre=None, audience=["young_adult"])
        agent = _make_agent(audience=["adult"])
        scores = ScoreBreakdown(audience_score=0.6)
        tags = compute_match_tags(ms, agent, scores, alias_map)
        aud_tags = [t for t in tags if t.dimension == "audience"]
        assert aud_tags[0].indicator == "close"

    def test_exact(self):
        alias_map = {}
        ms = _make_manuscript(genre=None, audience=["adult"])
        agent = _make_agent(audience=["adult"])
        scores = ScoreBreakdown(audience_score=1.0)
        tags = compute_match_tags(ms, agent, scores, alias_map)
        aud_tags = [t for t in tags if t.dimension == "audience"]
        assert aud_tags[0].indicator == "exact"


class TestSnippet:
    def test_snippet_from_keywords(self):
        agent = _make_agent(keywords=["literary fiction", "upmarket", "diverse voices"])
        snippet = generate_snippet(agent)
        assert "\u00b7" in snippet
        assert "literary fiction" in snippet

    def test_snippet_max_5(self):
        agent = _make_agent(keywords=[f"kw{i}" for i in range(10)])
        snippet = generate_snippet(agent)
        parts = snippet.split(" \u00b7 ")
        assert len(parts) == 5

    def test_snippet_no_raw_text(self):
        """Snippets are built from keywords only, never raw text."""
        agent = _make_agent(keywords=["character-driven", "family saga"])
        agent.wishlist_raw = "I am looking for deeply personal stories..."
        snippet = generate_snippet(agent)
        assert "deeply personal" not in snippet
        assert "character-driven" in snippet
