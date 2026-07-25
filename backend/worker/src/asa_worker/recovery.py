"""Worker 就绪后的异常任务恢复扫描。"""

import os

from asa_core.application.commands.recover_stale import RecoverStaleTasksCommand
from asa_core.infrastructure.database.scheduling_repository import (
    SqlAlchemySchedulingRepository,
)
from celery.signals import worker_ready

from asa_worker.bootstrap import container
from asa_worker.tasks.runtime import run_async


async def scan_stale_tasks() -> int:
    timeout = int(os.getenv("ASA_TASK_HEARTBEAT_TIMEOUT_SECONDS", "300"))
    async with container.session_factory() as session:
        tasks = await container.recover_stale_tasks_handler.handle(
            RecoverStaleTasksCommand(heartbeat_timeout_seconds=timeout),
            repository=SqlAlchemySchedulingRepository(session),
        )
    # 当前表结构未提供心跳和诊断状态，按规范只报告数量，不做猜测性收敛。
    return len(tasks)


def on_worker_ready(**kwargs: object) -> None:
    run_async(scan_stale_tasks())


worker_ready.connect(on_worker_ready, weak=False)
