"""项目聚合根和只读投影。"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ProjectStatus(StrEnum):
    """项目权威状态。"""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class SourceType(StrEnum):
    """源码接入类型。"""

    LOCAL = "local"
    REPOSITORY = "repository"


@dataclass
class Project:
    """项目聚合根。"""

    id: uuid.UUID
    project_name: str
    source_type: str
    source_path: str
    task_content: str
    environment_type: str
    project_status: str
    created_by: uuid.UUID
    stop_requested_at: datetime | None
    last_started_at: datetime | None
    last_finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        project_name: str,
        source_type: str,
        source_path: str,
        task_content: str,
        environment_type: str,
        created_by: uuid.UUID,
    ) -> "Project":
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            project_name=project_name,
            source_type=source_type,
            source_path=source_path,
            task_content=task_content,
            environment_type=environment_type,
            project_status=ProjectStatus.CREATED,
            created_by=created_by,
            stop_requested_at=None,
            last_started_at=None,
            last_finished_at=None,
            created_at=now,
            updated_at=now,
        )


@dataclass(frozen=True)
class ProjectSummary:
    """项目列表只读投影，不加载任务说明等大字段。"""

    id: uuid.UUID
    project_name: str
    source_type: str
    source_path: str
    environment_type: str
    project_status: str
    last_started_at: datetime | None
    last_finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ProjectRuntimeSummary:
    """项目运行环境摘要。"""

    id: uuid.UUID
    runtime_identifier: str | None
    container_status: str
    started_at: datetime | None
    stopped_at: datetime | None
    error_message: str | None


@dataclass(frozen=True)
class ProjectStatistics:
    """项目持久化统计值。"""

    vulnerability_count: int = 0
    verified_vulnerability_count: int = 0
    attack_path_count: int = 0
    worker_task_count: int = 0


@dataclass(frozen=True)
class ProjectDetail:
    """项目详情只读投影。"""

    project: Project
    runtime: ProjectRuntimeSummary | None
    statistics: ProjectStatistics
    report_status: str | None
