from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import httpx

from backend.core.enums import TaskType
from backend.core.errors import ErrorCode, ExternalServiceError
from backend.domain.ports import LLMResponse, LLMUsage
from backend.domain.task import ModelBinding


class AnthropicLLMGateway:
    """Claude Messages API 网关，强制 JSON 输出和低温度分析。"""

    API_VERSION = "2023-06-01"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 120,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("LLM API Key 不能为空")
        self._api_key = api_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
        )

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
        payload = {
            "model": model.name,
            "max_tokens": max_output_tokens,
            "temperature": float(model.temperature),
            "system": self._system_prompt(task_type, prompt_name, model.prompt_version),
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "input": input_data,
                            "context": list(context),
                            "rule_results": list(rule_results),
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                }
            ],
        }
        try:
            response = await self._client.post(
                "/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": self.API_VERSION,
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
            content = self._parse_content(body)
            usage_data = body.get("usage", {})
            return LLMResponse(
                content=content,
                usage=LLMUsage(
                    prompt_tokens=int(usage_data.get("input_tokens", 0)),
                    completion_tokens=int(usage_data.get("output_tokens", 0)),
                    request_id=response.headers.get("request-id"),
                    # body.model 是模型名称，不等同于治理版本标识。
                    model_version=response.headers.get("anthropic-model-version"),
                    is_cached=bool(usage_data.get("cache_read_input_tokens", 0)),
                ),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ExternalServiceError(
                ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
                "大模型服务调用失败",
                detail=str(exc),
            ) from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _parse_content(body: Mapping[str, Any]) -> Mapping[str, Any]:
        blocks = body.get("content")
        if not isinstance(blocks, Sequence) or isinstance(blocks, (str, bytes)):
            raise ValueError("大模型响应缺少 content")
        text = "".join(
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, Mapping) and block.get("type") == "text"
        ).strip()
        if text.startswith("```json"):
            text = text.removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(text)
        if not isinstance(parsed, Mapping):
            raise ValueError("大模型响应必须是 JSON 对象")
        return parsed

    @staticmethod
    def _system_prompt(
        task_type: TaskType,
        prompt_name: str,
        prompt_version: str,
    ) -> str:
        return (
            "你是产品分析平台的受控分析角色。"
            f"任务类型={task_type.value}，模板={prompt_name}，版本={prompt_version}。"
            "只能依据 context 和 rule_results 输出 JSON 对象；每个事实必须携带与 context "
            "完全一致的 citation，无法定位引用时标记 evidence_type=inference，"
            "材料不足时标记 missing。"
        )
