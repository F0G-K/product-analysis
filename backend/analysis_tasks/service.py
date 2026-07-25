from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID, uuid4

from backend.core.enums import ProjectRole, TaskStatus, TaskType
from backend.core.errors import ErrorCode, PermissionDeniedError
from backend.core.settings import Settings
from backend.domain.ports import AnalysisInputStore, TaskRepositoryFactory
from backend.domain.task import ModelBinding, Task, TaskActor


class ProjectAccessChecker(Protocol):
    async def ensure_access(self, project_id: UUID, actor: TaskActor) -> None: ...


class AnalysisTaskCreationService:
    def __init__(
        self,
        repository_factory: TaskRepositoryFactory,
        input_store: AnalysisInputStore,
        project_access: ProjectAccessChecker,
        settings: Settings,
    ) -> None:
        self._repository_factory = repository_factory
        self._input_store = input_store
        self._project_access = project_access
        self._settings = settings

    async def create(
        self,
        *,
        actor: TaskActor,
        project_id: UUID,
        task_type: TaskType,
        title: str,
        description: str | None,
        query: str,
        input_data: Mapping[str, Any],
    ) -> Task:
        await self._project_access.ensure_access(project_id, actor)
        if not actor.is_tenant_admin and actor.role_for(project_id) == ProjectRole.VIEWER:
            raise PermissionDeniedError(
                ErrorCode.OPERATION_PERMISSION_DENIED,
                "只读成员无权创建分析任务",
            )
        task = Task(
            id=uuid4(),
            tenant_id=actor.tenant_id,
            project_id=project_id,
            task_type=task_type,
            status=TaskStatus.DRAFT,
            title=title.strip(),
            description=description.strip() if description else None,
            model_binding=ModelBinding(
                name=self._settings.llm_default_model,
                version=self._settings.llm_default_model_version,
                prompt_version=self._settings.llm_prompt_version,
            ),
            created_by=actor.user_id,
        )
        payload = {
            "query": query.strip(),
            "input_data": dict(input_data),
            "retrieval_filters": {},
            "check_items": [],
        }
        async with self._repository_factory(actor.tenant_id) as repository:
            await repository.add(task)
            try:
                await self._input_store.put(task.id, payload)
                await repository.commit()
            except Exception:
                await repository.rollback()
                raise
        return task
