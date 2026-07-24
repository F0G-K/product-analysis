from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from backend.ai.cached_llm_gateway import CachedLLMGateway
from backend.core.enums import TaskType
from backend.domain.ports import LLMResponse, LLMUsage
from backend.domain.task import ModelBinding
from tests.fakes import FakeLLMGateway


class MemoryLLMCache:
    def __init__(self) -> None:
        self.values: dict[str, LLMResponse] = {}

    async def get(self, key: str) -> LLMResponse | None:
        response = self.values.get(key)
        if response is None:
            return None
        return LLMResponse(
            content=response.content,
            usage=LLMUsage(
                prompt_tokens=0,
                completion_tokens=0,
                request_id=response.usage.request_id,
                model_version=response.usage.model_version,
                is_cached=True,
            ),
        )

    async def set(self, key: str, response: LLMResponse, *, ttl_seconds: int) -> None:
        self.values[key] = response


class CachedLLMGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_tenant_and_input_reuses_cached_result(self) -> None:
        gateway = FakeLLMGateway()
        cached = CachedLLMGateway(gateway, MemoryLLMCache())
        tenant_id = uuid4()
        kwargs = self._kwargs(tenant_id)

        first = await cached.analyze(**kwargs)
        second = await cached.analyze(**kwargs)

        self.assertFalse(first.usage.is_cached)
        self.assertTrue(second.usage.is_cached)
        self.assertEqual(len(gateway.calls), 1)

    async def test_cache_is_isolated_by_tenant(self) -> None:
        gateway = FakeLLMGateway()
        cached = CachedLLMGateway(gateway, MemoryLLMCache())

        await cached.analyze(**self._kwargs(uuid4()))
        await cached.analyze(**self._kwargs(uuid4()))

        self.assertEqual(len(gateway.calls), 2)

    @staticmethod
    def _kwargs(tenant_id):
        return {
            "tenant_id": tenant_id,
            "task_type": TaskType.ASSESSMENT,
            "model": ModelBinding(
                name="claude-opus-4-8",
                version="20260724",
                prompt_version="abc1234",
                temperature=Decimal("0.20"),
            ),
            "prompt_name": "assessment_scoring",
            "context": ({"citation": "doc:section", "content": "事实"},),
            "rule_results": (),
            "input_data": {"name": "画像看板"},
            "max_output_tokens": 4096,
        }


if __name__ == "__main__":
    unittest.main()
