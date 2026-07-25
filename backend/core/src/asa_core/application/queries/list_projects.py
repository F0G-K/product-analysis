"""查询项目列表用例。"""

import uuid
from dataclasses import dataclass

from asa_core.application.ports.project_repository import (
    ProjectListResult,
    ProjectRepository,
)


@dataclass(frozen=True)
class ListProjectsQuery:
    actor_user_id: uuid.UUID
    actor_is_admin: bool
    page: int = 1
    page_size: int = 20
    project_status: str | None = None
    source_type: str | None = None
    keyword: str | None = None
    sort: str = "created_at:desc"


class ListProjectsHandler:
    """分页查询当前用户可访问项目。"""

    async def handle(
        self,
        query: ListProjectsQuery,
        *,
        project_repo: ProjectRepository,
    ) -> ProjectListResult:
        return await project_repo.list_accessible(
            actor_user_id=query.actor_user_id,
            actor_is_admin=query.actor_is_admin,
            page=query.page,
            page_size=query.page_size,
            project_status=query.project_status,
            source_type=query.source_type,
            keyword=query.keyword.strip() if query.keyword else None,
            sort=query.sort,
        )
