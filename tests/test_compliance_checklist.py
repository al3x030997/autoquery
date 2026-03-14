"""Automated compliance checklist from 14_compliance_and_gdpr.md."""
import pytest


def test_agent_public_excludes_raw_fields():
    """AgentPublic schema must not expose internal raw fields."""
    from autoquery.api.schemas.agent import AgentPublic

    fields = set(AgentPublic.model_fields.keys())
    assert "wishlist_raw" not in fields
    assert "bio_raw" not in fields
    assert "hard_nos_raw" not in fields
    assert "email" not in fields


def test_agent_internal_has_raw_fields():
    """AgentInternal schema must have raw fields (for admin use)."""
    from autoquery.api.schemas.agent import AgentInternal

    fields = set(AgentInternal.model_fields.keys())
    assert "wishlist_raw" in fields
    assert "bio_raw" in fields
    assert "hard_nos_raw" in fields


def test_blacklist_enforced():
    """Blacklisted domains must raise BlacklistError."""
    from autoquery.crawler.crawler_engine import BlacklistError, _load_blacklist

    blacklist = _load_blacklist()
    assert len(blacklist) >= 5

    # All known aggregators must be blocked
    for domain in ["querytracker.net", "manuscriptwishlist.com", "publishersmarketplace.com"]:
        assert domain in blacklist, f"{domain} not in blacklist"


def test_opted_out_agents_filtered(db_session):
    """Agents with opted_out=True must be excluded from matching."""
    from autoquery.database.models import Agent
    from autoquery.matching.phase1.filter import filter_basic

    agent = Agent(
        name="Opted Out Agent",
        profile_url="https://optedout.com",
        review_status="approved",
        is_open=True,
        opted_out=True,
        genres=["fantasy"],
        audience=["Adult"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    passed, rejected = filter_basic([agent])
    assert len(passed) == 0
    assert len(rejected) == 1
    assert rejected[0][1] == "opted_out"


def test_allowed_event_types_documented():
    """All allowed event types should be in the schema."""
    from autoquery.api.schemas.events import ALLOWED_EVENT_TYPES

    expected = {
        "result_shown",
        "card_clicked",
        "profile_expanded",
        "submission_checklist",
        "source_link_clicked",
        "signup_cta_shown",
        "signup_completed",
        "feedback_positive",
        "feedback_neutral",
        "result_ignored",
    }
    assert expected == ALLOWED_EVENT_TYPES


def test_health_endpoint_basic(client):
    """Basic health check must return ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_opt_out_endpoint_creates_request(client, db_session):
    """Opt-out form must create a request record."""
    resp = client.post("/api/opt-out", json={
        "agent_name": "Test Agent",
        "contact_email": "agent@example.com",
        "reason": "Please remove my profile",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "received"
