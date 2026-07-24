from __future__ import annotations

import logging

from backend.core.enums import TaskStatus
from backend.core.errors import ErrorCode, ResourceNotFoundError, TaskCancelledError
from backend.domain.ports import EventPublisher, TaskRepositoryFactory
from backend.domain.task import Task

logger = logging.getLogger(__name__)


class RepositoryExecutionGuard:
    """从持久化层读取最新状态，解决取消与 Worker 执行竞态。"""

    def __init__(self, repository_factory: TaskRepositoryFactory) -> None:
        self._repository_factory = repository_factory

    async def ensure_active(self, task: Task) -> None:
        async with self._repository_factory(task.tenant_id) as repository:
            current = await repository.get(task.id)
        if current is None:
            raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
        if current.status == TaskStatus.CANCELLED:
            raise TaskCancelledError(str(task.id))


class RepositoryProgressRecorder:
    def __init__(
        self,
        repository_factory: TaskRepositoryFactory,
        publisher: EventPublisher | None = None,
    ) -> None:
        self._repository_factory = repository_factory
        self._publisher = publisher

    async def record(self, task: Task) -> None:
        async with self._repository_factory(task.tenant_id) as repository:
            current = await repository.get(task.id, for_update=True)
            if current is None:
                raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
            if current.status == TaskStatus.CANCELLED:
                await repository.rollback()
                raise TaskCancelledError(str(task.id))
            await repository.save(task)
            await repository.commit()
        if self._publisher is not None and current.status != task.status:
            try:
                await self._publisher.publish(
                    "task.status_changed",
                    {
                        "task_id": str(task.id),
                        "task_type": task.task_type.value,
                        "old_status": current.status.value,
                        "new_status": task.status.value,
                        "timestamp": task.updated_at.isoformat(),
                    },
                )
            except Exception:
                logger.warning(
                    "task.progress_publish_failed",
                    extra={"task_id": str(task.id), "status": task.status.value},
                    exc_info=True,
                )
