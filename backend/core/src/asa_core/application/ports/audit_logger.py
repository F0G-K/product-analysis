"""AuditLogger Port 接口。

定义审计日志的标准接口。
MVP 阶段提供接口定义，实现可为 No-Op 或写入 audit_logs 表。
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any


class AuditLogger(ABC):
    """审计日志接口（应用层 Port）。

    记录系统关键操作（初始化、登录成功/失败、越权访问等）。
    审计写入失败时，安全敏感操作不得静默成功。
    """

    @abstractmethod
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
        """写入一条脱敏审计记录。

        Args:
            action: 操作标识（如 'system_init', 'login'）。
            object_type: 操作对象类型（如 'system', 'user'）。
            result_status: 操作结果（'success', 'failure', 'denied'）。
            actor_user_id: 操作者用户 ID。
            project_id: 关联项目 ID。
            request_id: 请求链路 ID。
            client_ip: 客户端 IP。
            idempotency_key: 写操作的幂等键。
            metadata: 脱敏后的扩展信息（不得包含密码、Token 等）。
        """
        ...


class NoOpAuditLogger(AuditLogger):
    """No-Op 审计日志实现。

    用于 MVP 阶段暂时不需要完整的审计日志存储的场景。
    所有 log 调用均为空操作。
    """

    async def log(
        self,
        action: str,
        object_type: str,
        result_status: str,
        **kwargs: Any,
    ) -> None:
        """空操作：不写入任何审计记录。"""
        pass
