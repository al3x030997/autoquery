"""Tests for opt-out routes."""
import pytest

from autoquery.database.models import Agent, REVIEW_STATUS_APPROVED


def test_optout_creates_record(client, db_session):
    resp = client.post("/api/opt-out", json={
        "agent_name": "Jane Smith",
        "contact_email": "jane@agency.com",
        "reason": "No longer accepting queries",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "received"
    assert "id" in data


def test_optout_matches_agent(client, db_session):
    agent = Agent(
        name="Jane Smith",
        profile_url="https://example.com/jane",
        review_status=REVIEW_STATUS_APPROVED,
    )
    db_session.add(agent)
    db_session.commit()

    resp = client.post("/api/opt-out", json={
        "agent_name": "Jane Smith",
        "contact_email": "jane@agency.com",
    })
    assert resp.status_code == 201


def test_optout_validates_email(client):
    resp = client.post("/api/opt-out", json={
        "agent_name": "Jane Smith",
        "contact_email": "not-an-email",
    })
    assert resp.status_code == 422


def test_optout_missing_name(client):
    resp = client.post("/api/opt-out", json={
        "agent_name": "",
        "contact_email": "jane@agency.com",
    })
    assert resp.status_code == 422
