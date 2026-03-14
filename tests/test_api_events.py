"""Tests for interaction event routes."""
import pytest


def test_event_creates_record(client, db_session):
    resp = client.post("/api/events", json={
        "event_type": "card_clicked",
        "manuscript_id": 1,
        "agent_id": 2,
    })
    assert resp.status_code == 202
    assert resp.json()["status"] == "accepted"


def test_event_invalid_type(client):
    resp = client.post("/api/events", json={
        "event_type": "invalid_event",
    })
    assert resp.status_code == 422


def test_event_optional_fields(client, db_session):
    resp = client.post("/api/events", json={
        "event_type": "signup_cta_shown",
    })
    assert resp.status_code == 202


def test_event_with_payload(client, db_session):
    resp = client.post("/api/events", json={
        "event_type": "feedback_positive",
        "payload": {"comment": "Great match!"},
    })
    assert resp.status_code == 202


def test_event_with_auth(client, db_session):
    # Register a user first
    reg = client.post("/api/auth/register", json={
        "email": "events@example.com",
        "password": "securepass123",
    })
    token = reg.json()["access_token"]

    resp = client.post(
        "/api/events",
        json={"event_type": "card_clicked"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
