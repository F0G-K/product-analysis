"""执行一次 AI 角色任务。"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from asa_core.application.ports.model_port import ModelPort, ModelRequest
from asa_core.application.ports.scheduling_repository import SchedulingRepository
from asa_core.application.ports.stage_task_dispatcher import (
    StageTaskDispatcher,
    WorkerTaskMessage,
)
from asa_core.application.services.context_assembler import ContextAssembler
from asa_core.application.services.sensitive_text import redact_sensitive_text
from asa_core.domain.agents.role import RoleRegistry
from asa_core.domain.scheduling.cancel_policy import CancelPolicy
from asa_core.domain.scheduling.entities import ExecutionStatus, WorkerTask
from asa_core.domain.scheduling.exceptions import (
    ProjectRuntimeNotFound,
    RuntimeStageNotFound,
    SchedulingConflict,
    WorkerTaskNotFound,
)
from asa_core.domain.scheduling.task_policy import TaskDistributionPolicy, TaskStateMachine


@dataclass(frozen=True, slots=True)
class ExecuteWorkerCommand:
    project_id: uuid.UUID
    stage_id: uuid.UUID
    worker_task_id: uuid.UUID
    request_id: uuid.UUID
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ExecuteWorkerResult:
    worker_task_id: uuid.UUID
    task_status: str
    result_summary: str | None = None
    replayed: bool = False


class ExecuteWorkerTaskHandler:
    """模型调用前后均检查取消；输出先校验再进入持久化。"""

    def __init__(
        self,
        *,
        model: ModelPort,
        context_assembler: ContextAssembler,
    ):
        self._model = model
        self._context_assembler = context_assembler

    async def claim(
        self,
        command: ExecuteWorkerCommand,
        *,
        repository: SchedulingRepository,
    ) -> ExecuteWorkerResult | None:
        project = await repository.get_project(command.project_id, for_update=True)
        if project is None:
            raise ProjectRuntimeNotFound()
        CancelPolicy.ensure_not_cancelled(project)
        stage = await repository.get_stage(
            command.stage_id,
            project_id=command.project_id,
        )
        if stage is None:
            raise RuntimeStageNotFound()
        task = await repository.get_worker_task(
            command.worker_task_id,
            project_id=command.project_id,
            for_update=True,
        )
        if task is None or task.stage_id != stage.id:
            raise WorkerTaskNotFound()
        if task.idempotency_key != command.idempotency_key:
            raise SchedulingConflict("角色任务幂等键不匹配")
        if task.task_status == ExecutionStatus.SUCCESS:
            return ExecuteWorkerResult(
                worker_task_id=task.id,
                task_status=task.task_status,
                result_summary=task.result_summary,
                replayed=True,
            )
        if task.task_status == ExecutionStatus.FAILED:
            raise SchedulingConflict("失败角色任务不能重复执行")
        TaskStateMachine.ensure_transition(task.task_status, ExecutionStatus.RUNNING)
        changed = await repository.claim_worker_task(
            task.id,
            started_at=datetime.now(UTC),
        )
        if not changed:
            raise SchedulingConflict()
        return None

    async def run_model(
        self,
        command: ExecuteWorkerCommand,
        *,
        repository: SchedulingRepository,
    ) -> str:
        request = await self.build_model_request(command, repository=repository)
        return await self.call_model(request)

    async def build_model_request(
        self,
        command: ExecuteWorkerCommand,
        *,
        repository: SchedulingRepository,
    ) -> ModelRequest:
        """在短数据库会话中构建模型请求，返回后即可释放连接。"""
        project = await repository.get_project(command.project_id)
        if project is None:
            raise ProjectRuntimeNotFound()
        CancelPolicy.ensure_not_cancelled(project)
        stage = await repository.get_stage(
            command.stage_id,
            project_id=command.project_id,
        )
        task = await repository.get_worker_task(
            command.worker_task_id,
            project_id=command.project_id,
        )
        if stage is None:
            raise RuntimeStageNotFound()
        if task is None:
            raise WorkerTaskNotFound()
        RoleRegistry.ensure_allowed(task.worker_role, stage.stage_name)
        assembled = await self._context_assembler.assemble(task=task, stage=stage)
        return ModelRequest(
            system_prompt=assembled.system_prompt,
            user_prompt=assembled.user_prompt,
            context=assembled.context,
            tools=assembled.tools,
            output_schema=self._output_schema(task.worker_role),
        )

    async def call_model(self, request: ModelRequest) -> str:
        """模型网络调用不持有数据库事务或行锁。"""
        result = await self._model.complete(request)
        summary = redact_sensitive_text(result.summary, max_length=4000)
        if not summary:
            raise ValueError("模型结果摘要为空")
        return summary

    async def finalize_success(
        self,
        command: ExecuteWorkerCommand,
        *,
        result_summary: str,
        repository: SchedulingRepository,
    ) -> tuple[ExecuteWorkerResult, list[WorkerTaskMessage], uuid.UUID | None]:
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
        task = await repository.get_worker_task(
            command.worker_task_id,
            project_id=command.project_id,
            for_update=True,
        )
        if task is None:
            raise WorkerTaskNotFound()
        TaskStateMachine.ensure_transition(task.task_status, ExecutionStatus.SUCCESS)
        now = datetime.now(UTC)
        changed = await repository.complete_worker_task(
            task.id,
            result_summary=result_summary,
            finished_at=now,
        )
        if not changed:
            raise SchedulingConflict()
        await repository.append_event(
            project_id=project.id,
            event_type="worker_status",
            aggregate_type="worker_task",
            aggregate_id=str(task.id),
            payload={
                "worker_task_id": str(task.id),
                "worker_role": task.worker_role,
                "task_status": ExecutionStatus.SUCCESS.value,
                "request_id": str(command.request_id),
            },
            occurred_at=now,
        )

        stage_tasks = await repository.list_stage_tasks(stage.id)
        stage_tasks = [
            updated_task
            if updated_task.id != task.id
            else dataclass_replace_status(updated_task, ExecutionStatus.SUCCESS)
            for updated_task in stage_tasks
        ]
        completed_roles = {item.worker_role for item in stage_tasks if item.task_status == ExecutionStatus.SUCCESS}
        existing_roles = {item.worker_role for item in stage_tasks}
        ready_specs = TaskDistributionPolicy.ready_roles(
            stage.stage_name,
            completed_roles,
            existing_roles,
        )
        messages: list[WorkerTaskMessage] = []
        for spec in ready_specs:
            key = f"stage:{stage.id}:role:{spec.worker_role}:request:{command.request_id}"
            next_task = await repository.create_worker_task(
                project_id=project.id,
                stage_id=stage.id,
                worker_role=spec.worker_role,
                task_content=spec.task_content,
                request_id=command.request_id,
                idempotency_key=key,
            )
            messages.append(
                WorkerTaskMessage(
                    project_id=project.id,
                    stage_id=stage.id,
                    worker_task_id=next_task.id,
                    request_id=command.request_id,
                    idempotency_key=key,
                )
            )

        all_specs = TaskDistributionPolicy.tasks_for(stage.stage_name)
        terminal_roles = {item.worker_role for item in stage_tasks if item.task_status.is_terminal}
        next_stage_id: uuid.UUID | None = None
        if not ready_specs and {spec.worker_role for spec in all_specs}.issubset(terminal_roles):
            failed_critical = any(
                item.task_status == ExecutionStatus.FAILED
                and TaskDistributionPolicy.is_critical(
                    stage.stage_name,
                    item.worker_role,
                )
                for item in stage_tasks
            )
            if not failed_critical:
                if stage.stage_name.value == "environment_scan" and project.project_status == "created":
                    if not await repository.mark_project_running(
                        project.id,
                        started_at=now,
                    ):
                        raise SchedulingConflict("项目运行状态更新冲突")
                    await repository.append_event(
                        project_id=project.id,
                        event_type="project_status",
                        aggregate_type="project",
                        aggregate_id=str(project.id),
                        payload={
                            "project_status": "running",
                            "request_id": str(command.request_id),
                        },
                        occurred_at=now,
                    )
                stage_changed = await repository.transition_stage(
                    stage.id,
                    expected_status=ExecutionStatus.RUNNING,
                    target_status=ExecutionStatus.SUCCESS,
                    changed_at=now,
                )
                if not stage_changed:
                    raise SchedulingConflict("阶段完成状态更新冲突")
                await repository.append_event(
                    project_id=project.id,
                    event_type="stage_status",
                    aggregate_type="runtime_stage",
                    aggregate_id=str(stage.id),
                    payload={
                        "stage_id": str(stage.id),
                        "stage_name": stage.stage_name.value,
                        "stage_status": ExecutionStatus.SUCCESS.value,
                        "request_id": str(command.request_id),
                    },
                    occurred_at=now,
                )
                next_stage = await repository.get_next_stage(stage)
                next_stage_id = next_stage.id if next_stage is not None else None
        return (
            ExecuteWorkerResult(
                worker_task_id=task.id,
                task_status=ExecutionStatus.SUCCESS,
                result_summary=result_summary,
            ),
            messages,
            next_stage_id,
        )

    async def handle(
        self,
        command: ExecuteWorkerCommand,
        *,
        repository: SchedulingRepository,
        dispatcher: StageTaskDispatcher,
    ) -> ExecuteWorkerResult:
        replay = await self.claim(command, repository=repository)
        if replay is not None:
            return replay
        summary = await self.run_model(command, repository=repository)
        result, messages, _ = await self.finalize_success(
            command,
            result_summary=summary,
            repository=repository,
        )
        if messages:
            await dispatcher.dispatch_workers(messages)
        return result

    @staticmethod
    def _output_schema(worker_role: str) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["summary"],
            "properties": {
                "summary": {"type": "string", "minLength": 1, "maxLength": 4000},
                "role": {"const": worker_role},
                "findings": {"type": "array", "items": {"type": "object"}},
            },
            "additionalProperties": True,
        }


def dataclass_replace_status(
    task: WorkerTask,
    status: ExecutionStatus,
) -> WorkerTask:
    """局部替换不可变实体状态，避免事务内再次查询。"""
    from dataclasses import replace

    return replace(task, task_status=status)
