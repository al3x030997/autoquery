"""Layer 1: Hard constraint filtering."""
from __future__ import annotations

import os

from autoquery.database.models import Agent, REVIEW_STATUS_APPROVED

HARD_NOS_THRESHOLD = float(os.environ.get("HARD_NOS_THRESHOLD", "0.75"))


def filter_basic(agents: list[Agent]) -> tuple[list[Agent], list[tuple[int, str]]]:
    """
    Synchronous filter: exclude agents that are not open, opted out,
    or not approved. Returns (passed, rejected) where rejected is
    list of (agent_id, reason).
    """
    passed: list[Agent] = []
    rejected: list[tuple[int, str]] = []

    for agent in agents:
        if not agent.is_open:
            rejected.append((agent.id, "not_open"))
        elif agent.opted_out:
            rejected.append((agent.id, "opted_out"))
        elif agent.review_status != REVIEW_STATUS_APPROVED:
            rejected.append((agent.id, f"review_status={agent.review_status}"))
        else:
            passed.append(agent)

    return passed, rejected


async def filter_hard_nos(
    agents: list[Agent],
    ms_embedding: list[float],
    embedding_model,
) -> tuple[list[Agent], list[tuple[int, str]]]:
    """
    Async filter: embed each agent's hard_nos_keywords, compare to
    manuscript embedding. Reject if cosine similarity > threshold.
    """
    passed: list[Agent] = []
    rejected: list[tuple[int, str]] = []

    for agent in agents:
        keywords = agent.hard_nos_keywords
        if not keywords:
            passed.append(agent)
            continue

        joined = ", ".join(keywords)
        hard_nos_emb = await embedding_model.embed(joined)

        # Dot product = cosine similarity for L2-normalized vectors
        sim = sum(a * b for a, b in zip(ms_embedding, hard_nos_emb))

        if sim > HARD_NOS_THRESHOLD:
            rejected.append((agent.id, f"hard_nos_sim={sim:.3f}"))
        else:
            passed.append(agent)

    return passed, rejected
