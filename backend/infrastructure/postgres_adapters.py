from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.ports import LLMUsage
from backend.domain.task import ModelBinding, Task
from backend.models.analysis import (
    EvidenceItemModel,
    ModelGovernanceRecordModel,
    SnapshotModel,
)


class SQLAlchemyScenarioResultWriter(Protocol):
    async def save_result(
        self,
        *,
        session: AsyncSession,
        task: Task,
        result: Mapping[str, Any],
        confidence: Mapping[str, Any],
    ) -> None: ...


class PostgresSnapshotStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_immutable_snapshot(
        self,
        *,
        task: Task,
        input_data: Mapping[str, Any],
    ) -> tuple[UUID, Mapping[str, Any]]:
        snapshot_id = uuid4()
        snapshot_data = dict(input_data)
        async with self._session_factory() as session, session.begin():
            await self._set_tenant_context(session, task.tenant_id)
            session.add(
                SnapshotModel(
                    id=snapshot_id,
                    tenant_id=task.tenant_id,
                    task_type=task.task_type.value,
                    task_id=task.id,
                    snapshot_data=snapshot_data,
                    associated_deliverable_versions=[],
                )
            )
        return snapshot_id, snapshot_data

    @staticmethod
    async def _set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )


class PostgresGovernanceRecorder:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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
    ) -> None:
        async with self._session_factory() as session, session.begin():
            await PostgresSnapshotStore._set_tenant_context(session, task.tenant_id)
            session.add(
                ModelGovernanceRecordModel(
                    tenant_id=task.tenant_id,
                    task_type=task.task_type.value,
                    task_id=task.id,
                    call_phase=call_phase,
                    model_name=model.name,
                    model_version=model.version,
                    prompt_template_version=model.prompt_version,
                    prompt_template_name=prompt_name,
                    temperature=model.temperature,
                    max_tokens=max_tokens,
                    prompt_tokens=usage.prompt_tokens if usage else None,
                    completion_tokens=usage.completion_tokens if usage else None,
                    total_tokens=usage.total_tokens if usage else None,
                    latency_ms=latency_ms,
                    request_id=usage.request_id if usage else None,
                    is_cached=usage.is_cached if usage else False,
                    error_info=dict(error) if error else None,
                )
            )


class PostgresResultStore:
    """在同一完成动作中写入场景结果和公共证据。"""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        scenario_writer: SQLAlchemyScenarioResultWriter,
    ) -> None:
        self._session_factory = session_factory
        self._scenario_writer = scenario_writer

    async def save_analysis_result(
        self,
        *,
        task: Task,
        result: Mapping[str, Any],
        evidence: Sequence[Mapping[str, Any]],
        confidence: Mapping[str, Any],
    ) -> None:
        async with self._session_factory() as session, session.begin():
            await PostgresSnapshotStore._set_tenant_context(session, task.tenant_id)
            # 场景结果与公共证据使用同一事务，任何一步失败均整体回滚。
            await self._scenario_writer.save_result(
                session=session,
                task=task,
                result=result,
                confidence=confidence,
            )
            await session.execute(
                delete(EvidenceItemModel).where(
                    EvidenceItemModel.tenant_id == task.tenant_id,
                    EvidenceItemModel.task_id == task.id,
                    EvidenceItemModel.task_type == task.task_type.value,
                )
            )
            session.add_all(
                [
                    EvidenceItemModel(
                        tenant_id=task.tenant_id,
                        task_type=task.task_type.value,
                        task_id=task.id,
                        evidence_type=str(item["evidence_type"]),
                        citation_location=self._text(item.get("citation_location")),
                        content_summary=self._text(item.get("content_summary")),
                        related_conclusion_id=self._text(
                            item.get("related_conclusion_id")
                        ),
                        excerpt_text=self._text(item.get("excerpt_text")),
                    )
                    for item in evidence
                ]
            )

    @staticmethod
    def _text(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None


class UnavailableScenarioResultWriter:
    async def save_result(
        self,
        *,
        session: AsyncSession,
        task: Task,
        result: Mapping[str, Any],
        confidence: Mapping[str, Any],
    ) -> None:
        raise RuntimeError(
            f"任务类型 {task.task_type.value} 未配置场景结果持久化处理器"
        )
