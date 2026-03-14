"""Matching request/response schemas."""
from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, BeforeValidator

from autoquery.api.schemas.agent import AgentPublic


def strip_html(v: str) -> str:
    if isinstance(v, str):
        return re.sub(r"<[^>]+>", "", v)
    return v


SanitizedStr = Annotated[str, BeforeValidator(strip_html)]


class ManuscriptInput(BaseModel):
    genre: str
    audience: str
    tone: SanitizedStr = Field(max_length=200, default="")
    themes: list[str] = Field(min_length=2, max_length=8)
    comps: list[str] = Field(default_factory=list)
    query_letter: SanitizedStr = ""
    synopsis: SanitizedStr = ""
    additional_notes: SanitizedStr = Field(max_length=300, default="")

    @field_validator("genre")
    @classmethod
    def genre_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("genre must not be empty")
        return v.strip()


class MatchTagResponse(BaseModel):
    dimension: str
    indicator: str
    label: str


class ScoreBreakdownResponse(BaseModel):
    genre_score: float
    fts_score: float
    semantic_score: float
    audience_score: float


class ScoredAgentResponse(BaseModel):
    agent: AgentPublic
    composite_score: float
    mmr_rank: int | None = None
    match_tags: list[MatchTagResponse] = []
    snippet: str = ""
    scores: ScoreBreakdownResponse


class MatchResponse(BaseModel):
    manuscript_id: int
    results: list[ScoredAgentResponse]
    total_found: int
