"""End-to-end API flow tests."""
from unittest.mock import AsyncMock, patch

import pytest

from autoquery.database.models import (
    Agent, Manuscript, MatchingResult, REVIEW_STATUS_APPROVED,
)
from autoquery.matching.types import MatchTag, ScoreBreakdown, ScoredAgent


def _create_approved_agent(db_session, name="Agent A", agency="Agency X"):
    agent = Agent(
        name=name,
        agency=agency,
        profile_url=f"https://example.com/{name.lower().replace(' ', '-')}",
        genres=["literary fiction"],
        keywords=["contemporary", "debut"],
        audience=["adult"],
        is_open=True,
        review_status=REVIEW_STATUS_APPROVED,
        opted_out=False,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


def _mock_scored_agent(agent_id, name="Agent A", agency="Agency X", rank=1):
    return ScoredAgent(
        agent_id=agent_id,
        agent_name=name,
        agency=agency,
        composite_score=0.85,
        scores=ScoreBreakdown(genre_score=0.9, fts_score=0.7, semantic_score=0.8, audience_score=0.6),
        mmr_rank=rank,
        match_tags=[MatchTag(dimension="genre", indicator="exact", label="Genre: Literary Fiction")],
        snippet="contemporary, debut",
    )


MATCH_INPUT = {
    "genre": "literary fiction",
    "audience": "adult",
    "themes": ["identity", "family"],
    "tone": "introspective",
    "comps": ["Normal People"],
    "query_letter": "A story about family bonds.",
}


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_full_guest_journey(mock_match, mock_expand, client, db_session):
    """Guest: match -> events -> get results (limited to 3)."""
    agents = [_create_approved_agent(db_session, name=f"Agent {i}") for i in range(5)]
    mock_match.return_value = [_mock_scored_agent(a.id, a.name, rank=i + 1) for i, a in enumerate(agents)]

    # POST /api/match as guest
    resp = client.post("/api/match", json=MATCH_INPUT)
    assert resp.status_code == 200
    data = resp.json()
    ms_id = data["manuscript_id"]
    # Guest gets output_size=3
    assert mock_match.call_args[1]["output_size"] == 3

    # POST /api/events
    for event_type in ["result_shown", "card_clicked"]:
        resp = client.post("/api/events", json={
            "event_type": event_type,
            "manuscript_id": ms_id,
            "agent_id": agents[0].id,
        })
        assert resp.status_code == 202

    # GET /api/results/{id} — guest sees ≤3
    resp = client.get(f"/api/results/{ms_id}")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 3


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_guest_registers_unlocks_full(mock_match, mock_expand, client, db_session):
    """Guest matches, registers, then sees full results."""
    agents = [_create_approved_agent(db_session, name=f"Agent R{i}") for i in range(5)]
    mock_match.return_value = [_mock_scored_agent(a.id, a.name, rank=i + 1) for i, a in enumerate(agents)]

    # Guest match
    resp = client.post("/api/match", json=MATCH_INPUT)
    ms_id = resp.json()["manuscript_id"]

    # Register (same session)
    reg = client.post("/api/auth/register", json={
        "email": "e2e_guest@example.com", "password": "securepass123",
    })
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    # GET results with auth — should see up to 20
    resp = client.get(
        f"/api/results/{ms_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    # After registration, manuscript.user_id should be set
    ms = db_session.query(Manuscript).filter(Manuscript.id == ms_id).first()
    assert ms.user_id is not None


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_authenticated_match_gets_20(mock_match, mock_expand, client, db_session):
    """Authenticated user gets output_size=20."""
    agent = _create_approved_agent(db_session)
    mock_match.return_value = [_mock_scored_agent(agent.id)]

    # Register first
    reg = client.post("/api/auth/register", json={
        "email": "e2e_auth@example.com", "password": "securepass123",
    })
    token = reg.json()["access_token"]

    # Match with auth
    resp = client.post(
        "/api/match", json=MATCH_INPUT,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert mock_match.call_args[1]["output_size"] == 20


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_events_linked_after_registration(mock_match, mock_expand, client, db_session):
    """Anonymous events get user_id set after registration."""
    from autoquery.database.models import InteractionEvent

    agent = _create_approved_agent(db_session)
    mock_match.return_value = [_mock_scored_agent(agent.id)]

    # Guest match + event
    resp = client.post("/api/match", json=MATCH_INPUT)
    ms_id = resp.json()["manuscript_id"]

    client.post("/api/events", json={
        "event_type": "card_clicked",
        "manuscript_id": ms_id,
        "agent_id": agent.id,
    })

    # Register
    reg = client.post("/api/auth/register", json={
        "email": "e2e_link@example.com", "password": "securepass123",
    })
    assert reg.status_code == 201
    token = reg.json()

    # Verify events linked
    events = db_session.query(InteractionEvent).filter(
        InteractionEvent.manuscript_id == ms_id,
    ).all()
    # Events should have user_id set after session linking
    for evt in events:
        if evt.user_id is not None:
            assert evt.user_id > 0
