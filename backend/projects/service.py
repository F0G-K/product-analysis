from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.enums import ProjectRole
from backend.core.errors import (
    ErrorCode,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from backend.domain.task import TaskActor
from backend.models.project import ProjectMemberModel, ProjectModel


@dataclass(frozen=True, slots=True)
class Project:
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    status: str
    timezone: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectPage:
    items: tuple[Project, ...]
    total: int
    page: int
    page_size: int


class ProjectService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_project(
        self,
        *,
        actor: TaskActor,
        name: str,
        description: str | None,
        timezone: str,
    ) -> Project:
        can_create = actor.is_tenant_admin or (
            ProjectRole.PROJECT_ADMIN in actor.project_roles.values()
        )
        if not can_create:
            raise PermissionDeniedError(
                ErrorCode.OPERATION_PERMISSION_DENIED,
                "当前角色无权创建项目",
            )
        model = ProjectModel(
            id=uuid4(),
            tenant_id=actor.tenant_id,
            name=name.strip(),
            description=description.strip() if description else None,
            timezone=timezone,
            settings={},
        )
        member = ProjectMemberModel(
            id=uuid4(),
            project_id=model.id,
            user_id=actor.user_id,
            role="project_admin",
        )
        async with self._session_factory() as session, session.begin():
            await self._set_tenant_context(session, actor.tenant_id)
            session.add_all((model, member))
        return self._to_domain(model)

    async def list_projects(
        self,
        *,
        actor: TaskActor,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ProjectPage:
        async with self._session_factory() as session:
            await self._set_tenant_context(session, actor.tenant_id)
            statement = select(ProjectModel).where(
                ProjectModel.tenant_id == actor.tenant_id,
                ProjectModel.deleted_at.is_(None),
            )
            if not actor.is_tenant_admin:
                statement = statement.join(
                    ProjectMemberModel,
                    ProjectMemberModel.project_id == ProjectModel.id,
                ).where(ProjectMemberModel.user_id == actor.user_id)
            if status:
                statement = statement.where(ProjectModel.status == status)
            if search:
                statement = statement.where(ProjectModel.name.ilike(f"%{search.strip()}%"))
            total = int(
                await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
            )
            rows = await session.scalars(
                statement.order_by(ProjectModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            return ProjectPage(
                items=tuple(self._to_domain(row) for row in rows),
                total=total,
                page=page,
                page_size=page_size,
            )

    async def get_project(self, project_id: UUID, actor: TaskActor) -> Project:
        async with self._session_factory() as session:
            await self._set_tenant_context(session, actor.tenant_id)
            statement = select(ProjectModel).where(
                ProjectModel.id == project_id,
                ProjectModel.tenant_id == actor.tenant_id,
                ProjectModel.deleted_at.is_(None),
            )
            if not actor.is_tenant_admin:
                statement = statement.join(
                    ProjectMemberModel,
                    ProjectMemberModel.project_id == ProjectModel.id,
                ).where(ProjectMemberModel.user_id == actor.user_id)
            model = await session.scalar(statement)
        if model is None:
            raise ResourceNotFoundError(ErrorCode.RESOURCE_NOT_FOUND, "项目不存在")
        return self._to_domain(model)

    async def ensure_access(self, project_id: UUID, actor: TaskActor) -> None:
        await self.get_project(project_id, actor)

    @staticmethod
    async def _set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

    @staticmethod
    def _to_domain(model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            description=model.description,
            status=model.status,
            timezone=model.timezone,
            settings=dict(model.settings or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
