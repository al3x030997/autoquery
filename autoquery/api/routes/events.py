"""Interaction event logging route."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from autoquery.api.deps import get_optional_user
from autoquery.api.schemas.events import EventInput
from autoquery.database.db import get_db
from autoquery.database.models import InteractionEvent, User

router = APIRouter(prefix="/api", tags=["events"])


def _write_event(
    event: EventInput,
    user_id: int | None,
    db: Session,
) -> None:
    record = InteractionEvent(
        event_type=event.event_type,
        manuscript_id=event.manuscript_id,
        agent_id=event.agent_id,
        user_id=user_id,
        payload=event.payload,
    )
    db.add(record)
    db.commit()


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def log_event(
    body: EventInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    user_id = user.id if user else None
    background_tasks.add_task(_write_event, body, user_id, db)
    return {"status": "accepted"}
