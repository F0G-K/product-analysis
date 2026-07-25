"""SQLAlchemy 调度仓储实现。"""

import uuid
from datetime import datetime
from typing import Any

from asa_core.application.ports.scheduling_repository import (
    SchedulingRepository,
    WorkerTaskListResult,
)
from asa_core.domain.scheduling.entities import (
    ExecutionStatus,
    ProjectExecution,
    RuntimeStage,
    StageName,
    WorkerTask,
)
from asa_core.infrastructure.database.models import (
    DomainEventModel,
    ProjectModel,
    ProjectRuntimeModel,
    RuntimeStageModel,
    WorkerTaskModel,
)
from sqlalchemy import asc, desc, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemySchedulingRepository(SchedulingRepository):
    """使用条件更新和项目行锁保证调度状态一致性。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def project_exists(self, project_id: uuid.UUID) -> bool:
        stmt = select(ProjectModel.id).where(ProjectModel.id == project_id).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def find_accessible_project(
        self,
        project_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
    ) -> ProjectExecution | None:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        if not actor_is_admin:
            stmt = stmt.where(ProjectModel.created_by == actor_user_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_project(model) if model is not None else None

    async def get_project(
        self,
        project_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> ProjectExecution | None:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_project(model) if model is not None else None

    async def list_stages(self, project_id: uuid.UUID) -> list[RuntimeStage]:
        stmt = (
            select(RuntimeStageModel)
            .where(RuntimeStageModel.project_id == project_id)
            .order_by(RuntimeStageModel.stage_order.asc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [self._to_stage(model) for model in models]

    async def get_stage(
        self,
        stage_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        for_update: bool = False,
    ) -> RuntimeStage | None:
        stmt = select(RuntimeStageModel).where(RuntimeStageModel.id == stage_id)
        if project_id is not None:
            stmt = stmt.where(RuntimeStageModel.project_id == project_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_stage(model) if model is not None else None

    async def get_previous_stage(self, stage: RuntimeStage) -> RuntimeStage | None:
        stmt = select(RuntimeStageModel).where(
            RuntimeStageModel.runtime_id == stage.runtime_id,
            RuntimeStageModel.stage_order == stage.stage_order - 1,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_stage(model) if model is not None else None

    async def get_next_stage(self, stage: RuntimeStage) -> RuntimeStage | None:
        stmt = select(RuntimeStageModel).where(
            RuntimeStageModel.runtime_id == stage.runtime_id,
            RuntimeStageModel.stage_order == stage.stage_order + 1,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_stage(model) if model is not None else None

    async def transition_stage(
        self,
        stage_id: uuid.UUID,
        *,
        expected_status: str,
        target_status: str,
        changed_at: datetime,
        error_message: str | None = None,
    ) -> bool:
        values: dict[str, Any] = {
            "stage_status": target_status,
            "error_message": error_message,
        }
        if target_status == ExecutionStatus.RUNNING:
            values.update(started_at=changed_at, finished_at=None)
        elif target_status in {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED}:
            values["finished_at"] = changed_at
        stmt = (
            update(RuntimeStageModel)
            .where(
                RuntimeStageModel.id == stage_id,
                RuntimeStageModel.stage_status == expected_status,
            )
            .values(**values)
        )
        result = await self._session.execute(stmt)
        return self._rowcount(result) == 1

    async def list_worker_tasks(
        self,
        project_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        stage_id: uuid.UUID | None,
        worker_role: str | None,
        task_status: str | None,
        request_id: uuid.UUID | None,
        sort: str,
    ) -> WorkerTaskListResult:
        conditions: list[Any] = [WorkerTaskModel.project_id == project_id]
        if stage_id is not None:
            conditions.append(WorkerTaskModel.stage_id == stage_id)
        if worker_role is not None:
            conditions.append(WorkerTaskModel.worker_role == worker_role)
        if task_status is not None:
            conditions.append(WorkerTaskModel.task_status == task_status)
        if request_id is not None:
            conditions.append(WorkerTaskModel.request_id == request_id)
        total_stmt = select(func.count(WorkerTaskModel.id)).where(*conditions)
        total = int((await self._session.execute(total_stmt)).scalar_one())
        direction = sort.split(":", maxsplit=1)[1]
        order = asc if direction == "asc" else desc
        data_stmt = (
            select(WorkerTaskModel)
            .where(*conditions)
            .order_by(order(WorkerTaskModel.created_at), order(WorkerTaskModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        models = (await self._session.execute(data_stmt)).scalars().all()
        return WorkerTaskListResult(
            items=[self._to_task(model) for model in models],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def list_stage_tasks(self, stage_id: uuid.UUID) -> list[WorkerTask]:
        stmt = (
            select(WorkerTaskModel)
            .where(WorkerTaskModel.stage_id == stage_id)
            .order_by(WorkerTaskModel.created_at.asc(), WorkerTaskModel.id.asc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [self._to_task(model) for model in models]

    async def get_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        for_update: bool = False,
    ) -> WorkerTask | None:
        stmt = select(WorkerTaskModel).where(WorkerTaskModel.id == worker_task_id)
        if project_id is not None:
            stmt = stmt.where(WorkerTaskModel.project_id == project_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_task(model) if model is not None else None

    async def create_worker_task(
        self,
        *,
        project_id: uuid.UUID,
        stage_id: uuid.UUID,
        worker_role: str,
        task_content: str,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> WorkerTask:
        now = datetime.now().astimezone()
        model = WorkerTaskModel(
            id=uuid.uuid4(),
            project_id=project_id,
            stage_id=stage_id,
            worker_role=worker_role,
            task_content=task_content,
            task_status=ExecutionStatus.IDLE,
            request_id=request_id,
            idempotency_key=idempotency_key,
            attempt_count=0,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_task(model)

    async def claim_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        started_at: datetime,
    ) -> bool:
        stmt = (
            update(WorkerTaskModel)
            .where(
                WorkerTaskModel.id == worker_task_id,
                WorkerTaskModel.task_status == ExecutionStatus.IDLE,
            )
            .values(
                task_status=ExecutionStatus.RUNNING,
                started_at=started_at,
                attempt_count=WorkerTaskModel.attempt_count + 1,
                error_message=None,
            )
        )
        result = await self._session.execute(stmt)
        return self._rowcount(result) == 1

    async def complete_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        result_summary: str,
        finished_at: datetime,
    ) -> bool:
        stmt = (
            update(WorkerTaskModel)
            .where(
                WorkerTaskModel.id == worker_task_id,
                WorkerTaskModel.task_status == ExecutionStatus.RUNNING,
            )
            .values(
                task_status=ExecutionStatus.SUCCESS,
                result_summary=result_summary,
                error_message=None,
                finished_at=finished_at,
            )
        )
        result = await self._session.execute(stmt)
        return self._rowcount(result) == 1

    async def fail_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        error_message: str,
        finished_at: datetime,
    ) -> bool:
        stmt = (
            update(WorkerTaskModel)
            .where(
                WorkerTaskModel.id == worker_task_id,
                WorkerTaskModel.task_status == ExecutionStatus.RUNNING,
            )
            .values(
                task_status=ExecutionStatus.FAILED,
                error_message=error_message,
                finished_at=finished_at,
            )
        )
        result = await self._session.execute(stmt)
        return self._rowcount(result) == 1

    async def mark_project_running(
        self,
        project_id: uuid.UUID,
        *,
        started_at: datetime,
    ) -> bool:
        stmt = (
            update(ProjectModel)
            .where(
                ProjectModel.id == project_id,
                ProjectModel.project_status == "created",
                ProjectModel.stop_requested_at.is_(None),
            )
            .values(project_status="running", last_started_at=started_at)
        )
        result = await self._session.execute(stmt)
        if self._rowcount(result) == 1:
            await self._session.execute(
                update(ProjectRuntimeModel)
                .where(ProjectRuntimeModel.project_id == project_id)
                .values(container_status="running", started_at=started_at)
            )
            return True
        return False

    async def mark_project_terminal(
        self,
        project_id: uuid.UUID,
        *,
        target_status: str,
        finished_at: datetime,
    ) -> bool:
        expected_statuses = ("created", "running") if target_status == "failed" else ("running",)
        stmt = (
            update(ProjectModel)
            .where(
                ProjectModel.id == project_id,
                ProjectModel.project_status.in_(expected_statuses),
            )
            .values(project_status=target_status, last_finished_at=finished_at)
        )
        result = await self._session.execute(stmt)
        return self._rowcount(result) == 1

    async def converge_project_stopped(
        self,
        project_id: uuid.UUID,
        *,
        finished_at: datetime,
        reason: str,
    ) -> bool:
        """停止不新增任务状态；运行中的任务以失败摘要收敛。"""
        await self._session.execute(
            update(WorkerTaskModel)
            .where(
                WorkerTaskModel.project_id == project_id,
                WorkerTaskModel.task_status == ExecutionStatus.RUNNING,
            )
            .values(
                task_status=ExecutionStatus.FAILED,
                error_message=reason,
                finished_at=finished_at,
            )
        )
        await self._session.execute(
            update(RuntimeStageModel)
            .where(
                RuntimeStageModel.project_id == project_id,
                RuntimeStageModel.stage_status == ExecutionStatus.RUNNING,
            )
            .values(
                stage_status=ExecutionStatus.FAILED,
                error_message=reason,
                finished_at=finished_at,
            )
        )
        stmt = (
            update(ProjectModel)
            .where(
                ProjectModel.id == project_id,
                ProjectModel.project_status == "running",
                ProjectModel.stop_requested_at.is_not(None),
            )
            .values(project_status="stopped", last_finished_at=finished_at)
        )
        result = await self._session.execute(stmt)
        return self._rowcount(result) == 1

    async def append_event(
        self,
        *,
        project_id: uuid.UUID,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, object],
        occurred_at: datetime,
    ) -> None:
        # 锁定项目行后分配序号，避免并发 MAX(sequence)+1 冲突。
        await self._session.execute(select(ProjectModel.id).where(ProjectModel.id == project_id).with_for_update())
        sequence_stmt = select(func.coalesce(func.max(DomainEventModel.sequence), 0) + 1).where(
            DomainEventModel.project_id == project_id
        )
        sequence = int((await self._session.execute(sequence_stmt)).scalar_one())
        self._session.add(
            DomainEventModel(
                event_id=uuid.uuid4(),
                project_id=project_id,
                sequence=sequence,
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload=payload,
                publish_status="pending",
                retry_count=0,
                occurred_at=occurred_at,
            )
        )

    async def list_stale_running_tasks(
        self,
        *,
        stale_before: datetime,
        limit: int,
    ) -> list[WorkerTask]:
        stmt = (
            select(WorkerTaskModel)
            .where(
                WorkerTaskModel.task_status == ExecutionStatus.RUNNING,
                WorkerTaskModel.started_at < stale_before,
            )
            .order_by(WorkerTaskModel.started_at.asc(), WorkerTaskModel.id.asc())
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [self._to_task(model) for model in models]

    @staticmethod
    def _to_project(model: ProjectModel) -> ProjectExecution:
        return ProjectExecution(
            id=model.id,
            project_status=model.project_status,
            stop_requested_at=model.stop_requested_at,
        )

    @staticmethod
    def _to_stage(model: RuntimeStageModel) -> RuntimeStage:
        return RuntimeStage(
            id=model.id,
            project_id=model.project_id,
            runtime_id=model.runtime_id,
            stage_name=StageName(model.stage_name),
            stage_order=model.stage_order,
            stage_status=ExecutionStatus(model.stage_status),
            started_at=model.started_at,
            finished_at=model.finished_at,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_task(model: WorkerTaskModel) -> WorkerTask:
        return WorkerTask(
            id=model.id,
            project_id=model.project_id,
            stage_id=model.stage_id,
            worker_role=model.worker_role,
            task_content=model.task_content,
            task_status=ExecutionStatus(model.task_status),
            result_summary=model.result_summary,
            error_message=model.error_message,
            request_id=model.request_id,
            idempotency_key=model.idempotency_key,
            attempt_count=model.attempt_count,
            started_at=model.started_at,
            finished_at=model.finished_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _rowcount(result: object) -> int:
        return result.rowcount if isinstance(result, CursorResult) else -1
