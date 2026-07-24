from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from backend.core.enums import TaskStatus, TaskType
from backend.core.errors import (
    BusinessError,
    ErrorCode,
    ExternalServiceError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from backend.domain.ports import (
    AnalysisInputStore,
    EventPublisher,
    TaskFilters,
    TaskQueue,
    TaskRepositoryFactory,
)
from backend.domain.task import Task, TaskActor

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Page:
    items: Sequence[Task]
    total: int
    page: int
    page_size: int


class TaskSchedulerService:
    """通用任务查询、投递、取消和业务重试。"""

    ALLOWED_SORT_FIELDS = frozenset({"created_at", "updated_at", "status"})

    def __init__(
        self,
        repository_factory: TaskRepositoryFactory,
        queue: TaskQueue,
        publisher: EventPublisher,
        input_store: AnalysisInputStore,
    ) -> None:
        self._repository_factory = repository_factory
        self._queue = queue
        self._publisher = publisher
        self._input_store = input_store

    async def get_task(self, task_id: UUID, actor: TaskActor) -> Task:
        async with self._repository_factory(actor.tenant_id) as repository:
            task = await repository.get(task_id)
        if task is None:
            raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
        if not actor.can_view_project(task.project_id):
            raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
        return task

    async def list_tasks(
        self,
        *,
        actor: TaskActor,
        task_type: TaskType | None = None,
        status: TaskStatus | None = None,
        project_id: UUID | None = None,
        created_by: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
    ) -> Page:
        if page < 1 or not 1 <= page_size <= 100:
            raise BusinessError(ErrorCode.VALIDATION_FAILED, "分页参数不合法")
        if sort_by not in self.ALLOWED_SORT_FIELDS:
            raise BusinessError(ErrorCode.VALIDATION_FAILED, "排序字段不合法")
        visible_projects = tuple(actor.project_roles)
        if project_id is not None and not actor.can_view_project(project_id):
            # 对无权限资源返回空列表，避免泄露项目是否存在。
            return Page(items=(), total=0, page=page, page_size=page_size)

        filters = TaskFilters(
            task_type=task_type,
            status=status,
            project_id=project_id,
            created_by=created_by or actor.user_id,
            project_ids=None if actor.is_tenant_admin else visible_projects,
        )
        async with self._repository_factory(actor.tenant_id) as repository:
            items, total = await repository.list(
                filters,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
            )
        return Page(items=items, total=total, page=page, page_size=page_size)

    async def dispatch(self, task_id: UUID, actor: TaskActor) -> str:
        async with self._repository_factory(actor.tenant_id) as repository:
            task = await repository.get(task_id, for_update=True)
            if task is None:
                raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
            task.ensure_actor_can_manage(actor)
            if task.status != TaskStatus.DRAFT:
                raise BusinessError(
                    ErrorCode.BUSINESS_RULE_VIOLATION,
                    "仅草稿任务可以投递",
                )
            if await self._input_store.get(task.id) is None:
                raise BusinessError(
                    ErrorCode.VALIDATION_FAILED,
                    "任务缺少分析输入",
                )
            validating = task.transition(TaskStatus.VALIDATING)
            await repository.save(validating)
            try:
                await repository.commit()
                queue_id = await self._queue.enqueue(task.id, task.task_type, task.tenant_id)
            except Exception as exc:
                await repository.rollback()
                await self._mark_dispatch_failed(
                    tenant_id=task.tenant_id,
                    task_id=task.id,
                    error=exc,
                )
                raise ExternalServiceError(
                    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
                    "任务队列暂不可用",
                    detail=str(exc),
                ) from exc
        await self._publish_status(task, validating)
        return queue_id

    async def cancel(self, task_id: UUID, actor: TaskActor) -> Task:
        async with self._repository_factory(actor.tenant_id) as repository:
            task = await repository.get(task_id, for_update=True)
            if task is None:
                raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
            task.ensure_actor_can_manage(actor)
            if task.status not in Task.CANCELLABLE_STATUSES:
                raise BusinessError(
                    ErrorCode.BUSINESS_RULE_VIOLATION,
                    "当前任务状态不可取消",
                    detail=task.status.value,
                )

            cancelled = task.transition(TaskStatus.CANCELLED)
            await repository.save(cancelled)
            await repository.commit()

        # 先提交取消状态，Worker 即使未被撤销也会在角色边界停止。
        try:
            await self._queue.cancel(task_id, terminate=False)
        except Exception:
            logger.warning("task.queue_cancel_failed", extra={"task_id": str(task_id)})
        await self._publish_status(task, cancelled)
        return cancelled

    async def retry(self, task_id: UUID, actor: TaskActor) -> Task:
        async with self._repository_factory(actor.tenant_id) as repository:
            original = await repository.get(task_id, for_update=True)
            if original is None:
                raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
            original.ensure_actor_can_manage(actor)
            if await repository.has_retry(original.id):
                raise ResourceConflictError(
                    ErrorCode.RESOURCE_CONFLICT,
                    "该失败任务已创建重试任务",
                )
            retried = original.create_retry()
            original = replace(original, retry_count=retried.retry_count)
            await self._input_store.copy(original.id, retried.id)
            await repository.save(original)
            await repository.add(retried)
            try:
                await repository.commit()
                await self._queue.enqueue(
                    retried.id, retried.task_type, retried.tenant_id
                )
            except Exception as exc:
                await repository.rollback()
                # 数据库提交后队列投递可能失败，显式失败状态便于用户重试和审计。
                persisted = await repository.get(retried.id, for_update=True)
                if persisted is not None and persisted.status == TaskStatus.DRAFT:
                    failed = persisted.transition(TaskStatus.VALIDATING).transition(
                        TaskStatus.FAILED,
                        failure_reason="重试任务投递到队列失败",
                        error_details={"phase": "queue_dispatch", "type": type(exc).__name__},
                    )
                    await repository.save(failed)
                    await repository.commit()
                raise ExternalServiceError(
                    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
                    "重试任务投递失败",
                    detail=str(exc),
                ) from exc

        await self._safe_publish(
            "task.retried",
            {
                "task_id": str(retried.id),
                "retry_of_task_id": str(original.id),
                "retry_count": retried.retry_count,
            },
        )
        return retried

    async def _publish_status(self, before: Task, after: Task) -> None:
        await self._safe_publish(
            "task.status_changed",
            {
                "task_id": str(after.id),
                "task_type": after.task_type.value,
                "old_status": before.status.value,
                "new_status": after.status.value,
                "timestamp": after.updated_at.isoformat(),
            },
        )

    async def _safe_publish(self, event: str, payload: dict[str, object]) -> None:
        try:
            await self._publisher.publish(event, payload)
        except Exception:
            logger.warning(
                "task.event_publish_failed",
                extra={"event": event, "task_id": payload.get("task_id")},
                exc_info=True,
            )

    async def _mark_dispatch_failed(
        self,
        *,
        tenant_id: UUID,
        task_id: UUID,
        error: Exception,
    ) -> None:
        async with self._repository_factory(tenant_id) as repository:
            current = await repository.get(task_id, for_update=True)
            if current is None or current.status != TaskStatus.VALIDATING:
                await repository.rollback()
                return
            failed = current.transition(
                TaskStatus.FAILED,
                failure_reason="任务投递到队列失败",
                error_details={"phase": "queue_dispatch", "type": type(error).__name__},
            )
            await repository.save(failed)
            await repository.commit()
