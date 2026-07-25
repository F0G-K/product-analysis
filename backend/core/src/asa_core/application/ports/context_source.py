"""AI 上下文数据来源 Port。"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from asa_core.domain.scheduling.entities import RuntimeStage, WorkerTask


@dataclass(frozen=True, slots=True)
class ProjectContext:
    project_name: str
    task_content: str
    environment_type: str


class AgentContextSource(ABC):
    """只暴露经过裁剪的结构化数据，不向角色提供数据库访问。"""

    @abstractmethod
    async def get_project_context(self, project_id: uuid.UUID) -> ProjectContext: ...

    @abstractmethod
    async def get_previous_results(
        self,
        project_id: uuid.UUID,
        stage: RuntimeStage,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_source_snippets(self, task: WorkerTask) -> list[dict[str, Any]]: ...
