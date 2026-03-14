"""Shared genre alias loading and matching utilities."""
from __future__ import annotations

from pathlib import Path

import yaml

_DEFAULT_PATH = Path(__file__).parent.parent.parent / "config" / "genre_aliases.yaml"


def load_genre_aliases(path: str | Path | None = None) -> dict[str, str]:
    """Build reverse lookup: alias (lowercase) → canonical genre name."""
    path = path or _DEFAULT_PATH
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        aliases = data.get("aliases", {})
        reverse: dict[str, str] = {}
        for canonical, alias_list in aliases.items():
            canonical_lower = canonical.lower().strip()
            reverse[canonical_lower] = canonical_lower
            if isinstance(alias_list, list):
                for alias in alias_list:
                    reverse[alias.lower().strip()] = canonical_lower
        return reverse
    except Exception:
        return {}


def genre_match_score(
    ms_genre: str | None,
    agent_genres: list[str] | None,
    alias_map: dict[str, str],
    ms_embedding: list[float] | None = None,
    agent_embedding: list[float] | None = None,
) -> float:
    """
    Score genre overlap between manuscript and agent.

    exact=1.0, alias=0.85, embedding fallback capped at 0.7, else 0.0.
    """
    if not ms_genre or not agent_genres:
        return 0.0

    ms_key = ms_genre.lower().strip()
    ms_canonical = alias_map.get(ms_key, ms_key)

    for ag in agent_genres:
        ag_key = ag.lower().strip()
        ag_canonical = alias_map.get(ag_key, ag_key)
        if ms_canonical == ag_canonical:
            # Exact match: original keys are the same
            if ms_key == ag_key:
                return 1.0
            # Alias match: different surface forms resolve to same canonical
            return 0.85

    # Embedding fallback
    if ms_embedding and agent_embedding and len(ms_embedding) == len(agent_embedding):
        dot = sum(a * b for a, b in zip(ms_embedding, agent_embedding))
        return min(max(dot, 0.0), 0.7)

    return 0.0
