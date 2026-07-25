from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from backend.api.deps import ProjectServiceDep, TaskActorDep
from backend.schemas.common import APIResponse, PageData
from backend.schemas.project import ProjectCreateRequest, ProjectResponse

router = APIRouter(prefix="/projects", tags=["项目"])


def _request_id(request: Request) -> str:
    return str(request.state.request_id)


@router.post(
    "",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    service: ProjectServiceDep,
    actor: TaskActorDep,
) -> APIResponse[ProjectResponse]:
    project = await service.create_project(
        actor=actor,
        name=payload.name,
        description=payload.description,
        timezone=payload.timezone,
    )
    return APIResponse(
        data=ProjectResponse.from_domain(project),
        request_id=_request_id(request),
    )


@router.get("", response_model=APIResponse[PageData[ProjectResponse]])
async def list_projects(
    request: Request,
    service: ProjectServiceDep,
    actor: TaskActorDep,
    project_status: Annotated[str | None, Query(alias="status")] = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PageData[ProjectResponse]]:
    result = await service.list_projects(
        actor=actor,
        status=project_status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return APIResponse(
        data=PageData(
            items=[ProjectResponse.from_domain(item) for item in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        ),
        request_id=_request_id(request),
    )


@router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def get_project(
    project_id: UUID,
    request: Request,
    service: ProjectServiceDep,
    actor: TaskActorDep,
) -> APIResponse[ProjectResponse]:
    project = await service.get_project(project_id, actor)
    return APIResponse(
        data=ProjectResponse.from_domain(project),
        request_id=_request_id(request),
    )
