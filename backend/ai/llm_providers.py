"""多后端 LLM 网关。

支持三种大模型接入方式：
1. Anthropic API (Claude)
2. OpenAI 兼容 API (vLLM / DeepSeek / 通义千问 / 智谱 等)
3. 本地部署模型 (Ollama / vLLM local)

通过 LLMProviderFactory 根据配置自动创建对应 provider。
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any
from uuid import UUID

import httpx

from backend.core.enums import TaskType
from backend.core.errors import ErrorCode, ExternalServiceError
from backend.domain.ports import LLMResponse, LLMUsage
from backend.domain.task import ModelBinding

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """LLM Provider 基类。"""

    @abstractmethod
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
        ...

    @abstractmethod
    async def chat_stream(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: Sequence[Mapping[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """流式聊天对话，逐块返回文本 delta。"""
        ...

    @abstractmethod
    async def aclose(self) -> None:
        ...

    @staticmethod
    def _build_user_content(
        input_data: Mapping[str, Any],
        context: Sequence[Mapping[str, Any]],
        rule_results: Sequence[Mapping[str, Any]],
    ) -> str:
        return json.dumps(
            {
                "input": input_data,
                "context": list(context),
                "rule_results": list(rule_results),
            },
            ensure_ascii=False,
            default=str,
        )


class AnthropicProvider(BaseLLMProvider):
    """Claude Messages API Provider。"""

    API_VERSION = "2023-06-01"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        timeout_seconds: float = 120,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Anthropic API Key 不能为空")
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
                    "content": self._build_user_content(input_data, context, rule_results),
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
                    model_version=response.headers.get("anthropic-model-version"),
                    is_cached=bool(usage_data.get("cache_read_input_tokens", 0)),
                ),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ExternalServiceError(
                ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
                "Anthropic API 调用失败",
                detail=str(exc),
            ) from exc

    async def chat_stream(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: Sequence[Mapping[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": list(messages),
            "stream": True,
        }
        async with self._client.stream(
            "POST",
            "/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": self.API_VERSION,
                "content-type": "application/json",
            },
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line.removeprefix("data: ").strip()
                if data_str == "[DONE]":
                    continue
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type", "")
                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield text
                elif event_type == "message_stop":
                    break

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
    def _system_prompt(task_type: TaskType, prompt_name: str, prompt_version: str) -> str:
        return (
            "你是产品分析平台的受控分析角色。"
            f"任务类型={task_type.value}，模板={prompt_name}，版本={prompt_version}。"
            "只能依据 context 和 rule_results 输出 JSON 对象；每个事实必须携带与 context "
            "完全一致的 citation，无法定位引用时标记 evidence_type=inference，"
            "材料不足时标记 missing。"
        )


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI 兼容 API Provider。

    适用于：vLLM、DeepSeek、通义千问、智谱、Moonshot 等兼容 OpenAI 格式的 API。
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 120,
        client: httpx.AsyncClient | None = None,
    ) -> None:
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
        system_prompt = (
            "你是产品分析平台的受控分析角色。"
            f"任务类型={task_type.value}，模板={prompt_name}，版本={model.prompt_version}。"
            "只能依据 context 和 rule_results 输出 JSON 对象；每个事实必须携带与 context "
            "完全一致的 citation，无法定位引用时标记 evidence_type=inference，"
            "材料不足时标记 missing。"
        )

        payload = {
            "model": model.name,
            "max_tokens": max_output_tokens,
            "temperature": float(model.temperature),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": self._build_user_content(input_data, context, rule_results),
                },
            ],
        }

        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = await self._client.post(
                "/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

            text = body["choices"][0]["message"]["content"].strip()
            if text.startswith("```json"):
                text = text.removeprefix("```json").removesuffix("```").strip()
            content = json.loads(text)
            if not isinstance(content, Mapping):
                raise ValueError("大模型响应必须是 JSON 对象")

            usage_data = body.get("usage", {})
            return LLMResponse(
                content=content,
                usage=LLMUsage(
                    prompt_tokens=int(usage_data.get("prompt_tokens", 0)),
                    completion_tokens=int(usage_data.get("completion_tokens", 0)),
                    request_id=response.headers.get("x-request-id"),
                    model_version=body.get("model"),
                ),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ExternalServiceError(
                ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
                "OpenAI 兼容 API 调用失败",
                detail=str(exc),
            ) from exc

    async def chat_stream(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: Sequence[Mapping[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[str]:
        api_messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)

        payload = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "messages": api_messages,
            "stream": True,
        }
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with self._client.stream(
            "POST",
            "/v1/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                try:
                    err = json.loads(body)
                    msg = err.get("error", {}).get("message", body.decode())
                except Exception:
                    msg = body.decode()[:500]
                raise ExternalServiceError(
                    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
                    f"OpenAI 兼容 API 返回错误: {msg}",
                    detail=str(msg),
                )
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line.removeprefix("data: ").strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                text = delta.get("content", "")
                if text:
                    yield text

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class OllamaProvider(BaseLLMProvider):
    """Ollama 本地模型 Provider。

    适用于本地部署的 Ollama 服务，默认地址 http://localhost:11434。
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 300,
        client: httpx.AsyncClient | None = None,
    ) -> None:
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
        system_prompt = (
            "你是产品分析平台的受控分析角色。"
            f"任务类型={task_type.value}，模板={prompt_name}，版本={model.prompt_version}。"
            "只能依据 context 和 rule_results 输出 JSON 对象。"
            "请严格以 JSON 格式输出，不要包含其他文本。"
        )

        payload = {
            "model": model.name,
            "system": system_prompt,
            "prompt": self._build_user_content(input_data, context, rule_results),
            "stream": False,
            "options": {
                "temperature": float(model.temperature),
                "num_predict": max_output_tokens,
            },
        }

        try:
            response = await self._client.post("/api/generate", json=payload)
            response.raise_for_status()
            body = response.json()

            text = body.get("response", "").strip()
            if text.startswith("```json"):
                text = text.removeprefix("```json").removesuffix("```").strip()
            content = json.loads(text)
            if not isinstance(content, Mapping):
                raise ValueError("大模型响应必须是 JSON 对象")

            return LLMResponse(
                content=content,
                usage=LLMUsage(
                    prompt_tokens=int(body.get("prompt_eval_count", 0)),
                    completion_tokens=int(body.get("eval_count", 0)),
                    model_version=body.get("model"),
                ),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ExternalServiceError(
                ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
                "Ollama 本地模型调用失败",
                detail=str(exc),
            ) from exc

    async def chat_stream(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: Sequence[Mapping[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[str]:
        # 将 messages 拼接为 prompt 文本
        prompt_parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(f"用户: {content}")
            elif role == "assistant":
                prompt_parts.append(f"助手: {content}")
        prompt_parts.append("助手: ")
        full_prompt = "\n\n".join(prompt_parts)

        payload = {
            "model": model_name,
            "system": system_prompt,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": max_tokens,
            },
        }
        async with self._client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = chunk.get("response", "")
                if text:
                    yield text
                if chunk.get("done", False):
                    break

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class LLMProviderFactory:
    """LLM Provider 工厂：根据配置创建对应的 provider 实例。"""

    def __init__(self, providers: Mapping[str, BaseLLMProvider]) -> None:
        self._providers = dict(providers)

    def get(self, provider_name: str) -> BaseLLMProvider:
        provider = self._providers.get(provider_name)
        if provider is None:
            available = ", ".join(self._providers.keys())
            raise ValueError(f"未知的 LLM provider: {provider_name}，可用: {available}")
        return provider

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers.keys())

    async def aclose(self) -> None:
        for provider in self._providers.values():
            await provider.aclose()


def create_default_provider_factory(
    *,
    anthropic_api_key: str = "",
    anthropic_base_url: str = "https://api.anthropic.com",
    openai_api_key: str = "",
    openai_base_url: str = "",
    ollama_base_url: str = "http://localhost:11434",
) -> LLMProviderFactory:
    """根据环境变量创建默认 provider 工厂。"""
    providers: dict[str, BaseLLMProvider] = {}

    if anthropic_api_key:
        providers["anthropic"] = AnthropicProvider(
            api_key=anthropic_api_key,
            base_url=anthropic_base_url,
        )
        logger.info("llm_provider.registered", extra={"provider": "anthropic"})

    if openai_base_url:
        providers["openai_compatible"] = OpenAICompatibleProvider(
            api_key=openai_api_key,
            base_url=openai_base_url,
        )
        logger.info("llm_provider.registered", extra={"provider": "openai_compatible"})

    # Ollama 始终注册，连接失败时在调用时报告
    providers["ollama"] = OllamaProvider(base_url=ollama_base_url)
    logger.info("llm_provider.registered", extra={"provider": "ollama"})

    return LLMProviderFactory(providers)
