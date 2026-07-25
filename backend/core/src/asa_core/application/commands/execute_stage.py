"""执行并推进一个固定阶段。"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from asa_core.application.ports.scheduling_repository import SchedulingRepository
from asa_core.application.ports.stage_task_dispatcher import (
    StageTaskDispatcher,
    StageTaskMessage,
    WorkerTaskMessage,
)
from asa_core.domain.projects.status_machine import ProjectStatusMachine
from asa_core.domain.scheduling.cancel_policy import CancelPolicy
from asa_core.domain.scheduling.entities import ExecutionStatus, StageName
from asa_core.domain.scheduling.exceptions import (
    ProjectRuntimeNotFound,
    RuntimeStageNotFound,
    SchedulingConflict,
)
from asa_core.domain.scheduling.stage_machine import StageStateMachine
from asa_core.domain.scheduling.task_policy import TaskDistributionPolicy


@dataclass(frozen=True, slots=True)
class ExecuteStageCommand:
    project_id: uuid.UUID
    stage_id: uuid.UUID
    request_id: uuid.UUID
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ExecuteStageResult:
    stage_id: uuid.UUID
    stage_status: str
    created_worker_task_ids: tuple[uuid.UUID, ...] = ()
    next_stage_id: uuid.UUID | None = None
    replayed: bool = False


class ExecuteStageHandler:
    """阶段事务仅修改数据库；Celery 投递在事务提交后执行。"""

    async def prepare(
        self,
        command: ExecuteStageCommand,
        *,
        repository: SchedulingRepository,
    ) -> tuple[ExecuteStageResult, list[WorkerTaskMessage]]:
        project = await repository.get_project(command.project_id, for_update=True)
        if project is None:
            raise ProjectRuntimeNotFound()
        CancelPolicy.ensure_not_cancelled(project)

        stage = await repository.get_stage(
            command.stage_id,
            project_id=command.project_id,
            for_update=True,
        )
        if stage is None:
            raise RuntimeStageNotFound()
        if stage.stage_status == ExecutionStatus.SUCCESS:
            return (
                ExecuteStageResult(
                    stage_id=stage.id,
                    stage_status=stage.stage_status,
                    replayed=True,
                ),
                [],
            )
        if stage.stage_status == ExecutionStatus.FAILED:
            raise SchedulingConflict("失败阶段不能重复执行")

        previous_stage = await repository.get_previous_stage(stage)
        now = datetime.now(UTC)
        if stage.stage_status == ExecutionStatus.IDLE:
            StageStateMachine.ensure_can_start(
                stage,
                previous_stage=previous_stage,
                stop_requested=False,
            )
            changed = await repository.transition_stage(
                stage.id,
                expected_status=ExecutionStatus.IDLE,
                target_status=ExecutionStatus.RUNNING,
                changed_at=now,
            )
            if not changed:
                raise SchedulingConflict()
            await repository.append_event(
                project_id=project.id,
                event_type="stage_status",
                aggregate_type="runtime_stage",
                aggregate_id=str(stage.id),
                payload={
                    "stage_id": str(stage.id),
                    "stage_name": stage.stage_name.value,
                    "stage_status": ExecutionStatus.RUNNING.value,
                    "request_id": str(command.request_id),
                },
                occurred_at=now,
            )

        # done 是显式终止阶段，不调用模型，也不创建角色任务。
        if stage.stage_name == StageName.DONE:
            return await self._finish_done_stage(
                command,
                repository=repository,
                stage_id=stage.id,
                changed_at=now,
            )

        existing_tasks = await repository.list_stage_tasks(stage.id)
        completed_roles = {task.worker_role for task in existing_tasks if task.task_status == ExecutionStatus.SUCCESS}
        existing_roles = {task.worker_role for task in existing_tasks}
        specs = TaskDistributionPolicy.ready_roles(
            stage.stage_name,
            completed_roles,
            existing_roles,
        )
        messages: list[WorkerTaskMessage] = []
        specs_by_role = {spec.worker_role: spec for spec in TaskDistributionPolicy.tasks_for(stage.stage_name)}
        for task in existing_tasks:
            spec = specs_by_role.get(task.worker_role)
            if (
                task.task_status == ExecutionStatus.IDLE
                and task.idempotency_key
                and spec is not None
                and set(spec.depends_on).issubset(completed_roles)
            ):
                messages.append(
                    WorkerTaskMessage(
                        project_id=project.id,
                        stage_id=stage.id,
                        worker_task_id=task.id,
                        request_id=task.request_id,
                        idempotency_key=task.idempotency_key,
                    )
                )
        for spec in specs:
            task_key = f"stage:{stage.id}:role:{spec.worker_role}:request:{command.request_id}"
            task = await repository.create_worker_task(
                project_id=project.id,
                stage_id=stage.id,
                worker_role=spec.worker_role,
                task_content=spec.task_content,
                request_id=command.request_id,
                idempotency_key=task_key,
            )
            await repository.append_event(
                project_id=project.id,
                event_type="worker_status",
                aggregate_type="worker_task",
                aggregate_id=str(task.id),
                payload={
                    "worker_task_id": str(task.id),
                    "worker_role": task.worker_role,
                    "task_status": task.task_status.value,
                    "stage_id": str(stage.id),
                    "request_id": str(command.request_id),
                },
                occurred_at=now,
            )
            messages.append(
                WorkerTaskMessage(
                    project_id=project.id,
                    stage_id=stage.id,
                    worker_task_id=task.id,
                    request_id=command.request_id,
                    idempotency_key=task_key,
                )
            )
        return (
            ExecuteStageResult(
                stage_id=stage.id,
                stage_status=ExecutionStatus.RUNNING,
                created_worker_task_ids=tuple(message.worker_task_id for message in messages),
            ),
            messages,
        )

    async def handle(
        self,
        command: ExecuteStageCommand,
        *,
        repository: SchedulingRepository,
        dispatcher: StageTaskDispatcher,
    ) -> ExecuteStageResult:
        result, messages = await self.prepare(command, repository=repository)
        if messages:
            await dispatcher.dispatch_workers(messages)
        return result

    async def _finish_done_stage(
        self,
        command: ExecuteStageCommand,
        *,
        repository: SchedulingRepository,
        stage_id: uuid.UUID,
        changed_at: datetime,
    ) -> tuple[ExecuteStageResult, list[WorkerTaskMessage]]:
        changed = await repository.transition_stage(
            stage_id,
            expected_status=ExecutionStatus.RUNNING,
            target_status=ExecutionStatus.SUCCESS,
            changed_at=changed_at,
        )
        if not changed:
            raise SchedulingConflict()
        project = await repository.get_project(command.project_id, for_update=True)
        if project is None:
            raise ProjectRuntimeNotFound()
        ProjectStatusMachine.ensure_transition(project.project_status, "completed")
        project_changed = await repository.mark_project_terminal(
            project.id,
            target_status="completed",
            finished_at=changed_at,
        )
        if not project_changed:
            raise SchedulingConflict("项目完成状态更新冲突")
        await repository.append_event(
            project_id=project.id,
            event_type="stage_status",
            aggregate_type="runtime_stage",
            aggregate_id=str(stage_id),
            payload={
                "stage_id": str(stage_id),
                "stage_name": StageName.DONE.value,
                "stage_status": ExecutionStatus.SUCCESS.value,
                "request_id": str(command.request_id),
            },
            occurred_at=changed_at,
        )
        await repository.append_event(
            project_id=project.id,
            event_type="project_status",
            aggregate_type="project",
            aggregate_id=str(project.id),
            payload={
                "project_status": "completed",
                "request_id": str(command.request_id),
            },
            occurred_at=changed_at,
        )
        return (
            ExecuteStageResult(
                stage_id=stage_id,
                stage_status=ExecutionStatus.SUCCESS,
            ),
            [],
        )


async def dispatch_next_stage_after_commit(
    *,
    dispatcher: StageTaskDispatcher,
    project_id: uuid.UUID,
    stage_id: uuid.UUID,
    request_id: uuid.UUID,
) -> None:
    """统一生成下一阶段消息，避免调用方拼接不一致的幂等键。"""
    await dispatcher.dispatch_stage(
        StageTaskMessage(
            project_id=project_id,
            stage_id=stage_id,
            request_id=request_id,
            idempotency_key=f"stage:{stage_id}:request:{request_id}",
        )
    )
