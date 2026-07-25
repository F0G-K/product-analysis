from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.projects.service import Project


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    status: str
    timezone: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: Project) -> ProjectResponse:
        return cls(
            id=project.id,
            tenant_id=project.tenant_id,
            name=project.name,
            description=project.description,
            status=project.status,
            timezone=project.timezone,
            settings=project.settings,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
