"""Backward test evaluation orchestrator."""
from __future__ import annotations

from autoquery.database.models import Agent, Manuscript, REVIEW_STATUS_APPROVED
from autoquery.evaluation.metrics import (
    EvalReport,
    agency_diversity_index,
    hard_nos_violation_rate,
    precision_at_k,
    recall_at_k,
    summarize_reports,
)
from autoquery.evaluation.test_data import BackwardTestCase, get_test_cases
from autoquery.matching.phase1.pipeline import match
from autoquery.matching.types import MatchWeights


async def run_backward_test(
    db_session,
    embedding_model,
    test_cases: list[BackwardTestCase] | None = None,
    weights: MatchWeights | None = None,
) -> list[EvalReport]:
    """Run backward test cases and return evaluation reports.

    Per case: insert agents into DB -> create Manuscript -> call match() ->
    compute metrics -> return EvalReport.
    """
    if test_cases is None:
        test_cases = get_test_cases()

    reports: list[EvalReport] = []

    for case in test_cases:
        # Insert known agents
        known_ids: set[int] = set()
        all_agents: list[Agent] = []

        for agent_def in case.known_agents:
            agent = Agent(
                name=agent_def["name"],
                profile_url=f"https://test.com/{case.id}/{agent_def['name'].lower().replace(' ', '-')}",
                genres=agent_def.get("genres"),
                audience=agent_def.get("audience"),
                keywords=agent_def.get("keywords"),
                agency=agent_def.get("agency"),
                is_open=True,
                review_status=REVIEW_STATUS_APPROVED,
                opted_out=False,
            )
            db_session.add(agent)
            db_session.flush()
            known_ids.add(agent.id)
            all_agents.append(agent)

        # Insert decoy agents
        for agent_def in case.decoy_agents:
            agent = Agent(
                name=agent_def["name"],
                profile_url=f"https://test.com/{case.id}/{agent_def['name'].lower().replace(' ', '-')}",
                genres=agent_def.get("genres"),
                audience=agent_def.get("audience"),
                keywords=agent_def.get("keywords"),
                agency=agent_def.get("agency"),
                is_open=True,
                review_status=REVIEW_STATUS_APPROVED,
                opted_out=False,
            )
            db_session.add(agent)
            db_session.flush()
            all_agents.append(agent)

        db_session.commit()

        # Create manuscript mock
        ms = Manuscript(
            title=case.description,
            genre=case.manuscript.get("genre"),
            audience=case.manuscript.get("audience"),
            query_letter=case.manuscript.get("query_letter"),
            comps=case.manuscript.get("comps"),
        )
        db_session.add(ms)
        db_session.commit()
        db_session.refresh(ms)

        # Embed manuscript if embedding_model provided
        if embedding_model:
            text = f"{ms.genre or ''} {ms.query_letter or ''}"
            ms.embedding_fulltext = await embedding_model.embed(text)
            db_session.commit()

        # Run matching
        results = await match(
            ms, all_agents,
            db_session=db_session,
            embedding_model=embedding_model,
            weights=weights,
            output_size=20,
        )

        # Compute metrics
        ranked_ids = [r.agent_id for r in results]
        agent_agency_map = {a.id: (a.agency or f"unknown_{a.id}") for a in all_agents}

        report = EvalReport(
            test_case_id=case.id,
            precision_at_5=precision_at_k(ranked_ids, known_ids, 5),
            precision_at_10=precision_at_k(ranked_ids, known_ids, 10),
            recall_at_10=recall_at_k(ranked_ids, known_ids, 10),
            hard_nos_violations=hard_nos_violation_rate(results, []),
            diversity=agency_diversity_index(results, agent_agency_map),
        )
        reports.append(report)

    return reports


async def run_backward_test_with_weights(
    db_session,
    embedding_model,
    weights: MatchWeights,
    test_cases: list[BackwardTestCase] | None = None,
) -> dict:
    """Convenience wrapper: run backward test + summarize."""
    reports = await run_backward_test(
        db_session, embedding_model,
        test_cases=test_cases, weights=weights,
    )
    return summarize_reports(reports)
