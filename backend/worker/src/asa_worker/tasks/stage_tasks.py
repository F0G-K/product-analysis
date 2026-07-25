"""阶段调度 Celery 入口。"""

from asa_core.application.commands.execute_stage import ExecuteStageCommand
from asa_core.infrastructure.database.scheduling_repository import (
    SqlAlchemySchedulingRepository,
)

import asa_worker.recovery  # noqa: E402,F401  # 注册 Worker ready 恢复扫描信号
from asa_worker.bootstrap import container
from asa_worker.celery_app import celery_app
from asa_worker.message_schema import StageTaskPayload
from asa_worker.tasks.runtime import run_async


async def _execute(payload: StageTaskPayload) -> dict[str, object]:
    async with container.session_factory() as session:
        async with session.begin():
            repository = SqlAlchemySchedulingRepository(session)
            result, messages = await container.execute_stage_handler.prepare(
                ExecuteStageCommand(**payload.model_dump()),
                repository=repository,
            )
    # Celery 消息必须在数据库事务提交后投递。
    if messages:
        await container.dispatcher.dispatch_workers(messages)
    return {
        "stage_id": str(result.stage_id),
        "stage_status": str(result.stage_status),
        "replayed": result.replayed,
    }


@celery_app.task(
    bind=True,
    name="asa.scheduler.execute_stage",
    acks_late=True,
)
def execute_stage(self, **message):
    payload = StageTaskPayload.model_validate(message)
    try:
        return run_async(_execute(payload))
    except Exception as exc:
        decision = container.retry_policy.decide(exc, retries=self.request.retries)
        if decision.retry:
            raise self.retry(
                exc=exc,
                countdown=decision.countdown_seconds,
            ) from exc
        raise
