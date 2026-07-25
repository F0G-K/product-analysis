"""API 进程中的 Celery 阶段消息适配器。"""

import os

from asa_core.application.ports.stage_task_dispatcher import StageTaskMessage


class CeleryApiStageDispatcher:
    """延迟创建 Celery 客户端，避免导入阶段访问 Broker。"""

    async def dispatch_stage(self, message: StageTaskMessage) -> None:
        from celery import Celery

        broker_url = os.getenv(
            "ASA_CELERY_BROKER_URL",
            os.getenv("ASA_REDIS_URL", "redis://root:kkkcm520@127.0.0.1:6380/0"),
        )
        celery_app = Celery(
            "asa_api_dispatcher",
            broker=broker_url,
        )
        celery_app.send_task(
            "asa.scheduler.execute_stage",
            kwargs={
                "project_id": str(message.project_id),
                "stage_id": str(message.stage_id),
                "request_id": str(message.request_id),
                "idempotency_key": message.idempotency_key,
                "schema_version": message.schema_version,
            },
            queue="scheduler",
        )
