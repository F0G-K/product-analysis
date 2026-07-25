from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from backend.analysis_tasks.service import AnalysisTaskCreationService
from backend.core.enums import ProjectRole, TaskStatus, TaskType
from backend.core.errors import PermissionDeniedError
from backend.core.settings import Settings
from backend.domain.task import TaskActor
from tests.fakes import MemoryInputStore, MemoryRepositoryFactory


class FakeProjectAccess:
    def __init__(self) -> None:
        self.checked: list[UUID] = []

    async def ensure_access(self, project_id: UUID, actor: TaskActor) -> None:
        self.checked.append(project_id)


class AnalysisTaskCreationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.project_id = uuid4()
        self.actor = TaskActor(
            user_id=uuid4(),
            tenant_id=uuid4(),
            project_roles={self.project_id: ProjectRole.PROJECT_MEMBER},
        )
        self.tasks = {}
        self.inputs = MemoryInputStore()
        self.access = FakeProjectAccess()
        self.service = AnalysisTaskCreationService(
            MemoryRepositoryFactory(self.tasks),
            self.inputs,
            self.access,
            Settings(_env_file=None),
        )

    async def test_create_persists_draft_and_analysis_input(self) -> None:
        task = await self.service.create(
            actor=self.actor,
            project_id=self.project_id,
            task_type=TaskType.ASSESSMENT,
            title="用户画像需求评估",
            description="评估业务价值",
            query="请评估需求价值和风险",
            input_data={"content": "需求材料"},
        )

        self.assertEqual(task.status, TaskStatus.DRAFT)
        self.assertEqual(task.task_type, TaskType.ASSESSMENT)
        self.assertIsNotNone(task.model_binding)
        self.assertIn(task.id, self.tasks)
        self.assertEqual(self.inputs.values[task.id]["query"], "请评估需求价值和风险")
        self.assertEqual(self.access.checked, [self.project_id])

    async def test_viewer_cannot_create_analysis_task(self) -> None:
        viewer = TaskActor(
            user_id=uuid4(),
            tenant_id=self.actor.tenant_id,
            project_roles={self.project_id: ProjectRole.VIEWER},
        )

        with self.assertRaises(PermissionDeniedError):
            await self.service.create(
                actor=viewer,
                project_id=self.project_id,
                task_type=TaskType.ATTRIBUTION,
                title="问题归因",
                description=None,
                query="请分析根因",
                input_data={"content": "异常材料"},
            )


if __name__ == "__main__":
    unittest.main()
