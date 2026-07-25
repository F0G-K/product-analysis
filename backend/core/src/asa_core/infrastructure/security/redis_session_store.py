"""Redis 会话存储实现。

实现 application/ports/session_store.py 中定义的 SessionStore 接口。
使用 Redis 存储用户会话，支持 TTL 自动过期和主动撤销。

会话存储结构：
    asa:session:{token} → user_id (string)
    asa:csrf:{token}    → csrf_token (string)
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from asa_core.application.ports.session_store import SessionStore
from redis.asyncio import Redis


class RedisSessionStore(SessionStore):
    """基于 Redis 的会话存储。

    会话数据使用 Redis String 类型存储，通过 TTL 实现自动过期。
    """

    SESSION_KEY_PREFIX: str = "asa:session:"
    CSRF_KEY_PREFIX: str = "asa:csrf:"

    def __init__(self, redis_client: Redis, default_ttl_seconds: int = 7200):
        """
        Args:
            redis_client: Redis 异步客户端。
            default_ttl_seconds: 会话默认有效期，默认 2 小时。
        """
        self._redis = redis_client
        self._ttl = default_ttl_seconds

    def _session_key(self, token: str) -> str:
        return f"{self.SESSION_KEY_PREFIX}{token}"

    def _csrf_key(self, token: str) -> str:
        return f"{self.CSRF_KEY_PREFIX}{token}"

    async def create_session(self, user_id: uuid.UUID, ttl_seconds: int | None = None) -> tuple[str, str, datetime]:
        """创建新会话。

        Returns:
            (session_token, csrf_token, expires_at) 三元组。
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl

        # 生成不可预测的 token
        session_token: str = secrets.token_urlsafe(32)
        csrf_token: str = secrets.token_urlsafe(32)

        session_key = self._session_key(session_token)
        csrf_key = self._csrf_key(session_token)

        # 原子写入 session 和 csrf
        async with self._redis.pipeline() as pipe:
            pipe.set(session_key, str(user_id), ex=ttl)
            pipe.set(csrf_key, csrf_token, ex=ttl)
            await pipe.execute()

        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        return session_token, csrf_token, expires_at

    async def validate_session(self, session_token: str) -> uuid.UUID | None:
        """验证会话 token，返回关联的 user_id 或 None。"""
        key = self._session_key(session_token)
        value: bytes | None = await self._redis.get(key)
        if value is None:
            return None
        try:
            return uuid.UUID(value.decode("utf-8"))
        except (ValueError, AttributeError):
            return None

    async def revoke_session(self, session_token: str) -> None:
        """撤销会话（幂等操作）。

        同时删除 session 和 csrf 记录，返回值忽略（会话不存在也无妨）。
        """
        session_key = self._session_key(session_token)
        csrf_key = self._csrf_key(session_token)
        await self._redis.delete(session_key, csrf_key)

    async def get_csrf_token(self, session_token: str) -> str | None:
        """获取与 session 关联的 CSRF token。"""
        key = self._csrf_key(session_token)
        value: bytes | None = await self._redis.get(key)
        if value is None:
            return None
        return value.decode("utf-8")
