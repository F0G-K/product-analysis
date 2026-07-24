from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from backend.ai.evidence import ConfidenceAssessor, EvidenceLinker
from backend.ai.masking import SensitiveDataMasker
from backend.ai.roles import (
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
from backend.ai.state import ReviewDecision
from backend.ai.workflow import AnalysisWorkflow, WorkflowRoles
from backend.core.enums import ReviewOperation, TaskStatus, TaskType
from backend.core.errors import AnalysisError, TokenBudgetExceededError
from backend.domain.task import ModelBinding, Task
from tests.fakes import (
    FakeGovernance,
    FakeLLMGateway,
    FakeResultStore,
    FakeRetriever,
    FakeRuleAnalyzer,
    FakeSnapshotStore,
)


def make_task() -> Task:
    return Task(
        id=uuid4(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        task_type=TaskType.ASSESSMENT,
        status=TaskStatus.DRAFT,
        title="需求价值评估",
        created_by=uuid4(),
        model_binding=ModelBinding(
            name="claude-opus-4-8",
            version="20260724",
            prompt_version="abc1234",
            temperature=Decimal("0.20"),
        ),
    )


class AIWorkflowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.snapshot_store = FakeSnapshotStore()
        self.rule_analyzer = FakeRuleAnalyzer()
        self.gateway = FakeLLMGateway()
        self.governance = FakeGovernance()
        self.result_store = FakeResultStore()
        masker = SensitiveDataMasker()
        self.workflow = AnalysisWorkflow(
            WorkflowRoles(
                validator=InputValidatorRole(),
                snapshot_locker=SnapshotLockerRole(self.snapshot_store, masker),
                retriever=DocumentRetrieverRole(FakeRetriever()),
                rule_analyst=RuleAnalystRole(self.rule_analyzer),
                llm_analyst=LLMAnalystRole(self.gateway, self.governance, masker),
                evidence_linker=EvidenceLinkerRole(EvidenceLinker()),
                confidence_assessor=ConfidenceAssessorRole(ConfidenceAssessor()),
                review_coordinator=HumanReviewCoordinatorRole(),
                finalizer=ResultFinalizerRole(self.result_store),
            )
        )

    async def test_pipeline_masks_sensitive_data_and_waits_for_review(self) -> None:
        outcome = await self.workflow.start(
            task=make_task(),
            input_data={
                "owner": "zhangsan@example.com",
                "phone": "13812345678",
                "token": "token=secret-value",
            },
            query="评估业务价值",
            check_items=({"name": "成本范围", "deterministic": True},),
        )

        self.assertTrue(outcome.awaiting_review)
        self.assertEqual(outcome.task.status, TaskStatus.PENDING_REVIEW)
        self.assertEqual(self.rule_analyzer.calls, 1)
        self.assertEqual(self.snapshot_store.inputs[0]["owner"], "***@***.***")
        self.assertEqual(self.snapshot_store.inputs[0]["phone"], "1**********")
        self.assertEqual(self.snapshot_store.inputs[0]["token"], "token=***")
        self.assertEqual(len(self.governance.records), 1)
        self.assertEqual(outcome.state.evidence[0]["evidence_type"], "fact")
        self.assertEqual(outcome.state.evidence[1]["evidence_type"], "inference")

    async def test_confirm_is_only_path_to_completed(self) -> None:
        started = await self.workflow.start(
            task=make_task(),
            input_data={"name": "画像看板"},
            query="评估业务价值",
        )
        completed = await self.workflow.resume(
            started.state,
            ReviewDecision(
                operation=ReviewOperation.CONFIRMED,
                actor_id=started.task.created_by,
            ),
        )
        self.assertEqual(completed.task.status, TaskStatus.COMPLETED)
        self.assertEqual(len(self.result_store.results), 1)

    async def test_revision_creates_new_snapshot_and_returns_to_review(self) -> None:
        started = await self.workflow.start(
            task=make_task(),
            input_data={"name": "画像看板"},
            query="评估业务价值",
        )
        old_snapshot_id = started.task.input_snapshot_id
        revised = await self.workflow.resume(
            started.state,
            ReviewDecision(
                operation=ReviewOperation.REVISED,
                actor_id=started.task.created_by,
                reason="补充用户覆盖数据",
                revision={"coverage": "10000 MAU"},
            ),
        )
        self.assertEqual(revised.task.status, TaskStatus.PENDING_REVIEW)
        self.assertNotEqual(revised.task.input_snapshot_id, old_snapshot_id)
        self.assertEqual(len(self.snapshot_store.inputs), 2)
        self.assertEqual(self.snapshot_store.inputs[1]["coverage"], "10000 MAU")

    async def test_model_version_drift_fails_and_is_recorded(self) -> None:
        gateway = FakeLLMGateway(model_version="unexpected-version")
        masker = SensitiveDataMasker()
        governance = FakeGovernance()
        workflow = AnalysisWorkflow(
            WorkflowRoles(
                validator=InputValidatorRole(),
                snapshot_locker=SnapshotLockerRole(self.snapshot_store, masker),
                retriever=DocumentRetrieverRole(FakeRetriever()),
                rule_analyst=RuleAnalystRole(self.rule_analyzer),
                llm_analyst=LLMAnalystRole(gateway, governance, masker),
                evidence_linker=EvidenceLinkerRole(EvidenceLinker()),
                confidence_assessor=ConfidenceAssessorRole(ConfidenceAssessor()),
                review_coordinator=HumanReviewCoordinatorRole(),
                finalizer=ResultFinalizerRole(self.result_store),
            )
        )

        with self.assertRaises(AnalysisError):
            await workflow.start(
                task=make_task(), input_data={"name": "画像看板"}, query="评估"
            )
        self.assertEqual(len(governance.records), 1)
        self.assertEqual(governance.records[0]["error"]["type"], "AnalysisError")

    async def test_prompt_over_budget_does_not_leave_reserved_tokens(self) -> None:
        started = await self.workflow.start(
            task=make_task(),
            input_data={"name": "画像看板"},
            query="评估业务价值",
        )
        started.state.token_budget.limit = 1
        with self.assertRaises(TokenBudgetExceededError):
            await self.workflow.resume(
                started.state,
                ReviewDecision(
                    operation=ReviewOperation.REVISED,
                    actor_id=started.task.created_by,
                    reason="补充材料",
                    revision={"long_text": "x" * 1000},
                ),
            )
        self.assertEqual(started.state.token_budget.reserved, 0)


if __name__ == "__main__":
    unittest.main()
