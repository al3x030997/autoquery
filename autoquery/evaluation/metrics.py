"""Pure metric functions for matching evaluation."""
from __future__ import annotations

from dataclasses import dataclass

from autoquery.matching.types import ScoredAgent


def precision_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int) -> float:
    """Precision@K: |ranked[:k] ∩ relevant| / min(k, len(ranked))."""
    if not ranked_ids or k <= 0:
        return 0.0
    top_k = ranked_ids[:k]
    hits = len(set(top_k) & relevant_ids)
    return hits / min(k, len(top_k))


def recall_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int) -> float:
    """Recall@K: |ranked[:k] ∩ relevant| / |relevant|."""
    if not relevant_ids:
        return 0.0
    top_k = ranked_ids[:k]
    hits = len(set(top_k) & relevant_ids)
    return hits / len(relevant_ids)


def hard_nos_violation_rate(results: list[ScoredAgent], violations: list[int]) -> float:
    """Fraction of results that are in the violations list."""
    if not results:
        return 0.0
    violation_set = set(violations)
    found = len({r.agent_id for r in results} & violation_set)
    return found / len(results)


def agency_diversity_index(
    results: list[ScoredAgent],
    agent_agency_map: dict[int, str],
    top_n: int = 10,
) -> float:
    """Unique agencies in top_n / top_n."""
    if not results or top_n <= 0:
        return 0.0
    top = results[:top_n]
    agencies = {agent_agency_map.get(r.agent_id, f"unknown_{r.agent_id}") for r in top}
    return len(agencies) / min(top_n, len(top))


@dataclass
class EvalReport:
    """Evaluation report for a single test case."""
    test_case_id: str
    precision_at_5: float
    precision_at_10: float
    recall_at_10: float
    hard_nos_violations: float
    diversity: float


def summarize_reports(reports: list[EvalReport]) -> dict:
    """Mean aggregation across all reports."""
    if not reports:
        return {
            "mean_p_at_5": 0.0,
            "mean_p_at_10": 0.0,
            "mean_recall_at_10": 0.0,
            "mean_hard_nos_violations": 0.0,
            "mean_diversity": 0.0,
            "num_cases": 0,
        }
    n = len(reports)
    return {
        "mean_p_at_5": sum(r.precision_at_5 for r in reports) / n,
        "mean_p_at_10": sum(r.precision_at_10 for r in reports) / n,
        "mean_recall_at_10": sum(r.recall_at_10 for r in reports) / n,
        "mean_hard_nos_violations": sum(r.hard_nos_violations for r in reports) / n,
        "mean_diversity": sum(r.diversity for r in reports) / n,
        "num_cases": n,
    }
