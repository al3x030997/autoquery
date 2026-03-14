"""Tests for matching routes."""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from autoquery.database.models import (
    Agent,
    Manuscript,
    MatchingResult,
    REVIEW_STATUS_APPROVED,
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


def _mock_scored_agent(agent_id, name="Agent A", agency="Agency X"):
    return ScoredAgent(
        agent_id=agent_id,
        agent_name=name,
        agency=agency,
        composite_score=0.85,
        scores=ScoreBreakdown(genre_score=0.9, fts_score=0.7, semantic_score=0.8, audience_score=0.6),
        mmr_rank=1,
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
def test_match_returns_results(mock_match, mock_expand, client, db_session):
    agent = _create_approved_agent(db_session)
    mock_match.return_value = [_mock_scored_agent(agent.id)]

    resp = client.post("/api/match", json=MATCH_INPUT)
    assert resp.status_code == 200
    data = resp.json()
    assert data["manuscript_id"] > 0
    assert len(data["results"]) == 1
    assert data["results"][0]["composite_score"] == 0.85


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_match_guest_gets_3(mock_match, mock_expand, client, db_session):
    agents = [_create_approved_agent(db_session, name=f"Agent {i}") for i in range(5)]
    mock_match.return_value = [_mock_scored_agent(a.id, a.name) for a in agents]

    resp = client.post("/api/match", json=MATCH_INPUT)
    assert resp.status_code == 200
    # Guest gets output_size=3, so match() is called with output_size=3
    call_kwargs = mock_match.call_args[1]
    assert call_kwargs["output_size"] == 3


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_match_auth_gets_20(mock_match, mock_expand, client, db_session):
    agent = _create_approved_agent(db_session)
    mock_match.return_value = [_mock_scored_agent(agent.id)]

    # Register
    reg = client.post("/api/auth/register", json={
        "email": "match@example.com", "password": "securepass123"
    })
    token = reg.json()["access_token"]

    resp = client.post(
        "/api/match", json=MATCH_INPUT,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    call_kwargs = mock_match.call_args[1]
    assert call_kwargs["output_size"] == 20


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_match_persists_to_db(mock_match, mock_expand, client, db_session):
    agent = _create_approved_agent(db_session)
    mock_match.return_value = [_mock_scored_agent(agent.id)]

    resp = client.post("/api/match", json=MATCH_INPUT)
    ms_id = resp.json()["manuscript_id"]

    results = db_session.query(MatchingResult).filter(
        MatchingResult.manuscript_id == ms_id
    ).all()
    assert len(results) == 1


def test_match_validates_genre(client):
    bad_input = MATCH_INPUT.copy()
    bad_input["genre"] = ""
    resp = client.post("/api/match", json=bad_input)
    assert resp.status_code == 422


def test_match_strips_html(client, db_session):
    from autoquery.api.schemas.matching import strip_html
    assert strip_html("<b>bold</b> text") == "bold text"
    assert strip_html("no tags") == "no tags"


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_get_results_stored(mock_match, mock_expand, client, db_session):
    agent = _create_approved_agent(db_session)
    mock_match.return_value = [_mock_scored_agent(agent.id)]

    # Create match first
    resp = client.post("/api/match", json=MATCH_INPUT)
    ms_id = resp.json()["manuscript_id"]

    # Get results
    resp = client.get(f"/api/results/{ms_id}")
    assert resp.status_code == 200
    assert resp.json()["manuscript_id"] == ms_id
    assert len(resp.json()["results"]) >= 1


def test_get_results_not_found(client, db_session):
    resp = client.get("/api/results/99999")
    assert resp.status_code == 404


def test_genres_endpoint(client):
    resp = client.get("/api/genres")
    assert resp.status_code == 200
    data = resp.json()
    assert "genres" in data
    assert isinstance(data["genres"], list)


@patch("autoquery.api.routes.matching.expand_query", new_callable=AsyncMock, return_value="keywords")
@patch("autoquery.api.routes.matching.match", new_callable=AsyncMock)
def test_get_results_auth_split(mock_match, mock_expand, client, db_session):
    """Auth user sees up to 20 results, guest sees 3."""
    agent = _create_approved_agent(db_session)

    # Create multiple MatchingResults for a manuscript
    ms = Manuscript(title="Test", genre="fiction", session_id="test-session-id")
    db_session.add(ms)
    db_session.commit()
    db_session.refresh(ms)

    for i in range(10):
        a = _create_approved_agent(db_session, name=f"Agent R{i}")
        mr = MatchingResult(
            manuscript_id=ms.id, agent_id=a.id,
            composite_score=0.9 - i * 0.05, mmr_rank=i + 1,
        )
        db_session.add(mr)
    db_session.commit()

    # Guest with matching session cookie gets 3
    client.cookies.set("session_id", "test-session-id")
    resp = client.get(f"/api/results/{ms.id}")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 3
    assert resp.json()["total_found"] == 10
