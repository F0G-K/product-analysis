"""数据库审计日志实现。"""

import uuid
from typing import Any

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.infrastructure.database.models import AuditLogModel
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyAuditLogger(AuditLogger):
    """使用当前业务事务写入审计日志，避免审计与业务部分提交。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def log(
        self,
        action: str,
        object_type: str,
        result_status: str,
        *,
        actor_user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        client_ip: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if request_id is None:
            request_id = uuid.uuid4()
        self._session.add(
            AuditLogModel(
                actor_user_id=actor_user_id,
                project_id=project_id,
                request_id=request_id,
                action=action,
                object_type=object_type,
                object_id=str(project_id) if project_id is not None else None,
                result_status=result_status,
                client_ip=client_ip,
                idempotency_key=idempotency_key,
                metadata_json=metadata or {},
            )
        )
