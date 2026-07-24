from __future__ import annotations

from dataclasses import dataclass

from backend.core.enums import TaskType
from backend.core.errors import TokenBudgetExceededError

TOKEN_LIMITS: dict[TaskType, int] = {
    TaskType.ASSESSMENT: 32_768,
    TaskType.CONSISTENCY_CHECK: 65_536,
    TaskType.ATTRIBUTION: 131_072,
}


@dataclass(slots=True)
class TokenBudget:
    limit: int
    used: int = 0
    reserved: int = 0

    @classmethod
    def for_task_type(cls, task_type: TaskType) -> TokenBudget:
        return cls(limit=TOKEN_LIMITS[task_type])

    @property
    def remaining(self) -> int:
        return self.limit - self.used - self.reserved

    def reserve(self, estimated_tokens: int) -> None:
        if estimated_tokens <= 0:
            raise ValueError("estimated_tokens 必须大于 0")
        if estimated_tokens > self.remaining:
            raise TokenBudgetExceededError(
                limit=self.limit,
                used=self.used + self.reserved,
                requested=estimated_tokens,
            )
        self.reserved += estimated_tokens

    def settle(self, *, estimated_tokens: int, actual_tokens: int) -> None:
        if estimated_tokens <= 0 or actual_tokens < 0:
            raise ValueError("token 数量不合法")
        if estimated_tokens > self.reserved:
            raise ValueError("结算数量超过已预留 token")
        if self.used + actual_tokens > self.limit:
            raise TokenBudgetExceededError(
                limit=self.limit,
                used=self.used,
                requested=actual_tokens,
            )

        self.reserved -= estimated_tokens
        self.used += actual_tokens

    def release(self, estimated_tokens: int) -> None:
        if estimated_tokens <= 0 or estimated_tokens > self.reserved:
            raise ValueError("释放数量超过已预留 token")
        self.reserved -= estimated_tokens
