"""Process opt-out requests: mark agents as opted out and delete raw fields."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from autoquery.database.models import Agent, OptOutRequest

logger = logging.getLogger(__name__)


def process_opt_out(db: Session, request_id: int) -> bool:
    """Process a single opt-out request.

    Returns True if successfully processed, False if agent not found.
    """
    req = db.query(OptOutRequest).filter(OptOutRequest.id == request_id).first()
    if not req or req.processed:
        return False

    agent = None
    if req.agent_id:
        agent = db.query(Agent).filter(Agent.id == req.agent_id).first()

    if not agent:
        # Try fuzzy match by name
        agent = db.query(Agent).filter(Agent.name == req.agent_name).first()

    if not agent:
        logger.warning("Opt-out request %d: no matching agent found for '%s'", request_id, req.agent_name)
        req.processed = True
        db.commit()
        return False

    # Mark agent as opted out
    agent.opted_out = True

    # Delete raw fields (GDPR compliance — not just hide, actually delete)
    agent.wishlist_raw = None
    agent.bio_raw = None
    agent.hard_nos_raw = None
    agent.email = None

    req.processed = True
    db.commit()

    logger.info("Processed opt-out for agent '%s' (id=%d)", agent.name, agent.id)
    return True


def process_all_pending(db: Session) -> int:
    """Process all unprocessed opt-out requests. Returns count processed."""
    pending = db.query(OptOutRequest).filter(OptOutRequest.processed != True).all()  # noqa: E712
    count = 0
    for req in pending:
        if process_opt_out(db, req.id):
            count += 1
    return count


def check_sla_violations(db: Session) -> list[OptOutRequest]:
    """Find opt-out requests that have been pending for more than 72 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    overdue = (
        db.query(OptOutRequest)
        .filter(
            OptOutRequest.processed != True,  # noqa: E712
            OptOutRequest.created_at < cutoff,
        )
        .all()
    )
    if overdue:
        logger.warning("SLA VIOLATION: %d opt-out requests pending > 72 hours", len(overdue))
    return overdue
