from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from backend.ai.state import AnalysisOutcome, ReviewDecision
from backend.core.enums import TaskStatus, TaskType
from backend.core.errors import (
    AnalysisError,
    ErrorCode,
    ExternalServiceError,
    ResourceNotFoundError,
    TaskAlreadyRunningError,
    TaskCancelledError,
)
from backend.domain.ports import (
    AnalysisInputStore,
    EventPublisher,
    LockManager,
    ResumableWorkflowRunner,
    TaskRepositoryFactory,
)


class TaskExecutor:
    """Celery Worker 调用入口，保证同一任务只有一个执行实例。"""

    LOCK_TTL_SECONDS = 16 * 60

    def __init__(
        self,
        repository_factory: TaskRepositoryFactory,
        input_store: AnalysisInputStore,
        lock_manager: LockManager,
        publisher: EventPublisher,
        workflow: ResumableWorkflowRunner,
    ) -> None:
        self._repository_factory = repository_factory
        self._input_store = input_store
        self._lock_manager = lock_manager
        self._publisher = publisher
        self._workflow = workflow

    async def execute(
        self,
        *,
        tenant_id: UUID,
        task_id: UUID,
        expected_task_type: TaskType | None = None,
    ) -> AnalysisOutcome:
        lock_key = f"task:lock:{task_id}"
        async with self._lock_manager.lock(
            lock_key, ttl_seconds=self.LOCK_TTL_SECONDS
        ) as acquired:
            if not acquired:
                raise TaskAlreadyRunningError(str(task_id))

            async with self._repository_factory(tenant_id) as repository:
                task = await repository.get(task_id, for_update=True)
                if task is None:
                    raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
                if task.status == TaskStatus.CANCELLED:
                    raise AnalysisError(ErrorCode.ANALYSIS_FAILED, "任务已取消")
                if task.status not in {
                    TaskStatus.DRAFT,
                    TaskStatus.VALIDATING,
                    TaskStatus.ANALYZING,
                }:
                    raise AnalysisError(
                        ErrorCode.ANALYSIS_FAILED,
                        "任务已被执行或状态不合法",
                        detail=task.status.value,
                    )
                if expected_task_type is not None and task.task_type != expected_task_type:
                    raise AnalysisError(
                        ErrorCode.ANALYSIS_FAILED,
                        "任务类型与执行队列不一致",
                        detail=(
                            f"expected={expected_task_type.value}, "
                            f"actual={task.task_type.value}"
                        ),
                    )

                payload = await self._input_store.get(task_id)
                if payload is None:
                    raise AnalysisError(ErrorCode.ANALYSIS_FAILED, "任务分析输入不存在")
                await repository.commit()

            try:
                outcome = await self._workflow.start(
                    task=task,
                    input_data=self._mapping(payload, "input_data"),
                    query=str(payload.get("query", "")),
                    retrieval_filters=self._mapping(payload, "retrieval_filters"),
                    check_items=tuple(payload.get("check_items", ())),
                )
            except TaskCancelledError:
                raise
            except (ExternalServiceError, ConnectionError, TimeoutError):
                # 交由 Celery 指数退避重试，达到上限后由任务包装器落失败状态。
                raise
            except Exception as exc:
                await self._mark_failed(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    error=exc,
                )
                raise

            async with self._repository_factory(tenant_id) as repository:
                # 再次锁定并读取最新状态，取消请求永远优先于 Worker 结果。
                current = await repository.get(task_id, for_update=True)
                if current is None:
                    raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
                if current.status == TaskStatus.CANCELLED:
                    await repository.rollback()
                    raise TaskCancelledError(str(task_id))
                await repository.save(outcome.task)
                await repository.commit()

            return outcome

    async def resume(
        self,
        *,
        tenant_id: UUID,
        task_id: UUID,
        decision: ReviewDecision,
    ) -> AnalysisOutcome:
        async with self._lock_manager.lock(
            f"task:lock:{task_id}", ttl_seconds=self.LOCK_TTL_SECONDS
        ) as acquired:
            if not acquired:
                raise TaskAlreadyRunningError(str(task_id))
            async with self._repository_factory(tenant_id) as repository:
                task = await repository.get(task_id, for_update=True)
                if task is None:
                    raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
                if task.status != TaskStatus.PENDING_REVIEW:
                    raise AnalysisError(
                        ErrorCode.ANALYSIS_FAILED,
                        "仅待确认任务可以恢复",
                        detail=task.status.value,
                    )
                await repository.commit()
            return await self._workflow.resume(task_id=str(task_id), decision=decision)

    async def mark_failed(
        self,
        *,
        tenant_id: UUID,
        task_id: UUID,
        error: Exception,
    ) -> None:
        await self._mark_failed(tenant_id=tenant_id, task_id=task_id, error=error)

    async def _mark_failed(
        self,
        *,
        tenant_id: UUID,
        task_id: UUID,
        error: Exception,
    ) -> None:
        async with self._repository_factory(tenant_id) as repository:
            current = await repository.get(task_id, for_update=True)
            if current is None or current.status == TaskStatus.CANCELLED:
                await repository.rollback()
                return
            if current.status == TaskStatus.DRAFT:
                current = current.transition(TaskStatus.VALIDATING)
            if current.status not in {TaskStatus.VALIDATING, TaskStatus.ANALYZING}:
                await repository.rollback()
                return
            failed = current.transition(
                TaskStatus.FAILED,
                failure_reason=str(error) or type(error).__name__,
                error_details={
                    "type": type(error).__name__,
                    "phase": "workflow",
                },
            )
            await repository.save(failed)
            await repository.commit()
        await self._publisher.publish(
            "task.failed",
            {
                "task_id": str(task_id),
                "task_type": failed.task_type.value,
                "failure_reason": failed.failure_reason,
            },
        )

    @staticmethod
    def _mapping(payload: Mapping[str, Any], field: str) -> Mapping[str, Any]:
        value = payload.get(field, {})
        if not isinstance(value, Mapping):
            raise AnalysisError(
                ErrorCode.ANALYSIS_FAILED,
                "任务输入格式不合法",
                detail=field,
            )
        return value
