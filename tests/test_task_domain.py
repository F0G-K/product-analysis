from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from backend.core.enums import ProjectRole, TaskStatus, TaskType
from backend.core.errors import BusinessError, PermissionDeniedError, TokenBudgetExceededError
from backend.domain.task import ModelBinding, Task, TaskActor
from backend.domain.token_budget import TokenBudget


def make_task(status: TaskStatus = TaskStatus.DRAFT, retry_count: int = 0) -> Task:
    return Task(
        id=uuid4(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        task_type=TaskType.ASSESSMENT,
        status=status,
        title="需求价值评估",
        created_by=uuid4(),
        model_binding=ModelBinding(
            name="claude-opus-4-8",
            version="20260724",
            prompt_version="abc1234",
            temperature=Decimal("0.30"),
        ),
        retry_count=retry_count,
    )


class TaskDomainTests(unittest.TestCase):
    def test_state_machine_rejects_skipping_human_review(self) -> None:
        task = make_task().transition(TaskStatus.VALIDATING).transition(TaskStatus.ANALYZING)
        with self.assertRaises(BusinessError):
            task.transition(TaskStatus.COMPLETED, actor_id=uuid4())

    def test_failed_task_retry_creates_new_traceable_task(self) -> None:
        task = make_task(TaskStatus.FAILED, retry_count=2)
        retried = task.create_retry()
        self.assertNotEqual(task.id, retried.id)
        self.assertEqual(retried.retry_of_task_id, task.id)
        self.assertEqual(retried.retry_count, 3)
        self.assertEqual(retried.status, TaskStatus.DRAFT)

    def test_retry_limit_is_enforced(self) -> None:
        with self.assertRaises(BusinessError):
            make_task(TaskStatus.FAILED, retry_count=3).create_retry()

    def test_project_member_cannot_manage_another_users_task(self) -> None:
        task = make_task()
        actor = TaskActor(
            user_id=uuid4(),
            tenant_id=task.tenant_id,
            project_roles={task.project_id: ProjectRole.PROJECT_MEMBER},
        )
        with self.assertRaises(PermissionDeniedError):
            task.ensure_actor_can_manage(actor)

    def test_token_budget_accounts_for_actual_usage(self) -> None:
        budget = TokenBudget(limit=200)
        budget.reserve(150)
        with self.assertRaises(TokenBudgetExceededError):
            budget.settle(estimated_tokens=150, actual_tokens=201)
        self.assertEqual(budget.reserved, 150)
        self.assertEqual(budget.used, 0)


if __name__ == "__main__":
    unittest.main()
