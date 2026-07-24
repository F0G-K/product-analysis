from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.asyncio.lock import Lock

from backend.domain.ports import LLMResponse, LLMUsage


class RedisDistributedLock:
    def __init__(self, lock: Lock) -> None:
        self._lock = lock
        self._acquired = False

    async def __aenter__(self) -> bool:
        self._acquired = bool(await self._lock.acquire(blocking=False))
        return self._acquired

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._acquired and await self._lock.owned():
            await self._lock.release()


class RedisLockManager:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def lock(self, key: str, *, ttl_seconds: int) -> RedisDistributedLock:
        return RedisDistributedLock(
            self._redis.lock(
                name=key,
                timeout=ttl_seconds,
                blocking_timeout=0,
                thread_local=False,
            )
        )


class RedisAnalysisInputStore:
    """短期保存异步任务输入，TTL 覆盖最长任务及人工确认等待窗口。"""

    def __init__(self, redis: Redis, *, ttl_seconds: int = 86_400) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, task_id: UUID) -> Mapping[str, Any] | None:
        value = await self._redis.get(self._key(task_id))
        if value is None:
            return None
        decoded = json.loads(value)
        if not isinstance(decoded, Mapping):
            return None
        return decoded

    async def put(self, task_id: UUID, payload: Mapping[str, Any]) -> None:
        await self._redis.set(
            self._key(task_id),
            json.dumps(payload, ensure_ascii=False, default=str),
            ex=self._ttl_seconds,
        )

    async def copy(self, source_task_id: UUID, target_task_id: UUID) -> None:
        source = await self._redis.get(self._key(source_task_id))
        if source is None:
            raise ValueError("原任务分析输入不存在")
        await self._redis.set(self._key(target_task_id), source, ex=self._ttl_seconds)

    @staticmethod
    def _key(task_id: UUID) -> str:
        return f"task:input:{task_id}"


class RedisEventPublisher:
    def __init__(self, redis: Redis, *, channel: str = "task-events") -> None:
        self._redis = redis
        self._channel = channel

    async def publish(self, event: str, payload: Mapping[str, Any]) -> None:
        message = json.dumps(
            {"event": event, "data": payload},
            ensure_ascii=False,
            default=str,
        )
        await self._redis.publish(self._channel, message)


class RedisLLMCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, key: str) -> LLMResponse | None:
        value = await self._redis.get(key)
        if value is None:
            return None
        payload = json.loads(value)
        return LLMResponse(
            content=payload["content"],
            usage=LLMUsage(
                prompt_tokens=0,
                completion_tokens=0,
                # 缓存命中没有新的供应商请求，避免治理表 request_id 唯一索引冲突。
                request_id=None,
                model_version=payload.get("model_version"),
                is_cached=True,
            ),
        )

    async def set(self, key: str, response: LLMResponse, *, ttl_seconds: int) -> None:
        payload = {
            "content": response.content,
            "request_id": response.usage.request_id,
            "model_version": response.usage.model_version,
        }
        await self._redis.set(
            key,
            json.dumps(payload, ensure_ascii=False, default=str),
            ex=ttl_seconds,
        )
