"""项目管理持久化 Port。"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from asa_core.domain.projects.entities import Project, ProjectDetail, ProjectSummary


@dataclass(frozen=True)
class ProjectListResult:
    """项目列表分页结果。"""

    items: list[ProjectSummary]
    page: int
    page_size: int
    total: int

    @property
    def has_next(self) -> bool:
        return self.page * self.page_size < self.total


@dataclass(frozen=True)
class ProjectOperationRecord:
    """持久化后的项目 API 幂等记录。"""

    operation: str
    request_fingerprint: str
    response_data: dict[str, Any]
    accepted_at: datetime


@dataclass(frozen=True)
class StartProjectResources:
    """启动事务内创建的资源标识。"""

    runtime_id: uuid.UUID
    first_stage_id: uuid.UUID
    worker_task_id: uuid.UUID


class ProjectRepository(ABC):
    """项目聚合仓储接口，Repository 不自行提交事务。"""

    @abstractmethod
    async def add(self, project: Project) -> None: ...

    @abstractmethod
    async def find_accessible(
        self,
        project_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
        for_update: bool = False,
    ) -> Project | None: ...

    @abstractmethod
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
    ) -> ProjectListResult: ...

    @abstractmethod
    async def get_detail(
        self,
        project_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
    ) -> ProjectDetail | None: ...

    @abstractmethod
    async def get_active_configuration(self) -> tuple[set[str], int | None]: ...

    @abstractmethod
    async def acquire_project_lock(self, project_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def acquire_operation_lock(
        self,
        *,
        actor_user_id: uuid.UUID,
        idempotency_key: str,
    ) -> None: ...

    @abstractmethod
    async def acquire_capacity_lock(self) -> None: ...

    @abstractmethod
    async def count_running(self) -> int: ...

    @abstractmethod
    async def has_runtime(self, project_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def find_operation(
        self,
        *,
        actor_user_id: uuid.UUID,
        idempotency_key: str,
    ) -> ProjectOperationRecord | None: ...

    @abstractmethod
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
    ) -> None: ...

    @abstractmethod
    async def create_start_resources(
        self,
        *,
        project: Project,
        request_id: uuid.UUID,
        worker_idempotency_key: str,
    ) -> StartProjectResources: ...

    @abstractmethod
    async def set_stop_requested(
        self,
        project_id: uuid.UUID,
        *,
        expected_status: str,
        stop_requested_at: datetime,
    ) -> bool: ...

    @abstractmethod
    async def append_event(
        self,
        *,
        project_id: uuid.UUID,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        occurred_at: datetime,
    ) -> None: ...
