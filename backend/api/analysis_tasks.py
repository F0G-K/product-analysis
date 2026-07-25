from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, status

from backend.api.deps import AnalysisTaskCreationServiceDep, TaskActorDep
from backend.schemas.analysis_task import AnalysisTaskCreateRequest
from backend.schemas.common import APIResponse
from backend.schemas.task import TaskResponse

router = APIRouter(prefix="/projects", tags=["分析任务"])


@router.post(
    "/{project_id}/analysis-tasks",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis_task(
    project_id: UUID,
    payload: AnalysisTaskCreateRequest,
    request: Request,
    service: AnalysisTaskCreationServiceDep,
    actor: TaskActorDep,
) -> APIResponse[TaskResponse]:
    task = await service.create(
        actor=actor,
        project_id=project_id,
        task_type=payload.task_type,
        title=payload.title,
        description=payload.description,
        query=payload.query,
        input_data=payload.input_data,
    )
    return APIResponse(
        data=TaskResponse.from_domain(task),
        request_id=str(request.state.request_id),
    )
