"""安全知识检索 Port。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from asa_core.domain.scheduling.entities import RuntimeStage, WorkerTask


@dataclass(frozen=True, slots=True)
class KnowledgeMatch:
    title: str
    content_summary: str
    knowledge_type: str
    similarity: float


class RagRetriever(ABC):
    """RAG 是增强能力，调用方必须允许返回空结果。"""

    @abstractmethod
    async def retrieve_for_task(
        self,
        *,
        task: WorkerTask,
        stage: RuntimeStage,
        query_text: str,
    ) -> list[KnowledgeMatch]: ...


class NoOpRagRetriever(RagRetriever):
    async def retrieve_for_task(
        self,
        *,
        task: WorkerTask,
        stage: RuntimeStage,
        query_text: str,
    ) -> list[KnowledgeMatch]:
        return []
