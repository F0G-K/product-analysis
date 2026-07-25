"""项目停止收敛 Celery 入口。"""

from uuid import UUID

from asa_core.application.commands.cancel_project import CancelProjectCommand
from asa_core.infrastructure.database.scheduling_repository import (
    SqlAlchemySchedulingRepository,
)

from asa_worker.bootstrap import container
from asa_worker.celery_app import celery_app
from asa_worker.tasks.runtime import run_async


async def _cancel(project_id: UUID, request_id: UUID) -> None:
    async with container.session_factory() as session:
        async with session.begin():
            await container.cancel_project_handler.handle(
                CancelProjectCommand(
                    project_id=project_id,
                    request_id=request_id,
                ),
                repository=SqlAlchemySchedulingRepository(session),
            )


@celery_app.task(name="asa.scheduler.cancel_project", acks_late=True)
def cancel_project(*, project_id: str, request_id: str, schema_version: int = 1):
    if schema_version != 1:
        raise ValueError("不支持的任务消息版本")
    run_async(_cancel(UUID(project_id), UUID(request_id)))
