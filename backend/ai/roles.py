from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from backend.ai.evidence import ConfidenceAssessor, EvidenceLinker
from backend.ai.masking import SensitiveDataMasker
from backend.ai.state import AnalysisState
from backend.core.enums import AIRoleName, ReviewOperation, TaskStatus
from backend.core.errors import AnalysisError, ErrorCode
from backend.domain.ports import (
    DocumentRetriever,
    GovernanceRecorder,
    LLMGateway,
    ResultStore,
    RuleAnalyzer,
    SnapshotStore,
)


class AIRole(ABC):
    name: AIRoleName

    @abstractmethod
    async def execute(self, state: AnalysisState) -> AnalysisState:
        """执行单一 AI 角色职责并返回新状态。"""


class InputValidatorRole(AIRole):
    name = AIRoleName.INPUT_VALIDATOR

    async def execute(self, state: AnalysisState) -> AnalysisState:
        errors: list[dict[str, str]] = []
        if not state.query.strip():
            errors.append({"field": "query", "message": "分析查询不能为空"})
        if not state.input_data:
            errors.append({"field": "input_data", "message": "分析输入不能为空"})
        if state.task.model_binding is None:
            errors.append({"field": "model_binding", "message": "任务必须绑定模型版本"})
        if errors:
            raise AnalysisError(
                ErrorCode.ANALYSIS_FAILED,
                "分析输入校验失败",
                context={"errors": errors},
            )
        return replace(state, current_role=self.name.value)


class SnapshotLockerRole(AIRole):
    name = AIRoleName.SNAPSHOT_LOCKER

    def __init__(self, store: SnapshotStore, masker: SensitiveDataMasker) -> None:
        self._store = store
        self._masker = masker

    async def execute(self, state: AnalysisState) -> AnalysisState:
        masked_input = self._masker.mask(state.input_data)
        snapshot_id, snapshot_data = await self._store.create_immutable_snapshot(
            task=state.task,
            input_data=masked_input,
        )
        task = replace(state.task, input_snapshot_id=snapshot_id)
        return replace(
            state,
            task=task,
            current_role=self.name.value,
            snapshot_id=snapshot_id,
            snapshot_data=snapshot_data,
        )


class DocumentRetrieverRole(AIRole):
    name = AIRoleName.DOCUMENT_RETRIEVER

    def __init__(
        self,
        retriever: DocumentRetriever,
        masker: SensitiveDataMasker | None = None,
    ) -> None:
        self._retriever = retriever
        self._masker = masker or SensitiveDataMasker()

    async def execute(self, state: AnalysisState) -> AnalysisState:
        documents = await self._retriever.retrieve(
            query=self._masker.mask_text(state.query),
            tenant_id=state.task.tenant_id,
            project_id=state.task.project_id,
            task_type=state.task.task_type,
            filters=self._masker.mask(state.retrieval_filters),
            top_k=20,
        )
        return replace(
            state,
            current_role=self.name.value,
            retrieved_docs=tuple(self._masker.mask(documents)),
        )


class RuleAnalystRole(AIRole):
    name = AIRoleName.RULE_ANALYST

    def __init__(self, analyzer: RuleAnalyzer) -> None:
        self._analyzer = analyzer

    async def execute(self, state: AnalysisState) -> AnalysisState:
        deterministic_items = tuple(
            item for item in state.check_items if item.get("deterministic") is True
        )
        if not deterministic_items:
            return replace(state, current_role=self.name.value, rule_results=())

        results = await self._analyzer.analyze(
            task_type=state.task.task_type,
            documents=state.retrieved_docs,
            check_items=deterministic_items,
        )
        normalized = tuple({**item, "confidence": "high"} for item in results)
        return replace(
            state,
            current_role=self.name.value,
            rule_results=normalized,
        )


