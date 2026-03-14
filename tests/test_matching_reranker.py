"""Tests for matching Layer 3: MMR re-ranking."""
import pytest

from autoquery.matching.phase1.reranker import mmr_rerank, MAX_PER_AGENCY_IN_TOP_10
from autoquery.matching.types import ScoreBreakdown, ScoredAgent


def _scored(id, score, agency=None, embedding=None):
    return ScoredAgent(
        agent_id=id,
        agent_name=f"Agent {id}",
        agency=agency,
        composite_score=score,
        scores=ScoreBreakdown(),
        embedding=embedding,
    )


class TestMMRRerank:
    def test_basic_ordering(self):
        """Without diversity pressure, should roughly preserve relevance order."""
        candidates = [_scored(1, 0.9), _scored(2, 0.7), _scored(3, 0.5)]
        result = mmr_rerank(candidates, lambda_param=1.0)  # pure relevance
        assert result[0].agent_id == 1
        assert result[0].mmr_rank == 1

    def test_diversifies(self):
        """With similar embeddings, MMR should promote diverse candidates."""
        emb_a = [1.0, 0.0, 0.0]
        emb_b = [0.99, 0.1, 0.0]  # very similar to a
        emb_c = [0.0, 1.0, 0.0]  # very different
        candidates = [
            _scored(1, 0.9, embedding=emb_a),
            _scored(2, 0.85, embedding=emb_b),
            _scored(3, 0.8, embedding=emb_c),
        ]
        result = mmr_rerank(candidates, lambda_param=0.5)
        # Agent 3 should be promoted due to diversity
        ids = [r.agent_id for r in result]
        assert ids[0] == 1  # highest relevance
        # Agent 3 should come before Agent 2 due to diversity
        assert ids.index(3) < ids.index(2)

    def test_agency_constraint_top10(self):
        """Max 3 agents from same agency in top 10."""
        candidates = [_scored(i, 1.0 - i * 0.01, agency="BigAgency") for i in range(1, 8)]
        candidates.extend([_scored(10 + i, 0.5, agency=f"Other{i}") for i in range(5)])
        result = mmr_rerank(candidates, lambda_param=1.0, output_size=12)
        top10 = result[:10]
        agency_count = sum(1 for r in top10 if r.agency == "BigAgency")
        assert agency_count <= MAX_PER_AGENCY_IN_TOP_10

    def test_agency_allows_beyond_top10(self):
        """Agency constraint only applies to top-10 positions."""
        candidates = [_scored(i, 1.0 - i * 0.01, agency="BigAgency") for i in range(1, 15)]
        candidates.extend([_scored(20 + i, 0.3, agency=f"Other{i}") for i in range(10)])
        result = mmr_rerank(candidates, lambda_param=1.0, output_size=20)
        all_big = [r for r in result if r.agency == "BigAgency"]
        # Can have more than 3 total, just not in top-10
        top10_big = sum(1 for r in result[:10] if r.agency == "BigAgency")
        assert top10_big <= MAX_PER_AGENCY_IN_TOP_10

    def test_no_embeddings_degrades(self):
        """Without embeddings, diversity term is 0 → pure relevance."""
        candidates = [_scored(1, 0.9), _scored(2, 0.7), _scored(3, 0.5)]
        result = mmr_rerank(candidates, lambda_param=0.5)
        assert result[0].agent_id == 1
        assert result[1].agent_id == 2
        assert result[2].agent_id == 3

    def test_output_size_limit(self):
        candidates = [_scored(i, 1.0 - i * 0.01) for i in range(30)]
        result = mmr_rerank(candidates, output_size=5)
        assert len(result) == 5

    def test_empty_input(self):
        assert mmr_rerank([]) == []
