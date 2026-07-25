"""启动项目受理用例。"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.project_repository import (
    ProjectRepository,
    StartProjectResources,
)
from asa_core.application.project_support import (
    build_request_fingerprint,
    ensure_idempotent_match,
    validate_idempotency_key,
)
from asa_core.domain.projects.exceptions import (
    EnvironmentTypeDisabled,
    ProjectCapacityExceeded,
    ProjectNotFound,
    ProjectStatusConflict,
)
from asa_core.domain.projects.status_machine import ProjectStatusMachine
from asa_core.domain.projects.validators import SourcePathValidator


@dataclass(frozen=True)
class StartProjectCommand:
    project_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_is_admin: bool
    request_id: uuid.UUID
    idempotency_key: str


@dataclass(frozen=True)
class StartProjectResult:
    response_data: dict[str, Any]
    resources: StartProjectResources | None
    replayed: bool


class StartProjectHandler:
    """在同一事务内受理启动并创建运行资源、幂等记录与 Outbox。"""

    def __init__(self, audit_logger: AuditLogger):
        self._audit_logger = audit_logger

    async def handle(
        self,
        command: StartProjectCommand,
        *,
        project_repo: ProjectRepository,
    ) -> StartProjectResult:
        idempotency_key = validate_idempotency_key(command.idempotency_key)
        fingerprint = build_request_fingerprint(
            actor_user_id=command.actor_user_id,
            project_id=command.project_id,
            operation="start",
            payload={},
        )

        await project_repo.acquire_operation_lock(
            actor_user_id=command.actor_user_id,
            idempotency_key=idempotency_key,
        )
        existing = await project_repo.find_operation(
            actor_user_id=command.actor_user_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            ensure_idempotent_match(
                existing_operation=existing.operation,
                existing_fingerprint=existing.request_fingerprint,
                expected_operation="start",
                expected_fingerprint=fingerprint,
            )
            return StartProjectResult(
                existing.response_data,
                self._resources_from_response(existing.response_data),
                True,
            )

        await project_repo.acquire_project_lock(command.project_id)
        project = await project_repo.find_accessible(
            command.project_id,
            actor_user_id=command.actor_user_id,
            actor_is_admin=command.actor_is_admin,
            for_update=True,
        )
        if project is None:
            raise ProjectNotFound()
        ProjectStatusMachine.ensure_can_start(project.project_status)
        if await project_repo.has_runtime(project.id):
            # `created` 状态下存在运行实例，说明启动请求已经被其他幂等键受理。
            raise ProjectStatusConflict(project.project_status, [])

        enabled_environment_types, max_concurrent_projects = (
            await project_repo.get_active_configuration()
        )
        if project.environment_type not in enabled_environment_types:
            raise EnvironmentTypeDisabled(project.environment_type)
        SourcePathValidator.validate(project.source_type, project.source_path)

        # 全局容量锁将“计数 + 创建运行资源”串行化，避免并发超卖。
        await project_repo.acquire_capacity_lock()
        if max_concurrent_projects is not None:
            running_count = await project_repo.count_running()
            if running_count >= max_concurrent_projects:
                raise ProjectCapacityExceeded(max_concurrent_projects)

        resources = await project_repo.create_start_resources(
            project=project,
            request_id=command.request_id,
            # Worker 幂等键使用请求指纹，避免 API Key 达到 128 字符时越过数据库上限。
            worker_idempotency_key=f"project-start:{fingerprint}",
        )
        accepted_at = datetime.now(UTC)
        response_data = {
            "project_id": str(project.id),
            "project_status": project.project_status,
            "operation": "start",
            "accepted_at": accepted_at.isoformat(),
            # 内部字段用于 Broker 故障后的同 Key 重投递，API 响应模型会裁剪。
            "_runtime_id": str(resources.runtime_id),
            "_first_stage_id": str(resources.first_stage_id),
            "_worker_task_id": str(resources.worker_task_id),
        }
        await project_repo.create_operation(
            actor_user_id=command.actor_user_id,
            project_id=project.id,
            operation="start",
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            response_data=response_data,
            accepted_at=accepted_at,
        )
        await project_repo.append_event(
            project_id=project.id,
            event_type="project_status",
            aggregate_type="project",
            aggregate_id=str(project.id),
            payload={
                "operation": "start_requested",
                "project_status": project.project_status,
                "runtime_id": str(resources.runtime_id),
                "worker_task_id": str(resources.worker_task_id),
                "request_id": str(command.request_id),
            },
            occurred_at=accepted_at,
        )
        await self._audit_logger.log(
            action="project_start",
            object_type="project",
            result_status="success",
            actor_user_id=command.actor_user_id,
            project_id=project.id,
            request_id=command.request_id,
            idempotency_key=idempotency_key,
        )
        return StartProjectResult(response_data, resources, False)

    @staticmethod
    def _resources_from_response(
        response_data: dict[str, Any],
    ) -> StartProjectResources | None:
        try:
            return StartProjectResources(
                runtime_id=uuid.UUID(str(response_data["_runtime_id"])),
                first_stage_id=uuid.UUID(str(response_data["_first_stage_id"])),
                worker_task_id=uuid.UUID(str(response_data["_worker_task_id"])),
            )
        except (KeyError, TypeError, ValueError):
            return None
