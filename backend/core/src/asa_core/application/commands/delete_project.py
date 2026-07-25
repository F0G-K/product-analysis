"""删除项目受理用例。"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.project_repository import ProjectRepository
from asa_core.application.project_support import (
    build_request_fingerprint,
    ensure_idempotent_match,
    validate_idempotency_key,
)
from asa_core.domain.projects.exceptions import (
    ProjectNameConfirmationMismatch,
    ProjectNotFound,
)
from asa_core.domain.projects.status_machine import ProjectStatusMachine


@dataclass(frozen=True)
class DeleteProjectCommand:
    project_id: uuid.UUID
    actor_user_id: uuid.UUID
    actor_is_admin: bool
    request_id: uuid.UUID
    idempotency_key: str
    confirm_project_name: str


@dataclass(frozen=True)
class DeleteProjectResult:
    response_data: dict[str, Any]
    replayed: bool


class DeleteProjectHandler:
    """事务内校验确认名称并记录异步清理请求。"""

    def __init__(self, audit_logger: AuditLogger):
        self._audit_logger = audit_logger

    async def handle(
        self,
        command: DeleteProjectCommand,
        *,
        project_repo: ProjectRepository,
    ) -> DeleteProjectResult:
        idempotency_key = validate_idempotency_key(command.idempotency_key)
        fingerprint = build_request_fingerprint(
            actor_user_id=command.actor_user_id,
            project_id=command.project_id,
            operation="delete",
            payload={"confirm_project_name": command.confirm_project_name},
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
                expected_operation="delete",
                expected_fingerprint=fingerprint,
            )
            return DeleteProjectResult(existing.response_data, True)

        await project_repo.acquire_project_lock(command.project_id)
        project = await project_repo.find_accessible(
            command.project_id,
            actor_user_id=command.actor_user_id,
            actor_is_admin=command.actor_is_admin,
            for_update=True,
        )
        if project is None:
            raise ProjectNotFound()
        ProjectStatusMachine.ensure_can_delete(project.project_status)
        if command.confirm_project_name != project.project_name:
            raise ProjectNameConfirmationMismatch()

        accepted_at = datetime.now(UTC)
        response_data = {
            "project_id": str(project.id),
            "operation": "delete",
            "accepted_at": accepted_at.isoformat(),
        }
        await project_repo.create_operation(
            actor_user_id=command.actor_user_id,
            project_id=project.id,
            operation="delete",
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
                "operation": "delete_requested",
                "project_status": project.project_status,
                "request_id": str(command.request_id),
            },
            occurred_at=accepted_at,
        )
        await self._audit_logger.log(
            action="project_delete",
            object_type="project",
            result_status="success",
            actor_user_id=command.actor_user_id,
            project_id=project.id,
            request_id=command.request_id,
            idempotency_key=idempotency_key,
        )
        return DeleteProjectResult(response_data, False)
