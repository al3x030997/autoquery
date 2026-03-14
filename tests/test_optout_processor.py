"""Tests for opt-out processing."""
from autoquery.compliance.optout_processor import (
    check_sla_violations,
    process_all_pending,
    process_opt_out,
)
from autoquery.database.models import Agent, OptOutRequest


def _create_agent(db, name="Test Agent", profile_url="https://example.com/agent"):
    agent = Agent(
        name=name,
        profile_url=profile_url,
        wishlist_raw="I love fantasy",
        bio_raw="A great agent",
        hard_nos_raw="No horror",
        email="agent@example.com",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def test_process_opt_out_marks_agent(db_session):
    agent = _create_agent(db_session)
    req = OptOutRequest(
        agent_name=agent.name,
        contact_email="contact@example.com",
        agent_id=agent.id,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    result = process_opt_out(db_session, req.id)
    assert result is True

    db_session.refresh(agent)
    assert agent.opted_out is True
    assert agent.wishlist_raw is None
    assert agent.bio_raw is None
    assert agent.hard_nos_raw is None
    assert agent.email is None

    db_session.refresh(req)
    assert req.processed is True


def test_process_opt_out_by_name_match(db_session):
    """If agent_id is not set, match by name."""
    agent = _create_agent(db_session, name="Jane Smith", profile_url="https://example.com/jane")
    req = OptOutRequest(
        agent_name="Jane Smith",
        contact_email="jane@example.com",
        agent_id=None,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    result = process_opt_out(db_session, req.id)
    assert result is True

    db_session.refresh(agent)
    assert agent.opted_out is True


def test_process_opt_out_no_matching_agent(db_session):
    """If no agent matches, still mark as processed."""
    req = OptOutRequest(
        agent_name="Nonexistent Agent",
        contact_email="no@one.com",
        agent_id=None,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    result = process_opt_out(db_session, req.id)
    assert result is False

    db_session.refresh(req)
    assert req.processed is True


def test_process_all_pending(db_session):
    agent1 = _create_agent(db_session, name="Agent A", profile_url="https://a.com")
    agent2 = _create_agent(db_session, name="Agent B", profile_url="https://b.com")
    req1 = OptOutRequest(agent_name="Agent A", contact_email="a@a.com", agent_id=agent1.id)
    req2 = OptOutRequest(agent_name="Agent B", contact_email="b@b.com", agent_id=agent2.id)
    db_session.add_all([req1, req2])
    db_session.commit()

    count = process_all_pending(db_session)
    assert count == 2

    db_session.refresh(agent1)
    db_session.refresh(agent2)
    assert agent1.opted_out is True
    assert agent2.opted_out is True


def test_already_processed_skipped(db_session):
    req = OptOutRequest(
        agent_name="Already Done",
        contact_email="done@done.com",
        processed=True,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    result = process_opt_out(db_session, req.id)
    assert result is False


def test_sla_violations_empty(db_session):
    violations = check_sla_violations(db_session)
    assert violations == []


def test_sla_violations_detects_overdue(db_session):
    from datetime import datetime, timedelta, timezone

    old_req = OptOutRequest(
        agent_name="Overdue Agent",
        contact_email="overdue@example.com",
    )
    db_session.add(old_req)
    db_session.commit()

    # Manually set created_at to 4 days ago
    old_time = datetime.now(timezone.utc) - timedelta(days=4)
    db_session.execute(
        OptOutRequest.__table__.update()
        .where(OptOutRequest.__table__.c.id == old_req.id)
        .values(created_at=old_time)
    )
    db_session.commit()

    violations = check_sla_violations(db_session)
    assert len(violations) == 1
    assert violations[0].agent_name == "Overdue Agent"
