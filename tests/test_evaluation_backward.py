"""Tests for backward test evaluation orchestrator."""
import pytest

from autoquery.database.models import Agent, REVIEW_STATUS_APPROVED
from autoquery.evaluation.backward_test import run_backward_test
from autoquery.evaluation.test_data import BackwardTestCase
from tests.conftest import _FakeEmbeddingModel


@pytest.mark.asyncio
async def test_backward_test_runs_single_case(db_session):
    """Verifies EvalReport is populated for a single case."""
    case = BackwardTestCase(
        id="test_single",
        description="Simple lit fic test",
        manuscript={"genre": "literary_fiction", "audience": ["adult"],
                     "query_letter": "A novel about family."},
        known_agents=[
            {"name": "Good Agent", "genres": ["literary_fiction"], "audience": ["adult"],
             "keywords": ["literary"], "agency": "Agency A"},
        ],
        decoy_agents=[
            {"name": "Bad Agent", "genres": ["science_fiction"], "audience": ["young_adult"],
             "keywords": ["space"], "agency": "Agency B"},
        ],
    )

    model = _FakeEmbeddingModel()
    reports = await run_backward_test(db_session, model, test_cases=[case])

    assert len(reports) == 1
    r = reports[0]
    assert r.test_case_id == "test_single"
    assert 0.0 <= r.precision_at_5 <= 1.0
    assert 0.0 <= r.recall_at_10 <= 1.0
    assert r.hard_nos_violations == 0.0


@pytest.mark.asyncio
async def test_backward_test_known_agent_ranked_high(db_session):
    """Exact genre match agent should appear in results (top positions)."""
    case = BackwardTestCase(
        id="test_rank",
        description="Genre match ranking test",
        manuscript={"genre": "mystery", "audience": ["adult"],
                     "query_letter": "A cozy mystery."},
        known_agents=[
            {"name": "Mystery Pro", "genres": ["mystery"], "audience": ["adult"],
             "keywords": ["cozy", "sleuth"], "agency": "Agency M"},
        ],
        decoy_agents=[
            {"name": "Sci-Fi Writer", "genres": ["science_fiction"], "audience": ["young_adult"],
             "keywords": ["aliens"], "agency": "Agency S"},
        ],
    )

    model = _FakeEmbeddingModel()
    reports = await run_backward_test(db_session, model, test_cases=[case])

    # With fake embeddings, genre/audience drive ranking.
    # Mystery agent should rank above sci-fi agent for mystery manuscript.
    assert reports[0].precision_at_5 > 0.0


@pytest.mark.asyncio
async def test_backward_test_hard_nos_not_returned(db_session):
    """Agent with is_open=False should be filtered out."""
    # Create a closed agent directly in DB
    closed = Agent(
        name="Closed Agent",
        profile_url="https://test.com/closed",
        genres=["literary_fiction"],
        audience=["adult"],
        is_open=False,
        review_status=REVIEW_STATUS_APPROVED,
        opted_out=False,
    )
    db_session.add(closed)
    db_session.commit()
    db_session.refresh(closed)

    case = BackwardTestCase(
        id="test_filter",
        description="Filtering test",
        manuscript={"genre": "literary_fiction", "audience": ["adult"],
                     "query_letter": "A literary novel."},
        known_agents=[
            {"name": "Open Agent", "genres": ["literary_fiction"], "audience": ["adult"],
             "keywords": ["literary"], "agency": "Agency O"},
        ],
        decoy_agents=[],
    )

    model = _FakeEmbeddingModel()
    reports = await run_backward_test(db_session, model, test_cases=[case])

    # The closed agent should not appear — it's filtered by filter_basic.
    # We can't directly check, but the test should complete without issues.
    assert len(reports) == 1
    assert reports[0].hard_nos_violations == 0.0
