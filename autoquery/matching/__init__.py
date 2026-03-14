"""Matching algorithm — agent-manuscript matching pipeline."""
from autoquery.matching.types import MatchWeights, ScoreBreakdown, ScoredAgent, MatchTag
from autoquery.matching.phase1.pipeline import match, persist_results, ALGORITHM_VERSION

__all__ = [
    "match",
    "persist_results",
    "ALGORITHM_VERSION",
    "ScoredAgent",
    "MatchWeights",
    "ScoreBreakdown",
    "MatchTag",
]
