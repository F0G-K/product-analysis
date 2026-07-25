"""阶段与角色任务投递 Port。"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StageTaskMessage:
    """Celery 阶段任务消息，只含可序列化标识。"""

    project_id: uuid.UUID
    stage_id: uuid.UUID
    request_id: uuid.UUID
    idempotency_key: str
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class WorkerTaskMessage:
    """Celery 角色任务消息，只含可序列化标识。"""

    project_id: uuid.UUID
    stage_id: uuid.UUID
    worker_task_id: uuid.UUID
    request_id: uuid.UUID
    idempotency_key: str
    schema_version: int = 1


class StageTaskDispatcher(ABC):
    """事务提交后向 Celery 投递任务。"""

    @abstractmethod
    async def dispatch_stage(self, message: StageTaskMessage) -> None: ...

    @abstractmethod
    async def dispatch_workers(self, messages: list[WorkerTaskMessage]) -> None: ...


class NoOpStageTaskDispatcher(StageTaskDispatcher):
    """测试或未启用 Worker 时的安全占位实现。"""

    async def dispatch_stage(self, message: StageTaskMessage) -> None:
        return None

    async def dispatch_workers(self, messages: list[WorkerTaskMessage]) -> None:
        return None
