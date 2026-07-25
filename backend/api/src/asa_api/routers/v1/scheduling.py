"""调度与 AI 角色过程查询接口。"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from asa_api.bootstrap import create_scheduling_repo, get_service_container
from asa_api.dependencies import CurrentUser, get_current_user
from asa_api.middleware.request_id import get_request_id
from asa_api.schemas.common import (
    ApiResponse,
    RuntimeStageListData,
    RuntimeStageResponse,
    WorkerTaskListData,
    WorkerTaskResponse,
)
from asa_core.application.queries.list_runtime_stages import ListRuntimeStagesQuery
from asa_core.application.queries.list_worker_tasks import ListWorkerTasksQuery
from asa_core.application.services.sensitive_text import redact_sensitive_text
from asa_core.domain.agents.role import WorkerRole
from asa_core.domain.scheduling.entities import ExecutionStatus
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["调度与 AI 角色"])


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@router.get(
    "/{project_id}/stages",
    operation_id="list_project_runtime_stages",
)
async def list_project_stages(
    request: Request,
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """按固定 stage_order 返回当前运行实例的全部阶段。"""
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        repository = create_scheduling_repo(session)
        stages = await container.list_runtime_stages_handler.handle(
            ListRuntimeStagesQuery(
                project_id=project_id,
                actor_user_id=current_user.id,
                actor_is_admin=current_user.is_admin,
            ),
            repository=repository,
        )
    data = RuntimeStageListData(
        items=[
            RuntimeStageResponse(
                id=str(stage.id),
                stage_name=stage.stage_name,
                stage_order=stage.stage_order,
                stage_status=stage.stage_status,
                started_at=_iso(stage.started_at),
                finished_at=_iso(stage.finished_at),
                error_message=redact_sensitive_text(
                    stage.error_message,
                    max_length=500,
                ),
            )
            for stage in stages
        ]
    )
    content = ApiResponse[RuntimeStageListData](
        code="PROJECT_STAGES_OK",
        message="查询成功",
        data=data,
        request_id=get_request_id(request),
    ).model_dump(mode="json")
    return JSONResponse(status_code=200, content=content)


@router.get(
    "/{project_id}/workers",
    operation_id="list_project_worker_tasks",
)
async def list_project_workers(
    request: Request,
    project_id: uuid.UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    stage_id: uuid.UUID | None = None,
    worker_role: WorkerRole | None = None,
    task_status: ExecutionStatus | None = None,
    sort: Literal["created_at:asc", "created_at:desc"] = "created_at:asc",
    request_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """分页查询角色任务，并在响应前再次执行敏感信息过滤。"""
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        repository = create_scheduling_repo(session)
        result = await container.list_worker_tasks_handler.handle(
            ListWorkerTasksQuery(
                project_id=project_id,
                actor_user_id=current_user.id,
                actor_is_admin=current_user.is_admin,
                page=page,
                page_size=page_size,
                stage_id=stage_id,
                worker_role=worker_role.value if worker_role is not None else None,
                task_status=task_status.value if task_status is not None else None,
                request_id=request_id,
                sort=sort,
            ),
            repository=repository,
        )
    data = WorkerTaskListData(
        items=[
            WorkerTaskResponse(
                id=str(task.id),
                stage_id=str(task.stage_id),
                worker_role=task.worker_role,
                task_content=redact_sensitive_text(
                    task.task_content,
                    max_length=4000,
                )
                or "",
                task_status=task.task_status,
                result_summary=redact_sensitive_text(
                    task.result_summary,
                    max_length=4000,
                ),
                error_message=redact_sensitive_text(
                    task.error_message,
                    max_length=1000,
                ),
                request_id=str(task.request_id),
                attempt_count=task.attempt_count,
                started_at=_iso(task.started_at),
                finished_at=_iso(task.finished_at),
                created_at=task.created_at.isoformat(),
            )
            for task in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )
    content = ApiResponse[WorkerTaskListData](
        code="PROJECT_WORKERS_OK",
        message="查询成功",
        data=data,
        request_id=get_request_id(request),
    ).model_dump(mode="json")
    return JSONResponse(status_code=200, content=content)
