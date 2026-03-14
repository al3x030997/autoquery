"""Analytics end-to-end validation tests."""
import pytest

from autoquery.api.schemas.events import ALLOWED_EVENT_TYPES
from autoquery.database.models import InteractionEvent


def test_all_10_event_types_accepted(client, db_session):
    """All ALLOWED_EVENT_TYPES should return 202."""
    for event_type in sorted(ALLOWED_EVENT_TYPES):
        resp = client.post("/api/events", json={"event_type": event_type})
        assert resp.status_code == 202, f"Failed for event_type={event_type}"


def test_event_persists_to_db(client, db_session):
    """Posted event should be persisted to InteractionEvent table."""
    client.post("/api/events", json={
        "event_type": "card_clicked",
        "manuscript_id": 42,
        "agent_id": 7,
    })
    # BackgroundTasks in TestClient run synchronously
    evt = db_session.query(InteractionEvent).filter(
        InteractionEvent.event_type == "card_clicked",
    ).first()
    assert evt is not None
    assert evt.manuscript_id == 42
    assert evt.agent_id == 7


def test_event_with_auth_sets_user_id(client, db_session):
    """Authenticated event should have user_id set."""
    # Register
    reg = client.post("/api/auth/register", json={
        "email": "analytics@example.com", "password": "securepass123",
    })
    token = reg.json()["access_token"]

    client.post(
        "/api/events",
        json={"event_type": "profile_expanded", "agent_id": 5},
        headers={"Authorization": f"Bearer {token}"},
    )

    evt = db_session.query(InteractionEvent).filter(
        InteractionEvent.event_type == "profile_expanded",
    ).first()
    assert evt is not None
    assert evt.user_id is not None


def test_visit_to_signup_funnel(client, db_session):
    """Verify funnel event sequence persists correctly."""
    funnel = ["result_shown", "card_clicked", "signup_cta_shown", "signup_completed"]
    for event_type in funnel:
        resp = client.post("/api/events", json={"event_type": event_type})
        assert resp.status_code == 202

    events = db_session.query(InteractionEvent).order_by(InteractionEvent.id).all()
    stored_types = [e.event_type for e in events]
    for et in funnel:
        assert et in stored_types


def test_engagement_payload_persisted(client, db_session):
    """card_clicked with payload should persist the payload."""
    client.post("/api/events", json={
        "event_type": "card_clicked",
        "payload": {"duration_ms": 3500},
    })

    evt = db_session.query(InteractionEvent).filter(
        InteractionEvent.event_type == "card_clicked",
    ).first()
    assert evt is not None
    assert evt.payload == {"duration_ms": 3500}


def test_feedback_event_with_payload(client, db_session):
    """feedback_positive with payload should persist."""
    client.post("/api/events", json={
        "event_type": "feedback_positive",
        "payload": {"comment": "Very helpful results!", "rating": 5},
    })

    evt = db_session.query(InteractionEvent).filter(
        InteractionEvent.event_type == "feedback_positive",
    ).first()
    assert evt is not None
    assert evt.payload["comment"] == "Very helpful results!"
    assert evt.payload["rating"] == 5
