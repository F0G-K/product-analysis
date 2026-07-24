from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Any
from uuid import UUID, uuid4

from backend.domain.ports import LLMResponse, LLMUsage, TaskFilters
from backend.domain.task import Task


class MemoryRepository:
    def __init__(self, tasks: dict[UUID, Task], tenant_id: UUID) -> None:
        self.tasks = tasks
        self.tenant_id = tenant_id
        self.commits = 0
        self.rollbacks = 0

    async def get(self, task_id: UUID, *, for_update: bool = False) -> Task | None:
        task = self.tasks.get(task_id)
        return task if task and task.tenant_id == self.tenant_id else None

    async def list(self, filters: TaskFilters, **kwargs: Any) -> tuple[Sequence[Task], int]:
        tasks = [task for task in self.tasks.values() if task.tenant_id == self.tenant_id]
        if filters.task_type:
            tasks = [task for task in tasks if task.task_type == filters.task_type]
        if filters.status:
            tasks = [task for task in tasks if task.status == filters.status]
        if filters.project_id:
            tasks = [task for task in tasks if task.project_id == filters.project_id]
        if filters.created_by:
            tasks = [task for task in tasks if task.created_by == filters.created_by]
        if filters.project_ids is not None:
            tasks = [task for task in tasks if task.project_id in filters.project_ids]
        return tuple(tasks), len(tasks)

    async def add(self, task: Task) -> None:
        self.tasks[task.id] = task

    async def save(self, task: Task) -> None:
        self.tasks[task.id] = task

    async def has_retry(self, task_id: UUID) -> bool:
        return any(task.retry_of_task_id == task_id for task in self.tasks.values())

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class RepositoryContext(AbstractAsyncContextManager[MemoryRepository]):
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    async def __aenter__(self) -> MemoryRepository:
        return self.repository

    async def __aexit__(self, *args: object) -> None:
        return None


class MemoryRepositoryFactory:
    def __init__(self, tasks: dict[UUID, Task]) -> None:
        self.tasks = tasks
        self.instances: list[MemoryRepository] = []

    def __call__(self, tenant_id: UUID) -> RepositoryContext:
        repository = MemoryRepository(self.tasks, tenant_id)
        self.instances.append(repository)
        return RepositoryContext(repository)


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[UUID, Any, UUID]] = []
        self.cancelled: list[UUID] = []
        self.fail_enqueue = False

    async def enqueue(self, task_id: UUID, task_type: Any, tenant_id: UUID) -> str:
        if self.fail_enqueue:
            raise ConnectionError("queue unavailable")
        self.enqueued.append((task_id, task_type, tenant_id))
        return str(task_id)

    async def cancel(self, task_id: UUID, *, terminate: bool = False) -> None:
        self.cancelled.append(task_id)


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, Mapping[str, Any]]] = []

    async def publish(self, event: str, payload: Mapping[str, Any]) -> None:
        self.events.append((event, payload))


class MemoryInputStore:
    def __init__(self, values: dict[UUID, Mapping[str, Any]] | None = None) -> None:
        self.values = values or {}

    async def get(self, task_id: UUID) -> Mapping[str, Any] | None:
        return self.values.get(task_id)

    async def copy(self, source_task_id: UUID, target_task_id: UUID) -> None:
        self.values[target_task_id] = dict(self.values[source_task_id])


class FakeSnapshotStore:
    def __init__(self) -> None:
        self.inputs: list[Mapping[str, Any]] = []

    async def create_immutable_snapshot(self, *, task: Task, input_data: Mapping[str, Any]):
        self.inputs.append(input_data)
        return uuid4(), dict(input_data)


class FakeRetriever:
    async def retrieve(self, **kwargs: Any):
        return (
            {"citation": "doc-1:section-a", "content": "事实一"},
            {"citation": "doc-2:section-b", "content": "事实二"},
        )


class FakeRuleAnalyzer:
    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, **kwargs: Any):
        self.calls += 1
        return ({"rule_id": "rule-1"},)


class FakeLLMGateway:
    def __init__(self, model_version: str = "20260724") -> None:
        self.model_version = model_version
        self.calls: list[Mapping[str, Any]] = []

    async def analyze(self, **kwargs: Any) -> LLMResponse:
        self.calls.append(kwargs)
        return LLMResponse(
            content={
                "summary": "分析完成",
                "evidence": [
                    {
                        "evidence_type": "fact",
                        "citation_location": "doc-1:section-a",
                        "content_summary": "可回查事实",
                    },
                    {
                        "evidence_type": "fact",
                        "citation_location": "not-exists",
                        "content_summary": "不可回查内容",
                    },
                ],
            },
            usage=LLMUsage(
                prompt_tokens=100,
                completion_tokens=50,
                request_id="req-1",
                model_version=self.model_version,
            ),
        )


class FakeGovernance:
    def __init__(self) -> None:
        self.records: list[Mapping[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        self.records.append(kwargs)


class FakeResultStore:
    def __init__(self) -> None:
        self.results: list[Mapping[str, Any]] = []

    async def save_analysis_result(self, **kwargs: Any) -> None:
        self.results.append(kwargs)
