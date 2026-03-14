import os

from celery import Celery
from celery.schedules import crontab

redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "autoquery",
    broker=redis_url,
    backend=redis_url,
    include=[
        "autoquery.crawler.tasks",
        "autoquery.crawler.orchestrator",
        "autoquery.tasks.compliance_tasks",
        "autoquery.tasks.monitoring_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "process-pending-opt-outs": {
            "task": "compliance.process_pending_opt_outs",
            "schedule": crontab(minute=0),  # every hour
        },
        "check-opt-out-sla": {
            "task": "compliance.check_opt_out_sla",
            "schedule": crontab(hour=8, minute=0),  # daily at 08:00 UTC
        },
        "cleanup-stale-sessions": {
            "task": "compliance.cleanup_stale_sessions",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # weekly, Sunday 03:00
        },
        "check-ollama-health": {
            "task": "monitoring.check_ollama_health",
            "schedule": 300.0,  # every 5 minutes
        },
        "daily-monitoring-report": {
            "task": "monitoring.daily_report",
            "schedule": crontab(hour=7, minute=0),  # daily at 07:00 UTC
        },
    },
)
