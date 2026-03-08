from typing import Any

from pydantic import BaseModel


class AgentPublic(BaseModel):
    """Public-facing agent schema. Never includes raw or PII fields."""

    id: int
    name: str
    agency: str | None = None
    profile_url: str
    genres: list[str] | None = None
    keywords: list[str] | None = None
    audience: list[str] | None = None
    hard_nos_keywords: list[str] | None = None
    submission_req: dict[str, Any] | None = None
    is_open: bool | None = None
    review_status: str
    opted_out: bool

    model_config = {"from_attributes": True}


class AgentInternal(AgentPublic):
    """Internal-only agent schema. Adds raw fields and email.

    WARNING: Never use on public routes. Internal services only.
    """

    wishlist_raw: str | None = None
    bio_raw: str | None = None
    hard_nos_raw: str | None = None
    email: str | None = None
