"""Celery 调度投递适配器。"""

from asa_core.application.ports.stage_task_dispatcher import (
    StageTaskDispatcher,
    StageTaskMessage,
    WorkerTaskMessage,
)

from asa_worker.celery_app import celery_app


class CeleryStageTaskDispatcher(StageTaskDispatcher):
    """只投递 ID 消息，不向 Broker 发送 ORM、源码或密钥。"""

    async def dispatch_stage(self, message: StageTaskMessage) -> None:
        celery_app.send_task(
            "asa.scheduler.execute_stage",
            kwargs=self._stage_payload(message),
            queue="scheduler",
        )

    async def dispatch_workers(self, messages: list[WorkerTaskMessage]) -> None:
        for message in messages:
            celery_app.send_task(
                "asa.agents.execute_worker",
                kwargs=self._worker_payload(message),
                queue="agents",
            )

    @staticmethod
    def _stage_payload(message: StageTaskMessage) -> dict[str, object]:
        return {
            "project_id": str(message.project_id),
            "stage_id": str(message.stage_id),
            "request_id": str(message.request_id),
            "idempotency_key": message.idempotency_key,
            "schema_version": message.schema_version,
        }

    @classmethod
    def _worker_payload(cls, message: WorkerTaskMessage) -> dict[str, object]:
        payload = cls._stage_payload(
            StageTaskMessage(
                project_id=message.project_id,
                stage_id=message.stage_id,
                request_id=message.request_id,
                idempotency_key=message.idempotency_key,
                schema_version=message.schema_version,
            )
        )
        payload["worker_task_id"] = str(message.worker_task_id)
        return payload
