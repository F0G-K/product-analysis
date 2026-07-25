"""统一模型调用 Port。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelTool:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ModelRequest:
    system_prompt: str
    user_prompt: str
    context: dict[str, Any]
    tools: tuple[ModelTool, ...]
    output_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ModelResult:
    content: dict[str, Any]
    summary: str
    prompt_tokens: int
    completion_tokens: int


class ModelPort(ABC):
    """业务代码不直接依赖任何模型供应商 SDK。"""

    @abstractmethod
    async def complete(self, request: ModelRequest) -> ModelResult: ...

    @abstractmethod
    def estimate_tokens(self, text: str) -> int: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
