"""Tests for monitoring health checks."""
from autoquery.monitoring.health import check_db, check_pending_opt_outs
from autoquery.database.models import Agent, OptOutRequest


def test_check_db_returns_ok(db_session):
    result = check_db(db_session)
    assert result["status"] == "ok"
    assert "agents_total" in result
    assert "agents_approved" in result


def test_check_db_with_agents(db_session):
    agent = Agent(name="Test", profile_url="https://test.com", review_status="approved")
    db_session.add(agent)
    db_session.commit()

    result = check_db(db_session)
    assert result["agents_total"] == 1
    assert result["agents_approved"] == 1


def test_check_pending_opt_outs_none(db_session):
    result = check_pending_opt_outs(db_session)
    assert result["pending"] == 0
    assert result["overdue_72h"] == 0


def test_check_pending_opt_outs_counts(db_session):
    req = OptOutRequest(agent_name="Test", contact_email="t@t.com")
    db_session.add(req)
    db_session.commit()

    result = check_pending_opt_outs(db_session)
    assert result["pending"] == 1
    assert result["overdue_72h"] == 0
