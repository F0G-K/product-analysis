"""SessionStore Port 接口。

定义会话存储的标准接口，由基础设施层的 Redis 实现。
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime


class SessionStore(ABC):
    """会话存储接口（应用层 Port）。

    负责创建、校验和撤销用户登录会话。
    实现类负责选择存储后端（Redis、数据库等）。
    """

    @abstractmethod
    async def create_session(self, user_id: uuid.UUID, ttl_seconds: int | None = None) -> tuple[str, str, datetime]:
        """创建新的登录会话。

        Args:
            user_id: 关联的用户 ID。
            ttl_seconds: 会话有效期（秒），None 使用默认值。

        Returns:
            (session_token, csrf_token, expires_at) 三元组。
        """
        ...

    @abstractmethod
    async def validate_session(self, session_token: str) -> uuid.UUID | None:
        """验证会话 token 的有效性。

        Args:
            session_token: 不透明会话标识。

        Returns:
            关联的用户 ID，会话无效或已过期返回 None。
        """
        ...

    @abstractmethod
    async def revoke_session(self, session_token: str) -> None:
        """撤销会话（使会话失效）。

        操作为幂等：会话不存在也不报错。
        """
        ...

    @abstractmethod
    async def get_csrf_token(self, session_token: str) -> str | None:
        """获取与会话关联的 CSRF token。

        Returns:
            CSRF token 字符串，会话不存在返回 None。
        """
        ...
