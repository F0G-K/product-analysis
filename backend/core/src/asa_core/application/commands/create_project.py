"""创建项目用例。"""

import uuid
from dataclasses import dataclass

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.project_repository import ProjectRepository
from asa_core.domain.projects.entities import Project
from asa_core.domain.projects.exceptions import EnvironmentTypeDisabled
from asa_core.domain.projects.validators import SourcePathValidator
from asa_core.domain.projects.value_objects import EnvironmentType, ProjectName, TaskContent


@dataclass(frozen=True)
class CreateProjectCommand:
    project_name: str
    source_type: str
    source_path: str
    task_content: str
    environment_type: str
    actor_user_id: uuid.UUID
    request_id: uuid.UUID


class CreateProjectHandler:
    """校验项目字段并创建 `created` 状态聚合。"""

    def __init__(self, audit_logger: AuditLogger):
        self._audit_logger = audit_logger

    async def handle(
        self,
        command: CreateProjectCommand,
        *,
        project_repo: ProjectRepository,
    ) -> Project:
        project_name = ProjectName(command.project_name).value
        task_content = TaskContent(command.task_content).value
        environment_type = EnvironmentType(command.environment_type).value
        source_path = SourcePathValidator.validate(command.source_type, command.source_path)

        enabled_environment_types, _ = await project_repo.get_active_configuration()
        if environment_type not in enabled_environment_types:
            raise EnvironmentTypeDisabled(environment_type)

        project = Project.create(
            project_name=project_name,
            source_type=command.source_type,
            source_path=source_path,
            task_content=task_content,
            environment_type=environment_type,
            created_by=command.actor_user_id,
        )
        await project_repo.add(project)
        await self._audit_logger.log(
            action="project_create",
            object_type="project",
            result_status="success",
            actor_user_id=command.actor_user_id,
            project_id=project.id,
            request_id=command.request_id,
            metadata={
                "source_type": project.source_type,
                "environment_type": project.environment_type,
            },
        )
        return project
