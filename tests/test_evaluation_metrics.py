"""Tests for evaluation metric functions."""
import pytest

from autoquery.evaluation.metrics import (
    EvalReport,
    agency_diversity_index,
    hard_nos_violation_rate,
    precision_at_k,
    recall_at_k,
    summarize_reports,
)
from autoquery.matching.types import ScoredAgent, ScoreBreakdown


def _scored(agent_id: int, agency: str = "A") -> ScoredAgent:
    return ScoredAgent(
        agent_id=agent_id, agent_name=f"Agent {agent_id}",
        agency=agency, composite_score=0.5,
        scores=ScoreBreakdown(),
    )


class TestPrecisionAtK:
    def test_perfect(self):
        assert precision_at_k([1, 2, 3], {1, 2, 3}, 3) == 1.0

    def test_none_relevant(self):
        assert precision_at_k([1, 2, 3], {4, 5}, 3) == 0.0

    def test_partial(self):
        assert precision_at_k([1, 2, 3, 4, 5], {1, 3, 5}, 5) == pytest.approx(0.6)

    def test_empty_ranked(self):
        assert precision_at_k([], {1, 2}, 5) == 0.0

    def test_k_larger_than_ranked(self):
        # Only 2 items ranked, k=5 → denominator = min(5, 2) = 2
        assert precision_at_k([1, 2], {1, 2}, 5) == 1.0


class TestRecallAtK:
    def test_basic(self):
        assert recall_at_k([1, 2, 3], {1, 2, 3, 4}, 3) == pytest.approx(0.75)

    def test_empty_relevant(self):
        assert recall_at_k([1, 2], set(), 5) == 0.0


class TestHardNosViolationRate:
    def test_zero_violations(self):
        results = [_scored(1), _scored(2)]
        assert hard_nos_violation_rate(results, [3, 4]) == 0.0

    def test_nonzero_violations(self):
        results = [_scored(1), _scored(2), _scored(3), _scored(4)]
        assert hard_nos_violation_rate(results, [2, 4]) == pytest.approx(0.5)


class TestAgencyDiversity:
    def test_all_same_agency(self):
        results = [_scored(i, "Same") for i in range(5)]
        assert agency_diversity_index(results, {i: "Same" for i in range(5)}, top_n=5) == pytest.approx(0.2)

    def test_all_different_agencies(self):
        results = [_scored(i, f"Agency_{i}") for i in range(5)]
        mapping = {i: f"Agency_{i}" for i in range(5)}
        assert agency_diversity_index(results, mapping, top_n=5) == 1.0


class TestSummarizeReports:
    def test_mean_aggregation(self):
        reports = [
            EvalReport("a", precision_at_5=0.6, precision_at_10=0.4, recall_at_10=0.8, hard_nos_violations=0.0, diversity=1.0),
            EvalReport("b", precision_at_5=0.4, precision_at_10=0.6, recall_at_10=0.6, hard_nos_violations=0.2, diversity=0.8),
        ]
        summary = summarize_reports(reports)
        assert summary["mean_p_at_5"] == pytest.approx(0.5)
        assert summary["mean_p_at_10"] == pytest.approx(0.5)
        assert summary["mean_recall_at_10"] == pytest.approx(0.7)
        assert summary["mean_hard_nos_violations"] == pytest.approx(0.1)
        assert summary["mean_diversity"] == pytest.approx(0.9)
        assert summary["num_cases"] == 2

    def test_empty_reports(self):
        summary = summarize_reports([])
        assert summary["num_cases"] == 0
        assert summary["mean_p_at_5"] == 0.0
