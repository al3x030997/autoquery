"""Interaction event schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator

ALLOWED_EVENT_TYPES = {
    "result_shown",
    "card_clicked",
    "profile_expanded",
    "submission_checklist",
    "source_link_clicked",
    "signup_cta_shown",
    "signup_completed",
    "feedback_positive",
    "feedback_neutral",
    "result_ignored",
}


class EventInput(BaseModel):
    event_type: str
    manuscript_id: int | None = None
    agent_id: int | None = None
    payload: dict[str, Any] | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{v}'. Allowed: {sorted(ALLOWED_EVENT_TYPES)}")
        return v
