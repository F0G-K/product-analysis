from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class APIResponse[DataT](BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: int = 0
    message: str = "success"
    data: DataT
    request_id: str


class PageData[DataT](BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DataT]
    total: int
    page: int
    page_size: int
