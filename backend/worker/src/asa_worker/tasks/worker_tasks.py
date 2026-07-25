"""AI 角色执行 Celery 入口。"""

from asa_core.application.commands.execute_stage import dispatch_next_stage_after_commit
from asa_core.application.commands.execute_worker import ExecuteWorkerCommand
from asa_core.domain.scheduling.exceptions import ProjectCancellationRequested
from asa_core.infrastructure.database.scheduling_repository import (
    SqlAlchemySchedulingRepository,
)

from asa_worker.bootstrap import container
from asa_worker.celery_app import celery_app
from asa_worker.message_schema import WorkerTaskPayload
from asa_worker.tasks.runtime import run_async


async def _execute(payload: WorkerTaskPayload) -> dict[str, object]:
    command = ExecuteWorkerCommand(**payload.model_dump())
    async with container.session_factory() as session:
        handler = container.create_worker_handler(session)
        async with session.begin():
            repository = SqlAlchemySchedulingRepository(session)
            replay = await handler.claim(command, repository=repository)
        if replay is not None:
            return {
                "worker_task_id": str(replay.worker_task_id),
                "task_status": str(replay.task_status),
                "replayed": True,
            }

    # 上下文读取结束后释放连接，再进行模型网络调用。
    async with container.session_factory() as context_session:
        handler = container.create_worker_handler(context_session)
        request = await handler.build_model_request(
            command,
            repository=SqlAlchemySchedulingRepository(context_session),
        )
    summary = await handler.call_model(request)

    async with container.session_factory() as cancel_session:
        project = await SqlAlchemySchedulingRepository(cancel_session).get_project(payload.project_id)
    if project is None or project.stop_requested_at is not None:
        raise ProjectCancellationRequested()

    async with container.session_factory() as session:
        handler = container.create_worker_handler(session)
        async with session.begin():
            repository = SqlAlchemySchedulingRepository(session)
            result, messages, next_stage_id = await handler.finalize_success(
                command,
                result_summary=summary,
                repository=repository,
            )
    if messages:
        await container.dispatcher.dispatch_workers(messages)
    if next_stage_id is not None:
        await dispatch_next_stage_after_commit(
            dispatcher=container.dispatcher,
            project_id=payload.project_id,
            stage_id=next_stage_id,
            request_id=payload.request_id,
        )
    return {
        "worker_task_id": str(result.worker_task_id),
        "task_status": str(result.task_status),
        "replayed": result.replayed,
    }


async def _converge_failure(payload: WorkerTaskPayload, exc: Exception) -> None:
    async with container.session_factory() as session:
        async with session.begin():
            await container.converge_failure_handler.handle(
                ExecuteWorkerCommand(**payload.model_dump()),
                error_message=str(exc),
                repository=SqlAlchemySchedulingRepository(session),
            )


@celery_app.task(
    bind=True,
    name="asa.agents.execute_worker",
    acks_late=True,
)
def execute_worker(self, **message):
    payload = WorkerTaskPayload.model_validate(message)
    try:
        return run_async(_execute(payload))
    except Exception as exc:
        if isinstance(exc, ProjectCancellationRequested):
            run_async(_cancel_after_request(payload))
            raise
        decision = container.retry_policy.decide(exc, retries=self.request.retries)
        if decision.retry:
            raise self.retry(
                exc=exc,
                countdown=decision.countdown_seconds,
            ) from exc
        run_async(_converge_failure(payload, exc))
        raise


async def _cancel_after_request(payload: WorkerTaskPayload) -> None:
    from asa_core.application.commands.cancel_project import CancelProjectCommand

    async with container.session_factory() as session:
        async with session.begin():
            await container.cancel_project_handler.handle(
                CancelProjectCommand(
                    project_id=payload.project_id,
                    request_id=payload.request_id,
                ),
                repository=SqlAlchemySchedulingRepository(session),
            )
