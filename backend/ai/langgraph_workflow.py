from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.ai.roles import AIRole
from backend.ai.state import AnalysisOutcome, AnalysisState, ReviewDecision
from backend.ai.workflow import NoopExecutionGuard, NoopProgressRecorder, WorkflowRoles
from backend.core.enums import ConfidenceLevel, ReviewOperation, TaskStatus
from backend.core.errors import AnalysisError, ErrorCode
from backend.domain.ports import TaskExecutionGuard, TaskProgressRecorder
from backend.domain.task import Task


class LangGraphAnalysisWorkflow:
    """生产工作流：PostgreSQL checkpointer 由应用启动时注入。"""

    def __init__(
        self,
        roles: WorkflowRoles,
        checkpointer: Any,
        execution_guard: TaskExecutionGuard | None = None,
        progress_recorder: TaskProgressRecorder | None = None,
    ) -> None:
        self._roles = roles
        self._execution_guard = execution_guard or NoopExecutionGuard()
        self._progress_recorder = progress_recorder or NoopProgressRecorder()
        self._graph = self._build_graph(checkpointer)

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
        state = AnalysisState(
            task=(
                task.transition(TaskStatus.VALIDATING)
                if task.status == TaskStatus.DRAFT
                else task
            ),
            input_data=dict(input_data),
            query=query,
            retrieval_filters=dict(retrieval_filters or {}),
            check_items=check_items,
        )
        await self._progress_recorder.record(state.task)
        config = {"configurable": {"thread_id": str(task.id)}}
        result = await self._graph.ainvoke(state, config=config)
        return self._to_outcome(result)

    async def resume(
        self, *, task_id: str, decision: ReviewDecision
    ) -> AnalysisOutcome:
        from langgraph.types import Command

        config = {"configurable": {"thread_id": task_id}}
        result = await self._graph.ainvoke(Command(resume=decision), config=config)
        return self._to_outcome(result)

    def _build_graph(self, checkpointer: Any) -> Any:
        graph = StateGraph(AnalysisState)
        graph.add_node("validate_input", self._validate)
        graph.add_node("lock_snapshot", self._lock_snapshot)
        graph.add_node("retrieve_docs", self._retrieve_docs)
        graph.add_node("run_rules", self._run_rules)
        graph.add_node("llm_analyze", self._llm_analyze)
        graph.add_node("link_evidence", self._link_evidence)
        graph.add_node("calc_confidence", self._calc_confidence)
        graph.add_node("prepare_review", self._prepare_review)
        graph.add_node("human_review", self._human_review)
        graph.add_node("finalize", self._finalize)

        graph.add_conditional_edges(
            START,
            self._route_start,
            {"validate": "validate_input", "analyze": "lock_snapshot"},
        )
        graph.add_edge("validate_input", "lock_snapshot")
        graph.add_edge("lock_snapshot", "retrieve_docs")
        graph.add_conditional_edges(
            "retrieve_docs",
            self._route_after_retrieval,
            {"has_rule_items": "run_rules", "llm_only": "llm_analyze"},
        )
        graph.add_edge("run_rules", "llm_analyze")
        graph.add_edge("llm_analyze", "link_evidence")
        graph.add_edge("link_evidence", "calc_confidence")
        graph.add_edge("calc_confidence", "prepare_review")
        graph.add_edge("prepare_review", "human_review")
        graph.add_conditional_edges(
            "human_review",
            self._route_after_review,
            {"confirmed": "finalize", "revised": "lock_snapshot", "rejected": END},
        )
        graph.add_edge("finalize", END)
        return graph.compile(checkpointer=checkpointer)

    async def _validate(self, state: AnalysisState) -> AnalysisState:
        await self._execution_guard.ensure_active(state.task)
        state = await self._roles.validator.execute(state)
        state = state.with_task(state.task.transition(TaskStatus.ANALYZING))
        await self._progress_recorder.record(state.task)
        return state

    async def _lock_snapshot(self, state: AnalysisState) -> AnalysisState:
        return await self._execute_role(state, self._roles.snapshot_locker)

    async def _retrieve_docs(self, state: AnalysisState) -> AnalysisState:
        return await self._execute_role(state, self._roles.retriever)

    async def _run_rules(self, state: AnalysisState) -> AnalysisState:
        return await self._execute_role(state, self._roles.rule_analyst)

    async def _llm_analyze(self, state: AnalysisState) -> AnalysisState:
        return await self._execute_role(state, self._roles.llm_analyst)

    async def _link_evidence(self, state: AnalysisState) -> AnalysisState:
        return await self._execute_role(state, self._roles.evidence_linker)

    async def _calc_confidence(self, state: AnalysisState) -> AnalysisState:
        return await self._execute_role(state, self._roles.confidence_assessor)

    async def _finalize(self, state: AnalysisState) -> AnalysisState:
        state = await self._execute_role(state, self._roles.finalizer)
        await self._progress_recorder.record(state.task)
        return state

    async def _prepare_review(self, state: AnalysisState) -> AnalysisState:
        state = await self._roles.review_coordinator.execute(state)
        await self._progress_recorder.record(state.task)
        return state

    async def _execute_role(self, state: AnalysisState, role: AIRole) -> AnalysisState:
        await self._execution_guard.ensure_active(state.task)
        return await role.execute(state)

    async def _human_review(self, state: AnalysisState) -> AnalysisState:
        raw_decision = interrupt(
            {
                "task_id": str(state.task.id),
                "status": state.task.status.value,
                "confidence": state.confidence,
            }
        )
        decision = self._normalize_decision(raw_decision)
        state = replace(state, review=decision)
        if decision.operation == ReviewOperation.CONFIRMED:
            return state
        state = await self._roles.review_coordinator.execute(state)
        await self._progress_recorder.record(state.task)
        return state

    @staticmethod
    def _route_start(state: AnalysisState) -> str:
        return "analyze" if state.task.status == TaskStatus.ANALYZING else "validate"

    @staticmethod
    def _route_after_retrieval(state: AnalysisState) -> str:
        has_deterministic = any(
            item.get("deterministic") is True for item in state.check_items
        )
        return "has_rule_items" if has_deterministic else "llm_only"

    @staticmethod
    def _route_after_review(state: AnalysisState) -> str:
        if state.task.status == TaskStatus.FAILED:
            return "rejected"
        if state.review and state.review.operation == ReviewOperation.CONFIRMED:
            return "confirmed"
        return "revised"

    @staticmethod
    def _normalize_decision(value: Any) -> ReviewDecision:
        if isinstance(value, ReviewDecision):
            return value
        if not isinstance(value, Mapping):
            raise AnalysisError(ErrorCode.ANALYSIS_FAILED, "人工确认参数不合法")
        try:
            from uuid import UUID

            return ReviewDecision(
                operation=ReviewOperation(str(value["operation"])),
                actor_id=UUID(str(value["actor_id"])),
                reason=value.get("reason"),
                revision=value.get("revision", {}),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AnalysisError(
                ErrorCode.ANALYSIS_FAILED,
                "人工确认参数不合法",
                detail=str(exc),
            ) from exc

    @staticmethod
    def _to_outcome(raw_state: Any) -> AnalysisOutcome:
        state = LangGraphAnalysisWorkflow._normalize_state(raw_state)
        level_value = state.confidence.get("level")
        confidence = ConfidenceLevel(level_value) if level_value else None
        return AnalysisOutcome(
            task=state.task,
            state=state,
            awaiting_review=state.task.status == TaskStatus.PENDING_REVIEW,
            confidence_level=confidence,
        )

    @staticmethod
    def _normalize_state(value: Any) -> AnalysisState:
        if isinstance(value, AnalysisState):
            return value
        if isinstance(value, Mapping):
            fields = AnalysisState.__dataclass_fields__
            payload = {key: item for key, item in value.items() if key in fields}
            return AnalysisState(**payload)
        raise AnalysisError(ErrorCode.ANALYSIS_FAILED, "工作流返回状态不合法")
