"""项目异步任务投递 Port。"""

import uuid
from abc import ABC, abstractmethod

from asa_core.application.ports.project_repository import StartProjectResources


class ProjectTaskDispatcher(ABC):
    """在数据库事务提交后投递异步任务。"""

    @abstractmethod
    async def dispatch_start(
        self,
        *,
        project_id: uuid.UUID,
        resources: StartProjectResources,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> None: ...

    @abstractmethod
    async def dispatch_stop(
        self,
        *,
        project_id: uuid.UUID,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> None: ...

    @abstractmethod
    async def dispatch_delete(
        self,
        *,
        project_id: uuid.UUID,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> None: ...


class NoOpProjectTaskDispatcher(ProjectTaskDispatcher):
    """调度模块接入前的安全占位实现。

    数据库中会保留受理记录、首个 worker task 和 Outbox 事件，
    后续恢复扫描可以按原幂等键补投递。
    """

    async def dispatch_start(self, **kwargs) -> None:
        return None

    async def dispatch_stop(self, **kwargs) -> None:
        return None

    async def dispatch_delete(self, **kwargs) -> None:
        return None
