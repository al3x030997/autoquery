"""Embedding pipeline: agent/manuscript embedding + query expansion."""

from __future__ import annotations

import json
import os

import httpx

from autoquery.database.models import REVIEW_STATUS_APPROVED, Agent, Manuscript
from autoquery.embeddings.model import EmbeddingModel, _l2_normalize

# Instruction prefixes for BGE-style models (asymmetric retrieval)
AGENT_PREFIX = (
    "Represent this literary agent profile for retrieval: "
    "This agent is looking for: "
)
MANUSCRIPT_PREFIX = (
    "Represent this manuscript to find matching literary agents: "
)

# Weights for combined manuscript embedding
FULLTEXT_WEIGHT = 0.7
QUERY_WEIGHT = 0.3

_EXPAND_SYSTEM = (
    "You are a publishing-industry assistant. Given a query letter, "
    "produce exactly 12 keywords or short phrases that a literary agent "
    "would use to describe the kind of book they want. "
    'Return a JSON object: {"keywords": ["...", ...]}'
)


def _build_agent_text(agent: Agent) -> str:
    """Build embedding input text from an Agent record."""
    parts: list[str] = []
    if agent.wishlist_raw:
        parts.append(agent.wishlist_raw)
    if agent.bio_raw:
        parts.append(agent.bio_raw)
    # Fallback: use structured keywords if no raw text available
    if not parts and agent.keywords:
        parts.append(", ".join(agent.keywords))
        parts.append(", ".join(agent.keywords))  # double for weight
    return "\n\n".join(parts)


def _build_manuscript_text(manuscript: Manuscript) -> str:
    """Combine all author-supplied fields into embedding input."""
    parts: list[str] = []
    if manuscript.genre:
        parts.append(f"Genre: {manuscript.genre}")
    if manuscript.audience:
        parts.append(f"Audience: {', '.join(manuscript.audience)}")
    if manuscript.comps:
        parts.append(f"Comparable titles: {', '.join(manuscript.comps)}")
    if manuscript.query_letter:
        parts.append(manuscript.query_letter)
    if manuscript.synopsis:
        parts.append(manuscript.synopsis)
    return "\n\n".join(parts)


async def embed_agent(agent: Agent, model: EmbeddingModel) -> list[float]:
    """Embed an agent profile and return the vector."""
    text = _build_agent_text(agent)
    if not text:
        raise ValueError(f"Agent {agent.id} has no text to embed")
    return await model.embed(AGENT_PREFIX + text)


async def embed_manuscript_fulltext(
    manuscript: Manuscript, model: EmbeddingModel
) -> list[float]:
    """Embed all manuscript fields (fulltext variant)."""
    text = _build_manuscript_text(manuscript)
    if not text:
        raise ValueError(f"Manuscript {manuscript.id} has no text to embed")
    return await model.embed(MANUSCRIPT_PREFIX + text)


async def expand_query(
    query_letter: str,
    ollama_url: str | None = None,
    llm_model: str | None = None,
) -> str:
    """Use Ollama /api/generate to expand a query letter into 12 agent-speak keywords."""
    url = (ollama_url or os.environ.get(
        "OLLAMA_URL", "http://localhost:11434"
    )).rstrip("/")
    model = llm_model or os.environ.get("LLM_MODEL", "llama3")

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{url}/api/generate",
            json={
                "model": model,
                "system": _EXPAND_SYSTEM,
                "prompt": query_letter,
                "stream": False,
                "format": "json",
            },
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")

    # Parse JSON from response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in expand_query response: {raw[:200]}")
    data = json.loads(raw[start:end])
    keywords = data.get("keywords", [])
    return ", ".join(keywords)


async def embed_manuscript_query_expanded(
    keywords: str, model: EmbeddingModel
) -> list[float]:
    """Embed expanded keywords with AGENT prefix (for cross-space matching)."""
    return await model.embed(AGENT_PREFIX + keywords)


def combine_manuscript_embeddings(
    fulltext: list[float], query_expanded: list[float]
) -> list[float]:
    """Weighted combination (70/30) of fulltext and query-expanded vectors, L2-normalized."""
    combined = [
        FULLTEXT_WEIGHT * f + QUERY_WEIGHT * q
        for f, q in zip(fulltext, query_expanded)
    ]
    return _l2_normalize(combined)


async def recompute_all_agent_embeddings(
    session, model: EmbeddingModel
) -> int:
    """Recompute embeddings for all approved agents. Returns count updated."""
    agents = (
        session.query(Agent)
        .filter(Agent.review_status == REVIEW_STATUS_APPROVED)
        .all()
    )
    count = 0
    for agent in agents:
        try:
            vec = await embed_agent(agent, model)
            agent.embedding = vec
            count += 1
        except ValueError:
            continue
    session.commit()
    return count
