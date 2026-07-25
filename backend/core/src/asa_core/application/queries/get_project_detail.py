"""查询项目详情用例。"""

import uuid
from dataclasses import dataclass

from asa_core.application.ports.project_repository import ProjectRepository
from asa_core.domain.projects.entities import ProjectDetail
from asa_core.domain.projects.exceptions import ProjectNotFound


@dataclass(frozen=True)
class GetProjectDetailQuery:
    project_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_is_admin: bool


class GetProjectDetailHandler:
    """返回项目、运行环境、统计与最新报告状态。"""

    async def handle(
        self,
        query: GetProjectDetailQuery,
        *,
        project_repo: ProjectRepository,
    ) -> ProjectDetail:
        detail = await project_repo.get_detail(
            query.project_id,
            actor_user_id=query.actor_user_id,
            actor_is_admin=query.actor_is_admin,
        )
        if detail is None:
            raise ProjectNotFound()
        return detail
