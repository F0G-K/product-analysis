"""Worker 侧停止收敛。"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from asa_core.application.ports.scheduling_repository import SchedulingRepository
from asa_core.domain.scheduling.exceptions import ProjectRuntimeNotFound, SchedulingConflict


@dataclass(frozen=True, slots=True)
class CancelProjectCommand:
    project_id: uuid.UUID
    request_id: uuid.UUID
    reason: str = "项目收到停止请求"


class CancelProjectHandler:
    """以数据库 stop_requested_at 为准，将项目最终收敛为 stopped。"""

    async def handle(
        self,
        command: CancelProjectCommand,
        *,
        repository: SchedulingRepository,
    ) -> None:
        project = await repository.get_project(command.project_id, for_update=True)
        if project is None:
            raise ProjectRuntimeNotFound()
        if project.project_status == "stopped":
            return
        if project.stop_requested_at is None:
            raise SchedulingConflict("项目没有停止标记")
        now = datetime.now(UTC)
        if not await repository.converge_project_stopped(
            project.id,
            finished_at=now,
            reason=command.reason,
        ):
            raise SchedulingConflict("项目停止状态更新冲突")
        await repository.append_event(
            project_id=project.id,
            event_type="project_status",
            aggregate_type="project",
            aggregate_id=str(project.id),
            payload={
                "project_status": "stopped",
                "request_id": str(command.request_id),
            },
            occurred_at=now,
        )
