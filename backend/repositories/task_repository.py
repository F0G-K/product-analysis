from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.enums import TaskStatus, TaskType
from backend.domain.ports import TaskFilters
from backend.domain.task import ModelBinding, Task
from backend.models.task import TaskModel


class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def get(self, task_id: UUID, *, for_update: bool = False) -> Task | None:
        await self._set_tenant_context()
        statement = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.tenant_id == self._tenant_id,
        )
        if for_update:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return self._to_domain(model) if model else None

    async def list(
        self,
        filters: TaskFilters,
        *,
        page: int,
        page_size: int,
        sort_by: str,
    ) -> tuple[Sequence[Task], int]:
        await self._set_tenant_context()
        base = select(TaskModel).where(TaskModel.tenant_id == self._tenant_id)
        base = self._apply_filters(base, filters)
        count_statement = select(func.count()).select_from(base.subquery())
        total = int(await self._session.scalar(count_statement) or 0)

        sort_column = getattr(TaskModel, sort_by)
        rows = await self._session.scalars(
            base.order_by(sort_column.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return tuple(self._to_domain(model) for model in rows), total

    async def add(self, task: Task) -> None:
        await self._set_tenant_context()
        self._session.add(self._from_domain(task))
        await self._session.flush()

    async def save(self, task: Task) -> None:
        await self._set_tenant_context()
        model = await self._session.scalar(
            select(TaskModel)
            .where(TaskModel.id == task.id, TaskModel.tenant_id == self._tenant_id)
            .with_for_update()
        )
        if model is None:
            raise LookupError(f"task not found: {task.id}")
        self._copy_to_model(task, model)
        await self._session.flush()

    async def has_retry(self, task_id: UUID) -> bool:
        await self._set_tenant_context()
        statement = select(
            exists().where(
                TaskModel.tenant_id == self._tenant_id,
                TaskModel.retry_of_task_id == task_id,
            )
        )
        return bool(await self._session.scalar(statement))

    async def _set_tenant_context(self) -> None:
        await self._session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self._tenant_id)},
        )

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    @staticmethod
    def _apply_filters(
        statement: Select[tuple[TaskModel]], filters: TaskFilters
    ) -> Select[tuple[TaskModel]]:
        if filters.task_type is not None:
            statement = statement.where(TaskModel.task_type == filters.task_type.value)
        if filters.status is not None:
            statement = statement.where(TaskModel.status == filters.status.value)
        if filters.project_id is not None:
            statement = statement.where(TaskModel.project_id == filters.project_id)
        if filters.created_by is not None:
            statement = statement.where(TaskModel.created_by == filters.created_by)
        if filters.project_ids is not None:
            if not filters.project_ids:
                return statement.where(text("false"))
            statement = statement.where(TaskModel.project_id.in_(filters.project_ids))
        return statement

    @staticmethod
    def _to_domain(model: TaskModel) -> Task:
        binding = None
        if model.model_name and model.model_version and model.prompt_version:
            binding = ModelBinding(
                name=model.model_name,
                version=model.model_version,
                prompt_version=model.prompt_version,
                temperature=model.temperature or Decimal("0.30"),
            )
        return Task(
            id=model.id,
            tenant_id=model.tenant_id,
            project_id=model.project_id,
            task_type=TaskType(model.task_type),
            status=TaskStatus(model.status),
            title=model.title,
            description=model.description,
            input_snapshot_id=model.input_snapshot_id,
            model_binding=binding,
            created_by=model.created_by,
            confirmed_by=model.confirmed_by,
            confirmed_at=model.confirmed_at,
            completed_at=model.completed_at,
            failure_reason=model.failure_reason,
            retry_count=model.retry_count,
            retry_of_task_id=model.retry_of_task_id,
            error_details=model.error_details or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _from_domain(task: Task) -> TaskModel:
        model = TaskModel(id=task.id, tenant_id=task.tenant_id, project_id=task.project_id)
        SQLAlchemyTaskRepository._copy_to_model(task, model)
        return model

    @staticmethod
    def _copy_to_model(task: Task, model: TaskModel) -> None:
        model.task_type = task.task_type.value
        model.status = task.status.value
        model.title = task.title
        model.description = task.description
        model.input_snapshot_id = task.input_snapshot_id
        model.model_name = task.model_binding.name if task.model_binding else None
        model.model_version = task.model_binding.version if task.model_binding else None
        model.prompt_version = task.model_binding.prompt_version if task.model_binding else None
        model.temperature = task.model_binding.temperature if task.model_binding else None
        model.created_by = task.created_by
        model.confirmed_by = task.confirmed_by
        model.confirmed_at = task.confirmed_at
        model.completed_at = task.completed_at
        model.failure_reason = task.failure_reason
        model.retry_count = task.retry_count
        model.retry_of_task_id = task.retry_of_task_id
        model.error_details = dict(task.error_details)
        model.created_at = task.created_at
        model.updated_at = task.updated_at


class SQLAlchemyTaskRepositoryFactory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def __call__(self, tenant_id: UUID) -> AsyncIterator[SQLAlchemyTaskRepository]:
        async with self._session_factory() as session:
            repository = SQLAlchemyTaskRepository(session, tenant_id)
            try:
                yield repository
            except Exception:
                await session.rollback()
                raise
