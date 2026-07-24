from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.core.enums import TaskStatus, TaskType
from backend.domain.task import Task


class TaskCreatorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: UUID
    project_id: UUID
    task_type: TaskType
    status: TaskStatus
    title: str
    description: str | None
    input_snapshot_id: UUID | None
    model_name: str | None
    model_version: str | None
    prompt_version: str | None
    temperature: Decimal | None
    created_by: TaskCreatorResponse
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None
    retry_count: int
    retry_of_task_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, task: Task) -> TaskResponse:
        binding = task.model_binding
        return cls(
            id=task.id,
            tenant_id=task.tenant_id,
            project_id=task.project_id,
            task_type=task.task_type,
            status=task.status,
            title=task.title,
            description=task.description,
            input_snapshot_id=task.input_snapshot_id,
            model_name=binding.name if binding else None,
            model_version=binding.version if binding else None,
            prompt_version=binding.prompt_version if binding else None,
            temperature=binding.temperature if binding else None,
            created_by=TaskCreatorResponse(id=task.created_by),
            confirmed_by=task.confirmed_by,
            confirmed_at=task.confirmed_at,
            completed_at=task.completed_at,
            failure_reason=task.failure_reason,
            retry_count=task.retry_count,
            retry_of_task_id=task.retry_of_task_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
