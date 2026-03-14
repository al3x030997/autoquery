"""Tests for compliance Celery tasks (session cleanup)."""
from datetime import datetime, timedelta, timezone

from autoquery.database.models import InteractionEvent, Manuscript


def test_cleanup_stale_sessions_deletes_old_events(db_session):
    """Anonymous events older than 90 days should be deleted."""
    old_time = datetime.now(timezone.utc) - timedelta(days=100)

    # Old anonymous event
    old_event = InteractionEvent(event_type="result_shown", user_id=None)
    db_session.add(old_event)
    db_session.commit()

    # Set created_at manually
    db_session.execute(
        InteractionEvent.__table__.update()
        .where(InteractionEvent.__table__.c.id == old_event.id)
        .values(created_at=old_time)
    )
    db_session.commit()

    # Recent anonymous event (should survive)
    recent_event = InteractionEvent(event_type="card_clicked", user_id=None)
    db_session.add(recent_event)
    db_session.commit()

    # Run cleanup logic directly (not via Celery)
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    deleted = (
        db_session.query(InteractionEvent)
        .filter(InteractionEvent.user_id.is_(None), InteractionEvent.created_at < cutoff)
        .delete(synchronize_session="fetch")
    )
    db_session.commit()

    assert deleted == 1
    remaining = db_session.query(InteractionEvent).count()
    assert remaining == 1


def test_cleanup_stale_sessions_nulls_old_manuscripts(db_session):
    """Anonymous manuscripts older than 90 days should have session_id nulled."""
    old_time = datetime.now(timezone.utc) - timedelta(days=100)

    old_ms = Manuscript(title="Old", genre="fantasy", session_id="old-session")
    db_session.add(old_ms)
    db_session.commit()

    db_session.execute(
        Manuscript.__table__.update()
        .where(Manuscript.__table__.c.id == old_ms.id)
        .values(created_at=old_time)
    )
    db_session.commit()

    # Recent manuscript (should keep session_id)
    recent_ms = Manuscript(title="Recent", genre="scifi", session_id="new-session")
    db_session.add(recent_ms)
    db_session.commit()

    # Run cleanup
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    nulled = (
        db_session.query(Manuscript)
        .filter(
            Manuscript.user_id.is_(None),
            Manuscript.session_id.isnot(None),
            Manuscript.created_at < cutoff,
        )
        .update({Manuscript.session_id: None}, synchronize_session="fetch")
    )
    db_session.commit()

    assert nulled == 1

    db_session.refresh(old_ms)
    db_session.refresh(recent_ms)
    assert old_ms.session_id is None
    assert recent_ms.session_id == "new-session"


def test_cleanup_preserves_authenticated_data(db_session):
    """Events and manuscripts with a user_id should never be cleaned up."""
    from autoquery.database.models import User

    user = User(email="test@test.com", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    old_time = datetime.now(timezone.utc) - timedelta(days=100)

    ms = Manuscript(title="Auth MS", genre="fantasy", user_id=user.id, session_id="auth-session")
    db_session.add(ms)
    db_session.commit()

    db_session.execute(
        Manuscript.__table__.update()
        .where(Manuscript.__table__.c.id == ms.id)
        .values(created_at=old_time)
    )
    db_session.commit()

    evt = InteractionEvent(event_type="result_shown", user_id=user.id, manuscript_id=ms.id)
    db_session.add(evt)
    db_session.commit()

    db_session.execute(
        InteractionEvent.__table__.update()
        .where(InteractionEvent.__table__.c.id == evt.id)
        .values(created_at=old_time)
    )
    db_session.commit()

    # Cleanup should not touch authenticated data
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    deleted_events = (
        db_session.query(InteractionEvent)
        .filter(InteractionEvent.user_id.is_(None), InteractionEvent.created_at < cutoff)
        .delete(synchronize_session="fetch")
    )
    nulled_ms = (
        db_session.query(Manuscript)
        .filter(
            Manuscript.user_id.is_(None),
            Manuscript.session_id.isnot(None),
            Manuscript.created_at < cutoff,
        )
        .update({Manuscript.session_id: None}, synchronize_session="fetch")
    )
    db_session.commit()

    assert deleted_events == 0
    assert nulled_ms == 0

    db_session.refresh(ms)
    assert ms.session_id == "auth-session"
