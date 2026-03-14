"""Opt-out route for agents requesting removal."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from autoquery.api.schemas.optout import OptOutInput
from autoquery.database.db import get_db
from autoquery.database.models import Agent, OptOutRequest

router = APIRouter(prefix="/api", tags=["opt-out"])


@router.post("/opt-out", status_code=status.HTTP_201_CREATED)
async def opt_out(
    body: OptOutInput,
    db: Session = Depends(get_db),
):
    # Try to match agent by name
    agent = db.query(Agent).filter(Agent.name == body.agent_name).first()

    record = OptOutRequest(
        agent_name=body.agent_name,
        contact_email=body.contact_email,
        agent_id=agent.id if agent else None,
        reason=body.reason,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"id": record.id, "status": "received"}
