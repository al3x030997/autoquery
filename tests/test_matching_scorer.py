"""Tests for matching Layer 2: scoring."""
import math
import pytest
from unittest.mock import MagicMock

from autoquery.database.models import Agent, Manuscript
from autoquery.matching.phase1.scorer import (
    _dbsf_normalize,
    _dot_product,
    compute_audience_score,
    compute_genre_score,
    compute_semantic_score,
    score_candidates,
)
from autoquery.matching.types import MatchWeights


def _make_agent(id=1, genres=None, audience=None, keywords=None, embedding=None, **kw):
    agent = MagicMock(spec=Agent)
    agent.id = id
    agent.name = kw.get("name", f"Agent {id}")
    agent.agency = kw.get("agency")
    agent.genres = genres or []
    agent.audience = audience or []
    agent.keywords = keywords or []
    agent.embedding = embedding
    agent.hard_nos_keywords = kw.get("hard_nos_keywords")
    return agent


def _make_manuscript(genre=None, audience=None, embedding=None, comps=None, **kw):
    ms = MagicMock(spec=Manuscript)
    ms.genre = genre
    ms.audience = audience
    ms.embedding_fulltext = embedding
    ms.comps = comps
    ms.query_letter = kw.get("query_letter")
    ms.genre_score_weight = kw.get("genre_score_weight")
    ms.fts_score_weight = kw.get("fts_score_weight")
    ms.semantic_score_weight = kw.get("semantic_score_weight")
    ms.audience_score_weight = kw.get("audience_score_weight")
    return ms


class TestDBSFNormalize:
    def test_basic(self):
        result = _dbsf_normalize([1.0, 2.0, 3.0, 4.0, 5.0])
        assert all(0.0 <= v <= 1.0 for v in result)
        # Highest should get highest norm
        assert result[-1] > result[0]

    def test_single_value_positive(self):
        result = _dbsf_normalize([5.0])
        assert result == [1.0]

    def test_single_value_zero(self):
        result = _dbsf_normalize([0.0])
        assert result == [0.0]

    def test_identical_values(self):
        result = _dbsf_normalize([3.0, 3.0, 3.0])
        # μ=3, σ=0 → σ floored to 0.1, (3-3)/0.1 = 0
        assert all(v == 0.0 for v in result)

    def test_empty(self):
        assert _dbsf_normalize([]) == []

    def test_sigma_floor(self):
        """Very small variance should still produce finite values."""
        result = _dbsf_normalize([1.0, 1.001, 1.002])
        assert all(0.0 <= v <= 1.0 for v in result)


class TestAudienceScore:
    def test_exact_match(self):
        assert compute_audience_score(["adult"], ["adult"]) == 1.0

    def test_one_step(self):
        assert compute_audience_score(["young_adult"], ["adult"]) == 0.6

    def test_two_step(self):
        assert compute_audience_score(["middle_grade"], ["adult"]) == 0.3

    def test_no_overlap(self):
        assert compute_audience_score(["children's"], ["adult"]) == 0.1

    def test_empty_audiences(self):
        assert compute_audience_score([], ["adult"]) == 0.0
        assert compute_audience_score(["adult"], []) == 0.0
        assert compute_audience_score(None, None) == 0.0

    def test_multiple_audiences_takes_best(self):
        assert compute_audience_score(
            ["young_adult", "adult"], ["adult"]
        ) == 1.0


class TestGenreScore:
    def test_exact_match(self):
        alias_map = {"literary_fiction": "literary_fiction", "literary": "literary_fiction"}
        score = compute_genre_score("literary_fiction", ["literary_fiction"], alias_map)
        assert score == 1.0

    def test_alias_match(self):
        alias_map = {"literary_fiction": "literary_fiction", "lit fic": "literary_fiction"}
        score = compute_genre_score("lit fic", ["literary_fiction"], alias_map)
        assert score == 0.85

    def test_no_match(self):
        alias_map = {"literary_fiction": "literary_fiction"}
        score = compute_genre_score("science_fiction", ["literary_fiction"], alias_map)
        assert score == 0.0

    def test_embedding_fallback(self):
        alias_map = {}
        ms_emb = [1.0, 0.0, 0.0]
        ag_emb = [0.6, 0.0, 0.0]  # dot product = 0.6
        score = compute_genre_score("genreA", ["genreB"], alias_map, ms_emb, ag_emb)
        assert score == pytest.approx(0.6)

    def test_embedding_fallback_capped_at_0_7(self):
        alias_map = {}
        ms_emb = [1.0, 0.0, 0.0]
        ag_emb = [0.9, 0.0, 0.0]  # dot product = 0.9, but capped
        score = compute_genre_score("genreA", ["genreB"], alias_map, ms_emb, ag_emb)
        assert score == 0.7


class TestSemanticScore:
    def test_dot_product(self):
        a = [1.0, 0.0, 0.0]
        b = [0.5, 0.5, 0.0]
        assert _dot_product(a, b) == 0.5

    def test_semantic_score(self):
        ms_emb = [1.0, 0.0, 0.0]
        ag_emb = [0.8, 0.6, 0.0]
        score = compute_semantic_score(ms_emb, ag_emb)
        assert score == pytest.approx(0.8)

    def test_semantic_score_none(self):
        assert compute_semantic_score(None, [1.0]) == 0.0
        assert compute_semantic_score([1.0], None) == 0.0


class TestWeightRedistribution:
    def test_missing_fts(self):
        w = MatchWeights(genre=0.35, fts=0.25, semantic=0.25, audience=0.15)
        r = w.redistribute(["genre", "semantic", "audience"])
        assert r.fts == 0.0
        assert abs(r.genre + r.semantic + r.audience - 1.0) < 1e-9

    def test_all_available(self):
        w = MatchWeights(genre=0.35, fts=0.25, semantic=0.25, audience=0.15)
        r = w.redistribute(["genre", "fts", "semantic", "audience"])
        assert abs(r.genre + r.fts + r.semantic + r.audience - 1.0) < 1e-9


class TestScoreCandidates:
    def test_end_to_end_no_db(self):
        """Score candidates with db_session=None → FTS skipped, weights redistributed."""
        ms = _make_manuscript(
            genre="literary_fiction",
            audience=["adult"],
            embedding=[1.0, 0.0, 0.0],
        )
        agents = [
            _make_agent(id=1, genres=["literary_fiction"], audience=["adult"],
                        embedding=[0.9, 0.1, 0.0]),
            _make_agent(id=2, genres=["science_fiction"], audience=["young_adult"],
                        embedding=[0.3, 0.7, 0.0]),
        ]
        alias_map = {"literary_fiction": "literary_fiction", "science_fiction": "science_fiction"}
        results = score_candidates(ms, agents, alias_map=alias_map, db_session=None)

        assert len(results) == 2
        # Agent 1 should rank higher (exact genre + exact audience + higher semantic)
        assert results[0].agent_id == 1
        assert results[0].composite_score > results[1].composite_score

    def test_returns_sorted(self):
        ms = _make_manuscript(genre="thriller", audience=["adult"], embedding=[0.5, 0.5, 0.0])
        agents = [
            _make_agent(id=1, genres=["romance"], audience=["adult"],
                        embedding=[0.1, 0.1, 0.0]),
            _make_agent(id=2, genres=["thriller"], audience=["adult"],
                        embedding=[0.5, 0.5, 0.0]),
        ]
        alias_map = {"thriller": "thriller", "romance": "romance"}
        results = score_candidates(ms, agents, alias_map=alias_map)
        assert results[0].composite_score >= results[1].composite_score
