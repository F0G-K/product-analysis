"""Celery 应用配置。"""

import os

from celery import Celery

_BROKER_URL = os.getenv(
    "ASA_CELERY_BROKER_URL",
    os.getenv("ASA_REDIS_URL", "redis://root:kkkcm520@127.0.0.1:6380/0"),
)

celery_app = Celery(
    "asa_worker",
    broker=_BROKER_URL,
    include=[
        "asa_worker.tasks.stage_tasks",
        "asa_worker.tasks.worker_tasks",
        "asa_worker.tasks.cancel_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)
