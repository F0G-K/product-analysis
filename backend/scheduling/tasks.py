from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded

from backend.core.celery_app import celery_app
from backend.core.enums import TaskType
from backend.core.errors import ExternalServiceError
from backend.scheduling.runtime import get_executor_scope


async def _execute(task_id: str, tenant_id: str, expected_type: TaskType) -> dict[str, Any]:
    async with get_executor_scope() as executor:
        outcome = await executor.execute(
            tenant_id=UUID(tenant_id),
            task_id=UUID(task_id),
            expected_task_type=expected_type,
        )
    if outcome.task.task_type != expected_type:
        raise ValueError(
            f"任务类型与队列不一致: expected={expected_type.value}, "
            f"actual={outcome.task.task_type.value}"
        )
    return {
        "task_id": str(outcome.task.id),
        "status": outcome.task.status.value,
        "awaiting_review": outcome.awaiting_review,
    }


async def _mark_failed(task_id: str, tenant_id: str, error: Exception) -> None:
    async with get_executor_scope() as executor:
        await executor.mark_failed(
            tenant_id=UUID(tenant_id),
            task_id=UUID(task_id),
            error=error,
        )


def _run(
    celery_task: Any,
    task_id: str,
    tenant_id: str,
    task_type: TaskType,
) -> dict[str, Any]:
    try:
        return asyncio.run(_execute(task_id, tenant_id, task_type))
    except SoftTimeLimitExceeded as exc:
        # Executor 已在角色边界持久化过程状态，超时后保留检查点供业务重试。
        asyncio.run(_mark_failed(task_id, tenant_id, exc))
        raise
    except (ExternalServiceError, ConnectionError, TimeoutError) as exc:
        if celery_task.request.retries >= celery_task.max_retries:
            asyncio.run(_mark_failed(task_id, tenant_id, exc))
            raise
        raise celery_task.retry(
            exc=exc,
            countdown=min(60, 2 ** celery_task.request.retries),
        ) from exc


@celery_app.task(
    name="analysis.run_assessment",
    bind=True,
    max_retries=3,
)
def run_assessment(self: Any, *, task_id: str, tenant_id: str) -> dict[str, Any]:
    # Celery 的任务装饰器运行时动态生成 Task 类型，静态检查无法推断。
    return _run(self, task_id, tenant_id, TaskType.ASSESSMENT)


@celery_app.task(
    name="analysis.run_consistency_check",
    bind=True,
    max_retries=3,
)
def run_consistency_check(self: Any, *, task_id: str, tenant_id: str) -> dict[str, Any]:
    return _run(self, task_id, tenant_id, TaskType.CONSISTENCY_CHECK)


@celery_app.task(
    name="analysis.run_attribution",
    bind=True,
    max_retries=3,
)
def run_attribution(self: Any, *, task_id: str, tenant_id: str) -> dict[str, Any]:
    return _run(self, task_id, tenant_id, TaskType.ATTRIBUTION)
