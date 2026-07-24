from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from backend.ai.roles import (
    AIRole,
    ConfidenceAssessorRole,
    DocumentRetrieverRole,
    EvidenceLinkerRole,
    HumanReviewCoordinatorRole,
    InputValidatorRole,
    LLMAnalystRole,
    ResultFinalizerRole,
    RuleAnalystRole,
    SnapshotLockerRole,
)
from backend.ai.state import AnalysisOutcome, AnalysisState, ReviewDecision
from backend.core.enums import ConfidenceLevel, ReviewOperation, TaskStatus
from backend.core.errors import AnalysisError, ErrorCode
from backend.domain.ports import TaskExecutionGuard, TaskProgressRecorder
from backend.domain.task import Task


class NoopExecutionGuard:
    async def ensure_active(self, task: Task) -> None:
        return None


class NoopProgressRecorder:
    async def record(self, task: Task) -> None:
        return None


@dataclass(frozen=True, slots=True)
class WorkflowRoles:
    validator: InputValidatorRole
    snapshot_locker: SnapshotLockerRole
    retriever: DocumentRetrieverRole
    rule_analyst: RuleAnalystRole
    llm_analyst: LLMAnalystRole
    evidence_linker: EvidenceLinkerRole
    confidence_assessor: ConfidenceAssessorRole
    review_coordinator: HumanReviewCoordinatorRole
    finalizer: ResultFinalizerRole


class AnalysisWorkflow:
    """LangGraph 可直接映射的确定性工作流核心。"""

    def __init__(
        self,
        roles: WorkflowRoles,
        execution_guard: TaskExecutionGuard | None = None,
        progress_recorder: TaskProgressRecorder | None = None,
    ) -> None:
        self._roles = roles
        self._execution_guard = execution_guard or NoopExecutionGuard()
        self._progress_recorder = progress_recorder or NoopProgressRecorder()

    async def start(
        self,
        *,
        task: Task,
        input_data: Mapping[str, Any],
        query: str,
        retrieval_filters: Mapping[str, Any] | None = None,
        check_items: tuple[Mapping[str, Any], ...] = (),
    ) -> AnalysisOutcome:
        if task.status not in {
            TaskStatus.DRAFT,
            TaskStatus.VALIDATING,
            TaskStatus.ANALYZING,
        }:
            raise AnalysisError(
                ErrorCode.ANALYSIS_FAILED,
                "仅草稿任务可以启动分析",
                detail=task.status.value,
            )

        if task.status == TaskStatus.DRAFT:
            task = task.transition(TaskStatus.VALIDATING)
            await self._progress_recorder.record(task)
        state = AnalysisState(
            task=task,
            input_data=dict(input_data),
            query=query,
            retrieval_filters=dict(retrieval_filters or {}),
            check_items=check_items,
        )
        if state.task.status == TaskStatus.VALIDATING:
            state = await self._execute_role(state, self._roles.validator)
            state = state.with_task(state.task.transition(TaskStatus.ANALYZING))
            await self._progress_recorder.record(state.task)
        state = await self._analyze(state, lock_snapshot=True)
        state = await self._roles.review_coordinator.execute(state)
        await self._progress_recorder.record(state.task)
        return self._outcome(state, awaiting_review=True)

    async def resume(self, state: AnalysisState, decision: ReviewDecision) -> AnalysisOutcome:
        if state.task.status != TaskStatus.PENDING_REVIEW:
            raise AnalysisError(
                ErrorCode.ANALYSIS_FAILED,
                "仅待确认任务可以恢复工作流",
                detail=state.task.status.value,
            )

        state = replace(state, review=decision)
        if decision.operation == ReviewOperation.CONFIRMED:
            state = await self._roles.finalizer.execute(state)
            await self._progress_recorder.record(state.task)
            return self._outcome(state, awaiting_review=False)

        state = await self._roles.review_coordinator.execute(state)
        if decision.operation == ReviewOperation.REJECTED:
            await self._progress_recorder.record(state.task)
            return self._outcome(state, awaiting_review=False)

        await self._progress_recorder.record(state.task)
        # 修正输入必须生成新快照，保留旧快照才能复现上一轮分析。
        state = await self._analyze(state, lock_snapshot=True)
        state = await self._roles.review_coordinator.execute(state)
        await self._progress_recorder.record(state.task)
        return self._outcome(state, awaiting_review=True)

    async def _analyze(
        self, state: AnalysisState, *, lock_snapshot: bool
    ) -> AnalysisState:
        if lock_snapshot:
            state = await self._execute_role(state, self._roles.snapshot_locker)
        state = await self._execute_role(state, self._roles.retriever)
        state = await self._execute_role(state, self._roles.rule_analyst)
        state = await self._execute_role(state, self._roles.llm_analyst)
        state = await self._execute_role(state, self._roles.evidence_linker)
        return await self._execute_role(state, self._roles.confidence_assessor)

    async def _execute_role(self, state: AnalysisState, role: AIRole) -> AnalysisState:
        await self._execution_guard.ensure_active(state.task)
        return await role.execute(state)

    @staticmethod
    def _outcome(state: AnalysisState, *, awaiting_review: bool) -> AnalysisOutcome:
        level_value = state.confidence.get("level")
        level = ConfidenceLevel(level_value) if level_value else None
        return AnalysisOutcome(
            task=state.task,
            state=state,
            awaiting_review=awaiting_review,
            confidence_level=level,
        )
