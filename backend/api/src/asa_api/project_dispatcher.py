"""API 侧项目异步任务投递适配器。"""

import uuid

from asa_api.stage_dispatcher import CeleryApiStageDispatcher
from asa_core.application.ports.project_repository import StartProjectResources
from asa_core.application.ports.project_task_dispatcher import ProjectTaskDispatcher
from asa_core.application.ports.stage_task_dispatcher import StageTaskMessage
from asa_core.domain.projects.exceptions import DependencyUnavailable


class ApiProjectTaskDispatcher(ProjectTaskDispatcher):
    """将项目受理结果转换为调度模块消息。

    导入 Worker 适配器放在方法内部，避免 API 启动阶段提前初始化
    Celery 客户端；实际投递仍发生在数据库事务提交之后。
    """

    async def dispatch_start(
        self,
        *,
        project_id: uuid.UUID,
        resources: StartProjectResources,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        try:
            await CeleryApiStageDispatcher().dispatch_stage(
                StageTaskMessage(
                    project_id=project_id,
                    stage_id=resources.first_stage_id,
                    request_id=request_id,
                    idempotency_key=(f"stage:{resources.first_stage_id}:start:{idempotency_key}"),
                )
            )
        except Exception as exc:
            raise DependencyUnavailable() from exc

    async def dispatch_stop(
        self,
        *,
        project_id: uuid.UUID,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        del idempotency_key
        try:
            import os

            from celery import Celery

            broker_url = os.getenv(
                "ASA_CELERY_BROKER_URL",
                os.getenv("ASA_REDIS_URL", "redis://root:kkkcm520@127.0.0.1:6380/0"),
            )
            Celery("asa_api_dispatcher", broker=broker_url).send_task(
                "asa.scheduler.cancel_project",
                kwargs={
                    "project_id": str(project_id),
                    "request_id": str(request_id),
                    "schema_version": 1,
                },
                queue="scheduler",
            )
        except Exception as exc:
            raise DependencyUnavailable() from exc

    async def dispatch_delete(
        self,
        *,
        project_id: uuid.UUID,
        request_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        # cleanup 模块尚无稳定消息契约，受理记录和 Outbox 保留恢复依据。
        return None
