"""Celery 消息边界校验。"""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StageTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: UUID
    stage_id: UUID
    request_id: UUID
    idempotency_key: Annotated[str, Field(min_length=1, max_length=128)]
    schema_version: Annotated[int, Field(ge=1, le=1)] = 1


class WorkerTaskPayload(StageTaskPayload):
    worker_task_id: UUID
