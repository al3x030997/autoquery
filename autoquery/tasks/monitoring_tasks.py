"""Celery tasks for monitoring and health checks."""
from __future__ import annotations

import logging

from autoquery.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="monitoring.check_ollama_health")
def check_ollama_health() -> dict:
    """Check Ollama availability. Runs every 5 minutes via Beat."""
    from autoquery.monitoring.health import check_ollama

    result = check_ollama()
    if result["status"] != "ok":
        logger.error("ALERT: Ollama unreachable — %s", result.get("error", "unknown"))
    return result


@celery_app.task(name="monitoring.daily_report")
def daily_report() -> dict:
    """Generate daily monitoring report. Runs daily via Beat."""
    from autoquery.database.db import SessionLocal
    from autoquery.monitoring.health import check_system_health

    db = SessionLocal()
    try:
        health = check_system_health(db)

        if health["status"] == "critical":
            logger.critical("DAILY REPORT: System status CRITICAL — %s", health)
        elif health["status"] != "ok":
            logger.warning("DAILY REPORT: System status %s — %s", health["status"], health)
        else:
            logger.info("DAILY REPORT: System status OK — DB: %d approved agents", health["database"].get("agents_approved", 0))

        return health
    finally:
        db.close()
