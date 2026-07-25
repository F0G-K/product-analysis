"""项目管理路由。"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from asa_api.bootstrap import (
    create_project_command_handlers,
    create_project_repo,
    get_service_container,
)
from asa_api.dependencies import CurrentUser, get_current_user
from asa_api.middleware.request_id import get_request_id
from asa_api.schemas.common import ApiResponse
from asa_api.schemas.projects import (
    CreateProjectRequest,
    DeleteProjectRequest,
    ProjectCreatedResponse,
    ProjectDetailResponse,
    ProjectListData,
    ProjectOperationResponse,
    ProjectRuntimeResponse,
    ProjectStatisticsResponse,
    ProjectSummaryResponse,
    StartProjectRequest,
    StopProjectRequest,
)
from asa_core.application.commands.create_project import CreateProjectCommand
from asa_core.application.commands.delete_project import DeleteProjectCommand
from asa_core.application.commands.start_project import StartProjectCommand
from asa_core.application.commands.stop_project import StopProjectCommand
from asa_core.application.queries.get_project_detail import GetProjectDetailQuery
from asa_core.application.queries.list_projects import ListProjectsQuery
from asa_core.domain.projects.entities import Project, ProjectDetail, ProjectSummary
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["项目管理"])

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$",
    ),
]


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    return ApiResponse[Any](
        code=code,
        message=message,
        data=data,
        request_id=get_request_id(request),
    ).model_dump(mode="json")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _to_summary(project: Project | ProjectSummary) -> ProjectSummaryResponse:
    return ProjectSummaryResponse(
        id=str(project.id),
        project_name=project.project_name,
        source_type=project.source_type,
        source_path=project.source_path,
        environment_type=project.environment_type,
        project_status=project.project_status,
        last_started_at=_iso(project.last_started_at),
        last_finished_at=_iso(project.last_finished_at),
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


def _to_created(project: Project) -> ProjectCreatedResponse:
    return ProjectCreatedResponse(
        id=str(project.id),
        project_name=project.project_name,
        source_type=project.source_type,
        source_path=project.source_path,
        task_content=project.task_content,
        environment_type=project.environment_type,
        project_status=project.project_status,
        created_by=str(project.created_by),
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


def _to_detail(detail: ProjectDetail) -> ProjectDetailResponse:
    project = detail.project
    runtime = detail.runtime
    return ProjectDetailResponse(
        **_to_summary(project).model_dump(),
        task_content=project.task_content,
        created_by=str(project.created_by),
        stop_requested_at=_iso(project.stop_requested_at),
        runtime=(
            ProjectRuntimeResponse(
                id=str(runtime.id),
                runtime_identifier=runtime.runtime_identifier,
                container_status=runtime.container_status,
                started_at=_iso(runtime.started_at),
                stopped_at=_iso(runtime.stopped_at),
                error_message=runtime.error_message,
            )
            if runtime is not None
            else None
        ),
        statistics=ProjectStatisticsResponse(
            vulnerability_count=detail.statistics.vulnerability_count,
            verified_vulnerability_count=detail.statistics.verified_vulnerability_count,
            attack_path_count=detail.statistics.attack_path_count,
            worker_task_count=detail.statistics.worker_task_count,
        ),
        report_status=detail.report_status,
    )


@router.post("", status_code=201)
async def create_project(
    request: Request,
    body: CreateProjectRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """登记源码来源和评估范围，不同步创建容器。"""

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            project_repo = create_project_repo(session)
            handlers = create_project_command_handlers(session)
            project = await handlers.create.handle(
                CreateProjectCommand(
                    project_name=body.project_name,
                    source_type=body.source_type,
                    source_path=body.source_path,
                    task_content=body.task_content,
                    environment_type=body.environment_type,
                    actor_user_id=current_user.id,
                    request_id=get_request_id(request),
                ),
                project_repo=project_repo,
            )
    return JSONResponse(
        status_code=201,
        content=_ok(
            "PROJECT_CREATED",
            "项目创建成功",
            _to_created(project),
            request,
        ),
    )


@router.get("")
async def list_projects(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_status: str | None = Query(
        default=None,
        pattern=r"^(created|running|completed|failed|stopped)$",
    ),
    source_type: str | None = Query(
        default=None,
        pattern=r"^(local|repository)$",
    ),
    keyword: str | None = Query(default=None, max_length=128),
    sort: str = Query(
        default="created_at:desc",
        pattern=r"^(created_at|updated_at):(asc|desc)$",
    ),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """分页查询当前用户项目；管理员可查看全部项目。"""

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        result = await container.list_projects_handler.handle(
            ListProjectsQuery(
                actor_user_id=current_user.id,
                actor_is_admin=current_user.is_admin,
                page=page,
                page_size=page_size,
                project_status=project_status,
                source_type=source_type,
                keyword=keyword,
                sort=sort,
            ),
            project_repo=create_project_repo(session),
        )
    data = ProjectListData(
        items=[_to_summary(project) for project in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )
    return JSONResponse(
        status_code=200,
        content=_ok("PROJECT_LIST_OK", "查询成功", data, request),
    )


@router.get("/{project_id}")
async def get_project_detail(
    request: Request,
    project_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """查询项目权威详情及持久化统计。"""

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        detail = await container.get_project_detail_handler.handle(
            GetProjectDetailQuery(
                project_id=project_id,
                actor_user_id=current_user.id,
                actor_is_admin=current_user.is_admin,
            ),
            project_repo=create_project_repo(session),
        )
    return JSONResponse(
        status_code=200,
        content=_ok(
            "PROJECT_DETAIL_OK",
            "查询成功",
            _to_detail(detail),
            request,
        ),
    )


@router.post("/{project_id}/start", status_code=202)
async def start_project(
    request: Request,
    project_id: UUID,
    body: StartProjectRequest,
    idempotency_key: IdempotencyKey,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """受理项目启动，事务提交后再投递异步任务。"""

    del body
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            handlers = create_project_command_handlers(session)
            result = await handlers.start.handle(
                StartProjectCommand(
                    project_id=project_id,
                    actor_user_id=current_user.id,
                    actor_is_admin=current_user.is_admin,
                    request_id=get_request_id(request),
                    idempotency_key=idempotency_key,
                ),
                project_repo=create_project_repo(session),
            )

    if result.resources is not None:
        await container.project_task_dispatcher.dispatch_start(
            project_id=project_id,
            resources=result.resources,
            request_id=get_request_id(request),
            idempotency_key=idempotency_key,
        )
    return JSONResponse(
        status_code=202,
        content=_ok(
            "PROJECT_START_ACCEPTED",
            "项目启动请求已受理",
            ProjectOperationResponse(**result.response_data),
            request,
        ),
    )


@router.post("/{project_id}/stop", status_code=202)
async def stop_project(
    request: Request,
    project_id: UUID,
    body: StopProjectRequest,
    idempotency_key: IdempotencyKey,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """记录协作取消意图，最终状态由 Worker 收敛。"""

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            handlers = create_project_command_handlers(session)
            result = await handlers.stop.handle(
                StopProjectCommand(
                    project_id=project_id,
                    actor_user_id=current_user.id,
                    actor_is_admin=current_user.is_admin,
                    request_id=get_request_id(request),
                    idempotency_key=idempotency_key,
                    reason=body.reason,
                ),
                project_repo=create_project_repo(session),
            )

    if not result.replayed:
        await container.project_task_dispatcher.dispatch_stop(
            project_id=project_id,
            request_id=get_request_id(request),
            idempotency_key=idempotency_key,
        )
    return JSONResponse(
        status_code=202,
        content=_ok(
            "PROJECT_STOP_ACCEPTED",
            "项目停止请求已受理",
            ProjectOperationResponse(**result.response_data),
            request,
        ),
    )


@router.delete("/{project_id}", status_code=202)
async def delete_project(
    request: Request,
    project_id: UUID,
    body: DeleteProjectRequest,
    idempotency_key: IdempotencyKey,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """受理非运行项目的异步清理。"""

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            handlers = create_project_command_handlers(session)
            result = await handlers.delete.handle(
                DeleteProjectCommand(
                    project_id=project_id,
                    actor_user_id=current_user.id,
                    actor_is_admin=current_user.is_admin,
                    request_id=get_request_id(request),
                    idempotency_key=idempotency_key,
                    confirm_project_name=body.confirm_project_name,
                ),
                project_repo=create_project_repo(session),
            )

    if not result.replayed:
        await container.project_task_dispatcher.dispatch_delete(
            project_id=project_id,
            request_id=get_request_id(request),
            idempotency_key=idempotency_key,
        )
    return JSONResponse(
        status_code=202,
        content=_ok(
            "PROJECT_DELETE_ACCEPTED",
            "项目删除请求已受理",
            ProjectOperationResponse(**result.response_data),
            request,
        ),
    )
