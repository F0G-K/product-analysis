"""SQLAlchemy 项目仓储实现。"""

import hashlib
import uuid
from datetime import datetime
from typing import Any

from asa_core.application.ports.project_repository import (
    ProjectListResult,
    ProjectOperationRecord,
    ProjectRepository,
    StartProjectResources,
)
from asa_core.domain.projects.entities import (
    Project,
    ProjectDetail,
    ProjectRuntimeSummary,
    ProjectStatistics,
    ProjectSummary,
)
from asa_core.infrastructure.database.models import (
    DomainEventModel,
    ProjectModel,
    ProjectOperationModel,
    ProjectRuntimeModel,
    RuntimeStageModel,
    SystemConfigModel,
    WorkerTaskModel,
)
from sqlalchemy import asc, desc, func, select, text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

_CAPACITY_LOCK_KEY = 6_134_884_327_020_026_105
_STAGES: tuple[tuple[str, int], ...] = (
    ("environment_scan", 1),
    ("code_analysis", 2),
    ("vulnerability_verify", 3),
    ("report_generate", 4),
    ("done", 5),
)


class SqlAlchemyProjectRepository(ProjectRepository):
    """基于 PostgreSQL 的项目仓储。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, project: Project) -> None:
        self._session.add(
            ProjectModel(
                id=project.id,
                project_name=project.project_name,
                source_type=project.source_type,
                source_path=project.source_path,
                task_content=project.task_content,
                environment_type=project.environment_type,
                project_status=project.project_status,
                created_by=project.created_by,
                stop_requested_at=project.stop_requested_at,
                last_started_at=project.last_started_at,
                last_finished_at=project.last_finished_at,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )
        # 项目与审计模型没有 ORM relationship；先写入主记录，确保同事务审计外键可用。
        await self._session.flush()

    async def find_accessible(
        self,
        project_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
        for_update: bool = False,
    ) -> Project | None:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        if not actor_is_admin:
            stmt = stmt.where(ProjectModel.created_by == actor_user_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model is not None else None

    async def list_accessible(
        self,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
        page: int,
        page_size: int,
        project_status: str | None,
        source_type: str | None,
        keyword: str | None,
        sort: str,
    ) -> ProjectListResult:
        conditions: list[Any] = []
        if not actor_is_admin:
            conditions.append(ProjectModel.created_by == actor_user_id)
        if project_status is not None:
            conditions.append(ProjectModel.project_status == project_status)
        if source_type is not None:
            conditions.append(ProjectModel.source_type == source_type)
        if keyword:
            escaped_keyword = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(
                ProjectModel.project_name.ilike(
                    f"%{escaped_keyword}%",
                    escape="\\",
                )
            )

        count_stmt = select(func.count(ProjectModel.id)).select_from(ProjectModel)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = int((await self._session.execute(count_stmt)).scalar_one())

        sort_field, sort_direction = sort.split(":", maxsplit=1)
        order_column = ProjectModel.created_at if sort_field == "created_at" else ProjectModel.updated_at
        order_expression = asc(order_column) if sort_direction == "asc" else desc(order_column)
        id_order = asc(ProjectModel.id) if sort_direction == "asc" else desc(ProjectModel.id)

        # 列表显式裁剪字段，避免加载 task_content 和错误详情等大字段。
        data_stmt = select(
            ProjectModel.id,
            ProjectModel.project_name,
            ProjectModel.source_type,
            ProjectModel.source_path,
            ProjectModel.environment_type,
            ProjectModel.project_status,
            ProjectModel.last_started_at,
            ProjectModel.last_finished_at,
            ProjectModel.created_at,
            ProjectModel.updated_at,
        )
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = data_stmt.order_by(order_expression, id_order).offset((page - 1) * page_size).limit(page_size)
        rows = (await self._session.execute(data_stmt)).all()
        return ProjectListResult(
            items=[
                ProjectSummary(
                    id=row.id,
                    project_name=row.project_name,
                    source_type=row.source_type,
                    source_path=row.source_path,
                    environment_type=row.environment_type,
                    project_status=row.project_status,
                    last_started_at=row.last_started_at,
                    last_finished_at=row.last_finished_at,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_detail(
        self,
        project_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
    ) -> ProjectDetail | None:
        project = await self.find_accessible(
            project_id,
            actor_user_id=actor_user_id,
            actor_is_admin=actor_is_admin,
        )
        if project is None:
            return None

        runtime_stmt = select(ProjectRuntimeModel).where(ProjectRuntimeModel.project_id == project_id)
        runtime_model = (await self._session.execute(runtime_stmt)).scalar_one_or_none()
        runtime = (
            ProjectRuntimeSummary(
                id=runtime_model.id,
                runtime_identifier=runtime_model.runtime_identifier,
                container_status=runtime_model.container_status,
                started_at=runtime_model.started_at,
                stopped_at=runtime_model.stopped_at,
                error_message=self._redact_error(runtime_model.error_message),
            )
            if runtime_model is not None
            else None
        )

        statistics = ProjectStatistics(
            vulnerability_count=await self._count_optional_table(
                "vulnerabilities",
                project_id,
            ),
            verified_vulnerability_count=await self._count_optional_table(
                "vulnerabilities",
                project_id,
                extra_predicate="verify_status = 'verified'",
            ),
            attack_path_count=await self._count_optional_table(
                "attack_paths",
                project_id,
            ),
            worker_task_count=await self._count_worker_tasks(project_id),
        )
        report_status = await self._latest_report_status(project_id)
        return ProjectDetail(
            project=project,
            runtime=runtime,
            statistics=statistics,
            report_status=report_status,
        )

    async def get_active_configuration(self) -> tuple[set[str], int | None]:
        stmt = (
            select(
                SystemConfigModel.enabled_environment_types,
                SystemConfigModel.max_concurrent_projects,
            )
            .where(SystemConfigModel.is_active.is_(True))
            .limit(1)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return set(), None
        return set(row.enabled_environment_types), row.max_concurrent_projects

    async def acquire_project_lock(self, project_id: uuid.UUID) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": self._advisory_key(project_id)},
        )

    async def acquire_operation_lock(
        self,
        *,
        actor_user_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        digest = hashlib.sha256(f"{actor_user_id}:{idempotency_key}".encode()).digest()
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": self._signed_bigint(digest[:8])},
        )

    async def acquire_capacity_lock(self) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _CAPACITY_LOCK_KEY},
        )

    async def count_running(self) -> int:
        stmt = (
            select(func.count(func.distinct(ProjectModel.id)))
            .select_from(ProjectModel)
            .outerjoin(
                ProjectRuntimeModel,
                ProjectRuntimeModel.project_id == ProjectModel.id,
            )
            .where(
                (ProjectModel.project_status == "running")
                | (ProjectRuntimeModel.container_status.in_(("pending", "starting", "running")))
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def has_runtime(self, project_id: uuid.UUID) -> bool:
        stmt = (
            select(ProjectRuntimeModel.id)
            .where(ProjectRuntimeModel.project_id == project_id)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def find_operation(
        self,
        *,
        actor_user_id: uuid.UUID,
        idempotency_key: str,
    ) -> ProjectOperationRecord | None:
        stmt = select(ProjectOperationModel).where(
            ProjectOperationModel.actor_user_id == actor_user_id,
            ProjectOperationModel.idempotency_key == idempotency_key,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return ProjectOperationRecord(
            operation=model.operation,
            request_fingerprint=model.request_fingerprint,
            response_data=dict(model.response_data),
            accepted_at=model.accepted_at,
        )

    async def create_operation(
        self,
        *,
        actor_user_id: uuid.UUID,
        project_id: uuid.UUID,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        response_data: dict[str, Any],
        accepted_at: datetime,
    ) -> None:
        self._session.add(
            ProjectOperationModel(
                actor_user_id=actor_user_id,
                project_id=project_id,
                operation=operation,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response_data=response_data,
                accepted_at=accepted_at,
            )
        )

    async def create_start_resources(
        self,
        *,
        project: Project,
        request_id: uuid.UUID,
        worker_idempotency_key: str,
    ) -> StartProjectResources:
        runtime_id = uuid.uuid4()
        self._session.add(
            ProjectRuntimeModel(
                id=runtime_id,
                project_id=project.id,
                container_status="pending",
                environment_snapshot={
                    "environment_type": project.environment_type,
                    "source_type": project.source_type,
                },
            )
        )

        stage_models: list[RuntimeStageModel] = []
        for stage_name, stage_order in _STAGES:
            stage_models.append(
                RuntimeStageModel(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    runtime_id=runtime_id,
                    stage_name=stage_name,
                    stage_order=stage_order,
                    stage_status="idle",
                )
            )
        self._session.add_all(stage_models)

        first_stage = stage_models[0]
        worker_task_id = uuid.uuid4()
        self._session.add(
            WorkerTaskModel(
                id=worker_task_id,
                project_id=project.id,
                stage_id=first_stage.id,
                worker_role="environment_inspector",
                task_content=("准备项目源码与隔离环境，并执行环境扫描阶段的初始检查。"),
                task_status="idle",
                request_id=request_id,
                idempotency_key=worker_idempotency_key,
                attempt_count=0,
            )
        )
        return StartProjectResources(
            runtime_id=runtime_id,
            first_stage_id=first_stage.id,
            worker_task_id=worker_task_id,
        )

    async def set_stop_requested(
        self,
        project_id: uuid.UUID,
        *,
        expected_status: str,
        stop_requested_at: datetime,
    ) -> bool:
        stmt = (
            update(ProjectModel)
            .where(
                ProjectModel.id == project_id,
                ProjectModel.project_status == expected_status,
                ProjectModel.stop_requested_at.is_(None),
            )
            .values(stop_requested_at=stop_requested_at)
        )
        result = await self._session.execute(stmt)
        assert isinstance(result, CursorResult)
        return result.rowcount == 1

    async def append_event(
        self,
        *,
        project_id: uuid.UUID,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        occurred_at: datetime,
    ) -> None:
        # 事件序号必须在项目锁内分配；重复获取同一事务级锁是安全的。
        await self.acquire_project_lock(project_id)
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

    async def _count_worker_tasks(self, project_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(WorkerTaskModel.id))
            .select_from(WorkerTaskModel)
            .where(WorkerTaskModel.project_id == project_id)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def _count_optional_table(
        self,
        table_name: str,
        project_id: uuid.UUID,
        *,
        extra_predicate: str | None = None,
    ) -> int:
        if not await self._table_exists(table_name):
            return 0
        sql = f"SELECT count(*) FROM {table_name} WHERE project_id = :project_id"
        if extra_predicate is not None:
            sql = f"{sql} AND {extra_predicate}"
        return int(
            (
                await self._session.execute(
                    text(sql),
                    {"project_id": project_id},
                )
            ).scalar_one()
        )

    async def _latest_report_status(self, project_id: uuid.UUID) -> str | None:
        if not await self._table_exists("reports"):
            return None
        stmt = text(
            "SELECT report_status FROM reports WHERE project_id = :project_id ORDER BY created_at DESC, id DESC LIMIT 1"
        )
        return (await self._session.execute(stmt, {"project_id": project_id})).scalar_one_or_none()

    async def _table_exists(self, table_name: str) -> bool:
        result = await self._session.execute(
            text("SELECT to_regclass(:table_name) IS NOT NULL"),
            {"table_name": table_name},
        )
        return bool(result.scalar_one())

    @staticmethod
    def _to_entity(model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            project_name=model.project_name,
            source_type=model.source_type,
            source_path=model.source_path,
            task_content=model.task_content,
            environment_type=model.environment_type,
            project_status=model.project_status,
            created_by=model.created_by,
            stop_requested_at=model.stop_requested_at,
            last_started_at=model.last_started_at,
            last_finished_at=model.last_finished_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _advisory_key(project_id: uuid.UUID) -> int:
        return SqlAlchemyProjectRepository._signed_bigint(project_id.bytes[:8])

    @staticmethod
    def _signed_bigint(raw: bytes) -> int:
        unsigned = int.from_bytes(raw, byteorder="big", signed=False)
        return unsigned - (1 << 64) if unsigned >= (1 << 63) else unsigned

    @staticmethod
    def _redact_error(error_message: str | None) -> str | None:
        if error_message is None:
            return None
        # 详情接口只暴露短错误摘要，避免泄露内部路径和超长第三方响应。
        return "".join(character for character in error_message if character.isprintable())[:500]
