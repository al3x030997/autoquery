"""Tests for launch readiness checks."""
import pytest

from autoquery.database.models import Agent, REVIEW_STATUS_APPROVED, REVIEW_STATUS_PENDING
from autoquery.evaluation.readiness import (
    check_agent_count,
    check_all_agents_have_embeddings,
    check_audience_coverage,
    check_genre_coverage,
    is_launch_ready,
    ReadinessResult,
)


_bulk_counter = 0


def _bulk_insert_agents(db, count, genres=None, audiences=None, with_embedding=True):
    """Insert `count` approved, open agents."""
    global _bulk_counter
    for i in range(count):
        _bulk_counter += 1
        agent = Agent(
            name=f"Agent {_bulk_counter}",
            profile_url=f"https://test.com/readiness/agent-{_bulk_counter}",
            genres=genres or ["literary_fiction"],
            audience=audiences or ["adult"],
            embedding=[0.1] * 3 if with_embedding else None,
            is_open=True,
            review_status=REVIEW_STATUS_APPROVED,
            opted_out=False,
        )
        db.add(agent)
    db.commit()


class TestAgentCount:
    def test_passes(self, db_session):
        _bulk_insert_agents(db_session, 200)
        result = check_agent_count(db_session, minimum=200)
        assert result.passed is True
        assert result.actual_value == 200

    def test_fails(self, db_session):
        _bulk_insert_agents(db_session, 50)
        result = check_agent_count(db_session, minimum=200)
        assert result.passed is False
        assert result.actual_value == 50


class TestGenreCoverage:
    def test_passes(self, db_session):
        genres_list = [
            ["literary_fiction"], ["science_fiction"], ["fantasy"],
            ["romance"], ["mystery"], ["thriller"],
        ]
        for i, genres in enumerate(genres_list):
            agent = Agent(
                name=f"Agent G{i}",
                profile_url=f"https://test.com/readiness/genre-{i}",
                genres=genres,
                audience=["adult"],
                is_open=True,
                review_status=REVIEW_STATUS_APPROVED,
                opted_out=False,
            )
            db_session.add(agent)
        db_session.commit()

        result = check_genre_coverage(db_session, minimum=5)
        assert result.passed is True
        assert result.actual_value >= 5

    def test_fails(self, db_session):
        _bulk_insert_agents(db_session, 10, genres=["literary_fiction"])
        result = check_genre_coverage(db_session, minimum=5)
        assert result.passed is False
        assert result.actual_value == 1


class TestAudienceCoverage:
    def test_passes(self, db_session):
        audiences_list = [["adult"], ["young_adult"], ["middle_grade"], ["children's"]]
        for i, aud in enumerate(audiences_list):
            agent = Agent(
                name=f"Agent A{i}",
                profile_url=f"https://test.com/readiness/aud-{i}",
                genres=["literary_fiction"],
                audience=aud,
                is_open=True,
                review_status=REVIEW_STATUS_APPROVED,
                opted_out=False,
            )
            db_session.add(agent)
        db_session.commit()

        result = check_audience_coverage(db_session, minimum=3)
        assert result.passed is True
        assert result.actual_value >= 3


class TestEmbeddings:
    def test_passes(self, db_session):
        _bulk_insert_agents(db_session, 5, with_embedding=True)
        result = check_all_agents_have_embeddings(db_session)
        assert result.passed is True
        assert result.actual_value == 0

    def test_fails(self, db_session):
        _bulk_insert_agents(db_session, 3, with_embedding=True)
        _bulk_insert_agents(db_session, 2, with_embedding=False)
        result = check_all_agents_have_embeddings(db_session)
        assert result.passed is False
        assert result.actual_value == 2


class TestIsLaunchReady:
    def test_all_pass(self):
        results = [
            ReadinessResult("a", True, 200, 200, "ok"),
            ReadinessResult("b", True, 5, 5, "ok"),
            ReadinessResult("c", True, 3, 3, "ok"),
        ]
        assert is_launch_ready(results) is True

    def test_one_fails(self):
        results = [
            ReadinessResult("a", True, 200, 200, "ok"),
            ReadinessResult("b", False, 2, 5, "fail"),
        ]
        assert is_launch_ready(results) is False
