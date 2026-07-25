"""查询项目阶段状态。"""

import uuid
from dataclasses import dataclass

from asa_core.application.ports.scheduling_repository import SchedulingRepository
from asa_core.domain.projects.exceptions import ProjectNotFound
from asa_core.domain.scheduling.entities import RuntimeStage
from asa_core.domain.scheduling.exceptions import ProjectRuntimeNotFound


@dataclass(frozen=True, slots=True)
class ListRuntimeStagesQuery:
    project_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_is_admin: bool


class ListRuntimeStagesHandler:
    async def handle(
        self,
        query: ListRuntimeStagesQuery,
        *,
        repository: SchedulingRepository,
    ) -> list[RuntimeStage]:
        project = await repository.find_accessible_project(
            query.project_id,
            actor_user_id=query.actor_user_id,
            actor_is_admin=query.actor_is_admin,
        )
        if project is None:
            if await repository.project_exists(query.project_id):
                from asa_core.domain.projects.exceptions import ProjectAccessDenied

                raise ProjectAccessDenied()
            raise ProjectNotFound()
        stages = await repository.list_stages(query.project_id)
        if not stages:
            raise ProjectRuntimeNotFound()
        return stages
