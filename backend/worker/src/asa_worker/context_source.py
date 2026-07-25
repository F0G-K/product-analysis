"""数据库侧 AI 上下文来源。"""

import uuid
from typing import Any

from asa_core.application.ports.context_source import AgentContextSource, ProjectContext
from asa_core.domain.scheduling.entities import RuntimeStage, WorkerTask
from asa_core.infrastructure.database.models import ProjectModel, RuntimeStageModel, WorkerTaskModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyAgentContextSource(AgentContextSource):
    """当前模块只读取结构化摘要；源码片段由后续 Executor 适配器提供。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_project_context(self, project_id: uuid.UUID) -> ProjectContext:
        stmt = select(
            ProjectModel.project_name,
            ProjectModel.task_content,
            ProjectModel.environment_type,
        ).where(ProjectModel.id == project_id)
        row = (await self._session.execute(stmt)).one()
        return ProjectContext(
            project_name=row.project_name,
            task_content=row.task_content,
            environment_type=row.environment_type,
        )

    async def get_previous_results(
        self,
        project_id: uuid.UUID,
        stage: RuntimeStage,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                RuntimeStageModel.stage_name,
                WorkerTaskModel.worker_role,
                WorkerTaskModel.result_summary,
            )
            .join(
                WorkerTaskModel,
                WorkerTaskModel.stage_id == RuntimeStageModel.id,
            )
            .where(
                RuntimeStageModel.project_id == project_id,
                RuntimeStageModel.stage_order < stage.stage_order,
                WorkerTaskModel.task_status == "success",
            )
            .order_by(RuntimeStageModel.stage_order.asc(), WorkerTaskModel.created_at.asc())
            .limit(100)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            {
                "stage": row.stage_name,
                "worker_role": row.worker_role,
                "summary": row.result_summary,
            }
            for row in rows
        ]

    async def get_source_snippets(self, task: WorkerTask) -> list[dict[str, Any]]:
        # 角色不得直接读宿主机；待 Executor Port 接入后由受控文件工具提供。
        return []
