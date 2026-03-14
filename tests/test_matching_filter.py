"""Tests for matching Layer 1: filtering."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from autoquery.database.models import Agent, REVIEW_STATUS_APPROVED, REVIEW_STATUS_PENDING
from autoquery.matching.phase1.filter import filter_basic, filter_hard_nos


def _make_agent(
    id=1,
    is_open=True,
    opted_out=False,
    review_status=REVIEW_STATUS_APPROVED,
    hard_nos_keywords=None,
    **kwargs,
):
    agent = MagicMock(spec=Agent)
    agent.id = id
    agent.is_open = is_open
    agent.opted_out = opted_out
    agent.review_status = review_status
    agent.hard_nos_keywords = hard_nos_keywords
    for k, v in kwargs.items():
        setattr(agent, k, v)
    return agent


class TestFilterBasic:
    def test_passes_valid_agent(self):
        agent = _make_agent()
        passed, rejected = filter_basic([agent])
        assert len(passed) == 1
        assert len(rejected) == 0

    def test_excludes_not_open(self):
        agent = _make_agent(is_open=False)
        passed, rejected = filter_basic([agent])
        assert len(passed) == 0
        assert rejected[0][1] == "not_open"

    def test_excludes_opted_out(self):
        agent = _make_agent(opted_out=True)
        passed, rejected = filter_basic([agent])
        assert len(passed) == 0
        assert rejected[0][1] == "opted_out"

    def test_excludes_not_approved(self):
        agent = _make_agent(review_status=REVIEW_STATUS_PENDING)
        passed, rejected = filter_basic([agent])
        assert len(passed) == 0
        assert "review_status" in rejected[0][1]

    def test_multiple_reasons_first_wins(self):
        """Agent with multiple disqualifying conditions: first check wins."""
        agent = _make_agent(is_open=False, opted_out=True, review_status=REVIEW_STATUS_PENDING)
        passed, rejected = filter_basic([agent])
        assert len(rejected) == 1
        assert rejected[0][1] == "not_open"

    def test_mixed_agents(self):
        agents = [
            _make_agent(id=1),
            _make_agent(id=2, is_open=False),
            _make_agent(id=3),
            _make_agent(id=4, opted_out=True),
        ]
        passed, rejected = filter_basic(agents)
        assert len(passed) == 2
        assert len(rejected) == 2


class TestFilterHardNos:
    @pytest.mark.asyncio
    async def test_triggers_on_high_similarity(self):
        agent = _make_agent(hard_nos_keywords=["vampires", "werewolves"])
        # Mock embedding model returning vector with high similarity
        ms_emb = [1.0] + [0.0] * 1023
        model = AsyncMock()
        model.embed.return_value = [0.9] + [0.0] * 1023  # high dot product ~0.9

        passed, rejected = await filter_hard_nos([agent], ms_emb, model)
        assert len(passed) == 0
        assert len(rejected) == 1
        assert "hard_nos_sim" in rejected[0][1]

    @pytest.mark.asyncio
    async def test_passes_on_low_similarity(self):
        agent = _make_agent(hard_nos_keywords=["vampires"])
        ms_emb = [1.0] + [0.0] * 1023
        model = AsyncMock()
        model.embed.return_value = [0.3] + [0.0] * 1023  # low sim ~0.3

        passed, rejected = await filter_hard_nos([agent], ms_emb, model)
        assert len(passed) == 1
        assert len(rejected) == 0

    @pytest.mark.asyncio
    async def test_skipped_when_no_keywords(self):
        agent = _make_agent(hard_nos_keywords=None)
        ms_emb = [1.0] + [0.0] * 1023
        model = AsyncMock()

        passed, rejected = await filter_hard_nos([agent], ms_emb, model)
        assert len(passed) == 1
        model.embed.assert_not_called()
