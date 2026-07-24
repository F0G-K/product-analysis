from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from backend.core.enums import TaskType
from backend.domain.ports import LLMCache, LLMGateway, LLMResponse
from backend.domain.task import ModelBinding

logger = logging.getLogger(__name__)


class CachedLLMGateway:
    TTL_SECONDS = 60 * 60

    def __init__(self, gateway: LLMGateway, cache: LLMCache) -> None:
        self._gateway = gateway
        self._cache = cache

    async def analyze(
        self,
        *,
        tenant_id: UUID,
        task_type: TaskType,
        model: ModelBinding,
        prompt_name: str,
        context: Sequence[Mapping[str, Any]],
        rule_results: Sequence[Mapping[str, Any]],
        input_data: Mapping[str, Any],
        max_output_tokens: int,
    ) -> LLMResponse:
        key = self._cache_key(
            tenant_id=tenant_id,
            task_type=task_type,
            model=model,
            prompt_name=prompt_name,
            context=context,
            rule_results=rule_results,
            input_data=input_data,
            max_output_tokens=max_output_tokens,
        )
        try:
            cached = await self._cache.get(key)
        except Exception:
            logger.warning("llm.cache_read_failed", exc_info=True)
            cached = None
        if cached is not None:
            return cached

        response = await self._gateway.analyze(
            tenant_id=tenant_id,
            task_type=task_type,
            model=model,
            prompt_name=prompt_name,
            context=context,
            rule_results=rule_results,
            input_data=input_data,
            max_output_tokens=max_output_tokens,
        )
        try:
            await self._cache.set(key, response, ttl_seconds=self.TTL_SECONDS)
        except Exception:
            logger.warning("llm.cache_write_failed", exc_info=True)
        return response

    @staticmethod
    def _cache_key(
        *,
        tenant_id: UUID,
        task_type: TaskType,
        model: ModelBinding,
        prompt_name: str,
        context: Sequence[Mapping[str, Any]],
        rule_results: Sequence[Mapping[str, Any]],
        input_data: Mapping[str, Any],
        max_output_tokens: int,
    ) -> str:
        payload = {
            "tenant_id": str(tenant_id),
            "task_type": task_type.value,
            "model": model.name,
            "model_version": model.version,
            "prompt_version": model.prompt_version,
            "prompt_name": prompt_name,
            "temperature": str(model.temperature),
            "max_output_tokens": max_output_tokens,
            "context": list(context),
            "rule_results": list(rule_results),
            "input_data": input_data,
        }
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"llm:cache:{digest}"