class LLMAnalystRole(AIRole):
    name = AIRoleName.LLM_ANALYST
    MAX_OUTPUT_TOKENS = 4_096

    _prompt_names = {
        "assessment": "assessment_scoring",
        "consistency_check": "consistency_comparison",
        "attribution": "attribution_inference",
    }

    def __init__(
        self,
        gateway: LLMGateway,
        governance: GovernanceRecorder,
        masker: SensitiveDataMasker,
    ) -> None:
        self._gateway = gateway
        self._governance = governance
        self._masker = masker

    async def execute(self, state: AnalysisState) -> AnalysisState:
        model = state.task.model_binding
        budget = state.token_budget
        if model is None or budget is None:
            raise AnalysisError(ErrorCode.ANALYSIS_FAILED, "任务缺少模型或 token 预算")

        estimated_prompt_tokens = self._estimate_prompt_tokens(state)
        max_output_tokens = min(
            self.MAX_OUTPUT_TOKENS,
            budget.remaining - estimated_prompt_tokens,
        )
        if max_output_tokens <= 0:
            # 输入上下文已经超过任务预算时，不向模型发起部分请求。
            budget.reserve(estimated_prompt_tokens + 1)
        reserved_tokens = estimated_prompt_tokens + max_output_tokens
        budget.reserve(reserved_tokens)
        started_at = time.monotonic()
        usage = None
        error: Mapping[str, Any] | None = None
        prompt_name = self._prompt_names[state.task.task_type.value]

        try:
            response = await self._gateway.analyze(
                tenant_id=state.task.tenant_id,
                task_type=state.task.task_type,
                model=model,
                prompt_name=prompt_name,
                context=self._masker.mask(state.retrieved_docs),
                rule_results=self._masker.mask(state.rule_results),
                input_data=self._masker.mask(state.snapshot_data),
                max_output_tokens=max_output_tokens,
            )
            usage = response.usage
            if usage.model_version and usage.model_version != model.version:
                raise AnalysisError(
                    ErrorCode.ANALYSIS_FAILED,
                    "模型实际版本与任务绑定版本不一致",
                    detail=f"expected={model.version}, actual={usage.model_version}",
                )
            budget.settle(
                estimated_tokens=reserved_tokens,
                actual_tokens=usage.total_tokens,
            )
            return replace(
                state,
                current_role=self.name.value,
                llm_result=dict(response.content),
            )
        except Exception as exc:
            if reserved_tokens <= budget.reserved:
                budget.release(reserved_tokens)
            error = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            latency_ms = int((time.monotonic() - started_at) * 1000)
            await self._governance.record(
                task=state.task,
                call_phase=prompt_name,
                prompt_name=prompt_name,
                model=model,
                max_tokens=max_output_tokens,
                usage=usage,
                latency_ms=latency_ms,
                error=error,
            )

    @staticmethod
    def _estimate_prompt_tokens(state: AnalysisState) -> int:
        payload = {
            "input": state.snapshot_data,
            "documents": state.retrieved_docs,
            "rules": state.rule_results,
        }
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
        # 无 tokenizer 时使用保守估算；网关返回的实际用量负责最终结算。
        return max(1, len(serialized.encode("utf-8")) // 3)


class EvidenceLinkerRole(AIRole):
    name = AIRoleName.EVIDENCE_LINKER

    def __init__(self, linker: EvidenceLinker) -> None:
        self._linker = linker

    async def execute(self, state: AnalysisState) -> AnalysisState:
        evidence = self._linker.link(state.llm_result, state.retrieved_docs)
        return replace(state, current_role=self.name.value, evidence=evidence)


class ConfidenceAssessorRole(AIRole):
    name = AIRoleName.CONFIDENCE_ASSESSOR

    def __init__(self, assessor: ConfidenceAssessor) -> None:
        self._assessor = assessor

    async def execute(self, state: AnalysisState) -> AnalysisState:
        confidence = self._assessor.assess(state.evidence)
        return replace(state, current_role=self.name.value, confidence=confidence)


class HumanReviewCoordinatorRole(AIRole):
    name = AIRoleName.HUMAN_REVIEW_COORDINATOR

    async def execute(self, state: AnalysisState) -> AnalysisState:
        if state.review is None:
            task = state.task.transition(TaskStatus.PENDING_REVIEW)
            return replace(state, task=task, current_role=self.name.value)

        if state.review.operation == ReviewOperation.REVISED:
            revised_input = self._merge_revision(state.input_data, state.review.revision)
            task = state.task.transition(TaskStatus.ANALYZING)
            return replace(
                state,
                task=task,
                input_data=revised_input,
                current_role=self.name.value,
                review=None,
                llm_result={},
                evidence=(),
                confidence={},
            )
        if state.review.operation == ReviewOperation.REJECTED:
            reason = state.review.reason or "人工驳回分析结果"
            task = state.task.transition(
                TaskStatus.FAILED,
                failure_reason=reason,
                error_details={"phase": self.name.value, "reason": reason},
            )
            return replace(state, task=task, current_role=self.name.value)
        return replace(state, current_role=self.name.value)

    @staticmethod
    def _merge_revision(
        original: Mapping[str, Any], revision: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        merged = dict(original)
        merged.update(revision)
        return merged


class ResultFinalizerRole(AIRole):
    name = AIRoleName.RESULT_FINALIZER

    def __init__(self, store: ResultStore) -> None:
        self._store = store

    async def execute(self, state: AnalysisState) -> AnalysisState:
        if state.review is None or state.review.operation != ReviewOperation.CONFIRMED:
            raise AnalysisError(ErrorCode.ANALYSIS_FAILED, "缺少有效的人工确认")
        await self._store.save_analysis_result(
            task=state.task,
            result=state.llm_result,
            evidence=state.evidence,
            confidence=state.confidence,
        )
        task = state.task.transition(TaskStatus.COMPLETED, actor_id=state.review.actor_id)
        return replace(state, task=task, current_role=self.name.value)
