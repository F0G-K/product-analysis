from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from backend.ai.evidence import ConfidenceAssessor, EvidenceLinker
from backend.ai.langgraph_workflow import LangGraphAnalysisWorkflow
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
from backend.ai.workflow import WorkflowRoles
from backend.core.enums import ReviewOperation, TaskStatus, TaskType
from backend.domain.task import ModelBinding, Task
from tests.fakes import (
    FakeGovernance,
    FakeLLMGateway,
    FakeResultStore,
    FakeRetriever,
    FakeRuleAnalyzer,
    FakeSnapshotStore,
)


class LangGraphWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupt_and_resume_to_completed(self) -> None:
        result_store = FakeResultStore()
        masker = SensitiveDataMasker()
        workflow = LangGraphAnalysisWorkflow(
            WorkflowRoles(
                validator=InputValidatorRole(),
                snapshot_locker=SnapshotLockerRole(FakeSnapshotStore(), masker),
                retriever=DocumentRetrieverRole(FakeRetriever(), masker),
                rule_analyst=RuleAnalystRole(FakeRuleAnalyzer()),
                llm_analyst=LLMAnalystRole(
                    FakeLLMGateway(), FakeGovernance(), masker
                ),
                evidence_linker=EvidenceLinkerRole(EvidenceLinker()),
                confidence_assessor=ConfidenceAssessorRole(ConfidenceAssessor()),
                review_coordinator=HumanReviewCoordinatorRole(),
                finalizer=ResultFinalizerRole(result_store),
            ),
            MemorySaver(),
        )
        task = Task(
            id=uuid4(),
            tenant_id=uuid4(),
            project_id=uuid4(),
            task_type=TaskType.ASSESSMENT,
            status=TaskStatus.DRAFT,
            title="LangGraph 集成测试",
            created_by=uuid4(),
            model_binding=ModelBinding(
                name="claude-opus-4-8",
                version="20260724",
                prompt_version="abc1234",
                temperature=Decimal("0.20"),
            ),
        )

        pending = await workflow.start(
            task=task,
            input_data={"name": "画像看板"},
            query="评估业务价值",
        )
        completed = await workflow.resume(
            task_id=str(task.id),
            decision=ReviewDecision(
                operation=ReviewOperation.CONFIRMED,
                actor_id=task.created_by,
            ),
        )

        self.assertEqual(pending.task.status, TaskStatus.PENDING_REVIEW)
        self.assertEqual(completed.task.status, TaskStatus.COMPLETED)
        self.assertEqual(len(result_store.results), 1)


if __name__ == "__main__":
    unittest.main()
