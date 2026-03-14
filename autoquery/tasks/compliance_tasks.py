"""Celery tasks for compliance: opt-out processing, session cleanup."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from autoquery.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="compliance.process_pending_opt_outs")
def process_pending_opt_outs() -> dict:
    """Process all unprocessed opt-out requests. Runs hourly via Beat."""
    from autoquery.compliance.optout_processor import process_all_pending
    from autoquery.database.db import SessionLocal

    db = SessionLocal()
    try:
        count = process_all_pending(db)
        if count:
            logger.info("Processed %d opt-out requests", count)
        return {"processed": count}
    finally:
        db.close()


@celery_app.task(name="compliance.check_opt_out_sla")
def check_opt_out_sla() -> dict:
    """Check for opt-out requests exceeding the 72h SLA. Runs daily via Beat."""
    from autoquery.compliance.optout_processor import check_sla_violations
    from autoquery.database.db import SessionLocal

    db = SessionLocal()
    try:
        overdue = check_sla_violations(db)
        return {"overdue_count": len(overdue)}
    finally:
        db.close()


@celery_app.task(name="compliance.cleanup_stale_sessions")
def cleanup_stale_sessions() -> dict:
    """Delete anonymous session data older than 90 days. Runs weekly via Beat."""
    from autoquery.database.db import SessionLocal
    from autoquery.database.models import InteractionEvent, Manuscript

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        # Delete anonymous events older than 90 days
        deleted_events = (
            db.query(InteractionEvent)
            .filter(
                InteractionEvent.user_id.is_(None),
                InteractionEvent.created_at < cutoff,
            )
            .delete(synchronize_session="fetch")
        )

        # Null out session_id on old anonymous manuscripts (keep the record for stats)
        nulled_manuscripts = (
            db.query(Manuscript)
            .filter(
                Manuscript.user_id.is_(None),
                Manuscript.session_id.isnot(None),
                Manuscript.created_at < cutoff,
            )
            .update({Manuscript.session_id: None}, synchronize_session="fetch")
        )

        db.commit()

        if deleted_events or nulled_manuscripts:
            logger.info(
                "Session cleanup: deleted %d anonymous events, nulled session_id on %d manuscripts",
                deleted_events,
                nulled_manuscripts,
            )

        return {"deleted_events": deleted_events, "nulled_manuscripts": nulled_manuscripts}
    finally:
        db.close()
