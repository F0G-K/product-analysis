from __future__ import annotations

import unittest
from uuid import uuid4

from backend.core.enums import ProjectRole, TaskStatus, TaskType
from backend.core.errors import BusinessError, ExternalServiceError, ResourceConflictError
from backend.domain.task import Task, TaskActor
from backend.scheduling.service import TaskSchedulerService
from tests.fakes import (
    FakePublisher,
    FakeQueue,
    MemoryInputStore,
    MemoryRepositoryFactory,
)


def make_task(status: TaskStatus = TaskStatus.DRAFT, retry_count: int = 0) -> Task:
    return Task(
        id=uuid4(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        task_type=TaskType.CONSISTENCY_CHECK,
        status=status,
        title="交付物一致性检查",
        created_by=uuid4(),
        retry_count=retry_count,
    )


def make_actor(task: Task, *, is_admin: bool = False) -> TaskActor:
    return TaskActor(
        user_id=uuid4() if is_admin else task.created_by,
        tenant_id=task.tenant_id,
        project_roles={
            task.project_id: (
                ProjectRole.PROJECT_ADMIN if is_admin else ProjectRole.PROJECT_MEMBER
            )
        },
    )


class TaskSchedulerServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.task = make_task()
        self.tasks = {self.task.id: self.task}
        self.factory = MemoryRepositoryFactory(self.tasks)
        self.queue = FakeQueue()
        self.publisher = FakePublisher()
        self.inputs = MemoryInputStore({self.task.id: {"query": "字段一致性"}})
        self.service = TaskSchedulerService(
            self.factory,
            self.queue,
            self.publisher,
            self.inputs,
        )

    async def test_cancel_persists_before_best_effort_revoke(self) -> None:
        cancelled = await self.service.cancel(self.task.id, make_actor(self.task))
        self.assertEqual(cancelled.status, TaskStatus.CANCELLED)
        self.assertEqual(self.tasks[self.task.id].status, TaskStatus.CANCELLED)
        self.assertEqual(self.queue.cancelled, [self.task.id])
        self.assertEqual(self.publisher.events[0][0], "task.status_changed")

    async def test_dispatch_marks_task_validating_before_enqueue(self) -> None:
        queue_id = await self.service.dispatch(self.task.id, make_actor(self.task))
        self.assertEqual(queue_id, str(self.task.id))
        self.assertEqual(self.tasks[self.task.id].status, TaskStatus.VALIDATING)
        self.assertEqual(self.publisher.events[0][1]["new_status"], "validating")

    async def test_dispatch_queue_failure_marks_task_failed(self) -> None:
        self.queue.fail_enqueue = True
        with self.assertRaises(ExternalServiceError):
            await self.service.dispatch(self.task.id, make_actor(self.task))
        self.assertEqual(self.tasks[self.task.id].status, TaskStatus.FAILED)

    async def test_completed_task_cannot_be_cancelled(self) -> None:
        pending = (
            self.task.transition(TaskStatus.VALIDATING)
            .transition(TaskStatus.ANALYZING)
            .transition(TaskStatus.PENDING_REVIEW)
        )
        completed = pending.transition(TaskStatus.COMPLETED, actor_id=self.task.created_by)
        self.tasks[self.task.id] = completed
        with self.assertRaises(BusinessError):
            await self.service.cancel(completed.id, make_actor(completed))

    async def test_retry_increments_root_counter_and_creates_new_task(self) -> None:
        failed = make_task(TaskStatus.FAILED, retry_count=1)
        self.tasks = {failed.id: failed}
        factory = MemoryRepositoryFactory(self.tasks)
        inputs = MemoryInputStore({failed.id: {"query": "重试"}})
        service = TaskSchedulerService(factory, self.queue, self.publisher, inputs)

        retried = await service.retry(failed.id, make_actor(failed, is_admin=True))

        self.assertEqual(retried.retry_count, 2)
        self.assertEqual(retried.retry_of_task_id, failed.id)
        self.assertEqual(self.tasks[failed.id].retry_count, 2)
        self.assertIn(retried.id, inputs.values)
        self.assertEqual(self.queue.enqueued[0][0], retried.id)

    async def test_queue_failure_marks_persisted_retry_failed(self) -> None:
        failed = make_task(TaskStatus.FAILED)
        tasks = {failed.id: failed}
        queue = FakeQueue()
        queue.fail_enqueue = True
        inputs = MemoryInputStore({failed.id: {"query": "重试"}})
        service = TaskSchedulerService(
            MemoryRepositoryFactory(tasks), queue, self.publisher, inputs
        )

        with self.assertRaises(ExternalServiceError):
            await service.retry(failed.id, make_actor(failed))

        retry_tasks = [task for task in tasks.values() if task.id != failed.id]
        self.assertEqual(len(retry_tasks), 1)
        self.assertEqual(retry_tasks[0].status, TaskStatus.FAILED)
        self.assertEqual(retry_tasks[0].error_details["phase"], "queue_dispatch")

    async def test_same_failed_task_cannot_create_parallel_retry_branches(self) -> None:
        failed = make_task(TaskStatus.FAILED)
        tasks = {failed.id: failed}
        inputs = MemoryInputStore({failed.id: {"query": "重试"}})
        service = TaskSchedulerService(
            MemoryRepositoryFactory(tasks), self.queue, self.publisher, inputs
        )
        await service.retry(failed.id, make_actor(failed))
        with self.assertRaises(ResourceConflictError):
            await service.retry(failed.id, make_actor(tasks[failed.id]))

    async def test_list_hides_unassigned_projects(self) -> None:
        actor = TaskActor(
            user_id=self.task.created_by,
            tenant_id=self.task.tenant_id,
            project_roles={},
        )
        page = await self.service.list_tasks(actor=actor)
        self.assertEqual(page.total, 0)


if __name__ == "__main__":
    unittest.main()
