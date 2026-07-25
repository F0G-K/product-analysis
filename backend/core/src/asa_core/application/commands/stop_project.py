"""停止项目受理用例。"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.project_repository import ProjectRepository
from asa_core.application.project_support import (
    build_request_fingerprint,
    ensure_idempotent_match,
    redact_user_text,
    validate_idempotency_key,
)
from asa_core.domain.projects.exceptions import ProjectNotFound, ProjectNotRunning
from asa_core.domain.projects.status_machine import ProjectStatusMachine


@dataclass(frozen=True)
class StopProjectCommand:
    project_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_is_admin: bool
    request_id: uuid.UUID
    idempotency_key: str
    reason: str | None


@dataclass(frozen=True)
class StopProjectResult:
    response_data: dict[str, Any]
    replayed: bool


class StopProjectHandler:
    """原子记录停止意图，最终状态由 Worker 收敛。"""

    def __init__(self, audit_logger: AuditLogger):
        self._audit_logger = audit_logger

    async def handle(
        self,
        command: StopProjectCommand,
        *,
        project_repo: ProjectRepository,
    ) -> StopProjectResult:
        idempotency_key = validate_idempotency_key(command.idempotency_key)
        reason = redact_user_text(command.reason, max_length=500)
        fingerprint = build_request_fingerprint(
            actor_user_id=command.actor_user_id,
            project_id=command.project_id,
            operation="stop",
            # 指纹使用原始请求内容；持久化事件和审计仍只写脱敏文本。
            payload={"reason": command.reason},
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
                expected_operation="stop",
                expected_fingerprint=fingerprint,
            )
            return StopProjectResult(existing.response_data, True)

        await project_repo.acquire_project_lock(command.project_id)
        project = await project_repo.find_accessible(
            command.project_id,
            actor_user_id=command.actor_user_id,
            actor_is_admin=command.actor_is_admin,
            for_update=True,
        )
        if project is None:
            raise ProjectNotFound()
        ProjectStatusMachine.ensure_can_stop(project.project_status)

        already_requested = project.stop_requested_at is not None
        accepted_at = project.stop_requested_at or datetime.now(UTC)
        if not already_requested:
            updated = await project_repo.set_stop_requested(
                project.id,
                expected_status=project.project_status,
                stop_requested_at=accepted_at,
            )
            if not updated:
                raise ProjectNotRunning(project.project_status)

        response_data = {
            "project_id": str(project.id),
            "project_status": project.project_status,
            "stop_requested_at": accepted_at.isoformat(),
            "operation": "stop",
        }
        await project_repo.create_operation(
            actor_user_id=command.actor_user_id,
            project_id=project.id,
            operation="stop",
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            response_data=response_data,
            accepted_at=accepted_at,
        )
        if not already_requested:
            await project_repo.append_event(
                project_id=project.id,
                event_type="project_status",
                aggregate_type="project",
                aggregate_id=str(project.id),
                payload={
                    "operation": "stop_requested",
                    "project_status": project.project_status,
                    "reason": reason,
                    "request_id": str(command.request_id),
                },
                occurred_at=accepted_at,
            )
        await self._audit_logger.log(
            action="project_stop",
            object_type="project",
            result_status="success",
            actor_user_id=command.actor_user_id,
            project_id=project.id,
            request_id=command.request_id,
            idempotency_key=idempotency_key,
            metadata={"reason": reason} if reason else None,
        )
        return StopProjectResult(response_data, already_requested)
