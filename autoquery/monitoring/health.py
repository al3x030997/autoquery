"""System health checks."""
from __future__ import annotations

import logging
import os

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from autoquery.database.models import Agent, OptOutRequest

logger = logging.getLogger(__name__)


def check_db(db: Session) -> dict:
    """Check database connectivity and basic stats."""
    try:
        db.execute(text("SELECT 1"))
        agent_count = db.query(Agent).count()
        approved = db.query(Agent).filter(Agent.review_status == "approved").count()
        return {"status": "ok", "agents_total": agent_count, "agents_approved": approved}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_redis() -> dict:
    """Check Redis connectivity."""
    try:
        import redis

        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(url, socket_timeout=3)
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_ollama() -> dict:
    """Check Ollama connectivity."""
    try:
        url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        resp = httpx.get(f"{url}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"status": "ok", "models": models}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_pending_opt_outs(db: Session) -> dict:
    """Check for unprocessed opt-out requests."""
    from datetime import datetime, timedelta, timezone

    pending = db.query(OptOutRequest).filter(OptOutRequest.processed != True).count()  # noqa: E712
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    overdue = (
        db.query(OptOutRequest)
        .filter(OptOutRequest.processed != True, OptOutRequest.created_at < cutoff)  # noqa: E712
        .count()
    )
    return {"pending": pending, "overdue_72h": overdue}


def check_system_health(db: Session) -> dict:
    """Run all health checks and return combined status."""
    db_status = check_db(db)
    redis_status = check_redis()
    ollama_status = check_ollama()
    opt_outs = check_pending_opt_outs(db)

    overall = "ok"
    if db_status["status"] != "ok":
        overall = "critical"
    elif redis_status["status"] != "ok":
        overall = "degraded"
    elif ollama_status["status"] != "ok":
        overall = "degraded"
    elif opt_outs["overdue_72h"] > 0:
        overall = "warning"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "ollama": ollama_status,
        "opt_outs": opt_outs,
    }
