from __future__ import annotations

from typing import Annotated, Protocol, cast

from fastapi import Depends, Request

from backend.analysis_tasks.service import AnalysisTaskCreationService
from backend.core.errors import AuthenticationError, ErrorCode
from backend.domain.task import TaskActor
from backend.projects.service import ProjectService
from backend.scheduling.service import TaskSchedulerService


class ActorResolver(Protocol):
    async def __call__(self, request: Request) -> TaskActor: ...


def get_task_service(request: Request) -> TaskSchedulerService:
    service = getattr(request.app.state, "task_scheduler_service", None)
    if not isinstance(service, TaskSchedulerService):
        raise RuntimeError("task_scheduler_service 未配置")
    return service


def get_project_service(request: Request) -> ProjectService:
    service = getattr(request.app.state, "project_service", None)
    if not isinstance(service, ProjectService):
        raise RuntimeError("project_service 未配置")
    return service


def get_analysis_task_creation_service(request: Request) -> AnalysisTaskCreationService:
    service = getattr(request.app.state, "analysis_task_creation_service", None)
    if not isinstance(service, AnalysisTaskCreationService):
        raise RuntimeError("analysis_task_creation_service 未配置")
    return service


async def get_task_actor(request: Request) -> TaskActor:
    resolver = getattr(request.app.state, "task_actor_resolver", None)
    if resolver is None:
        raise AuthenticationError(ErrorCode.INVALID_CREDENTIALS, "未配置认证服务")
    return await cast(ActorResolver, resolver)(request)


TaskServiceDep = Annotated[TaskSchedulerService, Depends(get_task_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
AnalysisTaskCreationServiceDep = Annotated[
    AnalysisTaskCreationService, Depends(get_analysis_task_creation_service)
]
TaskActorDep = Annotated[TaskActor, Depends(get_task_actor)]
