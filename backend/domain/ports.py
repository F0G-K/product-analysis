from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from backend.core.enums import TaskStatus, TaskType
from backend.domain.task import ModelBinding, Task

if TYPE_CHECKING:
    from backend.ai.state import AnalysisOutcome, ReviewDecision


@dataclass(frozen=True, slots=True)
class TaskFilters:
    task_type: TaskType | None = None
    status: TaskStatus | None = None
    project_id: UUID | None = None
    created_by: UUID | None = None
    project_ids: tuple[UUID, ...] | None = None


class TaskRepository(Protocol):
    async def get(self, task_id: UUID, *, for_update: bool = False) -> Task | None: ...

    async def list(
        self,
        filters: TaskFilters,
        *,
        page: int,
        page_size: int,
        sort_by: str,
    ) -> tuple[Sequence[Task], int]: ...

    async def add(self, task: Task) -> None: ...

    async def save(self, task: Task) -> None: ...

    async def has_retry(self, task_id: UUID) -> bool: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TaskRepositoryFactory(Protocol):
    def __call__(self, tenant_id: UUID) -> AbstractAsyncContextManager[TaskRepository]: ...


class DistributedLock(Protocol):
    async def __aenter__(self) -> bool: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class LockManager(Protocol):
    def lock(self, key: str, *, ttl_seconds: int) -> DistributedLock: ...


class TaskQueue(Protocol):
    async def enqueue(
        self,
        task_id: UUID,
        task_type: TaskType,
        tenant_id: UUID,
    ) -> str: ...

    async def cancel(self, task_id: UUID, *, terminate: bool = False) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: str, payload: Mapping[str, Any]) -> None: ...


class AnalysisInputStore(Protocol):
    async def get(self, task_id: UUID) -> Mapping[str, Any] | None: ...

    async def copy(self, source_task_id: UUID, target_task_id: UUID) -> None: ...


class SnapshotStore(Protocol):
    async def create_immutable_snapshot(
        self,
        *,
        task: Task,
        input_data: Mapping[str, Any],
    ) -> tuple[UUID, Mapping[str, Any]]: ...


class DocumentRetriever(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: UUID,
        project_id: UUID,
        task_type: TaskType,
        filters: Mapping[str, Any],
        top_k: int,
    ) -> Sequence[Mapping[str, Any]]: ...


class RuleAnalyzer(Protocol):
    async def analyze(
        self,
        *,
        task_type: TaskType,
        documents: Sequence[Mapping[str, Any]],
        check_items: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    request_id: str | None = None
    model_version: str | None = None
    is_cached: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: Mapping[str, Any]
    usage: LLMUsage


class LLMGateway(Protocol):
    async def analyze(
        self,
        *,
        tenant_id: UUID,
        task_type: TaskType,
        model: ModelBinding,
        prompt_name: str,
        context: Sequence[Mapping[str, Any]],
        rule_results: Sequence[Mapping[str, Any]],
        input_data: Mapping[str, Any],
        max_output_tokens: int,
    ) -> LLMResponse: ...


class LLMCache(Protocol):
    async def get(self, key: str) -> LLMResponse | None: ...

    async def set(self, key: str, response: LLMResponse, *, ttl_seconds: int) -> None: ...


class GovernanceRecorder(Protocol):
    async def record(
        self,
        *,
        task: Task,
        call_phase: str,
        prompt_name: str,
        model: ModelBinding,
        max_tokens: int,
        usage: LLMUsage | None,
        latency_ms: int,
        error: Mapping[str, Any] | None = None,
    ) -> None: ...


class ResultStore(Protocol):
    async def save_analysis_result(
        self,
        *,
        task: Task,
        result: Mapping[str, Any],
        evidence: Sequence[Mapping[str, Any]],
        confidence: Mapping[str, Any],
    ) -> None: ...


class WorkflowRunner(Protocol):
    async def start(
        self,
        *,
        task: Task,
        input_data: Mapping[str, Any],
        query: str,
        retrieval_filters: Mapping[str, Any] | None = None,
        check_items: tuple[Mapping[str, Any], ...] = (),
    ) -> AnalysisOutcome: ...


class ResumableWorkflowRunner(WorkflowRunner, Protocol):
    async def resume(
        self,
        *,
        task_id: str,
        decision: ReviewDecision,
    ) -> AnalysisOutcome: ...


class TaskExecutionGuard(Protocol):
    async def ensure_active(self, task: Task) -> None: ...


class TaskProgressRecorder(Protocol):
    async def record(self, task: Task) -> None: ...


class AsyncClosable(Protocol):
    async def aclose(self) -> None: ...


class AsyncStateStream(Protocol):
    def __aiter__(self) -> AsyncIterator[Mapping[str, Any]]: ...
