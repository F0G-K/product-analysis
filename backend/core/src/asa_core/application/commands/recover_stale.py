"""Worker 启动时扫描异常停留的运行任务。"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from asa_core.application.ports.scheduling_repository import SchedulingRepository
from asa_core.domain.scheduling.entities import WorkerTask


@dataclass(frozen=True, slots=True)
class RecoverStaleTasksCommand:
    heartbeat_timeout_seconds: int
    limit: int = 100


class RecoverStaleTasksHandler:
    """只返回待诊断任务，不把不确定任务自动标记为成功或失败。"""

    async def handle(
        self,
        command: RecoverStaleTasksCommand,
        *,
        repository: SchedulingRepository,
    ) -> list[WorkerTask]:
        if command.heartbeat_timeout_seconds <= 0:
            raise ValueError("heartbeat_timeout_seconds 必须大于 0")
        if not 1 <= command.limit <= 1000:
            raise ValueError("limit 必须在 1 到 1000 之间")
        stale_before = datetime.now(UTC) - timedelta(seconds=command.heartbeat_timeout_seconds)
        return await repository.list_stale_running_tasks(
            stale_before=stale_before,
            limit=command.limit,
        )
