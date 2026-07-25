from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.core.enums import TaskType


class AnalysisTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: TaskType
    title: str = Field(min_length=1, max_length=256)
    description: str | None = None
    query: str = Field(min_length=1, max_length=2000)
    input_data: dict[str, Any]

    @model_validator(mode="after")
    def validate_input_data(self) -> AnalysisTaskCreateRequest:
        if not self.input_data:
            raise ValueError("分析材料不能为空")
        return self
