"""Layer 4: Explainability — match tags and snippets."""
from __future__ import annotations

from autoquery.database.models import Agent, Manuscript
from autoquery.matching.genre_utils import genre_match_score
from autoquery.matching.types import MatchTag, ScoreBreakdown


def compute_match_tags(
    manuscript: Manuscript,
    agent: Agent,
    scores: ScoreBreakdown,
    alias_map: dict[str, str],
) -> list[MatchTag]:
    """Generate explainability tags for a match."""
    tags: list[MatchTag] = []

    # Genre tag
    tags.append(_genre_tag(manuscript.genre, agent.genres, alias_map))

    # Audience tag
    tags.append(_audience_tag(manuscript.audience, agent.audience, scores.audience_score))

    # Topics tag (keyword overlap)
    tags.extend(_topic_tags(manuscript, agent))

    return tags


def _genre_tag(
    ms_genre: str | None,
    agent_genres: list[str] | None,
    alias_map: dict[str, str],
) -> MatchTag:
    """Genre match indicator."""
    if not ms_genre or not agent_genres:
        return MatchTag(dimension="genre", indicator="miss", label="Genre: \u2717 No data")

    ms_key = ms_genre.lower().strip()
    ms_canonical = alias_map.get(ms_key, ms_key)

    for ag in agent_genres:
        ag_key = ag.lower().strip()
        ag_canonical = alias_map.get(ag_key, ag_key)
        if ms_canonical == ag_canonical:
            display = ms_genre.replace("_", " ").title()
            if ms_key == ag_key:
                return MatchTag(
                    dimension="genre", indicator="exact",
                    label=f"Genre: \u2713 {display}",
                )
            return MatchTag(
                dimension="genre", indicator="alias",
                label=f"Genre: \u2248 {display}",
            )

    display = ms_genre.replace("_", " ").title()
    return MatchTag(dimension="genre", indicator="miss", label=f"Genre: \u2717 {display}")


def _audience_tag(
    ms_audiences: list[str] | None,
    agent_audiences: list[str] | None,
    audience_score: float,
) -> MatchTag:
    """Audience proximity indicator."""
    if not ms_audiences or not agent_audiences:
        return MatchTag(dimension="audience", indicator="miss", label="Audience: \u2717 No data")

    if audience_score >= 1.0:
        return MatchTag(
            dimension="audience", indicator="exact",
            label=f"Audience: \u2713 {ms_audiences[0].replace('_', ' ').title()}",
        )
    elif audience_score >= 0.5:
        return MatchTag(
            dimension="audience", indicator="close",
            label=f"Audience: \u2248 {ms_audiences[0].replace('_', ' ').title()}",
        )
    else:
        return MatchTag(
            dimension="audience", indicator="miss",
            label=f"Audience: \u2717 {ms_audiences[0].replace('_', ' ').title()}",
        )


def _topic_tags(manuscript: Manuscript, agent: Agent) -> list[MatchTag]:
    """Keyword overlap tags."""
    tags: list[MatchTag] = []

    ms_keywords: set[str] = set()
    if manuscript.comps:
        ms_keywords.update(c.lower().strip() for c in manuscript.comps)
    if manuscript.genre:
        ms_keywords.add(manuscript.genre.lower().strip())

    agent_keywords: set[str] = set()
    if agent.keywords:
        agent_keywords.update(k.lower().strip() for k in agent.keywords)

    overlap = ms_keywords & agent_keywords
    for kw in sorted(overlap)[:3]:
        tags.append(MatchTag(
            dimension="topics", indicator="exact",
            label=f"Topic: \u2713 {kw.replace('_', ' ').title()}",
        ))

    return tags


def generate_snippet(agent: Agent) -> str:
    """
    Generate a short snippet from agent keywords.
    Up to 5 keywords with · separator. Never quotes raw text.
    """
    keywords = agent.keywords or []
    selected = [k.strip() for k in keywords[:5] if k and k.strip()]
    if not selected:
        return ""
    return " \u00b7 ".join(selected)
