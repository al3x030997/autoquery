"""Opt-out request schemas."""
from pydantic import BaseModel, EmailStr, Field


class OptOutInput(BaseModel):
    agent_name: str = Field(min_length=1)
    contact_email: EmailStr
    reason: str | None = None
