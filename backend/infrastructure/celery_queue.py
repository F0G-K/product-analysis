from __future__ import annotations

from uuid import UUID

from celery import Celery

from backend.core.enums import TaskType


class CeleryTaskQueue:
    TASK_NAMES = {
        TaskType.ASSESSMENT: "analysis.run_assessment",
        TaskType.CONSISTENCY_CHECK: "analysis.run_consistency_check",
        TaskType.ATTRIBUTION: "analysis.run_attribution",
    }

    def __init__(self, app: Celery) -> None:
        self._app = app

    async def enqueue(
        self,
        task_id: UUID,
        task_type: TaskType,
        tenant_id: UUID,
    ) -> str:
        result = self._app.send_task(
            self.TASK_NAMES[task_type],
            kwargs={"task_id": str(task_id), "tenant_id": str(tenant_id)},
            task_id=str(task_id),
            queue=self._queue_name(task_type),
        )
        return str(result.id)

    async def cancel(self, task_id: UUID, *, terminate: bool = False) -> None:
        self._app.control.revoke(str(task_id), terminate=terminate)

    @staticmethod
    def _queue_name(task_type: TaskType) -> str:
        return f"analysis.{task_type.value}"
