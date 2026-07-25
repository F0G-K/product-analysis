"""阶段、角色任务及项目执行上下文。"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class StageName(StrEnum):
    """PRD 规定的五个固定阶段。"""

    ENVIRONMENT_SCAN = "environment_scan"
    CODE_ANALYSIS = "code_analysis"
    VULNERABILITY_VERIFY = "vulnerability_verify"
    REPORT_GENERATE = "report_generate"
    DONE = "done"


STAGE_SEQUENCE: tuple[StageName, ...] = (
    StageName.ENVIRONMENT_SCAN,
    StageName.CODE_ANALYSIS,
    StageName.VULNERABILITY_VERIFY,
    StageName.REPORT_GENERATE,
    StageName.DONE,
)


class ExecutionStatus(StrEnum):
    """阶段和角色任务共享的状态值域。"""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {self.SUCCESS, self.FAILED}


@dataclass(frozen=True, slots=True)
class ProjectExecution:
    """调度器需要的最小项目执行信息。"""

    id: uuid.UUID
    project_status: str
    stop_requested_at: datetime | None


@dataclass(frozen=True, slots=True)
class RuntimeStage:
    """运行阶段领域实体。"""

    id: uuid.UUID
    project_id: uuid.UUID
    runtime_id: uuid.UUID
    stage_name: StageName
    stage_order: int
    stage_status: ExecutionStatus
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkerTask:
    """一次独立角色调用的领域实体。"""

    id: uuid.UUID
    project_id: uuid.UUID
    stage_id: uuid.UUID
    worker_role: str
    task_content: str
    task_status: ExecutionStatus
    result_summary: str | None
    error_message: str | None
    request_id: uuid.UUID
    idempotency_key: str | None
    attempt_count: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
