from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.analysis_tasks.service import AnalysisTaskCreationService
from backend.auth.service import DEFAULT_TENANT_ID, DEFAULT_USER_ID
from backend.core.settings import Settings
from backend.domain.task import TaskActor
from backend.main import create_app
from backend.projects.service import Project, ProjectPage, ProjectService
from backend.scheduling.service import TaskSchedulerService
from tests.fakes import (
    FakePublisher,
    FakeQueue,
    MemoryInputStore,
    MemoryRepositoryFactory,
)


class MemoryProjectService(ProjectService):
    def __init__(self) -> None:
        self.projects: dict[UUID, Project] = {}

    async def create_project(
        self,
        *,
        actor: TaskActor,
        name: str,
        description: str | None,
        timezone: str,
    ) -> Project:
        now = datetime.now(UTC)
        project = Project(
            id=uuid4(),
            tenant_id=actor.tenant_id,
            name=name,
            description=description,
            status="active",
            timezone=timezone,
            settings={},
            created_at=now,
            updated_at=now,
        )
        self.projects[project.id] = project
        return project

    async def list_projects(self, **kwargs: Any) -> ProjectPage:
        items = tuple(self.projects.values())
        return ProjectPage(items=items, total=len(items), page=1, page_size=20)

    async def get_project(self, project_id: UUID, actor: TaskActor) -> Project:
        return self.projects[project_id]

    async def ensure_access(self, project_id: UUID, actor: TaskActor) -> None:
        if project_id not in self.projects:
            raise KeyError(project_id)


class CreationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tasks = {}
        self.inputs = MemoryInputStore()
        self.repository_factory = MemoryRepositoryFactory(self.tasks)
        self.projects = MemoryProjectService()
        self.app = create_app(actor_resolver=self._resolve_actor)
        self.app.state.project_service = self.projects
        self.app.state.task_scheduler_service = TaskSchedulerService(
            self.repository_factory,
            FakeQueue(),
            FakePublisher(),
            self.inputs,
        )
        self.app.state.analysis_task_creation_service = AnalysisTaskCreationService(
            self.repository_factory,
            self.inputs,
            self.projects,
            Settings(_env_file=None),
        )
        self.client = TestClient(self.app)
        login = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        self.headers = {
            "Authorization": f"Bearer {login.json()['data']['access_token']}"
        }

    @staticmethod
    async def _resolve_actor(request: Any) -> TaskActor:
        return TaskActor(
            user_id=DEFAULT_USER_ID,
            tenant_id=DEFAULT_TENANT_ID,
            is_tenant_admin=True,
        )

    def test_project_and_analysis_task_creation_flow(self) -> None:
        project_response = self.client.post(
            "/api/v1/projects",
            headers=self.headers,
            json={"name": "新零售平台", "timezone": "Asia/Shanghai"},
        )
        self.assertEqual(project_response.status_code, 201)
        project_id = project_response.json()["data"]["id"]

        task_response = self.client.post(
            f"/api/v1/projects/{project_id}/analysis-tasks",
            headers=self.headers,
            json={
                "task_type": "assessment",
                "title": "需求价值评估",
                "query": "请评估需求价值和风险",
                "input_data": {"content": "需求背景与目标用户"},
            },
        )
        self.assertEqual(task_response.status_code, 201)
        body = task_response.json()["data"]
        self.assertEqual(body["status"], "draft")
        self.assertEqual(body["task_type"], "assessment")
        self.assertIn(UUID(body["id"]), self.inputs.values)


if __name__ == "__main__":
    unittest.main()
