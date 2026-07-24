from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any
from uuid import UUID

from backend.core.enums import ConfidenceLevel, ReviewOperation
from backend.domain.task import Task
from backend.domain.token_budget import TokenBudget


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    operation: ReviewOperation
    actor_id: UUID
    reason: str | None = None
    revision: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.operation in {ReviewOperation.REVISED, ReviewOperation.REJECTED}:
            if not self.reason or not self.reason.strip():
                raise ValueError("修正或驳回必须填写原因")


@dataclass(slots=True)
class AnalysisState:
    task: Task
    input_data: Mapping[str, Any]
    query: str
    retrieval_filters: Mapping[str, Any] = field(default_factory=dict)
    check_items: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    current_role: str | None = None
    snapshot_id: UUID | None = None
    snapshot_data: Mapping[str, Any] = field(default_factory=dict)
    retrieved_docs: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    rule_results: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    llm_result: Mapping[str, Any] = field(default_factory=dict)
    evidence: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    confidence: Mapping[str, Any] = field(default_factory=dict)
    review: ReviewDecision | None = None
    errors: list[Mapping[str, Any]] = field(default_factory=list)
    token_budget: TokenBudget | None = None

    def __post_init__(self) -> None:
        if self.token_budget is None:
            self.token_budget = TokenBudget.for_task_type(self.task.task_type)

    def with_task(self, task: Task) -> AnalysisState:
        return replace(self, task=task)


@dataclass(frozen=True, slots=True)
class AnalysisOutcome:
    task: Task
    state: AnalysisState
    awaiting_review: bool
    confidence_level: ConfidenceLevel | None = None

