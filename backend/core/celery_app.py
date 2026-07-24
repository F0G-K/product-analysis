from __future__ import annotations

from celery import Celery

from backend.core.settings import get_settings

settings = get_settings()
celery_app = Celery("product_analysis")
celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=900,
    task_time_limit=960,
    task_routes={
        "analysis.run_assessment": {"queue": "analysis.assessment"},
        "analysis.run_consistency_check": {"queue": "analysis.consistency_check"},
        "analysis.run_attribution": {"queue": "analysis.attribution"},
    },
    imports=("backend.scheduling.tasks",),
)
