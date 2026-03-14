"""Shared dataclasses for the matching pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ScoreBreakdown:
    """Raw and normalized score components."""
    genre_score: float = 0.0
    audience_score: float = 0.0
    fts_score: float = 0.0
    semantic_score: float = 0.0
    genre_norm: float = 0.0
    audience_norm: float = 0.0
    fts_norm: float = 0.0
    semantic_norm: float = 0.0


@dataclass
class MatchTag:
    """A single explainability tag for a match."""
    dimension: str   # "genre" | "audience" | "topics"
    indicator: str   # "exact" | "alias" | "close" | "miss"
    label: str       # e.g. "Genre: ✓ Literary Fiction"


@dataclass
class ScoredAgent:
    """An agent with computed match scores."""
    agent_id: int
    agent_name: str
    agency: str | None
    composite_score: float
    scores: ScoreBreakdown
    mmr_rank: int | None = None
    match_tags: list[MatchTag] = field(default_factory=list)
    snippet: str = ""
    embedding: list[float] | None = None  # carried for MMR, dropped before return


@dataclass
class MatchWeights:
    """Configurable scoring weights. Must sum to 1.0."""
    genre: float = 0.35
    fts: float = 0.25
    semantic: float = 0.25
    audience: float = 0.15

    def redistribute(self, available: list[str]) -> MatchWeights:
        """Proportionally rescale to sum=1.0, zeroing unavailable signals."""
        all_signals = ["genre", "fts", "semantic", "audience"]
        total = sum(getattr(self, s) for s in available)
        if total == 0:
            return MatchWeights(genre=0, fts=0, semantic=0, audience=0)
        new = MatchWeights(genre=0, fts=0, semantic=0, audience=0)
        for s in available:
            setattr(new, s, getattr(self, s) / total)
        return new

    @classmethod
    def from_env(cls) -> MatchWeights:
        """Load weights from environment variables."""
        return cls(
            genre=float(os.environ.get("GENRE_SCORE_WEIGHT", "0.35")),
            fts=float(os.environ.get("FTS_SCORE_WEIGHT", "0.25")),
            semantic=float(os.environ.get("SEMANTIC_SCORE_WEIGHT", "0.25")),
            audience=float(os.environ.get("AUDIENCE_SCORE_WEIGHT", "0.15")),
        )
