from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any
from uuid import UUID, uuid4

from backend.core.enums import TaskType
from backend.domain.task import Task


class InMemorySnapshotStore:
    """开发适配器；生产环境应替换为 PostgreSQL 元数据 + MinIO 文件存储。"""

    def __init__(self) -> None:
        self._snapshots: dict[UUID, Mapping[str, Any]] = {}

    async def create_immutable_snapshot(
        self,
        *,
        task: Task,
        input_data: Mapping[str, Any],
    ) -> tuple[UUID, Mapping[str, Any]]:
        snapshot_id = uuid4()
        snapshot = deepcopy(dict(input_data))
        self._snapshots[snapshot_id] = snapshot
        return snapshot_id, deepcopy(snapshot)


class NoopDocumentRetriever:
    """显式空检索器，保证无向量服务时结论只能降级为低置信度。"""

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: UUID,
        project_id: UUID,
        task_type: TaskType,
        filters: Mapping[str, Any],
        top_k: int,
    ) -> Sequence[Mapping[str, Any]]:
        return ()


class UnavailableDocumentRetriever:
    async def retrieve(self, **kwargs: Any) -> Sequence[Mapping[str, Any]]:
        raise RuntimeError("生产环境未配置 RAG DocumentRetriever")


class DeterministicRuleAnalyzer:
    async def analyze(
        self,
        *,
        task_type: TaskType,
        documents: Sequence[Mapping[str, Any]],
        check_items: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]:
        results: list[Mapping[str, Any]] = []
        for item in check_items:
            if "result" not in item:
                continue
            results.append(
                {
                    "rule_id": item.get("rule_id"),
                    "dimension": item.get("dimension"),
                    "title": item.get("title"),
                    "result": item["result"],
                    "evidence": item.get("evidence", []),
                }
            )
        return tuple(results)


class InMemoryResultStore:
    def __init__(self) -> None:
        self._results: dict[UUID, Mapping[str, Any]] = {}

    async def save_analysis_result(
        self,
        *,
        task: Task,
        result: Mapping[str, Any],
        evidence: Sequence[Mapping[str, Any]],
        confidence: Mapping[str, Any],
    ) -> None:
        self._results[task.id] = {
            "result": deepcopy(dict(result)),
            "evidence": deepcopy(list(evidence)),
            "confidence": deepcopy(dict(confidence)),
        }


class InMemoryGovernanceRecorder:
    def __init__(self) -> None:
        self._records: list[Mapping[str, Any]] = []

    async def record(self, **record: Any) -> None:
        self._records.append(dict(record))
