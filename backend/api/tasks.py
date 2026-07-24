from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from backend.api.deps import TaskActorDep, TaskServiceDep
from backend.core.enums import TaskStatus, TaskType
from backend.schemas.common import APIResponse, PageData
from backend.schemas.task import TaskResponse

router = APIRouter(prefix="/tasks", tags=["通用任务"])


def _request_id(request: Request) -> str:
    return str(request.state.request_id)


@router.get("", response_model=APIResponse[PageData[TaskResponse]])
async def list_tasks(
    request: Request,
    service: TaskServiceDep,
    actor: TaskActorDep,
    task_type: TaskType | None = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    project_id: UUID | None = None,
    created_by: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: str = "created_at",
) -> APIResponse[PageData[TaskResponse]]:
    result = await service.list_tasks(
        actor=actor,
        task_type=task_type,
        status=task_status,
        project_id=project_id,
        created_by=created_by,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    return APIResponse(
        data=PageData(
            items=[TaskResponse.from_domain(task) for task in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        ),
        request_id=_request_id(request),
    )


@router.get("/{task_id}", response_model=APIResponse[TaskResponse])
async def get_task(
    task_id: UUID,
    request: Request,
    service: TaskServiceDep,
    actor: TaskActorDep,
) -> APIResponse[TaskResponse]:
    task = await service.get_task(task_id, actor)
    return APIResponse(data=TaskResponse.from_domain(task), request_id=_request_id(request))


@router.post(
    "/{task_id}/cancel",
    response_model=APIResponse[None],
    status_code=status.HTTP_200_OK,
)
async def cancel_task(
    task_id: UUID,
    request: Request,
    service: TaskServiceDep,
    actor: TaskActorDep,
) -> APIResponse[None]:
    await service.cancel(task_id, actor)
    return APIResponse(data=None, request_id=_request_id(request))


@router.post(
    "/{task_id}/retry",
    response_model=APIResponse[None],
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_task(
    task_id: UUID,
    request: Request,
    service: TaskServiceDep,
    actor: TaskActorDep,
) -> APIResponse[None]:
    await service.retry(task_id, actor)
    return APIResponse(data=None, request_id=_request_id(request))
