"""Tests for session → user linking on registration."""
from autoquery.database.models import InteractionEvent, Manuscript, User


def test_register_links_session_manuscripts(client, db_session):
    """When a user registers, anonymous manuscripts with their session_id are linked."""
    # Create an anonymous manuscript with a known session_id
    manuscript = Manuscript(
        title="Test Manuscript",
        genre="fantasy",
        session_id="test-session-123",
    )
    db_session.add(manuscript)
    db_session.commit()
    db_session.refresh(manuscript)

    assert manuscript.user_id is None

    # Register with the same session cookie
    resp = client.post(
        "/api/auth/register",
        json={"email": "link@example.com", "password": "securepass123"},
        cookies={"session_id": "test-session-123"},
    )
    assert resp.status_code == 201

    # Verify manuscript is now linked
    db_session.refresh(manuscript)
    assert manuscript.user_id is not None

    user = db_session.query(User).filter(User.email == "link@example.com").first()
    assert manuscript.user_id == user.id


def test_register_links_session_events(client, db_session):
    """Events for anonymous manuscripts are also linked to the new user."""
    manuscript = Manuscript(
        title="Test Manuscript",
        genre="fantasy",
        session_id="test-session-456",
    )
    db_session.add(manuscript)
    db_session.commit()
    db_session.refresh(manuscript)

    event = InteractionEvent(
        event_type="result_shown",
        manuscript_id=manuscript.id,
        user_id=None,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.user_id is None

    resp = client.post(
        "/api/auth/register",
        json={"email": "link2@example.com", "password": "securepass123"},
        cookies={"session_id": "test-session-456"},
    )
    assert resp.status_code == 201

    db_session.refresh(event)
    user = db_session.query(User).filter(User.email == "link2@example.com").first()
    assert event.user_id == user.id


def test_register_does_not_link_other_sessions(client, db_session):
    """Registration only links manuscripts matching the user's session_id."""
    m1 = Manuscript(title="Mine", genre="fantasy", session_id="my-session")
    m2 = Manuscript(title="Not Mine", genre="scifi", session_id="other-session")
    db_session.add_all([m1, m2])
    db_session.commit()

    resp = client.post(
        "/api/auth/register",
        json={"email": "only-mine@example.com", "password": "securepass123"},
        cookies={"session_id": "my-session"},
    )
    assert resp.status_code == 201

    db_session.refresh(m1)
    db_session.refresh(m2)
    assert m1.user_id is not None
    assert m2.user_id is None


def test_register_without_session_manuscripts(client, db_session):
    """Registration works fine when there are no anonymous manuscripts."""
    resp = client.post(
        "/api/auth/register",
        json={"email": "nomanuscripts@example.com", "password": "securepass123"},
        cookies={"session_id": "empty-session"},
    )
    assert resp.status_code == 201
    assert "access_token" in resp.json()
