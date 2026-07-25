"""角色任务失败后的阶段与项目收敛。"""

from datetime import UTC, datetime

from asa_core.application.commands.execute_worker import ExecuteWorkerCommand
from asa_core.application.ports.scheduling_repository import SchedulingRepository
from asa_core.application.services.sensitive_text import redact_sensitive_text
from asa_core.domain.scheduling.entities import ExecutionStatus
from asa_core.domain.scheduling.exceptions import (
    ProjectRuntimeNotFound,
    RuntimeStageNotFound,
    SchedulingConflict,
    WorkerTaskNotFound,
)
from asa_core.domain.scheduling.task_policy import TaskDistributionPolicy, TaskStateMachine


class ConvergeWorkerFailureHandler:
    """关键角色失败时原子收敛任务、阶段和项目。"""

    async def handle(
        self,
        command: ExecuteWorkerCommand,
        *,
        error_message: str,
        repository: SchedulingRepository,
    ) -> None:
        project = await repository.get_project(command.project_id, for_update=True)
        if project is None:
            raise ProjectRuntimeNotFound()
        stage = await repository.get_stage(
            command.stage_id,
            project_id=command.project_id,
            for_update=True,
        )
        task = await repository.get_worker_task(
            command.worker_task_id,
            project_id=command.project_id,
            for_update=True,
        )
        if stage is None:
            raise RuntimeStageNotFound()
        if task is None:
            raise WorkerTaskNotFound()
        if task.task_status == ExecutionStatus.FAILED:
            return
        TaskStateMachine.ensure_transition(task.task_status, ExecutionStatus.FAILED)
        safe_error = redact_sensitive_text(error_message, max_length=1000) or "角色任务执行失败"
        now = datetime.now(UTC)
        if not await repository.fail_worker_task(
            task.id,
            error_message=safe_error,
            finished_at=now,
        ):
            raise SchedulingConflict()
        await repository.append_event(
            project_id=project.id,
            event_type="worker_status",
            aggregate_type="worker_task",
            aggregate_id=str(task.id),
            payload={
                "worker_task_id": str(task.id),
                "worker_role": task.worker_role,
                "task_status": ExecutionStatus.FAILED.value,
                "request_id": str(command.request_id),
            },
            occurred_at=now,
        )
        if not TaskDistributionPolicy.is_critical(stage.stage_name, task.worker_role):
            return
        if not await repository.transition_stage(
            stage.id,
            expected_status=ExecutionStatus.RUNNING,
            target_status=ExecutionStatus.FAILED,
            changed_at=now,
            error_message=safe_error,
        ):
            raise SchedulingConflict("阶段失败状态更新冲突")
        if project.project_status in {
            "created",
            "running",
        } and not await repository.mark_project_terminal(
            project.id,
            target_status="failed",
            finished_at=now,
        ):
            raise SchedulingConflict("项目失败状态更新冲突")
        await repository.append_event(
            project_id=project.id,
            event_type="stage_status",
            aggregate_type="runtime_stage",
            aggregate_id=str(stage.id),
            payload={
                "stage_id": str(stage.id),
                "stage_name": stage.stage_name.value,
                "stage_status": ExecutionStatus.FAILED.value,
                "request_id": str(command.request_id),
            },
            occurred_at=now,
        )
        await repository.append_event(
            project_id=project.id,
            event_type="project_status",
            aggregate_type="project",
            aggregate_id=str(project.id),
            payload={
                "project_status": "failed",
                "request_id": str(command.request_id),
            },
            occurred_at=now,
        )
