"""分页查询项目角色任务。"""

import uuid
from dataclasses import dataclass

from asa_core.application.ports.scheduling_repository import (
    SchedulingRepository,
    WorkerTaskListResult,
)
from asa_core.domain.projects.exceptions import (
    ProjectAccessDenied,
    ProjectNotFound,
)


@dataclass(frozen=True, slots=True)
class ListWorkerTasksQuery:
    project_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_is_admin: bool
    page: int = 1
    page_size: int = 20
    stage_id: uuid.UUID | None = None
    worker_role: str | None = None
    task_status: str | None = None
    request_id: uuid.UUID | None = None
    sort: str = "created_at:asc"


class ListWorkerTasksHandler:
    async def handle(
        self,
        query: ListWorkerTasksQuery,
        *,
        repository: SchedulingRepository,
    ) -> WorkerTaskListResult:
        project = await repository.find_accessible_project(
            query.project_id,
            actor_user_id=query.actor_user_id,
            actor_is_admin=query.actor_is_admin,
        )
        if project is None:
            if await repository.project_exists(query.project_id):
                raise ProjectAccessDenied()
            raise ProjectNotFound()
        return await repository.list_worker_tasks(
            query.project_id,
            page=query.page,
            page_size=query.page_size,
            stage_id=query.stage_id,
            worker_role=query.worker_role,
            task_status=query.task_status,
            request_id=query.request_id,
            sort=query.sort,
        )
