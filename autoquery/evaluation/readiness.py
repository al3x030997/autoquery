"""Launch readiness checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from autoquery.database.models import Agent, REVIEW_STATUS_APPROVED


@dataclass
class ReadinessResult:
    """Result of a single readiness check."""
    check_name: str
    passed: bool
    actual_value: Any
    threshold: Any
    message: str


def check_agent_count(db: Session, minimum: int = 200) -> ReadinessResult:
    """Check that we have enough approved, open agents."""
    count = (
        db.query(Agent)
        .filter(
            Agent.review_status == REVIEW_STATUS_APPROVED,
            Agent.is_open == True,  # noqa: E712
        )
        .count()
    )
    return ReadinessResult(
        check_name="agent_count",
        passed=count >= minimum,
        actual_value=count,
        threshold=minimum,
        message=f"{count} approved+open agents (need {minimum})",
    )


def check_genre_coverage(db: Session, minimum: int = 5) -> ReadinessResult:
    """Check distinct genres across approved agents."""
    agents = (
        db.query(Agent.genres)
        .filter(Agent.review_status == REVIEW_STATUS_APPROVED)
        .all()
    )
    all_genres: set[str] = set()
    for (genres,) in agents:
        if genres:
            for g in genres:
                all_genres.add(g)

    count = len(all_genres)
    return ReadinessResult(
        check_name="genre_coverage",
        passed=count >= minimum,
        actual_value=count,
        threshold=minimum,
        message=f"{count} distinct genres (need {minimum})",
    )


def check_audience_coverage(db: Session, minimum: int = 3) -> ReadinessResult:
    """Check distinct audiences across approved agents."""
    agents = (
        db.query(Agent.audience)
        .filter(Agent.review_status == REVIEW_STATUS_APPROVED)
        .all()
    )
    all_audiences: set[str] = set()
    for (audience,) in agents:
        if audience:
            for a in audience:
                all_audiences.add(a)

    count = len(all_audiences)
    return ReadinessResult(
        check_name="audience_coverage",
        passed=count >= minimum,
        actual_value=count,
        threshold=minimum,
        message=f"{count} distinct audiences (need {minimum})",
    )


def check_all_agents_have_embeddings(db: Session) -> ReadinessResult:
    """Check that all approved agents have embeddings."""
    missing = (
        db.query(Agent)
        .filter(
            Agent.review_status == REVIEW_STATUS_APPROVED,
            Agent.embedding.is_(None),
        )
        .count()
    )
    return ReadinessResult(
        check_name="all_agents_have_embeddings",
        passed=missing == 0,
        actual_value=missing,
        threshold=0,
        message=f"{missing} approved agents missing embeddings",
    )


async def check_sample_matching_no_hard_nos(
    db: Session, embedding_model,
) -> ReadinessResult:
    """Run 3 sample manuscripts through matching, check 0 hard-nos violations."""
    from autoquery.database.models import Manuscript
    from autoquery.evaluation.metrics import hard_nos_violation_rate
    from autoquery.matching.phase1.pipeline import match

    sample_genres = ["literary_fiction", "science_fiction", "romance"]
    total_violations = 0.0

    agents = (
        db.query(Agent)
        .filter(Agent.review_status == REVIEW_STATUS_APPROVED)
        .all()
    )

    for genre in sample_genres:
        ms = Manuscript(
            title=f"Sample {genre}",
            genre=genre,
            audience=["adult"],
        )
        db.add(ms)
        db.commit()
        db.refresh(ms)

        if embedding_model:
            ms.embedding_fulltext = await embedding_model.embed(genre)
            db.commit()

        results = await match(
            ms, agents, db_session=db,
            embedding_model=embedding_model, output_size=20,
        )
        total_violations += hard_nos_violation_rate(results, [])

    return ReadinessResult(
        check_name="sample_matching_no_hard_nos",
        passed=total_violations == 0.0,
        actual_value=total_violations,
        threshold=0.0,
        message=f"Hard-nos violation rate across samples: {total_violations}",
    )


def run_all_readiness_checks(
    db: Session, embedding_model=None,
) -> list[ReadinessResult]:
    """Run all synchronous readiness checks."""
    return [
        check_agent_count(db),
        check_genre_coverage(db),
        check_audience_coverage(db),
        check_all_agents_have_embeddings(db),
    ]


def is_launch_ready(results: list[ReadinessResult]) -> bool:
    """True if all checks passed."""
    return all(r.passed for r in results)
