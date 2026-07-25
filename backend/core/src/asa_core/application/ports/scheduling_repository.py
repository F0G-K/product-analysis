"""调度持久化 Port。"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from asa_core.domain.scheduling.entities import (
    ProjectExecution,
    RuntimeStage,
    WorkerTask,
)


@dataclass(frozen=True, slots=True)
class WorkerTaskListResult:
    """角色任务分页结果。"""

    items: list[WorkerTask]
    page: int
    page_size: int
    total: int

    @property
    def has_next(self) -> bool:
        return self.page * self.page_size < self.total


class SchedulingRepository(ABC):
    """阶段和角色任务聚合仓储；实现不得自行提交事务。"""

    @abstractmethod
    async def project_exists(self, project_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def find_accessible_project(
        self,
        project_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
    ) -> ProjectExecution | None: ...

    @abstractmethod
    async def get_project(
        self,
        project_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> ProjectExecution | None: ...

    @abstractmethod
    async def list_stages(self, project_id: uuid.UUID) -> list[RuntimeStage]: ...

    @abstractmethod
    async def get_stage(
        self,
        stage_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        for_update: bool = False,
    ) -> RuntimeStage | None: ...

    @abstractmethod
    async def get_previous_stage(self, stage: RuntimeStage) -> RuntimeStage | None: ...

    @abstractmethod
    async def get_next_stage(self, stage: RuntimeStage) -> RuntimeStage | None: ...

    @abstractmethod
    async def transition_stage(
        self,
        stage_id: uuid.UUID,
        *,
        expected_status: str,
        target_status: str,
        changed_at: datetime,
        error_message: str | None = None,
    ) -> bool: ...

    @abstractmethod
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
    ) -> WorkerTaskListResult: ...

    @abstractmethod
    async def list_stage_tasks(self, stage_id: uuid.UUID) -> list[WorkerTask]: ...

    @abstractmethod
    async def get_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        for_update: bool = False,
    ) -> WorkerTask | None: ...

    @abstractmethod
    async def create_worker_task(
        self,
        *,
        project_id: uuid.UUID,
        stage_id: uuid.UUID,
        worker_role: str,
        task_content: str,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> WorkerTask: ...

    @abstractmethod
    async def claim_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        started_at: datetime,
    ) -> bool: ...

    @abstractmethod
    async def complete_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        result_summary: str,
        finished_at: datetime,
    ) -> bool: ...

    @abstractmethod
    async def fail_worker_task(
        self,
        worker_task_id: uuid.UUID,
        *,
        error_message: str,
        finished_at: datetime,
    ) -> bool: ...

    @abstractmethod
    async def mark_project_running(
        self,
        project_id: uuid.UUID,
        *,
        started_at: datetime,
    ) -> bool: ...

    @abstractmethod
    async def mark_project_terminal(
        self,
        project_id: uuid.UUID,
        *,
        target_status: str,
        finished_at: datetime,
    ) -> bool: ...

    @abstractmethod
    async def converge_project_stopped(
        self,
        project_id: uuid.UUID,
        *,
        finished_at: datetime,
        reason: str,
    ) -> bool: ...

    @abstractmethod
    async def append_event(
        self,
        *,
        project_id: uuid.UUID,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, object],
        occurred_at: datetime,
    ) -> None: ...

    @abstractmethod
    async def list_stale_running_tasks(
        self,
        *,
        stale_before: datetime,
        limit: int,
    ) -> list[WorkerTask]: ...
